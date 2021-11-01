import pytest


@pytest.fixture(autouse=True)
def use_dummy_cache_backend(settings):
    settings.SKIP_NEW_ACCOUNT_EMAIL = True
