FROM python:slim AS builder

COPY docker/Makefile /app/Makefile

RUN apt update -yq \
    && apt install -yq bzip2 cmake g++ make wget \
    && pip wheel -w /app/ dlib \
    && make -C /app/ download-models

FROM python:slim

COPY --from=builder /app/dlib*.whl /tmp/
COPY --from=builder /app/vendor/ /app/vendor/

RUN pip install flask numpy gunicorn \
    && pip install --no-index -f /tmp/ dlib \
    && rm /tmp/dlib*.whl

COPY app/ /app/app/

WORKDIR /app/

EXPOSE 5000

ARG GUNICORN_WORKERS="1" \
    PORT="5000"
ENV GUNICORN_WORKERS="${GUNICORN_WORKERS}"\
    PORT="${PORT}"\
    API_KEY=some-super-secret-api-key\
    FLASK_APP=app.server

ENTRYPOINT ["gunicorn", "-c", "app/gunicorn.py", "app.server:app"]
