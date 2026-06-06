from __future__ import annotations

import json
import os

from openai import OpenAI, OpenAIError

from utils.logger import get_logger
from utils.validators import BriefValidationError, validate_brief

logger = get_logger(__name__)

BRIEF_SYSTEM_PROMPT = """Ты — опытный бизнес-аналитик. Твоя задача — прочитать расшифровку диалога с клиентом и извлечь из него структурированную информацию для формирования отчета по клиентскому запросу.

Верни ТОЛЬКО валидный JSON-объект — без markdown-обертки, без лишнего текста — строго со следующими полями:

{
  "client_name": "строка — полное имя клиента, или «Не указано»",
  "company_or_project": "строка — название компании или проекта, или «Не указано»",
  "topic": "строка — тема диалога одной фразой, деловым языком",
  "main_request": "строка — суть запроса клиента, сформулированная четко и по делу",
  "client_pain_points": ["строка — конкретная проблема, потребность или операционная сложность клиента", "..."],
  "requirements": ["строка — конкретное требование к решению", "..."],
  "deadline": "строка — сроки из диалога, или «Не указан»",
  "budget": "строка — бюджет из диалога, или «Не обсуждалось», или «Требует уточнения»",
  "risks_or_open_questions": ["строка — риск или вопрос, требующий уточнения", "..."],
  "next_steps": ["строка — конкретное действие на следующем этапе", "..."],
  "summary": "строка — деловое резюме диалога в 2–4 предложениях"
}

Требования к стилю:
- Деловой, точный русский язык — без канцелярита, без рекламных клише, без воды.
- Вместо разговорного «боли клиента» формулировать как «проблемы», «потребности», «операционные сложности», «затруднения».
- Не использовать восклицательные знаки, оценочные слова («отлично», «уникальный», «инновационный»).
- Каждый пункт списка — конкретная, самостоятельная мысль.
- Не использовать букву «ё» в русском тексте. Использовать «е»: «еще», «все», «отчет», «четко» и т.д.
- Каждое предложение и каждый пункт начинать с заглавной буквы.

Правила извлечения данных:
- Все текстовые значения — строго на русском языке.
- Имена собственные, названия компаний, сервисов и технологий не переводить: Telegram, Bitrix24, Notion, Google Sheets, OpenAI, RAG, CRM, Yclients, QUIK, Confluence, WordPress, Tilda, Яндекс Карты, 2ГИС и другие.
- Бюджет:
  * если назван в рублях — сохранять как есть, например «от 150 000 до 200 000 руб.» или «до 350 000 руб.»;
  * если в другой валюте — сохранять без конвертации;
  * если не назван — писать «Не обсуждалось»;
  * если упомянут, но не конкретизирован — писать «Требует уточнения».
- Сроки:
  * записывать так, как указано в диалоге: «до конца июля», «к 1 сентября 2026», «около 3 месяцев»;
  * если не упомянуты — писать «Не указан».
- Не выдумывать факты: никакого бюджета, сроков, технологий или требований, которых не было в диалоге.
- Каждое поле обязательно. Для списков — пустой список [], если данных нет.
- Не добавлять поля сверх схемы.
- Не оборачивать результат в markdown-блоки.
"""


def extract_brief_from_dialog(dialog_text: str) -> dict:
    """Send *dialog_text* to OpenAI and return the validated brief dict.

    Raises:
        EnvironmentError: if OPENAI_API_KEY is not set.
        OpenAIError: on API-level failures.
        BriefValidationError: if the response is not valid JSON or fails schema checks.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    client = OpenAI(api_key=api_key)

    logger.info("Sending dialog to OpenAI (model: %s) …", model)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": BRIEF_SYSTEM_PROMPT},
                {"role": "user", "content": dialog_text},
            ],
        )
    except OpenAIError as exc:
        logger.error("OpenAI API error: %s", exc)
        raise

    raw_content = response.choices[0].message.content or ""
    logger.debug("Raw OpenAI response:\n%s", raw_content)

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise BriefValidationError(
            f"OpenAI returned content that is not valid JSON: {exc}\n"
            f"Response was:\n{raw_content}"
        ) from exc

    logger.info("Response received — validating schema …")
    validated = validate_brief(data)
    logger.info("Schema validation passed.")
    return validated
