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
