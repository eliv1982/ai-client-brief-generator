"""AI Client Brief Generator — entry point.

Usage examples:
    python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_report
    python main.py input_dialogs/my_dialog.txt --mode client_report
    python main.py --list-files
    python main.py --interactive

    # client_brief is kept as a backward-compatible alias for client_report
    python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_brief
"""
from __future__ import annotations

import argparse
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

# Canonical mode name → alias(es)
SUPPORTED_MODES = ("client_report", "client_brief")
_CANONICAL_MODE = "client_report"
_MODE_ALIASES: dict[str, str] = {"client_brief": "client_report"}

_MODE_DISPLAY = {
    "client_report": "Отчет по клиентскому запросу",
}

SCAN_DIRS = ("example_dialogs", "input_dialogs")


def _canonical(mode: str) -> str:
    """Resolve alias to canonical mode name."""
    return _MODE_ALIASES.get(mode, mode)


# ── File discovery ─────────────────────────────────────────────────────────────

def find_txt_files() -> list[Path]:
    """Return all .txt files in SCAN_DIRS, sorted by directory then name."""
    found: list[Path] = []
    for dir_name in SCAN_DIRS:
        directory = Path(dir_name)
        if directory.is_dir():
            found.extend(sorted(directory.glob("*.txt")))
    return found


def _file_preview(path: Path) -> str:
    """Return a short one-line preview of the file (first non-empty line)."""
    try:
        text = path.read_text(encoding="utf-8-sig").strip()
        first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        if len(first_line) > 72:
            first_line = first_line[:69] + "..."
        return first_line
    except Exception:
        return ""


def print_file_list(files: list[Path]) -> None:
    """Print a numbered list of files with size and preview."""
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
    """Read *path* as UTF-8 text (BOM-aware). Exits on error."""
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


# ── Report generation ──────────────────────────────────────────────────────────

def run_client_report(dialog_path: Path) -> None:
    """Full pipeline: read file -> OpenAI -> validate -> PDF -> print path."""
    from utils.ai_processor import extract_brief_from_dialog
    from utils.pdf_generator import render_client_brief_pdf
    from utils.validators import BriefValidationError

    logger.info("Чтение файла диалога: %s", dialog_path)
    dialog_text = read_dialog_file(dialog_path)

    try:
        brief_data = extract_brief_from_dialog(dialog_text)
    except EnvironmentError as exc:
        logger.error("Environment error: %s", exc)
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    except BriefValidationError as exc:
        logger.error("Некорректный ответ от OpenAI:\n%s", exc)
        print(
            f"\n[ERROR] OpenAI вернул некорректный или неполный ответ:\n{exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        logger.error("Ошибка при обращении к OpenAI: %s", exc, exc_info=True)
        print(f"\n[ERROR] Ошибка при обращении к OpenAI: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        pdf_path = render_client_brief_pdf(brief_data)
    except FileNotFoundError as exc:
        logger.error("Шаблон не найден: %s", exc)
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as exc:
        logger.error("PermissionError при сохранении PDF: %s", exc)
        print(
            "\n[ERROR] Не удалось сохранить PDF. "
            "Возможно, файл с таким именем уже открыт. "
            "Закройте PDF и повторите попытку.",
            file=sys.stderr,
        )
        sys.exit(1)
    except RuntimeError as exc:
        logger.error("Ошибка генерации PDF: %s", exc)
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logger.error("Неожиданная ошибка при генерации PDF: %s", exc, exc_info=True)
        print(f"\n[ERROR] Неожиданная ошибка при генерации PDF: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[OK] Отчет успешно сформирован!\n  -> {pdf_path.resolve()}\n")


# ── CLI modes ──────────────────────────────────────────────────────────────────

def cmd_list_files() -> None:
    """--list-files: show available .txt files without generating anything."""
    files = find_txt_files()
    print_file_list(files)


def cmd_interactive(mode: str) -> None:
    """--interactive: let the user pick a file from the discovered list."""
    canonical = _canonical(mode)
    files = find_txt_files()
    if not files:
        print_file_list(files)
        sys.exit(0)

    print_file_list(files)
    while True:
        raw = input("Введите номер файла: ").strip()
        if not raw.isdigit():
            print("  Введите число от 1 до " + str(len(files)) + ".")
            continue
        idx = int(raw)
        if not (1 <= idx <= len(files)):
            print(f"  Номер должен быть от 1 до {len(files)}.")
            continue
        break

    chosen = files[idx - 1]
    display_mode = _MODE_DISPLAY.get(canonical, canonical)
    print(f"\nВыбран файл: {chosen}")
    print(f"Тип отчета: {display_mode}\n")
    logger.info("Interactive: выбран '%s', режим=%s", chosen, canonical)

    if canonical == "client_report":
        run_client_report(chosen)
    else:
        print(f"[ERROR] Режим '{canonical}' еще не реализован.", file=sys.stderr)
        sys.exit(1)


def cmd_run_file(dialog_path: Path, mode: str) -> None:
    """Direct file path mode."""
    canonical = _canonical(mode)
    display_mode = _MODE_DISPLAY.get(canonical, canonical)
    logger.info("Тип отчета: %s | Файл: %s", display_mode, dialog_path)

    if canonical == "client_report":
        run_client_report(dialog_path)
    else:
        print(f"[ERROR] Режим '{canonical}' еще не реализован.", file=sys.stderr)
        sys.exit(1)


# ── Argument parsing ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "AI Client Brief Generator\n"
            "Преобразует транскрибацию клиентского диалога в PDF-отчет.\n\n"
            "Примеры:\n"
            "  python main.py example_dialogs/ai_bot_client_dialog.txt --mode client_report\n"
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
        default=_CANONICAL_MODE,
        help=(
            "Тип отчета (по умолчанию: client_report). "
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
        help="Интерактивный выбор файла из списка.",
    )
    return parser.parse_args()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

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
