# Contributing

A practical guide to contributing to Euno.

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/buwilliams/euno.git
   cd euno
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Add your API key to `.env`:**
   ```
   OPENAI_API_KEY=your-key-here
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run Euno:**
   ```bash
   python main.py start    # Web server + agents
   ```

6. **Open Euno:** [localhost:8000](http://localhost:8000)

## Feature Branches

All work happens on feature branches, never directly on main.

**Branch naming:**
- `feature/short-description` — New features
- `fix/short-description` — Bug fixes
- `docs/short-description` — Documentation changes
- `refactor/short-description` — Code refactoring

**Creating a branch:**
```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature
```

## Pull Request Process

1. **Do the work** — Complete your feature, fix, or documentation
2. **Review against spec** — Run drift detection (see below)
3. **Update your contrib file** — Add an entry in `contrib/your-name.md`
4. **Push and create PR:**
   ```bash
   git push -u origin feature/my-feature
   gh pr create --title "Add my feature" --body "Description of changes"
   ```
5. **Get approval** — Repository administrators must approve merges into main

## Reviewing Your Branch

Before submitting a PR, review your changes against the spec files to detect implementation drift.

**Using Claude Code:**
```bash
# In the project directory, run Claude Code and ask:
"Review my changes against spec/*.md and identify any drift from the design rules"
```

**What to check:**
- `spec/1_agents.md` — Agent behavior, job coordination, triggers, work cycles
- `spec/2_data.md` — Data structures, file paths, schemas
- `spec/3_backend.md` — Server, API, authentication, storage
- `spec/4_ux_ui.md` — User experience and interface patterns
- `spec/5_cli.md` — Command-line interface commands and behavior

**Common drift issues:**
- Adding files outside the expected `data/` structure
- Changing tool names without updating agent configs
- Adding UI patterns that violate UX rules (nested modals, tabs within tabs)

## Deployment

Euno uses a **single-user, single-server architecture**. Each user deploys their own instance.

### Architecture

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

### Hosting

**[Vultr](https://my.vultr.com/)** shared CPU servers:
- **$5/month** — 1 vCPU, 1 GB RAM, 25 GB SSD
- Good privacy policy, 30+ global locations

**Stack:** Ubuntu 22.04 LTS, nginx, systemd, SQLite

### Server Setup

1. Create a Vultr server, note the IP address
2. Setup SSH keys (skip if you already have keys):
   ```bash
   ssh-keygen -t ed25519
   ssh-copy-id root@<ip>
   ```
3. Add to `.env`:
   ```bash
   EUNO_SERVER=root@<ip>
   OPENAI_API_KEY=sk-...
   ```
4. Run setup: `./devops/setup-server.sh`
5. Deploy code: `./devops/deploy-euno.sh`
6. Set password: `ssh root@<ip> 'cd /opt/euno && ./venv/bin/python main.py set-password'`
7. Access at `http://<ip>`

### Deployment Scripts

All scripts read `EUNO_SERVER` from `.env`.

| Script | Purpose |
|--------|---------|
| `./devops/setup-server.sh` | First-time server setup |
| `./devops/deploy-euno.sh` | Deploy code changes |
| `./devops/manage.sh status` | Check service status |
| `./devops/manage.sh logs` | Follow live logs |
| `./devops/manage.sh restart` | Restart service |
| `./devops/pull-data-remote.sh` | Download remote data |
| `./devops/push-data-remote.sh` | Upload local data |

The `data/` directory is **never overwritten** by deploy—your data stays intact.

### Adding HTTPS

```bash
ssh root@<ip>
apt install certbot python3-certbot-nginx
certbot --nginx -d euno.yourdomain.com
```

## Related Documents

- [Contribution Points](5_points.md) — How points and rewards work
- [Business Plan](2_business-plan.md) — Vision and growth gates
- [Operating Agreement](6_operating-agreement.md) — Ownership and governance
