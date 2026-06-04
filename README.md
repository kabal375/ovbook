# ovbook

CLI-инструмент для конвертации книг (PDF primary) в структурированное дерево `.md`-чанков, готовое для автоиндексации через OpenViking.

## Usage

```bash
uv run ovbook convert book.pdf -o ~/ov-lib/tech-lib/
```

Опции:
- `--dry-run` — только показать, что будет создано, без записи
- `-o, --output` — директория для результата (по умолч. `~/ov-lib/tech-lib/`)

## Output structure

```
tech-lib/
├── <book-slug>/
│   ├── 00-book.md          # метаданные (title, author, date)
│   ├── ch01-introduction.md
│   ├── ch02-deep-dive.md
│   └── ...
```

Каждый блок перекрёстно ссылается на соседние — навигация без потери контекста.

## Install

```bash
uv tool install .
```

## Tech

- Python 3.11+, [uv](https://github.com/astral-sh/uv), [Typer](https://typer.tiangolo.com/)
- PDF: [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) — font-size based heading detection
- Tests: `uv run pytest` — 52 тестов
