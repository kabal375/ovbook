# ovbook — Iteration 005: Structural FB2 & EPUB Readers

## Контекст и мотивация

PDF-пайплайн вынужден угадывать структуру по размеру шрифта (scoring,
drawing/TOC/index guards) — отсюда мусорные главы ("chapter-11-x", даты в
заголовках на FCP-4). FB2 и EPUB несут **явную структурную разметку** (XML/HTML
с секциями, заголовками, TOC), поэтому для них угадывать не нужно — главы
строятся напрямую из разметки. Эти форматы должны давать заметно более чистый
результат.

**Решение по итерации 004** уже унифицировало вывод: одна глава = один `.md`,
подсекции как `##`/`###` внутри, через `write_chapter_groups`. Эта итерация
делает FB2 и EPUB первоклассными источниками для того же вывода.

## Цель

- Структурный ридер FB2 (переписать существующий примитивный путь)
- Новый ридер EPUB
- Единый формат вывода для всех трёх форматов (PDF/FB2/EPUB → `list[ChapterGroup]`
  → `write_chapter_groups`)
- Границы глав: **структура первична** (верхнеуровневая секция FB2 / запись TOC
  верхнего уровня EPUB = глава), заголовки `<h2>`/`<h3>` / вложенные секции →
  подсекции (решение пользователя, вариант A)

## Архитектура

### Новый пакет `readers/`

Логика форматов сейчас размазана (`extract.py` содержит и PDF, и FB2; routing в
`cli.py`). Выделяем изолированный пакет, где каждый формат — модуль с единым
интерфейсом.

```
src/ovbook/
  readers/
    __init__.py      # реестр расширение → функция read
    base.py          # BookContent dataclass: (meta: dict, groups: list[ChapterGroup])
    pdf.py           # обёртка над текущим pipeline (profile→extract_rich→filter→group)
    fb2.py           # НОВЫЙ структурный
    epub.py          # НОВЫЙ структурный
  extract.py         # остаётся: extract_pdf_rich, get_pdf_metadata (используется readers/pdf)
  profile.py         # остаётся: detect_profile (используется readers/pdf)
  split.py           # Chunk, ChapterGroup — без изменений
  writer.py          # write_chapter_groups для всех форматов (+ фикс уровня заголовков)
  cli.py             # format-agnostic
```

### Единый интерфейс ридера

```python
# readers/base.py
from dataclasses import dataclass
from ovbook.split import ChapterGroup

@dataclass
class BookContent:
    meta: dict                    # book frontmatter (id, title, authors, language, ...)
    groups: list[ChapterGroup]    # главы, готовые для write_chapter_groups

# каждый ридер:
def read(path: Path) -> BookContent: ...
```

```python
# readers/__init__.py
from ovbook.readers import pdf, fb2, epub

_REGISTRY = {
    "pdf": pdf.read,
    "fb2": fb2.read,
    "epub": epub.read,
}

def get_reader(fmt: str):
    reader = _REGISTRY.get(fmt)
    if reader is None:
        raise ValueError(f"Unsupported format: {fmt} (supported: {', '.join(_REGISTRY)})")
    return reader
```

### cli.py становится format-agnostic

```python
fmt = format or input.suffix.lstrip(".").lower()
reader = get_reader(fmt)              # ValueError → typer.Exit(1)
content = reader(input)              # BookContent
# merge --domain/--topic/--edition в content.meta
# dry_run → печать
slug = make_slug(content.meta.get("title", input.stem))
write_chapter_groups(output, content.groups, content.meta, slug)
```

Routing PDF-vs-FB2 в CLI исчезает — все идут через `write_chapter_groups`.
`write_chunks` (старый FB2 per-file путь) **удаляется** вместе с тестами
`test_writer_hierarchy.py` и затронутыми частями `test_writer.py`.

## Поток данных

### FB2 (`readers/fb2.py`)

Парсинг через stdlib `xml.etree.ElementTree` (уже используется, новых зависимостей нет).

```
parse XML
→ <description>/<title-info> → meta (book-title, authors, lang, year, genre)
→ <body> → верхнеуровневые <section>:
     каждая = ChapterGroup
       chapter chunk: <title> секции (level=1), content = прямой текст до вложенных секций
       вложенные <section> → Chunk(level=2/3) с <title> как heading
→ инлайн-разметка → markdown:
     <p> → абзац, <empty-line> → пустая строка
     <emphasis> → *курсив*, <strong> → **жирный**, <code> → `код`
     <poem>/<stanza>/<v> → строки, <cite> → блок-цитата
     списки (FB2 не имеет нативных <ul>; пропускаем — редки в техкнигах)
```

Главы без `<title>` → fallback на "Chapter N" (нумерация по порядку).

### EPUB (`readers/epub.py`)

Контейнер через `ebooklib`, HTML-тело через `markdownify`.

```
ebooklib.epub.read_epub(path)
→ metadata (DC: title, creator[], language, date) → meta
→ TOC (book.toc) — верхнеуровневые записи = границы глав
→ spine (порядок чтения) — сопоставляем TOC-якоря с документами
→ для каждой главы:
     собрать XHTML-фрагмент(ы) между якорями
     markdownify(html) → markdown тело
     <h1> внутри → заголовок главы (если TOC-метка пустая)
     <h2>/<h3> → подсекции → Chunk(level=2/3)
→ ChapterGroup на главу
```

Граничные случаи EPUB:
- TOC отсутствует (редко) → fallback: каждый spine-документ = глава
- Якорь главы указывает в середину файла → режем по `id` атрибутам
- Front matter (cover, copyright, dedication) в spine, но не в TOC → пропускаем
  (нет TOC-записи = не глава)

### markdownify-конфиг

```python
markdownify(html,
    heading_style="ATX",        # ## вместо подчёркивания
    bullets="-",
    code_language="",           # сохранить <pre><code> как ``` блоки
    strip=["img"],              # картинки не индексируем
)
```

Важно для техкниг: `<pre><code>`, `<ul>/<ol>`, `<table>` сохраняются — это ядро
ценности для RAG.

## Доработка writer.py

`_write_chapter_file` сейчас всегда ставит `##` для всех `group.chunks[1:]`.
Меняем на уровень из чанка:

```python
for chunk in group.chunks[1:]:
    prefix = "#" * min(chunk.level, 6)   # level=2 → ##, level=3 → ###
    ...
```

Иначе вложенность секций FB2/EPUB схлопнется в один уровень.

## Зависимости

Добавляются в `pyproject.toml`:
```
ebooklib>=0.18      # EPUB-контейнер (zip/OPF/spine/TOC); тянет lxml (уже есть)
markdownify>=0.13   # HTML → markdown с сохранением кода/списков/таблиц
```

FB2 новых зависимостей не требует (stdlib ElementTree).

## Тестирование

Синтетические фикстуры по образцу существующего PDF-генератора в `conftest.py`:

### `tests/conftest.py` — новые фикстуры
- `fb2_fixture`: минимальный FB2 (ElementTree.tostring) с 2 главами, вложенной
  секцией, инлайн-разметкой (emphasis/strong/code)
- `epub_fixture`: минимальный EPUB (ebooklib.epub.write_epub) с TOC, 2 главами,
  `<h2>` подсекцией, блоком кода, списком

### `tests/test_readers_fb2.py`
- главы из верхнеуровневых секций
- вложенная секция → Chunk(level=2)
- инлайн emphasis/strong/code → markdown
- метаданные (title, authors, lang, year)
- глава без `<title>` → "Chapter N"
- полный путь через BookContent → write_chapter_groups

### `tests/test_readers_epub.py`
- главы из TOC верхнего уровня
- `<h2>` → подсекция level=2
- `<pre><code>` сохранён как ``` блок
- `<ul>` сохранён
- front matter (cover/copyright не в TOC) пропущен
- метаданные из DC
- fallback при отсутствии TOC → spine-документы как главы

### `tests/test_readers_registry.py`
- расширение → правильный reader
- неизвестный формат → ValueError

### `tests/test_cli.py` — дополнить
- `convert book.fb2` → структура `NN-chapter.md` + book_id
- `convert book.epub` → то же
- dry-run для обоих

### Совместимость
- Существующие PDF-тесты — зелёные (readers/pdf.py оборачивает текущую логику)
- `test_writer_hierarchy.py` — **удаляется** (тестировал удаляемый write_chunks)
- `test_writer.py` — блоки про write_chunks удаляются; тесты
  `_resolve_chapter_title` и `_slugify` остаются
- `test_metadata.py::test_domains_propagate_to_chunks` — переписать под новый путь

## Что НЕ входит

- MOBI/AZW (Kindle) — отдельная итерация при необходимости
- Картинки/диаграммы из EPUB (strip=["img"])
- OCR
- Part-иерархия для EPUB (TOC может быть многоуровневым — пока берём верхний
  уровень как главы, более глубокая вложенность → подсекции; полноценные Part'ы
  при необходимости позже)
- Авто-детект domains/topics из текста (по-прежнему только CLI-флаги)

## Порядок работ

1. `readers/base.py` — BookContent dataclass
2. `readers/__init__.py` — реестр + get_reader
3. `readers/pdf.py` — обёртка над текущим pipeline (рефакторинг из cli.py)
4. writer.py — фикс уровня заголовков подсекций
5. `readers/fb2.py` — структурный FB2 + инлайн-markdown
6. `readers/epub.py` — EPUB через ebooklib + markdownify
7. cli.py — format-agnostic routing; удалить write_chunks-ветку
8. Удалить write_chunks из writer.py + связанные тесты
9. Фикстуры FB2/EPUB в conftest.py
10. Тесты ридеров + реестра + CLI
11. pyproject.toml — ebooklib, markdownify
12. Конвертация реальной FB2 и EPUB книги → проверка → пуш
```
