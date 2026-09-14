from data import FEATURE_COLUMNS, ZERO_AS_MISSING, load_features_target, load_raw


def test_raw_shape():
    df = load_raw()
    assert len(df) == 768
    assert list(df.columns) == [
        *FEATURE_COLUMNS,
        "outcome",
    ]


def test_features_have_nans_for_zero_medical_fields():
    X, y = load_features_target()
    assert list(X.columns) == FEATURE_COLUMNS
    assert len(X) == len(y) == 768
    # At least some medical zeros should become NaN
    assert X[ZERO_AS_MISSING].isna().any().any()
    assert set(y.unique()) <= {0, 1}


def test_outcome_not_in_features():
    X, _ = load_features_target()
    assert "outcome" not in X.columns
