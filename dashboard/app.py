# Structure of code in this file
# 1. Imports
# 2. Page setup - Set dashboard page. Show title and intro.
# 3. Database path - Find db/jobs.duckdb. Stop if database is missing.
# 4. Query helper - Create reusable run_query() function.
# 5. Sidebar filters
# 6. build_filter_sql()
# 7. Dataset summary
# 8. sort_dataframe()
# 9. Dashboard tabs
# 9.1 Market Demand tab
# 9.2 Salary Ranges tab
# 9.3 Experience Requirements tab
# 9.4 Opportunity Score tab
# 9.5 Talent Shortage Signals tab



# Model of how streamlit works
# User changes filter
#    ↓
# Streamlit reruns app.py from top to bottom
#     ↓
# SQL query changes
#     ↓
# DataFrame changes
#     ↓
# table/chart changes



# 1. Imports 
from pathlib import Path
import duckdb
import streamlit as st



# 2. Page setup
# Set the browser page settings
# page_title controls the title shown in the browser tab.
# layout="wide" tells Streamlit: Use more of the screen width.
st.set_page_config(
    page_title="Career Coach - Job Market Navigator",
    layout="wide"
)

# Dashboard title - this creates the title at the top of the dashboard. + short description below the title.
st.title("Career Coach - Job Market Navigator")
st.write(
    """
    This dashboard helps career coaches explore Singapore job postings by
    market demand, salary range, experience requirements, and career opportunity signals.
    """
)



# 3. Database path
# __file__ means this Python file, dashboard/app.py.
# .parents[1] walks up to the project root:
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "db" / "jobs.duckdb"

# print the database path as small caption text in the dashboard (part of the caption)
st.caption(f"Database path: `{DB_PATH}`")

# safety check, stop if database is missing
# If the file is missing, Streamlit shows a red error box:
# Stop running the rest of the app.
if not DB_PATH.exists():
    st.error("Database not found. Run `python src/create_database.py` first.")
    st.stop()



# 4. Query helper
# run_query() is the reusable database-question machine.
# instead of running 
# "con = duckdb.connect(str(DB_PATH), read_only=True)
# result = con.execute(query).df()
# con.close()"
# make one function that run queries cleaner

# If the same query is run again, remember the result instead of recalculating everything.
@st.cache_data

def run_query(query):
    """
    Run a SQL query against the local DuckDB database
    and return the result as a DataFrame.
    """
    # opens the database in read-only mode. Also, read-only reduces DuckDB lock issues
    con = duckdb.connect(str(DB_PATH), read_only=True)
    # This sends the SQL query to DuckDB and returns the result as a pandas DataFrame.
    result = con.execute(query).df()
    con.close()
    return result







# 5. Sidebar filters
# The user chooses filters there.
# Later, those filter choices get turned into SQL conditions.
# Sidebar widgets
#    ↓
# User selects values
#    ↓
# Python stores those values in variables
#    ↓
# build_filter_sql() turns them into SQL
#    ↓
# All dashboard tabs use the filtered data

# title 
st.sidebar.header("Dashboard Filters")

# create a query to get all available categories:
category_list_query = """
SELECT DISTINCT
    category_name
FROM vw_career_coach_jobs
WHERE category_name IS NOT NULL
ORDER BY category_name;
"""

# This runs the SQL and turns the result into a normal Python list.
# ["category_name"] selects only the category, tolist() turns it into a Python list
category_list = run_query(category_list_query)["category_name"].tolist()

# This creates the category filter widget, create a dropdown where users can select multiple options with multiselect
# options=category_list, means these are the available choices. default selection is nothing
selected_categories = st.sidebar.multiselect(
    "Job categories",
    options=category_list,
    default=[]
)

# Ask the database for the smallest and biggest values for the sliders
range_query = """
SELECT
    MIN(average_salary) AS min_average_salary,
    MAX(average_salary) AS max_average_salary,
    MIN(minimum_years_experience) AS min_years_experience,
    MAX(minimum_years_experience) AS max_years_experience,
    MIN(new_posting_date) AS min_posting_date,
    MAX(new_posting_date) AS max_posting_date
FROM vw_career_coach_jobs;
"""

# run SQL query, store in range_df
range_df = run_query(range_query)

# Salary range slider, pulls values out of range_df 
# from row 0, get the min and max _average_salary value.
# row 0 because range_query returns only one row.
# int(...) converts it into a whole number.
min_salary = int(range_df.loc[0, "min_average_salary"])
max_salary = int(range_df.loc[0, "max_average_salary"])

# Keep the salary slider usable.
# Some datasets may contain extreme salary outliers.
# min() - Use the smaller value between:
# - actual max salary
# - 20000
salary_slider_max = min(max_salary, 30000)

# create salary slider
selected_salary_range = st.sidebar.slider(
    "Average salary range",
    min_value=min_salary,
    max_value=salary_slider_max,
    value=(min_salary, salary_slider_max),
    step=100
)

# experience range slider, pulls values out of range_df 
# from row 0, get the min and max _experience value.
# row 0 because range_query returns only one row.
# int(...) converts it into a whole number.
min_experience = int(range_df.loc[0, "min_years_experience"])
max_experience = int(range_df.loc[0, "max_years_experience"])

# Keep the experience slider readable.
# Some datasets may contain extreme salary outliers.
# min() - Use the smaller value between: max exp and 20
experience_slider_max = min(max_experience, 20)

# create experience slider
selected_experience_range = st.sidebar.slider(
    "Minimum years experience range",
    min_value=min_experience,
    max_value=experience_slider_max,
    value=(min_experience, experience_slider_max),
    step=1
)


# posting date range slider, pulls values out of range_df 
# This gets the earliest and latest posting dates from the data
min_posting_date = range_df.loc[0, "min_posting_date"]
max_posting_date = range_df.loc[0, "max_posting_date"]

# date range inpuut
selected_date_range = st.sidebar.date_input(
    "Job Posting date range",
    value=(min_posting_date, max_posting_date),
    min_value=min_posting_date,
    max_value=max_posting_date
)

# number of results slider, min 5, max 20, default 10, increment of 1
top_n = st.sidebar.slider(
    "Number of results to show",
    min_value=5,
    max_value=20,
    value=10,
    step=1
)

# Create a category dropdown.
# Create a salary slider.
# Create an experience slider.
# Create a date range filter.
# Create a top-N results slider.
# Store all user selections in Python variables.



# 6. build_filter_sql(), the bridge between the sidebar controls and the SQL queries.
# The sidebar collects user choices.
# build_filter_sql() turns those choices into SQL language.
# Then every tab uses that SQL to filter the database
# The sidebar itself does not filter the data, only store users choice
# e.g.
# category_name IS NOT NULL
# AND category_name IN ('Engineering', 'Information Technology')
# AND average_salary BETWEEN 3000 AND 10000
# AND minimum_years_experience BETWEEN 0 AND 5
# AND new_posting_date BETWEEN DATE '2023-02-24' AND DATE '2024-05-29'

def build_filter_sql():
    """
    Build SQL filters based on the sidebar selections.
    These filters are reused across the dashboard.
    """
    # creates a Python list called filters
    filters = [
        "category_name IS NOT NULL"
    ]

    # category filter
    # If the user selects nothing, selected_categories is an empty list
    # cleaned_categories = [category.replace("'", "''") - Handle apostrophes safely for SQL, loop through selection
    # If a category has an apostrophe, double it so SQL doesn’t choke
    if selected_categories:
        cleaned_categories = [
            category.replace("'", "''")
            for category in selected_categories
        ]

        # Join selected categories into SQL text, this turns the Python list into SQL-ready text.
        # f"'{category}'" wraps each category in single quotes
        # ", ".join(...) joins them with commas
        category_text = ", ".join(
            f"'{category}'"
            for category in cleaned_categories
        )

        # adds a new SQL condition into the filters list
        filters.append(f"category_name IN ({category_text})")

    # from salary slider, selected salary range has 2 values
    salary_min, salary_max = selected_salary_range

    # adds a salary condition to filters
    # BETWEEN - inclusive of min and max values
    # IS NULL - Keep rows with missing salary, or rows within the selected salary range.
    filters.append(
        f"""
        (
            average_salary IS NULL
            OR average_salary BETWEEN {salary_min} AND {salary_max}
        )
        """
    )

    # from experience slider, selected salary range has 2 values
    experience_min, experience_max = selected_experience_range

    # adds an experience condition to filters
    # BETWEEN - inclusive of min and max values
    # IS NULL - Keep rows with missing experience, or rows within the selected experience range.
    filters.append(
        f"""
        (
            minimum_years_experience IS NULL
            OR minimum_years_experience BETWEEN {experience_min} AND {experience_max}
        )
        """
    )

    # date input should return 2 dates
    if len(selected_date_range) == 2:
        start_date = selected_date_range[0]
        end_date = selected_date_range[1]

        # add date filter
        filters.append(
            f"new_posting_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'"
        )

    # this is the final line inside the function.
    # It takes the list of filters and joins them together using SQL AND.
    return " AND ".join(filters)

# It stores the final SQL filter text inside: filter_sql. e.g. WHERE {filter_sql}
filter_sql = build_filter_sql()

# User moves salary slider
#         ↓
# selected_salary_range changes
#         ↓
# Streamlit reruns app.py
#         ↓
# build_filter_sql() creates new SQL
#         ↓
# queries use WHERE {filter_sql}
#         ↓
# tables and charts update



# 7. Dataset summary
# shows the big dashboard numbers at the top
# After applying the sidebar filters, recalculate how much data we are looking at. reuse filter_sql data
# That means the summary is not fixed. It changes when the sidebar filters change
summary_query = f"""
SELECT
    COUNT(DISTINCT job_post_id) AS total_unique_job_postings,
    COUNT(DISTINCT category_name) AS total_categories,
    COUNT(DISTINCT company_name) AS total_companies,
    MIN(new_posting_date) AS earliest_posting_date,
    MAX(new_posting_date) AS latest_posting_date
FROM vw_career_coach_jobs
WHERE {filter_sql};
"""

# run summary query, store results in summary_df
# summary_df is a pandas DataFrame with one row
summary_df = run_query(summary_query)

# split the page into three side-by-side columns.
st.subheader("Dataset Summary")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Unique Job Postings",
    f"{summary_df.loc[0, 'total_unique_job_postings']:,}"
)

col2.metric(
    "Categories",
    f"{summary_df.loc[0, 'total_categories']:,}"
)

col3.metric(
    "Companies",
    f"{summary_df.loc[0, 'total_companies']:,}"
)

st.caption(
    f"Posting date range: {summary_df.loc[0, 'earliest_posting_date']} "
    f"to {summary_df.loc[0, 'latest_posting_date']}"
)


# 8. sort_dataframe()
# This function sorts a table based on what the user selects
# 3 inputs
# the dataframe, the table we want to sort
# the column to sort by
# the direction e.g. highest or lowest first
def sort_dataframe(dataframe, sort_column, sort_direction):
    """
    Sort a DataFrame using a selected column and direction.
    """
    # This line creates a Boolean value: either True or False
    # Lowest first means ascending = true
    # highest first means ascending = false
    ascending = sort_direction == "Lowest first"

    # This sorts the DataFrame and returns the sorted version.
    # After sorting, pandas keeps the old row numbers unless we reset them, don’t keep the old index as a new column.
    return dataframe.sort_values(
        sort_column,
        ascending=ascending
    ).reset_index(drop=True)

# sort control changes DataFrame
#         ↓
# table changes
#         ↓
# chart changes


# 9. Dashboard tabs

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Market Demand",
        "Salary Ranges",
        "Experience Requirements",
        "Opportunity Score",
        "Talent Shortage Signals"
    ]
)


# -----------------------------
# Tab 1: Market Demand
# -----------------------------

with tab1:
    st.header("Market Demand")

    st.write(
        """
        This section helps career coaches identify job categories with stronger
        visible market demand.
        """
    )

    postings_query = f"""
    SELECT
        category_name,
        COUNT(DISTINCT job_post_id) AS total_job_postings
    FROM vw_career_coach_jobs
    WHERE {filter_sql}
    GROUP BY category_name
    ORDER BY total_job_postings DESC
    LIMIT {top_n};
    """

    top_categories_by_postings = run_query(postings_query)

    vacancies_query = f"""
    SELECT
        category_name,
        SUM(number_of_vacancies) AS total_vacancies
    FROM vw_career_coach_jobs
    WHERE {filter_sql}
    GROUP BY category_name
    ORDER BY total_vacancies DESC
    LIMIT {top_n};
    """

    top_categories_by_vacancies = run_query(vacancies_query)

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Top Categories by Job Postings")

        postings_sort_direction = st.radio(
            "Sort job postings",
            ["Highest first", "Lowest first"],
            horizontal=True,
            key="postings_sort_direction"
        )

        top_categories_by_postings = sort_dataframe(
            top_categories_by_postings,
            "total_job_postings",
            postings_sort_direction
        )

        st.dataframe(
            top_categories_by_postings,
            use_container_width=True
        )

        chart_data = top_categories_by_postings.set_index("category_name")
        st.bar_chart(chart_data["total_job_postings"])

    with right_col:
        st.subheader("Top Categories by Vacancies")

        vacancies_sort_direction = st.radio(
            "Sort vacancies",
            ["Highest first", "Lowest first"],
            horizontal=True,
            key="vacancies_sort_direction"
        )

        top_categories_by_vacancies = sort_dataframe(
            top_categories_by_vacancies,
            "total_vacancies",
            vacancies_sort_direction
        )

        st.dataframe(
            top_categories_by_vacancies,
            use_container_width=True
        )

        chart_data = top_categories_by_vacancies.set_index("category_name")
        st.bar_chart(chart_data["total_vacancies"])


# -----------------------------
# Tab 2: Salary Ranges
# -----------------------------

with tab2:
    st.header("Salary Ranges")

    st.write(
        """
        This section compares median salary ranges across job categories.

        Median salary is used instead of average salary because salary data can contain
        outliers. This gives career coaches a more stable reference point for salary
        expectation discussions.
        """
    )

    salary_query = f"""
    SELECT
        category_name,
        COUNT(DISTINCT job_post_id) AS total_job_postings,
        MEDIAN(salary_minimum) AS median_salary_minimum,
        MEDIAN(salary_maximum) AS median_salary_maximum,
        MEDIAN(average_salary) AS median_average_salary
    FROM vw_career_coach_jobs
    WHERE {filter_sql}
      AND average_salary IS NOT NULL
    GROUP BY category_name
    ORDER BY median_average_salary DESC
    LIMIT {top_n};
    """

    salary_by_category = run_query(salary_query)

    st.subheader("Top Categories by Median Average Salary")

    salary_sort_option = st.selectbox(
        "Sort salary table and chart by",
        [
            "Median average salary",
            "Median salary minimum",
            "Median salary maximum",
            "Total job postings"
        ]
    )

    salary_sort_column_map = {
        "Median average salary": "median_average_salary",
        "Median salary minimum": "median_salary_minimum",
        "Median salary maximum": "median_salary_maximum",
        "Total job postings": "total_job_postings"
    }

    salary_sort_direction = st.radio(
        "Sort salary direction",
        ["Highest first", "Lowest first"],
        horizontal=True,
        key="salary_sort_direction"
    )

    salary_by_category = sort_dataframe(
        salary_by_category,
        salary_sort_column_map[salary_sort_option],
        salary_sort_direction
    )

    st.dataframe(
        salary_by_category,
        use_container_width=True
    )

    chart_data = salary_by_category.set_index("category_name")
    st.bar_chart(chart_data[salary_sort_column_map[salary_sort_option]])

    st.caption(
        """
        Note: Higher salary categories may also require more specialised skills,
        stronger experience, or higher qualifications. Career coaches should compare
        salary together with demand and experience requirements.
        """
    )


# -----------------------------
# Tab 3: Experience Requirements
# -----------------------------

with tab3:
    st.header("Experience Requirements")

    st.write(
        """
        This section helps career coaches identify job categories with lower
        experience requirements and stronger entry-level availability.

        This is useful when advising fresh graduates, early-career jobseekers,
        or mid-career switchers.
        """
    )

    experience_query = f"""
    SELECT
        category_name,
        COUNT(DISTINCT job_post_id) AS total_job_postings,
        MEDIAN(minimum_years_experience) AS median_min_years_experience,
        AVG(minimum_years_experience) AS average_min_years_experience
    FROM vw_career_coach_jobs
    WHERE {filter_sql}
      AND minimum_years_experience IS NOT NULL
    GROUP BY category_name
    ORDER BY median_min_years_experience ASC, total_job_postings DESC
    LIMIT {top_n};
    """

    experience_by_category = run_query(experience_query)

    entry_level_query = f"""
    SELECT
        category_name,
        COUNT(DISTINCT job_post_id) AS entry_level_job_postings,
        MEDIAN(average_salary) AS median_average_salary,
        MEDIAN(minimum_years_experience) AS median_min_years_experience
    FROM vw_career_coach_jobs
    WHERE {filter_sql}
      AND minimum_years_experience <= 1
    GROUP BY category_name
    ORDER BY entry_level_job_postings DESC
    LIMIT {top_n};
    """

    entry_level_friendly_categories = run_query(entry_level_query)

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Lower Experience Requirement Categories")

        experience_sort_option = st.selectbox(
            "Sort experience table and chart by",
            [
                "Median minimum years experience",
                "Average minimum years experience",
                "Total job postings"
            ]
        )

        experience_sort_column_map = {
            "Median minimum years experience": "median_min_years_experience",
            "Average minimum years experience": "average_min_years_experience",
            "Total job postings": "total_job_postings"
        }

        experience_sort_direction = st.radio(
            "Sort experience direction",
            ["Lowest first", "Highest first"],
            horizontal=True,
            key="experience_sort_direction"
        )

        experience_by_category = sort_dataframe(
            experience_by_category,
            experience_sort_column_map[experience_sort_option],
            experience_sort_direction
        )

        st.dataframe(
            experience_by_category,
            use_container_width=True
        )

        chart_data = experience_by_category.set_index("category_name")
        st.bar_chart(chart_data[experience_sort_column_map[experience_sort_option]])

    with right_col:
        st.subheader("Entry-Level Friendly Categories")

        entry_sort_direction = st.radio(
            "Sort entry-level postings",
            ["Highest first", "Lowest first"],
            horizontal=True,
            key="entry_sort_direction"
        )

        entry_level_friendly_categories = sort_dataframe(
            entry_level_friendly_categories,
            "entry_level_job_postings",
            entry_sort_direction
        )

        st.dataframe(
            entry_level_friendly_categories,
            use_container_width=True
        )

        chart_data = entry_level_friendly_categories.set_index("category_name")
        st.bar_chart(chart_data["entry_level_job_postings"])

    st.caption(
        """
        Note: Lower experience requirements do not automatically mean a role is easy
        to obtain. Career coaches should still consider skills, qualifications,
        competition, and jobseeker fit.
        """
    )


# -----------------------------
# Tab 4: Career Opportunity Score
# -----------------------------

with tab4:
    st.header("Career Opportunity Score")

    st.write(
        """
        This section creates a simple prototype score to compare job categories.

        The score combines three signals:

        1. Demand: job postings and vacancies
        2. Salary: median average salary
        3. Accessibility: lower experience requirements and more entry-level postings

        This is not a final recommendation engine. It is a simple scoring prototype
        to help career coaches compare job categories more easily.
        """
    )

    minimum_postings = st.slider(
        "Minimum job postings required for a category to be scored",
        min_value=0,
        max_value=150000,
        value=100,
        step=5000
    )

    category_summary_query = f"""
    SELECT
        category_name,
        COUNT(DISTINCT job_post_id) AS total_job_postings,
        SUM(number_of_vacancies) AS total_vacancies,
        MEDIAN(average_salary) AS median_average_salary,
        MEDIAN(minimum_years_experience) AS median_min_years_experience,
        COUNT(DISTINCT CASE
            WHEN minimum_years_experience <= 1 THEN job_post_id
        END) AS entry_level_job_postings
    FROM vw_career_coach_jobs
    WHERE {filter_sql}
    GROUP BY category_name
    HAVING COUNT(DISTINCT job_post_id) >= {minimum_postings}
    ORDER BY total_job_postings DESC;
    """

    category_summary = run_query(category_summary_query)

    st.write(f"Categories included in scoring: {len(category_summary)}")

    if category_summary.empty:
        st.warning(
            "No categories match the selected filters and minimum job postings threshold."
        )

    else:
        category_summary["entry_level_share"] = (
            category_summary["entry_level_job_postings"]
            / category_summary["total_job_postings"]
        )

        score_df = category_summary.copy()

        score_df = score_df.dropna(
            subset=[
                "total_job_postings",
                "total_vacancies",
                "median_average_salary",
                "median_min_years_experience",
                "entry_level_share"
            ]
        )

        # Demand score rewards categories with more postings and vacancies.
        score_df["posting_score"] = (
            score_df["total_job_postings"].rank(pct=True) * 100
        )

        score_df["vacancy_score"] = (
            score_df["total_vacancies"].rank(pct=True) * 100
        )

        score_df["demand_score"] = (
            score_df["posting_score"] * 0.5
            + score_df["vacancy_score"] * 0.5
        )

        # Salary score rewards higher median salary.
        score_df["salary_score"] = (
            score_df["median_average_salary"].rank(pct=True) * 100
        )

        # Accessibility score rewards lower experience requirements
        # and higher entry-level share.
        score_df["low_experience_score"] = (
            score_df["median_min_years_experience"]
            .rank(pct=True, ascending=False) * 100
        )

        score_df["entry_level_score"] = (
            score_df["entry_level_share"].rank(pct=True) * 100
        )

        score_df["accessibility_score"] = (
            score_df["low_experience_score"] * 0.5
            + score_df["entry_level_score"] * 0.5
        )

        # Final opportunity score.
        score_df["opportunity_score"] = (
            score_df["demand_score"] * 0.4
            + score_df["salary_score"] * 0.3
            + score_df["accessibility_score"] * 0.3
        )

        opportunity_score = score_df.copy()

        opportunity_score["entry_level_share_percent"] = (
            opportunity_score["entry_level_share"] * 100
        )

        score_sort_option = st.selectbox(
            "Sort opportunity score table and chart by",
            [
                "Opportunity score",
                "Demand score",
                "Salary score",
                "Accessibility score",
                "Total job postings",
                "Total vacancies",
                "Median average salary",
                "Entry-level share"
            ]
        )

        score_sort_column_map = {
            "Opportunity score": "opportunity_score",
            "Demand score": "demand_score",
            "Salary score": "salary_score",
            "Accessibility score": "accessibility_score",
            "Total job postings": "total_job_postings",
            "Total vacancies": "total_vacancies",
            "Median average salary": "median_average_salary",
            "Entry-level share": "entry_level_share_percent"
        }

        score_sort_direction = st.radio(
            "Sort opportunity score direction",
            ["Highest first", "Lowest first"],
            horizontal=True,
            key="score_sort_direction"
        )

        opportunity_score = sort_dataframe(
            opportunity_score,
            score_sort_column_map[score_sort_option],
            score_sort_direction
        )

        display_columns = [
            "category_name",
            "total_job_postings",
            "total_vacancies",
            "median_average_salary",
            "median_min_years_experience",
            "entry_level_share_percent",
            "demand_score",
            "salary_score",
            "accessibility_score",
            "opportunity_score"
        ]

        st.subheader("Top Categories by Career Opportunity Score")

        st.dataframe(
            opportunity_score[display_columns].head(top_n),
            use_container_width=True
        )

        chart_data = (
            opportunity_score[
                [
                    "category_name",
                    score_sort_column_map[score_sort_option]
                ]
            ]
            .head(top_n)
            .set_index("category_name")
        )

        st.bar_chart(chart_data[score_sort_column_map[score_sort_option]])

        st.caption(
            """
            Score weights: Demand 40%, Salary 30%, Accessibility 30%.

            Accessibility rewards categories with lower median experience requirements
            and a higher share of entry-level job postings.
            """
        )

        st.subheader("How to Interpret This Score")

        st.write(
            """
            A high score means the category performs relatively well across the selected
            labour-market signals. It does not mean the category is suitable for every
            jobseeker.

            Career coaches should still consider the jobseeker's skills, background,
            interests, qualifications, and constraints before making recommendations.
            """
        )

# -----------------------------
# Tab 5: Talent Shortage Signals
# -----------------------------
with tab5:
    st.header("Talent Shortage Signals")

    st.write(
        """
        This section identifies job categories where hiring demand appears high
        but applicant interest may be weaker.

        This is a proxy analysis using job postings, vacancies, applications,
        views, and salary data. It does not prove an actual shortage, but it can
        highlight categories worth further workforce-planning investigation.
        """
    )

    minimum_shortage_postings = st.slider(
        "Minimum job postings required for shortage analysis",
        min_value=0,
        max_value=150000,
        value=100,
        step=5000
    )

    talent_query = f"""
    SELECT
        category_name,
        total_job_postings,
        total_vacancies,
        total_applications,
        total_views,
        median_average_salary,
        applications_per_vacancy,
        applications_per_posting,
        views_per_posting
    FROM vw_talent_shortage_categories
    WHERE category_name IS NOT NULL
      AND total_job_postings >= {minimum_shortage_postings}
    ORDER BY total_vacancies DESC;
    """

    talent_df = run_query(talent_query)

    st.write(f"Categories included in shortage analysis: {len(talent_df)}")

    if talent_df.empty:
        st.warning("No categories match the selected shortage-analysis threshold.")

    else:
        talent_df = talent_df.dropna(
            subset=[
                "total_job_postings",
                "total_vacancies",
                "applications_per_vacancy",
                "views_per_posting",
                "median_average_salary"
            ]
        )

        talent_df["posting_demand_score"] = (
            talent_df["total_job_postings"].rank(pct=True) * 100
        )

        talent_df["vacancy_demand_score"] = (
            talent_df["total_vacancies"].rank(pct=True) * 100
        )

        talent_df["demand_score"] = (
            talent_df["posting_demand_score"] * 0.5
            + talent_df["vacancy_demand_score"] * 0.5
        )

        talent_df["low_application_score"] = (
            talent_df["applications_per_vacancy"]
            .rank(pct=True, ascending=False) * 100
        )

        talent_df["low_view_score"] = (
            talent_df["views_per_posting"]
            .rank(pct=True, ascending=False) * 100
        )

        talent_df["weak_interest_score"] = (
            talent_df["low_application_score"] * 0.7
            + talent_df["low_view_score"] * 0.3
        )

        talent_df["salary_attractiveness_score"] = (
            talent_df["median_average_salary"].rank(pct=True) * 100
        )

        talent_df["talent_shortage_signal_score"] = (
            talent_df["demand_score"] * 0.6
            + talent_df["weak_interest_score"] * 0.4
        )

        shortage_sort_option = st.selectbox(
            "Sort talent shortage table and chart by",
            [
                "Talent shortage signal score",
                "Demand score",
                "Weak interest score",
                "Total vacancies",
                "Applications per vacancy",
                "Median average salary"
            ]
        )

        shortage_sort_column_map = {
            "Talent shortage signal score": "talent_shortage_signal_score",
            "Demand score": "demand_score",
            "Weak interest score": "weak_interest_score",
            "Total vacancies": "total_vacancies",
            "Applications per vacancy": "applications_per_vacancy",
            "Median average salary": "median_average_salary"
        }

        shortage_sort_direction = st.radio(
            "Sort talent shortage direction",
            ["Highest first", "Lowest first"],
            horizontal=True,
            key="shortage_sort_direction"
        )

        talent_df = sort_dataframe(
            talent_df,
            shortage_sort_column_map[shortage_sort_option],
            shortage_sort_direction
        )

        display_columns = [
            "category_name",
            "total_job_postings",
            "total_vacancies",
            "total_applications",
            "applications_per_vacancy",
            "views_per_posting",
            "median_average_salary",
            "demand_score",
            "weak_interest_score",
            "salary_attractiveness_score",
            "talent_shortage_signal_score"
        ]

        st.subheader("Potential Talent Shortage Categories")

        st.dataframe(
            talent_df[display_columns].head(top_n),
            use_container_width=True
        )

        chart_data = (
            talent_df[
                [
                    "category_name",
                    shortage_sort_column_map[shortage_sort_option]
                ]
            ]
            .head(top_n)
            .set_index("category_name")
        )

        st.bar_chart(chart_data[shortage_sort_column_map[shortage_sort_option]])

        st.caption(
            """
            Talent shortage signal score combines high demand and weaker applicant
            interest. Salary attractiveness is shown as a supporting context, not
            as proof of shortage.

            A category with high demand and low applications per vacancy may indicate
            hiring friction, low attractiveness, skills mismatch, or other labour-market
            constraints.
            """
        )