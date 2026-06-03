from app.api.upload_parsing import parse_uploaded_dataframe


def test_parse_uploaded_dataframe_repairs_ragged_csv_rows():
    csv_bytes = (
        b"id,description\n"
        b"1,plain item\n"
        b"2,item with, unquoted, commas\n"
    )

    df = parse_uploaded_dataframe("products.csv", csv_bytes)

    assert list(df.columns) == ["id", "description"]
    assert len(df) == 2
    assert df.loc[1, "description"] == "item with, unquoted, commas"


def test_parse_uploaded_dataframe_rejects_empty_csv_after_parsing():
    try:
        parse_uploaded_dataframe("empty.csv", b"")
    except ValueError as exc:
        assert "does not contain any rows" in str(exc)
    else:
        raise AssertionError("empty CSV should be rejected")


def test_parse_uploaded_dataframe_extracts_sectioned_ai_khata_report():
    csv_bytes = (
        b'"AI Khata Report"\n'
        b'"Shop Name","Muhammad Muavia"\n'
        b'"Report Filter","all"\n'
        b'"Generated At","2026-05-01 11:43:47"\n'
        b'\n'
        b'"Summary"\n'
        b'"Total Sales","5000"\n'
        b'"Total Expenses","0"\n'
        b'"Udhaar Outstanding","300"\n'
        b'"Net Profit","5000"\n'
        b'"Profit Status","Profit"\n'
        b'\n'
        b'"Transaction Details"\n'
        b'"Date","Time","Category","Item/Customer","Amount (Rs)"\n'
        b'"2026-05-01","11:43:40","UDHAAR","Ali","100"\n'
        b'"2026-05-01","11:43:23","UDHAAR","N/A","200"\n'
        b'"2026-05-01","11:43:10","SALES","General Entry","5000"\n'
    )

    df = parse_uploaded_dataframe("AI_Khata_report.csv", csv_bytes)

    assert list(df.columns) == ["Date", "Time", "Category", "Item/Customer", "Amount (Rs)"]
    assert len(df) == 3
    assert df.loc[0, "Category"] == "UDHAAR"
    assert df.loc[2, "Amount (Rs)"] == 5000
    assert df.attrs["report_metadata"]["Shop Name"] == "Muhammad Muavia"
    assert df.attrs["report_summary"]["Net Profit"] == "5000"
