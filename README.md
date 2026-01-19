# Skill Client System

A skill-based agent framework with Anthropic-style progressive skill loading and built-in base tools for file and shell operations.

## Overview

- Skills live in folders under `skills/` with a `SKILL.md` frontmatter.
- Only lightweight metadata is loaded at startup (Level 1).
- Full skill instructions are injected only after a `use_skill` call (Level 2).
- Supporting resources (Level 3) can be loaded on demand.
- The agent always has base tools for files/directories and bash execution.

## Architecture

```
+-----------------------------+
| BaseAgent                   |
| - prompt assembly (L1/L2)   |
| - use_skill handler         |
| - tool routing              |
+-------------+---------------+
              |
              | tool calls / messages
              v
+----------------------+    +----------------------+
| LLMClient            |    | SkillLoader          |
| - OpenAI-compatible  |    | - L1 metadata        |
| - tool calling       |    | - L2 SKILL.md        |
+----------+-----------+    | - L3 resources       |
           |                +----------------------+
           v
+----------------------+
| BaseToolExecutor     |
| - read/write/list    |
| - create_directory   |
| - execute_bash       |
+----------------------+
```

## Key Components

### 1. BaseAgent
- Builds the system prompt with Level 1 skill metadata and activated Level 2 skill content
- Exposes a `use_skill` tool so the model can request skill activation
- Routes tool calls to the base tool executor

### 2. SkillLoader
- Discovers skill folders containing `SKILL.md`
- Loads YAML frontmatter for Level 1 metadata (name/description/license)
- Loads full `SKILL.md` content when activated (Level 2)
- Can load supporting files on demand (Level 3)

### 3. LLMClient
- OpenAI-compatible client (works with OpenAI, DeepSeek, and similar APIs)
- Handles tool calling and returns tool call payloads to the agent

### 4. BaseToolExecutor
- Provides built-in tools for file I/O, directory management, and bash execution
- Restricts relative paths to the working directory

## Installation

1. Clone or download this repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_api_key_here
# or
DEEPSEEK_API_KEY=your_api_key_here
```

`main.py` selects the provider based on which key is present. OpenAI-compatible providers can be configured directly via `LLMClient` if you embed the system in your own application code.

## Usage

Run the main script:

```bash
python main.py
```

The system will:
1. Discover available skills (Level 1 metadata only)
2. Initialize the LLM client
3. Start an interactive chat loop
4. Activate skills when the model calls `use_skill`

Example interaction:

```
You: Make a poster for a jazz festival
Assistant: ... (activates a relevant skill if needed)
```

## Skill Format

Skills are stored as folders under `skills/`. Each folder must contain a `SKILL.md` file with YAML frontmatter:

```
skills/
  my-skill/
    SKILL.md
    LICENSE.txt
    resources/
    scripts/
```

Example `SKILL.md` frontmatter:

```markdown
---
name: my-skill
description: Brief description of what this skill does
license: Optional license or reference
---

# Skill Instructions

Detailed instructions for the model...
```

The loader uses the frontmatter for Level 1 discovery. Everything after the frontmatter is treated as the full skill content (Level 2).

## Base Tools

These tools are always available to the model:
- `read_file`
- `write_file`
- `list_files`
- `create_directory`
- `execute_bash`

The working directory defaults to the current directory and can be customized when constructing `BaseAgent`.

## Extending Base Tools

Add a new handler method in `core/base_tools.py`, register it in `self.tools`, and include it in `get_tool_definitions()` so the model can call it.

## How It Works

1. **Discover**: `SkillLoader.discover_skills()` reads frontmatter from each `SKILL.md` (Level 1).
2. **Prompt**: `BaseAgent` injects the available skill list into the system prompt.
3. **Activate**: The model calls `use_skill` when it needs a skill.
4. **Load**: `SkillLoader.activate_skill()` loads full `SKILL.md` content (Level 2).
5. **Execute**: Tool calls are routed to `BaseToolExecutor`.

## Project Structure

```
skill_client_system/
├── core/
│   ├── base_agent.py
│   ├── base_tools.py
│   ├── llm_client.py
│   └── skill_loader.py
├── skills/
│   ├── canvas-design/
│   ├── frontend-design/
│   └── pptx/
├── main.py
├── requirements.txt
└── README.md
```

## License

MIT License - feel free to use and modify for your projects.

## Contributing

Contributions welcome! Feel free to:
- Add new skills
- Improve existing components
- Extend base tools
- Enhance documentation

## Contact

![Contact QR Code](contact.png)

Scan the QR code to connect with me