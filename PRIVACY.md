# UAH Privacy Policy

Last updated: 2026-04-28

Unified Application Hub (UAH) is a student-built, open-source project in active beta. This privacy policy explains what data we handle, why we handle it, and what choices you have.

UAH is an independent community project led by contributors; it is not an official university information system or an enterprise operated by any school — including the University of Massachusetts Lowell.

## TL;DR

- We do not sell your data.
- We do not share your data for advertising or data-broker purposes.
- Optional integrations stay opt-in.
- Cloud Parse is being phased out over time in favor of Local AI and Rules-based parsing.
- You can disconnect integrations and delete your data.

## Data We Collect

We collect the data needed to run UAH's account and job-application features:

- **Account data:** email, username, password hash, first/last name, auth metadata.
- **Resume data:** uploaded PDF, extracted OCR markdown, structured parsed resume fields.
- **Applicant profile data:** contact details, education, work history, skills, and related application profile fields you provide.
- **Application tracking data:** job title, company, platform, status, notes, and apply-session metadata.
- **Optional Gmail integration data:** Gmail account email label, encrypted refresh token (when connected), and Gmail message metadata/snippets used for status signals.

## How We Use Data

We use data only to operate product features you use, including:

- account access and security workflows,
- resume parsing and autofill preparation,
- application tracking and status organization,
- optional Gmail-based status update matching,
- reliability, debugging, and abuse prevention.

We do not use your personal data for ad targeting.

## Integrations and Processors

Depending on what you enable, UAH may send data to these providers:

- **Google OAuth / Gmail API (optional):** for connecting read-only Gmail access.
- **Cloud Parse provider (optional cloud mode):** resume content is sent for OCR/LLM parsing when Cloud AI is selected.
- **Local AI endpoints (optional local mode):** resume content is processed by your configured local pipeline.
- **Infrastructure services:** database, queueing, and transactional email providers used to run the app.

## Gmail Integration (Optional)

When Gmail is connected:

- Access scope is read-only Gmail mailbox access.
- UAH fetches selected message metadata (`Subject`, `From`, `Date`) and snippets for matching job updates.
- UAH stores an encrypted Gmail refresh token and mailbox label email while connected.
- Disconnecting Gmail clears stored token/email metadata in UAH and attempts token revocation with Google.

If you do not connect Gmail, UAH does not access your mailbox.

## Resume Parsing and Cloud Parse Transition

UAH supports three parse modes:

- **Rules-based**
- **Local AI**
- **Cloud AI (Cloud Parse)**

Current direction:

- Local AI and Rules-based parsing are the preferred path.
- Cloud Parse remains available as explicit opt-in during transition.
- Cloud Parse is being phased out over time.

Important transparency note: when Cloud Parse is selected, your resume content is transmitted to external cloud AI endpoints for processing. Deployed stacks may use inference vendors such as Z.ai for this path (URLs and credentials are configured per environment).

## Data Retention and Deletion

You can manage data through product controls:

- Disconnect Gmail from Settings.
- Delete uploaded resumes.
- Export all account data from Settings as a ZIP of CSV files (after re-authentication).
- Delete your account.

Deleting an account removes user-owned records through app deletion flows and cascading model relationships. Some limited deletion records may be retained only to enforce account-integrity constraints (for example, preventing immediate re-registration collisions).

## Security and Beta Reality

We use practical security controls suitable for an active beta (including encrypted storage of Gmail refresh tokens). UAH is still evolving, and we update this policy as behavior changes.

## Children

UAH is not intended for children under 13.

## Policy Changes

If data handling changes, we will update this document and corresponding public policy page so the change is visible and understandable.

## Contact

For privacy questions or requests:

- `privacy@uahapp.com`

