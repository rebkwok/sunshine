# Polefit Website

This is the codebase for the Polefit website, which is a Django site.

## Development

The simplest way to run this site for development is to install [Honcho](https://github.com/nickstenning/honcho).

Create a file in the top-level directory (the one containing this README file) called `.env` and paste in the following:

    DATABASE_URL=sqlite:///db.sqlite3
    SECRET_KEY=put-something-random-here-not-important-for-dev
    DEBUG=true

# Deployment

Ansible deployment for this (and other sites) is configured in this repository (and should probably be extracted).

## Testing deployment

A Vagrantfile is provided that will provision a Vagrant VM as a production-like machine.

* Create a file called `.vaultpass` containing the ansible-vault file's password.
* Run `vagrant up` (or `vagrant provision`)

## Deploying to EC2

**Always test with Vagrant before running against EC2.**

On a new server, the following will be required:

## To Do

* Configure logging in some way for uwsgi
* Configure uwsgi to run in emperor mode.
* Modify manage.py so that it automatically loads in envdir
