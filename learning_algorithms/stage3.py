"""Stage 3 stack, cache, and prefix-tree interview foundations."""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Generic, TypeVar, cast

Key = TypeVar("Key", bound=Hashable)
Value = TypeVar("Value")


def valid_parentheses(sequence: str) -> bool:
    """Return whether a bracket-only sequence is correctly balanced.

    Learning reference: LeetCode 20, Valid Parentheses.
    https://leetcode.com/problems/valid-parentheses/

    A stack gives O(n) time and O(n) worst-case space. The canonical learning
    contract accepts only ``()[]{}``; application wrappers can extract those
    delimiters from a larger structured value before calling this function.
    """
    opening = {"(", "[", "{"}
    matching_open = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []

    for character in sequence:
        if character in opening:
            stack.append(character)
            continue
        if character not in matching_open:
            raise ValueError("sequence may contain only (), [], and {} delimiters")
        if not stack or stack.pop() != matching_open[character]:
            return False

    return not stack


class _LRUNode(Generic[Key, Value]):
    """One node in the cache's internal doubly linked list."""

    def __init__(self, key: Key | None = None, value: Value | None = None) -> None:
        self.key = key
        self.value = value
        self.previous: _LRUNode[Key, Value] | None = None
        self.next: _LRUNode[Key, Value] | None = None


class LRUCache(Generic[Key, Value]):
    """Fixed-capacity least-recently-used cache with O(1) get and put.

    Learning reference: LeetCode 146, LRU Cache.
    https://leetcode.com/problems/lru-cache/

    A dictionary provides direct lookup while a doubly linked list maintains
    recency. This typed project adaptation returns ``None`` for a cache miss
    instead of the interview problem's integer-only ``-1`` sentinel.
    """

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("cache capacity must be at least 1")
        self.capacity = capacity
        self._nodes: dict[Key, _LRUNode[Key, Value]] = {}
        self._least_recent = _LRUNode[Key, Value]()
        self._most_recent = _LRUNode[Key, Value]()
        self._least_recent.next = self._most_recent
        self._most_recent.previous = self._least_recent

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, key: object) -> bool:
        return key in self._nodes

    def _detach(self, node: _LRUNode[Key, Value]) -> None:
        previous = node.previous
        following = node.next
        if previous is None or following is None:
            raise RuntimeError("cache list is corrupted")
        previous.next = following
        following.previous = previous

    def _append_most_recent(self, node: _LRUNode[Key, Value]) -> None:
        previous = self._most_recent.previous
        if previous is None:
            raise RuntimeError("cache list is corrupted")
        previous.next = node
        node.previous = previous
        node.next = self._most_recent
        self._most_recent.previous = node

    def _mark_recent(self, node: _LRUNode[Key, Value]) -> None:
        self._detach(node)
        self._append_most_recent(node)

    def get(self, key: Key) -> Value | None:
        """Return and refresh a cached value, or ``None`` on a miss."""
        node = self._nodes.get(key)
        if node is None:
            return None
        self._mark_recent(node)
        return cast(Value, node.value)

    def put(self, key: Key, value: Value) -> None:
        """Insert or update a value and evict the least-recent entry if full."""
        if value is None:
            raise ValueError(
                "cache value cannot be None because None represents a miss"
            )
        existing = self._nodes.get(key)
        if existing is not None:
            existing.value = value
            self._mark_recent(existing)
            return

        node = _LRUNode(key, value)
        self._nodes[key] = node
        self._append_most_recent(node)

        if len(self._nodes) <= self.capacity:
            return
        expired = self._least_recent.next
        if expired is None or expired is self._most_recent:
            raise RuntimeError("cache list is corrupted")
        self._detach(expired)
        del self._nodes[cast(Key, expired.key)]


@dataclass(slots=True)
class _TrieNode:
    children: dict[str, _TrieNode] = field(default_factory=dict)
    is_word: bool = False


class Trie:
    """Prefix tree for exact and prefix lookup.

    Learning reference: LeetCode 208, Implement Trie (Prefix Tree).
    https://leetcode.com/problems/implement-trie-prefix-tree/

    Insert, exact search, and prefix checks cost O(m), where ``m`` is the input
    length. Listing completions additionally costs the size of the returned
    subtree.
    """

    def __init__(self) -> None:
        self._root = _TrieNode()
        self._word_count = 0

    def __len__(self) -> int:
        return self._word_count

    def _node_for(self, value: str) -> _TrieNode | None:
        node = self._root
        for character in value:
            node = node.children.get(character)
            if node is None:
                return None
        return node

    def insert(self, word: str) -> None:
        """Insert one non-empty word, without counting duplicates twice."""
        if not word:
            raise ValueError("trie word cannot be empty")
        node = self._root
        for character in word:
            node = node.children.setdefault(character, _TrieNode())
        if not node.is_word:
            node.is_word = True
            self._word_count += 1

    def search(self, word: str) -> bool:
        """Return whether the complete word was inserted."""
        if not word:
            return False
        node = self._node_for(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        """Return whether any inserted word begins with the prefix."""
        return self._node_for(prefix) is not None

    def words_with_prefix(
        self,
        prefix: str,
        *,
        limit: int | None = None,
    ) -> tuple[str, ...]:
        """Return deterministic, alphabetically ordered prefix completions."""
        if limit is not None and limit < 1:
            raise ValueError("prefix result limit must be at least 1")
        start = self._node_for(prefix)
        if start is None:
            return ()

        matches: list[str] = []

        def collect(node: _TrieNode, suffix: str) -> None:
            if limit is not None and len(matches) >= limit:
                return
            if node.is_word:
                matches.append(prefix + suffix)
            for character in sorted(node.children):
                collect(node.children[character], suffix + character)

        collect(start, "")
        return tuple(matches)
