---
name: glm-code
description: "Claude Code via GLM (z.ai) for coding tasks. Use when: (1) building/creating new features or apps, (2) code generation, (3) file creation with code, (4) quick coding tasks. Alternative to coding-agent skill when using GLM instead of native Anthropic API."
---

# GLM Code

Claude Code via GLM (z.ai API) for coding tasks.

## Quick Start

```bash
# Set environment variables
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="<your-token>"
export ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5"

# Run Claude Code
claude --print --dangerously-skip-permissions "Your task here"
```

## Bash Tool Pattern

Use exec tool with pty:true and long timeout:

```json
{
  "command": "ANTHROPIC_BASE_URL=\"https://api.z.ai/api/anthropic\" ANTHROPIC_AUTH_TOKEN=\"<token>\" claude --print --dangerously-skip-permissions \"Create a simple HTML file\"",
  "pty": true,
  "timeout": 300
}
```

## Key Parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| `pty` | `true` | Claude Code needs PTY for proper output |
| `timeout` | `300+` | GLM may be slower than native API |
| `--print` | flag | Non-interactive mode |
| `--dangerously-skip-permissions` | flag | Skip confirmation dialogs |

## Environment Variables

Required for GLM:

```bash
ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
ANTHROPIC_AUTH_TOKEN="<your-zai-token>"
ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.5-air"
ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5"
ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5"
```

## Git Directory Required

Claude Code requires a git repository. Create temp dir for scratch work:

```bash
SCRATCH=$(mktemp -d) && cd $SCRATCH && git init -q
```

## Model Selection

```bash
# Use specific model
claude --print --model glm-5 "task"

# Default (sonnet = glm-5)
claude --print "task"
```

## Background Mode

For long tasks, use background + poll:

```bash
# Start
exec pty:true background:true command:"claude --print 'long task'"

# Monitor
process action:log sessionId:xxx
process action:poll sessionId:xxx timeout:120000
```

## Troubleshooting

- **Timeout**: Increase to 300s+
- **Permission denied**: Add `--dangerously-skip-permissions`
- **No output**: Ensure `pty:true`
- **Not logged in**: Set `ANTHROPIC_AUTH_TOKEN`
