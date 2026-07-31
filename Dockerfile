FROM python:3.14-slim-trixie

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt update && \
    apt upgrade -y && \
    apt install -y build-essential libarchive-tools python3-dev && \
    apt purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --gid ${GID:-1000} python && \
    adduser --disabled-password --gecos "" --home /app --uid ${UID:-1000} --gid ${GID:-1000} python && \
    chown -R python:python /app

COPY requirements.txt /app/
RUN --mount=type=cache,target=/var/cache/pip \
  pip install --cache-dir /var/cache/pip -U pip && \
  pip install --cache-dir /var/cache/pip -Ur /app/requirements.txt

ARG ENV_TYPE=production
COPY requirements-development.txt /app/
RUN --mount=type=cache,target=/car/cache/pip \
  if [ "$(echo $ENV_TYPE | tr A-Z a-z)" != "production" ]; then \
    pip install --cache-dir /var/cache/pip -Ur /app/requirements-development.txt; \
    apt update && apt install -y git && apt clean && rm -rf /var/lib/apt/lists/*; \
  else \
    rm /app/requirements-development.txt ; \
  fi

COPY --chown=python:python . /app/
USER python
