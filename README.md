# wikidata-upload

Builds a [QuickStatements](https://quickstatements.toolforge.org/) batch that
creates one Wikidata item per article in an issue of
[_Humanities Methods in Librarianship_](https://www.humanitiesmethods.org)
(HML).

The script reads two sources:

- the journal's RSS feed (`https://rss.humanitiesmethods.org/hml_feed.xml`),
  for each article's title, authors, URL and publication date, taken from the
  COinS citation at the top of each entry
- the CUNY Manifold API (`https://cuny.manifoldapp.org/api/v1`), to find the
  issue's project and the category (Peer Reviewed, Book Reviews, and so on) of
  each article

It writes the batch to a file. It does not edit Wikidata itself: you review
the file, then run it in QuickStatements.

## Requirements

- [uv](https://docs.astral.sh/uv/), which installs Python 3.11 or later if
  needed
- the script itself uses only the Python standard library

## Usage

```bash
uv run python hml_quickstatements.py 1
```

This writes `hml_issue_1.qs` (or replaces it, if it exists), prints one line
per item in the form `<type>: <title>`, and ends with
`Wrote N items to hml_issue_1.qs`.

To choose the file name:

```bash
uv run python hml_quickstatements.py 2 --output issue2.qs
```

`.qs` files are ignored by git.

### Running the batch

1. Open the file and check it.
2. Go to <https://quickstatements.toolforge.org/>, log in, and choose
   **New batch**.
3. Paste the file's contents, keep the format as V1 commands, and import.

The script does not check whether an article is already on Wikidata, so
running the same batch twice creates duplicate items.

## What each item gets

| Wikidata                         | Value                                                                      |
| -------------------------------- | -------------------------------------------------------------------------- |
| English label                    | article title                                                              |
| English description              | e.g. "scholarly article in Humanities Methods in Librarianship, issue 1 (2026)" |
| P31 instance of                  | type from the Manifold category (see below)                                |
| P1476 title                      | article title, in English                                                  |
| P1433 published in               | Q142069496 (_Humanities Methods in Librarianship_)                         |
| P433 issue                       | issue number                                                               |
| P577 publication date            | date from the feed                                                         |
| P407 language of work            | Q1860 (English)                                                            |
| P953 full work available at URL  | article URL on Manifold                                                    |
| P2093 author name string         | one per author, in feed order, with P1545 series ordinal                   |

Every statement except P953 has a reference: P854 reference URL (the article
URL) and P813 retrieved (today's date).

Author names in the feed are "Family, Given" and are written as
"Given Family". A name with no comma, such as "Editorial Board", is kept as is.

### Manifold category to Wikidata type

| Manifold category | P31 instance of               |
| ----------------- | ----------------------------- |
| Peer Reviewed     | Q13442814 (scholarly article) |
| Book Reviews      | Q637866 (book review)         |
| Editorial         | Q871232 (editorial)           |
| CREATIVE          | Q7725634 (literary work)      |

To support another category, add it to `WIKIDATA_TYPES` in
`hml_quickstatements.py`.

## When the script stops

The script writes no file when:

- the issue number is below 1
- the issue is not on Manifold, or Manifold still marks it as a draft
- a title or author name contains a straight double quote (`"`), which
  QuickStatements cannot write
- an article's Manifold category is not in `WIKIDATA_TYPES`, or an article in
  the feed is not in the issue's Manifold project (the script stops with a
  `KeyError` naming the category or the article's slug)

It still writes the batch, but prints a warning, when Manifold has published
an article that is not in the feed yet. That article is left out; run the
script again once the feed has caught up.

An article only counts as part of an issue when both its COinS citation and
the "(Issue N)" at the end of its feed title name that issue.

## Development

```bash
uv sync                 # install pytest and black
uv run pytest           # run the tests
uv run black .          # format the code
```

The tests use hand-made copies of the feed and the Manifold API responses, so
they never touch the network.
