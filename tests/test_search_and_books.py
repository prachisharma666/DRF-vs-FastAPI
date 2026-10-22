"""
Extra black-box tests: search, search validation, book detail, upstream failure.

Run the same file against either server by changing BASE_URL.

Required env var:
    BASE_URL        server under test, e.g. http://localhost:8000

Optional env var (for the 502 tests):
    BASE_URL_DEAD   a SECOND instance of the same app started with UPSTREAM_URL
                    pointing at a port where nothing is listening.
                    If it is not set, the 502 tests are skipped.
"""
import os
import re

import httpx
import pytest

BASE = os.environ["BASE_URL"]
BASE_DEAD = os.environ.get("BASE_URL_DEAD")

BOOK_KEYS = {"work_id", "title", "authors", "first_publish_year", "cover_url"}


# ---------- search: happy path ----------

def test_search_returns_200_and_a_list():
    r = httpx.get(f"{BASE}/api/search", params={"q": "tolkien", "limit": 3})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_search_respects_limit():
    r = httpx.get(f"{BASE}/api/search", params={"q": "x", "limit": 4})
    assert len(r.json()) == 4


def test_search_items_have_the_normalized_shape():
    r = httpx.get(f"{BASE}/api/search", params={"q": "x", "limit": 3})
    for book in r.json():
        assert BOOK_KEYS <= book.keys()
        assert re.fullmatch(r"OL\d+W", book["work_id"])      # "/works/" prefix stripped
        assert isinstance(book["title"], str)
        assert isinstance(book["authors"], list)
        assert book["first_publish_year"] is None or isinstance(book["first_publish_year"], int)
        assert book["cover_url"] is None or book["cover_url"].startswith(
            "https://covers.openlibrary.org/b/id/")


def test_search_default_limit_is_10():
    r = httpx.get(f"{BASE}/api/search", params={"q": "x"})
    assert r.status_code == 200
    assert len(r.json()) == 10


# ---------- search: validation ----------

@pytest.mark.parametrize("params", [
    {},                                # q missing
    {"q": ""},                         # q empty
    {"q": "x", "limit": 0},            # below minimum
    {"q": "x", "limit": 51},           # above maximum
    {"q": "x", "limit": "abc"},        # not a number
])
def test_search_invalid_params_rejected(params):
    r = httpx.get(f"{BASE}/api/search", params=params)
    assert r.status_code in (400, 422), r.text


def test_search_limit_boundaries_accepted():
    assert httpx.get(f"{BASE}/api/search", params={"q": "x", "limit": 1}).status_code == 200
    assert httpx.get(f"{BASE}/api/search", params={"q": "x", "limit": 50}).status_code == 200


# ---------- book detail ----------

def test_book_detail_returns_200_and_normalized_shape():
    r = httpx.get(f"{BASE}/api/books/OL27448W")
    assert r.status_code == 200
    body = r.json()
    assert BOOK_KEYS <= body.keys()
    assert body["work_id"] == "OL27448W"
    assert isinstance(body["title"], str)


def test_book_detail_unknown_work_returns_404():
    # "OL404W" is the magic ID the mock upstream answers with 404
    r = httpx.get(f"{BASE}/api/books/OL404W")
    assert r.status_code == 404


@pytest.mark.parametrize("bad_id", ["abc", "OL123", "123W", "ol1w"])
def test_book_detail_malformed_id_rejected(bad_id):
    r = httpx.get(f"{BASE}/api/books/{bad_id}")
    assert r.status_code in (400, 404, 422)


# ---------- upstream failure -> 502 ----------

@pytest.mark.skipif(not BASE_DEAD, reason="set BASE_URL_DEAD to run the 502 tests")
def test_search_returns_502_when_upstream_is_down():
    r = httpx.get(f"{BASE_DEAD}/api/search", params={"q": "x"}, timeout=15)
    assert r.status_code == 502


@pytest.mark.skipif(not BASE_DEAD, reason="set BASE_URL_DEAD to run the 502 tests")
def test_book_detail_returns_502_when_upstream_is_down():
    r = httpx.get(f"{BASE_DEAD}/api/books/OL27448W", timeout=15)
    assert r.status_code == 502