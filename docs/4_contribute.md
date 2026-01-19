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

## Arcs

An Arc is how contributors organize their work on Euno. It's not a technical roadmap—it's a personal chapter in your story of flourishing.

### Philosophy

An Arc answers one question: **What do I want Euno to do for me?**

Not "what feature should I build" but "what value do I want in my life that Euno could provide?" The technical work follows from that.

**Examples of Arcs (good):**
- "I want Euno to anticipate my day so my energy feels good all day long"
- "I want Euno to help me stay connected to the people I care about"
- "I want Euno to surface opportunities I wouldn't find on my own"
- "I want Euno to keep me accountable to my creative practice"

**Examples of Arcs (too technical):**
- "Calendar integration"
- "Android app"
- "Better memory system"
- "API refactoring"

The technical work might be identical—but the framing changes everything. When you're building toward *your own flourishing*, you know when it's working. You feel it.

### Structure

An Arc has two parts:

**1. The Vision** — What value do you want Euno to provide? Write it as a sentence starting with "I want Euno to..."

**2. The Work** — Whatever it takes to make that real: new features, bug fixes, UX improvements, documentation, agent configurations—anything that moves you closer.

There's no time limit. You stay in an Arc until it works—until you're actually getting the value you set out to get. Then you move on to the next chapter.

### Choosing an Arc

Use the questions above in "How to Think About Contributions." Pick one area. Write it as "I want Euno to..." and commit to it.

### Improvements Outside Your Arc

Bug fixes and small improvements that fall outside your Arc are always welcome. The Arc isn't a constraint—it's a compass. If you see something broken, fix it. If you have a quick win, take it.

But your *primary energy* should go toward your Arc until it's delivering real value.

### Completing an Arc

An Arc is complete when you're living the value you set out to create. Not when the feature is "done"—when it's actually working for you.

Ask yourself: Is Euno doing this thing for me now? Do I feel it?

If yes, your Arc is complete. Pick another, or take a beat and just use the system for a while.

### Current Arcs

| Contributor | Arc |
|-------------|-----|
| Buddy | I want Euno to understand who I am and help me stay productive on what matters |
| *Your name* | *Your arc* |

## Getting Started

1. Clone: `git clone https://github.com/buwilliams/euno.git && cd euno`
2. Setup: `cp .env.example .env` and add your API key
3. Install: `pip install -r requirements.txt`
4. Set password: `python main.py set-password`
5. Run: `python main.py start`
6. Open: [localhost:8000](http://localhost:8000)

## Your First Contributions

**Assignment 1: Use the System** — Open Chat, introduce yourself, create a reminder, explore Jobs and Timeline views, ask "What do you know about me?"

**Assignment 2: Create an Agent** — Ask Chat: "Create a social-media agent that finds interesting content daily based on my identity." The agent starts immediately.

**Assignment 3: Contribute** — Pick an issue from [GitHub Projects](https://github.com/users/buwilliams/projects/2), create a feature branch, review against `spec/*.md`, add entry to `contrib/your-name.md`, submit PR.

## Agent Library

The `agent-lib/` directory contains shareable agent templates that anyone can install. These are agents the community has built and tested—ready to use out of the box.

## Pull Request Guidelines

1. Create a feature branch from main
2. Complete your work
3. Review against `spec/*.md` for drift (see Spec section below)
4. Add contribution entry
5. Push and create PR (or ask your coding agent to do it):

### Spec (Design Rules)

The [spec/](../spec/) directory is the best place to understand how Euno works. Each file is intentionally scannable—designed for both humans and AI to quickly grasp the system's rules.

**Why specs matter:** Specs are our AI-first alternative to unit tests. They maintain system consistency across the entire platform. Before merging any PR, ask a coding agent to review the specs and check for implementation drift. This ensures changes align with the system's design.

- [Agents](../spec/1_agents.md) — Agent behavior, job coordination, triggers, work cycles
- [Data](../spec/2_data.md) — Entity schemas (memory, identity, agent, job, config)
- [Backend](../spec/3_backend.md) — Server, API, authentication, storage
- [UX & UI](../spec/4_ux_ui.md) — User experience and interface patterns
- [CLI](../spec/5_cli.md) — Command-line interface commands and behavior

### Submitting
   ```bash
   git push -u origin feature/my-feature
   gh pr create --title "Add my feature" --body "Description"
   ```
6. Get approval from repository admin

## Deployment

Single-user, single-server architecture. Each user deploys their own instance.

Recommended: [DigitalOcean](https://digitalocean.com/) $6/month Basic Droplet (1 vCPU, 1GB RAM, 25GB SSD, 1TB transfer, Ubuntu 24.04 LTS)

> **Note:** We previously recommended Vultr but encountered intrusive and incompetent support after a runaway agent incident.

1. Create a Droplet, note the IP
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

## Join the Community

**[Discord](https://discord.gg/5B9VdQ6vYP)** — where we meet, plan, and discuss Euno updates and what's happening. Come say hi!
