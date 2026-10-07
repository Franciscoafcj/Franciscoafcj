"""Regenerate the public avatar and contribution cards. Never store access tokens."""
import io
import json
import os
from pathlib import Path
from datetime import date, timedelta
from html import escape
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
USER = "Franciscoafcj"
CSS = """text{font-family:Consolas,'Liberation Mono',monospace}
.reveal{animation:reveal .5s both}
@keyframes reveal{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}
@media(prefers-reduced-motion:reduce){.reveal{animation:none}}"""
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

def text(x, y, value, size=12, color="#9eafbd", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'

def frame(width, height, title, description, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>'
            f'<desc>{escape(description)}</desc><style>{CSS}</style>'
            f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="14" fill="#0d1117" stroke="#303b49"/>'
            f'<path d="M1 48H{width-1}" stroke="#303b49"/>'
            '<circle cx="23" cy="25" r="5" fill="#ff6b6b"/><circle cx="42" cy="25" r="5" fill="#f2c76c"/>'
            '<circle cx="61" cy="25" r="5" fill="#63d6ab"/>'
            + text(83,30,title) + body + '</svg>\n')

def read_public_profile():
    token = os.environ["METRICS_TOKEN"]
    query = """query($login:String!) {
      user(login:$login) {
        avatarUrl(size:400)
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date weekday contributionCount contributionLevel } }
          }
        }
      }
    }"""
    req = Request("https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "Franciscoafcj-profile-art"})
    with urlopen(req, timeout=45) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError("GitHub did not return a valid public profile; previous SVGs are preserved.")
    user = result["data"]["user"]
    return user["avatarUrl"], user["contributionsCollection"]["contributionCalendar"]

def validate_calendar(calendar):
    weeks = calendar["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    if not 50 <= len(weeks) <= 54 or not 350 <= len(days) <= 372:
        raise ValueError("Incomplete calendar")
    dates = [date.fromisoformat(d["date"]) for d in days]
    if any(b-a != timedelta(days=1) for a,b in zip(dates, dates[1:])):
        raise ValueError("Non-contiguous calendar dates")
    if any(type(d["contributionCount"]) is not int or d["contributionCount"] < 0
           or d["contributionLevel"] not in LEVELS
           or d["weekday"] != (dt.weekday()+1) % 7 for d,dt in zip(days,dates)):
        raise ValueError("Invalid calendar values")
    if sum(d["contributionCount"] for d in days) != calendar["totalContributions"]:
        raise ValueError("Contribution total mismatch")
    return days

def render_calendar(calendar):
    days = validate_calendar(calendar)
    weeks = calendar["weeks"]
    width = 40 + 16 * len(weeks)
    months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    style = """text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}
.label{fill:#7d8590;font-size:13px;font-weight:600}
.total{fill:#57606a;font-size:15px;font-weight:600}
.cell{transform-box:fill-box;transform-origin:center;animation:pop .55s ease-out both}
.active{animation:pop .55s ease-out both,flash .7s ease-out both}
@keyframes pop{0%{opacity:0;transform:scale(.2)}60%{opacity:1;transform:scale(1.1)}100%{opacity:1;transform:scale(1)}}
@keyframes flash{0%,45%{filter:brightness(2.4)}100%{filter:brightness(1)}}
@media(prefers-color-scheme:dark){.total{fill:#e6edf3}}
@media(prefers-reduced-motion:reduce){.cell{opacity:1;transform:none;filter:none;animation:none!important}}"""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="158" viewBox="0 0 {width} 158" role="img">',
        '<title>Contribuições de Francisco Junior no GitHub</title>',
        f'<desc>Atividade real de {USER}, de {days[0]["date"]} a {days[-1]["date"]}. '
        'Cada quadrado representa um dia; a intensidade do verde indica o volume de contribuições.</desc>',
        f'<style>{style}</style>',
    ]
    last_month = None
    for col, week in enumerate(weeks):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month:
            parts.append(f'<text class="label" x="{34+col*16}" y="16">{months[first.month-1]}</text>')
            last_month = first.month
        for day in week["contributionDays"]:
            row = day["weekday"]
            color = COLORS[LEVELS.index(day["contributionLevel"])]
            classes = "cell active" if day["contributionCount"] else "cell"
            delay = col * .065 + row * .036
            parts.append(
                f'<rect class="{classes}" x="{34+col*16}" y="{24+row*16}" width="13" height="13" '
                f'rx="2.5" fill="{color}" style="animation-delay:{delay:.3f}s">'
                f'<title>{day["date"]}: {day["contributionCount"]} contribuições</title></rect>')
    for row, label in [(1, "seg"), (3, "qua"), (5, "sex")]:
        parts.append(f'<text class="label" x="2" y="{35+row*16}">{label}</text>')
    total = f'{calendar["totalContributions"]:,}'.replace(",", ".")
    parts.append(f'<text class="total" x="34" y="152">{total} contribuições nos últimos 12 meses</text>')
    return "".join(parts) + "</svg>\n"

def render_portrait(raw):
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    # Sample a denser grid; average pixels instead of taking one noisy pixel.
    image = ImageOps.fit(image, (400,400), method=Image.Resampling.LANCZOS)
    image = image.crop((16,12,392,388)).resize((90,58), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(image.convert("L"), cutoff=1).filter(
        ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    # Remove only background connected to the image border, preserving eyes and teeth.
    background_pixels = set()
    pending = [(x, y) for x in range(90) for y in (0, 57)]
    pending += [(x, y) for y in range(58) for x in (0, 89)]
    while pending:
        x, y = pending.pop()
        if (x, y) in background_pixels:
            continue
        r, g, b = image.getpixel((x, y))
        background = ((b > r*1.08 and b > g*1.12 and b > 100)
                      or (g > r*1.5 and b > r*1.4)
                      or (min(r, g, b) > 170 and max(r, g, b)-min(r, g, b) < 45))
        if background:
            background_pixels.add((x, y))
            pending.extend((nx, ny) for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
                           if 0 <= nx < 90 and 0 <= ny < 58 and (nx, ny) not in background_pixels)
    ramp = " .,:;irsXA253hMHGS#9B&@"
    body = ""
    rows = []
    for y in range(58):
        line = ""
        for x in range(90):
            if (x, y) in background_pixels:
                line += " "
            else:
                luminance = (gray.getpixel((x,y))/255)**0.72
                line += ramp[min(len(ramp)-1, max(1,round(luminance*(len(ramp)-1))))]
        rows.append(line)
        body += text(25,72+y*5.25,line,5.35,"#d5e2eb",
                     f'xml:space="preserve" class="reveal" style="animation-delay:{y*.026:.3f}s"')
    body += text(22,402,"francisco@github:~$ whoami",12,"#63d6ab")
    return frame(340,430,"francisco / avatar","Retrato ASCII de Francisco Junior com contraste e resolução aprimorados.",body), rows

def main():
    avatar, calendar = read_public_profile()
    if urlparse(avatar).hostname != "avatars.githubusercontent.com":
        raise ValueError("Unexpected avatar host")
    with urlopen(Request(avatar, headers={"User-Agent":"Franciscoafcj-profile-art"}),timeout=30) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError("Avatar exceeds size limit")
    portrait, rows = render_portrait(raw)
    heatmap = render_calendar(calendar)
    for svg in (portrait,heatmap):
        ET.fromstring(svg)
        if "<script" in svg or "<image" in svg:
            raise ValueError("SVG must be self-contained")
    # All inputs and outputs validated before replacing the published assets.
    (ROOT/"assets").mkdir(exist_ok=True)
    (ROOT/"data").mkdir(exist_ok=True)
    (ROOT/"assets/portrait.svg").write_text(portrait,encoding="utf-8")
    (ROOT/"github-metrics.svg").write_text(heatmap,encoding="utf-8")
    (ROOT/"data/portrait.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"data/contributions.json").write_text(json.dumps(calendar,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Validated portrait and {calendar['totalContributions']} contributions; no credentials saved.")

if __name__ == "__main__":
    main()
