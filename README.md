# Polefit Website

This is the codebase for the Polefit website, which is a Django site.

## Development

The simplest way to run this site for development is to install [Honcho](https://github.com/nickstenning/honcho).

Create a file in the top-level directory (the one containing this README file) called `.env` and paste in the following:

    DATABASE_URL=sqlite:///db.sqlite3
    SECRET_KEY=put-something-random-here-not-important-for-dev
    DEBUG=true

## Deploying to EC2

On a new server, the following will be required:

create `/opt/sites/<site>/envdir/SECRET_KEY`

run

    source venv/bin/activate
    envdir envdir ./manage.py syncdb
    envdir envdir ./manage.py collectstatic
    # ... and any other manage commands you need
    touch /etc/uwsgi/<site>.ini

## To Do

* Configure logging in some way for uwsgi
* Move the ssh keys into the vault.
* Configure uwsgi to run in emperor mode.
* Modify manage.py so that it automatically loads in envdir
