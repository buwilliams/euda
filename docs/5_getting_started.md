# Getting Started

Set up Euno for local development or deploy to your own server.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key

## Local Development

```bash
# Clone the repository
git clone https://github.com/buwilliams/euno.git && cd euno

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Install dependencies
uv sync

# Optional: Add alias for convenience
echo "alias euno='uv run euno'" >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc

# Set your password
euno set-password

# Start Euno (choose one)
euno web     # Web UI at http://localhost:8000
euno chat    # CLI chat interface
```

## Verify It Works

1. Open Chat tab
2. Send a message: "Hello, what can you do?"
3. Check Topics tab to see system topics
4. Ask: "Create a reminder to test Euno tomorrow"
5. Verify the reminder appears in Topics

## Usage

Commands below assume the alias. Without it, prefix with `uv run`.

```bash
euno web                           # Web UI + agents
euno chat                          # CLI chat + agents
euno dev watch                     # Stream all system events
euno dev memory chat               # View agent's memory
euno skills core topics list       # List topics via skill

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
OPENAI_API_KEY=sk-...

# 4. Run setup and deploy
./devops/setup-server.sh
./devops/deploy-euno.sh

# 5. Push data to server
euno sync --push

# 6. Access at http://<ip>
```

**Syncing data:** Use `euno sync` to keep local and remote in sync. See [Contributing](6_contribute.md#syncing-data) for details.

## Next Steps

- [Contributing](6_contribute.md) — Learn how to extend and improve Euno
- [System](4_system.md) — Understand the architecture
- [Discord](https://discord.gg/5B9VdQ6vYP) — Join the community
