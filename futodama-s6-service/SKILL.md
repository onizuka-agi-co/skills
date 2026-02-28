---
name: futodama-s6-service
description: "Create or update persistent s6 services for FUTODAMA/OpenClaw Docker containers. Use when: (1) running long-lived Python/Bash workers, (2) needing auto-restart after crashes, (3) adding services under /config/s6-services, (4) using config.env-driven runtime settings, (5) verifying s6 service behavior after container restarts."
---

# FUTODAMA s6 Service

Create persistent `s6` services in FUTODAMA by placing service definitions under `/config/s6-services/<service-name>/`. This skill is for long-running workers that should auto-start and auto-restart.

## When To Use

Use this skill when the process should:

- start automatically after container start/restart
- keep running continuously
- restart automatically if it exits/crashes
- keep config/logs in `/config` (persistent volume)

Do not use this skill for one-time startup tasks. Use the container init hook approach (`/custom-cont-init.d/*` / `PYTHON_AUTOSTART_*`) for one-shot execution.

## Quick Start

1. Put your script under `/config` (for this repo: `futodama-config/...`), for example `futodama-config/startup/my_worker.py`.
2. Create `/config/s6-services/<name>/run` (for this repo: `futodama-config/s6-services/<name>/run`).
3. Ensure `run` is executable and ends with `exec ...`.
4. Run `docker compose restart` so FUTODAMA links `/config/s6-services/*` into `/run/service`.
5. Verify with `s6-svstat /run/service/<name>` and logs.

## Workflow

### 1. Choose service pattern

- **Direct process**: The Python script is already a long-running loop/server. `run` should `exec python3 ...`.
- **Interval loop**: The task should run periodically (e.g., webhook heartbeat). `run` should contain a `while true; do ...; sleep N; done` loop.

### 2. Create service directory and run script

Required layout:

```text
/config/s6-services/<service-name>/
└── run
```

Recommended optional files:

```text
/config/s6-services/<service-name>/
├── run
└── config.env
```

Rules for `run`:

- start with `#!/usr/bin/env bash` and `set -euo pipefail`
- load `config.env` if present
- run as `abc` user via `s6-setuidgid abc`
- write logs under `/config/.local/state/futodama/`
- use `exec` for the final foreground process

### 3. Keep persistence boundaries correct

Persist in `/config`:

- scripts (`/config/startup/...`)
- service definitions (`/config/s6-services/...`)
- logs (`/config/.local/state/futodama/...`)
- runtime config (`config.env`)

Do not rely on container-only paths for custom service definitions (e.g. editing `/run/service` manually). Those are recreated on restart.

### 4. Verify and test restart behavior

Inside the container (`agi-ws-futodama` in this repo):

```bash
s6-svstat /run/service/<service-name>
ps -ef | grep -v grep | grep <script-or-process-name>
tail -f /config/.local/state/futodama/<service>.log
```

Force a service restart:

```bash
s6-svc -t /run/service/<service-name>
```

Bring a stopped service up:

```bash
s6-svc -u /run/service/<service-name>
```

### 5. Validate crash recovery (recommended)

Kill the worker process and confirm `s6` starts a new PID.

## Common Pitfalls

- **Permission denied on log file**: create/chown log directory before switching to `abc`, or write logs after `s6-setuidgid abc`.
- **Service flaps immediately**: missing `exec`, wrong script path, or missing env var in `config.env`.
- **No auto-start after adding new service**: `docker compose restart` was not run after creating `/config/s6-services/<name>`.
- **Works manually but not in s6**: relative paths or shell profile assumptions. Use absolute paths and set `HOME=/config`.
- **Webhook/API requests blocked**: add a `User-Agent` header in the client script if the endpoint blocks generic clients.

## Resources

- Use `scripts/create_python_s6_service.sh` to scaffold a Python `s6` service.
- Read `references/examples.md` for tested examples from this FUTODAMA workspace (`sample-python`, `discord-webhook-heartbeat`).

## Example Requests

- "Create an s6 service for `/config/startup/my_bot.py` with auto-restart and log file under `/config/.local/state/futodama/`."
- "Convert this one-shot Python autostart into an s6 service with `config.env` settings."
- "Make a periodic Discord webhook notifier as an s6 service using the FUTODAMA layout."
