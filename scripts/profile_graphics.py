"""Generate self-contained profile SVGs from public GitHub API data."""
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen
from profile_dashboard import fetch_dashboard, render_dashboard, render_stack

ROOT = Path(__file__).resolve().parents[1]
USER = 'RafyBhuiyan'
COLORS = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24', '#fb7185', '#f97316', '#94a3b8']


def get_json(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-graphics'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urlopen(Request('https://api.github.com' + path, headers=headers), timeout=30) as response:
        return json.load(response)


def fetch_data():
    totals, repositories, page = Counter(), [], 1
    while True:
        batch = get_json(f'/users/{USER}/repos?per_page=100&page={page}')
        for repo in batch:
            if repo['fork'] or repo['private']:
                continue
            totals.update(get_json(f'/repos/{USER}/{repo["name"]}/languages'))
            repositories.append({key: repo[key] for key in ['name', 'pushed_at', 'stargazers_count', 'html_url']})
        if len(batch) < 100:
            break
        page += 1
    if not sum(totals.values()):
        raise ValueError('No language data; retaining previous graphics.')
    user = get_json(f'/users/{USER}')
    return {'languages': dict(totals), 'repositories': repositories, 'followers': user['followers'],
            'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'dashboard': fetch_dashboard(get_json, USER)}


def start_svg(title, description, height):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<style>text {{font-family:Segoe UI,Arial,sans-serif;}}</style>
<rect width="960" height="{height}" rx="20" fill="#0f172a"/>'''


def mane_radius(angle):
    # Tufted outline with a heavier lower mane, rather than a circular collar.
    return 133 + 22 * ((1 + math.cos(18 * angle)) / 2)**4 + 14 * max(0, math.sin(angle))


def mane_slice(start_fraction, fraction, inner=87):
    """Partition a tufted annulus by measured area, not simply by angle."""
    steps = 2160
    angles = [-math.pi / 2 + i * 2 * math.pi / steps for i in range(steps + 1)]
    radii = [mane_radius(a) for a in angles]
    areas = [0.0]
    for i in range(steps):
        areas.append(areas[-1] + (radii[i] * radii[i+1] - inner**2) * math.sin(2 * math.pi / steps) / 2)
    def boundary(f):
        import bisect
        target = f * areas[-1]
        index = min(steps - 1, max(0, bisect.bisect_right(areas, target) - 1))
        t = (target - areas[index]) / (areas[index+1] - areas[index])
        return angles[index] + t * (angles[index+1] - angles[index])
    first, last = boundary(start_fraction), boundary(min(1, start_fraction + fraction))
    selected = [first] + [a for a in angles if first < a < last] + [last]
    outer = [(mane_radius(a)*math.cos(a), mane_radius(a)*math.sin(a)) for a in selected]
    inside = [(inner*math.cos(a), inner*math.sin(a)) for a in reversed(selected)]
    return 'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x,y in outer + inside) + 'Z'


def render_lion(data):
    rows = sorted(data['languages'].items(), key=lambda item: (-item[1], item[0]))
    if any(value < 0 for _, value in rows) or not sum(value for _, value in rows):
        raise ValueError('Expected nonnegative language bytes with positive total.')
    rows = [(name, value) for name, value in rows if value]
    if len(rows) > 7:
        rows = rows[:6] + [('Other', sum(value for _, value in rows[6:]))]
    total = sum(value for _, value in rows)
    parts = [start_svg('My language lion', 'An alert lion snarls, breathes, blinks and flicks its tail. Colored mane sectors represent language percentages.', 560), '''
<defs>
  <radialGradient id="halo"><stop stop-color="#1e3a5f" stop-opacity=".8"/><stop offset="1" stop-color="#0f172a" stop-opacity="0"/></radialGradient>
  <linearGradient id="fur" x2=".8" y2="1"><stop stop-color="#efbb62"/><stop offset="1" stop-color="#bd702f"/></linearGradient>
  <linearGradient id="muzzle" x2="0" y2="1"><stop stop-color="#f5dda4"/><stop offset="1" stop-color="#d9b56c"/></linearGradient>
  <linearGradient id="shine" x2=".4" y2="1"><stop stop-color="#fff" stop-opacity=".28"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".16"/></linearGradient>
</defs>
<style>
.breathe {animation:breathe 3s ease-in-out infinite;transform-origin:270px 442px;}
.head {animation:tilt 6s ease-in-out infinite;}
.mane {animation:mane 6s ease-in-out infinite;}
.tail {animation:tail 2.4s ease-in-out infinite;transform-origin:337px 414px;}
.eyes {animation:blink 4.8s infinite;transform-origin:0px -4px;}
.shadow {animation:shadow 3s ease-in-out infinite;transform-origin:270px 461px;}
.spark {animation:spark 3s ease-in-out infinite;}
@keyframes breathe {0%,100% {transform:translateY(0) scale(1,1);} 50% {transform:translateY(-3px) scale(1.01,1.015);}}
@keyframes tilt {0%,100% {transform:rotate(-1.5deg);} 50% {transform:rotate(1.5deg);}}
@keyframes mane {0%,100% {transform:rotate(-2deg);} 50% {transform:rotate(2deg);}}
@keyframes tail {0%,100% {transform:rotate(-5deg);} 50% {transform:rotate(7deg);}}
@keyframes blink {0%,43%,47%,100% {transform:scaleY(1);} 45% {transform:scaleY(.08);}}
@keyframes shadow {0%,100% {transform:scaleX(1);opacity:.45;} 50% {transform:scaleX(.9);opacity:.25;}}
@keyframes spark {0%,100% {opacity:.2;} 50% {opacity:.9;}}
@media (prefers-reduced-motion:reduce) {* {animation:none !important;}}
</style>
<text x="38" y="44" fill="#67e8f9" font-size="12" letter-spacing="3">CODE HAS CHARACTER</text>
<text x="38" y="80" fill="#f8fafc" font-size="30" font-weight="700">Meet my language lion.</text>
<circle cx="267" cy="292" r="205" fill="url(#halo)"/>
<g fill="none" stroke="#38bdf8" stroke-opacity=".12"><circle cx="267" cy="292" r="178"/><circle cx="267" cy="292" r="198" stroke-dasharray="2 10"/></g>
<g class="spark" fill="#67e8f9"><path d="M89 218l3 9 9 3-9 3-3 9-3-9-9-3 9-3Z"/><circle cx="449" cy="332" r="3"/><circle cx="114" cy="380" r="2"/></g>
<ellipse class="shadow" cx="270" cy="461" rx="118" ry="13" fill="#020617"/>
<g class="breathe">
  <g class="tail"><path d="M337 414 C414 443 454 403 428 362" fill="none" stroke="#eab460" stroke-width="16" stroke-linecap="round"/><path d="M428 372 Q397 342 425 329 Q452 338 428 372" fill="#bf7b37"/></g>
  <path d="M207 317 Q172 345 184 403 L194 445 Q222 461 270 454 Q324 464 346 443 L353 398 Q359 346 321 315Z" fill="url(#fur)"/>
  <path d="M240 348L269 365L301 348L287 403L270 423L250 403Z" fill="#d39a4e"/>
  <path d="M209 346 Q185 373 195 431 L224 435 L237 360" fill="url(#fur)"/>
  <ellipse cx="224" cy="443" rx="34" ry="19" fill="url(#fur)"/><ellipse cx="315" cy="443" rx="34" ry="19" fill="url(#fur)"/>
  <g stroke="#bc8546" stroke-width="2" stroke-linecap="round"><path d="M210 444v8m10-8v9m83-9v8m10-8v9"/></g>
  <g transform="translate(265 255)"><g class="head">
    <circle r="88" fill="#bd7c39"/>
    <g class="mane">
''']
    share = 0
    for i, (language, value) in enumerate(rows):
        fraction = value / total
        parts.append(f'<path d="{mane_slice(share, fraction)}" fill="{COLORS[i]}"/>')
        share += fraction
    parts.append(f'<path d="{mane_slice(0, 1)}" fill="url(#shine)"/>')
    for i in range(18):
        a = i * math.pi / 9
        x1,y1 = 104*math.cos(a),104*math.sin(a)
        x2,y2 = (mane_radius(a)-10)*math.cos(a+.025),(mane_radius(a)-10)*math.sin(a+.025)
        parts.append(f'<path d="M{x1:.2f},{y1:.2f} Q{(x1+x2)/2+4:.2f},{(y1+y2)/2:.2f} {x2:.2f},{y2:.2f}" fill="none" stroke="#0f172a" stroke-opacity=".17" stroke-width="3" stroke-linecap="round"/>')
    parts.append('''
    </g>
    <circle cx="-72" cy="-54" r="14" fill="#d89a49"/><circle cx="72" cy="-54" r="14" fill="#d89a49"/>
    <circle cx="-72" cy="-54" r="7" fill="#7d4b2d"/><circle cx="72" cy="-54" r="7" fill="#7d4b2d"/>
    <path d="M-76-40 C-75-98 75-98 76-40 L67 17 L77 31 L61 40 Q48 76 0 90 Q-48 76-61 40 L-77 31 L-67 17Z" fill="url(#fur)"/>
    <path d="M-19-72L0-57L19-72 M-12-54L0-42L12-54" fill="none" stroke="#9a5d2f" stroke-width="4" stroke-linecap="round"/>
    <g fill="none" stroke="#573620" stroke-width="7" stroke-linecap="round"><path d="M-57-24L-23-10 M23-10L57-24"/></g>
    <g class="eyes">
      <path d="M-57-15 L-23-5 Q-40 8-57-15 M23-5 L57-15 Q40 8 23-5" fill="#70482e"/>
      <ellipse cx="-39" cy="-7" rx="7" ry="5" fill="#e9b84f"/><ellipse cx="39" cy="-7" rx="7" ry="5" fill="#e9b84f"/>
      <ellipse cx="-39" cy="-7" rx="2.5" ry="5" fill="#302a30"/><ellipse cx="39" cy="-7" rx="2.5" ry="5" fill="#302a30"/>
      <g fill="#fff"><circle cx="-37" cy="-8" r="1.2"/><circle cx="41" cy="-8" r="1.2"/></g>
    </g>
    <path d="M-26 64L-18 81L-9 78L0 91L9 78L18 81L26 64" fill="#fff0c8"/>
    <path d="M-10-16 Q-15 10-26 27 L26 27 Q15 10 10-16" fill="#edb965"/>
    <path d="M-36 40 Q0 31 36 40 L28 70 Q0 91-28 70Z" fill="#362128"/>
    <path d="M-17 74Q0 64 17 74L0 80Z" fill="#994d45"/>
    <ellipse cx="-21" cy="32" rx="29" ry="16" fill="url(#muzzle)"/><ellipse cx="21" cy="32" rx="29" ry="16" fill="url(#muzzle)"/>
    <path d="M-30 44L-16 45L-23 69Z M16 45L30 44L23 69Z M-17 72L-11 59L-6 76Z M6 76L11 59L17 72Z" fill="#fff1d5"/>
    <path d="M-8 45H8L6 51H-6Z" fill="#fff1d5"/>
    <path d="M-19 21 Q0 13 19 21 L8 34 Q0 40-8 34Z" fill="#4e3431"/>
    <path d="M-9 22Q0 19 9 22" fill="none" stroke="#a87868" stroke-width="3" stroke-linecap="round"/>
    <path d="M0 35V43 M-32 42L-42 37 M32 42L42 37" fill="none" stroke="#71452d" stroke-width="3" stroke-linecap="round"/>
    <g fill="none" stroke="#71452d" stroke-width="1.8" stroke-linecap="round" opacity=".65"><path d="M-33 26L-68 16 M-35 32L-72 31 M-33 38L-64 46 M33 26L68 16 M35 32L72 31 M33 38L64 46"/></g>
    <g fill="#a1744e"><circle cx="-29" cy="36" r="2"/><circle cx="-36" cy="43" r="2"/><circle cx="29" cy="36" r="2"/><circle cx="36" cy="43" r="2"/></g>
  </g></g>
<path d="M319 346 Q343 373 333 431 L304 435 L291 360" fill="url(#fur)"/>
<g fill="#f4e1b3"><path d="M201 452L204 464L210 452 M215 454L220 467L224 453 M306 454L310 467L315 453 M320 452L326 464L329 450"/></g>
</g>
<text x="554" y="131" fill="#94a3b8" font-size="12" letter-spacing="2">MY PUBLIC CODE MIX</text>
''')
    for i, (language, value) in enumerate(rows):
        y, percent = 168 + i * 42, value / total * 100
        label = '&lt;0.1%' if percent < .1 else f'{percent:.1f}%'
        parts.append(f'<circle cx="562" cy="{y-6}" r="5" fill="{COLORS[i]}"/>'
                     f'<text x="582" y="{y}" fill="#e2e8f0" font-size="17">{escape(language)}</text>'
                     f'<text x="914" y="{y}" text-anchor="end" fill="{COLORS[i]}" font-size="18" font-weight="700">{label}</text>'
                     f'<path d="M554 {y+14}H914" stroke="#1e293b"/>')
    parts.append(f'''<text x="38" y="513" fill="#94a3b8" font-size="13">Colored mane area = language share. Code bytes, not hours or proficiency.</text>
<text x="38" y="536" fill="#64748b" font-size="12">{len(data['repositories'])} public, non-fork owned repositories · Updated {data['updated']} UTC</text></svg>''')
    return '\n'.join(parts)



if __name__ == '__main__':
    import sys
    snapshot = ROOT / 'images' / 'profile-data.json'
    data = json.loads(snapshot.read_text(encoding='utf-8')) if '--offline' in sys.argv else fetch_data()
    lion, activity = render_lion(data), render_dashboard(data, start_svg)
    stack = render_stack(start_svg)
    (ROOT / 'images' / 'language-lion.svg').write_text(lion, encoding='utf-8')
    (ROOT / 'images' / 'github-activity.svg').write_text(activity, encoding='utf-8')
    (ROOT / 'images' / 'tech-stack.svg').write_text(stack, encoding='utf-8')
    snapshot.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(f'Generated lion and activity cards from {len(data["repositories"])} repositories.')
