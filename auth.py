import streamlit as st
from datetime import datetime, timedelta

COOKIE_NAME = "octail_auth"
COOKIE_EXPIRY_DAYS = 1


def _get_controller():
    from streamlit_cookies_controller import CookieController
    return CookieController()


def check_password() -> bool:
    ctrl = _get_controller()

    if st.session_state.get("authenticated"):
        return True

    if ctrl.get(COOKIE_NAME) == "ok":
        st.session_state.authenticated = True
        st.session_state["admin_mode"] = False
        return True

    st.title("🔐 ログイン")
    password = st.text_input("パスワード", type="password", key="login_password")

    if st.button("ログイン"):
        if password == st.secrets["app"]["password"]:
            st.session_state.authenticated = True
            st.session_state["admin_mode"] = False
            ctrl.set(COOKIE_NAME, "ok")
            st.rerun()
        else:
            st.error("パスワードが違います")

    return False


def logout():
    ctrl = _get_controller()
    st.session_state.authenticated = False
    st.session_state["admin_mode"] = False
    ctrl.remove(COOKIE_NAME)
