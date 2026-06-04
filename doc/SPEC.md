# ovbook — Design Spec

## Overview

CLI-утилита для конвертации книг (PDF primary, fb2 fallback) в структурированное дерево .md-чанков для индексации в OpenViking.

## Архитектура — две репы

| Репа | Видимость | Назначение |
|------|-----------|------------|
| `kabal375/ovbook` | public | CLI-утилита |
| `kabal375/ov-lib` | private | Хранилище .md-чанков + OpenViking watch |

`ov-lib/` структура:

```
tech-lib/
  <book-slug>/               ← slug по английскому названию
    00-book.md                ← карточка книги (YAML frontmatter)
    01-<chapter-slug>/
      01-<section-slug>.md
    02-<chapter-slug>/
      ...
```

Без прослойки автора — авторы только в frontmatter.

## ovbook — pipeline

```
PDF → extract text (PyMuPDF) → heading detection (font size) → markdown
→ split by H2+ headings → add YAML frontmatter → write tree to ov-lib/
```

## Ключевые решения (brainstorming)

1. Исходники не хранятся, удаляются после конвертации
2. Личные заметки (`notes.md`) вне scope MVP
3. Первый формат — PDF (PyMuPDF, заголовки по font size)
4. Язык — Python 3.11+, uv + typer
5. Индексация — OpenViking watch (15 мин) на `~/ov-lib/tech-lib/`

## Chunking rules

- По естественной структуре (главы → секции)
- 700-1200 токенов на чанк
- Заголовок главы в тексте чанка
- Один чанк = одна секция или группа параграфов

## Что не входит в MVP

- Личные заметки к книге
- Non-fiction / художественная литература
- LLM-классификация
- Kindle/Readwise импорт
- Web UI

## Definition of Done

- [x] `ovbook convert` работает для PDF
- [x] Дерево чанков пишется в `tech-lib/<book>/`
- [x] OpenViking индексирует через watch
- [ ] 3-5 реальных поисковых запросов работают
- [x] Обе репы созданы на GitHub

## Принятые решения

1. **Тип репозитория:** public (ovbook) + private (ov-lib)
2. **Структура хранилища:** без прослойки автора, slug по книге
3. **Исходники:** не хранятся
4. **Личные заметки:** вне scope MVP
5. **Формат CLI:** Python/uv + typer
6. **Автоиндексация:** OpenViking watch + add-resource
