# Migration Guide: Upgrading to RLM Architecture

This guide helps you upgrade an existing Euno installation to the new RLM (Recursive Language Model) architecture.

## What's New in RLM

The RLM branch introduces a major architectural change:

- **Long-term memory is now the primary store** - All agent memory is stored in long-term format
- **RLM-powered intelligent access** - Semantic search, pattern analysis, and identity extraction
- **New package manager** - Switched from `pip` to `uv` for faster, more reliable dependency management
- **`euno store` command** - Bulk import external files into long-term memory
- **Pattern recognition** - Automatic discovery and validation of behavioral patterns

## Before You Begin

**Requirements:**
- Existing Euno installation on a server
- SSH access to your server
- Backup of your data (script creates one automatically)

**Estimated time:** 5-10 minutes

## Step 1: Run Migration Script

The migration script prepares your server for the RLM upgrade:

```bash
cd /path/to/euno
./devops/migrate-to-rlm.sh root@your-server-ip
```

When prompted, type `yes` to confirm.

**What it does:**
1. Creates a backup of your data directory
2. Installs `uv` package manager
3. Updates systemd service configuration
4. Validates all changes

**Output should show:**
```
✓ All validation checks passed!
```

## Step 2: Deploy RLM Branch

After migration completes successfully:

```bash
git checkout rlm-memory  # Or your RLM branch name
git pull origin rlm-memory
./devops/deploy-euno.sh root@your-server-ip
```

**What it does:**
1. Syncs code to server
2. Updates system prompt templates
3. Installs dependencies with `uv`
4. Restarts the service

## Step 3: Verify Deployment

Check that the service is running:

```bash
ssh root@your-server-ip 'sudo systemctl status euno'
```

Should show:
```
Active: active (running)
```

Test chat functionality by visiting `http://your-server-ip` and sending a message.

## Troubleshooting

### Chat Returns "I had trouble processing that"

**Cause:** System prompt templates weren't updated

**Fix:**
```bash
scp data/system/prompts/agent/system.md root@your-server-ip:/opt/euno/data/system/prompts/agent/system.md
ssh root@your-server-ip 'sudo systemctl restart euno'
```

### Service Won't Start: "uv: command not found"

**Cause:** uv wasn't installed properly

**Fix:**
```bash
ssh root@your-server-ip 'curl -LsSf https://astral.sh/uv/install.sh | sh'
./devops/migrate-to-rlm.sh root@your-server-ip
```

### Import Error: "cannot import name 'read_long_term_memory'"

**Cause:** Code wasn't synced properly or you're on wrong branch

**Fix:**
```bash
git checkout rlm-memory
git pull origin rlm-memory
./devops/deploy-euno.sh root@your-server-ip
```

### Service Fails: "No module named 'src'"

**Cause:** Dependencies not installed with uv

**Fix:**
```bash
ssh root@your-server-ip 'cd /opt/euno && source ~/.local/bin/env && uv sync'
ssh root@your-server-ip 'sudo systemctl restart euno'
```

## Rollback

If you need to rollback to the previous version:

### Find Your Backup

```bash
ssh root@your-server-ip 'ls -la /opt/ | grep backup-rlm-migration'
```

### Restore Backup

```bash
# Replace TIMESTAMP with your actual backup timestamp
ssh root@your-server-ip 'sudo systemctl stop euno && \
  rm -rf /opt/euno/data && \
  cp -r /opt/data_backup-rlm-migration-TIMESTAMP /opt/euno/data && \
  sudo systemctl start euno'
```

### Switch Back to Main Branch

```bash
git checkout main
./devops/deploy-euno.sh root@your-server-ip
```

## Post-Migration Checklist

After successful deployment, verify:

- [ ] Service is running: `sudo systemctl status euno`
- [ ] Chat responds correctly (not showing error messages)
- [ ] Memory browsing works (can view long-term memory dates)
- [ ] Agents are running (check logs: `journalctl -u euno -f`)

## What Changed Under the Hood

### Package Management
- **Before:** `pip install -r requirements.txt` with venv
- **After:** `uv sync` with pyproject.toml

### Systemd Service
- **Before:** `ExecStart=/opt/euno/venv/bin/python main.py start`
- **After:** `ExecStart=/root/.local/bin/uv run euno start`

### Memory System
- **Before:** Separate short-term (JSONL) and long-term (markdown) stores
- **After:** Long-term memory as primary store with RLM-powered access

### System Prompts
- **Before:** `{profile}` and `{tools_by_type}` variables
- **After:** `{identity}`, `{user_identity}`, `{user_patterns}`, `{tools_by_type}` variables

## Getting Help

If you encounter issues not covered in this guide:

1. Check server logs: `ssh root@your-server-ip 'journalctl -u euno -n 100'`
2. Verify uv is installed: `ssh root@your-server-ip 'uv --version'`
3. Check service config: `ssh root@your-server-ip 'cat /etc/systemd/system/euno.service'`
4. Review template: `ssh root@your-server-ip 'cat /opt/euno/data/system/prompts/agent/system.md'`

Open an issue on GitHub with:
- Output from above commands
- Migration script output
- Deploy script output
- Any error messages from logs

## Next Steps

After successful migration:

- Explore the new `euno store` command to import existing files
- Try RLM-powered memory recall: `recall_memory("What did I do last week?")`
- Check discovered patterns in the UI
- Review the pattern recognition system in `spec/8_patterns.md`
