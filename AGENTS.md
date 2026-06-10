# AGENTS.md

Guidance for OpenCode sessions working in this repository.

## What this repo is

A small Flask service that wraps dlib-based face detection/recognition so it can run as a remote "external model" for the Nextcloud [Face Recognition](https://github.com/matiasdelellis/facerecognition) app. The Python code lives in a single file inside a tiny package; the Docker assets are grouped under `docker/`. There are no tests, no linter, no type checker.

## Layout

- `app/server.py` — Flask app (`app` object) + dlib model loading + endpoints. Loaded by gunicorn as `app.server:app`.
- `app/gunicorn.py` — gunicorn config (bind, workers/threads, startup hook that creates and purges the `images/` temp dir). Lives next to the app module; loaded by the Dockerfile's `ENTRYPOINT` as `-c app/gunicorn.py`.
- `Makefile` (root) — convenience wrapper that delegates to `docker/Makefile` so `make compose-up` / `make compose-down` / `make serve` / `make download-models` work from the repo root. Pass `FACE_MODEL=N` to forward a different model.
- `docker/Dockerfile` — multi-stage build that compiles `dlib` via `pip wheel` (needs `cmake g++ make wget bzip2`) and downloads the `.dat` model files via `make -C /app download-models`. Build context is the repo root.
- `docker/Makefile` — `download-models` fetches the three dlib `.dat` files into `vendor/models/` (the path used by the Dockerfile's `make -C /app/ download-models`); `serve` runs `flask run` with `FLASK_APP=app.server` after downloading them. `FACE_MODEL` is overridable on the make command line. `compose-up` / `compose-down` wrap `docker compose -f docker/docker-compose.yml`.
- `docker/docker-compose.yml` — service definition. `build.context` is the parent dir, `dockerfile: docker/Dockerfile`. Loads the API key from `../.env` via `env_file:`.
- `.env` — defines `API_KEY=...`. Picked up automatically by docker-compose via `env_file` and exported into the container, where the `require_appkey` decorator reads it from `os.environ`. Gitignored — never commit a real one. The Dockerfile also sets a default `API_KEY` for plain `docker run` users, which `env_file` overrides.
- `.github/workflows/docker-build.yml` — manual `workflow_dispatch` only; takes a `tagName` input, builds `linux/amd64,linux/arm64`, pushes to DockerHub as `matiasdelellis/facerecognition-external-model:<tagName>`. Stays at the repo root (GitHub Actions only looks at `.github/workflows/` at the top level). No CI on push.
- `vendor/` and `images/` are gitignored (vendored model files and per-request temp uploads). `__pycache__/` and `.env` are also ignored.
- `doc/` — user-facing documentation: `README.md` (overview + quickstart), `api.md` (HTTP reference), `configuration.md` (env vars, `FACE_MODEL` semantics), `integration.md` (wiring it to Nextcloud), `.env.example` (template for the `.env` file consumed by docker-compose). The repo-root `README.md` is just an index that points here. Keep the two in sync when endpoints or env vars change.

## Commands

- `make download-models` — required before first local run; downloads and decompresses the three `.dat` files into `vendor/models/`. Re-run if `vendor/models/*.dat` is missing.
- `make serve` (or `FACE_MODEL=3 make serve`) — local dev via Flask's dev server from the repo root (so `FLASK_APP=app.server` resolves and `vendor/` / `images/` are found relative to CWD). **Note:** the `images/` temp dir is only created/cleaned by gunicorn's `on_starting` hook, not by `flask run`, so a stale `images/` directory will not be auto-purged in dev.
- `make compose-up` (or `FACE_MODEL=3 GUNICORN_WORKERS=2 make compose-up`) — build & run via `docker/docker-compose.yml`, then tail logs. API key is read from `.env` (via `env_file:`); override with `API_KEY=...`. Stop with `make compose-down`.
- Docker is the supported runtime: `docker run -p 8080:5000 -v /path/to/api.key:/app/api.key --name facerecognition matiasdelellis/facerecognition-external-model:<tag>` (see `README.md` for full options).
- `curl localhost:8080/welcome` — health-ish check; returns 200 with model + version, or 200 with a "missing neural network files" message if models are absent.
- `python3 test/api_smoke.py` (with `API_KEY=...` exported) — smoke test the full API against the two images in `test/`. Stdlib-only, exits non-zero on any failure. Assumes the service is reachable at `API_BASE` (default `http://localhost:8080`).
- No `requirements.txt`, no `pyproject.toml`. Runtime deps are pinned only in the Dockerfile (`flask`, `numpy`, `gunicorn`, `dlib`). Don't add a `requirements.txt` without confirming.

## Endpoints (all under API key except `/health` and `/welcome`)

- `POST /detect` — multipart `file=<image>`. Saves to `images/<basename>`, runs `DETECT_FACES_FUNCTIONS[FACE_MODEL]`, deletes the file, returns face list.
- `POST /compute` — multipart `file=<image>` + form field `face=<json rect>`. Computes landmarks + 128-d descriptor for a single known face rect.
- `GET /open` — eagerly loads dlib models; returns `preferred_mimetype` and `maximum_area`. Loading is also lazy on first `/detect` or `/compute`.
- `GET /health` — unauthenticated, returns `"ok"`.
- `GET /welcome` — unauthenticated, reports version and active `FACE_MODEL`.

Auth: client sends `x-api-key` header. If header missing or wrong → 401. Image area > `3840*2160` → 412.

## `FACE_MODEL` semantics

Index into `DETECT_FACES_FUNCTIONS` at `app/server.py:93`. Currently:

- `1` — CNN detector only (`cnn_detect`).
- `3` — HOG detector only (`hog_detect`). Faster but less accurate; also skips the CNN detector load.
- `4` — CNN detector validated against HOG (`cnn_hog_detect`). **Default** in both code (`os.environ` fallback) and `Makefile`.

Index `2` is `None` — selecting it will raise `TypeError` on the first request. Don't advertise model 2.

## Known quirks worth knowing

- The detection functions share module-level globals (`CNN_DETECTOR`, `HOG_DETECTOR`, `PREDICTOR`, `FACE_REC`) that are populated lazily on the first request, not at import. `HOG_DETECTOR` is referenced by `hog_detect` before being assigned if model 1 is selected with HOG paths — model 1 path doesn't touch it, so it's fine in practice, but be careful when editing.
- `/compute` writes the upload to `filename` in the **current working directory** (bare, no `images/` join — `app/server.py:169`), unlike `/detect` which uses `images/<filename>`. Looks like an inconsistency rather than intentional; confirm with the maintainer before changing.
- `app/gunicorn.py:8` sets `threads = int(os.getenv("GUNICORN_WORKERS", 1))` — workers and threads share the same env var, not a typo to "fix". README's "one core per process" claim assumes `threads=1`, so set `GUNICORN_WORKERS` deliberately.
- `reload = bool("false")` in `app/gunicorn.py:10` is always `True` (non-empty string is truthy) and reloads the app on every gunicorn boot inside the container. Inert in the Docker entrypoint but surprising if you read it standalone.
- The legacy `api.key` file is no longer used by `docker-compose` (it now reads `API_KEY` from `.env`). The `require_appkey` decorator still has a fallback that opens `api.key` from CWD if `API_KEY` is not in the environment — useful for plain `docker run` users who mount the file directly via `-v /path/to/api.key:/app/api.key:ro` (the Dockerfile's default `ENV API_KEY` is overridden by an explicit `-e API_KEY=...` or by `env_file` from compose).

## Release flow

There is no automated release. To publish a new image:

1. Bump `PACKAGE_VERSION` in `app/server.py:11`.
2. Update the `vX.Y.Z` references in `README.md` if you care about the doc example.
3. Trigger `.github/workflows/docker-build.yml` manually from the Actions tab with a `tagName` (e.g. `v0.3.0`). It builds multi-arch and pushes to DockerHub.

Do not push tags to git and expect a release — the workflow does not watch tags or `master`.
