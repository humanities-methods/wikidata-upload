import argparse

import pytest

import hml_quickstatements as hml

# --- the command line argument: only whole numbers above zero are accepted ---


def test_issue_number_accepts_one():
    assert hml.issue_number("1") == 1


def test_issue_number_rejects_zero():
    with pytest.raises(argparse.ArgumentTypeError, match="must be 1 or greater"):
        hml.issue_number("0")


def test_issue_number_rejects_negative_one():
    with pytest.raises(argparse.ArgumentTypeError, match="must be 1 or greater"):
        hml.issue_number("-1")


def test_issue_number_rejects_words():
    with pytest.raises(ValueError):
        hml.issue_number("abc")


# --- small hand-made copies of the two outside sources ---

READ = "https://cuny.manifoldapp.org/read/"


def coins(title, issue, authors):
    """Build the citation <span> that the feed puts at the top of each article."""
    fields = f"rft.atitle={title}&amp;rft.issue={issue}"
    for author in authors:
        fields += f"&amp;rft.au={author}"
    return f'<span class="Z3988" title="{fields.replace(" ", "%20")}"></span>'


def feed_item(feed_title, slug, pub_date, body):
    return f"""<item>
      <title>{feed_title}</title>
      <link>{READ}{slug}</link>
      <description><![CDATA[<!DOCTYPE html>{body}<p>Text</p>]]></description>
      <pubDate>{pub_date}</pubDate>
    </item>"""


FEED = f"""<?xml version='1.0' encoding='UTF-8'?>
<rss version="2.0"><channel><title>Humanities Methods in Librarianship</title>
{feed_item("Submissions (Issue 0)", "submissions", "Wed, 08 Oct 2025 13:59:25 +0000", "")}
{feed_item("Zero With Citation (Issue 0)", "zero-with-citation", "Wed, 08 Oct 2025 13:59:25 +0000", coins("Zero With Citation", 0, ["Zero, Zed"]))}
{feed_item("Draft Piece (Issue -1)", "draft-piece", "Wed, 08 Oct 2025 13:59:25 +0000", coins("Draft Piece", -1, ["Draft, Dee"]))}
{feed_item("Title Says One (Issue 1)", "title-says-one", "Wed, 08 Oct 2025 13:59:25 +0000", coins("Title Says One", 0, ["Mix, Max"]))}
{feed_item("Citation Says One (Issue 0)", "citation-says-one", "Wed, 08 Oct 2025 13:59:25 +0000", coins("Citation Says One", 1, ["Mix, Max"]))}
{feed_item("Care and Compliance (Issue 1)", "care-d3f5", "Fri, 23 Oct 2026 16:38:58 +0000", coins("Care and Compliance", 1, ["Bell, Scout"]))}
{feed_item("Review of Triptych (Issue 1)", "triptych-dcee", "Thu, 17 Sep 2026 16:21:14 +0000", coins("Review of Triptych", 1, ["Blechinger, Joel"]))}
{feed_item("Editorial (Issue 1)", "editorial-818c", "Tue, 27 Oct 2026 12:18:31 +0000", coins("Editorial", 1, []))}
{feed_item("Ode (Issue 1)", "ode-3a52", "Fri, 18 Sep 2026 13:11:57 +0000", coins("Ode", 1, ["Francis, Sean", "Rowe-Morris, J. Morgan"]))}
{feed_item("Next Year (Issue 2)", "next-year", "Mon, 01 Mar 2027 10:00:00 +0000", coins("Next Year", 2, ["Later, Lee"]))}
</channel></rss>"""

ISSUES = {
    "data": [
        {"attributes": {"number": "1", "projectSlug": "hml-no-1"}},
        {"attributes": {"number": "0", "projectSlug": "hml-no-0"}},
        {"attributes": {"number": "-1", "projectSlug": "hml-no-1-116dd5c9"}},
    ]
}


def api_text(slug, category_id):
    return {
        "type": "texts",
        "attributes": {"slug": slug},
        "relationships": {"category": {"data": {"id": category_id}}},
    }


PROJECT = {
    "included": [
        {"type": "categories", "id": "cat-ed", "attributes": {"title": "Editorial"}},
        {
            "type": "categories",
            "id": "cat-pr",
            "attributes": {"title": "Peer Reviewed"},
        },
        {"type": "categories", "id": "cat-cr", "attributes": {"title": "CREATIVE"}},
        {"type": "categories", "id": "cat-br", "attributes": {"title": "Book Reviews"}},
        {"type": "users", "id": "u1", "attributes": {}},
        api_text("care-d3f5", "cat-pr"),
        api_text("triptych-dcee", "cat-br"),
        api_text("editorial-818c", "cat-ed"),
        api_text("ode-3a52", "cat-cr"),
    ]
}


# --- reading the feed ---


def test_feed_articles_returns_only_the_requested_issue():
    urls = [article["url"] for article in hml.feed_articles(FEED, 1)]
    assert urls == [
        READ + "care-d3f5",
        READ + "triptych-dcee",
        READ + "editorial-818c",
        READ + "ode-3a52",
    ]


def test_feed_articles_can_select_a_later_issue():
    urls = [article["url"] for article in hml.feed_articles(FEED, 2)]
    assert urls == [READ + "next-year"]


def test_feed_articles_reads_title_date_and_issue():
    article = hml.feed_articles(FEED, 1)[0]
    assert article["title"] == "Care and Compliance"
    assert article["date"] == "2026-10-23"
    assert article["issue"] == 1


def test_feed_articles_puts_given_name_before_family_name():
    article = hml.feed_articles(FEED, 1)[0]
    assert article["authors"] == ["Scout Bell"]


def test_feed_articles_keeps_several_authors_in_feed_order():
    article = hml.feed_articles(FEED, 1)[3]
    assert article["authors"] == ["Sean Francis", "J. Morgan Rowe-Morris"]


def test_feed_articles_gives_editorial_no_authors():
    article = hml.feed_articles(FEED, 1)[2]
    assert article["authors"] == []


# --- reading the Manifold API ---


def test_project_slug_finds_issue_one_not_the_draft_numbered_minus_one():
    assert hml.project_slug(ISSUES, 1) == "hml-no-1"


def test_project_slug_stops_when_issue_is_not_on_manifold():
    with pytest.raises(SystemExit, match="Issue 2 was not found on Manifold"):
        hml.project_slug(ISSUES, 2)


def test_text_categories_maps_each_text_slug_to_its_category():
    assert hml.text_categories(PROJECT) == {
        "care-d3f5": "Peer Reviewed",
        "triptych-dcee": "Book Reviews",
        "editorial-818c": "Editorial",
        "ode-3a52": "CREATIVE",
    }


# --- writing the QuickStatements batch ---

CATEGORIES = {
    "care-d3f5": "Peer Reviewed",
    "triptych-dcee": "Book Reviews",
    "editorial-818c": "Editorial",
    "ode-3a52": "CREATIVE",
}

CARE = {
    "title": "Care and Compliance",
    "url": READ + "care-d3f5",
    "issue": 1,
    "authors": ["Scout Bell"],
    "date": "2026-10-23",
}

SOURCE = f'\tS854\t"{READ}care-d3f5"\tS813\t+2026-11-15T00:00:00Z/11'


def test_quickstatements_writes_one_complete_item():
    assert hml.quickstatements([CARE], CATEGORIES, "2026-11-15") == (
        "CREATE\n"
        'LAST\tLen\t"Care and Compliance"\n'
        'LAST\tDen\t"scholarly article in Humanities Methods in Librarianship, issue 1 (2026)"\n'
        f"LAST\tP31\tQ13442814{SOURCE}\n"
        f'LAST\tP1476\ten:"Care and Compliance"{SOURCE}\n'
        f"LAST\tP1433\tQ142069496{SOURCE}\n"
        f'LAST\tP433\t"1"{SOURCE}\n'
        f"LAST\tP577\t+2026-10-23T00:00:00Z/11{SOURCE}\n"
        f"LAST\tP407\tQ1860{SOURCE}\n"
        f'LAST\tP953\t"{READ}care-d3f5"\n'
        f'LAST\tP2093\t"Scout Bell"\tP1545\t"1"{SOURCE}\n'
    )


def test_quickstatements_types_a_book_review():
    review = dict(CARE, url=READ + "triptych-dcee")
    batch = hml.quickstatements([review], CATEGORIES, "2026-11-15")
    assert "LAST\tP31\tQ637866\t" in batch
    assert 'LAST\tDen\t"book review in Humanities Methods' in batch


def test_quickstatements_types_an_editorial():
    editorial = dict(CARE, url=READ + "editorial-818c")
    batch = hml.quickstatements([editorial], CATEGORIES, "2026-11-15")
    assert "LAST\tP31\tQ871232\t" in batch
    assert 'LAST\tDen\t"editorial in Humanities Methods' in batch


def test_quickstatements_types_a_creative_piece_as_literary_work():
    ode = dict(CARE, url=READ + "ode-3a52")
    batch = hml.quickstatements([ode], CATEGORIES, "2026-11-15")
    assert "LAST\tP31\tQ7725634\t" in batch
    assert 'LAST\tDen\t"literary work in Humanities Methods' in batch


def test_quickstatements_numbers_several_authors_in_order():
    two = dict(CARE, authors=["Sean Francis", "J. Morgan Rowe-Morris"])
    batch = hml.quickstatements([two], CATEGORIES, "2026-11-15")
    assert 'LAST\tP2093\t"Sean Francis"\tP1545\t"1"\t' in batch
    assert 'LAST\tP2093\t"J. Morgan Rowe-Morris"\tP1545\t"2"\t' in batch


def test_quickstatements_writes_no_author_line_without_authors():
    editorial = dict(CARE, url=READ + "editorial-818c", authors=[])
    batch = hml.quickstatements([editorial], CATEGORIES, "2026-11-15")
    assert "P2093" not in batch


def test_quickstatements_refuses_issue_zero():
    with pytest.raises(ValueError, match="Refusing to write issue 0"):
        hml.quickstatements([dict(CARE, issue=0)], CATEGORIES, "2026-11-15")


def test_quickstatements_refuses_negative_issue():
    with pytest.raises(ValueError, match="Refusing to write issue -1"):
        hml.quickstatements([dict(CARE, issue=-1)], CATEGORIES, "2026-11-15")


def test_quickstatements_stops_on_a_category_it_does_not_know():
    with pytest.raises(KeyError, match="Interviews"):
        hml.quickstatements([CARE], {"care-d3f5": "Interviews"}, "2026-11-15")


def test_quickstatements_stops_when_article_is_missing_from_manifold():
    with pytest.raises(KeyError, match="care-d3f5"):
        hml.quickstatements([CARE], {}, "2026-11-15")


# --- running the command, with only the network faked ---

import io
import json
import urllib.request

API = "https://cuny.manifoldapp.org/api/v1/"

PAGES = {
    "https://rss.humanitiesmethods.org/hml_feed.xml": FEED,
    API + "journals/hml/relationships/journal_issues": json.dumps(ISSUES),
    API + "projects/hml-no-1": json.dumps(PROJECT),
}


def fake_network(monkeypatch):
    """Replace urlopen with a fake that answers only the three expected URLs."""
    requested = []

    def fake_urlopen(request):
        requested.append(request.full_url)
        return io.BytesIO(PAGES[request.full_url].encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return requested


def test_main_writes_the_batch_file_for_issue_one(monkeypatch, tmp_path):
    fake_network(monkeypatch)
    monkeypatch.chdir(tmp_path)
    hml.main(["1"])
    batch = (tmp_path / "hml_issue_1.qs").read_text(encoding="utf-8")
    assert batch.count("CREATE\n") == 4
    assert 'LAST\tLen\t"Care and Compliance"\n' in batch
    assert 'LAST\tLen\t"Review of Triptych"\n' in batch
    assert 'LAST\tLen\t"Editorial"\n' in batch
    assert 'LAST\tLen\t"Ode"\n' in batch


def test_main_leaves_out_everything_from_other_issues(monkeypatch, tmp_path):
    fake_network(monkeypatch)
    monkeypatch.chdir(tmp_path)
    hml.main(["1"])
    batch = (tmp_path / "hml_issue_1.qs").read_text(encoding="utf-8")
    assert "submissions" not in batch
    assert "zero-with-citation" not in batch
    assert "draft-piece" not in batch
    assert "title-says-one" not in batch
    assert "citation-says-one" not in batch
    assert "next-year" not in batch


def test_main_writes_to_the_file_named_with_output(monkeypatch, tmp_path):
    fake_network(monkeypatch)
    monkeypatch.chdir(tmp_path)
    hml.main(["1", "--output", str(tmp_path / "mine.qs")])
    assert (tmp_path / "mine.qs").read_text(encoding="utf-8").startswith("CREATE\n")


def test_main_reports_each_item_with_its_type(monkeypatch, tmp_path, capsys):
    fake_network(monkeypatch)
    monkeypatch.chdir(tmp_path)
    hml.main(["1"])
    report = capsys.readouterr().out
    assert "scholarly article: Care and Compliance" in report
    assert "book review: Review of Triptych" in report
    assert "editorial: Editorial" in report
    assert "literary work: Ode" in report
    assert "Wrote 4 items to hml_issue_1.qs" in report


def test_main_refuses_issue_zero_before_touching_the_network(monkeypatch, tmp_path):
    requested = fake_network(monkeypatch)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as stopped:
        hml.main(["0"])
    assert stopped.value.code == 2
    assert requested == []
    assert list(tmp_path.iterdir()) == []


def test_main_refuses_the_draft_issue_numbered_minus_one(monkeypatch, tmp_path):
    requested = fake_network(monkeypatch)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as stopped:
        hml.main(["-1"])
    assert stopped.value.code == 2
    assert requested == []
    assert list(tmp_path.iterdir()) == []


def test_main_writes_no_file_when_issue_is_not_on_manifold(monkeypatch, tmp_path):
    fake_network(monkeypatch)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="Issue 2 was not found on Manifold"):
        hml.main(["2"])
    assert list(tmp_path.iterdir()) == []
