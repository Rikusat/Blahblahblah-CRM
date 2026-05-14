import streamlit as st
import pandas as pd

from auth import check_password
from sheets import get_dataframe, update_row, add_row, delete_row, write_replied

st.set_page_config(page_title="CRM", page_icon="📊", layout="wide")

if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_CARDS_PER_ROW = 3
TEXTAREA_KEYWORDS = {"備考", "メモ", "次回アクション", "notes", "memo", "コメント"}

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    return get_dataframe()

def reload():
    st.cache_data.clear()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None

def render_fields(columns: list[str], defaults: dict | None = None, key_prefix: str = "") -> dict:
    values = {}
    defaults = defaults or {}
    for col in columns:
        val = str(defaults.get(col, "")) if pd.notna(defaults.get(col, "")) else ""
        key = f"{key_prefix}__{col}" if key_prefix else col
        if col in TEXTAREA_KEYWORDS:
            values[col] = st.text_area(col, value=val, key=key)
        else:
            values[col] = st.text_input(col, value=val, key=key)
    return values

def render_cards(df: pd.DataFrame):
    name_col   = find_col(df, "事業所名", "会社名", "担当者名", "名前")
    ind_col    = find_col(df, "業種")
    person_col = find_col(df, "担当者名", "担当者名/代表者名", "代表者名")
    email_col  = find_col(df, "メールアドレス", "メール")
    url_col    = find_col(df, "URL", "url", "ウェブサイト")
    note_col   = find_col(df, "備考", "メモ")

    cols = st.columns(N_CARDS_PER_ROW, gap="large")
    for n_row, (_, row) in enumerate(df.iterrows()):
        i = n_row % N_CARDS_PER_ROW
        if i == 0 and n_row > 0:
            cols = st.columns(N_CARDS_PER_ROW, gap="large")
        with cols[i]:
            with st.container(border=True):
                if name_col:
                    st.markdown(f"**{row[name_col]}**")
                if ind_col:
                    st.caption(f"🏢 {row[ind_col]}")
                if person_col and person_col != name_col:
                    st.markdown(f"👤 {row[person_col]}")
                if email_col and row[email_col]:
                    st.markdown(f"📧 {row[email_col]}")
                if url_col and row[url_col]:
                    url = str(row[url_col]).strip()
                    st.markdown(f"🔗 [{url}]({url})")
                if note_col and row[note_col]:
                    note = str(row[note_col])
                    st.caption(note[:80] + ("…" if len(note) > 80 else ""))

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("📊 CRM")
page = st.sidebar.radio("ページ", ["ダッシュボード", "顧客一覧", "見込み", "新規登録"])

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

    c1, c2, c3 = st.columns(3)
    c1.metric("総顧客数", len(df))

    email_sent_col = next(
        (c for c in df.columns if "メール" in c and any(k in c for k in ["済", "送信", "フラグ"])),
        None,
    )
    if email_sent_col:
        sent = df[email_sent_col].astype(str).str.contains(
            r"済|✓|○|TRUE|1", case=False, na=False, regex=True
        ).sum()
        c2.metric("メール送信済み", int(sent))

    if len(df.columns) >= 9:
        col_i = df.columns[8]
        replied = df[col_i].astype(str).str.contains("返信あり", na=False).sum()
        c3.metric("返信あり", int(replied))

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

    # Filters
    col1, col2 = st.columns(2)
    search = col1.text_input("🔍 キーワード検索")
    selected_industry = "すべて"
    if "業種" in df.columns:
        industry_values = sorted(
            x for x in df["業種"].unique() if str(x).strip()
        )
        selected_industry = col2.selectbox("業種フィルタ", ["すべて"] + industry_values)

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

    # Edit / Delete / 返信あり
    st.divider()
    st.subheader("✏️ 編集・削除")

    if filtered.empty:
        st.info("該当するレコードがありません。")
        st.stop()

    label_col = find_col(filtered, "事業所名", "担当者名", "担当者名/代表者名", "名前", "会社名")
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
        edited = render_fields(list(df.columns), defaults=row_data, key_prefix=f"edit_{selected_idx}")
        c1, c2, c3 = st.columns(3)
        save    = c1.form_submit_button("💾 保存", use_container_width=True, type="primary")
        replied = c2.form_submit_button("📩 返信あり", use_container_width=True)
        delete  = c3.form_submit_button("🗑️ 削除", use_container_width=True)

    if save:
        with st.spinner("保存中..."):
            update_row(selected_idx, edited)
        reload()
        st.success("保存しました")
        st.rerun()

    if replied:
        with st.spinner("更新中..."):
            write_replied(selected_idx)
        reload()
        st.success("返信ありを記録しました")
        st.rerun()

    if delete:
        with st.spinner("削除中..."):
            delete_row(selected_idx)
        reload()
        st.success("削除しました")
        st.rerun()

# ---------------------------------------------------------------------------
# 見込み
# ---------------------------------------------------------------------------

elif page == "見込み":
    st.title("⭐ 見込み顧客")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    if len(df.columns) < 9:
        st.warning("I列（9列目）がスプレッドシートに存在しません。")
        st.stop()

    col_i = df.columns[8]
    mikomi = df[df[col_i].astype(str).str.contains("返信あり", na=False)]

    st.caption(f"返信あり：{len(mikomi)} 件")

    if mikomi.empty:
        st.info("返信ありの顧客はまだいません。")
        st.stop()

    render_cards(mikomi)

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
