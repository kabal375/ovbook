# ovbook — Iteration 003: Scored Heading Detector + Depth Guard + Document Profile

## Что меняем

### 1. Scoring pipeline вместо font-size threshold

Заменяем наивное `if max_size >= body_size * 1.3 → H2` на `score_heading(c, body_size)` с positive/negative signals:

- **Positive**: chapter keyword (+6), numbered heading (+5), font ≥ 1.18× body (+3), bold (+2)
- **Negative**: <4 chars (-5), TOC dots (-8), near drawing (-6), index letter (-8), non-letter-only (-10)

### 2. Depth guard — subsections внутри chapter файлов

**Не каждый heading = отдельный файл.** Двухуровневая модель:

```
book-slug/
  00-book.md
  01-chapter-1-introduction.md    ← Chapter 1: вступление + все ##/### внутри
  02-chapter-2-smr-hdd.md         ← Chapter 2: SMR + все подсекции
  ...
```

Section-level (1.1, 1.2, Figure 5-8, Table 2-4) → `##`/`###` Markdown внутри chapter файла.

### 3. Drawing guard — отсечь диаграммный шум

PyMuPDF: `page.cluster_drawings()` — кластеризует векторную графику.
Если bbox текстового блока рядом с drawing cluster → `near_drawing = True` → score -6.

### 4. TOC guard — не путать TOC entries с content

Строки с leader dots (`.............1`) и хвостовым page number → `looks_like_toc_entry = True` → score -10 → фильтрация.

### 5. Index guard — алфавитные секции не главы

Single uppercase letter (`A`, `B`, `C`, `W, X`) после Index → фильтр.

### 6. Document profile

Перед экстракцией — `detect_profile(path)` определяет:
- `type`: born-digital / diagram-heavy / cjk-broken
- `body_size`: медианный font-size
- `encoding_ok`: проверка mojibake
- `drawing_count`: количество drawing clusters

### 7. Rich Chunk — метаданные для scoring

```python
@dataclass
class Chunk:
    ...
    font_size: float = 0.0
    is_bold: bool = False
    near_drawing: bool = False
    looks_like_toc_entry: bool = False
    looks_like_index_letter: bool = False
    page_type: str = "body"
    score: float = 0.0
```

## Pipeline (новый)

```
PDF → detect_profile → extract_pdf (rich blocks)
→ score_heading(c, body_size) на каждом
→ filter_toc_chunks
→ filter_low_score (diagram guard)
→ group_chunks_by_chapter (depth guard)
→ write_chapter_groups (subsections inside)
```

## CLI — без изменений

Флаги и интерфейс те же. Изменения только внутри.

## Тесты

- Все существующие 75 тестов зелёные
- + тест на score_heading() (5 кейсов)
- + тест на group_chunks_by_chapter()
- + тест на filter_toc_chunks()
- + тест на detect_profile()

## Порядок работ

1. Chunk — новые поля (font_size, is_bold, score, ...)
2. score_heading() — core scoring function
3. extract_pdf — rich blocks вместо markdown
4. Drawing guard — cluster_drawings + near_drawing
5. TOC guard — filter_toc_chunks
6. Depth guard — group_chunks_by_chapter + writer
7. Document profile — detect_profile()
8. Интеграция — cli.py pipeline
9. Тест на реальном PDF

## Что НЕ входит

- Авто-детект edition по тексту
- OCR pipeline (tesseract) — только mojibake detection
- FB2 обновления
- Part-иерархия (остаётся как в ITERATION-002)
