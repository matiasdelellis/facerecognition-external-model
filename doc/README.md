# Face Recognition External Model

This service implements the same [models](https://github.com/matiasdelellis/facerecognition/wiki/Models) shipped with the Nextcloud [Face Recognition](https://github.com/matiasdelellis/facerecognition) application, but runs on a separate machine. That offloads the heaviest work from the server hosting Nextcloud, where it competes with web serving, sync and other tasks.

You can use it as a black-box reference: the API is the same surface the Nextcloud app expects from any "external model", so the same protocol applies if you decide to implement your own backend in another language or framework.

## What is in this repository

```
.
├── app/
│   ├── server.py            # Flask app + dlib model loading + endpoints
│   └── gunicorn.py          # gunicorn configuration
├── docker/
│   ├── Dockerfile
│   ├── Makefile
│   └── docker-compose.yml
├── doc/                     # you are here
│   ├── README.md            # this file
│   ├── api.md               # HTTP API reference
│   ├── configuration.md     # environment variables, FACE_MODEL semantics
│   └── integration.md       # wiring it up to Nextcloud
├── Makefile                 # convenience wrapper → docker/Makefile
├── vendor/                  # dlib .dat model files (downloaded, gitignored)
└── images/                  # per-request temp uploads (gitignored)
```

## Documentation

- [API reference](api.md) — every endpoint, request and response shape.
- [Configuration](configuration.md) — environment variables, `FACE_MODEL` semantics, sizing.
- [Integration with Nextcloud](integration.md) — `occ` commands and parallel-import script.

## Privacy

The service receives a copy of every image you want analyzed. The image is sent via `POST`, saved to a local temp directory, processed, and deleted before the response is sent. The shared API key travels in the `x-api-key` header of every request.

This is only as secure as the connection between the two hosts. **Do not expose the service to the public internet without putting it behind an HTTPS reverse proxy.** Think about data security before deploying outside your local network.

## Quickstart (Docker)

The fastest path. You only need an API key and a host port.

```sh
# 1. Generate an API key
openssl rand -base64 32 > api.key

# 2. Run the container
docker run --rm -d \
  -p 8080:5000 \
  -v "$(pwd)/api.key:/app/api.key:ro" \
  --name facerecognition \
  matiasdelellis/facerecognition-external-model:v0.2.0

# 3. Verify
curl localhost:8080/welcome
# {"facerecognition-external-model":"welcome","model":4,"version":"0.2.0"}
```

### With docker-compose

```sh
# 1. Copy and fill in the env file
cp doc/.env.example .env
# edit .env and replace API_KEY with a real secret

# 2. Build and start
make compose-up

# 3. Stop when done
make compose-down
```

A docker-compose setup is also provided. See [`docker/docker-compose.yml`](../docker/docker-compose.yml) and the [configuration](configuration.md) docs for environment variables.

For local development without Docker, see [configuration.md → Local development](configuration.md#local-development).

## Supported versions

The image is published to Docker Hub as `matiasdelellis/facerecognition-external-model:<tag>`. Tags are cut manually from the GitHub Actions workflow; the latest published tag is what you should use unless you have a reason to pin older versions.
