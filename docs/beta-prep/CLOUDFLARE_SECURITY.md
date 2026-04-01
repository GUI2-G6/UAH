# Cloudflare Security Configuration Guide

**Domain:** `beta.uahapp.com`  
**For:** Team members with Cloudflare access to the `uahapp.com` zone  
**Intent:** This guide describes *what to configure and why* — not the specific conditions, IP ranges, or rule logic that would expose the security posture.

---

## Overview

All traffic to `beta.uahapp.com` must route through Cloudflare. The origin server is never exposed directly to the internet. Cloudflare provides:

- Reverse proxy and DDoS protection (orange-cloud proxy)
- Zero Trust access control (authentication before the app is reached)
- WAF (web application firewall) with managed rules
- Rate limiting on sensitive endpoints
- TLS termination and HTTPS enforcement

---

## Section 1 — Cloudflare Proxy (Orange Cloud)

### 1.1 Confirm the DNS Record Is Proxied

In the Cloudflare dashboard for `uahapp.com`:

1. Go to **DNS → Records**
2. Find or create the A record for `beta.uahapp.com` pointing to the origin server IP
3. The **Proxy status** column must show the orange cloud icon (Proxied), not the grey cloud (DNS only)
4. If it is grey, click the record, toggle proxy to **Proxied**, and save

All traffic to `beta.uahapp.com` will now route through Cloudflare's network. The origin server's IP address will not appear in DNS lookups for this subdomain.

### 1.2 Block Direct-to-Origin IP Access

Even with Cloudflare proxying active, an attacker who discovers the origin server IP can bypass Cloudflare by sending requests directly to that IP. To prevent this, configure the origin server's host firewall to only accept inbound HTTP/HTTPS traffic from Cloudflare's IP ranges.

**How to do this:**

1. Retrieve the current list of Cloudflare's IP ranges from the official source:  
   [https://www.cloudflare.com/ips/](https://www.cloudflare.com/ips/)  
   Do not embed this list in this document or any configuration file — the list is maintained by Cloudflare and must be fetched fresh when applied.

2. Update the host's firewall rules (iptables, ufw, or cloud security group) to:
   - Allow inbound TCP on port 80 from Cloudflare IP ranges only
   - Drop all other inbound TCP on port 80
   - Keep port 22 (SSH) restricted to the team's management IP(s) — not from Cloudflare

3. Confirm no other ports are accessible from the public internet. Specifically:
   - Port 5432 (Postgres) — must be blocked
   - Port 8000 (FastAPI backend) — must be blocked
   - WireGuard port (if present from dev deployment) — must be blocked or restricted

4. After applying firewall rules, test by attempting to access the origin IP directly on port 80 from an IP that is not in Cloudflare's range — the connection should be refused.

### 1.3 Origin-Only Ports

The only port that the public Cloudflare proxy touches on the origin is port 80. All other service ports (database, backend API) are internal to Docker and must never be exposed on the host.

---

## Section 2 — Cloudflare Zero Trust Access Policy

The Cloudflare Access policy sits in **front of the entire `beta.uahapp.com` subdomain**. Any visitor who navigates to any path on `beta.uahapp.com` will be intercepted by Cloudflare Access and must authenticate before they can reach the application at all.

This is the same pattern used for the team's VPN portal.

### 2.1 Create a Cloudflare Access Application

1. In the Cloudflare dashboard, navigate to **Zero Trust → Access → Applications**
2. Click **Add an application** → select **Self-hosted**
3. Configure:
   - **Application name:** UAH Beta
   - **Application domain:** `beta.uahapp.com` (covers all paths)
   - **Session duration:** Set to a value appropriate for a testing session (e.g., 24 hours)
4. Click **Next**

### 2.2 Create an Access Policy

1. Name the policy (e.g., "Approved Testers")
2. Set **Action** to **Allow**
3. Under **Include**, select **Emails** as the rule type
4. Enter the approved email addresses for testers, graders, and team members
5. Do not document the approved email list in this guide or in any repository file
6. Click **Save**

The allowed authentication methods are configured under **Login methods** on the Access application. Enable **One-time PIN** (email-based) so approved users receive a PIN to their email address — no additional account creation required.

### 2.3 Adding and Removing Approved Emails

To **add** a tester:

1. Go to **Zero Trust → Access → Applications → UAH Beta → Edit policy**
2. Under **Include → Emails**, add the new email address
3. Save the policy

To **remove** a tester:

1. Go to **Zero Trust → Access → Applications → UAH Beta → Edit policy**
2. Under **Include → Emails**, remove the email address
3. Save the policy
4. If the person has an active session, go to **Zero Trust → Access → Active Sessions** and revoke their session

### 2.4 Temporary Time-Limited Access

For a testing session that should have a defined end time:

1. Create a separate Access policy scoped to the testing period:
   - Set the policy's **Session duration** to match the testing window
   - Add the tester's email to this policy
2. After the testing session ends, edit the policy to remove the email, or delete the temporary policy entirely
3. Optionally, manually revoke any active sessions from **Zero Trust → Access → Active Sessions**

Alternatively, use a **service token** for programmatic or automated testing:

1. Go to **Zero Trust → Access → Service Tokens**
2. Create a token with an explicit expiration
3. Provide the token to the tester
4. After the session, delete the service token — it will immediately invalidate access

### 2.5 Confirming the Access Policy Is Active

After configuring:

1. Open a private/incognito browser window
2. Navigate to `https://beta.uahapp.com`
3. You should be redirected to the Cloudflare Access authentication page before seeing the app
4. Complete authentication with an approved email — confirm access is granted
5. Try with an unapproved email — confirm access is denied

---

## Section 3 — WAF and Rate Limiting

### 3.1 Enable the WAF Managed Ruleset

1. In the Cloudflare dashboard, go to **Security → WAF**
2. Under **Managed rules**, enable the **Cloudflare Managed Ruleset**
3. Set the ruleset action to **Block** (not just Log) once you have confirmed it does not block legitimate traffic
4. Enable the **Cloudflare OWASP Core Ruleset** as well, starting in **Log** mode before switching to **Block**

**Recommendation:** Run the WAF in Log mode for the first 24–48 hours of beta and review the security events before switching to Block mode. This prevents false positives from blocking legitimate testers.

### 3.2 Rate Limiting Rules

Create rate limiting rules under **Security → WAF → Rate limiting rules** for the following endpoint groups:

**Authentication endpoints** (`/api/auth/*`):
- Intent: Prevent brute-force login and registration attempts
- Set a threshold appropriate for normal human login behavior
- Action: Block, with a duration that deters automated attempts without affecting real users

**Password reset** (`/api/account/forgot-password`):
- Intent: Prevent automated email flooding via the password reset flow
- Set a low threshold — legitimate users rarely trigger this endpoint more than once per session
- Action: Block

**Email verification** (`/api/account/send-verification`):
- Intent: Prevent email spam via the verification resend endpoint
- Set a per-IP threshold similar to password reset
- Action: Block

Do not document specific threshold values (requests per second/minute) or the exact matching conditions in this guide.

### 3.3 Bot Fight Mode

1. Go to **Security → Bots**
2. Enable **Bot Fight Mode**

This blocks known bad bots from reaching the origin. Note that Cloudflare Access authentication already prevents most automated access, but Bot Fight Mode adds an additional layer before the Access gate.

---

## Section 4 — SSL/TLS Configuration

### 4.1 Set TLS Mode to Full (Strict)

1. Go to **SSL/TLS → Overview**
2. Set the encryption mode to **Full (strict)**

Full (strict) requires that the origin server presents a valid certificate. Either:
- Use a **Cloudflare Origin Certificate** (recommended — generated in the Cloudflare dashboard and trusted by Cloudflare's proxy) and configure the Nginx container to use it, or
- Use a Let's Encrypt certificate on the origin

With Full (strict), Cloudflare will not proxy traffic to an origin that presents an untrusted or self-signed certificate.

**Note:** If using the current `DEV_TLS_ENABLED=false` config (Nginx serving plain HTTP), you must enable `DEV_TLS_ENABLED=true` and provision an origin certificate before switching to Full (strict). Alternatively, Cloudflare's **Full** mode (not strict) allows plain HTTP to the origin — but Full (strict) is the required setting for beta.

### 4.2 Enable HSTS

1. Go to **SSL/TLS → Edge Certificates**
2. Under **HTTP Strict Transport Security (HSTS)**, click **Enable HSTS**
3. Configure:
   - **Max Age:** 6 months (15552000 seconds) or longer
   - **Include subdomains:** Optional — only enable if all subdomains of `uahapp.com` serve HTTPS
   - **Preload:** Only enable after the deployment has been stable for some time

HSTS instructs browsers to always use HTTPS for this domain and refuse plaintext connections.

### 4.3 Minimum TLS Version

1. Go to **SSL/TLS → Edge Certificates**
2. Under **Minimum TLS Version**, select **TLS 1.2**

This ensures that older, insecure TLS versions (1.0, 1.1) are not negotiated with browsers.

---

## What This Guide Intentionally Does Not Include

This guide is written for developers with legitimate access. It intentionally omits the following to avoid creating an attack profile:

- The origin server's IP address
- The specific Cloudflare IP ranges to use in firewall rules (link provided instead)
- The list of approved email addresses for the Access policy
- Specific rate limit thresholds or request counts
- Any conditions under which the Access policy can be bypassed
- Any service token values or bypass headers

If you need any of the above, they are stored in the team's secret manager, not in this repository.
