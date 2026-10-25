import pytest

from backend.providers.model_registry import complete_with_alias


@pytest.mark.asyncio
async def test_unknown_alias_returns_inspectable_error():
    response = await complete_with_alias("does_not_exist", user_prompt="hello")
    assert response.error == "Unknown model alias: does_not_exist"
    assert response.attempted_aliases == ["does_not_exist"]
