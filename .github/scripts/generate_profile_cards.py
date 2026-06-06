#!/usr/bin/env python3
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
  <rect width="100%" height="100%" rx="8" fill="#040F0F" stroke="#E4E2E2"/>
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
        '<rect x="18" y="18" width="106" height="129" rx="12" fill="#071A1A" stroke="#E4E2E2" />',
        '<rect x="18" y="18" width="106" height="5" rx="2.5" fill="#2F97C1" />',
        '<text x="32" y="48" fill="#0CF574" font-family="Arial, sans-serif" font-size="11" font-weight="700">GITHUB SUMMARY</text>',
        '<text x="32" y="76" fill="#E4E2E2" font-family="Arial, sans-serif" font-size="18" font-weight="700">Public</text>',
        '<text x="32" y="96" fill="#E4E2E2" font-family="Arial, sans-serif" font-size="18" font-weight="700">Activity</text>',
        f'<text x="32" y="122" fill="#0CF574" font-family="Arial, sans-serif" font-size="10">Updated {svg_escape(updated)}</text>',
    ]
    metrics = [
        ("Repos", str(public_repos)),
        ("Followers", str(followers)),
        ("Following", str(following)),
        ("Stars", str(stars)),
    ]
    positions = [(144, 18), (315, 18), (144, 79), (315, 79)]
    for (label, value), (x, y) in zip(metrics, positions):
        lines.append(f'<rect x="{x}" y="{y}" width="162" height="55" rx="12" fill="#071A1A" stroke="#E4E2E2" />')
        lines.append(f'<text x="{x + 14}" y="{y + 19}" fill="#0CF574" font-family="Arial, sans-serif" font-size="11">{svg_escape(label)}</text>')
        lines.append(f'<text x="{x + 14}" y="{y + 41}" fill="#E4E2E2" font-family="Arial, sans-serif" font-size="22" font-weight="700">{svg_escape(value)}</text>')
    lines.append('<text x="144" y="150" fill="#0CF574" font-family="Arial, sans-serif" font-size="10">Public GitHub data · generated locally</text>')
    return "\n  ".join(lines)


def render_langs(lang_totals):
    total = sum(lang_totals.values()) or 1
    top = sorted(lang_totals.items(), key=lambda kv: kv[1], reverse=True)[:3]
    lines = [
        '<text x="24" y="38" fill="#E4E2E2" font-family="Arial, sans-serif" font-size="20" font-weight="700">Top Languages</text>',
        f'<text x="24" y="68" fill="#0CF574" font-family="Arial, sans-serif" font-size="12">Public repos by language</text>',
    ]
    y = 92
    palette = ["#2F97C1", "#0CF574", "#F5B700"]
    for idx, (lang, count) in enumerate(top):
        pct = count / total
        bar_w = int(242 * pct)
        color = palette[idx % len(palette)]
        lines.append(f'<text x="24" y="{y}" fill="#E4E2E2" font-family="Arial, sans-serif" font-size="12">{svg_escape(lang)}</text>')
        lines.append(f'<rect x="110" y="{y-10}" width="242" height="10" rx="5" fill="#071A1A" stroke="#E4E2E2" />')
        lines.append(f'<rect x="110" y="{y-10}" width="{max(bar_w, 6)}" height="10" rx="5" fill="{color}" />')
        lines.append(f'<text x="374" y="{y}" fill="#0CF574" font-family="Arial, sans-serif" font-size="12">{pct*100:.1f}%</text>')
        y += 20
    lines.append(f'<text x="24" y="158" fill="#0CF574" font-family="Arial, sans-serif" font-size="11">Repos analyzed: {sum(lang_totals.values()):,}</text>')
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

    write_svg(OUT_DIR / "stats.svg", render_stats(user, repos))
    write_svg(OUT_DIR / "top-langs.svg", render_langs(lang_totals))


if __name__ == "__main__":
    main()
