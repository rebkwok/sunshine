#!/bin/bash

cp sunshine/dev_env sunshine/.env
uv run python manage.py migrate
uv run python manage.py populatedb
uv run python manage.py ensure_superuser
