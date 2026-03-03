from app.services.feature_catalog import build_feature_question, has_feature, list_features


def test_feature_catalog_contains_expected_features() -> None:
    features = list_features()
    keys = {feature.key for feature in features}

    assert len(features) >= 4
    assert "code_explanation" in keys
    assert "dependency_mapping" in keys
    assert "business_logic_extraction" in keys
    assert has_feature("pattern_detection") is True
    assert has_feature("nonexistent") is False


def test_build_feature_question_uses_subject_or_default() -> None:
    with_subject = build_feature_question("code_explanation", "READ-CUSTOMER")
    default_subject = build_feature_question("code_explanation", "")

    assert "READ-CUSTOMER" in with_subject
    assert "MAIN-LOGIC" in default_subject
