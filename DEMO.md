# UAH Alpha — Demo Guide

---

## Auth

- **Register** with email/password or OAuth (Google / LinkedIn)
- **Login**, logout, session auto-expires
- Email verification flow; password reset via email token
- Settings → change name, email, username, password, or delete account

---

## Resumes Tab

### Import flow (4 steps)

1. Drag-drop or browse a PDF (max 5 MB)
2. Confirm file, pick parse method — **AI (LLM)** or **Rules-based**
3. Progress bar with live stage labels (Queued → Parsing → Validating) + **Cancel** button
4. Resume appears in list with portal-readiness badge

### View a resume

- Opens modal with two sub-tabs
- **PDF Document** — inline iframe viewer of the original file
- **Parsed Data** — structured fields, portal readiness bar, missing-field pills, link to fill them in Applicant Info

### List actions

- View, Delete (double-confirm)
- Stats row: total resumes / portal-ready count / latest upload date

---

## Applicant Information Tab

- **Profile switcher** — multiple saved profiles, switch with a dropdown, create new, delete extras
- First visit auto-migrates any existing local data to your first backend profile
- Fields: personal info, address, summary, work authorization, education, experience, skills, certifications, links, demographics
- **Save All** button in top-right persists everything to the backend; also updates your display name

---

## Job Application Info Tab

- EEO self-identification: veteran status, disability status, California residency
- Saves directly to your active applicant profile

---

## Job Board Tab

- Browse live job listings (Muse API)
- Filter by keyword, location, category, experience level
- Save jobs to your account
- Apply button links out to the employer portal

---

## Settings

- Change name, email, username, password
- Email verification badge
- Delete account

---

## Demo Script — Things to Show

| # | Action | What to highlight |
|---|--------|-------------------|
| 1 | Upload a PDF | Watch the parse progress bar move through stages |
| 2 | Open View on a parsed resume | Switch between PDF tab and Parsed Data tab |
| 3 | Portal readiness bar | Show missing-field pills, click "Review Missing Fields" |
| 4 | Applicant Info | Create a second profile, switch to it, switch back |
| 5 | Save All | Show success feedback, name update reflects in navbar |
| 6 | Job Board | Search a keyword, save a job |
| 7 | Settings | Show account options |

---

## Known Alpha Limitations

- Legacy resumes uploaded before this build won't have a PDF tab — Parsed Data only
- AI parse can take 30–60 s on large PDFs — progress bar covers the wait
- No mobile-optimized layout yet
- Rules-based parser may miss fields on non-standard resume formats
