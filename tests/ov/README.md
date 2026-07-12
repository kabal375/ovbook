# OpenViking functionality tests

Black-box smoke tests for a **running OpenViking server** (the RAG backend ovbook
feeds into). These check the live REST API — they do **not** test the ovbook
converter (see the pytest suite in `tests/` for that).

- **One test = one script** (`test_*.sh`). Each is standalone: exit `0` PASS, `1` FAIL, `2` SKIP.
- **One runner** (`run.sh`) executes a named set.

## Run

```bash
cd tests/ov
./run.sh            # full  — every test
./run.sh health     # quick liveness only
./run.sh functions  # core API surface only
```

Sets are selected by filename: `test_health_*.sh` (health), `test_func_*.sh` (functions),
all `test_*.sh` (full).

## Requirements

- `curl` and `python3` on PATH.
- A reachable OpenViking server. By default tests hit `http://127.0.0.1:1933` and
  read the user API key from `~/.openviking/ovcli.conf`, so on the OV host they
  run with no extra setup.

## Config (env vars)

| Var | Default | Meaning |
|-----|---------|---------|
| `OV_URL` | `http://127.0.0.1:1933` | Server base URL |
| `OV_KEY` | `ovcli.conf.api_key` | User API key (Bearer) |
| `OV_TEST_DIR` | `viking://resources/second-brain` | Resource dir for stat/tree/overview/find/glob |
| `OV_TEST_FILE` | `viking://resources/second-brain/CLAUDE.md` | File for read/abstract/grep |
| `OV_TEST_QUERY` | disks/snapshots phrase | Semantic query for find |
| `OV_TEST_GREP` | `OpenViking` | Literal pattern for grep |

Point them at any resource you have indexed, e.g.:

```bash
OV_TEST_DIR=viking://resources/ov-lib \
OV_TEST_FILE=viking://resources/ov-lib/README.md \
OV_TEST_GREP=library ./run.sh functions
```

## What each test checks

**health**
- `test_health_server` — `/system/status` reports `initialized: true`.
- `test_health_auth` — the configured key reaches tenant-scoped data APIs (catches a root-key misconfig).

**functions**
- `test_func_ls` / `test_func_tree` — `fs/ls`, `fs/tree` return entries.
- `test_func_stat` — `fs/stat` returns metadata (`isDir`, `count`).
- `test_func_read` / `test_func_overview` / `test_func_abstract` — L2/L1/L0 content is non-empty.
- `test_func_find` — semantic `search/find` with `target_uri` returns ranked hits under `resources`
  (guards the "find returns nothing / wrong scope field" regression).
- `test_func_grep` — `search/grep` returns `matches` for a known pattern.
- `test_func_glob` — `search/glob` resolves a filename pattern.
- `test_func_watches` — `/watches` control plane returns the task list.
