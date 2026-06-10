# Face Recognition External Model 👪

A small HTTP service that runs the same face detection / recognition models shipped with the Nextcloud [Face Recognition](https://github.com/matiasdelellis/facerecognition) app, but on a separate host. It offloads the heaviest work from the Nextcloud server, where it competes with web serving, sync, and other workloads.

The service speaks the same JSON-over-HTTP protocol the Nextcloud app expects from any "external model" backend, so you can also use this repository as a reference implementation if you want to build your own in another language.

## Documentation

Full documentation lives in [`doc/`](doc/README.md):

- [Overview & quickstart](doc/README.md)
- [API reference](doc/api.md) — every endpoint, request, and response shape
- [Configuration](doc/configuration.md) — environment variables, `FACE_MODEL`, sizing
- [Integrating with Nextcloud](doc/integration.md) — `occ` commands and the parallel-import script

## TL;DR

```sh
# 1. Generate a key
openssl rand -base64 32 > .env   # put API_KEY=... inside

# 2. Run
docker compose -f docker/docker-compose.yml up -d

# 3. Verify
curl localhost:8080/welcome
# {"facerecognition-external-model":"welcome","model":4,"version":"0.2.0"}
```

Then point the Nextcloud app at it — see [doc/integration.md](doc/integration.md).
