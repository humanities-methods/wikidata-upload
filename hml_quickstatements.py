"""Build a QuickStatements batch for one issue of Humanities Methods in Librarianship."""

import argparse
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl

FEED_URL = "https://rss.humanitiesmethods.org/hml_feed.xml"
API_URL = "https://cuny.manifoldapp.org/api/v1"


def issue_number(value):
    """Turn the command line argument into an issue number. Only 1 and up is allowed."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"issue must be 1 or greater, got {number}")
    return number


def feed_articles(feed_xml, issue):
    """Read the RSS feed and return the articles that belong to one issue.

    An article counts only if it carries a citation <span> (COinS) and both that
    citation and the "(Issue N)" ending of the feed title name the requested issue.
    """
    articles = []
    for item in ET.fromstring(feed_xml).iter("item"):
        citation = re.search(
            r'<span class="Z3988" title="([^"]*)"', item.findtext("description")
        )
        title_issue = re.search(r"\(Issue (-?\d+)\)$", item.findtext("title"))
        if not citation or not title_issue:
            continue
        fields = parse_qsl(html.unescape(citation.group(1)))
        cited = dict(fields)
        if int(cited["rft.issue"]) != issue or int(title_issue.group(1)) != issue:
            continue
        authors = []
        for key, value in fields:
            if key == "rft.au":
                family, comma, given = value.partition(", ")
                authors.append(f"{given} {family}" if comma else value)
        published = parsedate_to_datetime(item.findtext("pubDate"))
        articles.append(
            {
                "title": cited["rft.atitle"],
                "url": item.findtext("link"),
                "issue": int(cited["rft.issue"]),
                "authors": authors,
                "date": published.date().isoformat(),
            }
        )
    return articles


def project_slug(issues, issue):
    """Find the Manifold project that holds one issue, from the journal's issue list."""
    for entry in issues["data"]:
        if entry["attributes"]["number"] == str(issue):
            return entry["attributes"]["projectSlug"]
    raise SystemExit(f"Issue {issue} was not found on Manifold")


def text_categories(project):
    """Map each text's slug to the title of its Manifold category."""
    titles = {}
    for entry in project["included"]:
        if entry["type"] == "categories":
            titles[entry["id"]] = entry["attributes"]["title"]
    categories = {}
    for entry in project["included"]:
        if entry["type"] == "texts":
            category_id = entry["relationships"]["category"]["data"]["id"]
            categories[entry["attributes"]["slug"]] = titles[category_id]
    return categories


JOURNAL_QID = "Q142069496"
JOURNAL_NAME = "Humanities Methods in Librarianship"
ENGLISH_QID = "Q1860"

# Manifold category title -> (Wikidata "instance of" item, its English name)
WIKIDATA_TYPES = {
    "Peer Reviewed": ("Q13442814", "scholarly article"),
    "Book Reviews": ("Q637866", "book review"),
    "Editorial": ("Q871232", "editorial"),
    "CREATIVE": ("Q7725634", "literary work"),
}


def wikidata_type(article, categories):
    """Return (item, English name) of the Wikidata type for one article.

    The last part of the article's URL is its Manifold slug, which leads to its
    category, which leads to the type.
    """
    slug = article["url"].rsplit("/", 1)[1]
    return WIKIDATA_TYPES[categories[slug]]


def quickstatements(articles, categories, retrieved):
    """Write the articles as QuickStatements V1 commands, one new item each.

    `categories` maps a text's slug to its Manifold category, and `retrieved` is
    today's date (YYYY-MM-DD) for the "retrieved" part of each reference.
    """
    lines = []
    for article in articles:
        if article["issue"] < 1:
            raise ValueError(f"Refusing to write issue {article['issue']}")
        type_qid, type_name = wikidata_type(article, categories)
        year = article["date"][:4]
        source = f'\tS854\t"{article["url"]}"\tS813\t+{retrieved}T00:00:00Z/11'
        lines += [
            "CREATE",
            f'LAST\tLen\t"{article["title"]}"',
            f'LAST\tDen\t"{type_name} in {JOURNAL_NAME}, issue {article["issue"]} ({year})"',
            f"LAST\tP31\t{type_qid}{source}",
            f'LAST\tP1476\ten:"{article["title"]}"{source}',
            f"LAST\tP1433\t{JOURNAL_QID}{source}",
            f'LAST\tP433\t"{article["issue"]}"{source}',
            f'LAST\tP577\t+{article["date"]}T00:00:00Z/11{source}',
            f"LAST\tP407\t{ENGLISH_QID}{source}",
            f'LAST\tP953\t"{article["url"]}"',
        ]
        for position, author in enumerate(article["authors"], start=1):
            lines.append(f'LAST\tP2093\t"{author}"\tP1545\t"{position}"{source}')
    return "".join(line + "\n" for line in lines)


def fetch(url):
    """Download a URL and return its contents as bytes.

    The XML and JSON readers both accept bytes and work out the encoding themselves.
    """
    with urllib.request.urlopen(url) as response:
        return response.read()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue", type=issue_number, help="issue number, 1 or greater")
    parser.add_argument("--output", help="file to write (default: hml_issue_N.qs)")
    args = parser.parse_args(argv)
    output = args.output or f"hml_issue_{args.issue}.qs"

    articles = feed_articles(fetch(FEED_URL), args.issue)
    issues = json.loads(fetch(f"{API_URL}/journals/hml/relationships/journal_issues"))
    slug = project_slug(issues, args.issue)
    categories = text_categories(json.loads(fetch(f"{API_URL}/projects/{slug}")))
    batch = quickstatements(articles, categories, date.today().isoformat())

    with open(output, "w", encoding="utf-8") as file:
        file.write(batch)
    for article in articles:
        print(f"{wikidata_type(article, categories)[1]}: {article['title']}")
    print(f"Wrote {len(articles)} items to {output}")


if __name__ == "__main__":
    main()
