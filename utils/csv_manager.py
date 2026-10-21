"""CSV persistence and CRUD managers used by all Streamlit pages."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data_cleaner import DataCleaner


class CSVStorageError(Exception):
    """Safe, user-facing description of a file operation failure."""


class ValidationError(ValueError):
    """Raised when submitted data does not meet a manager's schema."""


class CSVManager:
    COLUMNS: tuple[str, ...] = ()
    ID_COLUMN = ""
    NUMERIC: tuple[str, ...] = ()
    CATEGORICAL: tuple[str, ...] = ()
    DATES: tuple[str, ...] = ()
    BOUNDS: dict[str, tuple[float, float]] = {}
    ID_PATTERN = r"^[A-Z]{2,5}-\d{3,6}$"

    def __init__(self, file_path: str | Path):
        self.path = Path(file_path)
        self.cleaner = DataCleaner()
        self._data = pd.DataFrame(columns=self.COLUMNS)
        self._io_in_progress = False

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy()

    def _clean(self, frame: pd.DataFrame) -> pd.DataFrame:
        return self.cleaner.clean(frame, list(self.COLUMNS), id_column=self.ID_COLUMN,
                                  numeric=self.NUMERIC, categorical=self.CATEGORICAL,
                                  date_columns=self.DATES, bounds=self.BOUNDS)

    def _read_reference_csv(self, file_path: Path, columns: list[str]) -> pd.DataFrame:
        self._io_in_progress = True
        try:
            if not file_path.exists():
                raise FileNotFoundError(str(file_path))
            frame = pd.read_csv(file_path, usecols=columns)
        except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError, OSError) as exc:
            raise CSVStorageError("A related CSV file is missing or invalid. Check the project data folder.") from exc
        else:
            return frame
        finally:
            self._io_in_progress = False

    def load(self) -> pd.DataFrame:
        self._io_in_progress = True
        try:
            if not self.path.exists():
                raise FileNotFoundError(str(self.path))
            raw = pd.read_csv(self.path)
            if len(raw.columns) == 0:
                raise pd.errors.EmptyDataError("CSV has no columns")
            missing = set(self.COLUMNS) - set(raw.columns.str.strip())
            if missing:
                raise ValueError("CSV header does not match the required schema")
            cleaned = self._clean(raw)
            if not cleaned[self.ID_COLUMN].astype(str).str.fullmatch(self.ID_PATTERN).all():
                raise ValueError("CSV contains an invalid record ID")
        except FileNotFoundError as exc:
            raise CSVStorageError("The data file is missing. Restore it from the project data folder.") from exc
        except pd.errors.EmptyDataError as exc:
            raise CSVStorageError("The data file is empty. Add a valid header and at least one record.") from exc
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError, OSError) as exc:
            raise CSVStorageError("The data file could not be read. Check its header, types, and CSV format.") from exc
        else:
            self._data = cleaned
            return self.data
        finally:
            self._io_in_progress = False

    def save(self, frame: pd.DataFrame) -> pd.DataFrame:
        self._io_in_progress = True
        temp_path = self.path.with_name(f"{self.path.stem}.tmp{self.path.suffix}")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            cleaned = self._clean(frame.reindex(columns=self.COLUMNS))
            cleaned.to_csv(temp_path, index=False, encoding="utf-8")
            # Verify the temporary file can be reloaded before replacing the original.
            reloaded = pd.read_csv(temp_path)
            if list(reloaded.columns) != list(self.COLUMNS):
                raise OSError("Temporary CSV validation failed")
            os.replace(temp_path, self.path)
        except (OSError, PermissionError, pd.errors.ParserError, ValueError) as exc:
            raise CSVStorageError("Unable to save changes safely. Check that the CSV folder is writable.") from exc
        else:
            self._data = cleaned
            return self.data
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    self._temporary_cleanup_failed = True
            self._io_in_progress = False

    def _record(self, record: dict[str, Any]) -> dict[str, Any]:
        missing = [column for column in self.COLUMNS if column not in record or record[column] is None or str(record[column]).strip() == ""]
        if missing:
            raise ValidationError("Complete all required fields.")
        item = {column: record[column] for column in self.COLUMNS}
        item[self.ID_COLUMN] = str(item[self.ID_COLUMN]).strip()
        if not re.fullmatch(self.ID_PATTERN, item[self.ID_COLUMN]):
            raise ValidationError(f"{self.ID_COLUMN} must use the format EMP-001 (uppercase letters, hyphen, digits).")
        for column in self.NUMERIC:
            try:
                value = float(item[column])
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"{column.replace('_', ' ').title()} must be numeric.") from exc
            if not np.isfinite(value):
                raise ValidationError(f"{column.replace('_', ' ').title()} must be a finite number.")
            if column in self.BOUNDS:
                lower, upper = self.BOUNDS[column]
                if value < lower or value > upper:
                    raise ValidationError(f"{column.replace('_', ' ').title()} must be between {lower:g} and {upper:g}.")
            if column in {"experience_yrs", "salary", "duration_hrs", "cost", "avg_salary", "demand"} and value < 0:
                raise ValidationError(f"{column.replace('_', ' ').title()} cannot be negative.")
            item[column] = int(value) if value.is_integer() and column not in {"rating", "min_level", "demand"} else value
        for column in self.CATEGORICAL:
            item[column] = str(item[column]).strip()
        for column in self.DATES:
            try:
                parsed = pd.to_datetime(item[column], errors="raise")
            except (ValueError, TypeError) as exc:
                raise ValidationError(f"{column.replace('_', ' ').title()} must be a valid date.") from exc
            item[column] = parsed.strftime("%Y-%m-%d")
        self.validate_record(item)
        return item

    def validate_record(self, record: dict[str, Any]) -> None:
        """Subclass hook for referential checks and calculated values."""

    def create(self, record: dict[str, Any]) -> pd.DataFrame:
        current = self.load()
        item = self._record(record)
        if current[self.ID_COLUMN].astype(str).eq(item[self.ID_COLUMN]).any():
            raise ValidationError(f"{self.ID_COLUMN} already exists.")
        return self.save(pd.concat([current, pd.DataFrame([item])], ignore_index=True))

    def read(self, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        frame = self.load()
        for column, value in (filters or {}).items():
            if column not in frame.columns or value in (None, "All"):
                continue
            if isinstance(value, tuple) and len(value) == 2:
                series = pd.to_datetime(frame[column], errors="coerce") if column in self.DATES else pd.to_numeric(frame[column], errors="coerce")
                frame = frame.loc[series.between(value[0], value[1])]
            elif column in frame.columns:
                frame = frame.loc[frame[column].astype(str).str.contains(str(value), case=False, na=False)]
        return frame.reset_index(drop=True)

    def update(self, record_id: str, record: dict[str, Any]) -> pd.DataFrame:
        current = self.load()
        record_id = str(record_id).strip()
        if not re.fullmatch(self.ID_PATTERN, record_id):
            raise ValidationError(f"Enter a valid {self.ID_COLUMN}.")
        matches = current[self.ID_COLUMN].astype(str).eq(record_id)
        if not matches.any():
            raise ValidationError(f"No record found for {record_id}.")
        item = self._record(record)
        if item[self.ID_COLUMN] != record_id and current[self.ID_COLUMN].astype(str).eq(item[self.ID_COLUMN]).any():
            raise ValidationError(f"{self.ID_COLUMN} already exists.")
        current.loc[matches, list(self.COLUMNS)] = list(item.values())
        return self.save(current)

    def delete(self, record_id: str) -> pd.DataFrame:
        current = self.load()
        record_id = str(record_id).strip()
        if not re.fullmatch(self.ID_PATTERN, record_id):
            raise ValidationError(f"Enter a valid {self.ID_COLUMN}.")
        matches = current[self.ID_COLUMN].astype(str).eq(record_id)
        if not matches.any():
            raise ValidationError(f"No record found for {record_id}.")
        return self.save(current.loc[~matches].copy())


class EmployeeManager(CSVManager):
    COLUMNS = ("emp_id", "name", "department", "job_role", "experience_yrs", "education_level", "salary")
    ID_COLUMN = "emp_id"
    ID_PATTERN = r"^EMP-\d{3,6}$"
    NUMERIC = ("experience_yrs", "salary")
    CATEGORICAL = ("name", "department", "job_role", "education_level")
    BOUNDS = {"experience_yrs": (0, 60), "salary": (0, 100000000)}

    def statistics(self) -> dict[str, Any]:
        frame = self.load()
        return {"employee_count": len(frame), "average_salary": float(frame["salary"].mean()) if len(frame) else 0.0,
                "average_experience": float(frame["experience_yrs"].mean()) if len(frame) else 0.0,
                "salary_by_department": frame.groupby("department", as_index=False)["salary"].mean(),
                "count_by_job_role": frame.groupby("job_role").size().reset_index(name="employee_count")}


class SkillAssessmentManager(CSVManager):
    COLUMNS = ("assess_id", "emp_id", "skill_name", "current_level", "required_level", "gap", "assessed_date")
    ID_COLUMN = "assess_id"
    ID_PATTERN = r"^ASM-\d{3,6}$"
    NUMERIC = ("current_level", "required_level", "gap")
    CATEGORICAL = ("emp_id", "skill_name")
    DATES = ("assessed_date",)
    BOUNDS = {"current_level": (0, 7), "required_level": (0, 7), "gap": (-7, 7)}

    def __init__(self, file_path: str | Path, employee_path: str | Path | None = None,
                 requirements_path: str | Path | None = None):
        super().__init__(file_path)
        self.employee_path = Path(employee_path) if employee_path else None
        self.requirements_path = Path(requirements_path) if requirements_path else None

    def _record(self, record: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(record)
        if self.employee_path and self.requirements_path:
            employees = self._read_reference_csv(self.employee_path, ["emp_id", "job_role"])
            employee = employees.loc[employees["emp_id"].astype(str).eq(str(enriched.get("emp_id", "")))]
            if employee.empty:
                raise ValidationError("Select an employee ID that exists in employees.csv.")
            role = employee.iloc[0]["job_role"]
            requirements = self._read_reference_csv(self.requirements_path, ["job_role", "skill_name", "min_level"])
            requirement = requirements.loc[
                requirements["job_role"].astype(str).str.casefold().eq(str(role).casefold())
                & requirements["skill_name"].astype(str).str.casefold().eq(str(enriched.get("skill_name", "")).casefold())
            ]
            if requirement.empty:
                raise ValidationError("That employee's job role has no requirement for the selected skill.")
            enriched["required_level"] = float(requirement.iloc[0]["min_level"])
        try:
            enriched["gap"] = float(enriched["required_level"]) - float(enriched["current_level"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("Enter a valid current skill level.") from exc
        item = super()._record(enriched)
        item["gap"] = round(float(item["required_level"]) - float(item["current_level"]), 2)
        return item

    def validate_record(self, record: dict[str, Any]) -> None:
        if self.employee_path:
            employees = self._read_reference_csv(self.employee_path, ["emp_id"])
            if str(record["emp_id"]) not in set(employees["emp_id"].astype(str)):
                raise ValidationError("Select an employee ID that exists in employees.csv.")
        if self.requirements_path:
            requirements = self._read_reference_csv(self.requirements_path, ["job_role", "skill_name"])
            if not requirements["skill_name"].astype(str).str.casefold().eq(str(record["skill_name"]).casefold()).any():
                raise ValidationError("Select a skill that exists in job_requirements.csv.")

    def statistics(self) -> dict[str, Any]:
        frame = self.load()
        return {"assessment_count": len(frame), "average_current": float(frame["current_level"].mean()) if len(frame) else 0.0,
                "average_required": float(frame["required_level"].mean()) if len(frame) else 0.0,
                "average_gap": float(frame["gap"].mean()) if len(frame) else 0.0,
                "gap_by_skill": frame.groupby("skill_name", as_index=False)["gap"].mean().sort_values("gap", ascending=False)}


class JobRequirementManager(CSVManager):
    COLUMNS = ("req_id", "job_role", "industry", "skill_name", "min_level", "demand", "avg_salary")
    ID_COLUMN = "req_id"
    ID_PATTERN = r"^REQ-\d{3,6}$"
    NUMERIC = ("min_level", "demand", "avg_salary")
    CATEGORICAL = ("job_role", "industry", "skill_name")
    BOUNDS = {"min_level": (0, 7), "demand": (0, 100), "avg_salary": (0, 100000000)}

    def statistics(self) -> dict[str, Any]:
        frame = self.load()
        return {"requirement_count": len(frame), "average_salary": float(frame["avg_salary"].mean()) if len(frame) else 0.0,
                "average_demand": float(frame["demand"].mean()) if len(frame) else 0.0,
                "highest_demand_skill": frame.loc[frame["demand"].idxmax(), "skill_name"] if len(frame) else "—",
                "demand_by_skill": frame.groupby("skill_name", as_index=False)["demand"].mean().sort_values("demand", ascending=False),
                "skills_by_industry": frame.groupby("industry", as_index=False)["skill_name"].nunique().rename(columns={"skill_name": "skill_count"})}


class TrainingCourseManager(CSVManager):
    COLUMNS = ("course_id", "course_name", "skill_name", "provider", "duration_hrs", "cost", "rating", "mode")
    ID_COLUMN = "course_id"
    ID_PATTERN = r"^CRS-\d{3,6}$"
    NUMERIC = ("duration_hrs", "cost", "rating")
    CATEGORICAL = ("course_name", "skill_name", "provider", "mode")
    BOUNDS = {"duration_hrs": (0.1, 1000), "cost": (0, 1000000), "rating": (0, 5)}
    MODES = ("Online", "In-person", "Hybrid")

    def validate_record(self, record: dict[str, Any]) -> None:
        if record["mode"] not in self.MODES:
            raise ValidationError("Mode must be Online, In-person, or Hybrid.")

    def statistics(self) -> dict[str, Any]:
        frame = self.load()
        return {"course_count": len(frame), "average_rating": float(frame["rating"].mean()) if len(frame) else 0.0,
                "average_cost": float(frame["cost"].mean()) if len(frame) else 0.0,
                "average_duration": float(frame["duration_hrs"].mean()) if len(frame) else 0.0,
                "count_by_mode": frame.groupby("mode").size().reset_index(name="course_count")}
