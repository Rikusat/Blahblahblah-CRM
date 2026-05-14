import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


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
    if not values:
        return pd.DataFrame()
    headers = _deduplicate_headers(values[0])
    if len(values) == 1:
        return pd.DataFrame(columns=headers)
    return pd.DataFrame(values[1:], columns=headers)


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


def get_headers() -> list[str]:
    ws = _get_worksheet()
    return ws.row_values(1)


def update_row(row_index: int, data: dict) -> None:
    ws = _get_worksheet()
    headers = ws.row_values(1)
    sheet_row = row_index + 2  # 1-indexed + header offset
    for col_idx, header in enumerate(headers, start=1):
        ws.update_cell(sheet_row, col_idx, data.get(header, ""))


def add_row(data: dict) -> None:
    ws = _get_worksheet()
    headers = ws.row_values(1)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")


def delete_row(row_index: int) -> None:
    ws = _get_worksheet()
    sheet_row = row_index + 2  # 1-indexed + header offset
    ws.delete_rows(sheet_row)
