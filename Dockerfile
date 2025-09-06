FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04 AS builder

COPY Makefile /app/

RUN apt update -yq
RUN apt install -yq python3 python3-pip bzip2 cmake g++ make wget git libopenblas-dev liblapack-dev

# This is TMP until this PR is merged:
# https://github.com/davisking/dlib/pull/3090
RUN git clone https://github.com/smu-sc-gj/dlib
RUN cd dlib && pip wheel -w /app/ . -vvv
RUN make -C /app/ download-models

# CUDA Runtime
FROM  nvidia/cuda:13.0.0-cudnn-runtime-ubuntu24.04

RUN apt update -yq
RUN apt install -yq python3 python3-pip libopenblas-dev liblapack-dev

COPY --from=builder /app/dlib*.whl /tmp/
COPY --from=builder /app/vendor/ /app/vendor/

RUN pip install --break-system-packages flask numpy gunicorn
RUN pip install --break-system-packages --no-index -f /tmp/ dlib \
    && rm /tmp/dlib*.whl

COPY facerecognition-external-model.py /app/
COPY gunicorn_config.py /app/

WORKDIR /app/

EXPOSE 5000

ARG GUNICORN_WORKERS="1" \
    PORT="5000"
ENV GUNICORN_WORKERS="${GUNICORN_WORKERS}"\
    PORT="${PORT}"\
    API_KEY=some-super-secret-api-key\
    FLASK_APP=facerecognition-external-model.py

ENTRYPOINT ["gunicorn"  , "-c", "gunicorn_config.py", "facerecognition-external-model:app"]
