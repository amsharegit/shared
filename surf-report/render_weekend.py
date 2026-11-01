#!/usr/bin/env python3
"""
render_weekend.py - One PNG covering Fri 00:00 to Mon 00:00 HST for Honolulu.
  Tide: harmonic prediction from NOAA 1612340 constants (filled area, left axis, ft MLLW)
  Wind: NWS hourly forecast (line + direction arrows, right axis, mph)
  Night shaded sunset to sunrise; surf heights per shore printed under each day label.

Usage: python3 render_weekend.py noaa_1612340.json wind_hourly.json weekend.json out.png
weekend.json: {"friday":"YYYY-MM-DD",
               "days":[{"surf":{"North":"4-6","South":"2-4","West":"3-5","East":"3-5"}}, {...}, {...}]}
Prints JSON with per-day sunrise/sunset, tide highs/lows and wind min/max/onset for writing the summary.
"""
import json, sys, math, os
from datetime import datetime, timedelta, timezone
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from astral import LocationInfo
from astral.sun import sun
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tide_predict as tp

HST = timezone(timedelta(hours=-10))
INK, MUTED, GRID = '#1f2328', '#57606a', '#d0d7de'
NIGHT, SUNBAND, TIDE_FILL, TIDE_LINE = '#dcdcf5', '#f3ecb0', '#a9b4c8', '#26334d'
DIRS = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']

def wind_color(m):
    return '#2e7d32' if m < 10 else '#9a8c00' if m < 15 else '#e07000' if m < 20 else '#c62828'

c = json.load(open(sys.argv[1])); wind = json.load(open(sys.argv[2])); wk = json.load(open(sys.argv[3])); out = sys.argv[4]
fri = datetime.strptime(wk['friday'], '%Y-%m-%d').replace(tzinfo=HST)
x0, x1 = fri, fri + timedelta(days=3)

ser = tp.predict(c['hc'], c['msl_above_mllw'], x0.astimezone(timezone.utc) - timedelta(hours=1), 74)
ex = [(t.astimezone(HST), y, k) for t, y, k in tp.extrema(ser) if x0 <= t.astimezone(HST) < x1]
ser = [(t.astimezone(HST), y) for t, y in ser if x0 <= t.astimezone(HST) <= x1]

wh = [(datetime.fromisoformat(h['t']).astimezone(HST), h['mph'], h['dir']) for h in wind.get('hours', [])]
wh = [w for w in wh if x0 <= w[0] <= x1]

loc = LocationInfo('Honolulu', 'USA', 'Pacific/Honolulu', 21.3069, -157.8583)
suns = [sun(loc.observer, date=(fri + timedelta(days=i)).date(), tzinfo=HST) for i in range(3)]

fig, ax = plt.subplots(figsize=(14, 6.4), dpi=150)
axw = ax.twinx()
axw.set_zorder(ax.get_zorder() + 1); axw.patch.set_visible(False)  # wind drawn over tide
ax.set_xlim(x0, x1)

# night + sun bands
edges = [x0] + [t for s in suns for t in (s['sunrise'], s['sunset'])] + [x1]
for i in range(0, len(edges) - 1, 2):
    ax.axvspan(edges[i], edges[i + 1], color=NIGHT, lw=0, zorder=0)
for s in suns:
    for t in (s['sunrise'], s['sunset']):
        ax.axvspan(t - timedelta(minutes=12), t + timedelta(minutes=12), color=SUNBAND, lw=0, zorder=0.5)
for i in range(1, 3):
    ax.axvline(x0 + timedelta(days=i), color='#9aa3b5', lw=1, zorder=0.6)

# tide
ts, ys = [t for t, _ in ser], [y for _, y in ser]
lo, hi = min(ys + [0]), max(ys)
ax.fill_between(ts, lo - 0.6, ys, color=TIDE_FILL, alpha=0.55, lw=0, zorder=1)
ax.plot(ts, ys, color=TIDE_LINE, lw=1.8, zorder=2)
ax.set_ylim(lo - 0.6, hi + 1.45)
ax.set_ylabel('Tide (ft, MLLW)', color=MUTED, fontsize=10)
for t, y, k in ex:
    ax.annotate(f"{t.strftime('%-I:%M%p').lower()[:-1]}\n{(0.0 if abs(y) < 0.05 else y):.1f}'",
                (t, y), xytext=(0, 7 if k == 'H' else -24), textcoords='offset points',
                ha='center', fontsize=7.5, color=TIDE_LINE, zorder=5)

# wind (separate right axis, labelled)
wmax = max([w[1] for w in wh] + [20])
axw.set_ylim(0, wmax * 1.45)
axw.set_ylabel('Wind (mph)', color=MUTED, fontsize=10)
summary_wind = {}
if wh:
    wt = [w[0] for w in wh]; wm = [w[1] for w in wh]
    axw.plot(wt, wm, color='#8d4b2c', lw=2, zorder=3)
    for t, m, d in wh[::2]:
        if d not in DIRS: continue
        to = math.radians(DIRS.index(d) * 22.5 + 180)   # arrow points where the wind blows toward
        axw.quiver([mdates.date2num(t)], [m], [math.sin(to)], [math.cos(to)], angles='uv', scale=55, width=0.0025,
                   headwidth=4, headlength=4, color=wind_color(m), zorder=4, pivot='middle')
    axw.axhline(15, color='#e07000', lw=0.8, ls=(0, (4, 4)), alpha=0.6, zorder=2)
    axw.text(x0 + timedelta(minutes=40), 15.4, '15 mph', va='bottom', ha='left', fontsize=7.5, color='#e07000')

# day headers + surf row
for i in range(3):
    day = fri + timedelta(days=i); mid = day + timedelta(hours=12)
    ax.text(mid, hi + 1.38, day.strftime('%a %b %-d'), ha='center', va='top', fontsize=13, fontweight='bold', color=INK)
    surf = wk['days'][i].get('surf', {}) if i < len(wk.get('days', [])) else {}
    line = '   '.join(f"{k[0]} {surf.get(k, 'n/a')}" for k in ('North', 'South', 'West', 'East'))
    ax.text(mid, hi + 1.02, line + ' ft', ha='center', va='top', fontsize=9.5, color=INK)
    s = suns[i]
    ax.text(mid, hi + 0.72, f"sunrise {s['sunrise'].strftime('%-I:%M')}  sunset {s['sunset'].strftime('%-I:%M')}",
            ha='center', va='top', fontsize=7.5, color=MUTED)
    dw = [w for w in wh if day <= w[0] < day + timedelta(days=1)]
    daylight = [w for w in dw if s['sunrise'] <= w[0] <= s['sunset']]
    onset = next((w[0].strftime('%-I%p').lower() for w in daylight if w[1] >= 15), None)
    summary_wind[day.strftime('%a')] = {
        'min_mph': min((w[1] for w in daylight), default=None), 'max_mph': max((w[1] for w in daylight), default=None),
        'dir': max(set(w[2] for w in daylight), key=[w[2] for w in daylight].count) if daylight else None,
        'first_hour_15mph_plus': onset}

ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18], tz=HST))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%-I%p', tz=HST))
for a in (ax, axw):
    for sp in a.spines.values(): sp.set_visible(False)
    a.tick_params(colors=MUTED, labelsize=8.5, length=0)
ax.grid(axis='y', color=GRID, lw=0.6)
fig.text(0.01, 0.01, 'Shaded = night. Tide: NOAA 1612340 Honolulu harmonic prediction. Wind: NWS hourly forecast, Honolulu '
         '(arrows point downwind; green <10, olive 10-15, orange 15-20, red 20+ mph). Surf: NWS HFO surf forecast, face ft.',
         fontsize=7, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(out, facecolor='white')
print(json.dumps({'png': out, 'days': {(fri + timedelta(days=i)).strftime('%a'): {
    'sunrise': suns[i]['sunrise'].strftime('%H:%M'), 'sunset': suns[i]['sunset'].strftime('%H:%M'),
    'tides': [(t.strftime('%H:%M'), round(y, 1), k) for t, y, k in ex if t.date() == (fri + timedelta(days=i)).date()],
    'wind': summary_wind.get((fri + timedelta(days=i)).strftime('%a'))} for i in range(3)}}, indent=1))
