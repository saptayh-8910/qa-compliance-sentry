import pytest

from api.sauce_client import SauceDemoClient

pytestmark = [pytest.mark.api, pytest.mark.external]


def test_get_posts_returns_list() -> None:
    client = SauceDemoClient()
    posts = client.get_posts()
    assert len(posts) >= 1
    client.assert_post_shape(posts[0])


def test_get_single_post() -> None:
    client = SauceDemoClient()
    post = client.get_post(1)
    assert post["id"] == 1
    client.assert_post_shape(post)
