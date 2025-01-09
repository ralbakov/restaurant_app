FROM python:3.12-alpine

LABEL authors="albakov.ruslan@gmail.com"

COPY poetry.lock pyproject.toml /

RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-root --no-directory

COPY . .

WORKDIR source/
