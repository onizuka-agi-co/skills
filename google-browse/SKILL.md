---
name: google-browse
description: "Web browsing via Google search using the browser tool with CDP-connected Chrome (Antigravity). Use when: (1) searching the web with Google, (2) browsing pages interactively, (3) extracting live content from websites, (4) web_search tool fails or returns insufficient results. Requires browser CDP connection on localhost:9222."
---

# Google Browse

Browse the web using Google Search via Playwright/CDP.

## Prerequisites

- Chrome with CDP enabled on `localhost:9222`
- OpenClaw config: `browser.profiles.antigravity.cdpUrl = "http://localhost:9222"`

## Basic Flow

### 1. Check Connection

```
browser action=status profile=antigravity
```

Verify `cdpReady: true`. If not, Chrome may need restart with `--remote-debugging-port=9222`.

### 2. Navigate to Google Search

```
browser action=navigate profile=antigravity targetUrl="https://www.google.com/search?q=<query>"
```

URL-encode the query (spaces become `+` or `%20`).

### 3. Read Results

```
browser action=snapshot profile=antigravity targetId=<targetId>
```

The snapshot returns accessibility tree with `ref` IDs for interaction.

### 4. Click Links

```
browser action=act profile=antigravity request={kind:"click", ref:"e123"}
```

Use refs from snapshot.

## Common Patterns

### Search Query

```
# Japanese
targetUrl: "https://www.google.com/search?q=東京+天気"

# English
targetUrl: "https://www.google.com/search?q=tokyo+weather"
```

### Extract Text from Page

After navigation, snapshot returns structured content:

```markdown
- heading "Example Domain" [level=1] [ref=e3]
- paragraph [ref=e4]: This domain is for use in...
- link "Learn more" [ref=e5] [cursor=pointer]
```

### Interact with Elements

```json
// Click
{ "kind": "click", "ref": "e5" }

// Type
{ "kind": "type", "ref": "e27", "text": "search query" }

// Press key
{ "kind": "press", "key": "Enter" }
```

## Tips

- **Japanese queries**: Use `+` for spaces, not `%20`
- **Scroll**: Use `request={kind:"press", key:"End"}` or click pagination
- **Multiple tabs**: Use `action=tabs` to list, then operate on specific `targetId`
- **Timeouts**: Increase with `timeoutMs` if pages load slowly

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `cdpReady: false` | Chrome not running or CDP off | Start Chrome with `--remote-debugging-port=9222` |
| `timed out` | Page load slow | Retry or increase timeout |
| `Can't reach browser control` | Gateway restart needed | Run `openclaw gateway restart` |

## Example: Weather Search

```
1. browser action=navigate profile=antigravity targetUrl="https://www.google.com/search?q=東京+天気"
2. browser action=snapshot profile=antigravity targetId=<returned>
3. Parse snapshot for weather widget content
```
