# API reference

The service speaks HTTP. Every endpoint that takes an image expects a standard `multipart/form-data` upload with a `file` field. All responses are JSON unless noted otherwise.

## Authentication

Every endpoint except `/health` and `/welcome` requires the API key in the `x-api-key` request header.

```
x-api-key: <the value of API_KEY from your .env or api.key file>
```

Responses on auth failure:

| Status | When |
|--------|------|
| `401`  | Header missing, or value does not match `API_KEY`. |
| `412`  | Image dimensions exceed the configured maximum (see below). |

The `API_KEY` value is supplied to the container either via the `API_KEY` environment variable (preferred — `docker-compose.yml` reads it from `../.env` via `env_file:`) or by mounting a file at `/app/api.key` and omitting the env var.

## Endpoints

### `GET /health`

Unauthenticated liveness probe. Returns plain text `"ok"` with `200`. Use this for container healthchecks.

```sh
curl -s localhost:8080/health
# ok
```

### `GET /welcome`

Unauthenticated. Reports the running version and the active `FACE_MODEL`. If the dlib `.dat` model files are missing from `vendor/models/`, the response changes to flag that the service is not ready to serve real requests.

When models are present:

```json
{
  "facerecognition-external-model": "welcome",
  "version": "0.2.0",
  "model": 4
}
```

When models are missing:

```json
{
  "facerecognition-external-model": "Neural network files are missing. Install them with 'make download-models",
  "version": "0.2.0"
}
```

This is the recommended first call from a new client: if you don't get the `model` field, the container is not actually usable.

### `GET /open`

**Authenticated.** Eagerly loads the dlib models (if not already loaded) and returns the metadata the Nextcloud app needs to know what to send.

```sh
curl -s -H "x-api-key: $API_KEY" localhost:8080/open
```

```json
{
  "preferred_mimetype": "image/jpeg",
  "maximum_area": 8294400
}
```

- `preferred_mimetype` — the format the service prefers for uploads. The Nextcloud client may still send other formats; dlib handles them.
- `maximum_area` — pixel budget (`width * height`). The service rejects larger images with `412`; clients should downscale before sending to save bandwidth and CPU.

> Calling `/open` is **optional**. The same model loading happens lazily on the first `/detect` or `/compute` call.

### `POST /detect`

**Authenticated.** Main entry point. Takes one image, returns the list of detected faces, each with its bounding box, landmarks, and 128-dimensional descriptor.

```sh
curl -s -H "x-api-key: $API_KEY" \
  -F "file=@photo.jpg" \
  localhost:8080/detect
```

```json
{
  "filename": "photo.jpg",
  "faces-count": 2,
  "faces": [
    {
      "detection_confidence": 1.0,
      "left": 180,
      "top": 100,
      "right": 280,
      "bottom": 230,
      "landmarks": [
        {"x": 192, "y": 138},
        {"x": 268, "y": 138},
        ...
      ],
      "descriptor": [
        -0.043, 0.076, 0.011, -0.040, ...
      ]
    }
  ]
}
```

Field reference for each face:

- `detection_confidence` — dlib's confidence score, in `[0, 1]`. For HOG-only models the service reports a constant `1.1`. For models that combine CNN + HOG validation, faces that did not validate get multiplied by `0.8`.
- `left`, `top`, `right`, `bottom` — bounding box in image pixels.
- `landmarks` — five `(x, y)` points (left eye, right eye, nose, left mouth, right mouth) when the active predictor is `shape_predictor_5_face_landmarks.dat`. Used for face alignment before descriptor extraction.
- `descriptor` — 128 floats. Two descriptors compared with Euclidean distance are considered the same person when the distance is below ~`0.6`.

### `POST /compute`

**Authenticated.** Given a known face rectangle in an image, recompute its landmarks and 128-d descriptor. Use this after the user has manually adjusted a face box, or to re-extract a descriptor after re-alignment.

```sh
curl -s -H "x-api-key: $API_KEY" \
  -F "file=@photo.jpg" \
  -F 'face={"left":180,"top":100,"right":280,"bottom":230}' \
  localhost:8080/compute
```

The `face` field is a JSON object with the four rectangle edges. Response:

```json
{
  "filename": "photo.jpg",
  "face": {
    "left": 180,
    "top": 100,
    "right": 280,
    "bottom": 230,
    "landmarks": [
      {"x": 192, "y": 138},
      ...
    ],
    "descriptor": [
      -0.043, 0.076, 0.011, -0.040, ...
    ]
  }
}
```

The input `face` rectangle is echoed back alongside the new `landmarks` and `descriptor`.

## Error responses

The service uses conventional HTTP status codes and returns a small JSON or HTML body (Flask's default for `abort(...)`).

| Status | Meaning |
|--------|---------|
| `400`  | Malformed request (missing `file`, malformed `face` JSON, etc.). |
| `401`  | Missing or wrong `x-api-key`. |
| `404`  | Unknown endpoint. |
| `405`  | Wrong HTTP method. |
| `412`  | Image area exceeds `maximum_area` from `/open`. |
| `500`  | Unexpected server error. The full traceback lands in the container logs. |

`/detect` and `/compute` clean up the uploaded file on success. If processing fails after the upload, the temp file may be left behind and will be purged on the next gunicorn worker boot.
