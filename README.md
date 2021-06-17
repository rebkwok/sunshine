# Carousel Fitness Website

This is the codebase for the Carousel Fitness website, which is a Django site.

## Development

Requires Python 3.7+

Clone this repo and change directory to the cloned folder:

```
git clone https://rebkwok@bitbucket.org/markandbecky/polefit.git
cd polefit
```

Recommended: Create and activate a virtual env before setting up your local environment.

To install dev dependencies, run migrations, populate a test database and setup an admin user, run: 
```
./setup_dev
```

Run the django server:
```
python manage.py runserver
```

Access in a web browser at http://127.0.0.1:8000

To access the Django admin, go to http://127.0.0.1:8000/site-admin.  Login with username admin, password admin. 

