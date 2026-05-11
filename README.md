# DSAI Module 1 Individual Prototype: Career Coach Job Market Navigator

This is a small individual prototype built alongside the Module 1 group project.

The goal is to demonstrate an end-to-end data workflow using Singapore job postings data:

1. Define a simple business problem
2. Design a simple ERD
3. Create a database
4. Query the database using Python
5. Generate simple insights
6. Build a simple dashboard

## Target User

Career coaches supporting jobseekers, fresh graduates, and mid-career switchers in Singapore.

## Problem Statement

Career coaches need a quick way to guide jobseekers using evidence from the labour market, but raw job postings are noisy and difficult to interpret quickly.

Identify potential talent shortage areas by comparing job demand, applicant interest, and salary attractiveness.


## Prototype Objective/Usecases

    This project helps career coaches compare job categories by:

- market demand
- salary range
- experience requirements
- opportunity score
- talent shortage signals

This prototype also includes a talent shortage signal analysis. It compares job postings and vacancies against applications and views to identify categories where hiring demand may be high but applicant interest appears weaker.

## Tech Stack

- Python
- pandas
- DuckDB
- SQL
- matplotlib
- Streamlit
- VSCode
- WSL Ubuntu
- Git / GitHub

## Project Structure

ntu-sctp/data/   The full raw CSV is stored locally outside the repo at ~/code/ntu-sctp/data/SGJobData.csv. 
data/processed/  Cleaned or exported data files  
db/              Local DuckDB database files  
notebooks/       Jupyter notebooks for EDA and analysis  
src/             Reusable Python scripts  
dashboard/       Streamlit dashboard app  
docs/            Problem statement, ERD, and notes  
outputs/         Charts, screenshots, and other outputs  

Raw data files and local database files are not committed to GitHub.


## Assumptions - Relationship between category and job category tables
- For ERD
A job can have many categories.
A category can have many jobs.
But the same exact job-category pair should not repeat.

category is the master list of job categories, job_category is the linking table that says which job belongs to which category.
job_posting = the job
category = the category label
job_category = which category labels belong to which job


Example: One job with multiple categories
Job ID: JOB002
Title: Data Analyst
Categories:
- Information Technology
- Banking and Finance
- Consulting

Then category stores the category names once:
category_id	category_name
21	Information Technology
3	Banking and Finance
9	Consulting

Then job_category stores the relationship:
job_post_id	category_id
JOB002	21
JOB002	3
JOB002	9

That means:
JOB002 belongs to Information Technology
JOB002 belongs to Banking and Finance
JOB002 belongs to Consulting

Why not just put category_name inside job_posting?
Because one job can have more than one category.
Bad design:
job_post_id	title	categories
JOB002	Data Analyst	Information Technology, Banking and Finance, Consulting

That puts many values inside one cell. Databases hate that. It breaks the “one value per cell” idea.

Cleaner design:

job_posting:
job_post_id	title
JOB002	Data Analyst

category:
category_id	category_name
21	Information Technology
3	Banking and Finance
9	Consulting

job_category:
job_post_id	category_id
JOB002	21
JOB002	3
JOB002	9

That is cleaner because each relationship gets its own row.

## Assumptions - Table View
vw_career_coach_jobs:
many rows, one row per job-category relationship

vw_talent_shortage_categories:
one row per category


## Notes - Others 
One job ad can have multiple openings.
Did not remove 
1. $1 salary records
2. salary outliers
3. low salary placeholders
4. missing salary job records
5. missing application/view job records

Removed
1. unreadable CSV rows may be skipped by DuckDB due to ignore_errors=True
2. blank company/employment/position values from lookup tables
3. clean job_posting rows without metadata_jobPostId
4. missing/unreadable category values from category processing
5. duplicate category master records
6. duplicate job-category links
7. missing category rows from category-level views