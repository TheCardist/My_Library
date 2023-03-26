import pandas as pd
import polars as pl
import streamlit as st
import streamlit.components.v1 as components
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
st.set_page_config(layout="wide")
st.title("Books I've Read")


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df.style.format({"star rating": "{:.2f}"})

    df = df.copy()

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(
                        map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(
                        str).str.contains(user_text_input)]

    return df.style.format({"star rating": "{:.2f}"})


def create_df() -> pl.DataFrame:
    read_df = (pl.read_csv(
        "./book_stats.csv", ignore_errors=True, columns=['Title', 'Authors', 'Read Status', 'Last Date Read', 'Read Count', 'Star Rating', 'Tags'], encoding="utf8")
        .filter(pl.col('Read Status') == 'read')
        .with_columns(pl.col('Star Rating').cast(pl.Float64, strict=False))
        .rename({'Authors': 'Author'})
        .drop('Read Status'))
    # .with_columns(pl.col('Last Date Read').str.strptime(pl.Date, fmt='%Y/%m/%d', strict=False)))

    read_df = read_df.to_pandas()
    read_df.columns = read_df.columns.str.lower()

    return read_df


df = create_df()
st.dataframe(filter_dataframe(df), height=800, use_container_width=True)
