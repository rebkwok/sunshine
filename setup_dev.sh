#!/bin/bash

pip install -r requirements-dev.txt
cp polefit/dev_env polefit/.env
python manage.py migrate
python manage.py populatedb
python manage.py ensure_superuser
