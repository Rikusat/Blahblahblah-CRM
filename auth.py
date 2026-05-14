import streamlit as st


def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("🔐 ログイン")
    password = st.text_input("パスワード", type="password", key="login_password")

    if st.button("ログイン"):
        if password == st.secrets["app"]["password"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います")

    return False
