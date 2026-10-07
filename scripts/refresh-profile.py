"""Regenerate the public avatar and contribution cards. Never store access tokens."""
import base64
import io
import json
import os
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
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
COLORS = ["#18232d", "#164c43", "#238873", "#42baa0", "#80efd2"]
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
    body = text(28,82,"CONTRIBUIÇÕES",18,"#e6edf3")
    body += text(28,106,f'{days[0]["date"]} → {days[-1]["date"]} · dados do GitHub',11)
    months = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    last_month = None
    step = min(14, 742 / len(calendar["weeks"]))
    for col, week in enumerate(calendar["weeks"]):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month:
            body += text(round(60+col*step,2),133,months[first.month-1],10)
            last_month = first.month
        for day in week["contributionDays"]:
            x, y = 60+col*step, 146+day["weekday"]*15
            color = COLORS[LEVELS.index(day["contributionLevel"])]
            body += (f'<rect class="reveal" style="animation-delay:{(col*.018+day["weekday"]*.022):.3f}s" '
                     f'x="{x:.2f}" y="{y}" width="{step-3:.2f}" height="12" rx="3" fill="{color}">'
                     f'<title>{day["date"]}: {day["contributionCount"]} contribuições</title></rect>')
    for row,label in [(1,"seg"),(3,"qua"),(5,"sex")]:
        body += text(28,155+row*15,label,10)
    total = calendar["totalContributions"]
    active = sum(d["contributionCount"]>0 for d in days)
    recent = sum(d["contributionCount"] for d in days[-30:])
    for x, number, label in [(28,total,"contribuições no período"),(307,active,"dias com atividade"),(574,recent,"nos últimos 30 dias")]:
        body += text(x,293,number,26,"#80efd2") + text(x,315,label,11)
    body += '<path d="M28 263H810" stroke="#303b49"/>'
    body += text(590,113,"menos",10)
    for i,c in enumerate(COLORS):
        body += f'<rect x="{630+i*16}" y="103" width="12" height="12" rx="3" fill="{c}"/>'
    body += text(717,113,"mais",10)
    return frame(840,350,"francisco / contribuicoes","Calendário de contribuições reais do GitHub, com totais e atividade dos últimos 30 dias.",body)

def render_portrait(raw):
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    # Sample a denser grid; average pixels instead of taking one noisy pixel.
    image = ImageOps.fit(image, (400,400), method=Image.Resampling.LANCZOS)
    image = image.crop((16,12,392,388)).resize((90,58), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(image.convert("L"), cutoff=1).filter(
        ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    ramp = " .,:;irsXA253hMHGS#9B&@"
    body = ""
    rows = []
    for y in range(58):
        line = ""
        for x in range(90):
            r,g,b = image.getpixel((x,y))
            # Suppress the purple/teal background of this public avatar.
            background = ((b > r*1.08 and b > g*1.12 and b > 100)
                          or (g > r*1.5 and b > r*1.4)
                          or (min(r,g,b)>240))
            if background:
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
