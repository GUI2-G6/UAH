# Task: Sync .env.example with config.py

## Trigger
Run this task when the `ENV Example Sync Check` status check fails on a PR.

## What to do

1. Run the sync checker to see what is missing:
```bash
   python .github/scripts/check_env_sync.py --suggest
```

2. For each missing variable, add a documented entry to `.env.example`:
   - Add a `# comment` above it explaining what the variable does
   - Use an empty value or a safe placeholder (never a real secret)
   - Match the style of existing entries in the file
   - Place it in the correct logical section (Auth, Database, Email, etc.)

3. Check `backend/app/core/config.py` to understand:
   - Whether the variable has a default value (if so, use that as the placeholder)
   - Whether it is required (empty placeholder, note it is required)
   - What service or feature it configures

4. Commit the change with message:
   `docs: add missing env vars to .env.example`

## What NOT to do
- Do not add real secret values
- Do not remove existing entries
- Do not change variable names
- Do not modify config.py