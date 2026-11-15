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
