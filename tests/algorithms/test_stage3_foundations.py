from __future__ import annotations

import pytest

from learning_algorithms.stage3 import LRUCache, Trie, valid_parentheses


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        ("()", True),
        ("()[]{}", True),
        ("(]", False),
        ("([)]", False),
        ("{[]}", True),
        ("]", False),
        ("((", False),
        ("", True),
    ],
)
def test_valid_parentheses_matches_interview_examples(
    sequence: str, expected: bool
) -> None:
    assert valid_parentheses(sequence) is expected


def test_valid_parentheses_rejects_non_delimiter_input() -> None:
    with pytest.raises(ValueError, match="only"):
        valid_parentheses("(answer)")


def test_valid_parentheses_checks_extracted_model_structure() -> None:
    generated = "Result: {checks: [supported, cited]}"
    delimiters = "".join(char for char in generated if char in "()[]{}")

    assert valid_parentheses(delimiters)


def test_lru_cache_matches_interview_sequence() -> None:
    cache = LRUCache[int, int](2)

    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)
    assert cache.get(2) is None
    cache.put(4, 4)
    assert cache.get(1) is None
    assert cache.get(3) == 3
    assert cache.get(4) == 4
    assert len(cache) == 2
    assert 3 in cache
    assert 2 not in cache


def test_lru_cache_update_refreshes_recency() -> None:
    cache = LRUCache[str, int](2)
    cache.put("first", 1)
    cache.put("second", 2)

    cache.put("first", 10)
    cache.put("third", 3)

    assert cache.get("first") == 10
    assert cache.get("second") is None
    assert cache.get("third") == 3


def test_lru_cache_holds_typed_retrieval_results() -> None:
    cache = LRUCache[tuple[str, int], tuple[str, ...]](1)
    key = ("coverage", 3)
    result = ("docs/ci.md",)

    cache.put(key, result)

    assert cache.get(key) is result


@pytest.mark.parametrize("capacity", [0, -1])
def test_lru_cache_rejects_non_positive_capacity(capacity: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        LRUCache[str, str](capacity)


def test_lru_cache_reserves_none_for_cache_misses() -> None:
    cache = LRUCache[str, str | None](1)

    with pytest.raises(ValueError, match="represents a miss"):
        cache.put("query", None)


def test_trie_matches_interview_sequence() -> None:
    trie = Trie()
    trie.insert("apple")

    assert trie.search("apple")
    assert not trie.search("app")
    assert trie.starts_with("app")

    trie.insert("app")

    assert trie.search("app")
    assert len(trie) == 2


def test_trie_deduplicates_and_returns_sorted_prefix_matches() -> None:
    trie = Trie()
    for source in ("docs/rag.md", "docs/api.md", "README.md", "docs/rag.md"):
        trie.insert(source)

    assert len(trie) == 3
    assert trie.words_with_prefix("docs/") == ("docs/api.md", "docs/rag.md")
    assert trie.words_with_prefix("docs/", limit=1) == ("docs/api.md",)
    assert trie.words_with_prefix("missing") == ()
    assert trie.words_with_prefix("") == (
        "README.md",
        "docs/api.md",
        "docs/rag.md",
    )


def test_trie_empty_prefix_exists_but_empty_word_does_not() -> None:
    trie = Trie()

    assert trie.starts_with("")
    assert not trie.search("")
    with pytest.raises(ValueError, match="cannot be empty"):
        trie.insert("")


def test_trie_rejects_non_positive_result_limit() -> None:
    trie = Trie()
    trie.insert("docs/rag.md")

    with pytest.raises(ValueError, match="at least 1"):
        trie.words_with_prefix("docs", limit=0)
