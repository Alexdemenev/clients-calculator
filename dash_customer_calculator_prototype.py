# dash_customer_calculator_prototype.py
# Prototype Dash app: "Калькулятор клиентов" (Customer Calculator)
# Requirements: dash, pandas, numpy, plotly
# Install: pip install dash pandas numpy plotly

import io
import base64
from datetime import datetime
import pandas as pd
import numpy as np
from math import prod

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go

# -----------------------------
# Helper functions
# -----------------------------


def parse_contents(contents, filename):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif filename.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None
    except Exception as e:
        print(e)
        return None
    return df


def prepare_timeseries(df, date_col="date", value_col="active_customers"):
    # Expect monthly data or daily; we'll resample to month start
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    ts = df.set_index(date_col)[value_col].resample("MS").sum().ffill()
    ts = ts.rename("active_customers")
    return ts


def compute_metrics(ts):
    # ts: pd.Series indexed by month start
    # monthly change = (prev - curr)/prev when prev>0
    prev = ts.shift(1)
    raw_change = (ts - prev) / prev.replace({0: np.nan})
    # churn when change < 0 : churn rate positive
    monthly_churn = (-raw_change.clip(upper=0)).fillna(0)
    monthly_growth = raw_change.clip(lower=0).fillna(0)

    avg_monthly_churn = monthly_churn.mean()
    # annual churn (approx) = 1 - product(1 - monthly_churn for months in last 12)
    months = monthly_churn.dropna()
    if len(months) >= 12:
        window = months[-12:]
    else:
        window = months
    annual_churn = 1 - prod((1 - window).values) if len(window) > 0 else np.nan

    # survival over year = 1 - annual_churn
    survival_year = 1 - annual_churn if not np.isnan(annual_churn) else np.nan
    # survival over entire period
    survival_period = (
        prod((1 - monthly_churn).values) if len(monthly_churn) > 0 else np.nan
    )

    # monthly/yearly growth: average positive change
    avg_monthly_growth = monthly_growth.mean()
    # approximate annual growth = (prod(1 + monthly_growth_last12) -1)
    if len(monthly_growth.dropna()) >= 12:
        mg = monthly_growth.dropna()[-12:]
    else:
        mg = monthly_growth.dropna()
    annual_growth = prod((1 + mg).values) - 1 if len(mg) > 0 else np.nan

    metrics = {
        "avg_monthly_churn": float(avg_monthly_churn),
        "avg_yearly_churn": float(annual_churn) if not np.isnan(annual_churn) else None,
        "survival_year": float(survival_year) if not np.isnan(survival_year) else None,
        "survival_period": (
            float(survival_period) if not np.isnan(survival_period) else None
        ),
        "avg_monthly_growth": float(avg_monthly_growth),
        "annual_growth": float(annual_growth) if not np.isnan(annual_growth) else None,
        "monthly_churn_series": monthly_churn,
        "monthly_growth_series": monthly_growth,
        "timeseries": ts,
    }
    return metrics


def extrapolate_series(ts, months_forward=12, degree=1):
    # Simple polynomial fit (degree 1 = linear) on monthly index
    if len(ts) < 3:
        return None
    x = np.arange(len(ts))
    y = ts.values
    coeffs = np.polyfit(x, y, degree)
    poly = np.poly1d(coeffs)
    x_future = np.arange(len(ts) + months_forward)
    y_future = poly(x_future)
    idx = pd.date_range(ts.index[0], periods=len(x_future), freq="MS")
    return pd.Series(y_future, index=idx)


# -----------------------------
# Sample data generator
# -----------------------------


def sample_data(months=36, start_customers=1000, churn_rate=0.02, seasonality=0.03):
    # Simple synthetic monthly series
    rng = pd.date_range(end=pd.Timestamp.today(), periods=months, freq="MS")
    vals = []
    cur = start_customers
    for i in range(months):
        # seasonal variation
        seasonal = 1 + seasonality * np.sin(2 * np.pi * i / 12)
        # random noise
        noise = np.random.normal(0, cur * 0.01)
        # churn and growth
        churn = cur * churn_rate
        growth = cur * (0.005 if i % 6 == 0 else 0.01)  # occasional growth
        cur = max(1, cur - churn + growth)
        vals.append(cur * seasonal + noise)
    df = pd.DataFrame({"date": rng, "active_customers": np.round(vals).astype(int)})
    return df


# -----------------------------
# Dash App
# -----------------------------

app = dash.Dash(__name__, title="Калькулятор клиентов — Prototype")
server = app.server

app.layout = html.Div(
    [
        html.H2("Калькулятор клиентов — Prototype", style={"textAlign": "center"}),
        html.Div(
            [
                html.Div(
                    [
                        html.H4(
                            "1) Загрузите CSV (обязательные колонки: date, active_customers) или используйте пример"
                        ),
                        dcc.Upload(
                            id="upload-data",
                            children=html.Div(
                                ["Перетащите файл сюда или нажмите чтобы выбрать"],
                                style={
                                    "whiteSpace": "normal",
                                    "overflowWrap": "anywhere",
                                    "wordBreak": "break-word",
                                    "lineHeight": "1.2",
                                    "padding": "0 8px",
                                },
                            ),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "1px",
                                "textAlign": "center",
                                "marginBottom": "5px",
                            },
                            multiple=False,
                        ),
                        html.Button(
                            "Загрузить пример данных", id="sample-btn", n_clicks=0
                        ),
                        html.Div(id="file-info", style={"marginTop": "8px"}),
                    ],
                    style={
                        "width": "33%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                        "padding": 10,
                    },
                ),
                html.Div(
                    [
                        html.H4("2) Настройки прогноза"),
                        html.Label("Месяцев вперед (экстраполяция)"),
                        dcc.Input(
                            id="months-forward", type="number", value=12, min=1, step=1
                        ),
                        html.Br(),
                        html.Br(),
                        html.Label("Степень полинома (1 — линейная)"),
                        dcc.Input(
                            id="poly-degree",
                            type="number",
                            value=1,
                            min=1,
                            max=3,
                            step=1,
                        ),
                        html.Br(),
                        html.Br(),
                        html.Button("Сгенерировать отчёт (CSV)", id="download-btn"),
                        dcc.Download(id="download-report"),
                    ],
                    style={
                        "width": "33%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                        "padding": 10,
                    },
                ),
                html.Div(
                    [html.H4("3) Быстрые метрики"), html.Div(id="metrics-output")],
                    style={
                        "width": "33%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                        "padding": 10,
                    },
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between"},
        ),
        html.Hr(),
        dcc.Tabs(
            id="tabs",
            value="tab-1",
            children=[
                dcc.Tab(label="Динамика показателей и прогноз", value="tab-1"),
                dcc.Tab(label="Отток и прирост (по месяцам)", value="tab-2"),
            ],
        ),
        html.Div(id="tabs-content"),
        # Hidden store for parsed data
        dcc.Store(id="timeseries-store"),
    ],
    style={"maxWidth": 1200, "margin": "0 auto", "fontFamily": "Arial, sans-serif"},
)


# -----------------------------
# Callbacks
# -----------------------------


@app.callback(
    Output("timeseries-store", "data"),
    Output("file-info", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    Input("sample-btn", "n_clicks"),
)
def handle_upload(contents, filename, sample_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "sample-btn":
        df = sample_data()
        ts = prepare_timeseries(df)
        return (
            ts.reset_index()
            .rename(columns={"index": "date"})
            .to_json(date_format="iso"),
            "Используются примерные данные (сгенерированы)",
        )

    if contents is None:
        raise dash.exceptions.PreventUpdate
    df = parse_contents(contents, filename)
    if df is None:
        return (
            dash.no_update,
            "Не удалось прочитать файл. Ожидается CSV с колонками date и active_customers.",
        )
    # try to find columns
    possible_date = None
    possible_val = None
    for c in df.columns:
        if c.lower() in ("date", "дата"):
            possible_date = c
        if c.lower() in (
            "active_customers",
            "customers",
            "clients",
            "значение",
            "value",
        ):
            possible_val = c
    if possible_date is None or possible_val is None:
        # try assume first two cols
        possible_date, possible_val = df.columns[0], df.columns[1]
    df2 = df[[possible_date, possible_val]].rename(
        columns={possible_date: "date", possible_val: "active_customers"}
    )
    ts = prepare_timeseries(df2)
    info = f'Файл: {filename}. Диапазон: {ts.index.min().strftime("%Y-%m")} — {ts.index.max().strftime("%Y-%m")}, точек: {len(ts)}'
    return (
        ts.reset_index().rename(columns={"index": "date"}).to_json(date_format="iso"),
        info,
    )


@app.callback(Output("metrics-output", "children"), Input("timeseries-store", "data"))
def update_metrics(data_json):
    if not data_json:
        return "Нет данных — загрузите CSV или используйте пример."
    ts_df = pd.read_json(data_json)
    ts_df["date"] = pd.to_datetime(ts_df["date"])
    ts = ts_df.set_index("date")["active_customers"]
    metrics = compute_metrics(ts)
    # present
    items = [
        html.Div(f'Средний месячный отток: {metrics["avg_monthly_churn"]:.2%}'),
        html.Div(
            f'Примерный годовой отток: {metrics["avg_yearly_churn"]:.2%}'
            if metrics["avg_yearly_churn"] is not None
            else "Примерный годовой отток: нет данных"
        ),
        html.Div(
            f'Выживаемость за год: {metrics["survival_year"]:.2%}'
            if metrics["survival_year"] is not None
            else "Выживаемость за год: нет данных"
        ),
        html.Div(
            f'Выживаемость за весь период: {metrics["survival_period"]:.2%}'
            if metrics["survival_period"] is not None
            else "Выживаемость за период: нет данных"
        ),
        html.Div(f'Средний месячный прирост: {metrics["avg_monthly_growth"]:.2%}'),
        html.Div(
            f'Примерный годовой прирост: {metrics["annual_growth"]:.2%}'
            if metrics["annual_growth"] is not None
            else "Примерный годовой прирост: нет данных"
        ),
    ]
    return html.Div(items)


@app.callback(
    Output("tabs-content", "children"),
    Input("tabs", "value"),
    Input("timeseries-store", "data"),
    Input("months-forward", "value"),
    Input("poly-degree", "value"),
)
def render_tab(tab, data_json, months_forward, poly_degree):
    if not data_json:
        return html.Div("Нет данных — загрузите CSV или используйте пример.")
    ts_df = pd.read_json(data_json)
    ts_df["date"] = pd.to_datetime(ts_df["date"])
    ts = ts_df.set_index("date")["active_customers"]
    metrics = compute_metrics(ts)

    # extrapolate timeseries
    ts_ext = extrapolate_series(ts, months_forward, degree=poly_degree)

    if tab == "tab-1":
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=ts.index, y=ts.values, mode="lines+markers", name="Actual")
        )
        if ts_ext is not None:
            fig.add_trace(
                go.Scatter(
                    x=ts_ext.index,
                    y=ts_ext.values,
                    mode="lines",
                    name="Extrapolated",
                    line={"dash": "dash"},
                )
            )
        fig.update_layout(
            title="Активные клиенты — фактические и прогноз",
            xaxis_title="Дата",
            yaxis_title="Активные клиенты",
        )
        return html.Div([dcc.Graph(figure=fig)])

    if tab == "tab-2":
        churn = metrics["monthly_churn_series"]
        growth = metrics["monthly_growth_series"]
        # align indexes
        dfc = pd.DataFrame({"churn": churn, "growth": growth}).fillna(0)
        # extrapolate churn/growth via polyfit on last 12 months values
        try:
            churn_ext = extrapolate_series(
                dfc["churn"], months_forward, degree=poly_degree
            )
            growth_ext = extrapolate_series(
                dfc["growth"], months_forward, degree=poly_degree
            )
        except Exception:
            churn_ext = None
            growth_ext = None

        fig = go.Figure()
        fig.add_trace(go.Bar(x=dfc.index, y=dfc["churn"], name="Отток (месяц)"))
        if churn_ext is not None:
            fig.add_trace(
                go.Scatter(
                    x=churn_ext.index,
                    y=churn_ext.values,
                    mode="lines",
                    name="Отток — прогноз",
                )
            )
        fig.update_layout(
            title="Динамика оттока по месяцам",
            xaxis_title="Дата",
            yaxis_title="Доля оттока",
        )

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=dfc.index, y=dfc["growth"], name="Прирост (месяц)"))
        if growth_ext is not None:
            fig2.add_trace(
                go.Scatter(
                    x=growth_ext.index,
                    y=growth_ext.values,
                    mode="lines",
                    name="Прирост — прогноз",
                )
            )
        fig2.update_layout(
            title="Динамика прироста по месяцам",
            xaxis_title="Дата",
            yaxis_title="Доля прироста",
        )

        return html.Div([dcc.Graph(figure=fig), dcc.Graph(figure=fig2)])


@app.callback(
    Output("download-report", "data"),
    Input("download-btn", "n_clicks"),
    State("timeseries-store", "data"),
    State("months-forward", "value"),
    State("poly-degree", "value"),
)
def create_report(n, data_json, months_forward, poly_degree):
    if not n:
        raise dash.exceptions.PreventUpdate
    if not data_json:
        return dash.no_update
    ts_df = pd.read_json(data_json)
    ts_df["date"] = pd.to_datetime(ts_df["date"])
    ts = ts_df.set_index("date")["active_customers"]
    metrics = compute_metrics(ts)
    ts_ext = extrapolate_series(ts, months_forward, degree=poly_degree)

    report = {
        "metrics": {
            k: v
            for k, v in metrics.items()
            if not k.endswith("_series") and k != "timeseries"
        },
        "timeseries": ts.reset_index().to_dict(orient="records"),
    }
    if ts_ext is not None:
        report["extrapolated"] = (
            ts_ext.reset_index()
            .rename(columns={"index": "date", 0: "value"})
            .to_dict(orient="records")
        )

    csv_buf = io.StringIO()
    # Save metrics + timeseries as two CSV parts separated by blank line
    mdf = pd.DataFrame([report["metrics"]])
    mdf.to_csv(csv_buf, index=False)
    csv_buf.write("\n")
    tdf = pd.DataFrame(report["timeseries"]).rename(
        columns={"active_customers": "value"}
    )
    tdf.to_csv(csv_buf, index=False)
    csv_buf.seek(0)
    return dict(content=csv_buf.getvalue(), filename="customer_calculator_report.csv")


if __name__ == "__main__":
    app.run(debug=True, port=8050)
