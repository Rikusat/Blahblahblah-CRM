import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER_ROW = 3   # 3行目がカラム名
DATA_OFFSET = 4  # データはシートの4行目から（DataFrame index 0 = sheet row 4）


def _get_worksheet() -> gspread.Worksheet:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["sheets"]["spreadsheet_id"])
    return spreadsheet.worksheet(st.secrets["sheets"]["worksheet_name"])


def get_dataframe() -> pd.DataFrame:
    ws = _get_worksheet()
    values = ws.get_all_values()
    if len(values) < HEADER_ROW:
        return pd.DataFrame()
    headers = _deduplicate_headers(values[HEADER_ROW - 1])  # 3行目（index 2）
    if len(values) <= HEADER_ROW:
        return pd.DataFrame(columns=headers)
    return pd.DataFrame(values[HEADER_ROW:], columns=headers)  # 4行目以降


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
    sheet_row = row_index + DATA_OFFSET
    for col_idx, header in enumerate(headers, start=1):
        ws.update_cell(sheet_row, col_idx, data.get(header, ""))


def add_row(data: dict) -> None:
    ws = _get_worksheet()
    headers = ws.row_values(HEADER_ROW)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")


def delete_row(row_index: int) -> None:
    ws = _get_worksheet()
    sheet_row = row_index + DATA_OFFSET
    ws.delete_rows(sheet_row)


def write_replied(row_index: int) -> None:
    ws = _get_worksheet()
    sheet_row = row_index + DATA_OFFSET
    ws.update_cell(sheet_row, 9, "返信あり")  # Column I = 9


def write_ordered(row_index: int) -> None:
    ws = _get_worksheet()
    sheet_row = row_index + DATA_OFFSET
    ws.update_cell(sheet_row, 11, "受注")  # Column K = 11


def write_mikomi_memo(row_index: int, memo: str) -> None:
    ws = _get_worksheet()
    sheet_row = row_index + DATA_OFFSET
    ws.update_cell(sheet_row, 10, memo)  # Column J = 10


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
