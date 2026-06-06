"""AI Client Brief Generator — entry point.

Usage examples:
    python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_report
    python main.py example_dialogs/website_design_dialog.txt --mode design_report
    python main.py input_dialogs/my_dialog.txt --mode client_report
    python main.py --list-files
    python main.py --interactive

    # client_brief is kept as a backward-compatible alias for client_report
    python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_brief
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows terminals that default to cp1251
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

from utils.logger import get_logger

load_dotenv()
logger = get_logger("main")

# Mode registry: canonical name -> display label
_MODES: dict[str, str] = {
    "client_report": "Отчет по клиентскому запросу",
    "design_report": "Отчет по дизайн-запросу с изображением",
}
# Backward-compatible aliases: alias -> canonical
_MODE_ALIASES: dict[str, str] = {
    "client_brief": "client_report",
}

SUPPORTED_MODES = tuple(_MODES) + tuple(_MODE_ALIASES)
_CANONICAL_DEFAULT = "client_report"

SCAN_DIRS = ("example_dialogs", "input_dialogs")


def _canonical(mode: str) -> str:
    return _MODE_ALIASES.get(mode, mode)


def _display(canonical_mode: str) -> str:
    return _MODES.get(canonical_mode, canonical_mode)


# ── File discovery ─────────────────────────────────────────────────────────────

def find_txt_files() -> list[Path]:
    found: list[Path] = []
    for dir_name in SCAN_DIRS:
        directory = Path(dir_name)
        if directory.is_dir():
            found.extend(sorted(directory.glob("*.txt")))
    return found


def _file_preview(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig").strip()
        first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        if len(first_line) > 72:
            first_line = first_line[:69] + "..."
        return first_line
    except Exception:
        return ""


def print_file_list(files: list[Path]) -> None:
    if not files:
        print("\nТекстовые материалы не найдены в папках: " + ", ".join(SCAN_DIRS))
        print(
            "Положите транскрибацию или текстовый материал в папку "
            "input_dialogs/ и повторите запуск.\n"
        )
        return

    print("\nДоступные материалы для обработки:\n")
    for i, path in enumerate(files, start=1):
        try:
            size = len(path.read_text(encoding="utf-8-sig"))
            size_label = f"{size} символов"
        except Exception:
            size_label = "? символов"
        preview = _file_preview(path)
        print(f"  [{i}] {path}  —  {size_label}")
        if preview:
            print(f"       {preview}")
    print()


# ── Dialog file reading ────────────────────────────────────────────────────────

def read_dialog_file(path: Path) -> str:
    if not path.exists():
        logger.error("File not found: %s", path)
        print(f"\n[ERROR] Файл не найден: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        logger.error("Cannot decode file as UTF-8: %s", path)
        print(
            f"\n[ERROR] Не удалось прочитать файл как UTF-8: {path}\n"
            "Убедитесь, что файл сохранен в кодировке UTF-8.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not text.strip():
        logger.error("File is empty: %s", path)
        print(f"\n[ERROR] Файл пустой: {path}", file=sys.stderr)
        sys.exit(1)

    logger.info("Файл загружен: %s (%d символов).", path, len(text))
    return text


# ── Error handling helpers ─────────────────────────────────────────────────────

def _handle_openai_errors(exc: Exception) -> None:
    from utils.validators import BriefValidationError

    if isinstance(exc, EnvironmentError):
        logger.error("Environment error: %s", exc)
        print(f"\n[ERROR] {exc}", file=sys.stderr)
    elif isinstance(exc, BriefValidationError):
        logger.error("Некорректный ответ от OpenAI:\n%s", exc)
        print(
            f"\n[ERROR] OpenAI вернул некорректный или неполный ответ:\n{exc}",
            file=sys.stderr,
        )
    else:
        logger.error("Ошибка при обращении к OpenAI: %s", exc, exc_info=True)
        print(f"\n[ERROR] Ошибка при обращении к OpenAI: {exc}", file=sys.stderr)
    sys.exit(1)


def _handle_pdf_errors(exc: Exception) -> None:
    if isinstance(exc, FileNotFoundError):
        logger.error("Шаблон не найден: %s", exc)
        print(f"\n[ERROR] {exc}", file=sys.stderr)
    elif isinstance(exc, PermissionError):
        logger.error("PermissionError при сохранении PDF: %s", exc)
        print(
            "\n[ERROR] Не удалось сохранить PDF. "
            "Возможно, файл с таким именем уже открыт. "
            "Закройте PDF и повторите попытку.",
            file=sys.stderr,
        )
    elif isinstance(exc, RuntimeError):
        logger.error("Ошибка генерации PDF: %s", exc)
        print(f"\n[ERROR] {exc}", file=sys.stderr)
    else:
        logger.error("Неожиданная ошибка при генерации PDF: %s", exc, exc_info=True)
        print(f"\n[ERROR] Неожиданная ошибка при генерации PDF: {exc}", file=sys.stderr)
    sys.exit(1)


# ── Mode runners ───────────────────────────────────────────────────────────────

def run_client_report(dialog_path: Path) -> None:
    from utils.ai_processor import extract_brief_from_dialog
    from utils.pdf_generator import render_client_brief_pdf
    from utils.validators import BriefValidationError

    logger.info("Чтение файла диалога: %s", dialog_path)
    dialog_text = read_dialog_file(dialog_path)

    try:
        brief_data = extract_brief_from_dialog(dialog_text)
    except (EnvironmentError, BriefValidationError, Exception) as exc:
        _handle_openai_errors(exc)
        return

    try:
        pdf_path = render_client_brief_pdf(brief_data)
    except Exception as exc:
        _handle_pdf_errors(exc)
        return

    print(f"\n[OK] Отчет успешно сформирован!\n  -> {pdf_path.resolve()}\n")


def run_design_report(dialog_path: Path) -> None:
    from utils.ai_processor import extract_design_report_from_dialog
    from utils.image_generator import generate_design_image
    from utils.pdf_generator import render_design_report_pdf
    from utils.validators import BriefValidationError

    logger.info("Чтение файла диалога: %s", dialog_path)
    dialog_text = read_dialog_file(dialog_path)

    try:
        design_data = extract_design_report_from_dialog(dialog_text)
    except (EnvironmentError, BriefValidationError, Exception) as exc:
        _handle_openai_errors(exc)
        return

    image_prompt = design_data.get("image_prompt", "")
    image_path: Path | None = None
    if image_prompt:
        logger.info("Generating concept image ...")
        image_path = generate_design_image(image_prompt)
        if image_path:
            logger.info("Concept image ready: %s", image_path)
        else:
            logger.warning(
                "Image generation skipped or failed — PDF will be generated without image."
            )
            print(
                "[WARNING] Изображение не было сгенерировано. "
                "Подробности смотрите в логах.",
                file=sys.stderr,
            )
    else:
        logger.warning("image_prompt is empty — skipping image generation.")
        print(
            "[WARNING] image_prompt пустой — генерация изображения пропущена.",
            file=sys.stderr,
        )

    try:
        pdf_path = render_design_report_pdf(design_data, image_path)
    except Exception as exc:
        _handle_pdf_errors(exc)
        return

    print(f"\n[OK] Отчет успешно сформирован!\n  -> {pdf_path.resolve()}\n")
    if image_path:
        print(f"     Изображение: {image_path.resolve()}\n")


# ── CLI modes ──────────────────────────────────────────────────────────────────

def cmd_test_image() -> None:
    """--test-image: диагностика image API — полный вывод ошибки."""
    from utils.image_generator import (
        generate_test_image,
        list_available_image_models,
        _DEFAULT_MODEL,
        _DEFAULT_SIZE,
        _DEFAULT_QUALITY,
    )

    model = os.getenv("IMAGE_MODEL", _DEFAULT_MODEL)
    size = os.getenv("IMAGE_SIZE", _DEFAULT_SIZE)
    quality = os.getenv("IMAGE_QUALITY", _DEFAULT_QUALITY)
    api_key = os.getenv("OPENAI_API_KEY", "")

    print("\nДиагностика image API")
    print("=" * 48)
    print(f"  Модель      : {model}")
    print(f"  Размер      : {size}")
    print(f"  Качество    : {quality}")
    print(f"  API key     : {'задан (' + api_key[:8] + '...)' if api_key else 'НЕ ЗАДАН'}")
    print(f"  Endpoint    : https://api.openai.com/v1/images/generations")
    print()

    image_path, error_text = generate_test_image()

    if image_path:
        print(f"[OK] Тестовое изображение сохранено:\n  -> {image_path.resolve()}\n")
        return

    # ── Неудача — максимально подробный вывод ─────────────────────────────────
    print("[ERROR] Генерация тестового изображения не удалась.", file=sys.stderr)
    print(file=sys.stderr)

    if error_text:
        print("Текст ошибки от OpenAI API:", file=sys.stderr)
        print("-" * 48, file=sys.stderr)
        print(error_text, file=sys.stderr)
        print("-" * 48, file=sys.stderr)
        print(file=sys.stderr)

    # Специфичная диагностика по тексту ошибки
    err_lower = (error_text or "").lower()
    if not api_key:
        print(
            "[HINT] OPENAI_API_KEY не задан. Добавьте его в файл .env и повторите.",
            file=sys.stderr,
        )
    elif "does not exist" in err_lower or "invalid_value" in err_lower and "model" in err_lower:
        print(
            f"[ERROR] Модель '{model}' недоступна для текущего OpenAI project / account.\n"
            "  Проверьте Billing, Limits и Project API key на platform.openai.com",
            file=sys.stderr,
        )
        print(file=sys.stderr)
        # Пробуем вывести список доступных image-моделей
        print("  Запрашиваем доступные image-модели для вашего аккаунта ...", file=sys.stderr)
        available = list_available_image_models()
        if available:
            print(f"  Доступные модели: {', '.join(available)}", file=sys.stderr)
            print(
                f"\n  Обновите IMAGE_MODEL в .env — например:\n"
                f"    IMAGE_MODEL={available[0]}",
                file=sys.stderr,
            )
        else:
            print(
                "  Список моделей получить не удалось. "
                "Проверьте API key и интернет-соединение.",
                file=sys.stderr,
            )
    elif "invalid_value" in err_lower and "quality" in err_lower:
        print(
            f"[HINT] Значение quality='{quality}' не поддерживается моделью '{model}'.\n"
            "  Для gpt-image-2 / gpt-image-1 используйте: low, medium, high, auto",
            file=sys.stderr,
        )
    elif "invalid_value" in err_lower and "size" in err_lower:
        print(
            f"[HINT] Значение size='{size}' не поддерживается моделью '{model}'.\n"
            "  Для gpt-image-2 / gpt-image-1: 1024x1024, 1536x1024, 1024x1536",
            file=sys.stderr,
        )
    elif "billing" in err_lower or "quota" in err_lower or "insufficient" in err_lower:
        print(
            "[HINT] Проблема с оплатой или квотой.\n"
            "  Проверьте баланс на platform.openai.com/account/billing",
            file=sys.stderr,
        )
    else:
        print(
            "  Подробности смотрите в логах выше.\n"
            "  Документация: https://platform.openai.com/docs/api-reference/images",
            file=sys.stderr,
        )

    sys.exit(1)


def cmd_list_files() -> None:
    print_file_list(find_txt_files())


def _pick_file(files: list[Path]) -> Path:
    """Interactive file picker. Returns the chosen Path."""
    while True:
        raw = input("Введите номер файла: ").strip()
        if not raw.isdigit():
            print(f"  Введите число от 1 до {len(files)}.")
            continue
        idx = int(raw)
        if not (1 <= idx <= len(files)):
            print(f"  Номер должен быть от 1 до {len(files)}.")
            continue
        return files[idx - 1]


def _pick_mode() -> str:
    """Interactive mode picker. Returns canonical mode name."""
    canonical_modes = list(_MODES.keys())
    print("\nТип отчета:\n")
    for i, mode in enumerate(canonical_modes, start=1):
        print(f"  [{i}] {_display(mode)}")
    print()
    while True:
        raw = input("Введите номер типа отчета (Enter = 1): ").strip()
        if raw == "":
            return canonical_modes[0]
        if not raw.isdigit():
            print(f"  Введите число от 1 до {len(canonical_modes)}.")
            continue
        idx = int(raw)
        if not (1 <= idx <= len(canonical_modes)):
            print(f"  Номер должен быть от 1 до {len(canonical_modes)}.")
            continue
        return canonical_modes[idx - 1]


def cmd_interactive(default_mode: str) -> None:
    files = find_txt_files()
    if not files:
        print_file_list(files)
        sys.exit(0)

    print_file_list(files)
    chosen = _pick_file(files)

    canonical = _pick_mode()
    label = _display(canonical)
    print(f"\nВыбран файл: {chosen}")
    print(f"Тип отчета: {label}\n")
    logger.info("Interactive: выбран '%s', режим=%s", chosen, canonical)

    _dispatch(chosen, canonical)


def _dispatch(dialog_path: Path, canonical: str) -> None:
    if canonical == "client_report":
        run_client_report(dialog_path)
    elif canonical == "design_report":
        run_design_report(dialog_path)
    else:
        print(f"[ERROR] Режим '{canonical}' еще не реализован.", file=sys.stderr)
        sys.exit(1)


def cmd_run_file(dialog_path: Path, mode: str) -> None:
    canonical = _canonical(mode)
    logger.info("Тип отчета: %s | Файл: %s", _display(canonical), dialog_path)
    _dispatch(dialog_path, canonical)


# ── Argument parsing ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "AI Client Brief Generator\n"
            "Преобразует транскрибацию клиентского диалога в PDF-отчет.\n\n"
            "Примеры:\n"
            "  python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_report\n"
            "  python main.py example_dialogs/website_design_dialog.txt --mode design_report\n"
            "  python main.py --list-files\n"
            "  python main.py --interactive"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "dialog_file",
        type=Path,
        nargs="?",
        help="Путь к .txt-файлу с транскрибацией или текстовым материалом.",
    )
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default=_CANONICAL_DEFAULT,
        help=(
            "Тип отчета: client_report (по умолчанию) или design_report. "
            "client_brief — технический alias для client_report."
        ),
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="Показать список доступных файлов и выйти.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Интерактивный выбор файла и типа отчета.",
    )
    parser.add_argument(
        "--test-image",
        action="store_true",
        help="Диагностика: сгенерировать тестовое изображение и сохранить в generated_images/.",
    )
    return parser.parse_args()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    if args.test_image:
        cmd_test_image()
        return

    if args.list_files:
        cmd_list_files()
        return

    if args.interactive:
        cmd_interactive(args.mode)
        return

    if args.dialog_file is None:
        print(
            "[ERROR] Укажите путь к файлу или используйте --interactive / --list-files.\n"
            "Пример: python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_report",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd_run_file(args.dialog_file, args.mode)


if __name__ == "__main__":
    main()
