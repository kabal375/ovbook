# ovbook

CLI-инструмент для конвертации книг (PDF / FB2 / EPUB) в структурированное дерево `.md`-чанков, готовое для автоиндексации через OpenViking.

## Usage

```bash
uv run ovbook convert book.pdf  -o ~/ov-lib/tech-lib/
uv run ovbook convert book.fb2  -o ~/ov-lib/tech-lib/
uv run ovbook convert book.epub -o ~/ov-lib/tech-lib/
```

Поддерживаемые форматы: **pdf** (детекция структуры по размеру шрифта),
**fb2** и **epub** (структурный парсинг разметки — точнее, чем PDF).

Опции:
- `--dry-run` — только показать, что будет создано, без записи
- `-o, --output` — директория для результата (по умолч. текущая)
- `-f, --format` — явно задать формат (по умолч. — по расширению)
- `--domain` / `--topic` — теги книги (можно повторять)
- `--edition` — издание (напр. `2nd`)

## Output structure

Одна глава = один файл. Подсекции встроены как `##`/`###` внутри файла главы.

```
tech-lib/
├── <book-slug>/
│   ├── 00-book.md                       # метаданные (title, authors, year, domains…)
│   ├── 01-<chapter-title-slug>.md       # глава 1 целиком, подсекции как ##
│   ├── 02-<chapter-title-slug>.md
│   └── ...
```

Каждый файл главы содержит `book_id` во frontmatter — связь чанка с книгой.

## Install

```bash
uv tool install .
```

## Tech

- Python 3.11+, [uv](https://github.com/astral-sh/uv), [Typer](https://typer.tiangolo.com/)
- PDF: [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) — heading detection через scoring по размеру шрифта
- FB2: stdlib ElementTree — структурный парсинг `<section>`/`<title>`
- EPUB: [ebooklib](https://github.com/aerkalov/ebooklib) + [markdownify](https://github.com/matthewwithanm/python-markdownify) — TOC/spine + HTML→markdown с сохранением кода, списков, таблиц
- Архитектура: пакет `readers/` — каждый формат отдаёт единый `BookContent` → общий writer
- Tests: `uv run pytest`
