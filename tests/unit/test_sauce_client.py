from unittest.mock import Mock

import pytest

from api.sauce_client import SauceDemoClient


def test_get_posts_returns_validated_list() -> None:
    response = Mock()
    response.json.return_value = [
        {"userId": 1, "id": 1, "title": "Example", "body": "Fixture"}
    ]
    session = Mock()
    session.get.return_value = response
    client = SauceDemoClient(session=session)

    posts = client.get_posts()

    assert posts[0]["id"] == 1
    client.assert_post_shape(posts[0])
    response.raise_for_status.assert_called_once_with()


def test_get_posts_rejects_non_list_payload() -> None:
    response = Mock()
    response.json.return_value = {"id": 1}
    session = Mock()
    session.get.return_value = response
    client = SauceDemoClient(session=session)

    with pytest.raises(ValueError, match="Expected list of posts"):
        client.get_posts()


def test_assert_post_shape_reports_missing_keys() -> None:
    client = SauceDemoClient(session=Mock())

    with pytest.raises(AssertionError, match="Post missing keys"):
        client.assert_post_shape({"id": 1})


def test_get_post_uses_configured_session() -> None:
    response = Mock()
    response.json.return_value = {
        "userId": 1,
        "id": 7,
        "title": "Example",
        "body": "Fixture",
    }
    session = Mock()
    session.get.return_value = response
    client = SauceDemoClient(
        base_url="https://api.example.test",
        timeout=3,
        session=session,
    )

    post = client.get_post(7)

    assert post["id"] == 7
    session.get.assert_called_once_with("https://api.example.test/posts/7", timeout=3)
    response.raise_for_status.assert_called_once_with()


def test_get_post_rejects_non_object_payload() -> None:
    response = Mock()
    response.json.return_value = []
    session = Mock()
    session.get.return_value = response
    client = SauceDemoClient(session=session)

    with pytest.raises(ValueError, match="Expected a post object"):
        client.get_post(1)
