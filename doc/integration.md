# Integration with Nextcloud

The Nextcloud [Face Recognition](https://github.com/matiasdelellis/facerecognition) app supports running its models on a remote HTTP service. This document covers the operational steps; for the wire protocol, see the [API reference](api.md).

## 1. Reachability

The Nextcloud host must be able to reach the service on the configured port. From the Nextcloud machine:

```sh
curl http://<service-host>:8080/welcome
# {"facerecognition-external-model":"welcome","model":4,"version":"0.2.0"}
```

If the request times out, the issue is network — firewall, NAT, or DNS — not the service.

Find the service host's IP with `hostname -I` (or `ip addr`).

## 2. Configure the Nextcloud app

```sh
# Tell the app where the service is
sudo -u www-data php occ config:system:set \
  facerecognition.external_model_url \
  --value "<service-host>:8080"

# Tell the app the shared secret (same value as API_KEY in the service's .env)
sudo -u www-data php occ config:system:set \
  facerecognition.external_model_api_key \
  --value "<the contents of api.key / API_KEY>"

# Select the external model (id 5)
sudo -u www-data php occ face:setup -m 5
# The files of model 5 (ExternalModel) are already installed
# The model 5 (ExternalModel) was configured as default
```

After this, the app treats model 5 — the external HTTP model — as the default. Background tasks (`php occ face:background_job`) will now call the service instead of running dlib in-process.

## 3. First run

Trigger an analysis pass from the command line to verify end-to-end:

```sh
sudo -u www-data php occ face:background_job -u <user> --analyze-mode
```

You can watch the service logs at the same time to confirm requests are arriving:

```sh
docker compose -f docker/docker-compose.yml logs -f facerecognition
```

A successful request looks like:

```
192.168.1.50 - - [10/Jun/2026:00:30:00 +0000] 'POST /detect HTTP/1.1' 200 8432 in 412ms
```

## 4. Parallel imports

The single-process Nextcloud background job is slow on large libraries. The script below runs multiple `analyze-mode` jobs in parallel. Set the loop count ≤ `GUNICORN_WORKERS` on the service side, otherwise the extra jobs just queue.

```sh
#!/bin/bash
set -o errexit

dir=$(pwd)
cd /var/www/nextcloud/html/   # your nextcloud path
sudo -u www-data php --define apc.enable_cli=1 ./occ face:stats

echo -n "Select user for import & parallel processing:"
read user
echo ""

echo "Enabling facerecognition for $user..."
sudo -u www-data php --define apc.enable_cli=1 ./occ user:setting \
  $user facerecognition enabled true
echo "Done"

echo "Synchronizing $user files..."
sudo -u www-data php --define apc.enable_cli=1 ./occ face:background_job \
  -u $user --sync-mode
echo "Done"

echo "Analyzing $user files..."
# the upper number has to be lower or equal to the number of GUNICORN_WORKERS
for i in {1..3}; do
  sudo -u www-data php --define apc.enable_cli=1 ./occ face:background_job \
    -u $user --analyze-mode &
  pids[${i}]=$!
done

for pid in ${pids[*]}; do
  wait $pid
done
echo "Done"

echo "Calculating $user face clusters..."
sudo -u www-data php --define apc.enable_cli=1 ./occ face:background_job \
  -u $user --cluster-mode
echo "Done"
cd $dir
```

This runs for a long time on big libraries. Use `tmux` or `screen` so the session survives disconnects.

## 5. Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `/welcome` returns the "missing neural network files" message | The image was built without the model files, or `vendor/models/` is empty in the running container. Rebuild with the model download step. |
| 401 on every request from Nextcloud | `external_model_api_key` does not match the service's `API_KEY` (watch for trailing newlines, shell quoting). |
| 412 from the service | An image exceeds `maximum_area`. Either downscale before uploading, or — if you control the Nextcloud side — adjust the upload size policy. |
| Requests time out | `REQ_TIMEOUT` too low for big images, or the service is single-worker and saturated. Raise `GUNICORN_WORKERS` if the host has spare cores and RAM. |
| 500 with a `TypeError` mentioning `NoneType` in the response | `FACE_MODEL=2` was selected. Use 1, 3, or 4. |

## 6. Privacy reminder

Every analyzed image leaves the Nextcloud host and is sent to this service. Make sure the link between them is trusted (LAN, VPN, or HTTPS through a reverse proxy) and that the host running the service is hardened accordingly.
