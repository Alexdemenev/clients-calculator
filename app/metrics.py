from app.utils import clients_intersection_vectorized, clients_intersection, clients_new_vectorized, clients_new


def calculate_metrics(df_grouped):
    """
    Calculate the metrics for the data.
    """

    df_grouped["clients_intersection"] = clients_intersection_vectorized(
        df_grouped["clients_prev"], df_grouped["clients"]
    )
    df_grouped["clients_new"] = clients_new_vectorized(
        df_grouped["clients_prev"], df_grouped["clients"]
    )

    df_grouped["growth_rate_month"] = df_grouped["clients_new"] / df_grouped[
        "clients_prev"
    ].apply(len)
    df_grouped["retention_month"] = df_grouped["clients_intersection"] / df_grouped[
        "clients_prev"
    ].apply(len)
    df_grouped["churn_month"] = 1 - df_grouped["retention_month"]

    df_grouped["clients_intersection_year"] = clients_intersection_vectorized(
        df_grouped["clients_prev_year"], df_grouped["clients"]
    )
    df_grouped["clients_new_year"] = clients_new_vectorized(
        df_grouped["clients_prev_year"], df_grouped["clients"]
    )
    df_grouped["growth_rate_year"] = df_grouped["clients_new_year"] / df_grouped[
        "clients_prev_year"
    ].apply(len)
    df_grouped["retention_year"] = df_grouped["clients_intersection_year"] / df_grouped[
        "clients_prev_year"
    ].apply(len)
    df_grouped["churn_year"] = 1 - df_grouped["retention_year"]
    
    retention_period = clients_intersection(df_grouped[df_grouped['year_month'] == df_grouped['year_month'].max()]["clients"].values[0], df_grouped[df_grouped['year_month'] == df_grouped['year_month'].min()]["clients"].values[0]) / df_grouped[df_grouped['year_month'] == df_grouped['year_month'].min()]["clients"].apply(len)
    df_grouped['retention_period'] = retention_period

    new_clients_period = clients_new(df_grouped[df_grouped['year_month'] == df_grouped['year_month'].max()]["clients"].values[0], df_grouped[df_grouped['year_month'] == df_grouped['year_month'].min()]["clients"].values[0]) / df_grouped[df_grouped['year_month'] == df_grouped['year_month'].min()]["clients"].apply(len)
    df_grouped['new_clients_period'] = new_clients_period
    
    return df_grouped