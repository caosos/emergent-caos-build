from app.services.agent_permission_classifier import classify_request_intent


def test_detect_repo_write_intent():
    d = classify_request_intent("Please edit code and create pr for this repo")
    assert d.approval_required is True
    assert d.is_read_only is False


def test_detect_email_send_intent():
    d = classify_request_intent("send email to team about outage")
    assert d.approval_required is True


def test_detect_calendar_create_intent():
    d = classify_request_intent("create calendar event for Friday")
    assert d.approval_required is True


def test_detect_memory_write_intent():
    d = classify_request_intent("remember this preference forever")
    assert d.approval_required is True


def test_read_only_inspection_allowed():
    d = classify_request_intent("check my github repo and report what needs attention")
    assert d.approval_required is False
    assert d.is_read_only is True
