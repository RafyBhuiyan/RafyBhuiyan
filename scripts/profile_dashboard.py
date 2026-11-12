"""Public-data dashboard for the GitHub profile README."""
import re
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from urllib.parse import quote
from urllib.request import Request, urlopen


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.counts, self.target, self.buffer = {}, {}, None, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and 'data-date' in attrs:
            self.cells[attrs['id']] = attrs['data-date']
        if tag == 'tool-tip':
            self.target, self.buffer = attrs.get('for'), []

    def handle_data(self, data):
        if self.target:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.target:
            text = ''.join(self.buffer).strip()
            match = re.match(r'(No|[\d,]+) contributions? on ', text)
            if match:
                self.counts[self.target] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
            self.target = None


def parse_calendar(html, today):
    parser = CalendarParser()
    parser.feed(html)
    first = (today - timedelta(days=364)).isoformat()
    days = []
    for key, date in parser.cells.items():
        if first <= date <= today.isoformat():
            if key not in parser.counts:
                raise ValueError('GitHub calendar count format changed; keeping the previous dashboard.')
            days.append({'date': date, 'count': parser.counts[key]})
    days.sort(key=lambda day: day['date'])
    if len(days) != 365 or len({day['date'] for day in days}) != 365:
        raise ValueError('Incomplete public contribution calendar; keeping previous dashboard.')
    return days


def fetch_dashboard(get_json, user):
    today = datetime.now(timezone.utc).date()
    since = (today - timedelta(days=29)).isoformat()
    with urlopen(Request(f'https://github.com/users/{user}/contributions', headers={'User-Agent': 'profile-graphics'}), timeout=30) as response:
        days = parse_calendar(response.read().decode(), today)
    events = []
    for page in range(1, 4):
        batch = get_json(f'/users/{user}/events/public?per_page=100&page={page}')
        events.extend(batch)
        if len(batch) < 100:
            break
    pushes = [{'repo': event['repo']['name'], 'date': event['created_at']}
              for event in {e['id']: e for e in events}.values()
              if event['type'] == 'PushEvent' and event['actor']['login'].lower() == user.lower()
              and since <= event['created_at'][:10] <= today.isoformat()]
    pushes.sort(key=lambda push: push['date'], reverse=True)
    query = quote(f'author:{user} author-date:{since}..{today.isoformat()}')
    search = get_json(f'/search/commits?q={query}&sort=author-date&order=desc&per_page=3')
    if search.get('incomplete_results'):
        raise ValueError('Commit search is incomplete; keeping previous dashboard.')
    commits = [{'repo': item['repository']['name'], 'sha': item['sha'][:7],
                'message': item['commit']['message'].splitlines()[0],
                'date': item['commit']['author']['date'], 'url': item['html_url']}
               for item in search['items']]
    return {'calendar': days, 'push_count': len(pushes), 'pushes': pushes[:3],
            'event_limit_reached': len(events) == 300, 'commit_count': search['total_count'],
            'commits': commits, 'since': since, 'until': today.isoformat()}


def text(x, y, value, size=15, color='#cbd5e1', weight='400'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'


def panel(x, y, w, h):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#162238" stroke="#26374e"/>'


def shorten(value, limit):
    return value if len(value) <= limit else value[:limit-1] + '…'


def render_stack(start_svg):
    parts = [start_svg('Technology stack', 'Five side-by-side groups: frontend, backend, data, containers and problem solving.', 290),
             text(26, 35, 'THE TOOLKIT', 12, '#67e8f9', '600'),
             text(26, 68, 'From interface to infrastructure.', 27, '#f8fafc', '700')]
    groups = [('FRONTEND','#38bdf8',['React','Thymeleaf','HTML','CSS']),
              ('BACKEND','#a78bfa',['ASP.NET Core 10','Spring Boot','Laravel','NodeJS']),
              ('DATABASE','#34d399',['SQL','PostgreSQL','MongoDB','Firebase']),
              ('CONTAINERS','#fbbf24',['Docker','Docker Compose']),
              ('PROBLEM SOLVING','#fb7185',['C++','Data structures','& algorithms'])]
    for i,(label,color,lines) in enumerate(groups):
        x,y=26+i*184,96
        parts += [panel(x,y,172,168),
                  f'<rect x="{x+16}" y="{y+16}" width="24" height="3" rx="1.5" fill="{color}"/>',
                  text(x+16,y+42,label,11,color,'600')]
        for j,line in enumerate(lines):
            parts.append(text(x+16,y+67+j*23,line,14,'#f8fafc' if j==0 else '#cbd5e1','600' if j==0 else '400'))
    return '\n'.join(parts + ['</svg>'])


def render_dashboard(data, start_svg):
    d = data['dashboard']
    days = d['calendar']
    parts = [start_svg('GitHub contribution dashboard', 'Public contribution heatmap, indexed authored commits and public push events with recent activity.', 750),
             text(32,38,'BUILD / PUSH / CONTRIBUTE',12,'#67e8f9','600'),
             text(32,73,'Activity dashboard',28,'#f8fafc','700'),
             text(665,71,'Updated '+data['updated']+' UTC',13,'#94a3b8')]
    parts.append('''<defs>
<linearGradient id="calendar-sheen"><stop stop-color="#67e8f9" stop-opacity="0"/><stop offset=".6" stop-color="#e0faff" stop-opacity=".32"/><stop offset="1" stop-color="#67e8f9" stop-opacity="0"/></linearGradient>
</defs>
<style>
.calendar-day {animation:calendar-reveal .65s ease-out backwards;}
.calendar-sheen {animation:calendar-scan 9s linear 2s infinite;}
@keyframes calendar-reveal {from {opacity:.7;transform:translateY(5px);} to {opacity:1;transform:translateY(0);}}
@keyframes calendar-scan {0% {transform:translateX(0);opacity:0;} 8% {opacity:1;} 78% {opacity:1;} 88%,100% {transform:translateX(1030px);opacity:0;}}
@media (prefers-reduced-motion:reduce) {.calendar-day {animation:none;} .calendar-sheen {display:none;animation:none;}}
</style>''')
    stats = [(32,sum(day['count'] for day in days),'Contributions · 365 days','#38bdf8'),
             (338,d['commit_count'],'Indexed authored commits · 30 days','#a78bfa'),
             (644,str(d['push_count'])+('+' if d['event_limit_reached'] else ''),'Push events returned · 30 days','#34d399')]
    for x,value,label,color in stats:
        parts += [panel(x,98,284,94),text(x+18,140,value,31,color,'700'),text(x+18,169,label,12)]
    parts += [text(32,228,'Contribution calendar',18,'#f8fafc','600'),text(32,250,days[0]['date']+' — '+days[-1]['date'],12,'#94a3b8')]
    first = datetime.fromisoformat(days[0]['date']).date()
    offset = (first.weekday()+1)%7
    month = None
    calendar_cells = []
    for i,day in enumerate(days):
        date = datetime.fromisoformat(day['date']).date()
        column,row = divmod(i+offset,7)
        x,y=43+column*16.5,285+row*16.5
        count=day['count']
        color='#1e293b' if count==0 else '#164e63' if count<3 else '#0e7490' if count<6 else '#06b6d4' if count<10 else '#67e8f9'
        if date.month != month and (date.day <= 7 or i==0):
            parts.append(text(x,274,date.strftime('%b'),10,'#94a3b8'))
            month=date.month
        geometry = f'x="{x}" y="{y}" width="12" height="12" rx="3"'
        calendar_cells.append(f'<rect {geometry}/>')
        parts.append(f'<rect class="calendar-day" style="animation-delay:{column*.022+row*.018:.3f}s" {geometry} fill="{color}"><title>{day["date"]}: {count} contributions</title></rect>')
    parts.append('<defs><clipPath id="calendar-cells">' + ''.join(calendar_cells) + '</clipPath></defs>')
    parts.append('<g clip-path="url(#calendar-cells)" pointer-events="none"><rect class="calendar-sheen" x="-90" y="285" width="110" height="112" fill="url(#calendar-sheen)"/></g>')
    parts += [text(32,421,'Includes the contribution types shown on your public GitHub calendar.',12,'#94a3b8'),
              panel(32,442,436,202),panel(492,442,436,202),
              text(50,472,'RECENT PUSHES' if d['pushes'] else 'REPOSITORY PUSH DATES',12,'#34d399','600'),text(510,472,'RECENT AUTHORED COMMITS',12,'#a78bfa','600')]
    for i,push in enumerate(d['pushes']):
        y=500+i*49
        parts += [text(50,y,shorten(push['repo'],43),14,'#f8fafc'),text(50,y+19,push['date'][:16].replace('T',' ')+' UTC',11,'#94a3b8')]
    for i,commit in enumerate(d['commits']):
        y=500+i*49
        parts += [text(510,y,shorten(commit['message'],45),14,'#f8fafc'),text(510,y+19,shorten(commit['repo'],25)+' · '+commit['sha'],11,'#94a3b8')]
    if not d['pushes']:
        recent = sorted((r for r in data['repositories'] if r['pushed_at']), key=lambda r: r['pushed_at'], reverse=True)[:3]
        for i, repo in enumerate(recent):
            y=500+i*49
            parts += [text(50,y,shorten(repo['name'],43),14,'#f8fafc'),text(50,y+19,repo['pushed_at'][:16].replace('T',' ')+' UTC',11,'#94a3b8')]
    if not d['commits']:
        parts.append(text(510,512,'No indexed authored commits in this period.',13,'#94a3b8'))
    parts += [text(32,672,f'{len(data["repositories"])} public original repos  ·  {data["followers"]} followers  ·  {sum(r["stargazers_count"] for r in data["repositories"])} repository stars',13),
              text(32,698,'Push events may be incomplete or delayed (300-event cap); repository push dates are shown if none return.',12,'#94a3b8'),
              text(32,719,'Commits: indexed author matches. Commit counts and contribution-calendar totals measure different things.',12,'#94a3b8'),
              text(32,739,'Sources: GitHub public calendar, Events API and Commit Search API. Refreshed daily.',11,'#64748b'),'</svg>']
    return '\n'.join(parts)
