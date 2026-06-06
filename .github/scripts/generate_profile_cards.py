#!/usr/bin/env python3
import datetime as dt
import json
import os
import pathlib
import urllib.request
from collections import defaultdict


USERNAME = os.getenv("PROFILE_USERNAME", "Phantomn")
TOKEN = os.getenv("GITHUB_TOKEN", "")
API_ROOT = "https://api.github.com"
OUT_DIR = pathlib.Path("profile")


def github_get(path: str):
    url = path if path.startswith("http") else f"{API_ROOT}{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Phantomn-profile-cards",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def paginated_get(path: str, limit_pages: int = 10):
    items = []
    for page in range(1, limit_pages + 1):
        sep = "&" if "?" in path else "?"
        url = f"{path}{sep}per_page=100&page={page}"
        chunk = github_get(url)
        if not chunk:
            break
        items.extend(chunk)
        if len(chunk) < 100:
            break
    return items


def svg_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_svg(path: pathlib.Path, body: str, width: int = 495, height: int = 165):
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
  <rect width="100%" height="100%" rx="8" fill="#0d1117" stroke="#30363d"/>
  {body}
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def render_stats(user, repos):
    public_repos = user["public_repos"]
    followers = user["followers"]
    following = user["following"]
    stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
    updated = user.get("updated_at", "")[:10]
    lines = [
        '<text x="24" y="38" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="20" font-weight="700">GitHub Stats</text>',
        f'<text x="24" y="68" fill="#8b949e" font-family="Arial, sans-serif" font-size="12">Updated {svg_escape(updated)}</text>',
    ]
    metrics = [
        ("Public Repos", str(public_repos)),
        ("Followers", str(followers)),
        ("Following", str(following)),
        ("Repo Stars", str(stars)),
    ]
    card_w = 214
    card_h = 36
    positions = [(24, 86), (257, 86), (24, 126), (257, 126)]
    for (label, value), (x, y) in zip(metrics, positions):
        lines.append(f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="8" fill="#161b22" stroke="#30363d" />')
        lines.append(f'<text x="{x + 12}" y="{y + 14}" fill="#58a6ff" font-family="Arial, sans-serif" font-size="11">{svg_escape(label)}</text>')
        lines.append(f'<text x="{x + 12}" y="{y + 28}" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="15" font-weight="700">{svg_escape(value)}</text>')
    return "\n  ".join(lines)


def render_langs(lang_totals):
    total = sum(lang_totals.values()) or 1
    top = sorted(lang_totals.items(), key=lambda kv: kv[1], reverse=True)[:3]
    lines = [
        '<text x="24" y="38" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="20" font-weight="700">Top Languages</text>',
        f'<text x="24" y="68" fill="#8b949e" font-family="Arial, sans-serif" font-size="12">By repository count across public repositories</text>',
    ]
    y = 92
    palette = ["#58a6ff", "#8b949e", "#c9d1d9", "#7ee787", "#f2cc60"]
    for idx, (lang, count) in enumerate(top):
        pct = count / total
        bar_w = int(242 * pct)
        color = palette[idx % len(palette)]
        lines.append(f'<text x="24" y="{y}" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="12">{svg_escape(lang)}</text>')
        lines.append(f'<rect x="110" y="{y-10}" width="242" height="10" rx="5" fill="#161b22" stroke="#30363d" />')
        lines.append(f'<rect x="110" y="{y-10}" width="{max(bar_w, 6)}" height="10" rx="5" fill="{color}" />')
        lines.append(f'<text x="374" y="{y}" fill="#8b949e" font-family="Arial, sans-serif" font-size="12">{pct*100:.1f}%</text>')
        y += 20
    lines.append(f'<text x="24" y="158" fill="#8b949e" font-family="Arial, sans-serif" font-size="11">Total repositories analyzed: {sum(lang_totals.values()):,}</text>')
    return "\n  ".join(lines)


def render_streak(days_with_push: set[dt.date]):
    today = dt.date.today()
    streak = 0
    cursor = today
    while cursor in days_with_push:
        streak += 1
        cursor -= dt.timedelta(days=1)
    if streak < 2:
        streak = 0
    longest = 0
    run = 0
    if days_with_push:
        all_days = sorted(days_with_push)
        prev = None
        for day in all_days:
            if prev is None or (day - prev).days == 1:
                run += 1
            else:
                longest = max(longest, run)
                run = 1
            prev = day
        longest = max(longest, run)
    lines = [
        '<text x="24" y="38" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="20" font-weight="700">GitHub Streak</text>',
        f'<text x="24" y="68" fill="#8b949e" font-family="Arial, sans-serif" font-size="12">Only consecutive push days count; 1-day runs are ignored</text>',
        '<rect x="24" y="84" width="206" height="56" rx="10" fill="#161b22" stroke="#30363d" />',
        '<rect x="256" y="84" width="206" height="56" rx="10" fill="#161b22" stroke="#30363d" />',
        f'<text x="40" y="107" fill="#58a6ff" font-family="Arial, sans-serif" font-size="11">Current streak</text>',
        f'<text x="40" y="131" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="24" font-weight="700">{streak}</text>',
        f'<text x="272" y="107" fill="#58a6ff" font-family="Arial, sans-serif" font-size="11">Best streak</text>',
        f'<text x="272" y="131" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="24" font-weight="700">{longest}</text>',
    ]
    return "\n  ".join(lines)


def main():
    user = github_get(f"/users/{USERNAME}")
    repos = paginated_get(f"/users/{USERNAME}/repos?type=owner&sort=updated&direction=desc", limit_pages=2)
    repos = [r for r in repos if not r.get("fork")]

    lang_totals = defaultdict(int)
    for repo in repos:
        lang = repo.get("language")
        if lang:
            lang_totals[lang] += 1

    events = paginated_get(f"/users/{USERNAME}/events/public", limit_pages=4)
    push_days = set()
    cutoff = dt.date.today() - dt.timedelta(days=365)
    for event in events:
        if event.get("type") != "PushEvent":
            continue
        created = event.get("created_at", "")
        if not created:
            continue
        day = dt.datetime.fromisoformat(created.replace("Z", "+00:00")).date()
        if day >= cutoff:
            push_days.add(day)

    write_svg(OUT_DIR / "stats.svg", render_stats(user, repos))
    write_svg(OUT_DIR / "top-langs.svg", render_langs(lang_totals))
    write_svg(OUT_DIR / "streak.svg", render_streak(push_days))


if __name__ == "__main__":
    main()
