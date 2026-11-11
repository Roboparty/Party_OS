"""Build the Party OS roadmap figures (English and Chinese) from one layout.

    python scripts/build_roadmap.py            # SVG + PNG (PNG needs `pip install playwright` and Edge or Chromium)
    python scripts/build_roadmap.py --svg-only

Edit the text in ROADMAP below; both languages share the same layout.
"""

from __future__ import annotations

import argparse
import base64
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

W, H = 1400, 910
LINE_Y = 520
CARD_W = 300
FONT = "'Segoe UI', -apple-system, 'Helvetica Neue', Arial, 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif"
BRAND = "#0A3C95"
INK = "#1F2937"
MUTED = "#6B7280"

# side: "above" stacks cards upward from the timeline, "below" downward. Cards are listed top to bottom.
# Wrap text in **...** to highlight it.
COLUMNS = [
    dict(key="mc", x=310, side="below", color="#0A3C95"),
    dict(key="ip", x=545, side="above", color="#0E7C86"),
    dict(key="wbm", x=770, side="below", color="#6D28D9"),
    dict(key="ah", x=1000, side="above", color="#C2410C"),
    dict(key="rsi", x=1225, side="below", color="#15803D"),
]
HARDWARE_X = [60, 125, 190]

ROADMAP = {
    "en": {
        "hardware_caption": "Hardware",
        "hardware": ["Joint Module", "Robot", "SDK"],
        "mc": ("Motion Control Infra", [
            ("Data", ["generate · data generation", "hhtools · retargeting", "Ego Humanoid · robot-free capture"]),
            ("BFM Control Algorithms", ["Supervised · MimicLite · **PartyMimic**", "Unsupervised · UFO"]),
            ("Deployment", ["sim2real & real2sim"]),
        ]),
        "ip": ("Interaction & Perception Infra", [
            ("Perceptive Loco", ["Stable perceptive locomotion"]),
            ("Perceptive Parkour · HSI", ["Human–scene interaction"]),
            ("Object Interaction · HOI", ["Low-dynamic: carrying, moving", "High-dynamic: ball sports"]),
        ]),
        "wbm": ("Whole-Body Manipulation Infra", [
            ("VLA / WAM", []),
            ("Real2Sim2Real", []),
            ("Onboard Inference Infra", []),
        ]),
        "ah": ("Agentic Humanoid", [
            ("Multi-task Decomposition", ["Polling & RL + SFT", "EQA & Task Planner"]),
            ("Scene Semantics & Navigation", ["Agent VLN"]),
            ("Hardware Infra", ["Time sync · physical latency"]),
            ("Loco / VLA Are Our Skills", []),
        ]),
        "rsi": ("Agent RSI System", [
            ("Agents Across the Company", ["Agent Tech · Agent Engineering", "Agent Ops · Agent Company"]),
            ("Plan → Execute → Verify", ["Values · Authorization · Oversight"]),
        ]),
    },
    "zh": {
        "hardware_caption": "硬件",
        "hardware": ["关节模组", "整机", "SDK"],
        "mc": ("运控 Infra", [
            ("数据", ["数据生成（generate）", "重定向（hhtools）", "无本体数采（Ego Humanoid）"]),
            ("BFM 控制算法", ["监督学习：MimicLite · **PartyMimic**", "无监督学习：UFO"]),
            ("部署", ["sim2real & real2sim"]),
        ]),
        "ip": ("交互感知 Infra", [
            ("稳定感控", ["Perceptive Loco"]),
            ("场景交互 · HSI", ["Perceptive Parkour"]),
            ("物体交互 · HOI", ["低动态交互：搬运、移动", "高动态交互：球类"]),
        ]),
        "wbm": ("全身操作 Infra", [
            ("VLA / WAM", []),
            ("Real2Sim2Real", []),
            ("端侧推理 Infra", []),
        ]),
        "ah": ("Agentic Humanoid", [
            ("多任务拆分", ["轮询 & RL + SFT", "EQA & Task Planner"]),
            ("场景语义理解和导航", ["Agent VLN"]),
            ("底层硬件 Infra", ["时间同步 · 物理延迟"]),
            ("Loco / VLA 是我们的技能", []),
        ]),
        "rsi": ("Agent RSI System", [
            ("Agent 公司", ["Agent 技术 · Agent 工程", "Agent 运营 · Agent 公司"]),
            ("规划 → 执行 → 验证", ["价值观 · 授权 · 监管"]),
        ]),
    },
}

TITLE_FS, TITLE_LH = 16, 22
LINE_FS, LINE_LH = 14.5, 21
PAD_TOP, PAD_BOTTOM, CARD_GAP = 14, 12, 12
STEM_GAP = 72


def text_width(s: str, fs: float) -> float:
    s = s.replace("**", "")
    return sum(fs if ord(c) > 0x2E80 else fs * 0.56 for c in s)


def card_height(lines: list[str]) -> int:
    return PAD_TOP + TITLE_LH + LINE_LH * len(lines) + PAD_BOTTOM


def rich(s: str, color: str) -> str:
    parts = re.split(r"(\*\*.+?\*\*)", s)
    out = []
    for p in parts:
        if p.startswith("**"):
            out.append(f'<tspan font-weight="700" fill="{color}">{escape(p[2:-2])}</tspan>')
        elif p:
            out.append(escape(p))
    return "".join(out)


def pill(cx: float, cy: float, label: str, color: str) -> str:
    w = text_width(label, 16) + 32
    return (
        f'<rect x="{cx - w / 2:.1f}" y="{cy - 16}" width="{w:.1f}" height="32" rx="16" fill="{color}"/>'
        f'<text x="{cx}" y="{cy + 5.5}" text-anchor="middle" font-size="16" font-weight="700" fill="#fff">{escape(label)}</text>'
    )


def column(col: dict, title: str, cards: list[tuple[str, list[str]]]) -> str:
    x, color, above = col["x"], col["color"], col["side"] == "above"
    heights = [card_height(lines) for _, lines in cards]
    total = sum(heights) + CARD_GAP * (len(cards) - 1)
    top = LINE_Y - STEM_GAP - total if above else LINE_Y + STEM_GAP
    bottom = top + total
    g = []
    stem_end = top + heights[0] / 2 if above else bottom - heights[-1] / 2
    g.append(f'<line x1="{x}" y1="{LINE_Y}" x2="{x}" y2="{stem_end:.1f}" stroke="{color}" stroke-width="2" stroke-dasharray="5 5" opacity="0.55"/>')
    y = top
    for (ctitle, lines), h in zip(cards, heights):
        x0 = x - CARD_W / 2
        g.append(f'<rect x="{x0}" y="{y}" width="{CARD_W}" height="{h}" rx="10" fill="#fff" stroke="{color}" stroke-opacity="0.35" stroke-width="1.2" filter="url(#shadow)"/>')
        g.append(f'<rect x="{x0}" y="{y + 10}" width="4" height="{h - 20}" rx="2" fill="{color}"/>')
        ty = y + PAD_TOP + 16
        g.append(f'<text x="{x0 + 18}" y="{ty}" font-size="{TITLE_FS}" font-weight="700" fill="{INK}">{rich(ctitle, color)}</text>')
        for i, line in enumerate(lines):
            g.append(f'<text x="{x0 + 18}" y="{ty + LINE_LH * (i + 1)}" font-size="{LINE_FS}" fill="{MUTED}">{rich(line, color)}</text>')
        y += h + CARD_GAP
    g.append(f'<circle cx="{x}" cy="{LINE_Y}" r="13" fill="#fff" stroke="{color}" stroke-width="5"/>')
    g.append(pill(x, LINE_Y + 40 if above else LINE_Y - 40, title, color))
    return "\n".join(g)


def build_svg(lang: str) -> str:
    t = ROADMAP[lang]
    logo = base64.b64encode((ASSETS / "robo-party-lab.png").read_bytes()).decode()
    logo_w = 250
    logo_h = logo_w * 230 / 1013
    banner_x0, banner_x1 = COLUMNS[0]["x"] - 110, W - 30
    body = [
        f'<rect width="{W}" height="{H}" rx="18" fill="#FFFFFF"/>',
        f'<image href="data:image/png;base64,{logo}" x="{(W - logo_w) / 2}" y="18" width="{logo_w}" height="{logo_h:.1f}"/>',
        f'<rect x="{banner_x0}" y="88" width="{banner_x1 - banner_x0}" height="34" rx="17" fill="url(#banner)"/>',
        f'<text x="{(banner_x0 + banner_x1) / 2}" y="111" text-anchor="middle" font-size="18" font-weight="700" fill="#fff" letter-spacing="1">Party OS</text>',
        f'<rect x="20" y="{LINE_Y - 7}" width="{W - 90}" height="14" rx="7" fill="url(#line)"/>',
        f'<polygon points="{W - 76},{LINE_Y - 30} {W - 22},{LINE_Y} {W - 76},{LINE_Y + 30}" fill="{BRAND}"/>',
    ]
    for x, label in zip(HARDWARE_X, t["hardware"]):
        body.append(f'<circle cx="{x}" cy="{LINE_Y}" r="10" fill="#fff" stroke="#94A3B8" stroke-width="4"/>')
        body.append(f'<text x="{x}" y="{LINE_Y + 36}" text-anchor="middle" font-size="13" font-weight="600" fill="{MUTED}">{escape(label)}</text>')
    body.append(f'<text x="{HARDWARE_X[1]}" y="{LINE_Y - 30}" text-anchor="middle" font-size="13" font-weight="700" fill="#94A3B8" letter-spacing="1">{escape(t["hardware_caption"].upper())}</text>')
    for col in COLUMNS:
        title, cards = t[col["key"]]
        body.append(column(col, title, cards))
    defs = f"""<defs>
  <linearGradient id="banner" x1="0" x2="1"><stop offset="0" stop-color="{BRAND}"/><stop offset="1" stop-color="#2563EB"/></linearGradient>
  <linearGradient id="line" x1="0" x2="1"><stop offset="0" stop-color="#CBD5E1"/><stop offset="0.16" stop-color="{BRAND}"/><stop offset="1" stop-color="{BRAND}"/></linearGradient>
  <filter id="shadow" x="-10%" y="-20%" width="120%" height="150%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0F172A" flood-opacity="0.10"/></filter>
</defs>"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">\n'
        + defs + "\n" + "\n".join(body) + "\n</svg>\n"
    )


def render_png(svg_path: Path, png_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge")
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        page.goto(svg_path.as_uri())
        page.screenshot(path=str(png_path), omit_background=True)
        browser.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg-only", action="store_true")
    args = ap.parse_args()
    for lang in ROADMAP:
        svg = ASSETS / f"party-os-roadmap-{lang}.svg"
        svg.write_text(build_svg(lang), encoding="utf-8")
        print("wrote", svg.relative_to(ROOT))
        if not args.svg_only:
            png = svg.with_suffix(".png")
            render_png(svg, png)
            print("wrote", png.relative_to(ROOT))


if __name__ == "__main__":
    main()
