# ovbook — Iteration 002: MVP доработка

## Что меняем

### 1. Part/Chapter иерархия

**Детекция Part:**
- H1-заголовки вида "Part I", "PART ONE", "Часть первая" — детектятся как Part
- Если Part детектится — чанки группируются под Part
- Если Part нет — структура остаётся плоской (book-slug/NN-chunk/ как сейчас)

**Структура на диске (с Part):**
```
book-slug/
  00-book.md
  01-slug-part/
    01-chapter-slug.md
    02-chapter-slug.md
  02-another-part/
    01-chapter-slug.md
```

**Структура без Part:**
```
book-slug/
  00-book.md
  01-NN-chapter/
    01-NN-chapter.md
```

### 2. Метаданные книги (00-book.md)

Добавить поля:
```
domains: [cloud-native, kubernetes]
topics: [containers, orchestration, ci-cd, monitoring]
book_type: technical
source_format: pdf
language: en
year: 2022
edition: 2
```

- `year` — из PDF metadata (creationDate)
- `source_format` — из расширения файла
- `book_type` — по умолчанию "technical"
- `domains`, `topics`, `edition` — через CLI флаги (`--domain`, `--topic`, `--edition`)
- `edition` — можно попробовать детектить из текста (поиск "Second Edition", "2nd edition")

### 3. Метаданные фрагмента

Добавить поля:
```
book_id: cloud-native-devops-with-kubernetes
part: ""                   # если в Part
chapter_no: 3
chapter_title: Getting Kubernetes
section_no: 2             # если H3 внутри главы
section_title: Node Components
domains: [cloud-native]
topics: [kubernetes, architecture]
sequence: 0302
```

- `book_id` — из книги
- `chapter_no` — номер из "CHAPTER 3" / "Chapter 3"
- `section_no` — номер секции внутри главы (H3)
- `sequence` — `chapter_no * 100 + section_no` (0302)
- `domains`/`topics` — наследуются из книги, можно уточнять по Part

### 4. Фильтрация контента

Чанки делятся на зоны:

| Зона | Что входит | Решение |
|------|-----------|---------|
| Front matter | Introduction, Foreword, Preface, About the Authors, Acknowledgments, cover, TOC, "Welcome Aboard" | Пропустить |
| Основной контент | Chapters, Appendix, summaries внутри глав | Оставить |
| Index | Index (буквы A–Z со ссылками), Colophon, About the Authors (дубль), реклама O'Reilly | Пропустить |

**Детекция границ:**
- Начало контента: первый заголовок `CHAPTER \d+`, `Part \w+`, `Appendix \w+`
- Конец контента: заголовок `Index` (и всё после него)

### 5. Изменения в pipeline

```
extract → detect Part (H1 regex) → split chapters (H2) → split sections (H3)
→ filter (front matter / index) → assign sequence → enrich frontmatter → write tree
```

### 6. CLI — новые флаги

```bash
uv run ovbook convert input.pdf \
  -o ~/ov-lib/tech-lib/ \
  --domain cloud-native \
  --domain kubernetes \
  --topic containers \
  --topic orchestration \
  --edition "2nd"
```

### 6. Тесты

- Не менее 3 новых тестов на Part детекцию
- Не менее 3 на метаданные
- Существующие 52 не сломать

### 7. Что НЕ входит в эту итерацию

- Part без Part заголовка (структурная группировка)
- Авто-детект edition по тексту (пока только флаг)
- topics из текста книги
- Index/appendix фильтрация

### 8. Порядок работ

1. Part/Chapter детекция в extract.py
2. Иерархическое дерево в writer.py
3. Sequence в формате NNNN
4. Фильтрация (front matter, index)
5. Метаданные книги + CLI флаги
6. Метаданные фрагмента
7. Тесты
8. Конвертация книги → проверка → пуш
