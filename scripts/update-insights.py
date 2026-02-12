#!/usr/bin/env python3
"""
Claude Code Insights Extractor and README Updater.

Aggregates session metadata and satisfaction facets from multiple accounts,
copies HTML reports, and updates GitHub profile README with metrics.
"""

import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


# Configuration
ACCOUNTS = {
    "baekenough": Path.home() / "workspace/claude/baekenough/usage-data",
    "baekgomiyo": Path.home() / "workspace/claude/baekgomiyo/usage-data",
}
PROFILE_REPO = Path.home() / "workspace/baekenough"


def aggregate_session_meta(accounts):
    """
    Aggregate session metadata from all accounts.

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

    for account, usage_dir in accounts.items():
        session_meta_dir = usage_dir / "session-meta"
        if not session_meta_dir.exists():
            print(f"Warning: {session_meta_dir} not found, skipping {account}")
            continue

        for meta_file in session_meta_dir.glob("*.json"):
            try:
                with meta_file.open() as f:
                    data = json.load(f)

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


def aggregate_facets(accounts):
    """
    Aggregate satisfaction facets from all accounts.

    Returns:
        dict: Satisfaction statistics including satisfied count, total count,
              and satisfaction rate as percentage.
    """
    facets = {
        "satisfied": 0,
        "total": 0,
        "rate": 0,
    }

    for account, usage_dir in accounts.items():
        facets_dir = usage_dir / "facets"
        if not facets_dir.exists():
            print(f"Warning: {facets_dir} not found, skipping {account}")
            continue

        for facet_file in facets_dir.glob("*.json"):
            try:
                with facet_file.open() as f:
                    data = json.load(f)

                satisfaction = data.get("user_satisfaction_counts", {})

                # Count satisfied (likely_satisfied + satisfied)
                facets["satisfied"] += satisfaction.get("likely_satisfied", 0)
                facets["satisfied"] += satisfaction.get("satisfied", 0)

                # Count total
                for count in satisfaction.values():
                    facets["total"] += count

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse {facet_file}: {e}")
                continue

    # Calculate satisfaction rate
    if facets["total"] > 0:
        facets["rate"] = int((facets["satisfied"] / facets["total"]) * 100)

    return facets


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


def generate_metrics_section_ko(stats, facets):
    """
    Generate metrics table section in Korean.

    Args:
        stats: Aggregated session statistics.
        facets: Aggregated satisfaction facets.

    Returns:
        str: HTML table with metrics.
    """
    return f"""<table>
<tr>
<td align="center"><b>{stats['total_messages']:,}</b><br/><sub>처리 메시지 ({stats['unique_days']}일)</sub></td>
<td align="center"><b>{stats['total_sessions']:,}</b><br/><sub>세션 수</sub></td>
<td align="center"><b>{facets['rate']}%</b><br/><sub>만족도 ({facets['satisfied']}/{facets['total']})</sub></td>
<td align="center"><b>{stats['total_task_events']:,}</b><br/><sub>병렬 세션 이벤트</sub></td>
</tr>
</table>"""


def generate_metrics_section_en(stats, facets):
    """
    Generate metrics table section in English.

    Args:
        stats: Aggregated session statistics.
        facets: Aggregated satisfaction facets.

    Returns:
        str: HTML table with metrics.
    """
    return f"""<table>
<tr>
<td align="center"><b>{stats['total_messages']:,}</b><br/><sub>Messages ({stats['unique_days']} days)</sub></td>
<td align="center"><b>{stats['total_sessions']:,}</b><br/><sub>Sessions</sub></td>
<td align="center"><b>{facets['rate']}%</b><br/><sub>Satisfaction ({facets['satisfied']}/{facets['total']})</sub></td>
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
                f"![{tool}](https://img.shields.io/badge/"
                f"{tool_urlenc}-{count}회-{color}?style=flat-square)"
            )
        else:
            badge = (
                f"![{tool}](https://img.shields.io/badge/"
                f"{tool_urlenc}-{count}_calls-{color}?style=flat-square)"
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

    # Aggregate data
    print("Aggregating session metadata...")
    stats = aggregate_session_meta(ACCOUNTS)

    print("Aggregating satisfaction facets...")
    facets = aggregate_facets(ACCOUNTS)

    # Print summary
    print("\n=== Stats Summary ===")
    print(f"Total Messages: {stats['total_messages']:,}")
    print(f"Total Sessions: {stats['total_sessions']:,}")
    print(f"Unique Days: {stats['unique_days']}")
    print(f"Total Commits: {stats['total_commits']:,}")
    print(f"Total Tokens: {stats['total_tokens']:,}")
    print(f"Total Task Events: {stats['total_task_events']:,}")
    print(f"Satisfaction Rate: {facets['rate']}% ({facets['satisfied']}/{facets['total']})")
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
        metrics_ko = generate_metrics_section_ko(stats, facets)
        tools_ko = generate_tools_section(stats, 'ko')

        content_ko = replace_between_markers(content_ko, "metrics", metrics_ko)
        content_ko = replace_between_markers(content_ko, "tools", tools_ko)

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
        metrics_en = generate_metrics_section_en(stats, facets)
        tools_en = generate_tools_section(stats, 'en')

        content_en = replace_between_markers(content_en, "metrics", metrics_en)
        content_en = replace_between_markers(content_en, "tools", tools_en)

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
