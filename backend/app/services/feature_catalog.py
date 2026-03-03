from app.models.features import FeatureDefinition

_FEATURES = [
    FeatureDefinition(
        key="code_explanation",
        title="Code Explanation",
        description="Explain what a specific paragraph/section does and why it matters.",
        requires_subject=True,
        example_subject="MAIN-LOGIC",
    ),
    FeatureDefinition(
        key="dependency_mapping",
        title="Dependency Mapping",
        description="Find what calls or depends on a given section, including PERFORM chains.",
        requires_subject=True,
        example_subject="READ-CUSTOMER",
    ),
    FeatureDefinition(
        key="pattern_detection",
        title="Pattern Detection",
        description="Locate recurring code patterns like file IO and control flow constructs.",
    ),
    FeatureDefinition(
        key="business_logic_extraction",
        title="Business Logic Extraction",
        description="Extract business rules affecting balances, fees, and account status.",
    ),
    FeatureDefinition(
        key="error_handling_review",
        title="Error Handling Review",
        description="Identify EOF/invalid/error handling paths and their behavior.",
    ),
]

_FEATURES_BY_KEY = {feature.key: feature for feature in _FEATURES}


def list_features() -> list[FeatureDefinition]:
    return _FEATURES


def has_feature(feature_key: str) -> bool:
    return feature_key in _FEATURES_BY_KEY


def build_feature_question(feature_key: str, subject: str | None = None) -> str:
    target = (subject or "").strip()

    if feature_key == "code_explanation":
        section = target or "MAIN-LOGIC"
        return (
            f"Explain what the COBOL section or paragraph '{section}' does. "
            "Summarize its business effect and key operations."
        )
    if feature_key == "dependency_mapping":
        section = target or "READ-CUSTOMER"
        return (
            f"Map dependencies around '{section}'. "
            "Show who calls it (PERFORM/CALL), what it calls, and related file/data interactions."
        )
    if feature_key == "pattern_detection":
        return (
            "Find recurring patterns in this codebase, focusing on file IO (OPEN/READ/WRITE/CLOSE), "
            "loop control, and section transitions."
        )
    if feature_key == "business_logic_extraction":
        return (
            "Extract the core business rules in this codebase, especially calculations and decision logic "
            "for balances, fees, and account status."
        )
    if feature_key == "error_handling_review":
        return (
            "Where does this code handle EOF, invalid records, or other failure conditions? "
            "Explain the handling path and resulting behavior."
        )

    raise KeyError(f"Unknown feature key: {feature_key}")
