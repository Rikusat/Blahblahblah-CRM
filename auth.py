import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta

COOKIE_NAME = "octail_auth"
COOKIE_EXPIRY_DAYS = 1


@st.cache_resource
def _cookie_manager():
    return stx.CookieManager(key="octail_cookie_mgr")


def check_password() -> bool:
    cm = _cookie_manager()

    if st.session_state.get("authenticated") or cm.get(COOKIE_NAME) == "ok":
        st.session_state.authenticated = True
        return True

    st.title("🔐 ログイン")
    password = st.text_input("パスワード", type="password", key="login_password")

    if st.button("ログイン"):
        if password == st.secrets["app"]["password"]:
            st.session_state.authenticated = True
            cm.set(COOKIE_NAME, "ok", expires=datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS))
            st.rerun()
        else:
            st.error("パスワードが違います")

    return False


def logout():
    cm = _cookie_manager()
    st.session_state.authenticated = False
    cm.delete(COOKIE_NAME)
