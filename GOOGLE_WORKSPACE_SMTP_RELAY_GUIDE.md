# Google Workspace SMTP Relay Guide (Option B)

This guide configures **Google Workspace SMTP relay** so the UAH backend can send verification + password reset emails from `uahapp.com` **without storing a mailbox password** on the server.

## Goal

- Backend sends mail via `smtp-relay.gmail.com` (TLS)
- Google Admin allows relay only from your server IP(s)
- Domain is authenticated (SPF/DKIM/DMARC) to improve deliverability

---

## 1) Prereqs / Info You Need

Before starting, collect:

- **Server public egress IP** (recommended: a static IP)
  - If you use a cloud VM, this is usually its public IP.
  - If you’re behind NAT, use the NAT’s public IP.
- **Sender address** you will use in emails (recommended): `noreply@uahapp.com`
- Confirm you control DNS for `uahapp.com` (Cloudflare / Route53 / etc.)

---

## 2) Configure Google Workspace SMTP Relay

In **Google Admin Console**:

1. Go to: **Apps → Google Workspace → Gmail → Routing → SMTP relay service**
2. Click **Add setting** (or edit an existing relay)
3. Recommended settings:
   - **Allowed senders**: *Only addresses in my domains* (or restrict to `uahapp.com`)
   - **Authentication**:
     - Prefer: **Only accept mail from the specified IP addresses**
       - Add your backend server egress IP(s)
   - **Encryption**:
     - Require **TLS**
   - **Spam / rate controls**:
     - Keep defaults initially
4. Save

SMTP host/port you’ll use from the backend:
- Host: `smtp-relay.gmail.com`
- Port: `587`
- TLS: `true`

---

## 3) DNS: SPF / DKIM / DMARC (Deliverability)

### SPF
Add/confirm an SPF TXT record for `uahapp.com` that includes Google:

- Name/Host: `@`
- Type: `TXT`
- Value (example):

```
v=spf1 include:_spf.google.com ~all
```

If you already have SPF, **merge** entries (don’t create multiple SPF records).

### DKIM
In Google Admin:

1. **Apps → Google Workspace → Gmail → Authenticate email (DKIM)**
2. Select domain: `uahapp.com`
3. Generate DKIM record (Google provides selector + TXT value)
4. Add the TXT record in DNS
5. Return to Admin Console and click **Start authentication**

### DMARC
Add a DMARC TXT record (start in monitoring mode):

- Name/Host: `_dmarc`
- Type: `TXT`
- Value (starter example):

```
v=DMARC1; p=none; rua=mailto:admincontact@uahapp.com; adkim=s; aspf=s
```

After you confirm everything is behaving, you can move to `p=quarantine` or `p=reject`.

---

## 4) Configure UAH Backend Environment Variables

The backend supports SMTP relay via environment variables.

### Required env vars
Set these in the environment used by `docker compose` (usually a `.env` file next to `docker-compose.yml` on your server):

```env
# Enable real emails (otherwise API returns "dev only" tokens)
EMAILS_ENABLED=true

# Used to include a helpful link in email text
PUBLIC_APP_URL=https://uahapp.com

# Google Workspace SMTP relay
SMTP_HOST=smtp-relay.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false

# Sender shown to users
SMTP_FROM=UAH <noreply@uahapp.com>

# Using IP allowlist relay: leave these blank
SMTP_USERNAME=
SMTP_PASSWORD=

# Optional
SMTP_TIMEOUT_SECONDS=20
```

### Docker Compose wiring
The repo’s `docker-compose.yml` is already set up to pass these variables through to the backend container.

---

## 5) Validate: Send a Verification Email End-to-End

1. Deploy the backend with the env vars above.
2. Create/login to a user with an email address you can receive at.
3. In Settings → Email Verification → click **Send verification token**.
4. Expected result:
   - API response: **"Verification email sent"**
   - You receive an email containing a **verification token**
5. Paste the token into the Settings verification field and click **Verify email**.

Notes:
- The token is a JWT that expires after ~24 hours.
- If `EMAILS_ENABLED=false`, you will still see `Verification token (dev only): ...` in the UI.

---

## 6) Troubleshooting

### I still see “dev only” tokens
- Check `EMAILS_ENABLED=true` is present in the backend container environment.
- If using Docker: `docker exec <backend_container> env | grep EMAILS_ENABLED`

### Backend returns “Email not configured”
- Ensure `SMTP_HOST` and `SMTP_FROM` are set.

### Backend returns “Failed to send verification email”
Common causes:
- Your server egress IP is **not** allowlisted in SMTP relay
- TLS is required but you disabled it (`SMTP_USE_TLS` should be `true` on port 587)
- Google relay policy is too strict for the sender

### Email goes to spam
- Confirm SPF includes Google
- DKIM is started and passing
- DMARC exists

---

## Recommended Sender Address

Use a stable mailbox identity like:

- `noreply@uahapp.com` (verification/reset notifications)
- `security@uahapp.com` (security alerts)

Even with SMTP relay, you want these addresses to be valid within your Workspace domain.
