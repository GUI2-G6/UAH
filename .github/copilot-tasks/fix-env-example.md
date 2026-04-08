# Task: Sync env-examples/dev/.env.example with config.py

## Trigger
Run this task when the `ENV Example Sync Check` status check fails on a PR.

## What to do

1. Run the sync checker to see what is missing:
```bash
   python .github/scripts/check_env_sync.py --template dev --suggest
   python .github/scripts/check_env_sync.py --template beta --suggest
```

2. For each missing variable, add a documented entry to the matching canonical template:
   - `env-examples/dev/.env.example`
   - `env-examples/beta/.env.example`
   - Add a `# comment` above it explaining what the variable does
   - Use an empty value or a safe placeholder (never a real secret)
   - Match the style of existing entries in the file
   - Place it in the correct logical section (Auth, Database, Email, etc.)

3. Check `backend/app/core/config.py` to understand:
   - Whether the variable has a default value (if so, use that as the placeholder)
   - Whether it is required (empty placeholder, note it is required)
   - What service or feature it configures

4. Commit the change with message:
   `docs: sync env vars in env-examples templates`

## What NOT to do
- Do not add real secret values
- Do not remove existing entries
- Do not change variable names
- Do not modify config.py
- Do not place runtime `.env` in `env-examples/`; runtime file belongs at repo root (`./.env`)