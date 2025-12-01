FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей (только необходимые)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копирование requirements-services.txt и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Экспорт портов
EXPOSE 8501 8050

# Команда по умолчанию (будет переопределена в docker-compose)
CMD ["streamlit", "run", "streamlit_auth.py", "--server.port=8501", "--server.address=0.0.0.0"]

