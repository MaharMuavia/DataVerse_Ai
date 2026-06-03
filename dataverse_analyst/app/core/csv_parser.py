from __future__ import annotations

import csv
import io
import re
from collections import Counter
from typing import Iterable

import pandas as pd


COMMON_DELIMITERS = [",", ";", "\t", "|"]


def _decode_csv(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def _choose_delimiter(text: str) -> str:
    sample_lines = [line for line in text.splitlines()[:50] if line.strip()]
    scores = {
        delimiter: sum(line.count(delimiter) for line in sample_lines)
        for delimiter in COMMON_DELIMITERS
    }
    delimiter, count = max(scores.items(), key=lambda item: item[1])
    if count > 0:
        return delimiter
    try:
        return csv.Sniffer().sniff("\n".join(sample_lines[:20]), delimiters="".join(COMMON_DELIMITERS)).delimiter
    except Exception:
        return ","


def _clean_cell(value: str) -> str:
    return str(value).strip().strip("\ufeff")


def _non_empty_rows(rows: Iterable[list[str]]) -> list[list[str]]:
    cleaned = [[_clean_cell(cell) for cell in row] for row in rows]
    return [row for row in cleaned if any(cell for cell in row)]


def _looks_numeric(value: str) -> bool:
    if not value:
        return False
    return bool(re.fullmatch(r"[-+]?\d+([.,]\d+)?", value.strip()))


def _header_score(rows: list[list[str]], index: int, width: int) -> tuple[int, int, int]:
    row = rows[index]
    following = rows[index + 1 : index + 8]
    compatible_following = sum(1 for item in following if len(item) >= max(2, width - 1))
    text_cells = sum(1 for cell in row if cell and not _looks_numeric(cell))
    numeric_cells = sum(1 for cell in row if _looks_numeric(cell))
    return (compatible_following, text_cells, -numeric_cells)


def _dedupe_columns(columns: list[str], width: int) -> list[str]:
    if sum(1 for column in columns if column and not _looks_numeric(column)) < max(1, width // 2):
        columns = [f"column_{idx}" for idx in range(1, width + 1)]
    names: list[str] = []
    seen: Counter[str] = Counter()
    for idx in range(width):
        base = columns[idx].strip() if idx < len(columns) and columns[idx].strip() else f"column_{idx + 1}"
        seen[base] += 1
        names.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return names


def _rows_to_frame(rows: list[list[str]]) -> pd.DataFrame:
    if not rows:
        raise ValueError("CSV file does not contain any readable rows")
    width = max(len(row) for row in rows)
    candidates = [idx for idx, row in enumerate(rows) if len(row) == width]
    header_idx = max(candidates, key=lambda idx: _header_score(rows, idx, width))
    columns = _dedupe_columns(rows[header_idx], width)

    data_rows: list[list[str | None]] = []
    minimum_width = max(2, width - 1)
    for row in rows[header_idx + 1 :]:
        if len(row) < minimum_width:
            continue
        normalized = row[:width] + [None] * max(0, width - len(row))
        data_rows.append(normalized)
    if not data_rows:
        raise ValueError("CSV table section was found, but it has no data rows")
    frame = pd.DataFrame(data_rows, columns=columns)
    return frame.convert_dtypes()


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Read regular or report-style CSV bytes into a dataframe.

    Report exports often begin with two-column metadata and later contain the
    actual wider table. The fallback parser detects that table-like section
    instead of letting pandas raise a tokenizing error.
    """

    try:
        return pd.read_csv(io.BytesIO(data))
    except pd.errors.ParserError:
        pass
    except UnicodeDecodeError:
        pass

    text = _decode_csv(data)
    delimiter = _choose_delimiter(text)
    rows = _non_empty_rows(csv.reader(io.StringIO(text), delimiter=delimiter))
    return _rows_to_frame(rows)
