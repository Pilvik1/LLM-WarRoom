from backend import config


def test_neutral_environment_name_takes_precedence(monkeypatch):
    monkeypatch.setenv("COUNCIL_TEST_SETTING", "new-value")
    monkeypatch.setenv("WARROOM_TEST_SETTING", "legacy-value")

    assert config._env(
        "COUNCIL_TEST_SETTING",
        "WARROOM_TEST_SETTING",
        "default-value",
    ) == "new-value"


def test_legacy_environment_name_remains_a_fallback(monkeypatch):
    monkeypatch.delenv("COUNCIL_TEST_SETTING", raising=False)
    monkeypatch.setenv("WARROOM_TEST_SETTING", "legacy-value")

    assert config._env(
        "COUNCIL_TEST_SETTING",
        "WARROOM_TEST_SETTING",
        "default-value",
    ) == "legacy-value"
