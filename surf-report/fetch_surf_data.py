#!/usr/bin/env python3
"""
fetch_surf_data.py - Weekly data relay for the Honolulu weekend surf report.

Runs in GitHub Actions (open internet) every Friday ~6:00 am HST and saves raw
NWS data so the Claude scheduled task (sandboxed, no weather.gov access) can read it.

Outputs (in the output dir given as argv[1], default ./out):
  wind_hourly.json  NWS hourly forecast for Honolulu grid HFO/154,145 (speed mph, direction)
  srf.txt           NWS Honolulu Surf Forecast (FZHW52 PHFO SRF) raw text
  srd.txt           NWS Honolulu Surf Discussion (FXHW52 PHFO SRD) raw text
  meta.json         fetch time and per-source status

Stdlib only. Each source is independent; a failed source is recorded in meta.json, not fatal.
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone

UA = {'User-Agent': 'amsharegit-surf-report (github actions)', 'Accept': 'application/geo+json, text/plain, */*'}
GRID = 'https://api.weather.gov/gridpoints/HFO/154,145/forecast/hourly'
SRF = 'https://tgftp.nws.noaa.gov/data/raw/fz/fzhw52.phfo.srf.hfo.txt'
SRD = 'https://tgftp.nws.noaa.gov/data/raw/fx/fxhw52.phfo.srd.hfo.txt'


def get(url, tries=4):
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # NWS API returns intermittent 500s; back off and retry
            err = e
            time.sleep(5 * (i + 1))
    raise err


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'out'
    os.makedirs(out, exist_ok=True)
    meta = {'fetched_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'sources': {}}

    try:
        d = json.loads(get(GRID))
        rows = [{'t': p['startTime'], 'mph': int(str(p['windSpeed']).split()[0]), 'dir': p['windDirection']}
                for p in d['properties']['periods']]
        json.dump({'source': GRID, 'updated': d['properties'].get('updateTime'), 'hours': rows},
                  open(os.path.join(out, 'wind_hourly.json'), 'w'), indent=0)
        meta['sources']['wind'] = f'ok ({len(rows)} hours)'
    except Exception as e:
        meta['sources']['wind'] = f'FAILED: {e}'

    for name, url in (('srf', SRF), ('srd', SRD)):
        try:
            open(os.path.join(out, f'{name}.txt'), 'w').write(get(url))
            meta['sources'][name] = 'ok'
        except Exception as e:
            meta['sources'][name] = f'FAILED: {e}'

    json.dump(meta, open(os.path.join(out, 'meta.json'), 'w'), indent=1)
    print(json.dumps(meta, indent=1))


if __name__ == '__main__':
    main()
