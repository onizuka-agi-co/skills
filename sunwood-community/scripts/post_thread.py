#!/usr/bin/env python3
"""
Post a main X post with a required image plus multiple replies in one run.

Usage:
    uv run skills/sunwood-community/scripts/post_thread.py --payload-file payload.json
    uv run skills/sunwood-community/scripts/post_thread.py --payload-file payload.json --dry-run

Payload schema:
{
  "main_post": {
    "text": "Main post body without URLs",
    "image_path": "memory/docs/public/example.png",
    "community_id": null,
    "share_with_followers": false
  },
  "replies": [
    {
      "id": "source",
      "text": "📎 元ポスト\n論点の補足です。\nhttps://x.com/i/status/123",
      "reply_to": "main"
    },
    {
      "id": "docs",
      "text": "🔗 公式情報\n仕様確認用のリンクです。\nhttps://example.com/spec",
      "reply_to": "main"
    }
  ],
  "metadata": {
    "source_url": "https://x.com/i/status/123",
    "report_path": "project/x-bookmarks-watcher/logs/reports/2026/03/22/sample.md"
  }
}
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMMUNITY_ID = "2010195061309587967"
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
DATA_X_DIR = WORKSPACE_ROOT / "data" / "x"
TOKEN_FILE = Path(os.environ.get("SUNWOOD_COMMUNITY_TOKEN_FILE", str(DATA_X_DIR / "x-tokens.json")))
LOGS_DIR = Path(__file__).parent.parent / "logs"
ONIAGI_TAG = "$ONIAGI"
LEGACY_TAGS = ("#ONIZUKA_AGI",)
URL_LINE_RE = re.compile(r"^https?://\S+$")
URL_RE = re.compile(r"https?://\S+")
ESCAPED_CONTROL_SEQUENCE_RE = re.compile(r"\\[nrt]")


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"Token file not found: {TOKEN_FILE}")

    with open(TOKEN_FILE, encoding="utf-8") as handle:
        data = json.load(handle)

    token = data.get("access_token", "")
    if not token:
        raise ValueError(f"access_token is missing in {TOKEN_FILE}")
    return token


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def validate_no_literal_escape_sequences(text: str) -> None:
    matches = sorted(set(ESCAPED_CONTROL_SEQUENCE_RE.findall(text or "")))
    if matches:
        raise ValueError(
            "Post text must not contain raw escaped control sequences. "
            f"Found: {', '.join(matches)}"
        )


def ensure_oniagi_tag(text: str) -> str:
    normalized = (text or "").strip()
    for legacy_tag in LEGACY_TAGS:
        normalized = normalized.replace(legacy_tag, ONIAGI_TAG)

    if ONIAGI_TAG not in normalized:
        lines = normalized.splitlines() if normalized else []
        if lines and URL_LINE_RE.match(lines[-1].strip()):
            url_line = lines.pop().strip()
            lines.extend(["", ONIAGI_TAG, "", url_line])
            normalized = "\n".join(lines)
        else:
            normalized = f"{normalized}\n\n{ONIAGI_TAG}" if normalized else ONIAGI_TAG

    return normalized


def validate_main_post_text(text: str) -> None:
    if not (text or "").strip():
        raise ValueError("Main post text must not be empty.")
    validate_no_literal_escape_sequences(text)
    urls = extract_urls(text)
    if urls:
        raise ValueError(
            "Main post text must not contain URLs. "
            f"Found {len(urls)} URL(s): {', '.join(urls)}"
        )


def validate_reply_text(text: str) -> None:
    if not (text or "").strip():
        raise ValueError("Reply text must not be empty.")
    validate_no_literal_escape_sequences(text)
    urls = extract_urls(text)
    if len(urls) > 1:
        raise ValueError(
            "Reply text must not contain multiple URLs. "
            f"Found {len(urls)} URL(s): {', '.join(urls)}"
        )


def resolve_local_path(raw_path: str, *, base_dir: Path) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        if not candidate.exists():
            raise FileNotFoundError(f"Path not found: {candidate}")
        return candidate

    search_roots = [Path.cwd(), base_dir, WORKSPACE_ROOT]
    for root in search_roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved

    raise FileNotFoundError(f"Path not found: {raw_path}")


def load_media_source(main_post: dict[str, Any], *, base_dir: Path) -> tuple[bytes, str, str, str]:
    raw_source = (
        main_post.get("image")
        or main_post.get("image_path")
        or main_post.get("image_url")
    )
    if not raw_source or not str(raw_source).strip():
        raise ValueError("Main post requires an image source. Set image_path or image_url.")

    source = str(raw_source).strip()
    if source.startswith("http://") or source.startswith("https://"):
        request = urllib.request.Request(source, headers={"User-Agent": "ONIZUKA-AGI/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type", "image/png")
        filename = source.split("/")[-1].split("?")[0] or "visual.png"
        return content, filename, content_type, source

    resolved = resolve_local_path(source, base_dir=base_dir)
    content = resolved.read_bytes()
    content_type = mimetypes.guess_type(str(resolved))[0] or "image/png"
    return content, resolved.name, content_type, str(resolved)


def api_request(method: str, endpoint: str, token: str, *, data: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"https://api.x.com{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"API error: {exc.code} - {error_body}") from exc


def multipart_upload(url: str, token: str, *, fields: dict[str, Any], files: dict[str, tuple[str, bytes, str]]) -> dict[str, Any]:
    import uuid

    boundary = uuid.uuid4().hex
    body_parts: list[bytes] = []

    for key, value in fields.items():
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(f'Content-Disposition: form-data; name="{key}"'.encode())
        body_parts.append(b"")
        body_parts.append(str(value).encode())

    for key, (filename, content, content_type) in files.items():
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode()
        )
        body_parts.append(f"Content-Type: {content_type}".encode())
        body_parts.append(b"")
        body_parts.append(content)

    body_parts.append(f"--{boundary}--".encode())
    body_parts.append(b"")
    body = b"\r\n".join(body_parts)

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"Upload error: {exc.code} - {error_body}") from exc


def upload_media(content: bytes, filename: str, content_type: str, token: str) -> str:
    result = multipart_upload(
        "https://api.x.com/2/media/upload",
        token,
        fields={"media_category": "tweet_image"},
        files={"media": (filename, content, content_type)},
    )
    media_id = result.get("data", {}).get("id")
    if not media_id:
        raise ValueError(f"Upload failed: {result}")
    return str(media_id)


def post_tweet(
    text: str,
    token: str,
    *,
    media_ids: list[str] | None = None,
    reply_to_tweet_id: str | None = None,
    community_id: str | None = None,
    share_with_followers: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text}
    if community_id:
        payload["community_id"] = community_id
        if share_with_followers:
            payload["share_with_followers"] = True
    if media_ids:
        payload["media"] = {"media_ids": media_ids}
    if reply_to_tweet_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id}

    return api_request("POST", "/2/tweets", token, data=payload)


def delete_tweet(tweet_id: str, token: str) -> None:
    api_request("DELETE", f"/2/tweets/{tweet_id}", token)


def fetch_media_keys(tweet_id: str, token: str) -> list[str]:
    result = api_request(
        "GET",
        f"/2/tweets/{tweet_id}?tweet.fields=attachments",
        token,
    )
    attachments = result.get("data", {}).get("attachments", {})
    return attachments.get("media_keys", []) or []


def load_payload(payload_file: Path) -> dict[str, Any]:
    with open(payload_file, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Payload root must be a JSON object.")
    return payload


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    main_post = payload.get("main_post")
    if not isinstance(main_post, dict):
        raise ValueError("Payload must include a main_post object.")

    normalized_main = dict(main_post)
    normalized_main["text"] = ensure_oniagi_tag(str(main_post.get("text", "")))
    validate_main_post_text(normalized_main["text"])

    replies = payload.get("replies", [])
    if replies is None:
        replies = []
    if not isinstance(replies, list):
        raise ValueError("replies must be an array.")

    normalized_replies: list[dict[str, Any]] = []
    seen_ids = {"main"}
    for index, item in enumerate(replies):
        if not isinstance(item, dict):
            raise ValueError(f"Reply #{index + 1} must be an object.")
        reply_id = str(item.get("id", f"reply-{index + 1}"))
        if reply_id in seen_ids:
            raise ValueError(f"Duplicate reply id: {reply_id}")
        reply_text = str(item.get("text", ""))
        validate_reply_text(reply_text)
        reply_to = str(item.get("reply_to", "main"))
        normalized_item = dict(item)
        normalized_item["id"] = reply_id
        normalized_item["text"] = reply_text
        normalized_item["reply_to"] = reply_to
        normalized_replies.append(normalized_item)
        seen_ids.add(reply_id)

    valid_targets = {"main"} | {item["id"] for item in normalized_replies}
    posted_targets = {"main"}
    for item in normalized_replies:
        target = item["reply_to"]
        if target not in valid_targets:
            raise ValueError(f"Reply target does not exist: {target}")
        if target not in posted_targets:
            raise ValueError(
                f"Reply target must refer to main or an earlier reply. Invalid target order: {target}"
            )
        posted_targets.add(item["id"])

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}

    return {
        "main_post": normalized_main,
        "replies": normalized_replies,
        "metadata": metadata,
        "options": options,
    }


def save_log(
    payload_file: Path,
    payload: dict[str, Any],
    image_source: str,
    main_post_result: dict[str, Any],
    reply_results: list[dict[str, Any]],
) -> Path:
    now = datetime.now(timezone.utc)
    date_dir = LOGS_DIR / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    main_post_id = main_post_result.get("data", {}).get("id", "unknown")
    log_file = date_dir / f"{now.strftime('%H-%M-%S')}_{main_post_id}.json"
    log_data = {
        "timestamp": now.isoformat(),
        "payload_file": str(payload_file),
        "metadata": payload.get("metadata", {}),
        "image_source": image_source,
        "main_post": {
            "id": main_post_id,
            "text": payload["main_post"]["text"],
            "url": f"https://x.com/i/status/{main_post_id}",
        },
        "replies": [
            {
                "id": result["result"].get("data", {}).get("id", ""),
                "reply_id": result["reply"]["id"],
                "reply_to": result["reply"]["reply_to"],
                "text": result["reply"]["text"],
                "url": f"https://x.com/i/status/{result['result'].get('data', {}).get('id', '')}",
            }
            for result in reply_results
        ],
    }

    with open(log_file, "w", encoding="utf-8") as handle:
        json.dump(log_data, handle, ensure_ascii=False, indent=2)

    return log_file


def rollback_posts(created_post_ids: list[str], token: str) -> None:
    for tweet_id in reversed(created_post_ids):
        try:
            delete_tweet(tweet_id, token)
            print(f"↩️ Deleted posted tweet during rollback: {tweet_id}")
        except Exception as exc:
            print(f"⚠️ Rollback failed for {tweet_id}: {exc}")


def print_summary(
    payload: dict[str, Any],
    *,
    payload_file: Path,
    image_source: str,
    main_post_result: dict[str, Any] | None = None,
    reply_results: list[dict[str, Any]] | None = None,
    log_file: Path | None = None,
    dry_run: bool = False,
) -> None:
    reply_results = reply_results or []
    summary = {
        "mode": "dry-run" if dry_run else "posted",
        "payload_file": str(payload_file),
        "image_source": image_source,
        "main_post_text": payload["main_post"]["text"],
        "reply_count": len(payload["replies"]),
        "main_post_url": None,
        "reply_urls": [],
        "log_file": str(log_file) if log_file else None,
    }
    if main_post_result is not None:
        main_id = main_post_result.get("data", {}).get("id", "")
        summary["main_post_url"] = f"https://x.com/i/status/{main_id}"
    for result in reply_results:
        reply_post_id = result["result"].get("data", {}).get("id", "")
        summary["reply_urls"].append(
            {
                "id": result["reply"]["id"],
                "reply_to": result["reply"]["reply_to"],
                "url": f"https://x.com/i/status/{reply_post_id}",
            }
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Post a main X post plus multiple replies from one payload file.")
    parser.add_argument("--payload-file", required=True, help="JSON payload file path")
    parser.add_argument("--dry-run", action="store_true", help="Validate only. Do not post.")
    parser.add_argument(
        "--no-rollback",
        action="store_true",
        help="Do not delete already-posted tweets if a later reply fails.",
    )
    args = parser.parse_args()

    payload_file = resolve_local_path(args.payload_file, base_dir=Path.cwd())
    payload = normalize_payload(load_payload(payload_file))
    image_content, image_name, image_type, image_source = load_media_source(
        payload["main_post"],
        base_dir=payload_file.parent,
    )

    if args.dry_run:
        print_summary(
            payload,
            payload_file=payload_file,
            image_source=image_source,
            dry_run=True,
        )
        return

    token = load_token()
    created_post_ids: list[str] = []
    rollback_on_failure = not args.no_rollback
    main_post_result: dict[str, Any] | None = None
    reply_results: list[dict[str, Any]] = []

    try:
        media_id = upload_media(image_content, image_name, image_type, token)
        if not media_id:
            raise ValueError("Main post image upload did not return a media_id.")

        main_post = payload["main_post"]
        community_id = main_post.get("community_id")
        if community_id in ("", False):
            community_id = None

        main_post_result = post_tweet(
            main_post["text"],
            token,
            media_ids=[media_id],
            community_id=community_id,
            share_with_followers=bool(main_post.get("share_with_followers", False)),
        )
        main_post_id = str(main_post_result.get("data", {}).get("id", ""))
        if not main_post_id:
            raise ValueError("Main post did not return a tweet id.")
        created_post_ids.append(main_post_id)

        media_keys = fetch_media_keys(main_post_id, token)
        if not media_keys:
            raise ValueError("Main post was created without attached media.")

        posted_ids = {"main": main_post_id}
        for reply in payload["replies"]:
            parent_id = posted_ids[reply["reply_to"]]
            result = post_tweet(
                reply["text"],
                token,
                reply_to_tweet_id=parent_id,
                community_id=community_id,
                share_with_followers=False,
            )
            reply_post_id = str(result.get("data", {}).get("id", ""))
            if not reply_post_id:
                raise ValueError(f"Reply {reply['id']} did not return a tweet id.")
            created_post_ids.append(reply_post_id)
            posted_ids[reply["id"]] = reply_post_id
            reply_results.append({"reply": reply, "result": result})

        log_file = save_log(
            payload_file,
            payload,
            image_source,
            main_post_result,
            reply_results,
        )
        print_summary(
            payload,
            payload_file=payload_file,
            image_source=image_source,
            main_post_result=main_post_result,
            reply_results=reply_results,
            log_file=log_file,
        )
    except Exception:
        if rollback_on_failure and created_post_ids:
            rollback_posts(created_post_ids, token)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ Error: {exc}")
        sys.exit(1)
