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
tech-lib/
  <book-slug>/               ← slug по английскому названию
    00-book.md                ← карточка книги (YAML frontmatter)
    NN-<chunk-slug>/
      NN-<chunk-slug>.md      ← чанк с YAML frontmatter
    ...
```

Авторы только в frontmatter — прослойки автора нет.

### Frontmatter книги (00-book.md)

```yaml
---
id: cloud-native-devops-with-kubernetes
title: Cloud Native DevOps with Kubernetes
authors:
  - Justin Domingus
  - John Arundel
language: en
---
```

### Frontmatter чанка

```yaml
---
heading: CHAPTER 1
level: 2
sequence: 11
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

- Из названия книги (PDF metadata title)
- `re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")`
- ID в frontmatter книги — тот же slug

### Авторы (PDF)

- Разделитель `;` (точка с запятой)
- Формат `Last,First` → разворачивается в `First Last`

## CLI

```bash
uv run ovbook convert <input.pdf> -o <output-dir>
uv run ovbook convert <input.pdf> --dry-run   # только показать структуру
```

Форматы: pdf, fb2 (detect из расширения).

## Технологии

- Python 3.11+, uv
- Typer (CLI)
- PyMuPDF / fitz (PDF)
- lxml (fb2)
- pytest (тесты, 52 шт.)

## OpenViking

- Watch на `~/ov-lib/tech-lib/`, 15 мин
- `ov add-resource <local_path> --to <uri> --watch-interval N`
- Без `--include` — ресурс индексирует все `.md` на любом уровне вложенности

## Известные ограничения MVP

1. **Нет части/главы/секции** — плоская разбивка по H2+ заголовкам
2. **Нет доменов/топиков** — только базовые метаданные (title, authors, language)
3. **Нет распознавания Part** — заголовки уровня Part не детектятся как отдельный уровень
4. **Index/appendix** — не фильтруются
5. **Нет year/edition/source_format** — не извлекаются из PDF metadata
6. **Sequence одноуровневый** — 0..N, не иерархический (0102)
