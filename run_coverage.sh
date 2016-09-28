coverage run --source=polefit,gallery,website,activitylog,booking,timetable,accounts,payments --omit=../*migrations*,../*tests*,../*wsgi*,../*__init__* manage.py test
coverage html
