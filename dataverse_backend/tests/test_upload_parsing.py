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
