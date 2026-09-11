"""A module fixture named fake_home cannot replace or become the security floor."""

import os

import pytest


@pytest.fixture
def fake_home():
    raise AssertionError("An unrequested module fixture became autouse")


def test_private_home_floor_survives_a_module_fixture_override(_disposable_test_home):
    assert os.environ["HOME"] == str(_disposable_test_home)
    assert os.environ["USERPROFILE"] == str(_disposable_test_home)
    assert (_disposable_test_home / ".aws" / "credentials").is_file()
    assert (_disposable_test_home / ".aws" / "config").is_file()
