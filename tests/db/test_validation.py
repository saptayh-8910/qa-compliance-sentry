from pathlib import Path

import pytest

from api.sauce_client import SauceDemoClient
from db.validation import DataValidator


@pytest.fixture
def validator(tmp_path: Path) -> DataValidator:
    db = tmp_path / "test.db"
    return DataValidator(db)


@pytest.mark.db
def test_all_seed_validations_pass(validator: DataValidator) -> None:
    results = validator.run_all()
    assert all(r.passed for r in results), [r for r in results if not r.passed]


@pytest.mark.db
def test_api_db_consistency(validator: DataValidator) -> None:
    post = SauceDemoClient().get_post(1)
    result = validator.api_post_matches_catalog(post, product_id=1)
    assert result.passed, result.detail
