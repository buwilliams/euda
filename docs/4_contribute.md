# Contributing

## What is Euno?

Euno is not a personal assistant—it's proactive, not reactive. Think of it like a genie that grants *eudaimonia* instead of wishes. It studies your life to help you flourish on your own terms: clearing the path, noticing patterns you can't see, and shielding you from distractions.

## How to Think About Contributions

Don't think about what other people want. Think about what *you* want.

Euno's mission is: *A deep sense of fulfillment achieved through virtuous living, developing one's potential, and engaging in meaningful activities.*

Ask yourself:
- **What would be useful to me?** What friction in your life could Euno reduce? What tasks drain your energy that a proactive intelligence could handle?
- **What would help me live a virtuous life?** What habits do you want to build? What temptations pull you away from who you want to be? How could Euno help you stay aligned with your values?
- **What would help me develop my potential?** What skills are you trying to build? What goals have you been putting off? How could Euno keep you accountable and moving forward?
- **What would help me have meaningful activities and connections?** What relationships matter most? What activities bring you alive? How could Euno help you prioritize these over the noise?

The best contributions come from lived experience. Build for yourself first. If it helps you flourish, it will help others too.

## Getting Started

1. Clone: `git clone https://github.com/buwilliams/euno.git && cd euno`
2. Setup: `cp .env.example .env` and add your API key
3. Install: `pip install -r requirements.txt`
4. Set password: `python main.py set-password`
5. Run: `python main.py start`
6. Open: [localhost:8000](http://localhost:8000)

## Your First Contributions

Complete these three assignments to learn how Euno works:

### Assignment 1: Use the System

Experience Euno as a user before contributing code.

**Tasks:**
1. Open Chat and introduce yourself
2. Ask Chat to create a reminder for tomorrow
3. Explore the Jobs view - see your reminder appear
4. Check the Timeline views (Today, Upcoming, Anytime, Someday)
5. Look at your User Profile - see what Euno knows about you

**What you'll learn:** How users interact with Euno, the job system, and how Chat manages tasks.

### Assignment 2: Create a New Agent

Learn how agents work by creating one through Chat.

**Example prompt to Chat:**
> "Create a social-media agent that goes out to the internet daily and finds interesting content I'd enjoy based on my profile. It should run exploration every morning."

**What Chat will do:**
1. Create the agent's config.json with tools and triggers
2. Generate a profile.md with purpose and behavioral rules
3. Set up exploration if requested
4. The agent appears after you restart Euno

**What you'll learn:** Agent architecture, configuration, profiles, and the agent lifecycle.

### Assignment 3: Contribute to the Backlog

Find real work to contribute.

1. Visit [GitHub Projects - Euno](https://github.com/users/buwilliams/projects/2)
2. Pick an issue from the backlog
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Complete your work
5. Review against `spec/*.md` for drift
6. Add entry to `contrib/your-name.md`: `- [YYYY-MM-DD][--] Description`
7. Push and create PR

## Agent Library

Pre-built agents are available in `agent-lib/`. To install one:
> "Install the fun agent from agent-lib"

To contribute a new agent template, create it via Chat, test it, then copy the config.json and profile.md to `agent-lib/your-agent/`.

## Pull Request Guidelines

1. Create a feature branch from main
2. Complete your work
3. Review against `spec/*.md` for drift
4. Add contribution entry
5. Push and create PR:
   ```bash
   git push -u origin feature/my-feature
   gh pr create --title "Add my feature" --body "Description"
   ```
6. Get approval from repository admin

## Deployment

Single-user, single-server architecture. Each user deploys their own instance.

Recommended: [Vultr](https://my.vultr.com/) $5/month (1 vCPU, 1GB RAM, 25GB SSD, Ubuntu 22.04)

1. Create server, note the IP
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
6. Push data: `./devops/push-data-remote.sh`
7. Access at `http://<ip>`
