#!/bin/sh

set -e

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"

coverage run --rcfile "${BASE_DIR}/pyproject.toml" -m pytest -s "${BASE_DIR}/tests" "$*"
coverage html --rcfile "${BASE_DIR}/pyproject.toml"
