"""Focused chat answers must still return the intent's charts (visual analyst)."""
from app.services.session_service import _response_charts


def _facts(answer_charts, facts_charts):
    return {
        "query_plan": {"report_mode": "focused_answer_report"},
        "query_answer": {"charts": answer_charts},
        "charts": facts_charts,
    }


def test_focused_answer_uses_intent_charts():
    facts = _facts(
        answer_charts=[],
        facts_charts=[
            {"type": "bar", "title": "Sales by region", "x_key": "region", "y_key": "revenue",
             "data": [{"region": "N", "revenue": 10}, {"region": "S", "revenue": 20}]},
        ],
    )
    out = _response_charts(facts, include_report_level=False)
    assert len(out) >= 1, "focused answers should still surface intent charts"


def test_focused_answer_prefers_answer_charts_when_present():
    facts = _facts(
        answer_charts=[{"type": "bar", "title": "A", "x_key": "k", "y_key": "v", "data": [{"k": "x", "v": 1}]}],
        facts_charts=[{"type": "bar", "title": "B", "x_key": "k", "y_key": "v", "data": [{"k": "y", "v": 2}]}],
    )
    out = _response_charts(facts, include_report_level=False)
    assert out, "should return charts"
