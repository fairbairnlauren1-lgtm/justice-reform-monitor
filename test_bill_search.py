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


def test_incremental_reconciliation_removes_updated_nonmatching_bill():
    old_bills = {
        "A": {
            "identifier": "A",
            "title": "Old justice bill",
            "abstract": "bail",
            "latest_action": "Old",
            "latest_action_date": "2026-01-01",
        },
        "B": {
            "identifier": "B",
            "title": "Unchanged bill",
            "abstract": "sentencing",
            "latest_action": "Old",
            "latest_action_date": "2026-01-01",
        },
    }

    all_bills = [
        {"identifier": "A", "title": "Old justice bill", "abstract": "highway funding"},
        {"identifier": "B", "title": "Unchanged bill", "abstract": "sentencing"},
    ]
    current_bills = [
        {
            "identifier": "B",
            "title": "Unchanged bill",
            "abstract": "sentencing",
            "latest_action": "Old",
            "latest_action_date": "2026-01-01",
        }
    ]

    database_records = dict(old_bills)
    fetched_ids = {bill.get("identifier", "") for bill in all_bills if bill.get("identifier")}
    for identifier in fetched_ids:
        database_records.pop(identifier, None)
    database_records.update({r["identifier"]: r for r in current_bills if r.get("identifier")})

    assert "A" not in database_records
    assert "B" in database_records



def test_find_matches_does_not_match_keyword_as_substring():
    bill = {
        "title": "Bailout funding for transportation",
        "abstract": "Provides emergency funding for local agencies."
    }

    assert bill_search.find_matches(bill) == {}


def test_find_matches_handles_hyphenation_consistently():
    bill = {
        "title": "Three strikes sentencing review",
        "abstract": "Updates eligibility for resentencing."
    }

    matches = bill_search.find_matches(bill)

    assert "Sentencing reform" in matches
    assert "three strikes" in matches["Sentencing reform"]
    assert "resentencing" in matches["Sentencing reform"]
