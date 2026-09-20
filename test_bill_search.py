import bill_search


def test_find_matches_is_case_insensitive():
    bill = {
        "title": "Bail Reform Act",
        "abstract": "Creates a pretrial release program."
    }

    matches = bill_search.find_matches(bill)

    assert "Bail and pretrial" in matches
    assert "bail" in matches["Bail and pretrial"]
    assert "pretrial release" in matches["Bail and pretrial"]


def test_find_matches_returns_empty_for_unrelated_bill():
    bill = {
        "title": "State Highway Funding",
        "abstract": "Provides funding for bridge maintenance."
    }

    assert bill_search.find_matches(bill) == {}


def test_find_matches_handles_missing_text():
    bill = {"title": None, "abstract": None}

    assert bill_search.find_matches(bill) == {}
