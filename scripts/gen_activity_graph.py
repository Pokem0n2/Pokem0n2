#!/usr/bin/env python3
"""Generate a 30-day contribution heartbeat line-chart SVG (stdlib only).

Data source: GitHub GraphQL contributionsCollection.contributionCalendar.
Refreshed daily by .github/workflows/activity-graph.yml; output committed as
activity-graph.svg so the profile README never depends on a third-party host.
"""
import json, os, sys, urllib.request
from datetime import date, timedelta

GH_TOKEN = os.environ["GH_TOKEN"]
GH_USER = os.environ.get("GH_USER", "Pokem0n2")
DAYS = 31

# User's original theme from the dead github-readme-activity-graph URL
BG, FG, LINE, POINT = "#ffffff", "#000000", "#E34234", "#40C463"

QUERY = """query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}"""


def fetch_days():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": GH_USER}}).encode(),
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "activity-graph-generator",
        },
    )
    last_err = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            if data.get("errors"):
                raise RuntimeError(data["errors"])
            weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            days = [d for w in weeks for d in w["contributionDays"]]
            return days[-DAYS:]
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last_err = e
    raise SystemExit(f"GraphQL fetch failed after 3 tries: {last_err}")


def nice_ticks(vmax):
    step = max(1, -(-vmax // 10))  # ceil(vmax/10), min 1
    top = ((vmax + step - 1) // step) * step
    return list(range(0, top + 1, step)), top


def build_svg(days):
    counts = [d["contributionCount"] for d in days]
    labels = [int(d["date"][8:10]) for d in days]
    n = len(counts)
    ticks, top = nice_ticks(max(counts + [1]))

    W, H = 1200, 420
    L, R, T, B = 80, 1160, 70, 330  # chart area

    def x(i):
        return L + i * (R - L) / (n - 1)

    def y(v):
        return B - v * (B - T) / top

    pts = " ".join(f"{x(i):.1f},{y(c):.1f}" for i, c in enumerate(counts))

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" fill="none" font-family="Segoe UI, Ubuntu, Sans-Serif">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>',
        f'<text x="{W/2}" y="38" text-anchor="middle" font-size="20" '
        f'font-weight="600" fill="{FG}">{GH_USER}&#39;s Contribution Graph</text>',
    ]
    for t in ticks:
        yy = y(t)
        s.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{R}" y2="{yy:.1f}" stroke="#e0e0e0" stroke-width="1"/>')
        s.append(f'<text x="{L-10}" y="{yy+4:.1f}" text-anchor="end" font-size="12" fill="{FG}">{t}</text>')
    for i, lab in enumerate(labels):  # daily labels, same as the original card
        s.append(f'<text x="{x(i):.1f}" y="352" text-anchor="middle" font-size="12" fill="{FG}">{lab}</text>')
    s.append(
        f'<polyline points="{pts}" fill="none" stroke="{LINE}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )
    for i, c in enumerate(counts):
        s.append(f'<circle cx="{x(i):.1f}" cy="{y(c):.1f}" r="3" fill="{POINT}"/>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "activity-graph.svg"
    days = fetch_days()
    while len(days) < DAYS:  # pad new accounts
        d0 = date.fromisoformat(days[0]["date"]) - timedelta(days=1)
        days.insert(0, {"date": d0.isoformat(), "contributionCount": 0})
    with open(out, "w") as f:
        f.write(build_svg(days))
    counts = [d["contributionCount"] for d in days]
    print(f"wrote {out}: {len(days)} days {days[0]['date']}..{days[-1]['date']} "
          f"total={sum(counts)} max={max(counts)}")


if __name__ == "__main__":
    main()
