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

## Testing stripe payments locally

In the stripe dashboard, ensure you're using sandbox mode.

Find STRIPE_PUBLISHABLE_KEY (should start pk_test...), STRIPE_SECRET_KEY (sk_test_...) and STRIPE_CONNECT_CLIENT_ID (ca_...)
and add to .env folder.

Enable Oauth for Connect:
https://dashboard.stripe.com/test/settings/connect/onboarding-options/oauth
(https://dashboard.stripe.com/settings/connect/onboarding-options/oauth for non-sandbox)
Add callback URIs (assuming running local server on port 7100):
http://localhost:7100/payments/stripe/oauth/callback/ 
http://127.0.0.1:7100/payments/stripe/oauth/callback/ 

Connect an account: go to localhost http://localhost:7100/payments/stripe/connect
Click "skip this form" to connect to a dummy test connected account.

Use the stripe CLI to test webhooks:
```
stripe login
stripe accounts retrieve (to set your account API keys)
stripe config --list (to check)
stripe listen --forward-connect-to localhost:7100/payments/stripe/webhook/
```

It will print a webhook signing secret - add it to you .env's STRIPE_ENDPOINT_SECRET and restart the dev server. 