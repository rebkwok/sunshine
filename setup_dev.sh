#!/bin/bash

pip install -r requirements.txt
cp sunshine/dev_env sunshine/.env
python manage.py migrate
python manage.py populatedb
python manage.py ensure_superuser
