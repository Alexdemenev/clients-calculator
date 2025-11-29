"""
Модуль для управления авторизацией
"""

import hashlib
import secrets
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from app.config import USERS

# Путь к файлу с сессиями
SESSIONS_FILE = Path("app/sessions.json")
# Время жизни сессии (в часах)
SESSION_LIFETIME_HOURS = 24


def hash_password(password: str) -> str:
    """Хеширует пароль"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_session_token() -> str:
    """Генерирует уникальный токен сессии"""
    return secrets.token_urlsafe(32)


def load_sessions() -> dict:
    """Загружает сессии из файла"""
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_sessions(sessions: dict):
    """Сохраняет сессии в файл"""
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


def create_session(username: str) -> str:
    """Создает новую сессию для пользователя"""
    sessions = load_sessions()
    token = generate_session_token()
    expires_at = (datetime.now() + timedelta(hours=SESSION_LIFETIME_HOURS)).isoformat()

    sessions[token] = {
        "username": username,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
    }

    save_sessions(sessions)
    return token


def validate_session(token: str) -> bool:
    """Проверяет валидность токена сессии"""
    if not token:
        return False

    sessions = load_sessions()
    if token not in sessions:
        return False

    session = sessions[token]
    expires_at = datetime.fromisoformat(session["expires_at"])

    # Проверяем срок действия
    if datetime.now() > expires_at:
        # Удаляем истекшую сессию
        del sessions[token]
        save_sessions(sessions)
        return False

    return True


def get_session_username(token: str) -> str:
    """Получает имя пользователя из сессии"""
    sessions = load_sessions()
    if token in sessions:
        return sessions[token].get("username", "")
    return ""


def delete_session(token: str):
    """Удаляет сессию"""
    sessions = load_sessions()
    if token in sessions:
        del sessions[token]
        save_sessions(sessions)


def cleanup_expired_sessions():
    """Удаляет истекшие сессии"""
    sessions = load_sessions()
    now = datetime.now()
    expired_tokens = []

    for token, session in sessions.items():
        expires_at = datetime.fromisoformat(session["expires_at"])
        if now > expires_at:
            expired_tokens.append(token)

    for token in expired_tokens:
        del sessions[token]

    if expired_tokens:
        save_sessions(sessions)


# Предустановленные пользователи (в продакшене лучше хранить в БД)
# Пароль по умолчанию: "admin" (хеш: 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918)
# USERS = {
#     "admin": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
#     # Можно добавить больше пользователей
#     # "user": "хеш_пароля",
# }


def authenticate(username: str, password: str) -> bool:
    """Проверяет учетные данные пользователя"""
    if username not in USERS:
        return False

    password_hash = hash_password(password)
    # print(USERS)
    # print(USERS[username], password_hash)
    return USERS[username] == password_hash
