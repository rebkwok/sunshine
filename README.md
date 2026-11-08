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

Only one account can be connected at a time; disconnect it at
http://localhost:7100/payments/stripe/disconnect/ to connect a different one. The connect pages are for superusers.

In production, set STRIPE_CONNECT_PAGES_ENABLED=False in .env once the account is connected, to disable the
connect and disconnect pages. To connect a different account, enable them again and restart the server.

Use the stripe CLI to test webhooks:
```
stripe login
stripe accounts retrieve (to set your account API keys)
stripe config --list (to check)
stripe listen --latest \
  --events payment_intent.succeeded,payment_intent.payment_failed,payment_intent.requires_action,charge.refunded,account.application.authorized,account.application.deauthorized \
  --forward-connect-to localhost:7100/payments/stripe/webhook/
```

It will print a webhook signing secret - add it to you .env's STRIPE_ENDPOINT_SECRET and restart the dev server.

`--latest` sends events in the latest API version. Without it, they use the account's default API version.

### Testing with a real sandbox webhook

`stripe listen` can't send events in a specific API version. To test with the same API version as the live
webhook endpoint, use a sandbox webhook endpoint with a zrok tunnel to the local server.

Set up the zrok namespace (only needed once):
```
zrok2 create name sunshine
```

Run the tunnel, and note the public URL:
```
zrok2 share public localhost:7100 -n public:sunshine
```

In the stripe dashboard in sandbox mode, add a webhook endpoint:
- Listen to events on connected accounts
- Use the same API version and events as the live webhook endpoint
- Set the URL to `<zrok public URL>/payments/stripe/webhook/`

Add the endpoint's signing secret to your .env's STRIPE_ENDPOINT_SECRET and restart the dev server. Use this secret
instead of the one from `stripe listen`, and stop `stripe listen` if it's running.

The tunnel needs `LOCAL` set in your .env, so that the dev server accepts the zrok host. Disable the webhook endpoint
when you've finished testing.

### Test cards

In sandbox mode, use any future expiry date, any CVC and any postcode with these card numbers:

| Card number | Result |
|---|---|
| `4242 4242 4242 4242` | Payment succeeds |
| `4000 0025 0000 3155` | Asks for 3D Secure authentication; choose to complete or fail it |
| `4000 0000 0000 0002` | Payment is declined |

To test a refund, cancel a paid booking. A failed or declined payment should be logged, with no failure email to
support.

See https://docs.stripe.com/testing for more test cards.
