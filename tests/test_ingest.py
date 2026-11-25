from policylens.ingest import clean_lines, parse_requirements

LINES = [
    "Requirement 6: Develop and Maintain Secure Systems",
    "6.2 Bespoke software is developed securely",
    "6.2.1 Software is developed based on industry standards",
    "and best practices.",
    "Page 41",
    "6.2.2 Developers are trained at least every 12 months.",
    "7.1 Access is restricted",
    "6.2.1 Testing procedure repeats the id with more text.",
]


def test_filters_by_top_level_and_groups_text():
    reqs = parse_requirements(clean_lines(LINES, [r"^Page \d+$"]), "std", ["6"])
    ids = [r["req_id"] for r in reqs]
    assert ids == ["6.2", "6.2.1", "6.2.2"]
    assert "best practices" in reqs[1]["text"]
    assert "Page 41" not in reqs[1]["text"]


def test_duplicate_ids_are_merged():
    reqs = parse_requirements(LINES, "std", ["6"])
    r = [x for x in reqs if x["req_id"] == "6.2.1"]
    assert len(r) == 1
    assert "repeats the id" in r[0]["text"]


def test_no_filter_keeps_everything():
    ids = [r["req_id"] for r in parse_requirements(LINES, "std")]
    assert "7.1" in ids


def test_other_top_level_text_not_leaked():
    reqs = parse_requirements(LINES, "std", ["6"])
    assert all("restricted" not in r["text"] for r in reqs)
