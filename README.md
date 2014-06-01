# Polefit Website

This is the codebase for the Polefit website, which is a Django site.

## Development

The simplest way to run this site for development is to install [Honcho](https://github.com/nickstenning/honcho).

Create a file in the top-level directory (the one containing this README file) called `.env` and paste in the following:

    DATABASE_URL=sqlite:///db.sqlite3
    SECRET_KEY=put-something-random-here-not-important-for-dev
    DEBUG=true

## Deploying to Heroku

This site is deployed as polefit.heroku.com.  Unfortunately, organisation
accounts cost money, so to deploy to Heroku, you will need the correct private
ssh key and ssh configuration to use it for heroku.com.  If you want Mark to
send it to you, you will need a Keybase account.

Once you have this stuff, you can deploy to heroku by running:

    git push heroku master

... but you'll probably need to do some other stuff with Heroku first.
