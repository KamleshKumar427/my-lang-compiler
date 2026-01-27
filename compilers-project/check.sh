#!/bin/bash
set -euo pipefail
cd "$(dirname "${0}")"
poetry run mypy .
poetry run pytest -vv tests/
