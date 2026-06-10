# Configuration

The service is configured entirely through environment variables and a few files on disk. There is no config file format of its own.

## Environment variables

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `API_KEY` | `some-super-secret-api-key` (in the Dockerfile) | recommended | Shared secret. Every authenticated request must send it in the `x-api-key` header. |
| `FACE_MODEL` | `4` | optional | Selects which detection algorithm runs (see below). |
| `GUNICORN_WORKERS` | `1` | optional | Number of gunicorn worker processes. The same number is also used for threads per worker. |
| `REQ_TIMEOUT` | `300` | optional | Per-request gunicorn timeout, in seconds. |
| `PORT` | `5000` | optional | Port the server binds to inside the container. |

### `API_KEY`

The auth secret. Generate one with `openssl rand -base64 32` and keep it private.

```sh
openssl rand -base64 32 > api.key
cat api.key
# NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=
```

The recommended way to pass it to the container is via the `.env` file in the repo root. `docker compose` reads it automatically through `env_file:` and exports it into the container.

```env
# .env
API_KEY=NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=
```

The legacy alternative — mounting a file at `/app/api.key` and letting the app read it on each request — still works for plain `docker run` users. The Dockerfile's default `ENV API_KEY=...` is overridden by either an explicit `-e API_KEY=...` or by `env_file:` from compose.

> **Never commit a real `API_KEY` to the repository.** The `.env` file is gitignored for this reason.

### `FACE_MODEL`

Picks the detection algorithm. This is the index into the `DETECT_FACES_FUNCTIONS` table at `app/server.py`.

| Value | Algorithm | Speed | Accuracy | Loads CNN? | Loads HOG? |
|-------|-----------|-------|----------|------------|------------|
| `1`   | CNN only | slow | high | yes | no |
| `3`   | HOG only | fast | medium | no | yes |
| `4`   | CNN validated against HOG | slow | high | yes | yes |

- `1` and `4` use the MMOD CNN detector (`mmod_human_face_detector.dat`) and return a real `detection_confidence` in `[0, 1]`.
- `3` uses dlib's classic HOG + SVM detector. Faster, weaker on profile and small faces. Reports a constant `detection_confidence: 1.1` since HOG has no score.
- `4` is the default. It runs the CNN detector, then for every CNN hit checks whether the HOG detector finds an overlapping face (IoU ≥ `0.35`). Hits that don't validate get their confidence multiplied by `0.8`.

**Value `2` is reserved** — it currently returns `None` and selecting it will crash the first request with a `TypeError`. Treat it as a non-option. Any other value not in the table above is rejected by Python's `int()` cast or the dict lookup.

### `GUNICORN_WORKERS`

Controls the number of gunicorn worker processes *and* the threads-per-worker (the same value is used for both — that is intentional, see the comment in `app/gunicorn.py`).

Each worker handles one request at a time. More workers = more parallelism = more RAM. The dlib models are loaded once per worker. A reasonable starting point is `GUNICORN_WORKERS = <number of physical CPU cores>`.

When raising `GUNICORN_WORKERS` from 1, monitor the container's memory: the CNN detector alone uses ~250 MB.

## Model files

The service needs three `.dat` files in `vendor/models/`:

- `mmod_human_face_detector.dat` — CNN detector (required for `FACE_MODEL` 1 and 4).
- `shape_predictor_5_face_landmarks.dat` — landmark predictor (always required).
- `dlib_face_recognition_resnet_model_v1.dat` — face descriptor model (always required).

The Docker build downloads and bakes them into the image, so end users of the published image do not need to think about this. For local development, run:

```sh
make -C docker download-models
```

The `/welcome` endpoint reports whether the files are present — see the [API reference](api.md#get-welcome).

## Image size limit

Hard-coded in `app/server.py` as `3840 * 2160` (8 294 400 pixels, roughly 4K). Images exceeding this get a `412` response. The same number is reported in the `/open` response as `maximum_area` so clients can downscale proactively.

## Local development

The repo supports a `flask run` workflow without Docker, useful for iteration.

```sh
# 1. Download the model files into vendor/models/
make -C docker download-models

# 2. Run Flask's dev server (port 5000 by default)
FACE_MODEL=4 make -C docker serve
```

The dev server runs from the repo root, so `FLASK_APP=app.server` resolves and `vendor/` / `images/` are picked up relative to the current working directory.

> The `images/` temp directory is only created and cleaned by gunicorn's `on_starting` hook. When using `flask run`, a stale `images/` directory will not be auto-purged — clear it manually with `rm -rf images/*` if you need a clean slate.

The `flask run` server is **single-threaded** by default. For parallel request testing locally, run gunicorn directly:

```sh
gunicorn -c app/gunicorn.py app.server:app
```
