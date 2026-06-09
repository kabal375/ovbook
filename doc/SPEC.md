# ovbook — Design Spec (MVP)

## Overview

CLI-утилита для конвертации книг (PDF primary) в структурированное дерево `.md`-чанков для индексации в OpenViking.

## Архитектура — две репы

| Репа | Видимость | Назначение |
|------|-----------|------------|
| `kabal375/ovbook` | public | CLI-утилита |
| `kabal375/ov-lib` | private | Хранилище .md-чанков + OpenViking watch |

## Структура хранилища

```
ov-lib/
  vocabulary.yaml                        ← controlled vocabulary (домены по коллекциям)
  tech-lib/                              ← коллекция (тип литературы)
    <book-slug>/                         ← slug по названию книги
      00-book.md                         ← карточка книги (YAML frontmatter)
      01-<chapter-slug>.md               ← одна глава = один файл
      02-<chapter-slug>.md               ← подсекции встроены как ##/### внутри
      ...
```

Плоско: **одна глава = один `.md`-файл**, подсекции — `##`/`###` внутри файла
главы (нет папок глав, нет прослойки автора — автор только в frontmatter,
книга может иметь нескольких авторов).

### Frontmatter книги (00-book.md)

Канонический набор полей (`schema.BOOK_FIELDS`), дефолты подставляются
детерминированно:

```yaml
---
id: cloud-native-devops-with-kubernetes   # голый слаг названия
title: Cloud Native DevOps with Kubernetes
authors:
  - Justin Domingus
  - John Arundel
domains:                                   # из --domain, валидированы по словарю
  - devops-sre
topics:                                    # из --topic, нормализованы в kebab-case
  - kubernetes
  - containers
book_type: technical
source_format: epub
language: en
year: 2019
edition:
status: unread
priority: high
---
```

### Frontmatter чанка (файл главы)

```yaml
---
book_id: cloud-native-devops-with-kubernetes
chapter_no: 1
chapter_title: Revolution in the Cloud
sequence: 1
---
```

## Pipeline

```
PDF → PyMuPDF extract → font-size heading detection (H1/H2/H3)
→ split by H2+ headings → chunk frontmatter → write tree
```

### Heading detection

- Определение body font size: наиболее частый размер на первых страницах
- H1: ≥ 2.0× body size
- H2: ≥ 1.6× body size
- H3: ≥ 1.3× body size
- Всё остальное — body text

### Slug

- Из названия книги (метаданные источника)
- `re.sub(r"[^0-9a-zа-я]+", "-", title.lower()).strip("-")` (кириллица поддержана)
- ID в frontmatter книги — тот же slug

## Classification & controlled vocabulary

Реальная запись требует валидной классификации: ≥1 `--domain` из **закрытого
списка** доменов коллекции. Список — данные в ov-lib (`vocabulary.yaml` в корне
репо), не вшит в код. ovbook ищет его, поднимаясь вверх от `--output`.

```yaml
# ov-lib/vocabulary.yaml
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

Реализация — `schema.py`:

| Функция | Поведение |
|---------|-----------|
| `load_vocabulary(start, collection)` | поиск `vocabulary.yaml` вверх; нет файла/коллекции → `SchemaError` |
| `validate_domains(domains, vocab)` | пусто или домен ∉ словаря → `SchemaError` + список |
| `normalize_topics(topics)` | kebab-case, кириллица ок, формат-only (не блокирует) |
| `normalize_book_meta(raw, …)` | reader-dict → канон `BOOK_FIELDS` + дефолты |

**Hard-fail** только: (1) пустые домены при записи, (2) домен вне словаря,
(3) нет `vocabulary.yaml`. Новый домен — только правкой `vocabulary.yaml` по
запросу (агент не придумывает: останавливается и спрашивает человека).
Топики открыты — агент предлагает из содержания книги.

`--dry-run` — режим исследования: классификация не требуется, но переданный
домен всё равно валидируется.

### Авторы (PDF)

- Разделитель `;` (точка с запятой)
- Формат `Last,First` → разворачивается в `First Last`

## CLI

```bash
uv run ovbook convert <input> -o <output-dir> --domain <d> [--topic <t> ...]
uv run ovbook convert <input> --dry-run                 # показать структуру (без классификации)
```

Опции: `--domain` (обязателен для записи, можно повторять), `--topic`
(повторяемый, нормализуется), `--edition`, `--collection` (по умолч. — имя
выходной директории), `--format`, `--dry-run`.

Форматы: **pdf / fb2 / epub** (detect из расширения).

## Технологии

- Python 3.11+, uv
- Typer (CLI)
- PyMuPDF / fitz (PDF)
- stdlib ElementTree (fb2)
- ebooklib + markdownify + beautifulsoup4 (epub)
- pyyaml (чтение vocabulary.yaml)
- pytest (тесты, 139 шт.)

## OpenViking

- Watch на `~/ov-lib/tech-lib/`, 15 мин
- `ov add-resource <local_path> --to <uri> --watch-interval N`
- Без `--include` — ресурс индексирует все `.md` на любом уровне вложенности

## Известные ограничения MVP

1. **Index/appendix** — не фильтруются (только PDF-шум: номера страниц, колонтитулы)
2. **Sequence одноуровневый** — 0..N, не иерархический (0102)
3. **Part-иерархия** — для EPUB берётся верхний уровень TOC как главы; глубокая
   вложенность → подсекции, полноценные Part'ы пока не выделяются
4. **Нет авто-детекта domains/topics** из текста — классификация через CLI-флаги
   (агент выбирает домен из словаря, предлагает топики из содержания)
5. **Нет линтера** уже залитых книг против схемы — следующая итерация (`ovbook lint`)

### История

- Iter 005 — структурные FB2/EPUB ридеры, единый `BookContent` → `write_chapter_groups`
- Iter 006 — controlled vocabulary + валидация классификации + канонический
  frontmatter (см. `ITERATION-006.md`)
