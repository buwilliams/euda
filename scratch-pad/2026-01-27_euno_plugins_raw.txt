  Help me design and implement a new plugin system. It will completely replace our 'tools' and 'integration' concept. The plugin system will be
  extensivble enabling more contributions. Store plugins in a new plugins/{plugin} directory in the <root> project. Each plugin will have a CLI
  (command-line interface) as it's primary interface. The 'plugin' concept will entirely replace the 'tools' concept. We will have a core plugin called
  'core' (in plugins/core/) which will have a CLI for all euno specific tools such as consolidation, etc. I want to move all the euno specific tools to
  this new plugin. This will give the plugins the abililty to call the euno plugin CLI to perform actions. We need to discuss how it will come together.
  The core entities of the system will be Agents, Topics, and Plugins. Agents use plugins via CLI. We'll still have the manager so that when the system is
  booted up, the Agents can starting working. For example, currently, we have a UI to expose Euno, but I also want a Euno CLI that is a chat interface
  where we can talk to the Euno platform. Moreover, the triggers will active the euno core plugin for operations (unless they are events from the
  EventBus). Review the current architecture in docs/ and specs/, and let's talk through this big idea and plan. So, Euno (src/) will own the manager,
  eventbus, agents, topics, and plugin calls interactions. Probably means we need to teach Euno (src/) how to call CLIs in the plugins directory. A plugin
  can be simply cloned to the plugins directory and blamo a new capability has been added to the system. In fact, I wonder if we even need to list the
  plugins (formerly tools) in the agent configs, perhaps Euno (src/) will just do a 'ls plugins/' to see which plugins are available. Let's change the
  'plugins' (formerly tools[] in data/agents/{agent}/config.json to excluded_plugins[] so that all plugins are available by default. There's a lot to
  cover:
  - new /plugins directory
  - new /plugins/core plugin (for Euno)
  - replace /data/agents/{agent}/config.json tools[] to excluded_plugins[]
  - allow agents to discover all plugins by default 'ls plugins/' (or equivelent) and use the cli --help menu to discover how to use it
  - entirely replace the 'tools' and integration concept with 'plugins'
  - rework the docs/ and specs/ with new architecture
  This is exciting! Challenge me. Question me. Let's get to it!
  
---

  Current State Summary

  Tools today:
  - 82+ Python functions with @tool() decorators in a global registry
  - In-process execution (fast, direct memory access)
  - Tightly coupled to agent internals (set_agent_context(), direct state modification)
  - LLM receives tool schemas, calls them, gets results in conversation loop
  - Static imports at startup, no dynamic discovery

  ---
  Questions & Challenges on Plugin Architecture

  1. LLM ↔ Plugin Interface Problem

  The LLM needs structured tool schemas to call tools. Currently:
  tools = [{"name": "create_topic", "description": "...", "input_schema": {...}}]

  CLI --help is human-readable, not machine-parseable. How does the LLM discover and call plugins?

  Options:
  - A) Each plugin provides a manifest.json with tool schemas (still need schema)
  - B) Standardized plugin schema subcommand that outputs JSON schema
  - C) Euno parses --help and generates schemas (fragile)
  - D) Plugins aren't called by LLM directly—only the core plugin is, and it orchestrates others

  Which direction are you thinking?

  2. Context Passing Problem

  Current tools access rich context:
  agent = get_agent_context()  # Who's calling
  agent.memory.add_entry(...)  # Modify agent state

  With CLI-based plugins, how do they get context?
  - Environment variables? (EUNO_AGENT_ID, EUNO_TOPIC_ID)
  - Config files? (plugins read from data/)
  - CLI arguments? (--agent-id chat --topic-id abc123)
  - Stdin JSON? (pipe context as JSON blob)

  3. Performance Concern

  Current tool call: ~1ms (in-process function call)
  CLI subprocess: ~50-200ms per invocation (fork, exec, parse args, init)

  In a single agent turn, the LLM might call 5-10 tools sequentially. That's 0.01s → 0.5-2s overhead per turn.

  Is this acceptable? Or should "hot path" operations stay in-process?

  4. The Core Plugin Scope

  You said the core plugin handles "euno specific tools such as consolidation." But looking at the current tools:
  ┌────────────────────────────────┬───────────────────┐
  │          Current Tool          │ Proposed Location │
  ├────────────────────────────────┼───────────────────┤
  │ create_topic, list_topics      │ Core plugin       │
  ├────────────────────────────────┼───────────────────┤
  │ get_memory, add_memory         │ Core plugin       │
  ├────────────────────────────────┼───────────────────┤
  │ nc_list_files, nc_create_event │ Nextcloud plugin  │
  ├────────────────────────────────┼───────────────────┤
  │ speak_aloud                    │ Speech plugin     │
  ├────────────────────────────────┼───────────────────┤
  │ get_mastodon_posts             │ Mastodon plugin   │
  └────────────────────────────────┴───────────────────┘
  Is the core plugin essentially the entire current src/tools/data/ + src/tools/system/?

  5. Discovery vs. Security

  "excluded_plugins[] so that all plugins are available by default"

  This is elegant for extensibility, but consider:
  - What if someone clones a malicious plugin?
  - Should plugins require explicit opt-in for agents handling sensitive data?
  - Or is this a "build for yourself" decision where you trust all plugins?

  6. Plugin-to-Plugin Communication

  "give plugins the ability to call the euno plugin CLI"

  So a Nextcloud plugin could call:
  euno core topics create --title "Sync reminder"

  This is powerful but creates dependency chains. How do we handle:
  - Plugin ordering (does core initialize first?)
  - Circular dependencies
  - Error propagation across CLIs

  7. The Manager's Role

  "We'll still have the manager so agents can start working"

  Currently the manager:
  1. Loads agent configs
  2. Registers triggers
  3. Starts the event bus
  4. Exposes agents via API

  With plugins:
  - Does the manager also load/validate plugins?
  - Does it pass plugin CLI paths to agents?
  - Does it maintain a plugin registry?

  ---
  Proposed Architecture Questions

  Let me sketch what I think you're describing and you can correct me:

  /plugins/
  ├── core/               # Euno's built-in capabilities
  │   ├── cli.py          # Main CLI entry: `euno core <subcommand>`
  │   ├── manifest.json   # Schema, metadata
  │   └── src/            # Implementation
  │       ├── topics.py
  │       ├── memory.py
  │       └── consolidation.py
  ├── nextcloud/
  │   ├── cli.py          # `euno nextcloud <subcommand>`
  │   ├── manifest.json
  │   └── src/
  └── speech/
      ├── cli.py
      └── manifest.json

  Invocation model:
  # From shell
  euno plugins nextcloud files list /Documents

  # From agent (conceptually)
  subprocess.run(["euno", "plugins", "nextcloud", "files", "list", "/Documents"])

  Key questions on this model:
  1. Is euno plugins <plugin> <command> the invocation pattern?
  2. Or does each plugin have its own entry point (nextcloud-cli files list)?
  3. How does Euno know what subcommands are available for schema generation?

  ---
  My Biggest Concern

  The LLM tool interface is the critical path. Today:
  LLM → tool_use block → execute_tool() → result → LLM

  With plugins:
  LLM → ??? → CLI → result → LLM

  The ??? is the gap. Options:
  1. Thin wrapper: Keep in-process tool registry, but tools just shell out to CLIs
  2. Schema manifest: Plugins provide JSON schemas, Euno builds tool list from manifests
  3. Core-only LLM: LLM only calls core plugin, core orchestrates other plugins

  Which model do you envision?

  ---
  What I Like About This

  1. Clone-and-go extensibility — Powerful for contributions
  2. Language agnostic — Plugins could be written in anything
  3. Clear boundaries — CLI forces clean interfaces
  4. Testable isolation — Each plugin testable independently
  5. Self-documenting — CLI help as documentation

  ---
  Let's discuss these points before diving into implementation. What's your thinking on the LLM integration and context passing?

---

  LLM will still use tools but they will be greatly simplified around the CLI use of plugins:
  - list_plugins
  - plugin_usage {plugin_name}
  - execute_plugin {plugin_name} {parameters...}
  etc.
  
---

  This is a brilliant simplification. Instead of 82 specialized tools with complex schemas, the LLM gets a universal plugin interface:

  # The entire LLM tool surface becomes:
  @tool("list_plugins")
  def list_plugins() -> list[str]:
      """Returns available plugin names"""

  @tool("plugin_usage")
  def plugin_usage(plugin: str) -> str:
      """Returns CLI help/usage for a plugin"""

  @tool("execute_plugin")
  def execute_plugin(plugin: str, command: str, args: dict) -> str:
      """Executes a plugin command with arguments"""

  The LLM operates like a human at a terminal:
  1. "What plugins do I have?" → list_plugins
  2. "How do I use nextcloud?" → plugin_usage("nextcloud")
  3. "List my calendar events" → execute_plugin("nextcloud", "calendar list", {"calendar": "personal"})

  ---
  This Changes Everything (For the Better)

  Before: Euno developers must define schemas for every tool, keep them updated, handle type coercion, etc.

  After: Plugin authors write a CLI with --help. That's it. The LLM figures out the rest.

  Before: Adding a capability requires Python code in src/tools/, imports, registry updates.

  After: git clone <plugin-repo> plugins/myplugin — done.

  ---
  Follow-up Questions

  1. Command Structure

  What's the CLI invocation pattern?

  # Option A: Unified entry point
  euno plugin <plugin_name> <command> [args]
  euno plugin nextcloud calendar list --calendar personal

  # Option B: Direct plugin executables
  plugins/nextcloud/cli <command> [args]
  ./plugins/nextcloud/cli calendar list --calendar personal

  # Option C: Plugin provides its own named command
  nextcloud-euno calendar list --calendar personal

  I'm guessing Option A since you mentioned euno core earlier?

  2. execute_plugin Signature

  How structured are the args?

  # Option A: Fully structured (LLM builds dict)
  execute_plugin("nextcloud", "calendar list", {"calendar": "personal", "limit": 10})

  # Option B: Raw string (LLM builds CLI string)
  execute_plugin("nextcloud", "calendar list --calendar personal --limit 10")

  # Option C: Positional + flags hybrid
  execute_plugin("nextcloud", "calendar", "list", ["personal"], {"limit": 10})

  Option B is simpler for the LLM (it just writes a command) but Option A gives you validation.

  3. Plugin Usage Format

  Should plugin_usage return raw --help text, or structured data?

  # Raw (simpler for plugin authors)
  Usage: nextcloud calendar <command>

  Commands:
    list      List calendar events
    create    Create a new event
    delete    Delete an event

  Options:
    --calendar TEXT   Calendar name [default: personal]
    --limit INT       Max events to return

  vs.

  {
    "commands": {
      "calendar list": {
        "description": "List calendar events",
        "args": {
          "calendar": {"type": "string", "default": "personal"},
          "limit": {"type": "integer"}
        }
      }
    }
  }

  Raw is easier for plugin authors. Structured helps the LLM. Could support both?

  4. Context Injection

  The LLM doesn't need to pass context, but the plugins do need it. I'm thinking:

  # Euno sets environment before calling plugin CLI
  EUNO_AGENT_ID=chat
  EUNO_DATA_DIR=/path/to/data
  EUNO_TOPICS_DB=/path/to/data/topics/db.sqlite

  # Plugin reads from env
  ./plugins/core/cli topics list --status todo
  # Internally: connects to $EUNO_TOPICS_DB

  This keeps the LLM interface clean while giving plugins what they need.

  5. Core Plugin Commands

  Based on current tools, here's what core might look like:

  euno plugin core topics list [--status STATUS] [--parent PARENT_ID]
  euno plugin core topics create --title TITLE [--description DESC]
  euno plugin core topics update ID [--status STATUS] [--title TITLE]
  euno plugin core topics complete ID

  euno plugin core memory list [--type TYPE] [--agent AGENT]
  euno plugin core memory add --type TYPE --content CONTENT
  euno plugin core memory delete ID

  euno plugin core identity show [--agent AGENT]
  euno plugin core identity update --section SECTION --content CONTENT

  euno plugin core consolidate [--phase append|consolidate|both]

  euno plugin core agents list
  euno plugin core agents show AGENT_ID

  Does this match your mental model?

  ---
  Refined Architecture Sketch

  Euno (src/)
  ├── manager.py           # Boots agents, event bus, discovers plugins
  ├── agent/
  │   └── agent.py         # Uses simplified tool interface
  ├── plugins/             # Plugin execution layer
  │   ├── discovery.py     # list_plugins() - scans plugins/
  │   ├── executor.py      # execute_plugin() - runs CLI, captures output
  │   └── usage.py         # plugin_usage() - runs --help, returns text
  └── llms/
      └── tools/           # Just 3-5 meta-tools now
          └── plugins.py   # list_plugins, plugin_usage, execute_plugin

  plugins/
  ├── core/                # Euno's built-in capabilities
  │   ├── cli.py           # Entry point
  │   └── commands/
  │       ├── topics.py
  │       ├── memory.py
  │       └── consolidate.py
  ├── nextcloud/
  │   └── cli.py
  └── speech/
      └── cli.py

  ---
  One More Question: Sync vs Async

  Some operations are slow (Nextcloud API calls, consolidation). Currently tools can be async. With CLI:

  - Sync (blocking): execute_plugin waits for CLI to complete
  - Async (background): execute_plugin returns immediately, result comes later

  Do we need async plugin execution, or is blocking acceptable given the simplified model?

  ---
  I think we're converging on something elegant. What's your take on the command structure and args format?

---

  1. Command Structure - Option A: Unified entry point
  2. execute_plugin Signature - Option B: Raw string (LLM builds CLI string)
  3. Plugin Usage Format - Raw (simpler for plugin authors)
  4. The Core Plugin Scope - The core plugin is essentially the entire current src/tools/data/ + src/tools/system/
  5. Core Plugin Commands - yes.
  6. One More Question: Sync vs Async - blocking is acceptable given the simplified model (we can leverage multiple agents)

---

  Excellent. Clear decisions. Let me now lay out the concrete implementation plan and surface a few remaining design choices.

  ---
  Implementation Plan

  Phase 1: Foundation

  1.1 Create plugin infrastructure in src/

  src/plugins/
  ├── __init__.py
  ├── discovery.py    # Scan plugins/, return names
  ├── executor.py     # Run CLI, capture output
  ├── usage.py        # Run --help, return text
  └── tools.py        # The 3 LLM tools: list_plugins, plugin_usage, execute_plugin

  1.2 Create plugins directory structure

  plugins/
  └── core/
      ├── cli.py              # Main entry point (Click/Typer)
      └── commands/
          ├── __init__.py
          ├── topics.py       # topics list, create, update, complete
          ├── assets.py       # assets list, read, write, delete
          ├── memory.py       # memory list, add, delete
          ├── identity.py     # identity show, update
          ├── agents.py       # agents list, show
          ├── consolidate.py  # consolidate (phases)
          ├── notifications.py
          ├── dates.py
          └── quote.py

  1.3 Define environment contract

  # Set by Euno before plugin execution
  EUNO_DATA_DIR=/path/to/data
  EUNO_AGENT_ID=chat
  EUNO_PLUGINS_DIR=/path/to/plugins

  Phase 2: Core Plugin

  2.1 Migrate all src/tools/data/ to plugins/core/commands/
  - topics.py (22 tools → CLI commands)
  - assets.py (4 tools)
  - memory.py (7 tools)
  - identity.py (4 tools)

  2.2 Migrate all src/tools/system/ to plugins/core/commands/
  - system.py → agents.py, notifications.py
  - dates.py
  - quote.py
  - consolidation/ → consolidate.py

  Phase 3: Integration Plugins

  3.1 Create plugins/nextcloud/
  - Migrate src/tools/integration/nextcloud/

  3.2 Create plugins/speech/
  - Migrate src/tools/integration/speech.py

  3.3 Create plugins/mastodon/
  - Migrate src/tools/integration/mastodon.py

  Phase 4: Agent Updates

  4.1 Update agent configs
  // Before
  {"tools": ["list_topics", "create_topic", "nc_list_files"]}

  // After
  {"excluded_plugins": []}  // or omit entirely for all plugins

  4.2 Update agent.py
  - Remove old tool loading
  - Use new simplified tools from src/plugins/tools.py

  Phase 5: Cleanup

  5.1 Remove old tools infrastructure
  - Delete src/tools/ (except maybe keep as src/tools_legacy/ temporarily)
  - Remove @tool decorator system

  5.2 Update documentation
  - CLAUDE.md
  - docs/4_system.md
  - specs/1_agents.md
  - specs/2_data.md
  - New specs/X_plugins.md

  ---
  Remaining Design Choices

  1. CLI Framework

  What should plugins use for CLI?
  ┌──────────┬─────────────────────────────────────────┬───────────────────────┐
  │  Option  │                  Pros                   │         Cons          │
  ├──────────┼─────────────────────────────────────────┼───────────────────────┤
  │ Click    │ Battle-tested, good help generation     │ Verbose               │
  ├──────────┼─────────────────────────────────────────┼───────────────────────┤
  │ Typer    │ Clean syntax, auto-help from type hints │ Extra dependency      │
  ├──────────┼─────────────────────────────────────────┼───────────────────────┤
  │ Argparse │ Stdlib, no deps                         │ Verbose, less elegant │
  └──────────┴─────────────────────────────────────────┴───────────────────────┘
  I'd suggest Typer for core (we control it) and let external plugins use whatever they want (as long as --help works).

  2. Plugin Entry Point Convention

  How does euno plugin <name> <command> execute?

  # Option A: Convention - plugins/<name>/cli.py with main()
  # Euno does: subprocess.run(["python", "plugins/<name>/cli.py", ...])

  # Option B: Executable script
  # plugins/<name>/cli is executable, shebang line
  # Euno does: subprocess.run(["plugins/<name>/cli", ...])

  # Option C: pyproject.toml entry point
  # Plugin defines: [project.scripts] myplugin = "myplugin:main"
  # Euno does: subprocess.run(["myplugin", ...])

  I'd suggest Option A for simplicity—no need for installed entry points, just a convention.

  3. Output Format

  # Plain text (default) - good for LLM
  euno plugin core topics list
  # ID: abc123
  # Title: Fix the bug
  # Status: todo

  # JSON (optional flag) - good for scripting
  euno plugin core topics list --json
  # [{"id": "abc123", "title": "Fix the bug", "status": "todo"}]

  Support both with --json flag?

  4. The euno plugin Command

  Should this be part of the existing euno CLI or separate?

  # Integrated (my suggestion)
  uv run euno plugin core topics list
  uv run euno plugin nextcloud calendar list

  # This means main.py gains a 'plugin' subcommand

  5. Plugin Dependencies

  For the core plugin, it can import from src/ since it's part of Euno. But external plugins?

  Options:
  - Shared environment: External plugins use the main Euno venv (simpler)
  - Isolated environments: Each plugin has its own venv (safer, more complex)

  For "build for yourself" philosophy, I'd say shared environment is fine. External plugins just list their deps in a requirements.txt that gets installed into
   the main env.

  ---
  Concrete Next Step

  Want me to start with Phase 1.1 + 1.2? Specifically:

  1. Create src/plugins/ with discovery, executor, usage, and the 3 LLM tools
  2. Create plugins/core/ skeleton with Typer CLI
  3. Implement one command group (e.g., topics) as proof of concept

  Then we can iterate from there. Sound good?

---

  1. CLI Framework - Typer works for me and I agree let other use whatever they want.
  2. Plugin Entry Point Convention - Option A: Convention - plugins/<name>/cli.py with main()
  3. Output Format - Plain text (default) - good for LLM
  4. The euno plugin Command - Integrated into exist CLI (move old commands and source code it all should move to plugins/core)
  5. Plugin Dependencies - Shared environment
  
  Create a full implementation plan with todos.