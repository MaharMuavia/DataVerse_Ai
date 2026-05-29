"""Shared upload parsing helpers for CSV and spreadsheet inputs."""
from __future__ import annotations

import csv
import io

import pandas as pd


def _decode_csv(contents: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return contents.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV file encoding is not supported")


def _detect_csv_dialect(csv_text: str) -> csv.Dialect:
    sample = csv_text[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def _read_repaired_csv(csv_text: str, dialect: csv.Dialect) -> pd.DataFrame:
    rows = list(csv.reader(io.StringIO(csv_text), dialect))
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError("Uploaded CSV does not contain any rows")

    header = rows[0]
    expected_fields = len(header)
    if expected_fields == 0 or not any(cell.strip() for cell in header):
        raise ValueError("Uploaded CSV does not contain a valid header row")

    repaired_rows = [header]
    for row in rows[1:]:
        if len(row) > expected_fields:
            row = row[: expected_fields - 1] + [dialect.delimiter.join(row[expected_fields - 1:])]
        elif len(row) < expected_fields:
            row = row + [""] * (expected_fields - len(row))
        repaired_rows.append(row)

    repaired_csv = io.StringIO()
    writer = csv.writer(repaired_csv)
    writer.writerows(repaired_rows)
    repaired_csv.seek(0)
    return pd.read_csv(repaired_csv)


def _ensure_non_empty_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty and len(df.columns) == 0:
        raise ValueError("Uploaded file does not contain any rows or columns")
    if len(df.columns) == 0:
        raise ValueError("Uploaded file does not contain any columns")
    return df


def parse_uploaded_dataframe(filename: str, contents: bytes) -> pd.DataFrame:
    filename_lower = filename.lower()
    if filename_lower.endswith(".csv"):
        csv_text = _decode_csv(contents)
        dialect = _detect_csv_dialect(csv_text)
        try:
            df = pd.read_csv(io.StringIO(csv_text), sep=dialect.delimiter)
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            df = _read_repaired_csv(csv_text, dialect)
        return _ensure_non_empty_dataframe(df)
    if filename_lower.endswith((".xlsx", ".xls")):
        try:
            return _ensure_non_empty_dataframe(pd.read_excel(io.BytesIO(contents)))
        except pd.errors.EmptyDataError as exc:
            raise ValueError("Uploaded Excel file does not contain any rows") from exc
    raise ValueError("Unsupported file format")
