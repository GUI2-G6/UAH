# Cloudflare And Tunnel Notes For Beta

This guide documents the current beta ingress posture at a high level.

## Current Repo-Managed Shape

The repository currently models beta ingress through a `cloudflared` tunnel container defined in `docker-compose.beta.yml`.

That means:

- the beta frontend joins the `cloudflared` network namespace
- the repo-managed beta path does not rely on publishing the frontend directly on a public host port
- Cloudflare-side policy still matters, but part of the public-exposure story now lives in tunnel configuration instead of only origin firewall rules

## What The Repo Can Prove

The repository can help prove:

- the beta override includes `cloudflared`
- the tunnel token is expected in env
- beta-specific hostnames and namespaces are configured
- the app itself disables generated docs in `ENVIRONMENT=beta`
- diagnostics stay admin-gated

## What Still Needs Manual Operator Review

The repo cannot fully prove these Cloudflare-side controls:

- Access / Zero Trust policy for who may enter beta
- WAF rules and rate limits
- DNS / hostname wiring in Cloudflare
- tunnel ownership, routing, and service mapping

Those should be reviewed alongside the repo-managed audit before inviting external testers.

## Practical Review Items

- Confirm the hostname used by `PUBLIC_APP_URL` matches the Cloudflare-routed beta hostname.
- Confirm the tunnel publishes the expected service only.
- Confirm beta access control is intentional for the audience you are inviting.
- Confirm Cloudflare-side rate limiting covers auth-sensitive routes.

## Related Docs

- [BETA_SETUP.md](BETA_SETUP.md)
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
- [../SECURITY_AUDIT_GUIDE.md](../SECURITY_AUDIT_GUIDE.md)
