from pathlib import Path
import ast
import json
import duckdb
import pandas as pd



# This finds the main project folder.
# Example:
# /home/kennywong/code/ntu-sctp/repos/dsai-module1-individual-project
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# This points to the big CSV file.
# The CSV is stored outside the Git repo because it is too large for GitHub.
CSV_PATH = PROJECT_ROOT / "../../data/SGJobData.csv"

# This is where we will create the DuckDB database file.
DB_PATH = PROJECT_ROOT / "db/jobs.duckdb"


# mini cleaning script
# Convert the raw categories text into a list of category dictionaries.
# Example input:
# [{"id": 21, "category": "Information Technology"}]
# Example output:
# [{"category_id": 21, "category_name": "Information Technology"}]

def parse_categories(value):  
    # If the value is missing, return an empty list.
    if pd.isna(value):
         return[]
    
    # Convert the value to text and remove extra spaces.
    text = str(value).strip()

    # If the text is blank or an empty list, return an empty list.
    if text == "" or text == "[]":
        return []

    # Try to read the text as JSON.
    try:
        data = json.loads(text)

    # If JSON reading fails, try a backup method.
    except json.JSONDecodeError:
        try:
            data = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return []
        
    # If the data is one dictionary, wrap it inside a list.
    if isinstance(data, dict):
        data = [data]

    # If the data is not a list, ignore it.
    if not isinstance(data, list):
        return []

    cleaned_categories = []

    # Loop through each category item.
    for item in data:
        if not isinstance(item, dict):
            continue

        category_id = item.get("id")
        category_name = item.get("category")

        if category_id is None or category_name is None:
            continue

        cleaned_categories.append(
            {
                "category_id": int(category_id),
                "category_name": str(category_name).strip(),
            }
        )

    return cleaned_categories



#start of the main job of the script
def main():
    # Check that Python knows where the project root folder is.
    print("Project Root:", PROJECT_ROOT)

    # Check where the CSV file should be.
    print("\nCSV path:", CSV_PATH)

    # Check where the database file will be created.
    print("\nDatabase path:", DB_PATH)

    # Safety check: stop the script if the CSV file cannot be found
    # This prevents us running 200 lines of database code only to discover the CSV path was wrong.
    if not CSV_PATH.exists():
          raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")
    print("\nCSV file found")

    # Make sure the db folder exists before creating the DuckDB file
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("\nDatabase folder is ready")



    # Connect to DuckDB
    # if jobs.duckdb does not exist yet, DuckDB will create it
    con = duckdb.connect(str(DB_PATH))
    print("\nConnected to DuckDB")

    # Convert the CSV path into a string for SQL
    csv_path_text = str(CSV_PATH)

    # Create a raw table from the CSV file
    # jobs_raw is the original CSV loaded into DuckDB
    # Send a SQL command to DuckDB.
    con.execute(   
        f"""
        CREATE OR REPLACE TABLE jobs_raw AS
        SELECT *
        FROM read_csv_auto('{csv_path_text}', header=True, all_varchar=True, ignore_errors=True);  
        """
    )
    
    print("\nSuccessfully loaded CSV into jobs_raw")
    print("Tables currently in DuckDB:")
    print(con.execute("SHOW TABLES").fetchall())


    # Sanity checks
    # Count number of rows inside jobs_raw.
    row_count = con.execute("SELECT COUNT(*) FROM jobs_raw").fetchone()[0]
    print(f"jobs_raw row count: {row_count:,}")

    # Show the columns inside jobs_raw.
    columns_df = con.execute("DESCRIBE jobs_raw").df()
    print("\nColumns in jobs_raw:")
    print(columns_df[["column_name", "column_type"]].to_string(index=False))



    # Create company lookup table.
    # This stores each unique company name once.
    con.execute(
        """
        CREATE OR REPLACE TABLE company AS
        SELECT 
        row_number() OVER (ORDER BY company_name) AS company_id,
        company_name
        FROM
        (
            SELECT DISTINCT
            NULLIF(TRIM(postedCompany_name),'') AS company_name
            
            FROM 
            jobs_raw
        )
        WHERE company_name IS NOT NULL;
        """
    )

    #create company row count, number of companies
    print("\nCreated company table")
    company_count = con.execute("SELECT COUNT(*) FROM company").fetchone()[0]
    print(f"company row count: {company_count:,}")



    # Create employment_type lookup table.
    # This stores each unique employment type once.
    con.execute(
        """
        CREATE OR REPLACE TABLE employment_type AS
        SELECT
            row_number() OVER (ORDER BY employment_type_name) AS employment_type_id,
            employment_type_name
        FROM 
        (
            SELECT DISTINCT
            NULLIF(TRIM(employmentTypes), '') AS employment_type_name
            
            FROM 
            jobs_raw
        )
        WHERE employment_type_name IS NOT NULL;
        """
    )


    #create employment type row count, number of employment types
    print("\nCreated employment_type table")
    employment_type_count = con.execute("SELECT COUNT(*) FROM employment_type").fetchone()[0]
    print(f"employment_type row count: {employment_type_count:,}")



    # Create position_level lookup table.
    # This stores each unique position level once.
    con.execute(
        """
        CREATE OR REPLACE TABLE position_level AS
        SELECT
            row_number() OVER (ORDER BY position_level_name) AS position_level_id, position_level_name
        FROM
        (
            SELECT DISTINCT
                NULLIF(TRIM(positionLevels), '') AS position_level_name
            FROM jobs_raw
        )    
        WHERE position_level_name IS NOT NULL
        """
    )

    #create position level row count, number of position level types
    print("\nCreated position_level position table")
    position_level_count = con.execute("SELECT COUNT(*) FROM position_level").fetchone()[0]
    print(f"position_level row count: {position_level_count:,}")



    # Create main job_posting table.
    # This table stores the main job posting details.
    con.execute(
        """
        CREATE OR REPLACE TABLE job_posting AS
        SELECT
            r.metadata_jobPostId AS job_post_id,
            r.title AS title,

            c.company_id,
            et.employment_type_id,
            pl.position_level_id,

            TRY_CAST(NULLIF(r.minimumYearsExperience, '') AS INTEGER) AS minimum_years_experience,
            TRY_CAST(NULLIF(r.numberOfVacancies, '') AS INTEGER) AS number_of_vacancies,

            TRY_CAST(NULLIF(r.salary_minimum, '') AS DECIMAL(12, 2)) AS salary_minimum,
            TRY_CAST(NULLIF(r.salary_maximum, '') AS DECIMAL(12, 2)) AS salary_maximum,
            TRY_CAST(NULLIF(r.average_salary, '') AS DECIMAL(12, 2)) AS average_salary,

            TRY_CAST(NULLIF(r.metadata_totalNumberJobApplication, '') AS INTEGER) AS total_applications,
            TRY_CAST(NULLIF(r.metadata_totalNumberOfView, '') AS INTEGER) AS total_views,

            COALESCE
            (
                TRY_CAST(r.metadata_newPostingDate AS DATE),
                TRY_STRPTIME(r.metadata_newPostingDate, '%d/%m/%Y')::DATE
            ) AS new_posting_date,

            COALESCE(

                TRY_CAST(r.metadata_originalPostingDate AS DATE),
                TRY_STRPTIME(r.metadata_originalPostingDate, '%d/%m/%Y')::DATE
            ) AS original_posting_date,

            COALESCE
            (
                TRY_CAST(r.metadata_expiryDate AS DATE),
                TRY_STRPTIME(r.metadata_expiryDate, '%d/%m/%Y')::DATE
            ) AS expiry_date

        FROM jobs_raw r

        LEFT JOIN company c
            ON NULLIF(TRIM(r.postedCompany_name), '') = c.company_name

        LEFT JOIN employment_type et
            ON NULLIF(TRIM(r.employmentTypes), '') = et.employment_type_name

        LEFT JOIN position_level pl
            ON NULLIF(TRIM(r.positionLevels), '') = pl.position_level_name

        WHERE r.metadata_jobPostId IS NOT NULL;
        """
    )

    print("\nCreated job_posting table")
    job_posting_count = con.execute("SELECT COUNT(*) FROM job_posting").fetchone()[0]
    print(f"job_posting row count: {job_posting_count:,}")



    # Pull job ID and raw categories into pandas so Python can split the category text.
    category_source = con.execute(
        """
        SELECT
            metadata_jobPostId AS job_post_id,
            categories
        FROM jobs_raw
        WHERE metadata_jobPostId IS NOT NULL AND categories IS NOT NULL;
        """
    ).df()

    category_records = []
    job_category_records = []

    # Loop through every job posting and split its categories.
    for _, row in category_source.iterrows():
        job_post_id = row["job_post_id"]
        categories = parse_categories(row["categories"])

        for category_order, category in enumerate(categories, start=1):
            category_records.append(category)

            job_category_records.append(
                {
                    "job_post_id": job_post_id,
                    "category_id": category["category_id"],
                    "category_order": category_order,
                }
            )

    # Convert Python lists into pandas DataFrames.
    category_df = pd.DataFrame(category_records)
    job_category_df = pd.DataFrame(job_category_records)

    # Remove duplicate category records.
    category_df = (
        category_df
        .drop_duplicates(subset=["category_id"])
        .sort_values("category_id")
        .reset_index(drop=True)
    )

    # Remove duplicate job-category links.
    job_category_df = (
        job_category_df
        .drop_duplicates(subset=["job_post_id", "category_id"])
        .reset_index(drop=True)
    )

    # Register pandas DataFrames so DuckDB can read them.
    con.register("category_df", category_df)
    con.register("job_category_df", job_category_df)

    # Create category table.
    con.execute(
        """
        CREATE OR REPLACE TABLE category AS
        SELECT
            category_id::INTEGER AS category_id,
            category_name::VARCHAR AS category_name
        FROM category_df;
        """
    )

    print("\nCreated category table")
    category_count = con.execute("SELECT COUNT(*) FROM category").fetchone()[0]
    print(f"category row count: {category_count:,}")



    # Create job_category bridge table.
    con.execute(
        """
        CREATE OR REPLACE TABLE job_category AS
        SELECT
            job_post_id::VARCHAR AS job_post_id,
            category_id::INTEGER AS category_id,
            category_order::INTEGER AS category_order
        FROM job_category_df;
        """
    )

    print("\nCreated job_category table")
    job_category_count = con.execute("SELECT COUNT(*) FROM job_category").fetchone()[0]
    print(f"job_category row count: {job_category_count:,}")



    # Create dashboard-ready view.
    # This joins the clean tables into one easy table for analysis.
    con.execute(
        """
        CREATE OR REPLACE VIEW vw_career_coach_jobs AS
        SELECT
            job_posting.job_post_id,
            job_posting.title,
            company.company_name,
            employment_type.employment_type_name,
            position_level.position_level_name,
            category.category_id,
            category.category_name,

            job_posting.minimum_years_experience,
            job_posting.number_of_vacancies,
            job_posting.salary_minimum,
            job_posting.salary_maximum,
            job_posting.average_salary,
            job_posting.total_applications,
            job_posting.total_views,
            job_posting.new_posting_date,
            job_posting.original_posting_date,
            job_posting.expiry_date

        FROM job_posting

        LEFT JOIN company
            ON job_posting.company_id = company.company_id

        LEFT JOIN employment_type
            ON job_posting.employment_type_id = employment_type.employment_type_id

        LEFT JOIN position_level
            ON job_posting.position_level_id = position_level.position_level_id

        LEFT JOIN job_category
            ON job_posting.job_post_id = job_category.job_post_id

        LEFT JOIN category
            ON job_category.category_id = category.category_id;
        """
    )

    print("\nCreated vw_career_coach_jobs view")
    view_count = con.execute("SELECT COUNT(*) FROM vw_career_coach_jobs").fetchone()[0]
    print(f"vw_career_coach_jobs row count: {view_count:,}")



    # close the connection when done
    con.close()
    print("\nDatabase connection closed")

# if I run this file directly, run main().
# python src/create_database.py will run main()
if __name__ == "__main__":
    main()