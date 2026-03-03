from app.core.settings import Settings


def test_settings_parse_json_list_values() -> None:
    settings = Settings(
        allowed_origins='["https://example.com","https://staging.example.com"]',
        source_extensions='[".cbl",".cob"]',
    )

    assert settings.allowed_origins == ["https://example.com", "https://staging.example.com"]
    assert settings.source_extensions == [".cbl", ".cob"]


def test_settings_parse_comma_separated_list_values() -> None:
    settings = Settings(
        allowed_origins="https://a.example.com, https://b.example.com",
        source_directories="backend/data/corpus, corpus",
    )

    assert settings.allowed_origins == ["https://a.example.com", "https://b.example.com"]
    assert settings.source_directories == ["backend/data/corpus", "corpus"]
