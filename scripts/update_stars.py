"""Update Party OS star badges and the combined star-history chart.

    GITHUB_TOKEN=... python scripts/update_stars.py
    python scripts/update_stars.py --cache stars_cache.json   # reuse fetched stargazers while editing the chart

Writes assets/stars/*.json (shields.io endpoint badges) and assets/star-history.svg.
Run daily by .github/workflows/stars.yml.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"

# One entry per project; a project may span several repositories (e.g. a fork and its upstream).
PROJECTS = [
    ("Party OS", ["Roboparty/Party_OS"], "#0A3C95"),
    ("hhtools", ["Roboparty/human-humanoid-tools"], "#2563EB"),
    ("MimicLite", ["Roboparty/MimicLite"], "#0E7C86"),
    ("PartyMimic", ["Roboparty/PartyMimic"], "#C2410C"),
    ("UFO", ["Roboparty/UFO"], "#6D28D9"),
    ("I-BFM", ["Roboparty/I-BFM-Code"], "#DB2777"),
    ("P-BFM", ["Roboparty/P-BFM"], "#15803D"),
    ("INTACT-JEPA", ["zju3dv/INTACT-JEPA", "Roboparty/INTACT-JEPA"], "#CA8A04"),
]
BADGES = {"intact-jepa": ["zju3dv/INTACT-JEPA", "Roboparty/INTACT-JEPA"]}


def get(url: str, token: str | None):
    headers = {"Accept": "application/vnd.github.star+json", "User-Agent": "party-os-stars"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return json.loads(r.read())


def stargazers(repo: str, token: str | None) -> list[str]:
    out, page = [], 1
    while True:
        batch = get(f"https://api.github.com/repos/{repo}/stargazers?per_page=100&page={page}", token)
        out += [s["starred_at"] for s in batch]
        if len(batch) < 100:
            return out
        page += 1


def badge(path: Path, label: str, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schemaVersion": 1, "label": label, "message": str(count), "namedLogo": "github"}) + "\n")


def nice_step(vmax: float) -> int:
    raw = vmax / 5
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return int(m * mag)
    return int(10 * mag)


def chart(stars: dict[str, list[str]], today: dt.date) -> str:
    W, H = 960, 470
    L, R, T, B = 64, 28, 78, 118
    pw, ph = W - L - R, H - T - B
    days = {name: sorted(dt.date.fromisoformat(s[:10]) for r in repos for s in stars[r]) for name, repos, _ in PROJECTS}
    start = min(d[0] for d in days.values() if d)
    n = (today - start).days + 1
    series = []
    for name, _, color in PROJECTS:
        cum, i, ds = [], 0, days[name]
        for k in range(n):
            day = start + dt.timedelta(days=k)
            while i < len(ds) and ds[i] <= day:
                i += 1
            cum.append(i)
        series.append((name, color, cum))
    total = [sum(s[2][k] for s in series) for k in range(n)]
    step = nice_step(total[-1])
    ymax = step * (total[-1] // step + 1)

    def X(k):
        return L + pw * k / max(n - 1, 1)

    def Y(v):
        return T + ph * (1 - v / ymax)

    g = [f'<rect width="{W}" height="{H}" rx="16" fill="#fff"/>',
         f'<text x="{L}" y="40" font-size="20" font-weight="700" fill="#111827">Party OS Star History</text>',
         f'<text x="{L}" y="62" font-size="13" fill="#6B7280">Party OS + all listed projects · updated {today.isoformat()}</text>',
         f'<text x="{W - R}" y="44" text-anchor="end" font-size="28" font-weight="800" fill="#0A3C95">★ {total[-1]:,}</text>']
    for v in range(0, ymax + 1, step):
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#E5E7EB"/>')
        g.append(f'<text x="{L - 10}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="12" fill="#6B7280">{v:,}</text>')
    month = dt.date(start.year, start.month, 1)
    while month <= today:
        k = (month - start).days
        if k >= 0:
            g.append(f'<line x1="{X(k):.1f}" x2="{X(k):.1f}" y1="{T + ph}" y2="{T + ph + 5}" stroke="#9CA3AF"/>')
            g.append(f'<text x="{X(k):.1f}" y="{T + ph + 20}" text-anchor="middle" font-size="12" fill="#6B7280">{month.strftime("%b %Y")}</text>')
        month = dt.date(month.year + month.month // 12, month.month % 12 + 1, 1)
    base = [0] * n
    stride = max(1, n // 400)
    idx = list(range(0, n, stride)) + ([n - 1] if (n - 1) % stride else [])
    for name, color, cum in series:
        top = [base[k] + cum[k] for k in range(n)]
        up = " ".join(f"{X(k):.1f},{Y(top[k]):.1f}" for k in idx)
        down = " ".join(f"{X(k):.1f},{Y(base[k]):.1f}" for k in reversed(idx))
        g.append(f'<polygon points="{up} {down}" fill="{color}" fill-opacity="0.78" stroke="#fff" stroke-width="0.6"/>')
        base = top
    g.append(f'<polyline points="{" ".join(f"{X(k):.1f},{Y(total[k]):.1f}" for k in idx)}" fill="none" stroke="#111827" stroke-width="2"/>')
    g.append(f'<circle cx="{X(n - 1):.1f}" cy="{Y(total[-1]):.1f}" r="4.5" fill="#111827"/>')
    cols = 4
    for i, (name, color, cum) in enumerate(series):
        lx = L + (pw / cols) * (i % cols)
        ly = H - 62 + 24 * (i // cols)
        g.append(f'<rect x="{lx:.1f}" y="{ly - 10}" width="12" height="12" rx="3" fill="{color}"/>')
        g.append(f'<text x="{lx + 18:.1f}" y="{ly}" font-size="13" fill="#374151">{escape(name)} <tspan fill="#9CA3AF">{cum[-1]:,}</tspan></text>')
    font = "'Segoe UI', -apple-system, 'Helvetica Neue', Arial, sans-serif"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{font}">\n'
            + "\n".join(g) + "\n</svg>\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, help="read stargazers from this file if it exists, otherwise fetch and save")
    args = ap.parse_args()
    repos = sorted({r for _, rs, _ in PROJECTS for r in rs})
    if args.cache and args.cache.exists():
        stars = json.loads(args.cache.read_text())
    else:
        token = os.environ.get("GITHUB_TOKEN")
        stars = {r: stargazers(r, token) for r in repos}
        if args.cache:
            args.cache.write_text(json.dumps(stars))
    for key, rs in BADGES.items():
        badge(OUT / "stars" / f"{key}.json", "Stars", sum(len(stars[r]) for r in rs))
    badge(OUT / "stars" / "total.json", "Party OS stars", sum(len(v) for v in stars.values()))
    (OUT / "stars" / "counts.json").write_text(json.dumps({r: len(stars[r]) for r in repos}, indent=2) + "\n")
    (OUT / "star-history.svg").write_text(chart(stars, dt.datetime.now(dt.timezone.utc).date()), encoding="utf-8")
    for r in repos:
        print(f"{r}: {len(stars[r])}")
    print("total:", sum(len(v) for v in stars.values()))


if __name__ == "__main__":
    main()
