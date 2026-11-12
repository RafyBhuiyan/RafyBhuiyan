"""Generate a self-contained animated SVG from public, non-fork repository bytes."""
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = "RafyBhuiyan"


def get_json(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "language-cats"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
        return json.load(response)


def fetch_languages():
    totals = Counter()
    count = 0
    page = 1
    while True:
        repos = get_json(f"/users/{USER}/repos?per_page=100&page={page}")
        for repo in repos:
            if repo["fork"] or repo["private"]:
                continue
            languages = get_json(f'/repos/{USER}/{repo["name"]}/languages')
            totals.update(languages)
            count += 1
        if len(repos) < 100:
            break
        page += 1
    if not sum(totals.values()):
        raise ValueError("No language data returned; preserving the previous chart.")
    return totals, count


def render(totals, count):
    total = sum(totals.values())
    if total <= 0 or any(value < 0 for value in totals.values()):
        raise ValueError("Language byte counts must have a positive total and no negatives.")
    rows = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    if len(rows) > 7:
        rows = rows[:6] + [("Other", sum(value for _, value in rows[6:]))]
    height = 158 + len(rows) * 64
    colors = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185", "#2dd4bf", "#94a3b8"]
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc">
<title id="title">Rafy's language cats</title>
<desc id="desc">Language shares by code bytes across {count} public, non-fork owned repositories. Cats walk along each language bar.</desc>
<style>
text {{ font-family:Segoe UI,Arial,sans-serif; }}
.walk {{ animation:walk 7s ease-in-out infinite alternate; }}
.tail {{ transform-box:fill-box; transform-origin:left center; animation:wag .8s ease-in-out infinite alternate; }}
@keyframes walk {{ from {{ transform:translateX(0); }} to {{ transform:translateX(var(--travel)); }} }}
@keyframes wag {{ to {{ transform:rotate(-22deg); }} }}
@media (prefers-reduced-motion:reduce) {{ .walk,.tail {{ animation:none; }} }}
</style>
<rect width="960" height="{height}" rx="18" fill="#0f172a"/>
<text x="32" y="43" fill="#f8fafc" font-size="25" font-weight="700">My language companions</text>
<text x="32" y="70" fill="#94a3b8" font-size="14">Public code, one paw at a time.</text>''']
    for i, (language, value) in enumerate(rows):
        y = 108 + i * 64
        percentage = value / total * 100
        width = 620 * value / total
        label = "&lt;0.1%" if percentage < .1 else f"{percentage:.1f}%"
        color = colors[i]
        parts.append(f'''<g>
<text x="32" y="{y + 14}" fill="#e2e8f0" font-size="17">{escape(language)}</text>
<rect x="180" y="{y + 4}" width="620" height="14" rx="7" fill="#1e293b"/>
<rect x="180" y="{y + 4}" width="{width:.3f}" height="14" rx="7" fill="{color}"/>
<text x="920" y="{y + 16}" text-anchor="end" fill="{color}" font-size="18" font-weight="700">{label}</text>
<g transform="translate(180 {y - 7})"><g class="walk" style="--travel:{max(0, width - 30):.3f}px;animation-delay:-{i * .7}s">
<g fill="{color}" stroke="{color}" stroke-linecap="round">
<path class="tail" d="M7 -5 Q-8 -8 -4 -20" fill="none" stroke-width="4"/>
<ellipse cx="14" cy="-7" rx="12" ry="7"/>
<path d="M8 -4 L5 2 M21 -4 L24 2" stroke-width="4"/>
<circle cx="27" cy="-13" r="8"/>
<path d="M20 -17 L20 -26 L26 -20 M28 -20 L34 -26 L35 -15"/>
</g><circle cx="30" cy="-14" r="1.5" fill="#0f172a"/>
</g></g></g>''')
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts.append(f'''<text x="32" y="{height - 42}" fill="#94a3b8" font-size="13">Code bytes, not proficiency or time spent. Forks and private repositories excluded.</text>
<text x="32" y="{height - 20}" fill="#94a3b8" font-size="13">{count} owned repositories · Updated {date} UTC · Source: GitHub Languages API</text></svg>''')
    return "\n".join(parts)


if __name__ == "__main__":
    totals, count = fetch_languages()
    output = ROOT / "images" / "language-cats.svg"
    output.write_text(render(totals, count), encoding="utf-8")
    print(f"Updated {output.name} from {count} repositories.")
