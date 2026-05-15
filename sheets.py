import csv
import os

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER_ROW = 1   # 1行目がカラム名
DATA_OFFSET = 2  # データはシートの2行目から（DataFrame index = sheet row番号）

COL_REPLIED = "返信タイプ"
COL_ORDERED = "受注"
COL_MEMO    = "連携メモ"
COL_CLAIM         = "クレーム日時"
COL_CLAIM_DONE    = "クレーム対応済み"
COL_CLAIM_CONTENT = "クレーム内容"
COL_CLAIM_NOTE    = "クレーム対応内容"


def _get_worksheet() -> gspread.Worksheet:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["sheets"]["spreadsheet_id"])
    return spreadsheet.worksheet(st.secrets["sheets"]["worksheet_name"])


def _col_index(ws: gspread.Worksheet, col_name: str) -> int:
    return ws.row_values(HEADER_ROW).index(col_name) + 1


def get_dataframe() -> pd.DataFrame:
    ws = _get_worksheet()
    values = ws.get_all_values()
    if len(values) < HEADER_ROW:
        return pd.DataFrame()
    headers = _deduplicate_headers(values[HEADER_ROW - 1])
    if len(values) <= HEADER_ROW:
        return pd.DataFrame(columns=headers)
    df = pd.DataFrame(values[HEADER_ROW:], columns=headers)
    df.index = range(DATA_OFFSET, DATA_OFFSET + len(df))
    return df


def _deduplicate_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            result.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            result.append(h)
    return result


def update_row(row_index: int, data: dict) -> None:
    ws = _get_worksheet()
    headers = ws.row_values(HEADER_ROW)
    for col_idx, header in enumerate(headers, start=1):
        ws.update_cell(row_index, col_idx, data.get(header, ""))


def add_row(data: dict) -> None:
    ws = _get_worksheet()
    headers = ws.row_values(HEADER_ROW)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")


def delete_row(row_index: int) -> None:
    ws = _get_worksheet()
    ws.delete_rows(row_index)


def _get_deleted_ws() -> gspread.Worksheet:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(st.secrets["sheets"]["spreadsheet_id"])
    return sh.worksheet("削除")


def archive_and_delete_row(row_index: int) -> None:
    from datetime import datetime
    ws = _get_worksheet()
    headers = ws.row_values(HEADER_ROW)
    row_data = ws.row_values(row_index)

    deleted_ws = _get_deleted_ws()
    existing = deleted_ws.get_all_values()
    if not existing:
        deleted_ws.append_row(headers + ["削除日時"])

    deleted_ws.append_row(row_data + [datetime.now().strftime("%Y/%m/%d %H:%M:%S")])
    ws.delete_rows(row_index)


def write_replied(row_index: int, value: str = "返信あり") -> None:
    ws = _get_worksheet()
    ws.update_cell(row_index, _col_index(ws, COL_REPLIED), value)


def write_ordered(row_index: int) -> None:
    from datetime import datetime
    ws = _get_worksheet()
    ts = datetime.now().strftime("%Y/%m/%d %H:%M")
    ws.update_cell(row_index, _col_index(ws, COL_ORDERED), ts)


def write_memo(row_index: int, memo: str) -> None:
    ws = _get_worksheet()
    ws.update_cell(row_index, _col_index(ws, COL_MEMO), memo)


def write_fields(row_index: int, data: dict) -> None:
    ws = _get_worksheet()
    headers = ws.row_values(HEADER_ROW)
    for col_name, value in data.items():
        if col_name in headers:
            ws.update_cell(row_index, headers.index(col_name) + 1, value)


def write_claim(row_index: int) -> None:
    from datetime import datetime
    ws = _get_worksheet()
    ts = datetime.now().strftime("%Y/%m/%d %H:%M")
    ws.update_cell(row_index, _col_index(ws, COL_CLAIM), ts)


def write_claim_done(row_index: int, value: str) -> None:
    ws = _get_worksheet()
    ws.update_cell(row_index, _col_index(ws, COL_CLAIM_DONE), value)


def write_claim_content(row_index: int, content: str) -> None:
    ws = _get_worksheet()
    ws.update_cell(row_index, _col_index(ws, COL_CLAIM_CONTENT), content)


def write_claim_note(row_index: int, note: str) -> None:
    ws = _get_worksheet()
    ws.update_cell(row_index, _col_index(ws, COL_CLAIM_NOTE), note)


def _get_board_ws() -> gspread.Worksheet:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(st.secrets["sheets"]["spreadsheet_id"])
    try:
        return sh.worksheet("掲示板")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="掲示板", rows=10, cols=5)
        ws.update("A1:D3", [
            ["type", "content", "color", "size"],
            ["admin", "", "#FF8C00", "中"],
            ["sales", "", "#d4d4d4", "中"],
        ])
        return ws


def get_board(board_type: str) -> dict:
    ws = _get_board_ws()
    for row in ws.get_all_values()[1:]:
        if row and row[0] == board_type:
            return {
                "content": row[1] if len(row) > 1 else "",
                "color":   row[2] if len(row) > 2 else "#d4d4d4",
                "size":    row[3] if len(row) > 3 else "中",
            }
    return {"content": "", "color": "#d4d4d4", "size": "中"}


def set_board(board_type: str, content: str, color: str, size: str) -> None:
    ws = _get_board_ws()
    rows = ws.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row and row[0] == board_type:
            ws.update(f"B{i}:D{i}", [[content, color, size]])
            return
    ws.append_row([board_type, content, color, size])


def _load_default_settings() -> list[list[str]]:
    path = os.path.join(os.path.dirname(__file__), "settings_default.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [row for row in csv.reader(f) if row]


def get_select_options() -> dict[str, list[str]]:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(st.secrets["sheets"]["spreadsheet_id"])
    try:
        ws = sh.worksheet("設定")
    except gspread.WorksheetNotFound:
        defaults = _load_default_settings()
        ws = sh.add_worksheet(title="設定", rows=max(50, len(defaults) + 10), cols=20)
        if defaults:
            ws.update("A1", defaults)
    result = {}
    for row in ws.get_all_values():
        if not row or not row[0].strip():
            continue
        col_name = row[0].strip()
        options = [v.strip() for v in row[1:] if v.strip()]
        if options:
            result[col_name] = [""] + options
    return result
