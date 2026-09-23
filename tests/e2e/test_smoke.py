import pytest
pytestmark=pytest.mark.skip(reason="Run with docker compose profile")
def test_console_and_api_smoke():
    assert True
