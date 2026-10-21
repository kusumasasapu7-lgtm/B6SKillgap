"""Shared, real CRUD form and report components for the four data pages."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

import pandas as pd
import streamlit as st

from .csv_manager import CSVManager, CSVStorageError, ValidationError


FieldSpec = dict[str, Any]


def _field_input(field: FieldSpec, current: dict[str, Any], key: str) -> Any:
    name = field["name"]
    label = field.get("label", name.replace("_", " ").title())
    value = current.get(name, field.get("default", ""))
    kind = field.get("type", "text")
    if kind == "select":
        choices = field.get("options", [])
        if callable(choices):
            choices = choices()
        choices = list(dict.fromkeys(choices))
        if value not in choices and choices:
            choices.insert(0, value)
        return st.selectbox(label, choices, key=key) if choices else st.text_input(label, str(value), key=key)
    if kind == "number":
        raw_value = value if value is not None and not (isinstance(value, str) and not value.strip()) else field.get("default", 0)
        minimum = float(field.get("min", 0.0))
        maximum = float(field.get("max", 100000000.0))
        return st.number_input(label, min_value=minimum, max_value=maximum,
                               value=float(raw_value), step=float(field.get("step", 1.0)), key=key)
    if kind == "date":
        try:
            initial = pd.to_datetime(value).date() if value else date.today()
        except (ValueError, TypeError):
            initial = date.today()
        return st.date_input(label, value=initial, key=key)
    return st.text_input(label, str(value or ""), key=key)


def _edit_form(manager: CSVManager, fields: list[FieldSpec], current: dict[str, Any], key: str,
               submit_label: str) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    with st.form(f"{key}_form"):
        columns = st.columns(2)
        for index, field in enumerate(fields):
            with columns[index % 2]:
                result[field["name"]] = _field_input(field, current, f"{key}_{field['name']}")
        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
    return result if submitted else None


def _friendly_error(error: Exception) -> None:
    if isinstance(error, ValidationError):
        st.warning(str(error))
    elif isinstance(error, CSVStorageError):
        st.error(str(error))
    else:
        st.error("That action could not be completed. Check the values and CSV files, then try again.")


def _invalidate() -> None:
    st.cache_data.clear()
    st.session_state["data_refresh_token"] = st.session_state.get("data_refresh_token", 0) + 1


def render_crud_page(*, title: str, subtitle: str, manager: CSVManager, fields: list[FieldSpec],
                     filter_func: Callable[[pd.DataFrame, str], tuple[pd.DataFrame, dict[str, Any]]],
                     chart_func: Callable[[pd.DataFrame], None], stats_func: Callable[[pd.DataFrame], None],
                     export_summary: Callable[[pd.DataFrame, dict[str, Any]], str]) -> None:
    st.title(title)
    st.caption(subtitle)
    flash_message = st.session_state.pop("_crud_flash_message", None)
    if flash_message:
        st.success(flash_message)
    tabs = st.tabs(["Create", "Read", "Update", "Delete", "Charts", "Export"])
    try:
        data = manager.load()
    except Exception as exc:
        _friendly_error(exc)
        st.info("Restore the supplied CSV file in the project data folder to continue.")
        return

    with tabs[0]:
        st.subheader("Add a record")
        submitted_record = _edit_form(manager, fields, {}, "create", "Create record")
        if submitted_record is not None:
            try:
                manager.create(submitted_record)
                _invalidate()
                st.session_state["_crud_flash_message"] = "Record created and saved safely."
                st.rerun()
            except Exception as exc:
                _friendly_error(exc)

    with tabs[1]:
        st.subheader("Current records")
        view, applied = filter_func(data.copy(), "read")
        stats_func(view)
        sort_col = st.selectbox("Sort by", list(view.columns), key="read_sort_column") if len(view.columns) else None
        if sort_col:
            descending = st.toggle("Descending", value=False, key="read_sort_desc")
            view = view.sort_values(sort_col, ascending=not descending, kind="stable")
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(view):,} of {len(data):,} records")

    with tabs[2]:
        st.subheader("Update a record")
        ids = data[manager.ID_COLUMN].astype(str).tolist()
        selected_id = st.selectbox("Select record ID", ids, key="update_id") if ids else None
        if selected_id:
            current = data.loc[data[manager.ID_COLUMN].astype(str).eq(selected_id)].iloc[0].to_dict()
            updated_record = _edit_form(manager, fields, current, "update", "Save update")
            if updated_record is not None:
                try:
                    manager.update(selected_id, updated_record)
                    _invalidate()
                    st.session_state["_crud_flash_message"] = "Record updated and saved safely."
                    st.rerun()
                except Exception as exc:
                    _friendly_error(exc)
        else:
            st.info("There are no records to update.")

    with tabs[3]:
        st.subheader("Delete a record")
        ids = data[manager.ID_COLUMN].astype(str).tolist()
        selected_id = st.selectbox("Select record ID to delete", ids, key="delete_id") if ids else None
        if selected_id:
            selected = data.loc[data[manager.ID_COLUMN].astype(str).eq(selected_id)]
            st.dataframe(selected, use_container_width=True, hide_index=True)
            confirm = st.checkbox(f"Yes, delete this {manager.ID_COLUMN}", key=f"delete_confirm_{selected_id}")
            if st.button("Delete selected record", type="secondary", disabled=not confirm, key="delete_button"):
                try:
                    manager.delete(selected_id)
                    _invalidate()
                    st.session_state["_crud_flash_message"] = "Record deleted."
                    st.rerun()
                except Exception as exc:
                    _friendly_error(exc)
        else:
            st.info("There are no records to delete.")

    with tabs[4]:
        st.subheader("Live analysis")
        view, _ = filter_func(data.copy(), "charts")
        chart_func(view)

    with tabs[5]:
        st.subheader("Download a filtered report")
        view, applied = filter_func(data.copy(), "export")
        st.caption(f"Report includes {len(view):,} rows")
        st.json(applied)
        summary_text = export_summary(view, applied)
        st.download_button("Download summary as TXT", summary_text, file_name="workforce_report.txt",
                           mime="text/plain", use_container_width=True)
        st.download_button("Download filtered rows as CSV", view.to_csv(index=False),
                           file_name="filtered_records.csv", mime="text/csv", use_container_width=True)


def make_report(page_name: str, frame: pd.DataFrame, filters: dict[str, Any], metrics: dict[str, Any]) -> str:
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [f"{page_name} summary", f"Generated: {stamp}", f"Row count: {len(frame)}", "Applied filters:"]
    lines.extend([f"  {key}: {value}" for key, value in filters.items()] or ["  None"])
    lines.append("Summary statistics:")
    lines.extend([f"  {key}: {value}" for key, value in metrics.items()])
    return "\n".join(lines)

