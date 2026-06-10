#!/usr/bin/env python3
"""Smoke test for the Face Recognition external model API.

Hits every public endpoint against every JPEG in test/, using the same
multipart upload the Nextcloud app sends. Exits non-zero on any failure.

Configuration via environment variables:
    API_BASE  base URL of the service (default: http://localhost:8080)
    API_KEY   shared secret (default: some-super-secret-api-key)

Usage:
    API_KEY=... python3 test/api_smoke.py
"""
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("API_BASE", "http://localhost:8080").rstrip("/")
API_KEY = os.environ.get("API_KEY", "some-super-secret-api-key")
TEST_DIR = Path(__file__).resolve().parent
IMAGES = sorted(TEST_DIR.glob("*.jpg")) + sorted(TEST_DIR.glob("*.jpeg"))


def request(method, path, *, headers=None, data=None, timeout=300):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ctype = resp.headers.get_content_type()
            return resp.status, body, ctype
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get_content_type() if e.headers else ""


def parse_json(body, ctype):
    if "json" in ctype or body.startswith(b"{") or body.startswith(b"["):
        return json.loads(body)
    return body.decode("utf-8", errors="replace")


def multipart(path, file_path):
    boundary = "----smoke-test-boundary-XYZ"
    fname = file_path.name
    ctype, _ = mimetypes.guess_type(str(file_path))
    if ctype is None:
        ctype = "application/octet-stream"
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "x-api-key": API_KEY,
    }
    return body, headers


def multipart_with_face(path, file_path, face):
    boundary = "----smoke-test-boundary-XYZ"
    fname = file_path.name
    ctype, _ = mimetypes.guess_type(str(file_path))
    if ctype is None:
        ctype = "application/octet-stream"
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    face_field = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="face"\r\n\r\n'
        f"{json.dumps(face)}\r\n"
    ).encode()
    file_field = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + file_bytes + b"\r\n"
    body = face_field + file_field + f"--{boundary}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "x-api-key": API_KEY,
    }
    return body, headers


def expect(condition, message):
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {message}")
    return condition


def check_unauth(name, path):
    print(f"\n{name} {path}")
    status, body, ctype = request("GET", path)
    if not expect(status == 200, f"status 200, got {status}"):
        return False
    payload = parse_json(body, ctype)
    if path == "/health":
        return expect(payload == "ok", f'body == "ok", got {payload!r}')
    if path == "/welcome":
        return expect(
            isinstance(payload, dict) and "version" in payload,
            f"body has 'version', got {payload!r}",
        )
    return True


def check_open():
    print("\nGET /open (auth)")
    status, body, ctype = request(
        "GET", "/open", headers={"x-api-key": API_KEY}
    )
    if not expect(status == 200, f"status 200, got {status}"):
        return False
    payload = parse_json(body, ctype)
    return expect(
        isinstance(payload, dict)
        and payload.get("preferred_mimetype")
        and isinstance(payload.get("maximum_area"), int),
        f"body has preferred_mimetype + maximum_area, got {payload!r}",
    )


def check_detect(image):
    print(f"\nPOST /detect {image.name}")
    body, headers = multipart("/detect", image)
    status, resp, ctype = request("POST", "/detect", headers=headers, data=body)
    if not expect(status == 200, f"status 200, got {status}"):
        return None
    payload = parse_json(resp, ctype)
    if not expect(
        isinstance(payload, dict) and "faces" in payload,
        f"body has 'faces', got {payload!r}",
    ):
        return None
    count = len(payload["faces"])
    print(f"  [INFO] detected {count} face(s)")
    if count == 0:
        return None
    face = payload["faces"][0]
    if not expect(
        {"left", "top", "right", "bottom", "landmarks", "descriptor"} <= set(face),
        "first face has all required fields",
    ):
        return None
    if not expect(
        len(face["descriptor"]) == 128, "descriptor is 128-d"
    ):
        return None
    return {
        "left": face["left"],
        "top": face["top"],
        "right": face["right"],
        "bottom": face["bottom"],
    }


def check_compute(image, face):
    print(f"\nPOST /compute {image.name} face={face}")
    body, headers = multipart_with_face("/compute", image, face)
    status, resp, ctype = request("POST", "/compute", headers=headers, data=body)
    if not expect(status == 200, f"status 200, got {status}"):
        return False
    payload = parse_json(resp, ctype)
    return expect(
        isinstance(payload, dict)
        and "face" in payload
        and len(payload["face"].get("descriptor", [])) == 128,
        f"body has face with 128-d descriptor, got {payload!r}",
    )


def main():
    if not IMAGES:
        print(f"No .jpg/.jpeg images found in {TEST_DIR}", file=sys.stderr)
        return 2

    print(f"API base: {API_BASE}")
    print(f"Images:   {[p.name for p in IMAGES]}")

    passed = 0
    failed = 0

    def tally(ok):
        nonlocal passed, failed
        if ok:
            passed += 1
        else:
            failed += 1
        return ok

    tally(check_unauth("GET", "/health"))
    tally(check_unauth("GET", "/welcome"))
    tally(check_open())

    for image in IMAGES:
        face = check_detect(image)
        tally(face is not None)
        if face is not None:
            tally(check_compute(image, face))

    total = passed + failed
    print(f"\n=== {passed}/{total} checks passed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
