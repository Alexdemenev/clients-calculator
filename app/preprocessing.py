import pandas as pd
import numpy as np


def preprocessing_data(df, date_col="date", client_id_col="client_id"):
    """
    Preprocess the data to create a time series of clients.
    """

    df[date_col] = pd.to_datetime(df[date_col])
    df["year_month"] = df[date_col].dt.to_period("M")

    # Create a time series of periods
    periods = pd.date_range(
        start=df[date_col].min(), end=df[date_col].max(), freq="M"
    ).to_period("M")
    periods = periods.to_frame(index=False)
    periods.columns = ["year_month"]

    # Group by year_month and create a time series of clients
    df_grouped = (
        df.groupby("year_month", as_index=False)
        .agg(clients=(client_id_col, set))
        .sort_values("year_month", ascending=True)
    )
    df_grouped = periods.merge(df_grouped, on="year_month", how="left")
    df_grouped["clients_count"] = df_grouped["clients"].apply(len)
    df_grouped["clients_prev"] = df_grouped["clients"].shift(1, fill_value=set())
    df_grouped["clients_prev"] = df_grouped["clients_prev"].bfill()
    df_grouped["clients_prev_year"] = df_grouped["clients"].shift(12, fill_value=set())
    df_grouped["clients_prev_year"] = df_grouped["clients_prev_year"].bfill()

    return df_grouped
