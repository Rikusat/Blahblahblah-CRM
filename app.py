import streamlit as st
import pandas as pd

from auth import check_password, logout
from sheets import (
    get_dataframe, update_row, add_row, delete_row, archive_and_delete_row,
    write_replied, write_ordered, write_memo,
    write_claim, write_claim_done, write_claim_content, write_claim_note,
    get_board, set_board,
    DATA_OFFSET, COL_REPLIED, COL_ORDERED, COL_MEMO,
    COL_CLAIM, COL_CLAIM_DONE, COL_CLAIM_CONTENT, COL_CLAIM_NOTE,
)

st.set_page_config(page_title="Octail", page_icon="🟠", layout="wide")

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

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

@st.cache_data(ttl=30)
def load_board_data(board_type: str) -> dict:
    return get_board(board_type)

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

SELECT_OPTIONS: dict[str, list[str]] = {
    COL_REPLIED: ["", "見込みC", "見込みB", "見込みA"],
    "メール済か": ["", "済み"],
    "メール": ["", "済み"],
}

def render_fields(columns: list[str], defaults: dict | None = None, key_prefix: str = "") -> dict:
    values = {}
    defaults = defaults or {}
    for col in columns:
        val = str(defaults.get(col, "")) if pd.notna(defaults.get(col, "")) else ""
        key = f"{key_prefix}__{col}" if key_prefix else col
        if col in SELECT_OPTIONS:
            opts = SELECT_OPTIONS[col]
            idx = opts.index(val) if val in opts else 0
            values[col] = st.selectbox(col, opts, index=idx, key=key)
        elif col in TEXTAREA_KEYWORDS:
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

df = load_data()

st.sidebar.markdown(
    "<div style='padding:1.2rem 0 0.4rem;font-size:1.3rem;font-family:monospace;color:#FF8C00;font-weight:700;letter-spacing:3px;'>◈ OCTAIL</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("<div style='color:#adadad;font-size:0.65rem;font-family:monospace;letter-spacing:2px;margin-bottom:1rem;'>CRM SYSTEM</div>", unsafe_allow_html=True)

_unresolved = 0
if not df.empty and COL_CLAIM in df.columns:
    _has_claim = df[COL_CLAIM].astype(str).str.strip().ne("").replace({"nan": False}, regex=False)
    _done_mask = df[COL_CLAIM_DONE].astype(str).str.strip().eq("対応済み") if COL_CLAIM_DONE in df.columns else pd.Series(False, index=df.index)
    _unresolved = int((_has_claim & ~_done_mask).sum())

_claim_label = f"クレーム  🔴{_unresolved}" if _unresolved > 0 else "クレーム"

page = st.sidebar.radio(
    "", ["ターミナル", "ダッシュボード", "顧客一覧", "見込み", "受注リスト", _claim_label],
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
            if COL_ORDERED in df.columns:
                ordered_count = int(df[COL_ORDERED].astype(str).str.contains("受注", na=False).sum())
            replied_count = 0
            if COL_REPLIED in df.columns:
                replied_count = int(df[COL_REPLIED].astype(str).str.contains("返信あり", na=False).sum())

            st.markdown("<div style='font-size:.65rem;color:#adadad;font-family:monospace;letter-spacing:3px;margin-bottom:.8rem;'>QUICK STATS</div>", unsafe_allow_html=True)
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("顧客総数", len(df))
            sc2.metric("返信あり", replied_count)
            target_color = "#2FFFB4" if ordered_count >= monthly_target else "#EC2D01"
            sc3.markdown(
                f"<div style='background:#111;border:1px solid #1e1e1e;border-radius:6px;padding:1rem 1.2rem;'>"
                f"<div style='color:#bbb;font-size:.7rem;text-transform:uppercase;letter-spacing:2px;font-family:monospace;margin-bottom:.3rem;'>受注 / 目標</div>"
                f"<div style='color:{target_color};font-family:monospace;font-size:1.8rem;font-weight:700;line-height:1;'>{ordered_count} / {monthly_target}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

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

    # ── 掲示板 ────────────────────────────────────────────────────
    st.divider()

    SIZE_MAP = {"小": "0.85rem", "中": "1.1rem", "大": "1.5rem", "特大": "2rem"}
    is_admin = st.session_state.get("admin_mode", False)

    def _safe_color(c: str, fallback: str) -> str:
        return c if (c.startswith("#") and len(c) == 7) else fallback

    def _render_board(board_type: str, label: str, editable: bool):
        data    = load_board_data(board_type)
        content = data.get("content", "")
        color   = _safe_color(data.get("color", ""), "#FF8C00" if board_type == "admin" else "#d4d4d4")
        size    = data.get("size", "中") if data.get("size", "中") in SIZE_MAP else "中"

        st.markdown(f"<div style='font-size:.65rem;color:#adadad;font-family:monospace;letter-spacing:3px;margin-bottom:.8rem;'>{label.upper()}</div>", unsafe_allow_html=True)
        if content:
            st.markdown(
                f"<div style='color:{color};font-size:{SIZE_MAP[size]};font-family:monospace;"
                f"background:#0a0a0a;border:1px solid #1e1e1e;border-radius:6px;"
                f"padding:1rem 1.2rem;white-space:pre-wrap;min-height:60px;'>{content}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='color:#555;font-size:.85rem;font-family:monospace;"
                "background:#0a0a0a;border:1px dashed #1e1e1e;border-radius:6px;"
                "padding:1rem 1.2rem;min-height:60px;'>— メッセージなし —</div>",
                unsafe_allow_html=True,
            )
        if editable:
            with st.expander("✏️ 編集"):
                draft = st.text_area("メッセージ", value=content, key=f"board_{board_type}_txt", height=120, label_visibility="collapsed", placeholder="メッセージを入力...")
                ec1, ec2 = st.columns(2)
                draft_color = ec1.color_picker("文字色", value=color, key=f"board_{board_type}_color")
                draft_size  = ec2.selectbox("文字サイズ", list(SIZE_MAP.keys()), index=list(SIZE_MAP.keys()).index(size), key=f"board_{board_type}_size")
                if st.button("💾 保存", key=f"board_{board_type}_save", type="primary", use_container_width=True):
                    with st.spinner("保存中..."):
                        set_board(board_type, draft, draft_color, draft_size)
                    reload()
                    st.success("掲示板を更新しました")
                    st.rerun()

    if is_admin:
        _render_board("admin", "管理者掲示板", editable=True)
    else:
        bc1, bc2 = st.columns(2, gap="large")
        with bc1:
            _render_board("admin", "管理者掲示板", editable=False)
        with bc2:
            _render_board("sales", "営業掲示板", editable=True)

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
    if COL_ORDERED in df.columns:
        ordered_count = int(df[COL_ORDERED].astype(str).str.contains("受注", na=False).sum())
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

    if COL_REPLIED in df.columns:
        replied = df[COL_REPLIED].astype(str).str.contains("返信あり", na=False).sum()
        c6.metric("返信あり", int(replied))

    if "業種" in df.columns:
        st.divider()
        st.subheader("業種別件数")
        counts = df["業種"].value_counts().rename_axis("業種").reset_index(name="件数")
        st.bar_chart(counts.set_index("業種"))

# ---------------------------------------------------------------------------
# Customer list
# ---------------------------------------------------------------------------

elif page.startswith("顧客一覧"):
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
        idx: f"#{idx}  {row[label_col]}" if label_col else f"#{idx}"
        for idx, row in filtered.iterrows()
    }

    selected_idx = st.selectbox("レコードを選択", list(option_labels.keys()), format_func=lambda x: option_labels[x], key="customer_select")
    row_data = df.loc[selected_idx].to_dict()

    edit_cols = list(df.columns)

    if st.session_state.get("admin_mode"):
        with st.form("edit_form"):
            edited = render_fields(edit_cols, defaults=row_data, key_prefix=f"edit_{selected_idx}")
            save = st.form_submit_button("💾 保存", use_container_width=True, type="primary")

        if save:
            with st.spinner("保存中..."):
                update_row(selected_idx, edited)
            reload(); st.success("保存しました"); st.rerun()

        # 削除（確認フロー）
        if st.session_state.get("confirm_delete_idx") == selected_idx:
            st.warning(f"⚠️ #{selected_idx} を削除します。削除シートに移動されます。")
            d1, d2 = st.columns(2)
            with d1:
                if st.button("🗑️ 削除を確定", use_container_width=True, type="primary", key="confirm_del_btn"):
                    with st.spinner("削除中..."):
                        archive_and_delete_row(selected_idx)
                    st.session_state.pop("confirm_delete_idx", None)
                    reload(); st.success("削除しました（削除シートに移動済み）"); st.rerun()
            with d2:
                if st.button("✕ キャンセル", use_container_width=True, key="cancel_del_btn"):
                    st.session_state.pop("confirm_delete_idx", None)
                    st.rerun()
        else:
            if st.button("🗑️ 削除", use_container_width=True, key="delete_btn"):
                st.session_state["confirm_delete_idx"] = selected_idx
                st.rerun()
    else:
        st.caption("🔒 編集・削除は管理者モードで行えます")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("📩 返信あり", use_container_width=True, key="btn_replied"):
            st.session_state["reply_selecting"] = selected_idx
            st.rerun()
    with b2:
        if st.button("🏆 受注", use_container_width=True, key="btn_ordered"):
            with st.spinner("更新中..."):
                write_ordered(selected_idx)
            reload(); st.success("受注を記録しました"); st.rerun()
    with b3:
        if st.button("⚠️ クレーム", use_container_width=True, key="btn_claim"):
            with st.spinner("更新中..."):
                write_claim(selected_idx)
            reload(); st.success("クレームを記録しました"); st.rerun()

    if st.session_state.get("reply_selecting") == selected_idx:
        st.markdown("<div style='font-size:.7rem;color:#adadad;font-family:monospace;letter-spacing:2px;margin:.6rem 0 .3rem;'>返信ステータスを選択</div>", unsafe_allow_html=True)
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        for col, label, value in [
            (rc1, "見込みC", "見込みC"),
            (rc2, "見込みB", "見込みB"),
            (rc3, "見込みA", "見込みA"),
            (rc4, "⚠️ クレーム", None),
            (rc5, "✕", "cancel"),
        ]:
            with col:
                if st.button(label, use_container_width=True, key=f"reply_opt_{value}_{selected_idx}"):
                    if value == "cancel":
                        st.session_state.pop("reply_selecting", None)
                    elif value is None:
                        with st.spinner("更新中..."):
                            write_claim(selected_idx)
                        st.session_state.pop("reply_selecting", None)
                        reload(); st.success("クレームを記録しました"); st.rerun()
                    else:
                        with st.spinner("更新中..."):
                            write_replied(selected_idx, value)
                        st.session_state.pop("reply_selecting", None)
                        reload(); st.success(f"{value} を記録しました"); st.rerun()

# ---------------------------------------------------------------------------
# 見込み
# ---------------------------------------------------------------------------

elif page == "見込み":
    from datetime import datetime

    st.title("PROSPECTS")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    if COL_REPLIED not in df.columns:
        st.warning(f"「{COL_REPLIED}」列がスプレッドシートに存在しません。")
        st.stop()

    if st.session_state.get("_last_page") != "見込み":
        st.session_state["mikomi_editing_idx"] = None
    st.session_state["_last_page"] = "見込み"

    memo_col = COL_MEMO if COL_MEMO in df.columns else None
    mikomi   = df[df[COL_REPLIED].astype(str).str.strip().replace("nan", "").ne("")]

    st.caption(f"返信あり：{len(mikomi)} 件")

    if mikomi.empty:
        st.info("返信ありの顧客はまだいません。")
        st.stop()

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
                replied_val = str(row[COL_REPLIED]).strip() if COL_REPLIED in row.index else ""
                if replied_val and replied_val not in ("nan", "None"):
                    st.caption(f"📌 {replied_val}")
                if ind_col:
                    st.caption(f"🏢 {row[ind_col]}")
                if person_col and person_col != name_col:
                    st.markdown(f"👤 {row[person_col]}")
                if email_col and row[email_col]:
                    st.markdown(f"📧 {row[email_col]}")
                if url_col and row[url_col]:
                    url = str(row[url_col]).strip()
                    st.markdown(f"🔗 [{url}]({url})")

                # 連携メモ表示
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

    # --- 編集フォーム ---
    editing_idx = st.session_state.get("mikomi_editing_idx")
    if editing_idx is not None and editing_idx in mikomi.index:
        st.divider()
        st.subheader(f"MEMO  ( {COL_MEMO} )")

        label_col_e = find_col(mikomi, "事業所名", "担当者名", "担当者名/代表者名", "名前", "会社名")
        label = f"#{editing_idx}  {mikomi.loc[editing_idx, label_col_e]}" if label_col_e else f"#{editing_idx}"
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
                    write_memo(editing_idx, st.session_state[memo_key])
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

    if COL_ORDERED not in df.columns:
        st.warning(f"「{COL_ORDERED}」列がスプレッドシートに存在しません。")
        st.stop()

    orders = df[df[COL_ORDERED].astype(str).str.contains("受注", na=False)]

    st.caption(f"受注：{len(orders)} 件")

    if orders.empty:
        st.info("受注済みの顧客はまだいません。")
        st.stop()

    st.dataframe(orders, use_container_width=True)

# ---------------------------------------------------------------------------
# クレーム
# ---------------------------------------------------------------------------

elif page.startswith("クレーム"):
    st.title("CLAIMS")

    if df.empty:
        st.info("データがありません。")
        st.stop()

    if COL_CLAIM not in df.columns:
        st.warning(f"「{COL_CLAIM}」列がスプレッドシートに存在しません。")
        st.stop()

    _claim_nonempty = df[COL_CLAIM].astype(str).str.strip().replace("nan", "").ne("")
    claims = df[_claim_nonempty].copy()
    claims = claims.sort_values(COL_CLAIM, ascending=False)

    st.caption(f"クレーム：{len(claims)} 件")

    if claims.empty:
        st.info("クレームの顧客はいません。")
        st.stop()

    name_col   = find_col(claims, "事業所名", "会社名", "担当者名", "名前")
    ind_col    = find_col(claims, "業種")
    person_col = find_col(claims, "担当者名", "担当者名/代表者名", "代表者名")
    email_col  = find_col(claims, "メールアドレス", "メール")
    url_col    = find_col(claims, "URL", "url", "ウェブサイト")

    cols = st.columns(N_CARDS_PER_ROW, gap="large")
    for n_row, (idx, row) in enumerate(claims.iterrows()):
        i = n_row % N_CARDS_PER_ROW
        if i == 0 and n_row > 0:
            cols = st.columns(N_CARDS_PER_ROW, gap="large")

        def _clean(v) -> str:
            s = str(v)
            return "" if s in ("nan", "None") else s

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

                st.markdown("<div style='border-top:1px solid #1e1e1e;margin-top:.5rem;padding-top:.5rem;'></div>", unsafe_allow_html=True)

                is_editing = st.session_state.get(f"claim_editing_{idx}", False)

                if not is_editing:
                    # 読み取り表示
                    claim_ts = _clean(row[COL_CLAIM]) if COL_CLAIM in row.index else ""
                    current_done = _clean(row.get(COL_CLAIM_DONE, "")) if COL_CLAIM_DONE in row.index else ""
                    done_label = "✅ 対応済み" if current_done == "対応済み" else "🔴 未対応"
                    st.markdown(
                        f"<div style='font-family:monospace;font-size:.75rem;color:#aaa;margin-bottom:.1rem;'>"
                        f"{done_label}"
                        f"<span style='float:right;font-size:.7rem;color:#666;'>{claim_ts}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if COL_CLAIM_CONTENT in row.index:
                        content_val = _clean(row[COL_CLAIM_CONTENT])
                        if content_val:
                            st.markdown(f"<div style='font-size:.7rem;color:#adadad;font-family:monospace;margin-bottom:.1rem;'>クレーム内容</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#c2c2c2;font-family:monospace;font-size:.78rem;white-space:pre-wrap;margin-bottom:.5rem;'>{content_val}</div>", unsafe_allow_html=True)

                    if COL_CLAIM_NOTE in row.index:
                        note_val = _clean(row[COL_CLAIM_NOTE])
                        if note_val:
                            st.markdown(f"<div style='font-size:.7rem;color:#adadad;font-family:monospace;margin-bottom:.1rem;'>対応内容</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#c2c2c2;font-family:monospace;font-size:.78rem;white-space:pre-wrap;margin-bottom:.5rem;'>{note_val}</div>", unsafe_allow_html=True)

                    if st.button("✏️ 編集", key=f"claim_edit_open_{idx}", use_container_width=True):
                        st.session_state[f"claim_editing_{idx}"] = True
                        st.rerun()

                else:
                    # 編集フォーム
                    current_content = _clean(row[COL_CLAIM_CONTENT]) if COL_CLAIM_CONTENT in row.index else ""
                    current_note    = _clean(row[COL_CLAIM_NOTE])    if COL_CLAIM_NOTE in row.index    else ""
                    current_done    = _clean(row[COL_CLAIM_DONE])    if COL_CLAIM_DONE in row.index    else ""

                    content_key = f"claim_edit_content_{idx}"
                    note_key    = f"claim_edit_note_{idx}"
                    done_key    = f"claim_edit_done_{idx}"

                    if content_key not in st.session_state:
                        st.session_state[content_key] = current_content
                    if note_key not in st.session_state:
                        st.session_state[note_key] = current_note
                    if done_key not in st.session_state:
                        st.session_state[done_key] = (current_done == "対応済み")

                    from datetime import datetime as _dt
                    def _insert_ts(key):
                        ts = _dt.now().strftime("%Y/%m/%d  %H:%M  ")
                        existing = st.session_state.get(key, "")
                        st.session_state[key] = (existing + "\n" + ts).lstrip("\n")

                    st.checkbox("対応済み", key=done_key)
                    ts_c, _ = st.columns([1, 4])
                    with ts_c:
                        if st.button("📅", key=f"ts_{idx}", use_container_width=True):
                            _insert_ts(content_key)
                            _insert_ts(note_key)
                            st.rerun()
                    if COL_CLAIM_CONTENT in row.index:
                        st.text_area("クレーム内容", key=content_key, height=80, placeholder="クレーム内容を入力...")
                    if COL_CLAIM_NOTE in row.index:
                        st.text_area("対応内容", key=note_key, height=80, placeholder="対応内容を入力...")

                    sv_col, cl_col = st.columns(2)
                    with sv_col:
                        if st.button("💾 保存", key=f"claim_save_{idx}", use_container_width=True, type="primary"):
                            with st.spinner("保存中..."):
                                if COL_CLAIM_CONTENT in row.index:
                                    write_claim_content(idx, st.session_state[content_key])
                                if COL_CLAIM_NOTE in row.index:
                                    write_claim_note(idx, st.session_state[note_key])
                                write_claim_done(idx, "対応済み" if st.session_state[done_key] else "")
                            for k in (content_key, note_key, done_key):
                                st.session_state.pop(k, None)
                            st.session_state[f"claim_editing_{idx}"] = False
                            reload(); st.success("保存しました"); st.rerun()
                    with cl_col:
                        if st.button("✕ キャンセル", key=f"claim_cancel_{idx}", use_container_width=True):
                            for k in (content_key, note_key, done_key):
                                st.session_state.pop(k, None)
                            st.session_state[f"claim_editing_{idx}"] = False
                            st.rerun()
