from app.services.agent_secret_redaction import redact_secrets_text


def test_redacts_api_key_token_password_and_bearer():
    raw = "api_key=sk-123456 token: abcdef password=hunter2 Authorization: Bearer mysecretbearertoken"
    red = redact_secrets_text(raw)
    assert "sk-123456" not in red
    assert "abcdef" not in red
    assert "hunter2" not in red
    assert "mysecretbearertoken" not in red
    assert "api_key=" in red
    assert "token:" in red
    assert "password=" in red
    assert "Bearer " in red
