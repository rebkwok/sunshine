# Sunshine Fitness Website

This is the codebase for the Sunshine Fitness website, which is a Django site.

## Development

Requires Python 3.13+ and uv

Clone this repo and change directory to the cloned folder:

```
cd sunshine
```

Recommended: Create and activate a virtual env before setting up your local environment.

To install dev dependencies, run migrations, populate a test database and setup an admin user, run: 
```
./setup_dev
```

Run the django server:
```
uv run python manage.py runserver
```

Access in a web browser at http://127.0.0.1:8000

To access the Django admin, go to http://127.0.0.1:8000/site-admin.  Login with username admin, password admin. 

