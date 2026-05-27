from app.services.agent_runtime_preflight import can_fallback_to_legacy


def test_fallback_allowed_read_only_only():
    assert can_fallback_to_legacy(is_side_effect=False, is_read_only=True, classification_known=True) is True


def test_fallback_blocked_for_side_effect():
    assert can_fallback_to_legacy(is_side_effect=True, is_read_only=False, classification_known=True) is False


def test_fallback_blocked_for_unknown_classification():
    assert can_fallback_to_legacy(is_side_effect=False, is_read_only=False, classification_known=False) is False
