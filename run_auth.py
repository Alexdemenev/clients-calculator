"""
Запуск приложений с авторизацией
"""

import subprocess
import sys
import time
import threading
import os


def run_streamlit():
    """Запускает Streamlit приложение для авторизации"""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/streamlit_auth.py",
            "--server.port=8501",
            "--server.headless=true",
        ]
    )


def run_dash():
    """Запускает Dash приложение"""
    time.sleep(2)  # Небольшая задержка для запуска Streamlit
    from app.dash_customer import app

    app.run(debug=True, port=8050, host="127.0.0.1")


if __name__ == "__main__":
    print("🚀 Запуск приложений...")
    print("📝 Streamlit (авторизация): http://localhost:8501")
    print("📊 Dash (приложение): http://localhost:8050")
    print("\n⚠️  Сначала войдите через Streamlit, затем перейдите к Dash приложению\n")

    # Запускаем Streamlit в отдельном потоке
    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()

    # Запускаем Dash в основном потоке
    try:
        run_dash()
    except KeyboardInterrupt:
        print("\n👋 Остановка приложений...")
