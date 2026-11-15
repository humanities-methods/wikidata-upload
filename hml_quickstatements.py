"""Build a QuickStatements batch for one issue of Humanities Methods in Librarianship."""

import argparse
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl


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
                family, given = value.split(", ", 1)
                authors.append(f"{given} {family}")
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
