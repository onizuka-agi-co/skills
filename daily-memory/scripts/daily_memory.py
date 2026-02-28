#!/usr/bin/env python3
"""
Daily Memory - 日報管理スクリプト

機能:
- 日報の追加（add）
- トピックの追加（add-topic）
- 目次の自動更新（update-toc）
- タグ検索（search-tags）
- 前回リンクの自動挿入（--continue）

Usage:
    uv run daily_memory.py add --completed "タスクA,タスクB" --tags "#AGI,#開発" --continue
    uv run daily_memory.py add-topic "X API開発" --content "OAuth認証を実装"
    uv run daily_memory.py update-toc
    uv run daily_memory.py search-tags "#AGI"
"""

import argparse
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# メモリリポジトリのパス
MEMORY_REPO = Path.home() / ".openclaw" / "workspace" / "memory"
DOCS_DIR = MEMORY_REPO / "docs"

# タイムゾーン
TIMEZONE = "Asia/Tokyo"


def get_today() -> tuple[str, str, str]:
    """今日の日付を取得（年, 月, 日）"""
    now = datetime.now()
    return now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")


def get_yesterday() -> tuple[str, str, str]:
    """昨日の日付を取得"""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y"), yesterday.strftime("%m"), yesterday.strftime("%d")


def get_date_path(year: str, month: str, day: str) -> Path:
    """日付からパスを生成"""
    return DOCS_DIR / year / month / day


def get_latest_report() -> Optional[tuple[str, str, str]]:
    """最新の日報の日付を取得"""
    today = get_today()
    today_path = get_date_path(*today)

    if today_path.exists() and (today_path / "index.md").exists():
        return today

    # 今日の分がない場合は昨日を探す
    yesterday = get_yesterday()
    yesterday_path = get_date_path(*yesterday)
    if yesterday_path.exists() and (yesterday_path / "index.md").exists():
        return yesterday

    return None


def get_previous_report(current_year: str, current_month: str, current_day: str) -> Optional[Path]:
    """前回の日報へのパスを取得"""
    current_date = datetime(int(current_year), int(current_month), int(current_day))

    # 過去30日分を探索
    for i in range(1, 31):
        prev_date = current_date - timedelta(days=i)
        prev_path = get_date_path(
            prev_date.strftime("%Y"),
            prev_date.strftime("%m"),
            prev_date.strftime("%d")
        )
        if prev_path.exists() and (prev_path / "index.md").exists():
            return prev_path / "index.md"

    return None


def extract_tags(text: str) -> list[str]:
    """テキストからハッシュタグを抽出"""
    pattern = r'#\w+'
    return list(set(re.findall(pattern, text)))


def create_index_content(
    title: str,
    completed: list[str],
    in_progress: list[str],
    notes: str,
    tags: list[str],
    prev_link: Optional[str]
) -> str:
    """日報のindex.mdの内容を生成"""
    lines = [f"# {title}", ""]

    # 前回リンク
    if prev_link:
        lines.append(f"**← 前回:** [{prev_link}]({prev_link})")
        lines.append("")

    # タグ
    if tags:
        lines.append("**タグ:** " + " ".join(tags))
        lines.append("")

    # 完了タスク
    if completed:
        lines.append("## ✅ 完了")
        for task in completed:
            lines.append(f"- {task}")
        lines.append("")

    # 進行中タスク
    if in_progress:
        lines.append("## 🔄 進行中")
        for task in in_progress:
            lines.append(f"- {task}")
        lines.append("")

    # メモ
    if notes:
        lines.append("## 📝 メモ")
        lines.append(notes)
        lines.append("")

    return "\n".join(lines)


def add_report(
    completed: str = "",
    in_progress: str = "",
    notes: str = "",
    tags: str = "",
    continue_link: bool = False,
    title: Optional[str] = None
) -> Path:
    """新しい日報を追加"""
    year, month, day = get_today()
    date_path = get_date_path(year, month, day)

    # ディレクトリ作成
    date_path.mkdir(parents=True, exist_ok=True)

    # パース
    completed_list = [t.strip() for t in completed.split(",") if t.strip()]
    in_progress_list = [t.strip() for t in in_progress.split(",") if t.strip()]
    tag_list = [t.strip() for t in tags.split() if t.strip()]

    # 前回リンク
    prev_link = None
    if continue_link:
        prev_report = get_previous_report(year, month, day)
        if prev_report:
            # docs/からの相対パスを計算
            rel_path = os.path.relpath(prev_report, date_path)
            prev_link = rel_path

    # タイトル
    if not title:
        title = f"{year}-{month}-{day} 日報"

    # コンテンツ生成
    content = create_index_content(
        title=title,
        completed=completed_list,
        in_progress=in_progress_list,
        notes=notes,
        tags=tag_list,
        prev_link=prev_link
    )

    # ファイル書き込み
    index_path = date_path / "index.md"
    index_path.write_text(content, encoding="utf-8")

    print(f"✅ Created: {index_path}")

    # 目次更新
    update_toc()

    return index_path


def add_topic(
    topic_name: str,
    content: str,
    year: Optional[str] = None,
    month: Optional[str] = None,
    day: Optional[str] = None
) -> Path:
    """既存の日報にトピックを追加"""
    if not year or not month or not day:
        year, month, day = get_today()

    date_path = get_date_path(year, month, day)

    if not date_path.exists():
        print(f"❌ Directory not found: {date_path}")
        raise FileNotFoundError(f"No report for {year}-{month}-{day}")

    # トピックファイル名を生成（英数字・ハイフンのみ）
    topic_filename = re.sub(r'[^a-zA-Z0-9\-]', '-', topic_name.lower())
    topic_filename = re.sub(r'-+', '-', topic_filename).strip('-')

    if not topic_filename:
        topic_filename = "topic"

    topic_path = date_path / f"{topic_filename}.md"

    # トピック内容生成
    topic_content = f"# {topic_name}\n\n{content}\n"
    topic_path.write_text(topic_content, encoding="utf-8")

    print(f"✅ Created: {topic_path}")

    # index.mdにリンクを追加
    index_path = date_path / "index.md"
    if index_path.exists():
        index_content = index_path.read_text(encoding="utf-8")
        if "## 詳細" not in index_content:
            index_content += "\n## 詳細\n\n"
        index_content += f"- [{topic_name}]({topic_filename}.md)\n"
        index_path.write_text(index_content, encoding="utf-8")
        print(f"✅ Updated: {index_path}")

    return topic_path


def update_toc():
    """目次を更新（MEMORY.md）"""
    memory_file = MEMORY_REPO / "MEMORY.md"

    if not memory_file.exists():
        print("⚠️ MEMORY.md not found, skipping TOC update")
        return

    # docs/2026/ を探索して日報一覧を取得
    reports = []
    for year_dir in DOCS_DIR.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue
                index_file = day_dir / "index.md"
                if index_file.exists():
                    reports.append((year_dir.name, month_dir.name, day_dir.name))

    # 日付順にソート（新しい順）
    reports.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

    # 目次セクションを生成
    toc_lines = ["## 最近の日報", ""]
    for year, month, day in reports[:10]:  # 最新10件
        toc_lines.append(f"- [{year}-{month}-{day}](docs/{year}/{month}/{day}/)")

    toc_lines.append("")
    toc_lines.append("---")
    toc_lines.append("")
    toc_lines.append("_このファイルはリンク集です。詳細は各日報を参照してください。_")

    # MEMORY.mdを読み込んで目次セクションを置換
    content = memory_file.read_text(encoding="utf-8")

    # 「## 最近の日報」セクションを見つけて置換
    pattern = r'## 最近の日報.*?(?=\n---|\n_[^_]*_$|$)'
    replacement = "\n".join(toc_lines[:-4])  # 最後の4行（区切りと注釈）を除く

    if "## 最近の日報" in content:
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        # セクションがない場合は追加
        new_content = content.rstrip() + "\n\n" + "\n".join(toc_lines)

    memory_file.write_text(new_content, encoding="utf-8")
    print(f"✅ Updated TOC: {memory_file}")


def search_tags(tag: str) -> list[Path]:
    """タグで検索"""
    results = []

    for md_file in DOCS_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if tag in content:
            results.append(md_file)

    return results


def commit():
    """変更をコミット＆プッシュ"""
    os.chdir(MEMORY_REPO)

    # git status
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("No changes to commit")
        return

    # git add
    subprocess.run(["git", "add", "."], check=True)

    # 今日の日付でコミットメッセージ
    year, month, day = get_today()
    commit_msg = f"docs: update daily report {year}-{month}-{day}"

    # git commit
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # git push
    subprocess.run(["git", "push"], check=True)

    print(f"✅ Committed and pushed: {commit_msg}")


def main():
    parser = argparse.ArgumentParser(description="Daily Memory - 日報管理")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add コマンド
    add_parser = subparsers.add_parser("add", help="新しい日報を追加")
    add_parser.add_argument("--completed", "-c", default="", help="完了タスク（カンマ区切り）")
    add_parser.add_argument("--in-progress", "-i", default="", help="進行中タスク（カンマ区切り）")
    add_parser.add_argument("--notes", "-n", default="", help="メモ")
    add_parser.add_argument("--tags", "-t", default="", help="タグ（スペース区切り）")
    add_parser.add_argument("--continue", "-C", action="store_true", dest="continue_link",
                           help="前回の日報へのリンクを追加")
    add_parser.add_argument("--title", default=None, help="タイトル")

    # add-topic コマンド
    topic_parser = subparsers.add_parser("add-topic", help="トピックを追加")
    topic_parser.add_argument("topic", help="トピック名")
    topic_parser.add_argument("--content", "-c", required=True, help="内容")
    topic_parser.add_argument("--date", "-d", default=None, help="日付（YYYY-MM-DD）")

    # update-toc コマンド
    subparsers.add_parser("update-toc", help="目次を更新")

    # search-tags コマンド
    search_parser = subparsers.add_parser("search-tags", help="タグで検索")
    search_parser.add_argument("tag", help="検索するタグ")

    # commit コマンド
    subparsers.add_parser("commit", help="変更をコミット＆プッシュ")

    args = parser.parse_args()

    if args.command == "add":
        add_report(
            completed=args.completed,
            in_progress=args.in_progress,
            notes=args.notes,
            tags=args.tags,
            continue_link=args.continue_link,
            title=args.title
        )
    elif args.command == "add-topic":
        date_parts = None
        if args.date:
            date_parts = args.date.split("-")
            if len(date_parts) != 3:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                return
        add_topic(
            topic_name=args.topic,
            content=args.content,
            year=date_parts[0] if date_parts else None,
            month=date_parts[1] if date_parts else None,
            day=date_parts[2] if date_parts else None
        )
    elif args.command == "update-toc":
        update_toc()
    elif args.command == "search-tags":
        results = search_tags(args.tag)
        if results:
            print(f"Found {len(results)} files with tag {args.tag}:")
            for r in results:
                print(f"  - {r}")
        else:
            print(f"No files found with tag {args.tag}")
    elif args.command == "commit":
        commit()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
