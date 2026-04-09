# UAH Dev Workflow — Branches, Issues, and Pull Requests

This guide covers the full loop from picking up an issue to getting your code into `dev`.
Follow this every time. It keeps everything logged, traceable, and clean.

---

## The Core Rule

**Every code change goes through a PR. Every PR closes an issue.**

No direct pushes to `dev`. No PRs without a linked issue.
This is how we keep the board accurate and the history readable.

---

## Step 1 — Pick Up an Issue

1. Go to the [Issues board](https://github.com/GUI2-G6/UAH/issues)
2. Find an open issue assigned to you (or assign yourself to one that needs an owner)
3. Read the full issue — acceptance criteria, dependencies, due date
4. If something is unclear, **comment on the issue** before writing any code
   - Tag @TrentBrownUML or the relevant assignee
   - Don't guess and submit a PR that misses the point

---

## Step 2 — Create Your Branch

Branch off `dev`. Never branch off `prod` or `beta`.
```bash
git checkout dev
git pull origin dev        # Always pull latest before branching
git checkout -b fix/pdf-viewer-auth
```

**Branch naming:**

| Type | Format | Example |
|---|---|---|
| Bug fix | `fix/short-description` | `fix/pdf-viewer-auth` |
| New feature | `feature/short-description` | `feature/gmail-oauth-scope` |
| Chore / infra | `chore/short-description` | `chore/update-env-example` |
| Documentation | `docs/short-description` | `docs/beta-setup-guide` |

Keep it lowercase and hyphenated. Short and descriptive.

---

## Step 3 — Do the Work

- Make your changes in focused commits
- Commit messages should describe **what changed and why**:
```
  ✅  Fix PDF viewer by fetching blob with auth token
  ✅  Add get_current_user dependency to /api/jobs/save
  ❌  fix stuff
  ❌  wip
```
- Push your branch to origin as you go:
```bash
  git push origin fix/pdf-viewer-auth
```
- **Never commit `.env` files.** If you add a new env var, add it to `env-examples/dev/.env.example` with a description.

---

## Step 4 — Open a Pull Request

When your work is ready:

1. Go to [github.com/GUI2-G6/UAH/pulls](https://github.com/GUI2-G6/UAH/pulls)
2. Click **New pull request**
3. Set base branch to **`dev`**, compare branch to your feature branch
4. Click **Create pull request**

**Fill out the PR template completely.** Every field matters.

The most important line is:
```
Closes #XX
```
Replace `XX` with the issue number this PR resolves.
This is what links the PR to the issue and auto-closes the issue when merged.

---

## Step 5 — PR Template Walkthrough

Here's what each section means and what to put:
```markdown
## What does this PR do?
```
One clear paragraph. What problem does this solve? What did you change?
Example: *"Fixes the PDF viewer returning 401 by fetching the PDF as an authenticated blob 
instead of a bare iframe src, then creating a temporary object URL for rendering."*

---
```markdown
## Related Issue
Closes #49
```
Use `Closes #XX` — this is the magic phrase that links and auto-closes the issue on merge.
If you're partially addressing an issue: use `Addresses #XX` instead so it doesn't auto-close.

---
```markdown
## Type of Change
- [x] Bug fix
```
Check every box that applies. More than one is fine.

---
```markdown
## How was this tested?
- [x] Tested locally
```
Check what you actually did. Then describe it:
*"Uploaded 3 different resumes, confirmed PDF renders in modal for all 3. 
Confirmed unauthenticated request returns 401."*

Don't leave the description blank — this tells the reviewer what to look for.

---
```markdown
## Checklist
- [x] No .env files or secrets committed
- [x] No console.log or debug code left in
- [x] PR title clearly describes the change
- [x] Linked to the correct issue above
```
Go through this honestly before opening the PR. 
If you added a new env var, check `env-examples/dev/.env.example` is updated before checking that box.

---
```markdown
## Notes for Reviewer
```
Anything the reviewer should pay attention to. 
Flag anything you're unsure about, any side effects, or any follow-up issues that should be created.
If there's nothing to note, write "None."

---

## Step 6 — Link the Issue to the PR

After opening the PR:

1. On the right sidebar of the PR, scroll to **Development**
2. Click the gear icon
3. Search for and select the issue this PR closes
4. This creates a visible link between the PR and the issue

The issue will also show the linked PR on its own page under **Development**.

**The issue should show this when done correctly:**
- PR linked under Development section
- PR title visible on the issue page
- When PR merges → issue auto-closes

---

## Step 7 — Assign and Milestone

On the PR sidebar:

- **Assignees:** Add yourself (and anyone else who worked on it)
- **Milestone:** Set to **BETA** (or whichever milestone the linked issue belongs to)
- **Labels:** Match the labels on the linked issue

---

## Step 8 — Copilot Review

Copilot code review is enabled on this repo and will automatically review your PR.
It may leave comments — read them. Some will be useful, some won't apply.

You don't need to resolve every Copilot comment before merging to `dev`,
but if it flags something clearly wrong (like a security issue or a broken suggestion),
either fix it or leave a reply explaining why you're not acting on it.

---

## Step 9 — Merge

For `dev`, **no human review approval is required** — you can merge your own PR once:

- [ ] The PR template is fully filled out
- [ ] The issue is linked with `Closes #XX`
- [ ] All checklist items are checked
- [ ] No merge conflicts with `dev`
- [ ] Copilot review has completed (doesn't need to be all-clear, just done)

To merge:
1. Click **Squash and merge** (preferred — keeps `dev` history clean)
   OR **Merge pull request** if you want to preserve individual commits
2. Edit the merge commit message if needed — make it clear
3. Click **Confirm merge**
4. Delete the branch when prompted — keeps the repo tidy

The linked issue will automatically close. ✅

---

## Full Example Walkthrough

**Issue #49 — Bug: PDF Viewer Returns "Not Authenticated"**
```bash
# 1. Pull latest dev
git checkout dev
git pull origin dev

# 2. Create branch
git checkout -b fix/pdf-viewer-auth

# 3. Make the fix
# ... edit frontend file to fetch PDF as authenticated blob ...

# 4. Commit
git add frontend/src/components/ResumeViewer.vue
git commit -m "Fix PDF viewer by fetching blob with auth token instead of bare iframe src"

# 5. Push
git push origin fix/pdf-viewer-auth

# 6. Open PR on GitHub
# Base: dev  ←  Compare: fix/pdf-viewer-auth
# Title: "Fix PDF viewer auth — fetch blob with token"
# Fill out template, add: Closes #49
# Assign yourself, set milestone to BETA

# 7. Wait for Copilot review to complete
# Read comments, address anything real

# 8. Merge → issue #49 auto-closes
# Delete branch
```

---

## Quick Reference

| Step | Action |
|---|---|
| Pick up work | Assign yourself to an issue, comment if unclear |
| Branch | `git checkout -b fix/description` off `dev` |
| Commit | Clear present-tense messages |
| Open PR | Base = `dev`, fill template completely |
| Link issue | `Closes #XX` in PR description + Development sidebar |
| Assign | Add yourself, set milestone, match labels |
| Merge | Squash and merge, delete branch |

---

## What a Properly Closed Issue Looks Like

When everything is done right, the closed issue will show:
- Status: **Closed as completed**
- A linked PR under **Development**
- The PR title visible on the issue page
- The issue was closed by the merge commit, not manually

And the PR will show:
- **Merged** status
- `Successfully merging this pull request may close these issues → [Issue Title]`
- All template sections filled in
- Copilot review completed
- Branch deleted

---

## Common Mistakes to Avoid

| Mistake | What to do instead |
|---|---|
| Pushing directly to `dev` | Always create a branch, open a PR |
| Opening a PR without `Closes #XX` | Add the closes link — issue won't auto-close without it |
| Leaving PR template blank | Fill it out — it's 2 minutes and saves everyone confusion |
| Committing `.env` | Check `git status` before every commit |
| Branching off `prod` or `beta` | Always branch off `dev` |
| Merging without checking Copilot review | Wait for it to complete, read the comments |
| Not deleting the branch after merge | Delete it — keeps the branch list clean |