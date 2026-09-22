from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure the project root (containing main.py and utils/) is importable
# no matter what directory pytest is invoked from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Keep every test offline and independent of the developer's real .env.

    main.py calls load_dotenv() at import time, which may have already
    populated a real OPENAI_API_KEY into the process environment. Tests
    must never rely on (or accidentally use) real credentials.
    """
    for var in ("OPENAI_API_KEY", "OPENAI_MODEL", "IMAGE_MODEL", "IMAGE_SIZE", "IMAGE_QUALITY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def valid_brief_payload() -> dict:
    return {
        "client_name": "Иван Иванов",
        "company_or_project": "Кофейня «Аромат»",
        "topic": "Автоматизация приема заказов через Telegram-бота",
        "main_request": (
            "Клиент хочет автоматизировать прием заказов и снизить нагрузку на администратора."
        ),
        "client_pain_points": [
            "Много ручной работы у администратора",
            "Задержки в ответах клиентам",
        ],
        "requirements": [
            "Интеграция с Telegram",
            "Уведомления о новых заказах",
        ],
        "deadline": "до конца июля",
        "budget": "от 150 000 до 200 000 руб.",
        "risks_or_open_questions": ["Не уточнена интеграция с кассой"],
        "next_steps": ["Подготовить техническое задание", "Согласовать бюджет"],
        "summary": (
            "Клиент запросил Telegram-бота для приема заказов. "
            "Обсуждены требования и ориентировочные сроки."
        ),
    }


@pytest.fixture
def valid_design_payload() -> dict:
    return {
        "client_name": "Мария Петрова",
        "company_or_project": "Студия йоги «Дыхание»",
        "project_type": "Лендинг",
        "design_goal": "Привлечь новых клиентов на пробное занятие.",
        "target_audience": "Женщины 25-45 лет, интересующиеся йогой и здоровым образом жизни.",
        "preferred_style": "Минимализм",
        "key_sections": ["Главный экран", "О студии", "Расписание", "Контакты"],
        "colors_or_visual_preferences": "Бежевый и терракотовый, натуральные текстуры.",
        "functional_requirements": [
            "Форма записи на пробное занятие",
            "Интеграция с Yclients",
        ],
        "deadline": "к 1 сентября 2026",
        "budget": "от 80 000 до 120 000 руб.",
        "risks_or_open_questions": ["Не определен окончательный список инструкторов"],
        "next_steps": ["Подготовить макет", "Согласовать цветовую палитру"],
        "summary": (
            "Клиент хочет лендинг для студии йоги с акцентом на запись на пробное занятие."
        ),
        "image_prompt": (
            "Minimalist yoga studio hero concept, warm beige and terracotta palette, "
            "soft natural side lighting, clean open layout, abstract card shapes with no "
            "text, no letters, no words, no UI copy, no logos, no labels."
        ),
    }


# A minimal, valid 1x1 transparent PNG — used wherever a real image file is
# needed (e.g. rendering a design report through WeasyPrint) without ever
# calling the image API.
MINIMAL_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
