import streamlit as st
import pandas as pd

from auth import check_password, logout
from sheets import get_dataframe, update_row, add_row, delete_row, write_replied, write_ordered, write_mikomi_memo

st.set_page_config(page_title="Octail", page_icon="🟠", layout="wide")

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }

/* ── Base ── */
.stApp { background-color: #0d0d0d; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #080808;
    border-right: 1px solid #1a1a1a;
}
[data-testid="stSidebar"] .stRadio label {
    font-family: monospace;
    color: #ddd;
    font-size: 0.85rem;
    letter-spacing: 1px;
}

/* ── Headings ── */
h1 { color: #FF8C00 !important; font-family: monospace !important; letter-spacing: 2px !important; }
h2, h3 { color: #cc7000 !important; font-family: monospace !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 6px;
    padding: 1rem 1.2rem;
}
[data-testid="stMetricLabel"] p  { color: #bbb !important; font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 2px; font-family: monospace; }
[data-testid="stMetricValue"]    { color: #FF8C00 !important; font-family: monospace !important; }
[data-testid="stMetricDelta"]    { color: #cfcfcf !important; }

/* ── Buttons ── */
.stButton > button {
    background: #111; border: 1px solid #2a2a2a;
    color: #eaeaea; font-family: monospace;
    border-radius: 3px; transition: all .15s;
}
.stButton > button:hover { border-color: #FF8C00; color: #FF8C00; background: #0d0d0d; }
[data-testid="baseButton-primary"] {
    background: #FF8C00 !important; border-color: #FF8C00 !important; color: #000 !important;
}
[data-testid="baseButton-secondary"]:hover { border-color: #FF8C00 !important; color: #FF8C00 !important; }

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
    background: #0a0a0a !important; border: 1px solid #222 !important;
    color: #d4d4d4 !important; font-family: monospace !important;
    border-radius: 4px !important;
}
.stTextArea textarea::placeholder { color: #b4b4b4 !important; }

/* ── Progress ── */
.stProgress > div > div > div > div { background: #FF8C00 !important; }
.stProgress > div > div > div { background: #1a1a1a !important; border-radius: 4px; }

/* ── Bordered containers (cards) ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #111 !important; border: 1px solid #1e1e1e !important; border-radius: 8px !important;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border: 1px solid #1e1e1e; border-radius: 6px; overflow: hidden; }

/* ── Divider ── */
hr { border-color: #1a1a1a !important; margin: 1.5rem 0 !important; }

/* ── Caption / small text ── */
.stCaption p { color: #b4b4b4 !important; font-family: monospace !important; font-size: 0.75rem !important; }

/* ── Radio ── */
.stRadio > div { gap: 0.4rem; }

/* ── Selectbox text ── */
.stSelectbox span { font-family: monospace !important; }

/* ── Terminal memo textarea special ── */
.terminal-memo textarea {
    background: #060606 !important; border: 1px solid #1a1a1a !important;
    color: #d4d4d4 !important; font-family: monospace !important;
    font-size: 1rem !important; line-height: 1.7 !important;
    min-height: 200px !important;
}
</style>
""", unsafe_allow_html=True)

if not check_password():
    st.stop()

if "session_initialized" not in st.session_state:
    st.session_state["session_initialized"] = True
    st.session_state["admin_mode"] = False
elif "admin_mode" not in st.session_state:
    st.session_state["admin_mode"] = False

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

st.sidebar.markdown(
    "<div style='padding:1.2rem 0 0.4rem;font-size:1.3rem;font-family:monospace;color:#FF8C00;font-weight:700;letter-spacing:3px;'>◈ OCTAIL</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("<div style='color:#adadad;font-size:0.65rem;font-family:monospace;letter-spacing:2px;margin-bottom:1rem;'>CRM SYSTEM</div>", unsafe_allow_html=True)

page = st.sidebar.radio(
    "", ["ターミナル", "ダッシュボード", "顧客一覧", "見込み", "受注リスト"],
    label_visibility="collapsed",
)

st.sidebar.markdown("<hr style='border-color:#1a1a1a;margin:1rem 0;'>", unsafe_allow_html=True)

admin_label = "🔓 ADMIN" if st.session_state.get("admin_mode") else "🔒 VIEWER"
st.sidebar.markdown(
    f"<div style='color:#{'FF8C00' if st.session_state.get('admin_mode') else 'b4b4b4'};font-family:monospace;font-size:.7rem;letter-spacing:2px;padding:.2rem 0;'>{admin_label}</div>",
    unsafe_allow_html=True,
)

if st.sidebar.button("⟳  データ更新", use_container_width=True):
    reload()
    st.rerun()

if st.sidebar.button("→  ログアウト", use_container_width=True):
    logout()
    st.rerun()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

df = load_data()

# ---------------------------------------------------------------------------
# ターミナル
# ---------------------------------------------------------------------------

if page == "ターミナル":

    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown("""
<div style="padding: 2rem 0 1rem;">
  <div id="oct-date" style="font-size:1rem;color:#bbbbbb;font-family:monospace;letter-spacing:3px;margin-bottom:.5rem;"></div>
  <div id="oct-time" style="font-size:4.5rem;font-weight:700;color:#FF8C00;font-family:monospace;letter-spacing:6px;line-height:1;"></div>
</div>
<script>
(function() {
  function pad(n){ return String(n).padStart(2,'0'); }
  function tick(){
    var now = new Date();
    var days=['日','月','火','水','木','金','土'];
    var d = document.getElementById('oct-date');
    var t = document.getElementById('oct-time');
    if(d) d.textContent = days[now.getDay()]+'. '+now.getFullYear()+'/'+pad(now.getMonth()+1)+'/'+pad(now.getDate());
    if(t) t.textContent = pad(now.getHours())+':'+pad(now.getMinutes())+':'+pad(now.getSeconds());
  }
  tick(); setInterval(tick, 1000);
})();
</script>
""", unsafe_allow_html=True)

        st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)

        # Quick stats
        if not df.empty:
            monthly_target = int(st.secrets["app"].get("monthly_target", 10))
            ordered_count = 0
            if len(df.columns) >= 11:
                ordered_count = int(df[df.columns[10]].astype(str).str.contains("受注", na=False).sum())
            replied_count = 0
            if len(df.columns) >= 9:
                replied_count = int(df[df.columns[8]].astype(str).str.contains("返信あり", na=False).sum())

            st.markdown("<div style='font-size:.65rem;color:#adadad;font-family:monospace;letter-spacing:3px;margin-bottom:.8rem;'>QUICK STATS</div>", unsafe_allow_html=True)
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("顧客総数", len(df))
            sc2.metric("返信あり", replied_count)
            sc3.metric(f"受注 / 目標", f"{ordered_count} / {monthly_target}")

    with col_r:
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:.65rem;color:#adadad;font-family:monospace;letter-spacing:3px;margin-bottom:.5rem;'>MEMO</div>", unsafe_allow_html=True)

        if "terminal_memo" not in st.session_state:
            st.session_state["terminal_memo"] = ""

        st.text_area(
            "",
            placeholder="Take a note...",
            height=220,
            key="terminal_memo",
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:.65rem;color:#adadad;font-family:monospace;letter-spacing:3px;margin-bottom:.5rem;'>ADMIN</div>", unsafe_allow_html=True)

        if st.session_state.get("admin_mode"):
            st.markdown(
                "<div style='color:#FF8C00;font-family:monospace;font-size:.8rem;letter-spacing:2px;margin-bottom:.5rem;'>🔓 管理者モード中</div>",
                unsafe_allow_html=True,
            )
            if st.button("🔒 ロック", use_container_width=True, key="admin_lock"):
                st.session_state["admin_mode"] = False
                st.session_state.pop("show_admin_input", None)
                st.rerun()
        else:
            if st.button("🔑 管理者モード", use_container_width=True, key="admin_btn"):
                st.session_state["show_admin_input"] = True

            if st.session_state.get("show_admin_input"):
                admin_pw = st.text_input("管理者パスワード", type="password", key="admin_pw_input", label_visibility="collapsed", placeholder="管理者パスワード")
                if st.button("解除", use_container_width=True, key="admin_unlock_btn", type="primary"):
                    if admin_pw == st.secrets["app"].get("admin_password", ""):
                        st.session_state["admin_mode"] = True
                        st.session_state["show_admin_input"] = False
                        st.rerun()
                    else:
                        st.error("パスワードが違います")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

elif page == "ダッシュボード":
    st.title("DASHBOARD")

    if df.empty:
        st.info("スプレッドシートにデータがありません。")
        st.stop()

    monthly_target = int(st.secrets["app"].get("monthly_target", 10))
    ordered_count = 0
    if len(df.columns) >= 11:
        col_k = df.columns[10]
        ordered_count = int(df[col_k].astype(str).str.contains("受注", na=False).sum())
    achievement = ordered_count / monthly_target if monthly_target > 0 else 0

    gauge_color = "#2FFFB4" if achievement >= 1.0 else "#EC2D01"
    st.markdown(
        f"<style>.stProgress > div > div > div > div {{ background: {gauge_color} !important; }}</style>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("月間目標", f"{monthly_target} 件")
    c2.metric("受注数", f"{ordered_count} 件")
    c3.metric("達成率", f"{achievement:.0%}")
    st.progress(min(achievement, 1.0))

    st.divider()

    c4, c5, c6 = st.columns(3)
    c4.metric("総顧客数", len(df))

    email_sent_col = next(
        (c for c in df.columns if "メール" in c and any(k in c for k in ["済", "送信", "フラグ"])), None,
    )
    if email_sent_col:
        sent = df[email_sent_col].astype(str).str.contains(r"済|✓|○|TRUE|1", case=False, na=False, regex=True).sum()
        c5.metric("メール送信済み", int(sent))

    if len(df.columns) >= 9:
        replied = df[df.columns[8]].astype(str).str.contains("返信あり", na=False).sum()
        c6.metric("返信あり", int(replied))

    if "業種" in df.columns:
        st.divider()
        st.subheader("業種別件数")
        counts = df["業種"].value_counts().rename_axis("業種").reset_index(name="件数")
        st.bar_chart(counts.set_index("業種"))

# ---------------------------------------------------------------------------
# Customer list
# ---------------------------------------------------------------------------

elif page == "顧客一覧":
    st.title("CUSTOMERS")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    col1, col2 = st.columns(2)
    search = col1.text_input("🔍 キーワード検索")
    selected_industry = "すべて"
    if "業種" in df.columns:
        industry_values = sorted(x for x in df["業種"].unique() if str(x).strip())
        selected_industry = col2.selectbox("業種フィルタ", ["すべて"] + industry_values)

    filtered = df.copy()
    if search:
        mask = filtered.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
        filtered = filtered[mask]
    if selected_industry != "すべて" and "業種" in df.columns:
        filtered = filtered[filtered["業種"] == selected_industry]

    st.caption(f"{len(filtered)} 件")
    st.dataframe(filtered, use_container_width=True)

    st.divider()
    st.subheader("EDIT / ACTION")

    if filtered.empty:
        st.info("該当するレコードがありません。")
        st.stop()

    label_col = find_col(filtered, "事業所名", "担当者名", "担当者名/代表者名", "名前", "会社名")
    option_labels = {
        idx: f"#{idx + 1}  {row[label_col]}" if label_col else f"#{idx + 1}"
        for idx, row in filtered.iterrows()
    }

    selected_idx = st.selectbox("レコードを選択", list(option_labels.keys()), format_func=lambda x: option_labels[x], key="customer_select")
    row_data = df.loc[selected_idx].to_dict()

    # メール有無（A列）・返信あり（I列）・受注（K列）はボタン管理のため編集フォームから除外
    EXCLUDE_COLS = {df.columns[0]} | (
        {df.columns[8]}  if len(df.columns) > 8  else set()
    ) | (
        {df.columns[10]} if len(df.columns) > 10 else set()
    )
    edit_cols = [c for c in df.columns if c not in EXCLUDE_COLS]

    if st.session_state.get("admin_mode"):
        with st.form("edit_form"):
            edited = render_fields(edit_cols, defaults=row_data, key_prefix=f"edit_{selected_idx}")
            c1, c2 = st.columns(2)
            save   = c1.form_submit_button("💾 保存", use_container_width=True, type="primary")
            delete = c2.form_submit_button("🗑️ 削除", use_container_width=True)

        if save:
            with st.spinner("保存中..."):
                update_row(selected_idx, edited)
            reload(); st.success("保存しました"); st.rerun()
        if delete:
            with st.spinner("削除中..."):
                delete_row(selected_idx)
            reload(); st.success("削除しました"); st.rerun()
    else:
        st.caption("🔒 編集・削除は管理者モードで行えます")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("📩 返信あり", use_container_width=True, key="btn_replied"):
            with st.spinner("更新中..."):
                write_replied(selected_idx)
            reload(); st.success("返信ありを記録しました"); st.rerun()
    with b2:
        if st.button("🏆 受注", use_container_width=True, key="btn_ordered"):
            with st.spinner("更新中..."):
                write_ordered(selected_idx)
            reload(); st.success("受注を記録しました"); st.rerun()

# ---------------------------------------------------------------------------
# 見込み
# ---------------------------------------------------------------------------

elif page == "見込み":
    from datetime import datetime

    st.title("PROSPECTS")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    if len(df.columns) < 9:
        st.warning("I列（9列目）がスプレッドシートに存在しません。")
        st.stop()

    if st.session_state.get("_last_page") != "見込み":
        st.session_state["mikomi_editing_idx"] = None
    st.session_state["_last_page"] = "見込み"

    col_i    = df.columns[8]
    memo_col = df.columns[9] if len(df.columns) >= 10 else None
    mikomi   = df[df[col_i].astype(str).str.contains("返信あり", na=False)]

    st.caption(f"返信あり：{len(mikomi)} 件")

    if mikomi.empty:
        st.info("返信ありの顧客はまだいません。")
        st.stop()

    # --- カード表示（メモ + 編集ボタン付き）---
    name_col   = find_col(mikomi, "事業所名", "会社名", "担当者名", "名前")
    ind_col    = find_col(mikomi, "業種")
    person_col = find_col(mikomi, "担当者名", "担当者名/代表者名", "代表者名")
    email_col  = find_col(mikomi, "メールアドレス", "メール")
    url_col    = find_col(mikomi, "URL", "url", "ウェブサイト")

    cols = st.columns(N_CARDS_PER_ROW, gap="large")
    for n_row, (idx, row) in enumerate(mikomi.iterrows()):
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

                # J列メモ表示
                is_expanded = st.session_state.get(f"mikomi_open_{idx}", False)
                if memo_col and memo_col in row.index:
                    memo_val = str(row[memo_col])
                    if memo_val not in ("", "nan", "None"):
                        st.markdown(
                            "<div style='border-top:1px solid #1e1e1e;margin-top:.5rem;'></div>",
                            unsafe_allow_html=True,
                        )
                        display_text = memo_val if is_expanded else memo_val[:150]
                        ellipsis = "" if is_expanded or len(memo_val) <= 150 else "…"
                        st.markdown(
                            f"<div style='color:#c2c2c2;font-family:monospace;font-size:.78rem;"
                            f"padding-top:.5rem;white-space:pre-wrap;'>{display_text}{ellipsis}</div>",
                            unsafe_allow_html=True,
                        )
                        if len(memo_val) > 150:
                            label = "閉じる ▲" if is_expanded else "開く ▼"
                            if st.button(label, key=f"mikomi_toggle_{idx}", use_container_width=True):
                                st.session_state[f"mikomi_open_{idx}"] = not is_expanded
                                st.rerun()

                if st.button("📝 メモ", key=f"mikomi_edit_{idx}", use_container_width=True):
                    st.session_state["mikomi_editing_idx"] = idx
                    st.rerun()

    # --- 編集フォーム（編集ボタン押下後に表示）---
    editing_idx = st.session_state.get("mikomi_editing_idx")
    if editing_idx is not None and editing_idx in mikomi.index:
        st.divider()
        st.subheader("MEMO  ( J列 )")

        label_col = find_col(mikomi, "事業所名", "担当者名", "担当者名/代表者名", "名前", "会社名")
        label = f"#{editing_idx + 1}  {mikomi.loc[editing_idx, label_col]}" if label_col else f"#{editing_idx + 1}"
        st.caption(f"編集中：{label}")

        current_memo = str(df.loc[editing_idx, memo_col]) if memo_col else ""
        if current_memo in ("nan", "None"):
            current_memo = ""

        memo_key = f"mikomi_memo_{editing_idx}"
        if memo_key not in st.session_state:
            st.session_state[memo_key] = current_memo

        ts_col, _ = st.columns([1, 5])
        with ts_col:
            if st.button("📅 日付挿入", key="ts_btn", use_container_width=True):
                ts = datetime.now().strftime("%Y/%m/%d  %H:%M  ")
                existing = st.session_state[memo_key]
                st.session_state[memo_key] = (existing + "\n" + ts).lstrip("\n")
                st.rerun()

        st.text_area("メモ", placeholder="Take a note...", key=memo_key, height=200)

        sv_col, cl_col = st.columns(2)
        with sv_col:
            if st.button("💾 保存", type="primary", use_container_width=True, key="save_memo_btn"):
                with st.spinner("保存中..."):
                    write_mikomi_memo(editing_idx, st.session_state[memo_key])
                reload()
                st.success("メモを保存しました")
                st.rerun()
        with cl_col:
            if st.button("✕ 閉じる", use_container_width=True, key="close_memo_btn"):
                del st.session_state["mikomi_editing_idx"]
                st.rerun()

# ---------------------------------------------------------------------------
# 受注リスト
# ---------------------------------------------------------------------------

elif page == "受注リスト":
    st.title("ORDERS")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    if len(df.columns) < 11:
        st.warning("K列（11列目）がスプレッドシートに存在しません。")
        st.stop()

    col_k = df.columns[10]
    orders = df[df[col_k].astype(str).str.contains("受注", na=False)]

    st.caption(f"受注：{len(orders)} 件")

    if orders.empty:
        st.info("受注済みの顧客はまだいません。")
        st.stop()

    st.dataframe(orders, use_container_width=True)
