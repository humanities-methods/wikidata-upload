"""Build a QuickStatements batch for one issue of Humanities Methods in Librarianship."""

import argparse


def issue_number(value):
    """Turn the command line argument into an issue number. Only 1 and up is allowed."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"issue must be 1 or greater, got {number}")
    return number
