---
name: discord-webhook-periodic
description: "Create or update periodic Discord webhook notifier services for FUTODAMA/OpenClaw containers using s6. Use when: (1) sending recurring status messages, (2) posting heartbeat/monitor alerts, (3) building webhook automation with config.env, (4) using embeds/cards via JSON payloads, (5) ensuring auto-restart and persistence under /config/s6-services."
---

# Discord Webhook Periodic

Build persistent, auto-restarting Discord webhook notifiers in FUTODAMA using `s6` services under `/config/s6-services/<service-name>/`.

## When To Use

Use this skill when you need:

- periodic Discord webhook notifications (heartbeat, cron-like reports, reminders)
- `s6` auto-restart behavior for a notifier process
- persistent config/logs in `/config`
- plain text or embed/card-based webhook payloads

## Quick Start

1. Ensure `/config/startup/discord_webhook_post.py` exists (this workspace already has it).
2. Generate a service scaffold with `scripts/create_discord_webhook_periodic_service.sh`.
3. Edit `config.env` (Webhook URL, interval, message template, username).
4. Run `docker compose restart`.
5. Verify `s6-svstat` and the service log.

## Workflow

### 1. Pick notifier style

- **Simple text**: send `content` with timestamp/hostname.
- **Embed/card**: generate JSON payload and call `discord_webhook_post.py --payload-file ...`.

### 2. Create `s6` service directory

Expected layout:

```text
/config/s6-services/<service-name>/
├── run
└── config.env
```

Rules:

- `run` must be executable
- keep secrets (Webhook URL) in `config.env`
- write logs to `/config/.local/state/futodama/*.log`
- run as `abc` via `s6-setuidgid abc`

### 3. Use the bundled scaffold script

Generate a periodic text notifier service:

```bash
scripts/create_discord_webhook_periodic_service.sh \
  --service discord-notify \
  --webhook-url 'https://discord.com/api/webhooks/...' \
  --interval-sec 3000
```

This creates files under `futodama-config/s6-services/<service-name>/` in the current repo.

### 4. Verify runtime behavior

```bash
docker compose restart
docker exec agi-ws-futodama s6-svstat /run/service/<service-name>
docker exec agi-ws-futodama tail -n 100 /config/.local/state/futodama/<service-name>.log
```

Force one cycle / restart:

```bash
docker exec agi-ws-futodama s6-svc -t /run/service/<service-name>
```

## Embed / Card Pattern

For more visual notifications:

- construct a JSON payload file with `embeds` and optional `content`
- call `/config/startup/discord_webhook_post.py --payload-file <json>`
- set colors based on severity (`ok`, `warning`, `critical`)

See `references/examples.md` for the tested `discord-webhook-heartbeat` implementation with CPU/RAM/Disk metrics and color-coded embeds.

## Common Pitfalls

- `403 / error 1010` on Discord webhook: add a `User-Agent` header in the webhook client (already handled by `discord_webhook_post.py` in this workspace).
- service exits immediately: missing `DISCORD_WEBHOOK_URL` or syntax error in `run`
- no auto-start after creating service: forgot `docker compose restart`
- noisy mentions: set `allowed_mentions: { parse: [] }` in embed payloads

## Resources

- `scripts/create_discord_webhook_periodic_service.sh`: scaffold periodic Discord webhook `s6` service (`run` + `config.env`)
- `references/examples.md`: tested examples (simple worker, webhook heartbeat embed service)

## Example Requests

- "Create an s6 service that posts a Discord webhook every 3000 seconds."
- "Convert this webhook notifier to an embed/card payload with severity colors."
- "Set up a FUTODAMA Discord heartbeat service with config.env and log verification commands."
