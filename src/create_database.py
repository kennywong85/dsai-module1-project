from pathlib import Path
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

    # Count number of rows inside jobs_raw.
    row_count = con.execute("SELECT COUNT(*) FROM jobs_raw").fetchone()[0]
    print(f"jobs_raw row count: {row_count:,}")

    # Show the columns inside jobs_raw.
    columns_df = con.execute("DESCRIBE jobs_raw").df()

    print("\nColumns in jobs_raw:")
    print(columns_df[["column_name", "column_type"]].to_string(index=False))

    # close th connection when done
    con.close()
    print("\nDatabase connection closed")

# if I run this file directly, run main().
# python src/create_database.py will run main()
if __name__ == "__main__":
    main()