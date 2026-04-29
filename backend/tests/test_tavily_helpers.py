"""Pure-function tests for tavily helpers (no network)."""
from researchpipe_api.tavily import _hostname, _time_range_to_days, shape_search_results


def test_time_range_to_days():
    assert _time_range_to_days("7d") == 7
    assert _time_range_to_days("30d") == 30
    assert _time_range_to_days("6m") == 180
    assert _time_range_to_days("1y") == 365
    assert _time_range_to_days("garbage") == 30  # default fallback


def test_hostname_extraction():
    assert _hostname("https://www.example.com/path") == "www.example.com"
    assert _hostname("http://foo.bar:8080/x") == "foo.bar"
    assert _hostname("not a url") == ""


def test_shape_search_results_basic():
    tavily_resp = {
        "query": "x",
        "answer": "ans",
        "results": [
            {
                "title": "T",
                "url": "https://example.com/a",
                "content": "abcdefg" * 100,
                "score": 0.8,
                "published_date": "2026-04-29",
            }
        ],
    }
    out = shape_search_results(tavily_resp)
    assert out["query"] == "x"
    assert out["answer"] == "ans"
    assert len(out["results"]) == 1
    r = out["results"][0]
    assert r["title"] == "T"
    assert r["source_name"] == "example.com"
    assert len(r["snippet"]) == 300
    assert r["score"] == 0.8


def test_shape_empty_results():
    out = shape_search_results({"query": "x", "results": []})
    assert out["results"] == []
    assert out["metadata"]["total_results"] == 0
