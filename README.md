# Workforce Skill Gap and Training Recommendation

A CSV-backed Streamlit application for connecting a sample workforce to occupational skill requirements, identifying skill gaps, and surfacing relevant training options. It is designed for a college term-project walkthrough; the included data is a small teaching sample and is not a live workforce report.

## Problem statement

Organizations need a practical way to compare current employee capabilities with the skills expected in their roles, then turn the largest gaps into learning actions. This project joins employee records, skill assessments, occupational requirements, and course references so users can explore the relationships, update the source data through CRUD pages, and review transparent rule-based recommendations.

## Sustainable Development Goals

- **SDG 8 – Decent Work and Economic Growth:** supports workforce development by helping organizations see capability needs and plan relevant upskilling.
- **SDG 4 – Quality Education:** supports accessible, targeted learning pathways by connecting skill needs with course references.

These are project aims, not measured impact claims.

## Features

- Four CSV-backed data areas with create, read, update, and delete operations.
- Atomic CSV writes through a temporary file followed by replacement.
- Shared object-oriented `CSVManager` base class and specialized managers.
- A `DataCleaner` that normalizes whitespace and mapped role spelling, removes duplicates, converts types, applies missing-value rules, and drops out-of-range records.
- Search, filters, sorting, group summaries, and current-data Plotly charts on each page.
- Filtered CSV downloads and timestamped TXT summary reports.
- A home dashboard that joins all four datasets and provides read-only, rule-based training recommendations.
- Friendly validation and file-operation messages instead of showing raw Python tracebacks.

## Dataset sources and transformations

Access date for the source pages below: **2026-10-20**.

### `employees.csv` — 30 rows

- **Dataset:** IBM HR Analytics Employee Attrition & Performance, a fictional/sample HR dataset.
- **Source:** [Kaggle dataset listing](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset); the sample rows were cross-checked against a [public CSV mirror](https://raw.githubusercontent.com/trishabhardwaj-analyst/IBM-HR-Analytics-Employee-Attrition/main/WA_Fn-UseC_-HR-Employee-Attrition.csv). A [metadata mirror](https://portal.mardi4nfdi.de/wiki/Ibm-employee-attrition) records the Open Database License (ODbL) and Database Contents License (DbCL) for this dataset. Review the current source record's terms before further redistribution.
- **How it was transformed:** the first 30 rows of the public sample were reduced to department, source job role, education ordinal, monthly income, and total working years. `emp_id` values (`EMP-001` onward) and anonymous names (`Employee_001` onward) were generated; no personal names were present or fabricated. IBM role titles were mapped to the closest selected O*NET occupation labels and the mapping is visible in `workforce_skill_gap` page choices and this data dictionary below. `education_level` maps the source ordinal to readable categories. `salary` is monthly income multiplied by 12; it has no currency label because the source field is unlabelled.
- **Cleaning:** whitespace and role spellings are normalized; numeric fields are coerced and range checked; duplicate IDs and rows are removed.

### `job_requirements.csv` — 35 rows

- **Dataset:** selected occupation and skill ratings derived from the [O*NET 31.0 Database](https://www.onetcenter.org/database.html) and [O*NET OnLine occupation pages](https://www.onetonline.org/).
- **License:** O*NET 31.0 database content is generally available under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), subject to the exceptions listed by O*NET. Required attribution: “This project includes information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. Changes were made to role mappings, scale conversions, and row structure. O*NET® is a trademark of USDOL/ETA.” See the [official database license terms](https://www.onetcenter.org/license_db.html).
- **How it was transformed:** seven IBM job-role groups were mapped to O*NET occupations: Laboratory Technician → Biological Technicians (19-4021.00); Manager → General and Operations Managers (11-1021.00); Research Scientist → Medical Scientists, Except Epidemiologists (19-1042.00); Manufacturing Director → Industrial Production Managers (11-3051.00); Healthcare Representative and Sales Representative → Sales Representatives, Wholesale and Manufacturing, Technical and Scientific Products (41-4011.00); Sales Executive → Sales Managers (11-2022.00); Human Resources → Human Resources Specialists (13-1071.00). These are approximate role mappings for demonstration, not equivalencies asserted by O*NET.
- Five skills are included for each mapped occupation: Active Listening, Critical Thinking, Reading Comprehension, Speaking, and Active Learning. `demand` is the O*NET standardized Importance value (0–100). `min_level` converts the standardized O*NET Level value from 0–100 to the project's 0–7 range by multiplying by 7/100. `industry` is a broad project category assigned to each role. `avg_salary` is the mean annualized income of sample employees mapped to that role, not an O*NET wage estimate.
- **Cleaning:** standard role names are normalized; numeric values are coerced and checked against the stated scale ranges; duplicate IDs are removed.

### `skill_assessments.csv` — 70 rows

- **Dataset:** project-generated demonstration assessments. O*NET role requirements in `job_requirements.csv` provide each assessment's required level.
- **Source / usage:** no external assessment dataset is copied. The employee IDs and skill labels link to the employee and requirement files.
- **How it was transformed:** synthetic current levels and sample dates were created for demonstration. `required_level` is copied from the employee's mapped job-role and skill requirement; `gap` is calculated as `required_level - current_level`. These levels are teaching examples, not observed employee performance or a validated assessment instrument. The UI calculates `required_level` and `gap` when creating or updating records to prevent manual mismatch.
- **Cleaning:** levels and dates are type converted and validated; duplicate IDs and rows are removed; invalid dates remain `NaT` if encountered in imported data.

### `training_courses.csv` — 30 rows

- **Dataset:** a curated set of course-title references from public [Coursera course listings](https://www.coursera.org/), mapped by project staff to the five project skill labels. Example listings: [Active Listening: Enhancing Communication Skills](https://www.coursera.org/learn/active-listening-enhancing-communication-skills), [Critical Thinking Skills for University Success](https://www.coursera.org/learn/critical-thinking-skills), [Introduction to Critical Reading & Research Writing](https://www.coursera.org/learn/critical-reading--research-writing), [Learning How to Learn](https://www.coursera.org/learn/learning-how-to-learn), and [Introduction to Public Speaking](https://www.coursera.org/learn/public-speaking). The same-title references appearing under more than one skill are mapped separately by project staff.
- **License / usage:** the course names are short references to third-party listings; course content is not copied. Coursera listing content is not presented as openly licensed. Listing availability, cost, ratings, and provider policies can change; links are provided for reference.
- **How it was transformed:** the 30 course titles are matched to relevant skill labels by project staff. Course IDs are generated. **Duration, cost, rating, and mode in the CSV are generated demonstration estimates, not current Coursera metadata or provider claims.** They exist only to demonstrate ranking and chart functionality.
- **Cleaning:** numeric fields are coerced and validated; mode values are checked; duplicate IDs and rows are removed.

### Role mapping and relation keys

The application connects `employees.emp_id` to `skill_assessments.emp_id`; connects an employee's `job_role` and `skill_name` to `job_requirements`; then connects `skill_name` to `training_courses`. The role mapping and course-to-skill labels are project choices documented above. In the skill assessment page, the required value is looked up from the employee's role and the selected skill.

## Missing-value strategy

- Numeric columns use median imputation when at least one valid number exists; if the entire column is missing or invalid, the cleaner fills it with `0` so the data remains usable and the assumption is explicit.
- Missing categorical values become `Unknown`.
- Invalid or missing dates become `NaT` and are not guessed. The Home page's data-quality expander describes this policy.
- CRUD forms reject missing required fields, invalid IDs, invalid numeric values, and values outside the allowed ranges.
- Loading an imported CSV drops records outside declared numeric ranges and deduplicates IDs; it does not silently claim those rows are valid.

## Installation and launch

Python 3.10 or newer is required.

```bash
python -m venv venv
```

Activate the environment on Windows:

```powershell
venv\Scripts\Activate.ps1
```

If PowerShell blocks local activation, use Command Prompt instead:

```bat
venv\Scripts\activate.bat
```

Install dependencies and launch from this folder:

```bash
pip install -r requirements.txt
streamlit run Home.py
```

`app.py` is an optional short entry page; `Home.py` is the recommended launch target because it contains the full dashboard.

## Project structure

```text
workforce_skill_gap/
├── app.py                         Optional launch page
├── Home.py                        Dashboard, joins, filters, and recommendations
├── requirements.txt               Runtime dependencies
├── README.md                       Project and data documentation
├── data/
│   ├── employees.csv               30 anonymous sample employees
│   ├── skill_assessments.csv       70 synthetic teaching assessments
│   ├── job_requirements.csv        35 O*NET-derived role/skill requirements
│   └── training_courses.csv        30 course references and estimated demo fields
├── pages/
│   ├── 1_Employees.py              Employee CRUD, analysis, charts, and reports
│   ├── 2_Skill_Assessments.py      Assessment CRUD, analysis, charts, and reports
│   ├── 3_Job_Requirements.py       Requirement CRUD, analysis, charts, and reports
│   └── 4_Training_Courses.py       Course CRUD, analysis, charts, and reports
└── utils/
    ├── __init__.py                 Shared helper package
    ├── charting.py                 Friendly Plotly dependency handling
    ├── csv_manager.py              Safe CSV persistence, validation, and OOP managers
    ├── data_cleaner.py             Shared type, missing-data, and duplicate handling
    └── page_components.py          Shared CRUD UI, cache refresh, and report helpers
```

All data paths are resolved relative to the project files. No database is used; CSV files are the persistent storage.

## Team responsibilities

- **Kusuma** → `employees.csv` and the employee CRUD page.
- **Jahnavi** → `skill_assessments.csv` and the skill assessment CRUD page.
- **Sahithi** → `job_requirements.csv` and the job requirement CRUD page.
- **Shanmuktha** → `training_courses.csv` and the training course CRUD page.

Each member should understand their data schema, validation rules, CRUD methods, and analysis shown on their page.

## Recommendation logic

The Home page calculates average gap by skill in the active filter view, keeps skills with a positive average gap, and joins them to courses with the same skill label. Its transparent score weights normalized gap relevance at 50%, course rating at 25%, lower estimated cost at 15%, and shorter estimated duration at 10%. Recommendations are read-only and rule-based; no machine-learning model is claimed.

## Notes for demonstrations

- CSV records are editable from the pages. Writes use a temporary CSV, validate that it can be reloaded, and then replace the current file.
- Create, update, and delete operations clear Streamlit's cached data and rerun the page so changes appear immediately.
- Take a copy of the four CSV files before a live demonstration if you want to restore the original teaching sample afterward.
- O*NET demand values use standardized Importance scores, not a forecast of local labor-market demand. The salary values in requirements are derived only from the small IBM sample.
