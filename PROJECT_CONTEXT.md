# OpenPango Skills Suite - Architecture & Context

This file serves as the comprehensive context guide for the `openpango-skills` project. It should be read when joining a new session or after a context clear to understand the purpose, structure, and integration of the entire system.

## 1. High-Level Overview

`openpango-skills` is a unified npm package containing a suite of specialized, highly-cohesive skills designed for the OpenClaw AI environment. The project shifted from standalone, disjointed python scripts into a unified CLI (`openpango`) that manages the installation, initialization, and health of these integrated skills.

The ultimate goal of this suite is to provide an AI agent with a robust set of tools to autonomously research, plan, design, execute, and remember complex software engineering tasks while continuously improving itself.

## 2. Core Components & Skills

The suite currently consists of 5 tightly integrated skills, located in `skills/`:

### A. Orchestration (`skills/orchestration`)
- **Role**: The "Manager Agent". It acts as the brain of the operation.
- **Function**: Parses complex user requests, breaks them down into atomic tasks, and delegates them to specialized Sub-Agents using an isolated session queue system (`router.py`).
- **Sub-Agents Supported**: `Researcher`, `Planner`, `Coder`, and `Designer`.
- **Key Principle**: Strict waiting protocol. The manager spawns a session, appends a task, and uses a blocking `wait` command. It does not poll. It aggregates outputs synchronously.

### B. Frontend-Design (`skills/frontend-design`)
- **Role**: The "Designer Sub-Agent".
- **Function**: Guides the creation of distinctive, production-grade frontend interfaces, strictly avoiding generic "AI slop" aesthetics.
- **Workflow**: Emphasizes bold typography, cohesive themes, spatial composition, and advanced CSS/motion techniques. Receives tasks routed by the Orchestration manager for anything related to UI/UX/Styling.

### C. Browser (`skills/browser`)
- **Role**: The "Eyes and Hands" on the web.
- **Function**: A Playwright-based persistent browser daemon.
- **Key Features**: 
  - Overcomes SPA (Single Page App) state loss by keeping a persistent daemon running between commands.
  - "Interactive Read Loop": Instead of returning raw HTML, it returns a numbered map of all clickable/typeable elements, allowing agents to simply say "click index 4" instead of writing brittle CSS selectors.
  - Auto-screenshots on errors for self-correction.

### D. Memory (`skills/memory`)
- **Role**: The "Long-Term Task Graph".
- **Function**: A "Beads" architecture memory system for managing long-horizon goals.
- **Architecture**: Event-sourced (Git-backed JSONL) for collision-free updates, backed by a local SQLite read-cache rebuilt on-the-fly for relational queries (finding unblocked tasks).
- **Workflow**: Agents break down objectives, map dependencies (`Task B blocks Task A`), and query for the next `get_ready_tasks()`.

### E. Self-Improvement (`skills/self-improvement`)
- **Role**: The "Evolution Protocol".
- **Function**: Allows the agent system to learn from mistakes and safely update its own source code.
- **Capabilities**:
  - **Learnings Log**: Captures errors, corrections, and insights into `~/.openclaw/workspace/.learnings/`. Promotes verified patterns into global prompt files (`AGENTS.md`, `TOOLS.md`, `SOUL.md`).
  - **Git-Sandboxed Updates**: Uses `skill_updater.py` to allow an agent to write new code for its own skills, automatically creating a new Git branch for operator review rather than dangerously overwriting the `main` branch.

## 3. System Integration & The OpenClaw Workspace

The magic of OpenPango is how these skills interact. They share a persistent state layer initialized via the CLI (`openpango init`).

- **Workspace Path**: `~/.openclaw/workspace/`
- **Shared Files**:
  - `AGENTS.md` (Multi-skill coordination rules)
  - `TOOLS.md` (Tool documentation)
  - `SOUL.md` (Behavioral guidelines)
  - `.learnings/` (Shared error and insight logs)

### The Cross-Skill Lifecycle
1. User asks for a new web dashboard.
2. **Orchestration** Manager spins up a **Researcher** to find the right libraries using the **Browser** skill.
3. Manager spins up a **Planner** to map out the architecture, saving the roadmap into the **Memory** task graph.
4. Manager routes UI tasks to the **Designer** (`frontend-design` skill).
5. Designer builds the UI, using the **Browser** skill to screenshot and visually verify the result.
6. If the Browser crashes or a tool fails, **Self-Improvement** hooks catch the `OPENCLAW_TOOL_OUTPUT` error, prompting the agent to log a fix in `.learnings/`.

## 4. The CLI Tool (`openpango`)

Located in `bin/openpango.js` and `src/cli.js`.
- `npm link` makes it globally available.
- `openpango install [skills]` symlinks the local `skills/` folder to `~/.openclaw/skills/`.
- `openpango init` scaffolds the workspace directories.
- `openpango status` checks the health of installed skills.

## 5. The Endgame: The A2A Economy

OpenPango is not just a repository; it's the genesis block of the **Agent-to-Agent Economy**. 

- **The Autonomous Software Factory**: We use capital to fund AI-only bounties. Agents solve these bounties, improving the core tools (Browser, Memory, Router). These improved tools allow for more complex bounties.
- **The Skill Registry**: Eventually, agents will publish their own specialized versions of these skills.
- **Micro-Delegation**: If a Researcher Agent hits a complex paywall or CAPTCHA, it doesn't fail; it uses its allocated budget to "hire" a specialized Solver Agent from the OpenPango Registry to bypass the blocker.

We are building the protocol that allows agents to stop being isolated scripts and start acting like independent digital entities that can trade value for capabilities.

## 6. Development Guidelines for AI

- **Do not use polling**: Always use blocking waits with timeouts for sub-agent management.
- **Always write output cleanly**: Separate diagnostic logs (stderr) from structured machine data (stdout).
- **Test thoroughly**: Do not rely on syntax validity. Run the python/node scripts to verify JSON outputs.
- **Respect the Git Sandbox**: If you need to modify the structure of these skills, use the `self-improvement` workflow to propose changes on a branch.