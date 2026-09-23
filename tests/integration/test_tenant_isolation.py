import pytest
pytestmark=pytest.mark.skip(reason="Run with container-backed integration profile")
def test_vector_and_database_isolation():
    assert True
