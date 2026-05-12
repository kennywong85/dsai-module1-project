from pathlib import Path
import ast
import json
import duckdb
import pandas as pd



# This finds the main project folder, no matter where I run this script from
# Example:
# /home/kennywong/code/ntu-sctp/repos/dsai-module1-individual-project
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# This points to the big CSV file. go uop twice into the data folder outisde of the project folder
# The CSV is stored outside the Git repo because it is too large for GitHub.
# Teammates should place the CSV inside:
# data/raw/SGJobData.csv
CSV_PATH = (PROJECT_ROOT / "data" / "raw" / "SGJobData.csv").resolve()

# Decide where database file goes
# This is where we will create the DuckDB database file.
# This file is local and should not be committed to GitHub.
DB_PATH = (PROJECT_ROOT / "db" / "jobs.duckdb").resolve()


# mini cleaning script
# This function takes the messy categories cell and turns it into a clean list of categories.
# Convert the raw categories text into a list of category dictionaries.
# Example input:
# [{"id": 21, "category": "Information Technology"}]
# Example output:
# [{"category_id": 21, "category_name": "Information Technology"}]


#If the category cell is missing, return nothing.
#If the category cell is blank, return nothing.
#Try to read the category text as structured data.
#If it is one category, turn it into a list.
#If it is not a list, ignore it.
#For each category:
#    check that it has an ID and name
#    clean the ID and name
#    save it
#Return the clean list.


def parse_categories(value):  
    # If the value is missing, return an empty list.
    if pd.isna(value):
         return[]
    
    # Convert the value to text and remove extra spaces.
    text = str(value).strip()

    # If the text is blank or an empty list, return an empty list.
    if text == "" or text == "[]":
        return []

    # Try to read the text as JSON. read data
    try:
        data = json.loads(text)

    # If JSON reading fails, try a backup method.
    # use ast
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

    # Loop through each category item using data
    for item in data:
        #skip anything that isnt a dictonary
        if not isinstance(item, dict):
            continue

        category_id = item.get("id")
        category_name = item.get("category")

        #skip incomplete records
        if category_id is None or category_name is None:
            continue

        #add cleaned category record
        cleaned_categories.append(
            {
                "category_id": int(category_id),
                "category_name": str(category_name).strip(),
            }
        )

    #gives the final cleaned category list back to whoever called the function
    return cleaned_categories



# start of the main job of the script - main()
# check CSV exists
# create/open database
# load CSV into jobs_raw
# create clean tables
# create view
# close database

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
        raise FileNotFoundError(
        f"""
            CSV file not found.

            Expected file location:
            {CSV_PATH}

            Please place the raw CSV file here:
            data/raw/SGJobData.csv

            Then run:
            python src/create_database.py
        """
    )

    print("\nCSV file found")

    # Make sure the db folder exists before creating the DuckDB file
    # This is where we will create the DuckDB database file.
    print("\nDatabase folder is ready")



    # Connect to DuckDB
    # if jobs.duckdb does not exist yet, DuckDB will create it
    con = duckdb.connect(str(DB_PATH))
    print("\nConnected to DuckDB")

    # Convert the CSV path into a string for SQL
    csv_path_text = str(CSV_PATH)



    # Create a raw table from the CSV file
    # jobs_raw is the original CSV loaded into DuckDB
    # Python sends SQL command to DuckDB.
    # Create a table called jobs_raw. If it already exists, replace it
    # read_csv_auto tries to understand the CSV automatically
    # Step 1: Load everything as text into jobs_raw
    # Step 2: Later, convert selected columns into numbers/dates
    # The f"..." is an f-string. It lets you insert variables into text.
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
    # The f"..." is an f-string. It lets you insert variables into text.
    # The [0] takes the first item from the tuple
    row_count = con.execute("SELECT COUNT(*) FROM jobs_raw").fetchone()[0]
    print(f"jobs_raw row count: {row_count:,}")

    # Show the columns inside jobs_raw, return result as pandas dataframe, don’t show the pandas row index
    columns_df = con.execute("DESCRIBE jobs_raw").df()
    print("\nColumns in jobs_raw:")
    print(columns_df[["column_name", "column_type"]].to_string(index=False))

    # so far
    # Print project path
    # Print CSV path
    # Print database path

    # Check CSV exists
    # Create db folder
    # Open DuckDB

    # Load CSV into jobs_raw
    # Show tables
    # Count rows
    # Show columns






    # Create company lookup table.
    # Create a temporary clean list of of unique company names first,  and then sort companies alphabetically, then number them 1, 2, 3, 4
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
    # for formatting
    print(f"company row count: {company_count:,}")



    # Create employment_type lookup table.
    # Create a temporary clean list of of unique employment types first,  and then sort companies alphabetically, then number them 1, 2, 3, 4
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
    # Create a temporary clean list of of unique position levels first,  and then sort companies alphabetically, then number them 1, 2, 3, 4
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

    # 1. Take a raw column from jobs_raw
    # 2. Remove extra spaces
    # 3. Convert blanks to missing values
    # 4. Keep unique values only
    # 5. Remove missing values
    # 6. Assign each value an ID
    # 7. Save it as a clean lookup table






    # Create main job_posting table.
    # This table stores the main job posting details.
    # job_posting is the main clean table.
    # It keeps one row per job posting.
    # It stores the job title, salary, experience, vacancies, applications, views, and dates.
    # It also connects each job to company, employment type, and position level using I
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

    # Create a clean job_posting table.
    # For each raw job:
    #     keep job ID and title
    #     look up company ID
    #     look up employment type ID
    #     look up position level ID
    #     convert experience and vacancy fields into numbers
    #     convert salary fields into money-like decimal numbers
    #     convert application/view counts into numbers
    #     convert posting dates into real dates
    #     only keep rows with a job ID
    # Then print how many rows were created.









    # The raw CSV has one ugly categories cell per job.
    # That cell may contain many categories.
    # Python splits it open, collects all categories, removes duplicates, and gives DuckDB two clean tables.
    # Pull job ID and raw categories into pandas so Python can split the category text, as a dataframe object
    category_source = con.execute(
        """
        SELECT
            metadata_jobPostId AS job_post_id,
            categories
        FROM jobs_raw
        WHERE metadata_jobPostId IS NOT NULL AND categories IS NOT NULL;
        """
    ).df()

    # create empty Python baskets
    # category stores category names and IDs
    category_records = []
    # job category records store which jobs belong to which category
    job_category_records = []

    # Loop through every job posting and split its categories.
    # Go through each row in the category_source table, one by one
    # The underscore _ means: “There is a row number here, but I do not care about it.”
    # row refers to actual row of data
    for _, row in category_source.iterrows():
        # grab the job ID from the current row
        job_post_id = row["job_post_id"]
        # Call earlier created function and take the ugly categories text and clean it into a Python list
        categories = parse_categories(row["categories"])

        # Loop through categories for each job
        # enumerate(..., start=1) gives category_order, category
        # Why keep category_order? Because the original category list has an order. 
        # We may not use it much, but keeping it is harmless and preserves information.
        for category_order, category in enumerate(categories, start=1):
            # Put this category into the category records basket.
            category_records.append(category)


            # Add job-category relationship record, record that this job belongs to this category.
            job_category_records.append(
                {
                    "job_post_id": job_post_id,
                    "category_id": category["category_id"],
                    "category_order": category_order,
                }
            )

    # Convert Python lists into pandas DataFrames.
    # Before this, category_records and job_category_records are just Python lists.
    # After this, they become pandas DataFrames.
    category_df = pd.DataFrame(category_records)
    job_category_df = pd.DataFrame(job_category_records)

    # Remove duplicate category records. If category ID repeats, keep only one copy. Sort categories by ID. 
    # Clean up the pandas row numbering.
    category_df = (
        category_df
        .drop_duplicates(subset=["category_id"])
        .sort_values("category_id")
        .reset_index(drop=True)
    )

    # Remove duplicate job category records. If category ID repeats, keep only one copy. Sort job categories by ID. 
    # Clean up the pandas row numbering.
    job_category_df = (
        job_category_df
        .drop_duplicates(subset=["job_post_id", "category_id"])
        .reset_index(drop=True)
    )

    # Register pandas DataFrames so DuckDB can read them.
    # "DuckDB, please look at these pandas tables as if they are temporary database tables" 
    # Expose these pandas DataFrames to DuckDB.
    # so that duckDB can see python variables even though category_df and job category_df started as pandas objects
    con.register("category_df", category_df)
    con.register("job_category_df", job_category_df)

    # Create category table.
    # Take the pandas category_df table and save it permanently inside DuckDB as category
    # Make sure category ID is stored as a number by using ::
    # Make sure category ID is stored as a number by using ::
    con.execute(
        """
        CREATE OR REPLACE TABLE category AS
        SELECT
            category_id::INTEGER AS category_id,
            category_name::VARCHAR AS category_name
        FROM category_df;
        """
    )

    # Count how many unique categories were created
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

    # Take the pandas job_category_df table and save it inside DuckDB as job_category
    # which job belongs to which category
    # one job can have many categories
    # one category can appear in many jobs
    print("\nCreated job_category table")
    job_category_count = con.execute("SELECT COUNT(*) FROM job_category").fetchone()[0]
    print(f"job_category row count: {job_category_count:,}")

    # Take job IDs and raw categories from jobs_raw.
    # For each job:
    #    split the categories text into clean category records
    #    save category info into one basket
    #    save job-category links into another basket
    # Turn both baskets into pandas DataFrames.
    # Remove duplicate categories.
    # Remove duplicate job-category links.
    # Let DuckDB read those pandas DataFrames.
    # Create category table.
    # Create job_category bridge table.










    # Create dashboard-ready view.
    # This joins the clean tables into one easy table for analysis.
    # The database is split into clean tables.
    # That is good for storage.
    # But annoying for analysis.
    # So we create one nice view that joins everything back together.
    # vw_career_coach_jobs acts like a ready-made analysis table.
    # a view is not really a new physical table. It is more like a saved SQL query
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




    # Create dashboard-ready view.
    # This view creates one row per category for
    # “Which categories have high hiring demand but weaker applicant interest?”
    # total_job_postings          = how many job ads
    # total_vacancies             = how many openings
    # total_applications          = how many applications
    # total_views                 = how many views
    # median_average_salary       = salary attractiveness
    # applications_per_vacancy    = applicant interest compared to demand
    # applications_per_posting    = applicant interest per ad
    # views_per_posting           = browsing interest per ad
    # Looking out for high vacancies + low applications per vacancy
    # applications_per_vacancy = total applications / total vacancies
    # applications_per_posting = total applications / total distinct posting
    # views_per_posting = total views / total job postings
    # *1.0 forces decimal division.
    # NULLIF(value, 0) means: If the value is 0, turn it into NULL. 
    # If total vacancies is zero, use NULL instead of zero.
    con.execute(
        """
        CREATE OR REPLACE VIEW vw_talent_shortage_categories AS
        SELECT
            category_name,
            
            COUNT(DISTINCT job_post_id) AS total_job_postings,
            
            SUM(number_of_vacancies) AS total_vacancies,
            SUM(total_applications) AS total_applications,
            SUM(total_views) AS total_views,

            MEDIAN(average_salary) AS median_average_salary,

            SUM(total_applications) * 1.0 / NULLIF(SUM(number_of_vacancies), 0)
            AS applications_per_vacancy,

            SUM(total_applications) * 1.0 / NULLIF(COUNT(DISTINCT job_post_id), 0)
            AS applications_per_posting,

            SUM(total_views) * 1.0 / NULLIF(COUNT(DISTINCT job_post_id), 0)
            AS views_per_posting

        FROM vw_career_coach_jobs
        
        WHERE category_name IS NOT NULL
        
        GROUP BY category_name; 
        """
    )

    print("\nCreated vw_talent_shortage_categories view")
    # Count rows in the new view
    talent_shortage_count = con.execute(
        "SELECT COUNT(*) FROM vw_talent_shortage_categories"
    ).fetchone()[0]
    print(f"vw_talent_shortage_categories row count: {talent_shortage_count:,}")

    # close the connection when done
    con.close()
    print("\nDatabase connection closed")
    
    # Create a saved summary view called vw_talent_shortage_categories (from the previous view table)
    # For each category:
    #    count job postings
    #    sum vacancies
    #    sum applications
    #    sum views
    #    calculate median salary
    #    calculate applications per vacancy
    #   calculate applications per posting
    #   calculate views per posting




# if I run this file directly, run main().
# python src/create_database.py will run main()
if __name__ == "__main__":
    main()