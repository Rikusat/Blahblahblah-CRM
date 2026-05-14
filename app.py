import streamlit as st
import pandas as pd

from auth import check_password
from sheets import get_dataframe, update_row, add_row, delete_row

st.set_page_config(page_title="CRM", page_icon="📊", layout="wide")

if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# Data loading with cache
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    return get_dataframe()


def reload():
    st.cache_data.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEXTAREA_KEYWORDS = {"備考", "メモ", "次回アクション", "notes", "memo", "コメント"}


def render_fields(columns: list[str], defaults: dict | None = None) -> dict:
    """Render input widgets for each column and return a dict of values."""
    values = {}
    defaults = defaults or {}
    for col in columns:
        val = str(defaults.get(col, "")) if pd.notna(defaults.get(col, "")) else ""
        if col in TEXTAREA_KEYWORDS:
            values[col] = st.text_area(col, value=val)
        else:
            values[col] = st.text_input(col, value=val)
    return values


def find_label_col(df: pd.DataFrame) -> str | None:
    for candidate in ["事業所名", "担当者名", "担当者名/代表者名", "名前", "会社名"]:
        if candidate in df.columns:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("📊 CRM")
page = st.sidebar.radio("ページ", ["ダッシュボード", "顧客一覧", "新規登録"])

if st.sidebar.button("🔄 データ更新"):
    reload()
    st.rerun()

st.sidebar.divider()
if st.sidebar.button("ログアウト"):
    st.session_state.authenticated = False
    st.rerun()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

df = load_data()

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

if page == "ダッシュボード":
    st.title("📊 ダッシュボード")

    if df.empty:
        st.info("スプレッドシートにデータがありません。")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("総顧客数", len(df))

    # Email sent metric — detect column containing "メール" and a done marker
    email_sent_col = next(
        (c for c in df.columns if "メール" in c and any(k in c for k in ["済", "送信", "フラグ"])),
        None,
    )
    if email_sent_col:
        sent = df[email_sent_col].astype(str).str.contains(
            r"済|✓|○|TRUE|1", case=False, na=False, regex=True
        ).sum()
        col2.metric("メール送信済み", int(sent))

    if "業種" in df.columns:
        col3.metric("業種数", df["業種"].nunique())

    if "業種" in df.columns:
        st.subheader("業種別件数")
        counts = df["業種"].value_counts().rename_axis("業種").reset_index(name="件数")
        st.bar_chart(counts.set_index("業種"))

# ---------------------------------------------------------------------------
# Customer list
# ---------------------------------------------------------------------------

elif page == "顧客一覧":
    st.title("👥 顧客一覧")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    # --- Filters ---
    col1, col2 = st.columns(2)
    search = col1.text_input("🔍 キーワード検索")

    selected_industry = "すべて"
    if "業種" in df.columns:
        industries = ["すべて"] + sorted(df["業種"].dropna().unique().tolist())
        selected_industry = col2.selectbox("業種フィルタ", industries)

    filtered = df.copy()
    if search:
        mask = filtered.apply(
            lambda row: row.astype(str).str.contains(search, case=False, na=False).any(),
            axis=1,
        )
        filtered = filtered[mask]
    if selected_industry != "すべて" and "業種" in df.columns:
        filtered = filtered[filtered["業種"] == selected_industry]

    st.caption(f"{len(filtered)} 件")
    st.dataframe(filtered, use_container_width=True)

    # --- Edit / Delete ---
    st.divider()
    st.subheader("✏️ 編集・削除")

    if filtered.empty:
        st.info("該当するレコードがありません。")
        st.stop()

    label_col = find_label_col(filtered)
    option_labels = {
        idx: f"#{idx + 1}  {row[label_col]}" if label_col else f"#{idx + 1}"
        for idx, row in filtered.iterrows()
    }

    selected_idx = st.selectbox(
        "レコードを選択",
        list(option_labels.keys()),
        format_func=lambda x: option_labels[x],
    )

    row_data = df.loc[selected_idx].to_dict()

    with st.form("edit_form"):
        edited = render_fields(list(df.columns), defaults=row_data)
        c1, c2 = st.columns(2)
        save = c1.form_submit_button("💾 保存", use_container_width=True, type="primary")
        delete = c2.form_submit_button("🗑️ 削除", use_container_width=True)

    if save:
        with st.spinner("保存中..."):
            update_row(selected_idx, edited)
        reload()
        st.success("保存しました")
        st.rerun()

    if delete:
        with st.spinner("削除中..."):
            delete_row(selected_idx)
        reload()
        st.success("削除しました")
        st.rerun()

# ---------------------------------------------------------------------------
# New registration
# ---------------------------------------------------------------------------

elif page == "新規登録":
    st.title("➕ 新規登録")

    if df.empty:
        st.info("スプレッドシートにヘッダー行が必要です。先にスプレッドシートに列名を設定してください。")
        st.stop()

    with st.form("add_form"):
        new_data = render_fields(list(df.columns))
        submitted = st.form_submit_button("登録", use_container_width=True, type="primary")

    if submitted:
        with st.spinner("登録中..."):
            add_row(new_data)
        reload()
        st.success("登録しました")
        st.rerun()
