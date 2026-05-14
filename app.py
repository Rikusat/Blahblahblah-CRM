import streamlit as st
import pandas as pd

from auth import check_password
from sheets import get_dataframe, update_row, add_row, delete_row, write_replied, write_ordered

st.set_page_config(page_title="Octail", page_icon="📊", layout="wide")

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

st.sidebar.title("📊 Octail")
page = st.sidebar.radio("ページ", ["ダッシュボード", "顧客一覧", "見込み", "受注リスト"])

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

    # --- 受注メトリクス ---
    monthly_target = int(st.secrets["app"].get("monthly_target", 10))

    ordered_count = 0
    if len(df.columns) >= 10:
        col_j = df.columns[9]
        ordered_count = int(df[col_j].astype(str).str.contains("受注", na=False).sum())

    achievement = ordered_count / monthly_target if monthly_target > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("月間目標", f"{monthly_target} 件")
    c2.metric("受注数", f"{ordered_count} 件")
    c3.metric("達成率", f"{achievement:.0%}")

    st.progress(min(achievement, 1.0))

    st.divider()

    # --- その他メトリクス ---
    c4, c5, c6 = st.columns(3)
    c4.metric("総顧客数", len(df))

    email_sent_col = next(
        (c for c in df.columns if "メール" in c and any(k in c for k in ["済", "送信", "フラグ"])),
        None,
    )
    if email_sent_col:
        sent = df[email_sent_col].astype(str).str.contains(
            r"済|✓|○|TRUE|1", case=False, na=False, regex=True
        ).sum()
        c5.metric("メール送信済み", int(sent))

    if len(df.columns) >= 9:
        col_i = df.columns[8]
        replied = df[col_i].astype(str).str.contains("返信あり", na=False).sum()
        c6.metric("返信あり", int(replied))

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
        c1, c2, c3, c4 = st.columns(4)
        save    = c1.form_submit_button("💾 保存",    use_container_width=True, type="primary")
        replied = c2.form_submit_button("📩 返信あり", use_container_width=True)
        ordered = c3.form_submit_button("🏆 受注",    use_container_width=True)
        delete  = c4.form_submit_button("🗑️ 削除",   use_container_width=True)

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

    if ordered:
        with st.spinner("更新中..."):
            write_ordered(selected_idx)
        reload()
        st.success("受注を記録しました")
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
# 受注リスト
# ---------------------------------------------------------------------------

elif page == "受注リスト":
    st.title("🏆 受注リスト")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    if len(df.columns) < 10:
        st.warning("J列（10列目）がスプレッドシートに存在しません。")
        st.stop()

    col_j = df.columns[9]
    orders = df[df[col_j].astype(str).str.contains("受注", na=False)]

    st.caption(f"受注：{len(orders)} 件")

    if orders.empty:
        st.info("受注済みの顧客はまだいません。")
        st.stop()

    st.dataframe(orders, use_container_width=True)
