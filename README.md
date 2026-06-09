# ovbook

CLI-инструмент для конвертации книг (PDF / FB2 / EPUB) в структурированное дерево `.md`-чанков, готовое для автоиндексации через OpenViking.

## Usage

```bash
uv run ovbook convert book.pdf  -o ~/ov-lib/tech-lib/ --domain operating-systems --topic scheduling
uv run ovbook convert book.fb2  -o ~/ov-lib/tech-lib/ --domain software-development
uv run ovbook convert book.epub -o ~/ov-lib/tech-lib/ --domain devops-sre
```

Поддерживаемые форматы: **pdf** (детекция структуры по размеру шрифта),
**fb2** и **epub** (структурный парсинг разметки — точнее, чем PDF).

Опции:
- `--dry-run` — только показать, что будет создано, без записи (режим исследования: классификация не требуется)
- `-o, --output` — директория для результата (по умолч. текущая)
- `-f, --format` — явно задать формат (по умолч. — по расширению)
- `--domain` — домен книги из словаря коллекции, можно повторять (**обязателен** для записи)
- `--topic` — тема книги, можно повторять (свободная форма, нормализуется в kebab-case)
- `--edition` — издание (напр. `2nd`)
- `--collection` — коллекция словаря (по умолч. — имя выходной директории, напр. `tech-lib`)

## Классификация и controlled vocabulary

Реальная запись **требует** валидной классификации: хотя бы один `--domain` из
закрытого списка доменов коллекции. Список живёт как данные в ov-lib —
`vocabulary.yaml` в корне репозитория, рядом с книгами:

```yaml
collections:
  tech-lib:
    domains:
      - software-development
      - operating-systems
      - networks-protocols
      - requirements-management
      - devops-sre
      - tools-applications
      - hardware-systems
    topics_registry: []
```

`ovbook` ищет `vocabulary.yaml`, поднимаясь вверх от `--output`. Правила:

- **домены закрыты** — домен вне списка → ошибка (агент не может придумать домен;
  новый домен добавляется только правкой `vocabulary.yaml` по запросу);
- пустые домены при записи → ошибка (нельзя залить книгу без классификации);
- нет `vocabulary.yaml` → ошибка (нечем валидировать);
- **топики открыты** — свободная форма, валидируется только формат (kebab-case);
- `--dry-run` — режим исследования: классификация не требуется, но переданный
  домен всё равно валидируется, чтобы поймать ошибку до записи.

Карточка `00-book.md` получает канонический frontmatter по схеме MVP
(`id, title, authors, domains, topics, book_type, source_format, language,
year, edition, status, priority`) с детерминированными значениями по умолчанию
(`status: unread`, `priority: high`, `book_type: technical`).

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
