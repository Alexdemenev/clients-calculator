"""
Запуск только Streamlit приложения для авторизации
"""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/streamlit_auth.py",
            "--server.port=8551",
        ]
    )
