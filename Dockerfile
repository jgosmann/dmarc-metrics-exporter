FROM python:3.8-alpine as base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

FROM base as build

WORKDIR /build
COPY . ./

RUN apk add --no-cache gcc libffi-dev openssl-dev libxml2-dev libxslt-dev make musl-dev && \
    pip install --upgrade pip && \
    pip install poetry && \
    poetry build && \
    poetry export -f requirements.txt --without-hashes --output requirements.txt

RUN python -m venv /venv && \
    /venv/bin/pip install -r requirements.txt && \
    /venv/bin/pip install dist/*.whl

FROM base as dist

COPY --from=build /venv /venv

RUN apk add --no-cache bash libffi libpq libxml2 libxslt openssl

COPY docker-entrypoint.sh /docker-entrypoint.sh
CMD /docker-entrypoint.sh
