import streamlit as st
import pandas as pd

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="SQL Builder Pro",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 SQL Builder Pro")
st.caption(
    "Generate Snowflake DDL, COPY INTO, MERGE scripts and SQL queries from CSV or Excel files."
)

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def detect_type(series):

    if pd.api.types.is_integer_dtype(series):
        return "NUMBER"

    if pd.api.types.is_float_dtype(series):
        return "NUMBER(18,2)"

    values = (
        series.dropna()
        .astype(str)
        .head(20)
        .tolist()
    )

    if values:

        try:
            pd.to_datetime(
                values,
                errors="raise"
            )
            return "DATE"
        except:
            pass

        lowered = [v.lower() for v in values]

        if all(
            v in ["true", "false", "1", "0"]
            for v in lowered
        ):
            return "BOOLEAN"

    return "VARCHAR"


# =====================================================
# FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "Upload CSV or Excel",
    type=["csv", "xlsx"]
)

# =====================================================
# MAIN APP
# =====================================================

if uploaded_file:

    try:

        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # =====================================================
        # DASHBOARD METRICS
        # =====================================================

        st.subheader("📊 Dataset Summary")

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Rows", len(df))
        m2.metric("Columns", len(df.columns))
        m3.metric(
            "Null Values",
            int(df.isnull().sum().sum())
        )
        m4.metric(
            "Duplicate Rows",
            int(df.duplicated().sum())
        )

        # =====================================================
        # PREVIEW
        # =====================================================

        st.subheader("📋 Data Preview")
        st.dataframe(df.head())

        # =====================================================
        # DATA QUALITY
        # =====================================================

        st.subheader("✅ Data Quality Report")

        duplicate_count = int(
            df.duplicated().sum()
        )

        if duplicate_count > 0:

            st.warning(
                f"{duplicate_count} duplicate rows detected."
            )

        else:

            st.success(
                "No duplicate rows detected."
            )

        null_summary = pd.DataFrame(
            {
                "Column": df.columns,
                "Null Count": df.isnull().sum().values,
                "Distinct Values": df.nunique().values
            }
        )

        st.dataframe(null_summary)

        st.divider()

        # =====================================================
        # CONFIGURATION
        # =====================================================

        col1, col2, col3 = st.columns(3)

        with col1:
            database_name = st.text_input(
                "Database",
                "DEV_DB"
            )

        with col2:
            schema_name = st.text_input(
                "Schema",
                "PUBLIC"
            )

        with col3:
            table_name = st.text_input(
                "Table",
                "CUSTOMER_DATA"
            )

        stage_name = st.text_input(
            "Stage Name",
            "MY_STAGE"
        )

        full_table_name = (
            f"{database_name}.{schema_name}.{table_name}"
        )

        columns = df.columns.tolist()

        st.subheader("📌 Columns")
        st.write(columns)

        primary_key = st.selectbox(
            "Primary Key Column",
            columns
        )

        # =====================================================
        # PROFILE TABLE
        # =====================================================

        st.subheader("📈 Data Profile")

        profile_df = pd.DataFrame(
            {
                "Column": df.columns,
                "Detected Type": [
                    detect_type(df[c])
                    for c in df.columns
                ],
                "Null Count": df.isnull().sum().values,
                "Distinct Values": df.nunique().values
            }
        )

        st.dataframe(profile_df)

        # =====================================================
        # CREATE TABLE
        # =====================================================

        ddl = (
            f"CREATE OR REPLACE TABLE "
            f"{full_table_name} (\n"
        )

        for col in columns:

            ddl += (
                f"    {col.upper()} "
                f"{detect_type(df[col])},\n"
            )

        ddl = ddl.rstrip(",\n")
        ddl += "\n);"

        # =====================================================
        # FILE FORMAT
        # =====================================================

        file_format_sql = """
CREATE OR REPLACE FILE FORMAT MY_CSV_FORMAT
TYPE = CSV
SKIP_HEADER = 1
FIELD_OPTIONALLY_ENCLOSED_BY = '"';
"""

        # =====================================================
        # STAGE
        # =====================================================

        stage_sql = f"""
CREATE OR REPLACE STAGE {stage_name}
FILE_FORMAT = MY_CSV_FORMAT;
"""

        # =====================================================
        # COPY INTO
        # =====================================================

        copy_sql = f"""
COPY INTO {full_table_name}
FROM @{stage_name}
FILE_FORMAT = MY_CSV_FORMAT;
"""

        # =====================================================
        # SELECT
        # =====================================================

        select_sql = f"""
SELECT *
FROM {full_table_name}
LIMIT 100;
"""

        # =====================================================
        # MERGE
        # =====================================================

        update_cols = []

        for col in columns:

            if col != primary_key:

                update_cols.append(
                    f"    tgt.{col.upper()} = src.{col.upper()}"
                )

        update_clause = ",\n".join(update_cols)

        insert_cols = ", ".join(
            [c.upper() for c in columns]
        )

        insert_vals = ", ".join(
            [
                f"src.{c.upper()}"
                for c in columns
            ]
        )

        merge_sql = f"""
MERGE INTO {full_table_name} tgt
USING STG_{table_name} src
ON tgt.{primary_key.upper()} =
   src.{primary_key.upper()}

WHEN MATCHED THEN
UPDATE SET
{update_clause}

WHEN NOT MATCHED THEN
INSERT (
    {insert_cols}
)
VALUES (
    {insert_vals}
);
"""

        # =====================================================
        # SQL GENERATOR
        # =====================================================

        st.subheader("🤖 SQL Assistant")

        question = st.text_input(
            "Ask a SQL question",
            placeholder="Show total sales by region"
        )

        if question:

            q = question.lower()

            generated_sql = ""

            if "sales" in q and "region" in q:

                generated_sql = f"""
SELECT REGION,
       SUM(SALES) AS TOTAL_SALES
FROM {table_name}
GROUP BY REGION
ORDER BY TOTAL_SALES DESC;
"""

            elif "top" in q and "customer" in q:

                generated_sql = f"""
SELECT CUSTOMER_NAME,
       SUM(SALES) AS TOTAL_SALES
FROM {table_name}
GROUP BY CUSTOMER_NAME
ORDER BY TOTAL_SALES DESC
LIMIT 10;
"""

            elif "count" in q:

                generated_sql = f"""
SELECT COUNT(*)
FROM {table_name};
"""

            else:

                generated_sql = """
-- Query pattern not yet supported.
-- Add additional rules in app.py
"""

            st.code(
                generated_sql,
                language="sql"
            )

        # =====================================================
        # DISPLAY SQL
        # =====================================================

        st.subheader("🏗 CREATE TABLE")
        st.code(ddl, language="sql")

        st.subheader("📁 FILE FORMAT")
        st.code(file_format_sql, language="sql")

        st.subheader("📦 STAGE")
        st.code(stage_sql, language="sql")

        st.subheader("🚚 COPY INTO")
        st.code(copy_sql, language="sql")

        st.subheader("🔄 MERGE")
        st.code(merge_sql, language="sql")

        st.subheader("🔍 SELECT")
        st.code(select_sql, language="sql")

        # =====================================================
        # DOWNLOAD PACKAGE
        # =====================================================

        full_script = f"""
{file_format_sql}

{stage_sql}

{ddl}

{copy_sql}

{merge_sql}
"""

        st.download_button(
            label="⬇ Download Full Snowflake Package",
            data=full_script,
            file_name=f"{table_name}_snowflake.sql",
            mime="text/plain"
        )

    except Exception as e:

        st.error(
            f"Error processing file: {str(e)}"
        )