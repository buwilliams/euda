# Getting Started

Set up Euda for local development or deploy to your own server.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- API key for your LLM provider (see `.env.example` for supported providers)

## Local Development

```bash
# Clone the repository
git clone https://github.com/buwilliams/euda.git && cd euda

# Configure environment
cp .env.example .env
# Edit .env and add your LLM provider API key

# Install dependencies
uv sync

# Optional: Add alias for convenience
echo "alias euda='uv run euda'" >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc

# Set your password
euda set-password

# Start Euda (choose one)
euda core web     # Web UI at http://localhost:8000
euda core chat    # CLI chat interface
```

## Verify It Works

1. Open Chat tab
2. Send a message: "Hello, what can you do?"
3. Check Topics tab to see system topics
4. Ask: "Create a reminder to test Euda tomorrow"
5. Verify the reminder appears in Topics

## Usage

Commands below assume the alias. Without it, prefix with `uv run`.

```bash
euda core web                      # Web UI + agents
euda core chat                     # CLI chat + agents
euda core logs tail                # Stream log entries
euda core topics list              # List topics via CLI app
euda skills list                   # List skill apps

# Run tests
uv run pytest                      # unit + integration tests
uv run pytest tests/e2e/           # e2e UI tests (requires running server)
```

## Deploy to Server

Single-user, single-server architecture. Each user deploys their own instance.

**Recommended:** [DigitalOcean](https://digitalocean.com/) $6/month Basic Droplet (1 vCPU, 1GB RAM, 25GB SSD, Ubuntu 24.04 LTS)

```bash
# 1. Create Droplet and note the IP

# 2. Setup SSH keys (skip if you have keys)
ssh-keygen -t ed25519
ssh-copy-id root@<ip>

# 3. Add to .env
EUNO_SERVER=root@<ip>
# Add your LLM provider API key (at least one required)

# 4. Run setup (first time only)
euda server-setup

# 5. Deploy code and sync data
euda sync

# 6. Access at http://<ip>
```

**Syncing:** `euda sync` deploys code and syncs data bidirectionally. Use `--data-only` to skip code deployment. See [Contributing](6_contribute.md#syncing-data) for details.

## Next Steps

- [Contributing](6_contribute.md) — Learn how to extend and improve Euda
- [System](4_system.md) — Understand the architecture
- [Discord](https://discord.gg/5B9VdQ6vYP) — Join the community
