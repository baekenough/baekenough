#!/usr/bin/env python3
"""
Claude Code Insights Extractor and README Updater.

Aggregates session metadata from multiple accounts,
copies HTML reports, and updates GitHub profile README with metrics.
"""

import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


# Configuration
ACCOUNTS = {
    "baekenough": Path.home() / "workspace/claude/baekenough/usage-data",
    "baekgomiyo": Path.home() / "workspace/claude/baekgomiyo/usage-data",
    "claude-global": Path.home() / ".claude/usage-data",
}
REMOTE_ACCOUNTS = {
    "ubuntu-server": {
        "ssh_host": "ubuntu24_home_server-ext",
        "data_path": "~/.claude/projects",
    },
}
PROFILE_REPO = Path.home() / "workspace/baekenough"


def aggregate_session_meta(accounts):
    """
    Aggregate session metadata from all accounts.

    Deduplicates sessions across accounts using the ``session_id`` field,
    so the same session appearing in multiple paths is counted only once.

    Returns:
        dict: Aggregated statistics including total messages, sessions,
              unique days, tool counts, task events, commits, and tokens.
    """
    stats = {
        "total_messages": 0,
        "total_sessions": 0,
        "unique_days": set(),
        "tool_counts": defaultdict(int),
        "total_task_events": 0,
        "total_commits": 0,
        "total_tokens": 0,
    }
    seen_session_ids = set()

    for account, usage_dir in accounts.items():
        session_meta_dir = usage_dir / "session-meta"
        if not session_meta_dir.exists():
            print(f"Warning: {session_meta_dir} not found, skipping {account}")
            continue

        for meta_file in session_meta_dir.glob("*.json"):
            try:
                with meta_file.open() as f:
                    data = json.load(f)

                # Deduplicate by session_id when present
                session_id = data.get("session_id")
                if session_id is not None:
                    if session_id in seen_session_ids:
                        continue
                    seen_session_ids.add(session_id)

                # Aggregate messages
                stats["total_messages"] += data.get("user_message_count", 0)
                stats["total_messages"] += data.get("assistant_message_count", 0)

                # Count sessions
                stats["total_sessions"] += 1

                # Extract unique days
                start_time = data.get("start_time")
                if start_time:
                    date = datetime.fromisoformat(
                        start_time.replace('Z', '+00:00')
                    ).date()
                    stats["unique_days"].add(date)

                # Aggregate tool counts (exclude StructuredOutput)
                tool_counts = data.get("tool_counts", {})
                for tool, count in tool_counts.items():
                    if tool != "StructuredOutput":
                        stats["tool_counts"][tool] += count

                # Aggregate commits and tokens
                stats["total_commits"] += data.get("git_commits", 0)
                stats["total_tokens"] += data.get("input_tokens", 0)
                stats["total_tokens"] += data.get("output_tokens", 0)

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse {meta_file}: {e}")
                continue

    # Calculate total task events
    stats["total_task_events"] = stats["tool_counts"].get("Task", 0)

    # Convert set to count
    stats["unique_days"] = len(stats["unique_days"])

    # Convert defaultdict to regular dict
    stats["tool_counts"] = dict(stats["tool_counts"])

    return stats


_REMOTE_PARSE_SCRIPT = r"""
import glob
import json
import sys
from collections import defaultdict

stats = {
    "total_messages": 0,
    "total_sessions": 0,
    "unique_days": set(),
    "tool_counts": defaultdict(int),
    "total_task_events": 0,
    "total_commits": 0,
    "total_tokens": 0,
}
seen_session_ids = set()

for path in glob.glob(sys.argv[1] + "/*/*.jsonl"):
    session_id = None
    session_messages = 0
    session_date = None
    session_tool_counts = defaultdict(int)

    try:
        with open(path) as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("type", "")

                # Extract session ID from queue-operation entries
                if entry_type == "queue-operation" and session_id is None:
                    session_id = entry.get("sessionId")

                # Count user and assistant messages
                if entry_type in ("user", "assistant"):
                    msg = entry.get("message", {})
                    role = msg.get("role", "")
                    if role in ("user", "assistant"):
                        session_messages += 1

                        # Extract timestamp for unique day tracking
                        if session_date is None:
                            ts = entry.get("timestamp")
                            if ts:
                                try:
                                    from datetime import datetime, timezone
                                    dt = datetime.fromisoformat(
                                        ts.replace("Z", "+00:00")
                                    )
                                    session_date = dt.date().isoformat()
                                except (ValueError, AttributeError):
                                    pass

                        # Count tool_use blocks in assistant messages
                        if role == "assistant":
                            content = msg.get("content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if (
                                        isinstance(block, dict)
                                        and block.get("type") == "tool_use"
                                    ):
                                        tool_name = block.get("name", "")
                                        if tool_name and tool_name != "StructuredOutput":
                                            session_tool_counts[tool_name] += 1
    except OSError:
        continue

    # Deduplicate sessions by ID
    if session_id is not None:
        if session_id in seen_session_ids:
            continue
        seen_session_ids.add(session_id)

    stats["total_sessions"] += 1
    stats["total_messages"] += session_messages
    if session_date:
        stats["unique_days"].add(session_date)
    for tool, count in session_tool_counts.items():
        stats["tool_counts"][tool] += count

stats["total_task_events"] = stats["tool_counts"].get("Task", 0)
stats["unique_days"] = len(stats["unique_days"])
stats["tool_counts"] = dict(stats["tool_counts"])

print(json.dumps(stats))
"""


def aggregate_remote_sessions(remote_accounts):
    """
    Aggregate session data from remote SSH servers.

    Connects to each remote server via SSH and runs a self-contained Python
    script that parses JSONL conversation files. The remote files use a
    different format from local session-meta JSON files: each JSONL line is
    a conversation entry with ``type``, ``message``, and ``timestamp`` fields.

    Commits and tokens are reported as 0 for remote sessions since JSONL
    conversation files do not contain git or token billing information.

    Args:
        remote_accounts: Dictionary mapping account names to SSH connection
            configs, each with ``ssh_host`` and ``data_path`` keys.

    Returns:
        dict: Aggregated statistics in the same format as
            ``aggregate_session_meta``, or an empty stats dict if all
            remote connections fail.
    """
    combined = {
        "total_messages": 0,
        "total_sessions": 0,
        "unique_days": 0,
        "tool_counts": defaultdict(int),
        "total_task_events": 0,
        "total_commits": 0,
        "total_tokens": 0,
    }

    for account, config in remote_accounts.items():
        ssh_host = config["ssh_host"]
        data_path = config["data_path"]
        print(f"Fetching remote session data from {account} ({ssh_host})...")

        try:
            result = subprocess.run(
                [
                    "ssh",
                    ssh_host,
                    f"python3 - {data_path}",
                ],
                input=_REMOTE_PARSE_SCRIPT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            print(f"Warning: SSH timeout connecting to {account} ({ssh_host}), skipping")
            continue
        except Exception as e:
            print(f"Warning: SSH failed for {account} ({ssh_host}): {e}, skipping")
            continue

        if result.returncode != 0:
            stderr_preview = result.stderr.strip()[:200]
            print(
                f"Warning: Remote script failed for {account} ({ssh_host}): "
                f"{stderr_preview}, skipping"
            )
            continue

        try:
            remote_stats = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            print(
                f"Warning: Failed to parse remote output from {account} ({ssh_host}): "
                f"{e}, skipping"
            )
            continue

        # Merge remote stats into combined
        combined["total_messages"] += remote_stats.get("total_messages", 0)
        combined["total_sessions"] += remote_stats.get("total_sessions", 0)
        combined["unique_days"] += remote_stats.get("unique_days", 0)
        combined["total_task_events"] += remote_stats.get("total_task_events", 0)
        combined["total_commits"] += remote_stats.get("total_commits", 0)
        combined["total_tokens"] += remote_stats.get("total_tokens", 0)

        for tool, count in remote_stats.get("tool_counts", {}).items():
            combined["tool_counts"][tool] += count

        print(
            f"  {account}: {remote_stats.get('total_sessions', 0):,} sessions, "
            f"{remote_stats.get('total_messages', 0):,} messages"
        )

    combined["tool_counts"] = dict(combined["tool_counts"])
    return combined


def merge_stats(base, remote):
    """
    Merge remote stats into base stats in-place.

    Adds numeric totals together and merges tool_counts dicts by summing
    values for matching keys. ``unique_days`` from separate machines are
    added directly since the days come from independent environments.

    Args:
        base: Base stats dict (modified in-place).
        remote: Remote stats dict to merge into base.
    """
    base["total_messages"] += remote["total_messages"]
    base["total_sessions"] += remote["total_sessions"]
    base["unique_days"] += remote["unique_days"]
    base["total_task_events"] += remote["total_task_events"]
    base["total_commits"] += remote["total_commits"]
    base["total_tokens"] += remote["total_tokens"]

    merged_tools = defaultdict(int, base["tool_counts"])
    for tool, count in remote["tool_counts"].items():
        merged_tools[tool] += count
    base["tool_counts"] = dict(merged_tools)


def copy_reports(accounts, insights_dir):
    """
    Copy HTML reports from each account to insights directory.

    Args:
        accounts: Dictionary of account names to usage data paths.
        insights_dir: Destination directory for copied reports.
    """
    insights_dir.mkdir(exist_ok=True)

    for account, usage_dir in accounts.items():
        report_file = usage_dir / "report.html"
        if not report_file.exists():
            print(f"Warning: {report_file} not found, skipping copy for {account}")
            continue

        dest = insights_dir / f"{account}-insights.html"
        try:
            shutil.copy2(report_file, dest)
            print(f"Copied {report_file} -> {dest}")
        except Exception as e:
            print(f"Warning: Failed to copy {report_file}: {e}")


def fetch_omc_info():
    """
    Fetch the latest oh-my-customcode version and commit count from GitHub.

    Uses the GitHub CLI (gh) to query release and commit data.

    Returns:
        tuple[str | None, int | None]: (version_tag, commit_count).
            version_tag includes the 'v' prefix (e.g., 'v0.51.0').
            Either value is None if the corresponding fetch fails.
    """
    version = None
    commit_count = None

    try:
        result = subprocess.run(
            [
                "gh", "api",
                "repos/baekenough/oh-my-customcode/releases/latest",
                "--jq", ".tag_name",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
        else:
            print(f"Warning: Failed to fetch omc version: {result.stderr.strip()}")
    except Exception as e:
        print(f"Warning: Failed to fetch omc version: {e}")

    try:
        result = subprocess.run(
            [
                "gh", "api",
                "repos/baekenough/oh-my-customcode/commits?per_page=1",
                "-i",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            match = re.search(r'page=(\d+)>;\s*rel="last"', result.stdout)
            if match:
                commit_count = int(match.group(1))
            else:
                print("Warning: Could not parse commit count from Link header")
        else:
            print(f"Warning: Failed to fetch omc commit count: {result.stderr.strip()}")
    except Exception as e:
        print(f"Warning: Failed to fetch omc commit count: {e}")

    return version, commit_count


def update_omc_version(content, version, commits, lang):
    """
    Replace the oh-my-customcode version and commit count in README content.

    Args:
        content: Original README content string.
        version: Version tag string including 'v' prefix (e.g., 'v0.51.0').
        commits: Total commit count as an integer.
        lang: Language code ('ko' or 'en').

    Returns:
        str: Content with the oh-my-customcode version line updated.
    """
    if lang == 'ko':
        pattern = r'oh-my-customcode v[\d.]+\s*\(\d[\d,]*\s*커밋\)'
        replacement = f'oh-my-customcode {version} ({commits:,} 커밋)'
    else:
        pattern = r'oh-my-customcode v[\d.]+\s*\(\d[\d,]*\s*commits\)'
        replacement = f'oh-my-customcode {version} ({commits:,} commits)'

    updated, sub_count = re.subn(pattern, replacement, content)
    if sub_count == 0:
        print(f"Warning: oh-my-customcode version pattern not found in {lang} README")
    return updated


def generate_metrics_section_ko(stats):
    """
    Generate metrics table section in Korean.

    Args:
        stats: Aggregated session statistics.

    Returns:
        str: HTML table with metrics.
    """
    return f"""<table>
<tr>
<td align="center"><b>{stats['total_messages']:,}</b><br/><sub>처리 메시지 ({stats['unique_days']}일)</sub></td>
<td align="center"><b>{stats['total_sessions']:,}</b><br/><sub>세션 수</sub></td>
<td align="center"><b>{stats['total_task_events']:,}</b><br/><sub>병렬 세션 이벤트</sub></td>
</tr>
</table>"""


def generate_metrics_section_en(stats):
    """
    Generate metrics table section in English.

    Args:
        stats: Aggregated session statistics.

    Returns:
        str: HTML table with metrics.
    """
    return f"""<table>
<tr>
<td align="center"><b>{stats['total_messages']:,}</b><br/><sub>Messages ({stats['unique_days']} days)</sub></td>
<td align="center"><b>{stats['total_sessions']:,}</b><br/><sub>Sessions</sub></td>
<td align="center"><b>{stats['total_task_events']:,}</b><br/><sub>Parallel Session Events</sub></td>
</tr>
</table>"""


def generate_tools_section(stats, lang):
    """
    Generate tools section with badge links.

    Args:
        stats: Aggregated session statistics.
        lang: Language code ('ko' or 'en').

    Returns:
        str: Markdown badges for top 4 tools.
    """
    # Get top 4 tools (excluding StructuredOutput)
    tool_counts = stats["tool_counts"]
    sorted_tools = sorted(
        tool_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:4]

    colors = ["22d3ee", "a78bfa", "34d399", "fb923c"]
    badges = []

    for i, (tool, count) in enumerate(sorted_tools):
        color = colors[i % len(colors)]
        tool_urlenc = quote(tool.replace(' ', '_'))

        if lang == 'ko':
            badge = (
                f'<img src="https://img.shields.io/badge/'
                f'{tool_urlenc}-{count}회-{color}?style=flat-square" alt="{tool}"/>'
            )
        else:
            badge = (
                f'<img src="https://img.shields.io/badge/'
                f'{tool_urlenc}-{count}_calls-{color}?style=flat-square" alt="{tool}"/>'
            )

        badges.append(badge)

    return "\n".join(badges)


def replace_between_markers(content, marker_name, replacement):
    """
    Replace content between HTML comment markers.

    Args:
        content: Original content string.
        marker_name: Name of the marker (used in comments).
        replacement: New content to insert between markers.

    Returns:
        str: Modified content with replacement applied.
    """
    start_marker = f"<!-- insights:{marker_name}:start -->"
    end_marker = f"<!-- insights:{marker_name}:end -->"

    if start_marker not in content or end_marker not in content:
        print(f"Warning: Markers for '{marker_name}' not found in content")
        return content

    start_idx = content.index(start_marker) + len(start_marker)
    end_idx = content.index(end_marker)

    return content[:start_idx] + "\n" + replacement + "\n" + content[end_idx:]


def main():
    """Main execution function."""
    dry_run = "--dry-run" in sys.argv

    # Aggregate local data
    print("Aggregating session metadata...")
    stats = aggregate_session_meta(ACCOUNTS)

    # Aggregate remote data and merge
    print("Aggregating remote session data...")
    remote_stats = aggregate_remote_sessions(REMOTE_ACCOUNTS)
    merge_stats(stats, remote_stats)

    # Fetch oh-my-customcode info
    print("Fetching oh-my-customcode info from GitHub...")
    omc_version, omc_commits = fetch_omc_info()

    # Print summary
    print("\n=== Stats Summary ===")
    print(f"Total Messages: {stats['total_messages']:,}")
    print(f"Total Sessions: {stats['total_sessions']:,}")
    print(f"Unique Days: {stats['unique_days']}")
    print(f"Total Commits: {stats['total_commits']:,}")
    print(f"Total Tokens: {stats['total_tokens']:,}")
    print(f"Total Task Events: {stats['total_task_events']:,}")
    print(f"oh-my-customcode: {omc_version} ({omc_commits} commits)")
    print(f"\nTop Tools:")
    for tool, count in sorted(
        stats['tool_counts'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]:
        print(f"  {tool}: {count:,}")

    # Copy reports
    insights_dir = PROFILE_REPO / "insights"
    print(f"\nCopying reports to {insights_dir}...")
    if not dry_run:
        copy_reports(ACCOUNTS, insights_dir)
    else:
        print("(dry run: skipping copy)")

    # Update READMEs
    readme_ko = PROFILE_REPO / "README.md"
    readme_en = PROFILE_REPO / "README_en.md"

    # Korean README
    if readme_ko.exists():
        print(f"\nUpdating {readme_ko}...")
        content_ko = readme_ko.read_text()
        metrics_ko = generate_metrics_section_ko(stats)
        tools_ko = generate_tools_section(stats, 'ko')

        content_ko = replace_between_markers(content_ko, "metrics", metrics_ko)
        content_ko = replace_between_markers(content_ko, "tools", tools_ko)
        if omc_version and omc_commits:
            content_ko = update_omc_version(content_ko, omc_version, omc_commits, 'ko')

        if dry_run:
            print("(dry run: would update metrics and tools)")
        else:
            readme_ko.write_text(content_ko)
            print(f"Updated {readme_ko}")
    else:
        print(f"Warning: {readme_ko} not found")

    # English README
    if readme_en.exists():
        print(f"\nUpdating {readme_en}...")
        content_en = readme_en.read_text()
        metrics_en = generate_metrics_section_en(stats)
        tools_en = generate_tools_section(stats, 'en')

        content_en = replace_between_markers(content_en, "metrics", metrics_en)
        content_en = replace_between_markers(content_en, "tools", tools_en)
        if omc_version and omc_commits:
            content_en = update_omc_version(content_en, omc_version, omc_commits, 'en')

        if dry_run:
            print("(dry run: would update metrics and tools)")
        else:
            readme_en.write_text(content_en)
            print(f"Updated {readme_en}")
    else:
        print(f"Warning: {readme_en} not found")

    print("\nDone!")


if __name__ == "__main__":
    main()
