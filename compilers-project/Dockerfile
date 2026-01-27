FROM python:3.12-alpine3.21

RUN pip install --no-cache-dir poetry==2.0.0
RUN apk add --no-cache bash binutils

WORKDIR /compiler
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-cache

COPY . .

RUN poetry install --no-cache && ./check.sh

EXPOSE 3000

# Setting PYTHONUNBUFFERED forces print() to flush even if stdout is not a TTY.
ENV PYTHONUNBUFFERED=1
CMD ["./compiler.sh", "serve", "--host=0.0.0.0"]
