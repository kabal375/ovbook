# ovbook — Iteration 006: Controlled-vocabulary classification + schema enforcement

## Контекст и мотивация

Агент-конвертер мог молча залить книгу с тремя дефектами сразу:

1. **забыл `--domain`/`--topic`** — `convert` тихо писал книгу без классификации;
2. **придумал домен** — controlled vocabulary не было, любой `--domain` проходил;
3. **метадата не по MVP** — readers отдавали свободный dict, поля расходились со
   спекой (`author` vs `authors`, нет `status`/`priority`/`book_type` и т.д.).

Все три — симптомы одного: **контракт метаданных нигде не был закодирован и не
проверялся.** Конвертер принимал что угодно (или ничего) и молча писал результат.

## Цель

Вынести контракт из головы агента в код, нарушения сделать громкими.

- *Форму* метаданных (какие поля у книги) закодировать в ovbook.
- *Значения* доменов (что легально) вынести как данные в ov-lib — пополняемо,
  с разными наборами под разные типы книг.
- При записи — hard-fail на пустые/неизвестные домены, чтобы агент не мог
  проскочить молча.

## Разделение ответственности

| Что | Где | Почему |
|-----|-----|--------|
| форма карточки (поля) | код, `schema.py` (`BOOK_FIELDS`) | структурно, меняется редко |
| легальные домены | данные, `ov-lib/vocabulary.yaml` | пополняемо, своё на каждую коллекцию |

ovbook остаётся generic: он не знает про «7 доменов техлита», он умеет читать
словарь и валидировать против него.

## Архитектура

### Новый модуль `schema.py`

```
src/ovbook/schema.py
  BOOK_FIELDS            # канонический порядок полей 00-book.md (форма)
  Vocabulary             # collection, domains(frozenset), topics_registry
  SchemaError
  load_vocabulary(start, collection)   # поиск vocabulary.yaml вверх от --output
  validate_domains(domains, vocab)     # закрытый список → hard-fail
  normalize_topics(topics)             # kebab-case, кириллица ок, формат-only
  normalize_book_meta(raw, *, domains, topics)  # reader-dict → канон MVP
```

### vocabulary.yaml (в ov-lib, корень репо)

```yaml
collections:
  tech-lib:
    domains:                # ЗАКРЫТЫЙ список
      - software-development
      - operating-systems
      - networks-protocols
      - requirements-management
      - devops-sre
      - tools-applications
      - hardware-systems
    topics_registry: []     # открытый, накопительный (резерв под будущий линтер)
```

`load_vocabulary` поднимается вверх от `--output` (типично `~/ov-lib/tech-lib/`
→ `~/ov-lib/vocabulary.yaml`). Коллекция выводится из листа пути, переопределяется
`--collection`.

### cli.py — валидация на границе

```
content = reader(input)
topics = normalize_topics(--topic)
coll   = --collection or output.name

if dry_run:
    if --domain: load_vocabulary → validate_domains   # ошибка → Exit(1)
    print; return                                      # классификация не обязательна

# real write:
vocab = load_vocabulary(output, coll)                  # нет файла → Exit(1)
validate_domains(--domain, vocab)                      # пусто/неизвестно → Exit(1)
meta = normalize_book_meta(content.meta, domains=--domain, topics=topics)
write_chapter_groups(...)
```

## Точные ограничения

Hard-fail только три случая:

1. `domains` пуст при записи → ошибка (убивает «забыл флаг»);
2. домен ∉ словаря коллекции → ошибка + печать разрешённого списка (убивает
   «придумал домен»);
3. нет `vocabulary.yaml` → ошибка (нечем валидировать).

Всё остальное — мягко: пустые топики → warn; формат топика → авто-нормализация.

`--dry-run` = режим исследования: классификация не требуется (можно посмотреть
структуру до выбора доменов), но переданный домен всё равно валидируется.

## Домены vs топики — разная строгость намеренно

- **домены закрыты** — агент выбирает из списка, не придумывает. Нужен новый
  домен → агент останавливается и спрашивает человека; домен добавляется только
  правкой `vocabulary.yaml`. В перспективе — классификаторы по доменам, поэтому
  в поле не должно быть случайных сущностей.
- **топики открыты** — агент предлагает 2–4 из содержания книги; валидируется
  только формат (kebab-case). Жёсткий список убил бы гранулярность.

## Канонический frontmatter книги

`normalize_book_meta` приводит loose-dict любого reader к канону с дефолтами:

```yaml
id: <bare-slug>          # слаг названия, без префикса tech-book-
title:
authors: []
domains: []              # из --domain (валидированы)
topics: []               # из --topic (нормализованы)
book_type: technical
source_format:
language: en
year:
edition:
status: unread
priority: high
```

## Зависимости

Добавляется в `pyproject.toml`:
```
pyyaml>=6.0     # чтение vocabulary.yaml (только чтение; запись frontmatter — по-прежнему вручную)
```

## Тестирование

- `tests/test_schema.py` (16 новых): normalize_topics (формат/кириллица/пустые),
  validate_domains (валидный/пустой/неизвестный+список), load_vocabulary
  (walk-up/нет файла/нет коллекции), normalize_book_meta (инъекция доменов,
  дефолты status/priority/book_type, сохранение reader-полей, голый слаг id,
  полнота контракта).
- `tests/conftest.py`: фикстура `tech_lib` (vocabulary.yaml + output-папка).
- Обновлены под новый контракт: `test_cli.py` (+5 enforcement-кейсов),
  `test_metadata.py`, `test_integration.py` — теперь передают `--domain` и пишут
  в `tech_lib`.
- Итог: **139 passed** (было 118).

## Что НЕ входит

- Авто-запись новых топиков в `topics_registry` (convert остаётся read-only к
  словарю — без git-шума; накопление уйдёт будущему линтеру).
- Линтер `ovbook lint` для проверки уже залитых книг против схемы (следующая
  итерация).
- Авто-детект domains/topics из текста LLM-ом (по-прежнему агент/CLI-флаги).
- Эскалация нового домена через файл-очередь (агент просто останавливается и
  спрашивает человека).

## Порядок работ

1. `schema.py` — TDD: normalize_topics → validate_domains → load_vocabulary →
   normalize_book_meta
2. `pyproject.toml` — pyyaml
3. `cli.py` — валидация при записи; `--collection`; dry-run как exploration
4. `conftest.py` — фикстура `tech_lib`
5. Обновить CLI/metadata/integration тесты под новый контракт
6. `vocabulary.yaml` в ov-lib (master)
7. README + SPEC обновить
8. Smoke-тест 4 сценариев → пуш → PR
