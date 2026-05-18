import streamlit as st
import pandas as pd

from auth import check_password, logout
from sheets import (
    get_dataframe, update_row, add_row, delete_row, archive_and_delete_row,
    write_replied, write_ordered, write_memo, write_fields,
    write_claim, write_claim_done, write_claim_content, write_claim_note,
    write_assignee,
    get_board, set_board, get_select_options,
    DATA_OFFSET, COL_REPLIED, COL_REPLIED_AT, COL_REPLY_STATUS, COL_ORDERED, COL_MEMO,
    COL_CLAIM, COL_CLAIM_DONE, COL_CLAIM_CONTENT, COL_CLAIM_NOTE, COL_ASSIGNEE,
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
    background: #111 !important; border: 1px solid #1e1e1e !important;
    border-radius: 6px !important; padding: 0.45rem 0.55rem !important;
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

N_CARDS_PER_ROW = 4

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    return get_dataframe()

@st.cache_data(ttl=30)
def load_board_data(board_type: str) -> dict:
    return get_board(board_type)

@st.cache_data(ttl=300)
def load_select_options() -> dict:
    return get_select_options()

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

def _val(row: pd.Series, col: str | None) -> str:
    if not col or col not in row.index:
        return ""
    v = str(row[col]).strip()
    return "" if v in ("nan", "None") else v

# 設定シートから全設定を読み込み、アプリ設定キーとフォーム選択肢に分離
_APP_CONFIG_KEYS = {"月間目標", "テキストエリア列"}
_TS_FIELD_KEYS   = {COL_ORDERED, COL_CLAIM}   # タイムスタンプ入力フィールド（セレクトボックス化しない）
_raw_settings: dict[str, list[str]] = load_select_options()

SELECT_OPTIONS: dict[str, list[str]] = {
    k: v for k, v in _raw_settings.items()
    if k not in _APP_CONFIG_KEYS and k not in _TS_FIELD_KEYS
}
TEXTAREA_KEYWORDS: set[str] = (
    set(_raw_settings["テキストエリア列"][1:])
    if "テキストエリア列" in _raw_settings
    else {"備考", "メモ", "次回アクション", "notes", "memo", "コメント"}
)
_MONTHLY_TARGET: int = (
    int(_raw_settings["月間目標"][1])
    if "月間目標" in _raw_settings and len(_raw_settings["月間目標"]) > 1
    else 10
)

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
            monthly_target = _MONTHLY_TARGET
            ordered_count = 0
            if COL_ORDERED in df.columns:
                ordered_count = int(df[COL_ORDERED].astype(str).str.strip().replace("nan", "").ne("").sum())
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
            if st.button("管理者ログアウト", use_container_width=True, key="admin_lock"):
                st.session_state["admin_mode"] = False
                st.session_state.pop("show_admin_input", None)
                st.rerun()
        else:
            if st.button("🔑 管理者モード", use_container_width=True, key="admin_btn"):
                st.session_state["show_admin_input"] = True

            if st.session_state.get("show_admin_input"):
                admin_pw = st.text_input("管理者パスワード", type="password", key="admin_pw_input", label_visibility="collapsed", placeholder="管理者パスワード")
                if st.button("ログイン", use_container_width=True, key="admin_unlock_btn", type="primary"):
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

    monthly_target = _MONTHLY_TARGET
    ordered_count = 0
    if COL_ORDERED in df.columns:
        ordered_count = int(df[COL_ORDERED].astype(str).str.strip().replace("nan", "").ne("").sum())
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
        from datetime import datetime as _dt
        _prefix = f"edit_{selected_idx}"

        def _ts_field(col_name: str, ts_key_suffix: str):
            _key     = f"{_prefix}__{col_name}"
            _pending = f"{_prefix}__{ts_key_suffix}_pending"
            _default = str(row_data.get(col_name, ""))
            if _default in ("nan", "None"):
                _default = ""
            if _pending in st.session_state:
                st.session_state[_key] = st.session_state.pop(_pending)
            fi_col, btn_col = st.columns([7, 1])
            with fi_col:
                val = st.text_input(col_name, key=_key,
                                    value=st.session_state.get(_key, _default))
            with btn_col:
                st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
                if st.button("📅", key=f"ts_{ts_key_suffix}_edit"):
                    _ts = _dt.now().strftime("%Y/%m/%d %H:%M")
                    st.session_state[_pending] = (st.session_state.get(_key, _default) + "\n" + _ts).lstrip("\n")
                    st.rerun()
            return val

        edited = {}
        _ts_cols  = {COL_ORDERED, COL_CLAIM}
        _claim_group = [COL_CLAIM, COL_CLAIM_CONTENT, COL_CLAIM_DONE, COL_CLAIM_NOTE]
        base_cols = [c for c in edit_cols if c not in _claim_group and c not in _ts_cols]
        edited.update(render_fields(base_cols, defaults=row_data, key_prefix=_prefix))

        # 受注日（タイムスタンプボタン付き）
        if COL_ORDERED in edit_cols:
            edited[COL_ORDERED] = _ts_field(COL_ORDERED, "ordered")

        # クレーム系フィールドを指定順でレンダリング
        for _col in [c for c in _claim_group if c in edit_cols]:
            if _col == COL_CLAIM:
                edited[COL_CLAIM] = _ts_field(COL_CLAIM, "claim")
            else:
                edited.update(render_fields([_col], defaults=row_data, key_prefix=_prefix))

        if st.button("💾 保存", use_container_width=True, type="primary", key="edit_save_btn"):
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

    if not st.session_state.get("admin_mode"):
        b1, b2 = st.columns(2)
        with b1:
            if st.button("📩 返信あり", use_container_width=True, key="btn_replied"):
                st.session_state["reply_selecting"] = selected_idx
                st.rerun()
        with b2:
            if st.button("🏆 受注", use_container_width=True, key="btn_ordered"):
                st.session_state["order_selecting"] = selected_idx
                st.rerun()

        if st.session_state.get("order_selecting") == selected_idx:
            st.markdown("<div style='font-size:.7rem;color:#adadad;font-family:monospace;letter-spacing:2px;margin:.6rem 0 .3rem;'>受注商品を選択</div>", unsafe_allow_html=True)
            _order_opts = [v for v in SELECT_OPTIONS.get("受注商品", []) if v]
            _order_items = [(opt, opt) for opt in _order_opts] + [("✕", "cancel")]
            for col, (label, value) in zip(st.columns(len(_order_items)), _order_items):
                with col:
                    if st.button(label, use_container_width=True, key=f"order_opt_{value}_{selected_idx}"):
                        if value == "cancel":
                            st.session_state.pop("order_selecting", None)
                        else:
                            with st.spinner("更新中..."):
                                write_ordered(selected_idx)
                                write_fields(selected_idx, {"受注商品": value})
                            st.session_state.pop("order_selecting", None)
                            reload(); st.success(f"受注（{value}）を記録しました"); st.rerun()

        if st.session_state.get("reply_selecting") == selected_idx:
            st.markdown("<div style='font-size:.7rem;color:#adadad;font-family:monospace;letter-spacing:2px;margin:.6rem 0 .3rem;'>返信ステータスを選択</div>", unsafe_allow_html=True)
            _reply_opts = [v for v in SELECT_OPTIONS.get(COL_REPLIED, []) if v]
            _reply_items = [(opt, opt) for opt in _reply_opts] + [("⚠️ クレーム", None), ("✕", "cancel")]
            for col, (label, value) in zip(st.columns(len(_reply_items)), _reply_items):
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
    mikomi = df[df[COL_REPLIED].astype(str).str.strip().replace("nan", "").ne("")]
    if COL_REPLIED_AT in mikomi.columns:
        mikomi = mikomi.sort_values(COL_REPLIED_AT, ascending=False)
    else:
        mikomi = mikomi.sort_index(ascending=False)

    st.caption(f"返信あり：{len(mikomi)} 件")

    if mikomi.empty:
        st.info("返信ありの顧客はまだいません。")
        st.stop()

    name_col        = find_col(mikomi, "事業所名", "会社名", "担当者名", "名前")
    ind_col         = find_col(mikomi, "業種")
    person_col      = find_col(mikomi, "担当者名", "担当者名/代表者名", "代表者名")
    email_col       = find_col(mikomi, "メールアドレス", "メール")
    url_col         = find_col(mikomi, "URL", "url", "ウェブサイト")
    next_action_col = "次回アクション" if "次回アクション" in mikomi.columns else None


    cols = st.columns(N_CARDS_PER_ROW, gap="small")
    for n_row, (idx, row) in enumerate(mikomi.iterrows()):
        i = n_row % N_CARDS_PER_ROW
        if i == 0 and n_row > 0:
            cols = st.columns(N_CARDS_PER_ROW, gap="small")
        with cols[i]:
            with st.container(border=True):
                _name        = _val(row, name_col) or f"#{idx}"
                _replied     = _val(row, COL_REPLIED)
                _claim       = _val(row, COL_CLAIM)
                _next_act    = _val(row, next_action_col)
                _replied_at    = _val(row, COL_REPLIED_AT)
                _reply_status  = _val(row, COL_REPLY_STATUS) if COL_REPLY_STATUS in row.index else ""
                _assignee      = _val(row, COL_ASSIGNEE) if COL_ASSIGNEE in row.index else ""

                st.markdown(
                    f"<div style='font-weight:700;font-size:.82rem;font-family:monospace;"
                    f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:.2rem;"
                    f"' title='{_name}'>{_name}</div>",
                    unsafe_allow_html=True,
                )
                _pills = ""
                if _replied:
                    _pills += (
                        f"<span style='font-size:.6rem;background:#1a1200;border:1px solid #2a2200;"
                        f"border-radius:3px;padding:.1rem .35rem;color:#FF8C00;font-family:monospace;"
                        f"margin-right:.25rem;'>{_replied}</span>"
                    )
                if _claim:
                    _pills += (
                        f"<span style='font-size:.6rem;background:#1a0000;border:1px solid #3a0000;"
                        f"border-radius:3px;padding:.1rem .35rem;color:#EC2D01;font-family:monospace;'>⚠️</span>"
                    )
                if _pills:
                    st.markdown(f"<div style='margin-bottom:.2rem;'>{_pills}</div>", unsafe_allow_html=True)
                if _replied_at:
                    st.markdown(
                        f"<div style='font-size:.65rem;font-family:monospace;color:#888;"
                        f"margin-bottom:.2rem;'>返信日時 {_replied_at}</div>",
                        unsafe_allow_html=True,
                    )
                if _reply_status:
                    st.markdown(
                        f"<div style='font-size:.65rem;font-family:monospace;color:#a0c4ff;"
                        f"margin-bottom:.2rem;'>返信状態 {_reply_status}</div>",
                        unsafe_allow_html=True,
                    )
                if _next_act:
                    st.markdown(
                        f"<div style='font-size:.65rem;font-family:monospace;color:#7ab3ff;"
                        f"margin-bottom:.2rem;'>次回アクション {_next_act}</div>",
                        unsafe_allow_html=True,
                    )
                if _assignee:
                    st.markdown(
                        f"<div style='font-size:.65rem;font-family:monospace;color:#2FFFB4;"
                        f"margin-bottom:.2rem;'>👤 担当：{_assignee}</div>",
                        unsafe_allow_html=True,
                    )

                _assign_key = f"assigning_{idx}"
                _is_open    = (st.session_state.get("det_mikomi_open") == idx) or st.session_state.get(_assign_key, False)
                if st.button("閉じる ▲" if _is_open else "詳細 ▼", key=f"det_btn_mikomi_{idx}", use_container_width=True):
                    if _is_open:
                        st.session_state["det_mikomi_open"] = None
                        st.session_state.pop(_assign_key, None)
                    else:
                        st.session_state["det_mikomi_open"] = idx
                    st.rerun()

                if _is_open:
                    st.markdown("<div style='border-top:1px solid #222;margin:.3rem 0 .2rem;'></div>", unsafe_allow_html=True)
                    if _val(row, ind_col):
                        st.caption(f"🏢 {_val(row, ind_col)}")
                    if person_col != name_col and _val(row, person_col):
                        st.caption(f"👤 {_val(row, person_col)}")
                    if _val(row, email_col):
                        st.caption(f"📧 {_val(row, email_col)}")
                    if _val(row, url_col):
                        _u = _val(row, url_col)
                        st.markdown(f"<div style='font-size:.72rem;font-family:monospace;word-break:break-all;'>🔗 <a href='{_u}' target='_blank'>{_u}</a></div>", unsafe_allow_html=True)
                    if _claim:
                        st.caption(f"⚠️ クレーム：{_claim}")
                    if memo_col:
                        _memo = _val(row, memo_col)
                        if _memo:
                            st.markdown("<div style='border-top:1px solid #1e1e1e;margin:.25rem 0;'></div>", unsafe_allow_html=True)
                            st.markdown(
                                f"<div style='color:#bbb;font-family:monospace;font-size:.72rem;"
                                f"white-space:pre-wrap;'>{_memo[:200]}{'…' if len(_memo) > 200 else ''}</div>",
                                unsafe_allow_html=True,
                            )
                    # 担当者引き受けUI
                    st.markdown("<div style='border-top:1px solid #1e1e1e;margin:.3rem 0 .2rem;'></div>", unsafe_allow_html=True)
                    if _assignee:
                        pass
                    elif st.session_state.get(_assign_key):
                        _assignee_opts = [v for v in SELECT_OPTIONS.get(COL_ASSIGNEE, []) if v]
                        if _assignee_opts:
                            _sel = st.selectbox("担当者を選択", _assignee_opts, key=f"assignee_sel_{idx}", label_visibility="collapsed")
                            _ac1, _ac2 = st.columns(2)
                            with _ac1:
                                if st.button("✅ 引き受ける", key=f"assignee_confirm_{idx}", type="primary", use_container_width=True):
                                    with st.spinner("保存中..."):
                                        write_assignee(idx, _sel)
                                    st.session_state.pop(_assign_key, None)
                                    reload(); st.success(f"担当：{_sel}"); st.rerun()
                            with _ac2:
                                if st.button("✕ キャンセル", key=f"assignee_cancel_{idx}", use_container_width=True):
                                    st.session_state.pop(_assign_key, None)
                                    st.rerun()
                        else:
                            st.caption("設定シートに担当者リストがありません")
                            if st.button("✕", key=f"assignee_cancel_{idx}", use_container_width=True):
                                st.session_state.pop(_assign_key, None)
                                st.rerun()
                    else:
                        if st.button("🙋 担当者引き受け", key=f"assignee_btn_{idx}", use_container_width=True):
                            st.session_state[_assign_key] = True
                            st.session_state["det_mikomi_open"] = idx
                            st.rerun()

                    if st.button("✏️", key=f"mikomi_edit_{idx}", use_container_width=True):
                        st.session_state["mikomi_editing_idx"] = idx
                        st.rerun()

    # --- 編集フォーム ---
    editing_idx = st.session_state.get("mikomi_editing_idx")
    if editing_idx is not None and editing_idx in mikomi.index:
        st.divider()
        st.subheader("MEMO")

        label_col_e = find_col(mikomi, "事業所名", "担当者名", "担当者名/代表者名", "名前", "会社名")
        label = f"#{editing_idx}  {mikomi.loc[editing_idx, label_col_e]}" if label_col_e else f"#{editing_idx}"
        st.caption(f"編集中：{label}")

        _rs_opts = [v for v in SELECT_OPTIONS.get(COL_REPLY_STATUS, []) if v]
        if _rs_opts and COL_REPLY_STATUS in df.columns:
            _rs_cur = str(df.loc[editing_idx, COL_REPLY_STATUS]) if COL_REPLY_STATUS in df.columns else ""
            if _rs_cur in ("nan", "None"):
                _rs_cur = ""
            _rs_index = _rs_opts.index(_rs_cur) if _rs_cur in _rs_opts else 0
            st.selectbox("返信状態", _rs_opts, index=_rs_index, key=f"mikomi_rs_{editing_idx}")

        _textarea_cols = [c for c in df.columns if c in TEXTAREA_KEYWORDS]

        for _col in _textarea_cols:
            _fkey  = f"mikomi_field_{editing_idx}_{_col}"
            _pkey  = f"mikomi_field_pending_{editing_idx}_{_col}"
            _cur   = str(df.loc[editing_idx, _col]) if _col in df.columns else ""
            if _cur in ("nan", "None"):
                _cur = ""
            if _pkey in st.session_state:
                st.session_state[_fkey] = st.session_state.pop(_pkey)
            if _fkey not in st.session_state:
                st.session_state[_fkey] = _cur

            _fa, _fb = st.columns([8, 1])
            with _fa:
                st.text_area(_col, key=_fkey, height=150, placeholder=f"{_col}を入力...")
            with _fb:
                st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
                if st.button("📅", key=f"ts_mikomi_{editing_idx}_{_col}"):
                    _ts = datetime.now().strftime("%Y/%m/%d  %H:%M  ")
                    st.session_state[_pkey] = (st.session_state.get(_fkey, _cur) + "\n" + _ts).lstrip("\n")
                    st.rerun()

        sv_col, cl_col = st.columns(2)
        with sv_col:
            if st.button("💾 保存", type="primary", use_container_width=True, key="save_memo_btn"):
                _save_data = {
                    _col: st.session_state.get(f"mikomi_field_{editing_idx}_{_col}", "")
                    for _col in _textarea_cols if _col in df.columns
                }
                _rs_val = st.session_state.get(f"mikomi_rs_{editing_idx}")
                if _rs_val and COL_REPLY_STATUS in df.columns:
                    _save_data[COL_REPLY_STATUS] = _rs_val
                    if _rs_val == "未返信" and COL_REPLIED_AT in df.columns:
                        _save_data[COL_REPLIED_AT] = ""
                with st.spinner("保存中..."):
                    write_fields(editing_idx, _save_data)
                reload()
                st.success("保存しました")
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

    orders = df[df[COL_ORDERED].astype(str).str.strip().replace("nan", "").ne("")].sort_values(COL_ORDERED, ascending=False)

    st.caption(f"受注：{len(orders)} 件")

    if orders.empty:
        st.info("受注済みの顧客はまだいません。")
        st.stop()

    name_col    = find_col(orders, "事業所名", "会社名", "担当者名", "名前")
    ind_col     = find_col(orders, "業種")
    person_col  = find_col(orders, "担当者名", "担当者名/代表者名", "代表者名")
    email_col   = find_col(orders, "メールアドレス", "メール")
    url_col     = find_col(orders, "URL", "url", "ウェブサイト")
    product_col = find_col(orders, "受注商品")

    cols = st.columns(N_CARDS_PER_ROW, gap="small")
    for n_row, (idx, row) in enumerate(orders.iterrows()):
        i = n_row % N_CARDS_PER_ROW
        if i == 0 and n_row > 0:
            cols = st.columns(N_CARDS_PER_ROW, gap="small")
        with cols[i]:
            with st.container(border=True):
                _name    = _val(row, name_col) or f"#{idx}"
                _ordered = _val(row, COL_ORDERED)
                _prod    = _val(row, product_col)

                st.markdown(
                    f"<div style='font-weight:700;font-size:.82rem;font-family:monospace;"
                    f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:.2rem;"
                    f"' title='{_name}'>{_name}</div>",
                    unsafe_allow_html=True,
                )
                _pills = ""
                if _ordered:
                    _pills += (
                        f"<span style='font-size:.6rem;background:#001a00;border:1px solid #002a00;"
                        f"border-radius:3px;padding:.1rem .35rem;color:#2FFFB4;font-family:monospace;"
                        f"margin-right:.25rem;'>🏆 受注日時 {_ordered}</span>"
                    )
                if _prod:
                    _pills += (
                        f"<span style='font-size:.6rem;background:#1a1a1a;border:1px solid #2a2a2a;"
                        f"border-radius:3px;padding:.1rem .35rem;color:#adadad;font-family:monospace;"
                        f"'>📦 {_prod}</span>"
                    )
                if _pills:
                    st.markdown(f"<div style='margin-bottom:.2rem;'>{_pills}</div>", unsafe_allow_html=True)

                _is_open = (st.session_state.get("det_order_open") == idx)
                if st.button("閉じる ▲" if _is_open else "詳細 ▼", key=f"det_btn_order_{idx}", use_container_width=True):
                    st.session_state["det_order_open"] = None if _is_open else idx
                    st.rerun()

                if _is_open:
                    st.markdown("<div style='border-top:1px solid #222;margin:.3rem 0 .2rem;'></div>", unsafe_allow_html=True)
                    if _val(row, ind_col):
                        st.caption(f"🏢 {_val(row, ind_col)}")
                    if person_col != name_col and _val(row, person_col):
                        st.caption(f"👤 {_val(row, person_col)}")
                    if _val(row, email_col):
                        st.caption(f"📧 {_val(row, email_col)}")
                    if _val(row, url_col):
                        _u = _val(row, url_col)
                        st.markdown(f"<div style='font-size:.72rem;font-family:monospace;word-break:break-all;'>🔗 <a href='{_u}' target='_blank'>{_u}</a></div>", unsafe_allow_html=True)

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

    def _clean(v) -> str:
        s = str(v)
        return "" if s in ("nan", "None") else s

    cols = st.columns(N_CARDS_PER_ROW, gap="small")
    for n_row, (idx, row) in enumerate(claims.iterrows()):
        i = n_row % N_CARDS_PER_ROW
        if i == 0 and n_row > 0:
            cols = st.columns(N_CARDS_PER_ROW, gap="small")

        with cols[i]:
            with st.container(border=True):
                _name     = _val(row, name_col) or f"#{idx}"
                _claim_ts = _val(row, COL_CLAIM)
                _done     = _val(row, COL_CLAIM_DONE) if COL_CLAIM_DONE in row.index else ""
                _done_icon = "✅" if _done == "対応済み" else "🔴"

                st.markdown(
                    f"<div style='font-weight:700;font-size:.82rem;font-family:monospace;"
                    f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:.15rem;"
                    f"' title='{_name}'>{_name}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='font-size:.65rem;font-family:monospace;color:#888;margin-bottom:.2rem;'>"
                    f"{_done_icon}&nbsp;<span style='color:#555;'>{_claim_ts}</span></div>",
                    unsafe_allow_html=True,
                )

                _is_editing = st.session_state.get(f"claim_editing_{idx}", False)
                _is_detail  = (st.session_state.get("det_claim_open") == idx)
                _show       = _is_detail or _is_editing

                if st.button("閉じる ▲" if _show else "詳細 ▼", key=f"det_btn_claim_{idx}", use_container_width=True):
                    if _show:
                        st.session_state["det_claim_open"] = None
                        for _k in (f"claim_editing_{idx}", f"claim_edit_content_{idx}", f"claim_edit_note_{idx}", f"claim_edit_done_{idx}"):
                            st.session_state.pop(_k, None)
                    else:
                        st.session_state["det_claim_open"] = idx
                    st.rerun()

                if _show:
                    st.markdown("<div style='border-top:1px solid #222;margin:.3rem 0 .2rem;'></div>", unsafe_allow_html=True)

                    if not _is_editing:
                        if _val(row, ind_col):
                            st.caption(f"🏢 {_val(row, ind_col)}")
                        if person_col != name_col and _val(row, person_col):
                            st.caption(f"👤 {_val(row, person_col)}")
                        if _val(row, email_col):
                            st.caption(f"📧 {_val(row, email_col)}")
                        if _val(row, url_col):
                            _u = _val(row, url_col)
                            st.markdown(f"<div style='font-size:.72rem;font-family:monospace;word-break:break-all;'>🔗 <a href='{_u}' target='_blank'>{_u}</a></div>", unsafe_allow_html=True)

                        _content_v = _val(row, COL_CLAIM_CONTENT) if COL_CLAIM_CONTENT in row.index else ""
                        _note_v    = _val(row, COL_CLAIM_NOTE)    if COL_CLAIM_NOTE in row.index    else ""
                        if _content_v:
                            st.markdown("<div style='font-size:.65rem;color:#adadad;font-family:monospace;margin-top:.25rem;'>クレーム内容</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#c2c2c2;font-family:monospace;font-size:.72rem;white-space:pre-wrap;margin-bottom:.25rem;'>{_content_v}</div>", unsafe_allow_html=True)
                        if _note_v:
                            st.markdown("<div style='font-size:.65rem;color:#adadad;font-family:monospace;margin-top:.25rem;'>対応内容</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#c2c2c2;font-family:monospace;font-size:.72rem;white-space:pre-wrap;margin-bottom:.25rem;'>{_note_v}</div>", unsafe_allow_html=True)

                        if st.button("✏️ 編集", key=f"claim_edit_open_{idx}", use_container_width=True):
                            st.session_state[f"claim_editing_{idx}"] = True
                            st.rerun()

                    else:
                        _cur_content = _val(row, COL_CLAIM_CONTENT) if COL_CLAIM_CONTENT in row.index else ""
                        _cur_note    = _val(row, COL_CLAIM_NOTE)    if COL_CLAIM_NOTE in row.index    else ""
                        _cur_done    = _val(row, COL_CLAIM_DONE)    if COL_CLAIM_DONE in row.index    else ""

                        _ck = f"claim_edit_content_{idx}"
                        _nk = f"claim_edit_note_{idx}"
                        _dk = f"claim_edit_done_{idx}"

                        if _ck not in st.session_state: st.session_state[_ck] = _cur_content
                        if _nk not in st.session_state: st.session_state[_nk] = _cur_note
                        if _dk not in st.session_state: st.session_state[_dk] = (_cur_done == "対応済み")

                        from datetime import datetime as _dt
                        def _insert_ts(key):
                            ts = _dt.now().strftime("%Y/%m/%d  %H:%M  ")
                            existing = st.session_state.get(key, "")
                            st.session_state[key] = (existing + "\n" + ts).lstrip("\n")

                        st.checkbox("対応済み", key=_dk)
                        if st.button("📅", key=f"ts_{idx}", use_container_width=True):
                            _insert_ts(_ck)
                            _insert_ts(_nk)
                            st.rerun()
                        if COL_CLAIM_CONTENT in row.index:
                            st.text_area("クレーム内容", key=_ck, height=80, placeholder="クレーム内容を入力...")
                        if COL_CLAIM_NOTE in row.index:
                            st.text_area("対応内容", key=_nk, height=80, placeholder="対応内容を入力...")

                        sv_col, cl_col = st.columns(2)
                        with sv_col:
                            if st.button("💾 保存", key=f"claim_save_{idx}", use_container_width=True, type="primary"):
                                with st.spinner("保存中..."):
                                    if COL_CLAIM_CONTENT in row.index:
                                        write_claim_content(idx, st.session_state[_ck])
                                    if COL_CLAIM_NOTE in row.index:
                                        write_claim_note(idx, st.session_state[_nk])
                                    write_claim_done(idx, "対応済み" if st.session_state[_dk] else "")
                                for _k in (_ck, _nk, _dk):
                                    st.session_state.pop(_k, None)
                                st.session_state[f"claim_editing_{idx}"] = False
                                reload(); st.success("保存しました"); st.rerun()
                        with cl_col:
                            if st.button("✕ キャンセル", key=f"claim_cancel_{idx}", use_container_width=True):
                                for _k in (_ck, _nk, _dk):
                                    st.session_state.pop(_k, None)
                                st.session_state[f"claim_editing_{idx}"] = False
                                st.rerun()
