FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

ENV LOG_OUTPUT_PATH=/app/logs
RUN mkdir -p /app/logs

ENV SLF_OUTPUT_PATH=/app/slf-output
RUN mkdir /app/slf-output

ENV ABOSA_OUTPUT_PATH=/abosa-output
RUN mkdir /abosa-output

COPY pyproject.toml .
COPY src ./src
COPY README.md .

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y build-essential python3-dev

RUN pip install --upgrade pip setuptools wheel
RUN pip install .

CMD ["--help"]
