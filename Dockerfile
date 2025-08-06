FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

ENV SLF_OUTPUT_PATH=/app/slf-output
RUN mkdir /app/slf-output

COPY pyproject.toml .
COPY src ./src
COPY README.md .

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y build-essential python3-dev

RUN pip install --upgrade pip setuptools wheel
RUN pip install .

CMD ["--help"]
