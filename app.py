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
    "Generate Snowflake DDL, COPY INTO and MERGE scripts from CSV or Excel files."
)

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def detect_type(series):

    if pd.api.types.is_integer_dtype(series):
        return "NUMBER"

    if pd.api.types.is_float_dtype(series):
        return "NUMBER(18,2)"

    return "VARCHAR"


# =====================================================
# FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "Upload CSV or Excel",
    type=["csv", "xlsx"]
)

# =====================================================
# PROCESS FILE
# =====================================================

if uploaded_file:

    try:

        # ---------------------------------------------
        # LOAD FILE
        # ---------------------------------------------

        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)

        else:
            df = pd.read_excel(uploaded_file)

        # ---------------------------------------------
        # DATA PREVIEW
        # ---------------------------------------------

        st.subheader("📊 Data Preview")
        st.dataframe(df.head())

        st.divider()

        # ---------------------------------------------
        # TABLE SETTINGS
        # ---------------------------------------------

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

        # ---------------------------------------------
        # COLUMN LIST
        # ---------------------------------------------

        st.subheader("📋 Detected Columns")
        st.write(columns)

        # ---------------------------------------------
        # DATA PROFILE
        # ---------------------------------------------

        st.subheader("📈 Data Profile")

        profile_df = pd.DataFrame(
            {
                "Column": df.columns,
                "Data Type": df.dtypes.astype(str),
                "Null Count": df.isnull().sum().values,
                "Distinct Values": df.nunique().values
            }
        )

        st.dataframe(profile_df)

        # ---------------------------------------------
        # PRIMARY KEY
        # ---------------------------------------------

        primary_key = st.selectbox(
            "Primary Key Column",
            columns
        )

        # ---------------------------------------------
        # DDL
        # ---------------------------------------------

        ddl = (
            f"CREATE OR REPLACE TABLE "
            f"{full_table_name} (\n"
        )

        for col in columns:

            snowflake_type = detect_type(
                df[col]
            )

            ddl += (
                f"    "
                f"{col.upper()} "
                f"{snowflake_type},\n"
            )

        ddl = ddl.rstrip(",\n")

        ddl += "\n);"

        # ---------------------------------------------
        # FILE FORMAT
        # ---------------------------------------------

        file_format_sql = """
CREATE OR REPLACE FILE FORMAT MY_CSV_FORMAT
TYPE = CSV
SKIP_HEADER = 1
FIELD_OPTIONALLY_ENCLOSED_BY = '"';
"""

        # ---------------------------------------------
        # STAGE
        # ---------------------------------------------

        stage_sql = f"""
CREATE OR REPLACE STAGE {stage_name}
FILE_FORMAT = MY_CSV_FORMAT;
"""

        # ---------------------------------------------
        # COPY INTO
        # ---------------------------------------------

        copy_sql = f"""
COPY INTO {full_table_name}
FROM @{stage_name}
FILE_FORMAT = MY_CSV_FORMAT;
"""

        # ---------------------------------------------
        # SELECT
        # ---------------------------------------------

        select_sql = f"""
SELECT *
FROM {full_table_name}
LIMIT 100;
"""

        # ---------------------------------------------
        # MERGE
        # ---------------------------------------------

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

        insert_values = ", ".join(
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
    {insert_values}
);
"""

        # ---------------------------------------------
        # DISPLAY SQL
        # ---------------------------------------------

        st.subheader("🏗 CREATE TABLE")
        st.code(
            ddl,
            language="sql"
        )

        st.subheader("📁 FILE FORMAT")
        st.code(
            file_format_sql,
            language="sql"
        )

        st.subheader("📦 STAGE")
        st.code(
            stage_sql,
            language="sql"
        )

        st.subheader("🚚 COPY INTO")
        st.code(
            copy_sql,
            language="sql"
        )

        st.subheader("🔍 SELECT Query")
        st.code(
            select_sql,
            language="sql"
        )

        st.subheader("🔄 MERGE Statement")
        st.code(
            merge_sql,
            language="sql"
        )

        # ---------------------------------------------
        # DOWNLOAD PACKAGE
        # ---------------------------------------------

        full_script = f"""
-- FILE FORMAT

{file_format_sql}

-- STAGE

{stage_sql}

-- TABLE

{ddl}

-- COPY INTO

{copy_sql}

-- MERGE

{merge_sql}
"""

        st.download_button(
            label="⬇ Download Full Snowflake Script",
            data=full_script,
            file_name=f"{table_name}_snowflake.sql",
            mime="text/plain"
        )

    except Exception as e:

        st.error(
            f"Error while processing file: {str(e)}"
        )