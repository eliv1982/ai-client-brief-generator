from __future__ import annotations

from utils.pdf_generator import _get_jinja_env

_XSS_PAYLOAD = "<script>alert('xss')</script>"
_INJECTION_PAYLOAD = '<img src=x onerror=alert(1)>"><svg onload=alert(2)>'


def _render_client_brief(**overrides) -> str:
    env = _get_jinja_env()
    template = env.get_template("client_brief_template.html")
    data = {
        "client_name": "Иван Иванов",
        "company_or_project": "Кофейня «Аромат»",
        "topic": "Автоматизация приема заказов",
        "main_request": "Суть запроса клиента.",
        "client_pain_points": ["Проблема один", "Проблема два"],
        "requirements": ["Требование один"],
        "deadline": "до конца июля",
        "budget": "150 000 руб.",
        "risks_or_open_questions": ["Риск один"],
        "next_steps": ["Шаг один"],
        "summary": "Краткое резюме.",
        "generated_at": "01.01.2026, 12:00",
    }
    data.update(overrides)
    return template.render(**data)


def _render_design_report(**overrides) -> str:
    env = _get_jinja_env()
    template = env.get_template("design_report_template.html")
    data = {
        "client_name": "Мария Петрова",
        "company_or_project": "Студия йоги",
        "project_type": "Лендинг",
        "design_goal": "Цель дизайна.",
        "target_audience": "Целевая аудитория.",
        "preferred_style": "Минимализм",
        "key_sections": ["Главный экран"],
        "colors_or_visual_preferences": "Бежевый и терракотовый.",
        "functional_requirements": ["Форма записи"],
        "deadline": "к 1 сентября",
        "budget": "100 000 руб.",
        "risks_or_open_questions": ["Риск один"],
        "next_steps": ["Шаг один"],
        "summary": "Краткое резюме.",
        "generated_at": "01.01.2026, 12:00",
        "image_uri": None,
    }
    data.update(overrides)
    return template.render(**data)


# ── Representative render succeeds ──────────────────────────────────────────

def test_client_brief_template_renders_representative_payload():
    html = _render_client_brief()
    assert "<html" in html
    assert "</html>" in html
    assert "Иван Иванов" in html


def test_design_report_template_renders_representative_payload():
    html = _render_design_report()
    assert "<html" in html
    assert "</html>" in html
    assert "Студия йоги" in html


# ── Escaping / no raw HTML injection ─────────────────────────────────────────

def test_client_brief_template_escapes_scalar_field():
    html = _render_client_brief(client_name=_XSS_PAYLOAD)
    assert _XSS_PAYLOAD not in html
    assert "&lt;script&gt;" in html


def test_client_brief_template_escapes_summary_field():
    html = _render_client_brief(summary=_INJECTION_PAYLOAD)
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img" in html


def test_client_brief_template_escapes_list_items():
    html = _render_client_brief(client_pain_points=[_INJECTION_PAYLOAD])
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img" in html


def test_client_brief_template_escapes_next_steps_list():
    html = _render_client_brief(next_steps=[_XSS_PAYLOAD])
    assert _XSS_PAYLOAD not in html
    assert "&lt;script&gt;" in html


def test_design_report_template_escapes_key_sections_tags():
    html = _render_design_report(key_sections=[_INJECTION_PAYLOAD])
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img" in html


def test_design_report_template_escapes_functional_requirements():
    html = _render_design_report(functional_requirements=[_XSS_PAYLOAD])
    assert _XSS_PAYLOAD not in html
    assert "&lt;script&gt;" in html


def test_design_report_template_placeholder_when_no_image():
    html = _render_design_report(image_uri=None)
    assert "<img" not in html
    assert "Изображение не было сгенерировано" in html


def test_design_report_template_does_not_allow_arbitrary_image_uri_injection():
    # image_uri is only ever produced internally from a local generated file
    # path (see pdf_generator.render_design_report_pdf) — never from raw
    # model/user text — but the template itself must still only ever emit
    # it inside a plain src attribute, never unescaped into markup.
    malicious = '"><script>alert(1)</script>'
    html = _render_design_report(image_uri=malicious)
    assert "<script>alert(1)</script>" not in html
