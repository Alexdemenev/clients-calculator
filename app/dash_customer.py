from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    State,
    callback,
    ctx,
    ALL,
    MATCH,
    no_update,
)
import dash_ag_grid as dag

import base64
import datetime
import io

import pandas as pd
import numpy as np
import plotly.graph_objs as go

# Импорты для препроцессинга и расчета метрик
from app.preprocessing import preprocessing_data
from app.metrics import calculate_metrics
from app.auth import validate_session, get_session_username, cleanup_expired_sessions

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = Dash(
    __name__, title="Калькулятор клиентов", external_stylesheets=external_stylesheets
)


# Добавляем middleware для проверки авторизации
@app.server.before_request
def check_authentication():
    """Проверяет авторизацию перед каждым запросом"""
    from flask import request, redirect, url_for

    # Очищаем истекшие сессии
    cleanup_expired_sessions()

    # Разрешаем доступ к статическим файлам
    if request.path.startswith("/_dash") or request.path.startswith("/assets"):
        return None

    # Получаем токен из cookies или query параметров
    session_token = request.cookies.get("session_token") or request.args.get("token")

    # Проверяем валидность токена
    if not validate_session(session_token):
        # Если токен невалиден, перенаправляем на страницу авторизации
        return redirect("http://localhost:8501")

    return None


# Функция для получения информации о пользователе
def get_user_info():
    """Получает информацию о текущем пользователе"""
    from flask import request

    session_token = request.cookies.get("session_token") or request.args.get("token")
    if session_token and validate_session(session_token):
        username = get_session_username(session_token)
        return username
    return None


app.layout = html.Div(
    [
        html.Div(
            [
                html.H2(
                    "Калькулятор клиентов", style={"textAlign": "center", "margin": "0"}
                ),
                html.Div(
                    id="user-info",
                    style={
                        "position": "absolute",
                        "top": "10px",
                        "right": "10px",
                        "fontSize": "14px",
                        "color": "#666",
                    },
                ),
            ],
            style={"position": "relative", "marginBottom": "20px"},
        ),
        dcc.Upload(
            id="upload-data",
            children=html.Div(
                [
                    "Перетащите файл сюда или нажмите, чтобы ",
                    html.A("Выбрать файл"),
                    html.Br(),
                    "Размер файла не должен превышать 100MB",
                ],
                style={
                    "whiteSpace": "normal",
                    "overflowWrap": "break-word",
                    "wordBreak": "break-word",
                    "padding": "0 10px",
                    "lineHeight": "1.4",
                },
            ),
            style={
                "width": "100%",
                "minHeight": "60px",
                "height": "auto",
                "lineHeight": "normal",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
                "padding": "10px",
                "boxSizing": "border-box",
                "overflow": "hidden",
            },
            # Allow multiple files to be uploaded
            multiple=True,
        ),
        # Индикатор загрузки для загрузки файлов
        dcc.Loading(
            id="loading-upload",
            type="default",
            children=html.Div(id="output-data-upload"),
            style={"minHeight": "100px"},
        ),
        # Store для хранения загруженных данных
        dcc.Store(id="uploaded-data-store"),
        # Блок для вывода результатов метрик
        html.Div(id="metrics-output", style={"margin": "20px", "padding": "10px"}),
    ]
)


def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(",")

    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif "xls" in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div(["There was an error processing this file."])

    return html.Div(
        [
            html.H5(filename),
            html.H6(datetime.datetime.fromtimestamp(date)),
            dag.AgGrid(
                rowData=df.to_dict("records"),
                columnDefs=[{"field": i} for i in df.columns],
            ),
            html.Br(),
            html.Div(
                [
                    html.Label(
                        "Название колонки с датой:",
                        style={"marginRight": "10px", "fontWeight": "bold"},
                    ),
                    dcc.Input(
                        id={"type": "date-col-input", "index": filename},
                        type="text",
                        placeholder="date",
                        value="date",
                        style={
                            "width": "200px",
                            "marginRight": "20px",
                            "padding": "5px",
                        },
                    ),
                    html.Label(
                        "Название колонки с client_id:",
                        style={"marginRight": "10px", "fontWeight": "bold"},
                    ),
                    dcc.Input(
                        id={"type": "client-id-col-input", "index": filename},
                        type="text",
                        placeholder="client_id",
                        value="client_id",
                        style={
                            "width": "200px",
                            "marginRight": "20px",
                            "padding": "5px",
                        },
                    ),
                ],
                style={
                    "marginTop": "10px",
                    "marginBottom": "10px",
                    "display": "flex",
                    "alignItems": "center",
                    "flexWrap": "wrap",
                },
            ),
            html.Button(
                "Запустить препроцессинг и расчет метрик",
                id={"type": "process-btn", "index": filename},
                n_clicks=0,
                style={
                    "marginTop": "10px",
                    "padding": "10px 20px",
                    "fontSize": "16px",
                    "cursor": "pointer",
                    "textAlign": "center",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
            ),
            # Индикатор загрузки для обработки данных
            dcc.Loading(
                id={"type": "loading-processing", "index": filename},
                type="circle",
                children=html.Div(
                    id={"type": "processing-status", "index": filename},
                    style={"marginTop": "10px"},
                ),
            ),
            # Store для хранения метрик для этого файла
            dcc.Store(id={"type": "metrics-store", "index": filename}),
            html.Br(),
            # Блок с кнопкой и полем выбора периода (изначально скрыт)
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(
                                "Период экстраполяции (месяцев):",
                                style={"marginRight": "10px", "fontWeight": "bold"},
                            ),
                            dcc.Input(
                                id={"type": "extrapolation-months", "index": filename},
                                type="number",
                                min=1,
                                max=12,
                                value=12,
                                style={
                                    "width": "100px",
                                    "marginRight": "20px",
                                    "padding": "5px",
                                },
                            ),
                        ],
                        style={
                            "marginTop": "10px",
                            "marginBottom": "10px",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                    html.Button(
                        "Создать графики метрик и прогноза",
                        id={"type": "plot-btn", "index": filename},
                        n_clicks=0,
                        style={
                            "marginTop": "10px",
                            "padding": "10px 20px",
                            "fontSize": "16px",
                            "cursor": "pointer",
                            "textAlign": "center",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                    ),
                ],
                id={"type": "plots-controls", "index": filename},
                style={"display": "none"},  # Изначально скрыт
            ),
            # Индикатор загрузки для графиков
            dcc.Loading(
                id={"type": "loading-plots", "index": filename},
                type="circle",
                children=html.Div(
                    id={"type": "plots-output", "index": filename},
                    style={"marginTop": "10px"},
                ),
            ),
        ]
    )


@callback(
    Output("output-data-upload", "children"),
    Output("uploaded-data-store", "data"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("upload-data", "last_modified"),
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = []
        all_data = {}
        for c, n, d in zip(list_of_contents, list_of_names, list_of_dates):
            content_type, content_string = c.split(",")
            decoded = base64.b64decode(content_string)
            try:
                if "csv" in n:
                    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
                elif "xls" in n:
                    df = pd.read_excel(io.BytesIO(decoded))
                else:
                    continue
                # Сохраняем данные в store
                all_data[n] = df.to_dict("records")
            except Exception:
                continue
            children.append(parse_contents(c, n, d))
        return children, all_data
    return None, None


def extrapolate_series(ts, months_forward=12, degree=1):
    """Экстраполяция временного ряда с помощью полиномиальной аппроксимации"""
    if len(ts) < 3:
        return None

    # Убеждаемся, что индекс это DatetimeIndex
    if not isinstance(ts.index, pd.DatetimeIndex):
        # Если это не DatetimeIndex, пытаемся преобразовать
        if hasattr(ts.index, "to_timestamp"):
            ts_index = ts.index.to_timestamp()
        else:
            ts_index = pd.to_datetime(ts.index)
        ts = pd.Series(ts.values, index=ts_index)

    x = np.arange(len(ts))
    y = ts.values
    coeffs = np.polyfit(x, y, degree)
    poly = np.poly1d(coeffs)
    x_future = np.arange(len(ts) + months_forward)
    y_future = poly(x_future)

    # Создаем DatetimeIndex для прогноза
    start_date = ts.index[0]
    if isinstance(start_date, pd.Timestamp):
        idx = pd.date_range(start_date, periods=len(x_future), freq="MS")
    else:
        # Если это не Timestamp, преобразуем
        start_date = pd.to_datetime(start_date)
        idx = pd.date_range(start_date, periods=len(x_future), freq="MS")

    return pd.Series(y_future, index=idx)


@callback(
    Output({"type": "processing-status", "index": MATCH}, "children"),
    Output({"type": "metrics-store", "index": MATCH}, "data"),
    Input({"type": "process-btn", "index": MATCH}, "n_clicks"),
    State("uploaded-data-store", "data"),
    State({"type": "process-btn", "index": MATCH}, "id"),
    State({"type": "date-col-input", "index": MATCH}, "value"),
    State({"type": "client-id-col-input", "index": MATCH}, "value"),
    prevent_initial_call=True,
)
def process_data(n_clicks, stored_data, button_id, date_col, client_id_col):
    if n_clicks is None or n_clicks == 0:
        return "", no_update

    if stored_data is None:
        return (
            html.Div("Ошибка: данные не найдены", style={"color": "red"}),
            no_update,
        )

    filename = button_id.get("index") if isinstance(button_id, dict) else None
    if not filename or filename not in stored_data:
        return (
            html.Div(
                "Ошибка: данные для этого файла не найдены", style={"color": "red"}
            ),
            no_update,
        )

    try:
        # Восстанавливаем DataFrame из словаря
        df = pd.DataFrame(stored_data[filename])

        # Проверяем, что указанные колонки существуют
        date_col = date_col.strip() if date_col else "date"
        client_id_col = client_id_col.strip() if client_id_col else "client_id"

        if date_col not in df.columns:
            return html.Div(
                f"Ошибка: колонка '{date_col}' не найдена в данных. Доступные колонки: {', '.join(df.columns)}",
                style={"color": "red", "marginTop": "10px"},
            )

        if client_id_col not in df.columns:
            return html.Div(
                f"Ошибка: колонка '{client_id_col}' не найдена в данных. Доступные колонки: {', '.join(df.columns)}",
                style={"color": "red", "marginTop": "10px"},
            )

        # Препроцессинг и расчет метрик с указанными названиями колонок
        df_preprocessed = preprocessing_data(
            df, date_col=date_col, client_id_col=client_id_col
        )
        df_metrics = calculate_metrics(df_preprocessed)

        items = [
            html.Div(f'Средний месячный отток: {df_metrics["churn_month"].mean():.2%}'),
            html.Div(f'Примерный годовой отток: {df_metrics["churn_year"].mean():.2%}'),
            html.Div(f'Выживаемость за год: {df_metrics["retention_year"].mean():.2%}'),
            html.Div(
                f'Выживаемость за весь период: {df_metrics["retention_period"].mean():.2%}'
            ),
            html.Div(
                f'Новые клиенты за период: {df_metrics["new_clients_period"].mean():.2%}'
            ),
            html.Div(
                f'Средний месячный прирост: {df_metrics[df_metrics["growth_rate_month"] < np.inf]["growth_rate_month"].mean():.2%}'
            ),
            html.Div(
                f'Примерный годовой прирост: {df_metrics[df_metrics["growth_rate_year"] < np.inf]["growth_rate_year"].mean():.2%}'
            ),
        ]

        # Сохраняем метрики в Store для использования в графиках
        # Преобразуем Period в строку для сериализации
        df_metrics_clean = df_metrics.copy()
        if "year_month" in df_metrics_clean.columns:
            df_metrics_clean["year_month"] = df_metrics_clean["year_month"].astype(str)
        # Преобразуем множества в списки
        for col in ["clients", "clients_prev", "clients_prev_year"]:
            if col in df_metrics_clean.columns:
                df_metrics_clean[col] = df_metrics_clean[col].apply(
                    lambda x: list(x) if isinstance(x, set) else []
                )

        metrics_data = {
            filename: df_metrics_clean.to_dict("records"),
            f"{filename}_year_month": df_metrics["year_month"].astype(str).tolist(),
        }

        return html.Div(items), metrics_data
    except Exception as e:
        return (
            html.Div(
                f"Ошибка при обработке: {str(e)}",
                style={"color": "red", "marginTop": "10px"},
            ),
            no_update,
        )


@callback(
    Output({"type": "plots-controls", "index": MATCH}, "style"),
    Input({"type": "metrics-store", "index": MATCH}, "data"),
    prevent_initial_call=False,
)
def show_plots_controls(metrics_data):
    """Показывает блок с кнопкой и полем выбора периода после успешного препроцессинга"""
    if (
        metrics_data is not None
        and isinstance(metrics_data, dict)
        and len(metrics_data) > 0
    ):
        return {"display": "block"}
    return {"display": "none"}


@callback(
    Output({"type": "plots-output", "index": MATCH}, "children"),
    Input({"type": "plot-btn", "index": MATCH}, "n_clicks"),
    State({"type": "metrics-store", "index": MATCH}, "data"),
    State({"type": "plot-btn", "index": MATCH}, "id"),
    State({"type": "extrapolation-months", "index": MATCH}, "value"),
    prevent_initial_call=True,
)
def create_plots(n_clicks, metrics_data, button_id, months_forward):
    if n_clicks is None or n_clicks == 0:
        return ""

    if metrics_data is None:
        return html.Div(
            "Ошибка: метрики не найдены. Сначала запустите препроцессинг и расчет метрик.",
            style={"color": "red"},
        )

    try:
        # metrics_data теперь содержит данные напрямую для этого файла
        # Структура: {filename: records, f"{filename}_year_month": periods}
        filename = button_id.get("index") if isinstance(button_id, dict) else None

        if not filename or not isinstance(metrics_data, dict):
            return html.Div(
                "Ошибка: метрики для этого файла не найдены", style={"color": "red"}
            )

        # Восстанавливаем DataFrame из словаря
        if filename in metrics_data:
            df_metrics = pd.DataFrame(metrics_data[filename])
        else:
            return html.Div(
                "Ошибка: метрики для этого файла не найдены", style={"color": "red"}
            )

        # Восстанавливаем year_month из Period строк
        year_month_key = f"{filename}_year_month"
        if year_month_key in metrics_data:
            df_metrics["year_month"] = pd.PeriodIndex(
                metrics_data[year_month_key], freq="M"
            )
        else:
            # Если нет, пытаемся восстановить из строк
            if "year_month" in df_metrics.columns:
                df_metrics["year_month"] = pd.PeriodIndex(
                    df_metrics["year_month"].astype(str), freq="M"
                )
            else:
                return html.Div(
                    "Ошибка: не найдена колонка year_month в метриках",
                    style={"color": "red"},
                )

        # Преобразуем Period в дату для графиков
        # Убеждаемся, что dates это DatetimeIndex
        if isinstance(df_metrics["year_month"].iloc[0], pd.Period):
            dates = df_metrics["year_month"].dt.to_timestamp()
        else:
            dates = pd.to_datetime(df_metrics["year_month"].astype(str))

        # Преобразуем в DatetimeIndex, если это еще не индекс
        if not isinstance(dates, pd.DatetimeIndex):
            dates = pd.DatetimeIndex(dates)

        # Получаем данные для графиков
        churn_month = df_metrics["churn_month"].fillna(0)
        growth_rate_month = (
            df_metrics["growth_rate_month"].replace([np.inf, -np.inf], np.nan).fillna(0)
        )

        # Устанавливаем период экстраполяции
        months_forward = int(months_forward) if months_forward else 12
        months_forward = max(1, min(12, months_forward))  # Ограничиваем от 1 до 12

        # Создаем временные ряды для экстраполяции с DatetimeIndex
        churn_ts = pd.Series(churn_month.values, index=dates)
        growth_ts = pd.Series(growth_rate_month.values, index=dates)

        # Экстраполяция
        churn_ext = extrapolate_series(
            churn_ts, months_forward=months_forward, degree=1
        )
        growth_ext = extrapolate_series(
            growth_ts, months_forward=months_forward, degree=1
        )

        # Линии тренда для фактических данных
        # Линейная регрессия для тренда
        x_trend = np.arange(len(churn_ts))
        churn_trend_coeffs = np.polyfit(x_trend, churn_ts.values, 1)
        churn_trend = np.poly1d(churn_trend_coeffs)
        churn_trend_values = churn_trend(x_trend)

        growth_trend_coeffs = np.polyfit(x_trend, growth_ts.values, 1)
        growth_trend = np.poly1d(growth_trend_coeffs)
        growth_trend_values = growth_trend(x_trend)

        # График 1: Отток
        fig_churn = go.Figure()
        fig_churn.add_trace(
            go.Scatter(
                x=dates,
                y=churn_month,
                mode="lines+markers",
                name="Отток (факт)",
                line=dict(color="red", width=2),
            )
        )
        fig_churn.add_trace(
            go.Scatter(
                x=dates,
                y=churn_trend_values,
                mode="lines",
                name="Тренд оттока",
                line=dict(color="red", width=2, dash="dash"),
            )
        )
        fig_churn.update_layout(
            title="График оттока",
            xaxis_title="Дата",
            yaxis_title="Доля оттока",
            hovermode="x unified",
        )

        # График 2: Приток
        fig_growth = go.Figure()
        fig_growth.add_trace(
            go.Scatter(
                x=dates,
                y=growth_rate_month,
                mode="lines+markers",
                name="Приток (факт)",
                line=dict(color="green", width=2),
            )
        )
        fig_growth.add_trace(
            go.Scatter(
                x=dates,
                y=growth_trend_values,
                mode="lines",
                name="Тренд притока",
                line=dict(color="green", width=2, dash="dash"),
            )
        )
        fig_growth.update_layout(
            title="График притока",
            xaxis_title="Дата",
            yaxis_title="Доля притока",
            hovermode="x unified",
        )

        # График 3: Прогноз оттока
        fig_churn_forecast = go.Figure()
        fig_churn_forecast.add_trace(
            go.Scatter(
                x=dates,
                y=churn_month,
                mode="lines+markers",
                name="Отток (факт)",
                line=dict(color="red", width=2),
            )
        )
        if churn_ext is not None:
            # Разделяем фактические и прогнозные данные
            # Прогнозные данные начинаются после последней фактической даты
            last_actual_idx = len(dates)
            forecast_dates = churn_ext.index[last_actual_idx:]
            forecast_values = churn_ext.values[last_actual_idx:]
            # Добавляем последнюю фактическую точку для плавного перехода
            if len(forecast_dates) > 0:
                fig_churn_forecast.add_trace(
                    go.Scatter(
                        x=[dates[-1]] + list(forecast_dates),
                        y=[churn_month.iloc[-1]] + list(forecast_values),
                        mode="lines",
                        name=f"Прогноз оттока ({months_forward} мес.)",
                        line=dict(color="orange", width=2, dash="dot"),
                    )
                )
        fig_churn_forecast.update_layout(
            title=f"График прогноза оттока (экстраполяция {months_forward} мес.)",
            xaxis_title="Дата",
            yaxis_title="Доля оттока",
            hovermode="x unified",
        )

        # График 4: Прогноз притока
        fig_growth_forecast = go.Figure()
        fig_growth_forecast.add_trace(
            go.Scatter(
                x=dates,
                y=growth_rate_month,
                mode="lines+markers",
                name="Приток (факт)",
                line=dict(color="green", width=2),
            )
        )
        if growth_ext is not None:
            # Разделяем фактические и прогнозные данные
            # Прогнозные данные начинаются после последней фактической даты
            last_actual_idx = len(dates)
            forecast_dates = growth_ext.index[last_actual_idx:]
            forecast_values = growth_ext.values[last_actual_idx:]
            # Добавляем последнюю фактическую точку для плавного перехода
            if len(forecast_dates) > 0:
                fig_growth_forecast.add_trace(
                    go.Scatter(
                        x=[dates[-1]] + list(forecast_dates),
                        y=[growth_rate_month.iloc[-1]] + list(forecast_values),
                        mode="lines",
                        name=f"Прогноз притока ({months_forward} мес.)",
                        line=dict(color="blue", width=2, dash="dot"),
                    )
                )
        fig_growth_forecast.update_layout(
            title=f"График прогноза притока (экстраполяция {months_forward} мес.)",
            xaxis_title="Дата",
            yaxis_title="Доля притока",
            hovermode="x unified",
        )

        return html.Div(
            [
                html.H4("Графики метрик и прогноза", style={"marginTop": "20px"}),
                dcc.Graph(figure=fig_churn),
                dcc.Graph(figure=fig_growth),
                dcc.Graph(figure=fig_churn_forecast),
                dcc.Graph(figure=fig_growth_forecast),
            ]
        )
    except Exception as e:
        return html.Div(
            f"Ошибка при создании графиков: {str(e)}",
            style={"color": "red", "marginTop": "10px"},
        )


# Callback для отображения информации о пользователе
@app.callback(
    Output("user-info", "children"),
    Input("output-data-upload", "children"),  # Триггер при загрузке страницы
    prevent_initial_call=False,
)
def update_user_info(_):
    """Обновляет информацию о пользователе"""
    username = get_user_info()
    if username:
        return html.Div(f"👤 {username}")
    return ""


if __name__ == "__main__":
    app.run(debug=True, port=8050)
