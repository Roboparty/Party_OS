"""Update Party OS star badges and the combined star-history chart.

    python scripts/update_stars.py                         # record today's star counts and redraw
    python scripts/update_stars.py --history history.json  # redraw from another history file (for editing the chart)

GitHub no longer exposes when each star was given (REST stargazers returns 404 and GraphQL reports the
current time), so the history is built from daily snapshots of the public star counts, kept in
assets/stars/history.json. Before the first snapshot, each repository is drawn as a straight line from 0
stars on its creation date; the chart marks that part as interpolated.

Writes assets/stars/*.json (shields.io endpoint badges) and assets/star-history.svg.
Run daily by .github/workflows/stars.yml.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
HISTORY = OUT / "stars" / "history.json"

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
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "party-os-stars"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = f"GET {url} failed: {e.code} {e.read().decode(errors='replace')[:200]}"
        print(f"::error::{msg}")
        raise SystemExit(msg) from None


def badge(path: Path, label: str, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schemaVersion": 1, "label": label, "message": str(count), "namedLogo": "github"}) + "\n")


def nice_step(vmax: float) -> int:
    raw = max(vmax / 5, 1)
    mag = 10 ** (len(str(int(raw))) - 1)
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return int(m * mag)
    return int(10 * mag)


def repo_curve(created: dt.date, snaps: list[tuple[dt.date, int]], start: dt.date, n: int) -> list[float]:
    """Daily star count of one repository: 0 at creation, linear up to the first snapshot, then the snapshots."""
    points = [(created, 0)] + [(d, c) for d, c in snaps if d > created]
    out = []
    for k in range(n):
        day = start + dt.timedelta(days=k)
        if day <= points[0][0]:
            out.append(0.0)
            continue
        for (d0, c0), (d1, c1) in zip(points, points[1:]):
            if day <= d1:
                out.append(c0 + (c1 - c0) * (day - d0).days / max((d1 - d0).days, 1))
                break
        else:
            out.append(float(points[-1][1]))
    return out


def chart(history: dict, today: dt.date) -> str:
    W, H = 960, 470
    L, R, T, B = 64, 28, 78, 118
    pw, ph = W - L - R, H - T - B
    created = {r: dt.date.fromisoformat(d) for r, d in history["created"].items()}
    dates = sorted(history["snapshots"])
    first = dt.date.fromisoformat(dates[0])
    start = min(created.values())
    n = (today - start).days + 1
    series = []
    for name, repos, color in PROJECTS:
        cum = [0.0] * n
        for r in repos:
            snaps = [(dt.date.fromisoformat(d), history["snapshots"][d][r]) for d in dates if r in history["snapshots"][d]]
            cum = [a + b for a, b in zip(cum, repo_curve(created[r], snaps, start, n))]
        series.append((name, color, cum))
    total = [sum(s[2][k] for s in series) for k in range(n)]
    step = nice_step(total[-1])
    ymax = step * (int(total[-1]) // step + 1)

    def X(k):
        return L + pw * k / max(n - 1, 1)

    def Y(v):
        return T + ph * (1 - v / ymax)

    kf = (first - start).days
    g = [f'<rect width="{W}" height="{H}" rx="16" fill="#fff"/>',
         '<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<rect width="8" height="8" fill="#fff" fill-opacity="0.35"/><line x1="0" y1="0" x2="0" y2="8" stroke="#fff" stroke-width="3" stroke-opacity="0.7"/>'
         '</pattern></defs>',
         f'<text x="{L}" y="40" font-size="20" font-weight="700" fill="#111827">Party OS Star History</text>',
         f'<text x="{L}" y="62" font-size="13" fill="#6B7280">Party OS + all listed projects · daily counts since {first.isoformat()}, '
         f'interpolated from creation dates before that</text>',
         f'<text x="{W - R}" y="44" text-anchor="end" font-size="28" font-weight="800" fill="#0A3C95">★ {int(total[-1]):,}</text>']
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
    base = [0.0] * n
    stride = max(1, n // 400)
    idx = sorted(set(range(0, n, stride)) | {n - 1, min(kf, n - 1)})
    for name, color, cum in series:
        top = [base[k] + cum[k] for k in range(n)]
        up = " ".join(f"{X(k):.1f},{Y(top[k]):.1f}" for k in idx)
        down = " ".join(f"{X(k):.1f},{Y(base[k]):.1f}" for k in reversed(idx))
        g.append(f'<polygon points="{up} {down}" fill="{color}" fill-opacity="0.78" stroke="#fff" stroke-width="0.6"/>')
        base = top
    if kf > 0:
        g.append(f'<rect x="{L}" y="{T}" width="{X(kf) - L:.1f}" height="{ph}" fill="url(#hatch)"/>')
    pre = [k for k in idx if k <= kf]
    post = [k for k in idx if k >= kf]
    g.append(f'<polyline points="{" ".join(f"{X(k):.1f},{Y(total[k]):.1f}" for k in pre)}" fill="none" stroke="#111827" '
             f'stroke-width="2" stroke-dasharray="6 5"/>')
    if len(post) > 1:
        g.append(f'<polyline points="{" ".join(f"{X(k):.1f},{Y(total[k]):.1f}" for k in post)}" fill="none" stroke="#111827" stroke-width="2.4"/>')
    g.append(f'<line x1="{X(kf):.1f}" x2="{X(kf):.1f}" y1="{T}" y2="{T + ph}" stroke="#111827" stroke-dasharray="3 4" stroke-opacity="0.6"/>')
    g.append(f'<text x="{X(kf) - 6:.1f}" y="{T + 14}" text-anchor="end" font-size="12" fill="#374151">interpolated</text>')
    if W - R - X(kf) > 110:
        g.append(f'<text x="{X(kf) + 6:.1f}" y="{T + 14}" font-size="12" fill="#374151">tracked daily →</text>')
    g.append(f'<circle cx="{X(n - 1):.1f}" cy="{Y(total[-1]):.1f}" r="4.5" fill="#111827"/>')
    cols = 4
    for i, (name, color, cum) in enumerate(series):
        lx = L + (pw / cols) * (i % cols)
        ly = H - 62 + 24 * (i // cols)
        g.append(f'<rect x="{lx:.1f}" y="{ly - 10}" width="12" height="12" rx="3" fill="{color}"/>')
        g.append(f'<text x="{lx + 18:.1f}" y="{ly}" font-size="13" fill="#374151">{escape(name)} <tspan fill="#9CA3AF">{int(cum[-1]):,}</tspan></text>')
    font = "'Segoe UI', -apple-system, 'Helvetica Neue', Arial, sans-serif"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{font}">\n'
            + "\n".join(g) + "\n</svg>\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", type=Path, help="redraw from this history file without calling the API")
    args = ap.parse_args()
    repos = sorted({r for _, rs, _ in PROJECTS for r in rs})
    today = dt.datetime.now(dt.timezone.utc).date()
    if args.history:
        history = json.loads(args.history.read_text())
    else:
        token = os.environ.get("GITHUB_TOKEN")
        history = json.loads(HISTORY.read_text()) if HISTORY.exists() else {"created": {}, "snapshots": {}}
        info = {r: get(f"https://api.github.com/repos/{r}", token) for r in repos}
        counts = {r: info[r]["stargazers_count"] for r in repos}
        for r in repos:
            history["created"].setdefault(r, info[r]["created_at"][:10])
        snaps = history["snapshots"]
        if not snaps or snaps[max(snaps)] != counts:
            snaps[today.isoformat()] = counts
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(history, indent=1, sort_keys=True) + "\n")
    last = history["snapshots"][max(history["snapshots"])]
    for key, rs in BADGES.items():
        badge(OUT / "stars" / f"{key}.json", "Stars", sum(last[r] for r in rs))
    badge(OUT / "stars" / "total.json", "Party OS stars", sum(last.values()))
    (OUT / "star-history.svg").write_text(chart(history, today), encoding="utf-8")
    for r in repos:
        print(f"{r}: {last[r]}")
    print("total:", sum(last.values()))


if __name__ == "__main__":
    main()
