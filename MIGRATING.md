# Migrating to RLM Architecture

Quick guide for upgrading existing Euno installations to the RLM branch.

## TL;DR

```bash
# Step 1: Run migration script (prepares server)
./devops/migrate-to-rlm.sh root@your-server-ip

# Step 2: Deploy RLM branch
git checkout rlm-memory
./devops/deploy-euno.sh root@your-server-ip

# Step 3: Verify
ssh root@your-server-ip 'sudo systemctl status euno'
```

## What You Get

- 🧠 **RLM-powered memory** - Semantic search across long-term memory
- 📊 **Pattern recognition** - Automatic discovery of behavioral patterns
- 📥 **Bulk import** - `euno store` command for importing files
- ⚡ **Faster deploys** - uv package manager (10x faster than pip)

## What Changes

- Package manager: `pip` → `uv`
- Service config: Updated to use uv
- System prompts: New template variables
- Memory architecture: Long-term memory as primary store

## Safety

- Migration script creates automatic backup
- Safe to run multiple times (idempotent)
- Easy rollback process documented
- No data loss (templates updated, data preserved)

## Full Documentation

See [docs/migration-to-rlm.md](docs/migration-to-rlm.md) for:
- Detailed steps
- Troubleshooting guide
- Rollback instructions
- Architecture changes

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "I had trouble processing that" | Run deploy script again (templates need sync) |
| "uv: command not found" | Run migration script first |
| Import errors | Ensure you're on `rlm-memory` branch |
| Service won't start | Check logs: `journalctl -u euno -n 50` |

## Questions?

Open an issue on GitHub or check the full migration guide.
