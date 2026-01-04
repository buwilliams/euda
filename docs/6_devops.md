# DevOps

## Architecture

Euno uses a **single-user, single-server architecture**. Each user deploys their own instance to a personal VPS. There's no multi-tenant infrastructure—your data stays on your server.

```
┌─────────────────────────────────────────────────────────────┐
│                     Your VPS (Vultr)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  nginx (port 80)                                     │   │
│  │    ↓                                                 │   │
│  │  Euno (port 8000)                                    │   │
│  │    ├── Web UI (FastAPI + static files)              │   │
│  │    ├── Agents (background threads)                   │   │
│  │    └── SQLite database                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  /opt/euno/                                                 │
│    ├── main.py                                             │
│    ├── src/                                                │
│    ├── data/          ← Your personal data                 │
│    ├── venv/          ← Python virtual environment         │
│    └── .env           ← API keys                           │
└─────────────────────────────────────────────────────────────┘
```

## Hosting

**[Vultr](https://my.vultr.com/)** shared CPU servers:
- **$5/month** — 1 vCPU, 1 GB RAM, 25 GB SSD
- Good privacy policy, 30+ global locations
- Full root SSH access
- Simple hourly billing

This is more than enough for a single-user Euno instance. The main resource usage is LLM API calls, which happen externally.

**Stack:**
- **OS:** Ubuntu 22.04 LTS
- **Scripts:** Bash (all `devops/*.sh` scripts)
- **Web server:** nginx (reverse proxy)
- **Process manager:** systemd
- **Database:** SQLite (no external DB needed)

## Prerequisites

1. **Server** — Create a Vultr instance:
   - Choose "Cloud Compute - Shared CPU"
   - Select $5/month tier (1 CPU, 1GB RAM, 25GB)
   - Choose nearest location
   - Select Ubuntu 22.04 LTS
   - Deploy and note the IP address

2. **SSH key** — Generate one if you don't have it:
   ```bash
   ssh-keygen -t ed25519
   ```

   Copy your key to the server:
   ```bash
   ssh-copy-id root@<server-ip>
   ```

3. **Local .env** — Configure your environment:
   ```bash
   cp .env.example .env
   ```

   Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   EUNO_SERVER=root@<your-server-ip>
   ```

## Deployment Scripts

All scripts read `EUNO_SERVER` from `.env`, so you can run them without arguments.

### setup-server.sh

**First-time server setup.** Run once on a fresh server.

```bash
./devops/setup-server.sh
```

What it does:
1. Installs Python 3, pip, venv, git
2. Creates `/opt/euno` directory
3. Sets up Python virtual environment
4. Creates systemd service (`euno.service`)
5. Installs and configures nginx reverse proxy
6. Opens firewall ports 80/443

### deploy-euno.sh

**Deploy code to server.** Run after any code changes.

```bash
./devops/deploy-euno.sh
```

What it does:
1. Syncs code via rsync (excludes `data/`, `venv/`, `.git/`)
2. Copies `.env` file
3. Installs Python dependencies
4. Restarts the systemd service

The `data/` directory is **never overwritten** by deploy—your data stays intact.

### manage.sh

**Control the remote service.**

```bash
./devops/manage.sh status    # Check if running
./devops/manage.sh logs      # Follow live logs (Ctrl+C to exit)
./devops/manage.sh restart   # Restart service
./devops/manage.sh stop      # Stop service
./devops/manage.sh start     # Start service
```

### pull-data-remote.sh

**Download remote data to local machine.** Useful for local development with production data.

```bash
./devops/pull-data-remote.sh
```

What it does:
1. Backs up local `data/` to `data_backup-{timestamp}/`
2. Downloads remote `data/` via rsync

### push-data-remote.sh

**Upload local data to server.** Use carefully—this overwrites remote data.

```bash
./devops/push-data-remote.sh
```

What it does:
1. Backs up remote `data/` to `data_backup-{timestamp}/`
2. Uploads local `data/` via rsync

## Typical Workflow

### Initial Setup

```bash
# 1. Create Vultr server, note the IP address

# 2. Configure .env
echo "EUNO_SERVER=root@<ip>" >> .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# 3. Setup server (once)
./devops/setup-server.sh

# 4. Deploy code
./devops/deploy-euno.sh

# 5. Set password
ssh root@<ip> 'cd /opt/euno && ./venv/bin/python main.py set-password'

# 6. Access at http://<ip>
```

### Ongoing Development

```bash
# Make code changes locally, then:
./devops/deploy-euno.sh

# Check logs if something breaks:
./devops/manage.sh logs
```

### Working with Data

```bash
# Pull production data for local testing
./devops/pull-data-remote.sh

# Run locally
python main.py start

# If you need to push local data to production (rare)
./devops/push-data-remote.sh
```

## Service Management

The Euno service runs via systemd:

```bash
# On the server directly:
sudo systemctl status euno
sudo systemctl restart euno
sudo journalctl -u euno -f

# Or via manage.sh from local machine:
./devops/manage.sh status
./devops/manage.sh restart
./devops/manage.sh logs
```

## Security Notes

- **SSH keys only** — Password authentication should be disabled on the server
- **Password protection** — Set a password via `main.py set-password` to protect the web UI
- **No HTTPS by default** — For production, add Let's Encrypt via certbot
- **API keys in .env** — Never commit `.env` to git

## Adding HTTPS (Optional)

```bash
ssh root@<ip>

# Install certbot
apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
certbot --nginx -d euno.yourdomain.com

# Auto-renewal is configured automatically
```

## Troubleshooting

**Service won't start:**
```bash
./devops/manage.sh logs
# Look for Python errors, missing dependencies, etc.
```

**Can't connect to server:**
```bash
# Check SSH key is added to Vultr
ssh -v root@<ip>
```

**Changes not showing:**
```bash
# Force restart after deploy
./devops/manage.sh restart

# Clear browser cache (nginx caching disabled, but browser might cache)
```

**Out of disk space:**
```bash
ssh root@<ip>
df -h
# Clean up old backups in /opt/euno/data_backup-*
```
