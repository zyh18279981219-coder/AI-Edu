from types import SimpleNamespace

from DashboardModule import dashboard_api as api


def configure(monkeypatch, content):
    monkeypatch.setenv("TEACHER_DEMO_FILE", "")
    monkeypatch.setattr(api._teacher_twin_service, "build_summary", lambda _: {
        "teacher_username": "teacher", "dimensions": [], "student_scope": {}})
    monkeypatch.setattr(api, "_get_llm_env", lambda: ("test-model", "https://example.invalid", "test-key"))
    def model(**kwargs):
        assert kwargs["timeout"] == 45 and kwargs["max_retries"] == 0
        return SimpleNamespace(invoke=lambda _: SimpleNamespace(content=content))
    monkeypatch.setattr(api, "ChatOpenAI", model)
    monkeypatch.setattr(api, "get_llm_logger", lambda: SimpleNamespace(log_llm_call=lambda **_: None))


def test_empty_model_result_is_visible_failure_not_success(monkeypatch):
    configure(monkeypatch, '{}')
    result = api.generate_teacher_twin_ai_suggestions({"username": "teacher"})
    assert result["is_ai_generated"] is False
    assert "未返回完整" in result["message"]


def test_valid_model_result_populates_both_cards(monkeypatch):
    configure(monkeypatch, '{"teaching_strategy_suggestions":[{"dimension":"评估","advice":"分层测验"}],"intervention_suggestions":[{"trigger":"低分","action":"安排复习"}]}')
    result = api.generate_teacher_twin_ai_suggestions({"username": "teacher"})
    assert result["is_ai_generated"] is True
    assert result["teaching_strategy_suggestions"][0]["advice"] == "分层测验"
    assert result["intervention_suggestions"][0]["action"] == "安排复习"
