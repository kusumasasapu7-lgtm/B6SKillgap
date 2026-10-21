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

### Role mapping and relation keys

The application connects `employees.emp_id` to `skill_assessments.emp_id`; connects an employee's `job_role` and `skill_name` to `job_requirements`; then connects `skill_name` to `training_courses`. The role mapping and course-to-skill labels are project choices documented above. In the skill assessment page, the required value is looked up from the employee's role and the selected skill.

## Project structure

workforce_skill_gap/
├── app.py                         
├── Home.py                        
├── requirements.txt               
├── README.md                       
├── data/
│   ├── employees.csv               
│   ├── skill_assessments.csv       
│   ├── job_requirements.csv       
│   └── training_courses.csv
├── pages/
│   ├── 1_Employees.py              
│   ├── 2_Skill_Assessments.py     
│   ├── 3_Job_Requirements.py
│   └── 4_Training_Courses.py       
└── utils/
    ├── __init__.py                 
    ├── charting.py                
    ├── csv_manager.py            
    ├── data_cleaner.py           
    └── page_components.py        
```

All data paths are resolved relative to the project files. No database is used; CSV files are the persistent storage.

## Team responsibilities

- **Kusuma** → `employees.csv` and the employee CRUD page.
- **Jahnavi** → `skill_assessments.csv` and the skill assessment CRUD page.
- **Sahithi** → `job_requirements.csv` and the job requirement CRUD page.
- **Shanmuktha** → `training_courses.csv` and the training course CRUD page.
