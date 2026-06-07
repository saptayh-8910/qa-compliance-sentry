from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class SauceDemoClient:
    """Thin client for public JSONPlaceholder-style API checks in Stage 1.

    Sauce Demo has no public REST API for candidates. This client validates
    HTTP patterns against jsonplaceholder.typicode.com as a stand-in for
    REST contract checks, while UI tests target saucedemo.com.
    """

    base_url: str = "https://jsonplaceholder.typicode.com"
    timeout: int = 15

    def get_posts(self) -> list[dict[str, Any]]:
        response = requests.get(f"{self.base_url}/posts", timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Expected list of posts")
        return data

    def get_post(self, post_id: int) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/posts/{post_id}", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def assert_post_shape(self, post: dict[str, Any]) -> None:
        required = {"userId", "id", "title", "body"}
        missing = required - set(post.keys())
        if missing:
            raise AssertionError(f"Post missing keys: {missing}")
