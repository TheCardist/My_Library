import pandas as pd
import polars as pl
from streamlit_option_menu import option_menu
import streamlit as st
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
)
from plotly_calplot import calplot, month_calplot
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(layout="wide")


def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


local_css("stylesheet.css")

selected = option_menu(
    menu_title=None,
    options=["Books Read", "Stats"],
    icons=["code", "braces", "bricks"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0px",
                      "width": "40rem",
                      "background-color": "#0e1117"
                      },
        "icon": {"color": "#8bff80", "font-size": "14px"},
        "nav-link": {
            "font-size": "14px",
            "text-align": "center",
            "margin": "auto",
            "background-color": "#333333",
            "height": "30px",
            "width": "13rem",
            "color": "#fff",
            "border-radius": "5px"
        },
        "nav-link-selected": {
            "background-color": "#454158",
            "font-weight": "300",
            "color": "#f7f8f2",
            "border": "1px solid #c42b1c"
        }
    }
)


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
    read_df = read_df.sort_values(
        by="last date read", ignore_index=True)
    read_df.index = read_df.index + 1
    read_df.index.name = "order"
    return read_df


def books_read():
    df = create_df()
    with st.container():
        st.title("Books I've Read")
        st.dataframe(filter_dataframe(df), height=800,
                     use_container_width=True)


def book_stats():
    URL = st.secrets['URL']
    JSON_KEY = {"type": st.secrets.json.type,
                "project_id": st.secrets.json.project_id,
                "private_key_id": st.secrets.json.private_key_id,
                "private_key": st.secrets.json.private_key,
                "client_email": st.secrets.json.client_email,
                "client_id": st.secrets.json.client_id,
                "auth_uri": st.secrets.json.auth_uri,
                "token_uri": st.secrets.json.token_uri,
                "auth_provider_x509_cert_url": st.secrets.json.auth_provider,
                "client_x509_cert_url": st.secrets.json.client}

    # Set up API credentials and open the worksheet
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        JSON_KEY, scope)
    gc = gspread.authorize(credentials)
    workbook = gc.open_by_url(URL)
    worksheet = workbook.worksheet('Sheet1')

    data = worksheet.get_all_values()
    headers = data.pop(0)

    df = pd.DataFrame(data, columns=headers)

    df['Dates'] = pd.to_datetime(df.Dates)
    df['Pages'] = pd.to_numeric(df.Pages)
    # df['Dates'] = df['Dates'].dt.strftime('%Y-%m-%d')

    fig = calplot(
        df,
        x='Dates',
        y='Pages',
        years_title=True,
        colorscale="Purpor",
        gap=5,
        title="Daily Pages Read",
        total_height=250,
        showscale=True,
        month_lines_width=1,
        dark_theme=True,
    )

    fig2 = month_calplot(
        df,
        x='Dates',
        y='Pages',
        colorscale="Purpor",
        showscale=True,
        total_height=250,
        title="Total Pages per Month",
        dark_theme=True)
    
    df2 = create_df()
    df2 = df2[['last date read', 'read count']]
    df2['last date read'] = pd.to_datetime(
        df2['last date read'], errors='coerce')
    df2.reset_index()

    fig3 = month_calplot(
        df2,
        x='last date read',
        y='read count',
        colorscale="Purpor",
        showscale=True,
        total_height=250,
        title="Books Read per Month",
        dark_theme=True)

    fig.update_layout(paper_bgcolor="#0e1117", font_size=14,
                      margin=dict(t=90))
    fig2.update_layout(paper_bgcolor="#0e1117",
                       font_size=14, margin=dict(t=90))
    fig3.update_layout(paper_bgcolor="#0e1117",
                       font_size=14, margin=dict(t=90))
    with st.container():
        st.title("Book Stats")
        st.plotly_chart(fig, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)

        df = create_df()
        chart_data = (
            pd.to_datetime(df['last date read'])
            .dt.year
            .value_counts()
            .rename("amount")
            .sort_index()
            #   .plot.bar()
        )
        st.write('Books read by month')
        st.bar_chart(chart_data)


if selected == "Books Read":
    books_read()
else:
    book_stats()
