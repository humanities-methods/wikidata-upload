import argparse
import io
import json
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote

import pytest

import hml_quickstatements as hml

SCRIPT = Path(hml.__file__)
READ = "https://cuny.manifoldapp.org/read/"
API = "https://cuny.manifoldapp.org/api/v1/"


# ---------------------------------------------------------------------------
# Hand-made copies of the two outside sources, shaped like the real ones
# ---------------------------------------------------------------------------


def coins(title, issue, authors, slug):
    """Build the citation <span> (COinS) the feed puts at the top of each article."""
    fields = [
        "ctx_ver=Z39.88-2004",
        "rft_val_fmt=" + quote("info:ofi/fmt:kev:mtx:journal", safe=""),
        "rft.genre=article",
        "rft.atitle=" + quote(title, safe=""),
        "rft.jtitle=" + quote("Humanities Methods in Librarianship", safe=""),
        f"rft.issue={issue}",
        "rft.date=2026",
    ]
    fields += ["rft.au=" + quote(author, safe="") for author in authors]
    fields += ["rft_id=" + quote(READ + slug, safe=""), "rft.language=en"]
    return f'<span class="Z3988" title="{"&amp;".join(fields)}"></span>'


def feed_item(feed_title, slug, pub_date, citation):
    return f"""<item>
      <title>{feed_title}</title>
      <link>{READ}{slug}</link>
      <description><![CDATA[<!DOCTYPE html><!-- note -->{citation}<h1>Heading</h1><p>Text</p>]]></description>
      <guid isPermaLink="true">{READ}{slug}</guid>
      <pubDate>{pub_date}</pubDate>
    </item>"""


def feed(*items):
    return (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0"><channel>'
        "<title>Humanities Methods in Librarianship</title>"
        + "".join(items)
        + "</channel></rss>"
    )


# This citation is copied character for character from the real feed.
PRETEND_CITATION = (
    '<span class="Z3988" title="ctx_ver=Z39.88-2004&amp;rft_val_fmt=info%3Aofi%2Ffmt'
    "%3Akev%3Amtx%3Ajournal&amp;rft.genre=article&amp;rft.atitle=Pretend%20It%E2%80%99s"
    "%20Magic%3A%20The%20Story%20of%20a%20Library%20Management%20System&amp;rft.jtitle="
    "Humanities%20Methods%20in%20Librarianship&amp;rft.issue=1&amp;rft.date=2026&amp;"
    "rft.au=Kunesh%2C%20Tara&amp;rft_id=https%3A%2F%2Fcuny.manifoldapp.org%2Fread%2F"
    'pretend-e6f0&amp;rft.language=en"></span>'
)

OLD = "Wed, 08 Oct 2025 13:59:25 +0000"

FEED = feed(
    # Pages and pieces that must never be written when issue 1 is asked for:
    feed_item("Submissions (Issue 0)", "submissions", OLD, ""),
    feed_item(
        "Zero With Citation (Issue 0)",
        "zero-with-citation",
        OLD,
        coins("Zero With Citation", 0, ["Zero, Zed"], "zero-with-citation"),
    ),
    feed_item(
        "Draft Piece (Issue -1)",
        "draft-piece",
        OLD,
        coins("Draft Piece", -1, ["Draft, Dee"], "draft-piece"),
    ),
    feed_item(
        "Title Says One (Issue 1)",
        "title-says-one",
        OLD,
        coins("Title Says One", 0, ["Mix, Max"], "title-says-one"),
    ),
    feed_item(
        "Citation Says One (Issue 0)",
        "citation-says-one",
        OLD,
        coins("Citation Says One", 1, ["Mix, Max"], "citation-says-one"),
    ),
    feed_item(
        "No Issue In Title",
        "no-issue-in-title",
        OLD,
        coins("No Issue In Title", 1, ["Mix, Max"], "no-issue-in-title"),
    ),
    # Issue 1:
    feed_item(
        "Care and Compliance (Issue 1)",
        "care-d3f5",
        "Fri, 23 Oct 2026 16:38:58 +0000",
        coins("Care and Compliance", 1, ["Bell, Scout"], "care-d3f5"),
    ),
    feed_item(
        "Pretend It’s Magic: The Story of a Library Management System (Issue 1)",
        "pretend-e6f0",
        "Fri, 18 Sep 2026 13:42:10 +0000",
        PRETEND_CITATION,
    ),
    feed_item(
        "Review of Triptych (Issue 1)",
        "triptych-dcee",
        "Thu, 17 Sep 2026 16:21:14 +0000",
        coins("Review of Triptych", 1, ["Blechinger, Joel"], "triptych-dcee"),
    ),
    feed_item(
        "Editorial (Issue 1)",
        "editorial-818c",
        "Tue, 27 Oct 2026 12:18:31 +0000",
        coins("Editorial", 1, [], "editorial-818c"),
    ),
    feed_item(
        "Ode (Issue 1)",
        "ode-3a52",
        "Fri, 18 Sep 2026 13:11:57 +0000",
        coins("Ode", 1, ["Francis, Sean", "Rowe-Morris, J. Morgan"], "ode-3a52"),
    ),
    # Issue 2:
    feed_item(
        "Next Year (Issue 2)",
        "next-year",
        "Mon, 01 Mar 2027 10:00:00 +0000",
        coins("Next Year", 2, ["Later, Lee"], "next-year"),
    ),
    # Issue 4 is still a draft on Manifold, but one article is already in the feed:
    feed_item(
        "Early Bird (Issue 4)",
        "early-bird",
        "Mon, 01 Nov 2027 10:00:00 +0000",
        coins("Early Bird", 4, ["Early, Em"], "early-bird"),
    ),
)


def api_issue(number, project_slug, draft):
    return {
        "id": f"issue-{number}",
        "type": "journalIssues",
        "attributes": {
            "number": number,
            "projectSlug": project_slug,
            "draft": draft,
            "title": f"Humanities Methods in Librarianship, no. {number}",
        },
        "relationships": {"project": {"data": {"id": "p", "type": "projects"}}},
    }


ISSUES = {
    "data": [
        api_issue("2", "hml-no-2", False),
        api_issue("1", "hml-no-1", False),
        api_issue("0", "hml-no-0", False),
        api_issue("-1", "hml-no-1-116dd5c9", True),
        api_issue("4", "hml-no-4", True),
    ],
    "meta": {"pagination": {"perPage": 20, "currentPage": 1, "totalPages": 1}},
}


def api_category(category_id, title):
    return {
        "id": category_id,
        "type": "categories",
        "attributes": {"title": title, "role": None, "position": 1},
    }


def api_text(slug, category_id, title="A Text", published=True):
    return {
        "id": "text-" + slug,
        "type": "texts",
        "attributes": {
            "slug": slug,
            "titlePlaintext": title,
            "published": published,
            "creatorNames": "",
        },
        "relationships": {
            "category": {"data": {"id": category_id, "type": "categories"}}
        },
    }


PROJECT_1 = {
    "data": {"id": "p1", "type": "projects", "attributes": {"draft": False}},
    "included": [
        api_category("cat-ed", "Editorial"),
        api_category("cat-pr", "Peer Reviewed"),
        api_category("cat-cr", "CREATIVE"),
        api_category("cat-br", "Book Reviews"),
        {"id": "u1", "type": "users", "attributes": {}},
        api_text("care-d3f5", "cat-pr"),
        api_text("pretend-e6f0", "cat-cr"),
        api_text("triptych-dcee", "cat-br"),
        api_text("editorial-818c", "cat-ed"),
        api_text("ode-3a52", "cat-cr"),
    ],
}

PROJECT_2 = {
    "data": {"id": "p2", "type": "projects", "attributes": {"draft": False}},
    "included": [
        api_category("cat-pr", "Peer Reviewed"),
        api_text("next-year", "cat-pr"),
    ],
}

# The only URLs the command may ask for.
PAGES = {
    "https://rss.humanitiesmethods.org/hml_feed.xml": FEED,
    API + "journals/hml/relationships/journal_issues": json.dumps(ISSUES),
    API + "projects/hml-no-1": json.dumps(PROJECT_1),
    API + "projects/hml-no-2": json.dumps(PROJECT_2),
}


class Fifteenth(date):
    """A stand-in for the clock: today is always 15 November 2026."""

    @classmethod
    def today(cls):
        return date(2026, 11, 15)


def fake_outside_world(monkeypatch, tmp_path):
    """Fake the network and the clock, and work inside an empty temporary folder.

    Returns the list of URLs the code asked for. Any URL not in PAGES is an error.
    """
    requested = []

    def fake_urlopen(url):
        requested.append(url)
        return io.BytesIO(PAGES[url].encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(hml, "date", Fifteenth)
    monkeypatch.chdir(tmp_path)
    return requested


# ---------------------------------------------------------------------------
# The command line argument: only whole numbers above zero are accepted
# ---------------------------------------------------------------------------


def test_issue_number_accepts_one():
    assert hml.issue_number("1") == 1


def test_issue_number_accepts_a_later_issue():
    assert hml.issue_number("12") == 12


def test_issue_number_rejects_zero():
    with pytest.raises(argparse.ArgumentTypeError, match="must be 1 or greater"):
        hml.issue_number("0")


def test_issue_number_rejects_negative_one():
    with pytest.raises(argparse.ArgumentTypeError, match="must be 1 or greater"):
        hml.issue_number("-1")


def test_issue_number_rejects_words():
    with pytest.raises(ValueError):
        hml.issue_number("abc")


# ---------------------------------------------------------------------------
# Reading the feed
# ---------------------------------------------------------------------------


def test_feed_articles_returns_only_the_requested_issue():
    urls = [article["url"] for article in hml.feed_articles(FEED, 1)]
    assert urls == [
        READ + "care-d3f5",
        READ + "pretend-e6f0",
        READ + "triptych-dcee",
        READ + "editorial-818c",
        READ + "ode-3a52",
    ]


def test_feed_articles_can_select_a_later_issue():
    urls = [article["url"] for article in hml.feed_articles(FEED, 2)]
    assert urls == [READ + "next-year"]


def test_feed_articles_reads_the_title_from_the_citation():
    assert hml.feed_articles(FEED, 1)[0]["title"] == "Care and Compliance"


def test_feed_articles_decodes_punctuation_in_a_real_citation():
    article = hml.feed_articles(FEED, 1)[1]
    assert article["title"] == (
        "Pretend It’s Magic: The Story of a Library Management System"
    )
    assert article["authors"] == ["Tara Kunesh"]


def test_feed_articles_reads_the_publication_date():
    assert hml.feed_articles(FEED, 1)[0]["date"] == "2026-10-23"


def test_feed_articles_records_the_issue_number():
    assert hml.feed_articles(FEED, 1)[0]["issue"] == 1


def test_feed_articles_puts_given_name_before_family_name():
    assert hml.feed_articles(FEED, 1)[0]["authors"] == ["Scout Bell"]


def test_feed_articles_keeps_several_authors_in_feed_order():
    article = hml.feed_articles(FEED, 1)[4]
    assert article["authors"] == ["Sean Francis", "J. Morgan Rowe-Morris"]


def test_feed_articles_gives_editorial_no_authors():
    assert hml.feed_articles(FEED, 1)[3]["authors"] == []


def test_feed_articles_keeps_an_author_name_that_has_no_comma():
    group = feed(
        feed_item(
            "Statement (Issue 1)",
            "statement",
            OLD,
            coins("Statement", 1, ["Editorial Board"], "statement"),
        )
    )
    assert hml.feed_articles(group, 1)[0]["authors"] == ["Editorial Board"]


# ---------------------------------------------------------------------------
# Reading the Manifold API
# ---------------------------------------------------------------------------


def test_project_slug_finds_issue_one_not_the_draft_numbered_minus_one():
    assert hml.project_slug(ISSUES, 1) == "hml-no-1"


def test_project_slug_finds_a_later_issue():
    assert hml.project_slug(ISSUES, 2) == "hml-no-2"


def test_project_slug_stops_when_issue_is_not_on_manifold():
    with pytest.raises(SystemExit, match="Issue 3 was not found on Manifold"):
        hml.project_slug(ISSUES, 3)


def test_project_slug_refuses_an_issue_still_in_draft():
    with pytest.raises(SystemExit, match="Issue 4 is still a draft on Manifold"):
        hml.project_slug(ISSUES, 4)


def test_text_categories_maps_each_text_slug_to_its_category():
    assert hml.text_categories(PROJECT_1) == {
        "care-d3f5": "Peer Reviewed",
        "pretend-e6f0": "CREATIVE",
        "triptych-dcee": "Book Reviews",
        "editorial-818c": "Editorial",
        "ode-3a52": "CREATIVE",
    }


# Issue 2's project with two extra texts: one published but not yet in the feed,
# and one Manifold has not published.
PROJECT_2_AHEAD_OF_FEED = {
    "data": PROJECT_2["data"],
    "included": PROJECT_2["included"]
    + [
        api_text("interview-9f1c", "cat-pr", title="An Interview"),
        api_text("unfinished-07aa", "cat-pr", title="Unfinished", published=False),
    ],
}


def test_missing_from_feed_lists_a_published_text_the_feed_lacks():
    articles = hml.feed_articles(FEED, 2)
    assert hml.missing_from_feed(PROJECT_2_AHEAD_OF_FEED, articles) == ["An Interview"]


def test_missing_from_feed_is_empty_when_the_feed_has_every_text():
    articles = hml.feed_articles(FEED, 1)
    assert hml.missing_from_feed(PROJECT_1, articles) == []


# ---------------------------------------------------------------------------
# Writing the QuickStatements batch
# ---------------------------------------------------------------------------

CARE = {
    "title": "Care and Compliance",
    "url": READ + "care-d3f5",
    "issue": 1,
    "authors": ["Scout Bell"],
    "date": "2026-10-23",
}

SOURCE = f'\tS854\t"{READ}care-d3f5"\tS813\t+2026-11-15T00:00:00Z/11'


def test_quickstatements_writes_one_complete_item():
    batch = hml.quickstatements([CARE], {"care-d3f5": "Peer Reviewed"}, "2026-11-15")
    assert batch == (
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


# parametrize runs the same test once per row: a Manifold category, then the
# Wikidata type and the description we expect for it, each written out by hand.
@pytest.mark.parametrize(
    "category, type_line, description_start",
    [
        (
            "Peer Reviewed",
            "LAST\tP31\tQ13442814\t",
            'LAST\tDen\t"scholarly article in ',
        ),
        ("Book Reviews", "LAST\tP31\tQ637866\t", 'LAST\tDen\t"book review in '),
        ("Editorial", "LAST\tP31\tQ871232\t", 'LAST\tDen\t"editorial in '),
        ("CREATIVE", "LAST\tP31\tQ7725634\t", 'LAST\tDen\t"literary work in '),
    ],
)
def test_quickstatements_types_each_manifold_category(
    category, type_line, description_start
):
    batch = hml.quickstatements([CARE], {"care-d3f5": category}, "2026-11-15")
    assert type_line in batch
    assert description_start in batch


def test_quickstatements_numbers_several_authors_in_order():
    two = dict(CARE, authors=["Sean Francis", "J. Morgan Rowe-Morris"])
    batch = hml.quickstatements([two], {"care-d3f5": "Peer Reviewed"}, "2026-11-15")
    assert 'LAST\tP2093\t"Sean Francis"\tP1545\t"1"\t' in batch
    assert 'LAST\tP2093\t"J. Morgan Rowe-Morris"\tP1545\t"2"\t' in batch


def test_quickstatements_writes_no_author_line_without_authors():
    unsigned = dict(CARE, authors=[])
    batch = hml.quickstatements([unsigned], {"care-d3f5": "Editorial"}, "2026-11-15")
    assert "P2093" not in batch


def test_quickstatements_refuses_issue_zero():
    with pytest.raises(ValueError, match="Refusing to write issue 0"):
        hml.quickstatements(
            [dict(CARE, issue=0)], {"care-d3f5": "Peer Reviewed"}, "2026-11-15"
        )


def test_quickstatements_refuses_negative_issue():
    with pytest.raises(ValueError, match="Refusing to write issue -1"):
        hml.quickstatements(
            [dict(CARE, issue=-1)], {"care-d3f5": "Peer Reviewed"}, "2026-11-15"
        )


def test_quickstatements_stops_on_a_category_it_does_not_know():
    with pytest.raises(KeyError, match="Interviews"):
        hml.quickstatements([CARE], {"care-d3f5": "Interviews"}, "2026-11-15")


def test_quickstatements_stops_when_article_is_missing_from_manifold():
    with pytest.raises(KeyError, match="care-d3f5"):
        hml.quickstatements([CARE], {}, "2026-11-15")


def test_quickstatements_stops_on_a_straight_quote_in_a_title():
    quoted = dict(CARE, title='The "Neutral" Catalogue')
    with pytest.raises(SystemExit, match='straight double quote.*The "Neutral"'):
        hml.quickstatements([quoted], {"care-d3f5": "Peer Reviewed"}, "2026-11-15")


# ---------------------------------------------------------------------------
# Running the command, with only the network and the clock faked
# ---------------------------------------------------------------------------


def test_main_writes_one_item_per_article_of_issue_one(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    hml.main(["1"])
    batch = (tmp_path / "hml_issue_1.qs").read_text(encoding="utf-8")
    labels = [line for line in batch.splitlines() if line.startswith("LAST\tLen\t")]
    assert labels == [
        'LAST\tLen\t"Care and Compliance"',
        'LAST\tLen\t"Pretend It’s Magic: The Story of a Library Management System"',
        'LAST\tLen\t"Review of Triptych"',
        'LAST\tLen\t"Editorial"',
        'LAST\tLen\t"Ode"',
    ]


def test_main_leaves_out_everything_from_other_issues(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    hml.main(["1"])
    batch = (tmp_path / "hml_issue_1.qs").read_text(encoding="utf-8")
    assert "submissions" not in batch
    assert "zero-with-citation" not in batch
    assert "draft-piece" not in batch
    assert "title-says-one" not in batch
    assert "citation-says-one" not in batch
    assert "no-issue-in-title" not in batch
    assert "next-year" not in batch


def test_main_asks_only_for_the_feed_the_issue_list_and_the_issue(
    monkeypatch, tmp_path
):
    requested = fake_outside_world(monkeypatch, tmp_path)
    hml.main(["1"])
    assert sorted(requested) == [
        API + "journals/hml/relationships/journal_issues",
        API + "projects/hml-no-1",
        "https://rss.humanitiesmethods.org/hml_feed.xml",
    ]


def test_main_writes_a_later_issue_to_its_own_file(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    hml.main(["2"])
    batch = (tmp_path / "hml_issue_2.qs").read_text(encoding="utf-8")
    labels = [line for line in batch.splitlines() if line.startswith("LAST\tLen\t")]
    assert labels == ['LAST\tLen\t"Next Year"']
    assert 'LAST\tP433\t"2"\t' in batch


def test_main_dates_each_reference_with_today(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    hml.main(["2"])
    batch = (tmp_path / "hml_issue_2.qs").read_text(encoding="utf-8")
    assert (
        f'LAST\tP433\t"2"\tS854\t"{READ}next-year"\tS813\t+2026-11-15T00:00:00Z/11\n'
        in batch
    )


def test_main_replaces_an_earlier_batch_file(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    (tmp_path / "hml_issue_2.qs").write_text("CREATE\nold batch\n", encoding="utf-8")
    hml.main(["2"])
    batch = (tmp_path / "hml_issue_2.qs").read_text(encoding="utf-8")
    assert "old batch" not in batch
    assert batch.count("CREATE\n") == 1


def test_main_writes_to_the_file_named_with_output(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    hml.main(["1", "--output", "mine.qs"])
    assert [path.name for path in tmp_path.iterdir()] == ["mine.qs"]
    assert (tmp_path / "mine.qs").read_text(encoding="utf-8").startswith("CREATE\n")


def test_main_warns_about_a_published_text_missing_from_the_feed(
    monkeypatch, tmp_path, capsys
):
    fake_outside_world(monkeypatch, tmp_path)
    monkeypatch.setitem(
        PAGES, API + "projects/hml-no-2", json.dumps(PROJECT_2_AHEAD_OF_FEED)
    )
    hml.main(["2"])
    warnings = capsys.readouterr().err
    assert "An Interview" in warnings
    assert "not in the feed" in warnings
    assert "Unfinished" not in warnings


def test_main_still_writes_the_batch_when_the_feed_is_behind(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    monkeypatch.setitem(
        PAGES, API + "projects/hml-no-2", json.dumps(PROJECT_2_AHEAD_OF_FEED)
    )
    hml.main(["2"])
    batch = (tmp_path / "hml_issue_2.qs").read_text(encoding="utf-8")
    assert 'LAST\tLen\t"Next Year"\n' in batch


def test_main_prints_no_warning_when_the_feed_is_complete(
    monkeypatch, tmp_path, capsys
):
    fake_outside_world(monkeypatch, tmp_path)
    hml.main(["1"])
    assert capsys.readouterr().err == ""


def test_main_reports_each_item_with_its_type(monkeypatch, tmp_path, capsys):
    fake_outside_world(monkeypatch, tmp_path)
    hml.main(["1"])
    assert capsys.readouterr().out == (
        "scholarly article: Care and Compliance\n"
        "literary work: Pretend It’s Magic: The Story of a Library Management System\n"
        "book review: Review of Triptych\n"
        "editorial: Editorial\n"
        "literary work: Ode\n"
        "Wrote 5 items to hml_issue_1.qs\n"
    )


def test_main_refuses_issue_zero_before_touching_the_network(monkeypatch, tmp_path):
    requested = fake_outside_world(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as stopped:
        hml.main(["0"])
    assert stopped.value.code == 2
    assert requested == []
    assert list(tmp_path.iterdir()) == []


def test_main_refuses_the_draft_issue_numbered_minus_one(monkeypatch, tmp_path):
    requested = fake_outside_world(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as stopped:
        hml.main(["-1"])
    assert stopped.value.code == 2
    assert requested == []
    assert list(tmp_path.iterdir()) == []


def test_main_writes_no_file_when_issue_is_not_on_manifold(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="Issue 3 was not found on Manifold"):
        hml.main(["3"])
    assert list(tmp_path.iterdir()) == []


def test_main_writes_no_file_when_a_title_has_a_straight_quote(monkeypatch, tmp_path):
    fake_outside_world(monkeypatch, tmp_path)
    quoted_feed = feed(
        feed_item(
            'The "Neutral" Catalogue (Issue 2)',
            "next-year",
            "Mon, 01 Mar 2027 10:00:00 +0000",
            coins('The "Neutral" Catalogue', 2, ["Later, Lee"], "next-year"),
        )
    )
    # setitem swaps in this feed for this one test and puts the original back after.
    monkeypatch.setitem(
        PAGES, "https://rss.humanitiesmethods.org/hml_feed.xml", quoted_feed
    )
    with pytest.raises(SystemExit, match="straight double quote"):
        hml.main(["2"])
    assert list(tmp_path.iterdir()) == []


def test_main_writes_no_file_for_a_draft_issue(monkeypatch, tmp_path):
    requested = fake_outside_world(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="Issue 4 is still a draft on Manifold"):
        hml.main(["4"])
    assert API + "projects/hml-no-4" not in requested
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Running the file itself, the way it is run from a terminal. These two never
# reach the network: the issue number is refused before anything is fetched.
# ---------------------------------------------------------------------------


def test_script_refuses_issue_zero_from_the_terminal(tmp_path):
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "0"], cwd=tmp_path, capture_output=True, text=True
    )
    assert run.returncode == 2
    assert "issue must be 1 or greater, got 0" in run.stderr
    assert list(tmp_path.iterdir()) == []


def test_script_refuses_issue_minus_one_from_the_terminal(tmp_path):
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "-1"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2
    assert "issue must be 1 or greater, got -1" in run.stderr
    assert list(tmp_path.iterdir()) == []
