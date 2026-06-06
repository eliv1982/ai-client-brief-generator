# AI Client Brief Generator

Инструмент для автоматического превращения текстовых материалов клиентского диалога в структурированный PDF-отчет на русском языке.

Проект ориентирован на русскоязычные бизнес-сценарии и формирует PDF-отчеты с корректной кириллицей, датами и бюджетами в рублях.

---

## Режимы работы

### `client_report` — Отчет по клиентскому запросу

Универсальный режим для любого типа клиентского диалога. Извлекает: суть запроса, проблемы и потребности клиента, требования к решению, сроки, бюджет, риски и следующие шаги.

```bash
python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_report
```

### `design_report` — Отчет по дизайн-запросу с изображением

Режим для диалогов о разработке сайта или лендинга. Дополнительно извлекает: цель дизайна, целевую аудиторию, визуальные предпочтения, основные блоки сайта и функциональные требования. Генерирует AI-изображение с визуальной концепцией.

```bash
python main.py example_dialogs/website_design_dialog.txt --mode design_report
```

По умолчанию проект использует `gpt-image-2` для генерации изображений — при наличии доступа к модели в вашем OpenAI project. Если `gpt-image-2` недоступна, можно использовать `gpt-image-1`. Prompt для визуальной концепции формируется автоматически на основе диалога и используется только внутри системы — в итоговом PDF он не отображается. Проверить доступность моделей можно командой:

```bash
python main.py --test-image
```

Генерация изображения является дополнительной функцией. Если image API не настроен или запрос завершился ошибкой, текстовый PDF все равно будет сформирован — с placeholder-блоком вместо изображения.

### `client_brief` — технический alias

`client_brief` сохранен как alias для `client_report` — старые команды не ломаются:

```bash
python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_brief
```

---

## Как проект получает данные

Проект **не подключается напрямую** к CRM, Telegram, Google Docs или другим сервисам. На текущем этапе единственный источник — локальный `.txt`-файл с транскрибацией или текстовыми материалами.

Как получить файл:

- **Zoom / Google Meet** — скачать автоматическую транскрибацию из записи встречи.
- **Telegram** — скопировать переписку в `.txt`.
- **Диктофон / телефонный звонок** — расшифровать через Whisper, Yandex SpeechKit или другой сервис, сохранить как `.txt`.
- **CRM** — экспортировать историю переписки или комментарии к сделке.

После этого положить файл в папку `input_dialogs/` и запустить генерацию.

---

## Структура проекта

```
ai-client-brief-generator/
├── main.py                               # Точка входа (CLI)
├── example_dialogs/                      # Учебные примеры для проверки
│   ├── ai_bot_client_dialog.txt          # Telegram-бот для обработки заявок
│   ├── website_design_dialog.txt         # Лендинг для студии йоги
│   ├── rag_assistant_client_dialog.txt   # RAG-ассистент по базе знаний
│   ├── customer_reviews_dialog.txt       # Автоматизация анализа отзывов
│   └── pdf_reports_dialog.txt            # Автогенерация PDF-отчетов
├── input_dialogs/                        # Сюда кладите ваши текстовые материалы
├── reports/                              # Готовые PDF сохраняются сюда
├── generated_images/                     # AI-изображения для design_report
├── templates/
│   ├── client_brief_template.html        # Шаблон client_report
│   └── design_report_template.html       # Шаблон design_report
├── utils/
│   ├── logger.py
│   ├── validators.py                     # Схемы для обоих режимов
│   ├── ai_processor.py                   # OpenAI: два промпта, два экстрактора
│   ├── pdf_generator.py                  # Два рендера PDF
│   └── image_generator.py               # GPT Image генерация с fallback
├── .env.example
├── requirements.txt
└── README.md
```

---

## Требования

- Python 3.11+
- [API-ключ OpenAI](https://platform.openai.com/api-keys)
- Системные зависимости WeasyPrint (см. ниже)

### Системные зависимости WeasyPrint

**Windows** — установите [GTK3 Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases), затем перезапустите терминал. Альтернатива — WSL.

**macOS**:
```bash
brew install pango gdk-pixbuf libffi cairo
```

**Ubuntu / Debian**:
```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf2.0-0
```

> HTML-шаблоны используют шрифт **DejaVu Sans** — поставляется с WeasyPrint, имеет полную поддержку кириллицы.

---

## Установка

```bash
cd ai-client-brief-generator

python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Настройка

```bash
cp .env.example .env
```

Откройте `.env`:

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Для режима design_report (GPT Image models, 2026):
IMAGE_MODEL=gpt-image-2      # gpt-image-2 (preferred) или gpt-image-1 (fallback)
IMAGE_SIZE=1024x1024         # 1024x1024 | 1536x1024 | 1024x1536
IMAGE_QUALITY=medium         # low | medium | high | auto

LOG_LEVEL=INFO
```

> **Про модели генерации изображений.** По умолчанию используется `gpt-image-2` — предпочтительная модель для генерации изображений при наличии доступа в вашем OpenAI project. Модели `dall-e-3` и `dall-e-2` относятся к предыдущему поколению (previous generation) и могут быть недоступны. Для проверки доступных моделей запустите `python main.py --test-image`.

---

## Все команды

### Диагностика генерации изображений

```bash
python main.py --test-image
```

Проверяет подключение к image API с текущими настройками из `.env`. При неудаче выводит точную ошибку от OpenAI, статус-код и список моделей, доступных на вашем аккаунте.

### Посмотреть список доступных файлов

```bash
python main.py --list-files
```

### Интерактивный выбор файла и типа отчета

```bash
python main.py --interactive
```

Программа покажет все `.txt`-файлы, предложит выбрать файл, затем — тип отчета.

### Отчет по клиентскому запросу

```bash
python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_report
python main.py input_dialogs/my_dialog.txt --mode client_report
```

### Отчет по дизайн-запросу с AI-изображением

```bash
python main.py example_dialogs/website_design_dialog.txt --mode design_report
```

---

## Где найти готовые файлы

Имена файлов включают дату и время с точностью до секунды:

```
reports/client_report_2026-06-06_12-00-28.pdf
reports/design_report_2026-06-06_15-42-10.pdf
generated_images/design_concept_2026-06-06_15-42-05.png
```

Повторный запуск создает новые уникальные файлы — существующие не перезаписываются.

---

## Обработка ошибок

| Ситуация | Поведение |
|---|---|
| Не задан API-ключ | Подсказка с инструкцией по настройке `.env` |
| Файл не найден | `[ERROR] Файл не найден: <путь>` |
| Файл не в UTF-8 | `[ERROR] Не удалось прочитать файл как UTF-8` |
| Файл пустой | `[ERROR] Файл пустой: <путь>` |
| OpenAI вернул невалидный JSON | `[ERROR] OpenAI вернул некорректный или неполный ответ` |
| Модель image API недоступна | Точная ошибка + список доступных моделей, PDF формируется без изображения |
| PDF заблокирован (PermissionError) | `[ERROR] Не удалось сохранить PDF. Возможно, файл уже открыт.` |

### Устранение ошибки Permission denied на Windows

Если при генерации PDF появляется ошибка `Permission denied`:

- Убедитесь, что файл отчета не открыт в просмотрщике PDF (Adobe Acrobat, браузер и т.д.).
- Проект создает уникальные имена файлов с секундами, но открытый файл может быть заблокирован Windows.
- Закройте PDF-просмотрщик и повторите запуск.

---

## Дорожная карта

- **Фаза 3** — интерфейс через Telegram-бот
- **Фаза 4** — Flask API для веб-интеграции
