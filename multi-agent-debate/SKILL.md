---
name: multi-agent-debate
description: "Orchestrate multi-agent debates where multiple AI personas discuss and analyze topics from different perspectives. Use when: (1) analyzing papers or ideas from multiple angles, (2) generating diverse viewpoints on a topic, (3) brainstorming with structured debate, (4) creating educational discussion content. Spawns sub-agents with distinct personas, collects their arguments, and synthesizes a final summary."
---

# Multi-Agent Debate

Orchestrate structured debates between multiple AI personas using OpenClaw's `sessions_spawn`.

## Architecture

```
Facilitator (main agent)
├── Researcher  → analyzes facts, evidence, data
├── Critic      → identifies weaknesses, counterarguments
├── Practitioner → real-world applicability, use cases
└── Synthesis   → facilitator summarizes and concludes
```

## Quick Start

```bash
# Run a debate on a topic
uv run scripts/debate.py --topic "The impact of AGI on society"

# Debate on a paper
uv run scripts/debate.py --topic-url "https://arxiv.org/abs/..." --mode paper

# Debate with custom personas
uv run scripts/debate.py --topic "..." --personas researcher,critic,visionary
```

## Debate Modes

### Paper Analysis (`--mode paper`)
1. Fetch paper content
2. Each agent reads and forms position
3. Round-robin arguments (2 rounds)
4. Final synthesis

### Idea Exploration (`--mode idea`)
1. Present topic to all agents
2. Each agent proposes their viewpoint
3. Agents respond to each other
4. Synthesis with action items

### Decision Support (`--mode decision`)
1. Present decision context
2. Agents argue for/against
3. Risk/benefit analysis
4. Recommendation

## Using sessions_spawn Directly

```python
# Spawn researcher
sessions_spawn(
  task="You are a Researcher persona. Analyze this topic from a factual, evidence-based perspective. Topic: {topic}. Provide your analysis in 3-5 key points.",
  model="zai/glm-5",
  runtime="subagent",
  mode="run"
)
```

## Output Format

Debate results are saved to:
- Console output (Discord-friendly)
- `memory/docs/YYYY/MM/DD/debate-{slug}.md` (full log)

### Discord Output

Use colored cards for each agent:
- 🔬 Researcher → Blue (`2196F3`)
- 🔍 Critic → Red (`C41E3A`)
- 🔧 Practitioner → Green (`4CAF50`)
- 📋 Synthesis → Gold (`FFD700`)

## Configuration

Personas are defined in `references/personas.md`.

## Resources

### scripts/
- `debate.py` — Main debate orchestration script

### references/
- `personas.md` — Persona definitions and prompt templates
