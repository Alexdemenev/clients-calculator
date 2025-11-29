"""
Streamlit приложение для авторизации и перенаправления на Dash
"""

import streamlit as st
import requests
from app.auth import authenticate, create_session, cleanup_expired_sessions

# Настройка страницы
st.set_page_config(
    page_title="Авторизация - Калькулятор клиентов",
    page_icon="🔐",
    layout="centered",
)

# Очистка истекших сессий
cleanup_expired_sessions()

# Инициализация состояния сессии
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "username" not in st.session_state:
    st.session_state.username = None

# Если уже авторизован, перенаправляем
if st.session_state.authenticated and st.session_state.session_token:
    st.success(f"✅ Вы авторизованы как {st.session_state.username}")
    st.markdown("---")

    # Ссылка на Dash приложение с токеном
    dash_url = f"http://localhost:8050?token={st.session_state.session_token}"

    st.markdown(
        f"""
    ### 🚀 Перейти к приложению
    
    [**Открыть Калькулятор клиентов**]({dash_url})
    
    Или скопируйте ссылку: `{dash_url}`
    """
    )

    # JavaScript для автоматической установки cookie (опционально)
    st.markdown(
        f"""
        <script>
        document.cookie = "session_token={st.session_state.session_token}; path=/; max-age={24*60*60}";
        </script>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Выйти"):
        st.session_state.authenticated = False
        st.session_state.session_token = None
        st.session_state.username = None
        st.rerun()
else:
    # Форма авторизации
    st.title("🔐 Авторизация")
    st.markdown("Войдите в систему для доступа к Калькулятору клиентов")

    with st.form("login_form"):
        username = st.text_input("Имя пользователя", placeholder="admin")
        password = st.text_input(
            "Пароль", type="password", placeholder="Введите пароль"
        )
        submit_button = st.form_submit_button("Войти", use_container_width=True)

        if submit_button:
            if not username or not password:
                st.error("⚠️ Пожалуйста, заполните все поля")
            elif authenticate(username, password):
                # Создаем сессию
                session_token = create_session(username)
                st.session_state.authenticated = True
                st.session_state.session_token = session_token
                st.session_state.username = username
                st.success("✅ Авторизация успешна!")
                st.rerun()
            else:
                st.error("❌ Неверное имя пользователя или пароль")

    # Информация для разработки
    # with st.expander("ℹ️ Информация для разработки"):
    #     st.markdown(
    #         """
    #     **Учетные данные по умолчанию:**
    #     - Имя пользователя: `admin`
    #     - Пароль: `admin`

    #     ⚠️ **Внимание:** В продакшене обязательно измените пароль!
    #     """
    #     )
