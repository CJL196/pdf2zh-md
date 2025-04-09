FROM python:3.12.9 AS builder

COPY . .

RUN pip install -r requirements.txt && \
    /usr/local/bin/python3.12 -m pip uninstall pathlib -y && \
    pip install pyinstaller && \
    pyinstaller app.spec

FROM ubuntu:24.04

WORKDIR /app

COPY --from=builder ./dist/app/* /app/

ENTRYPOINT ["/app/app"]