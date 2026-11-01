# Honolulu weekend surf report

Weekly chart (Fri to Sun): tide curve, night shading, NWS hourly wind with direction arrows, and surf heights per shore.

- `.github/workflows/surf-data.yml` runs every Friday at 5:41 am HST. It runs `fetch_surf_data.py` and force-pushes the NWS hourly wind, surf forecast (SRF) and surf discussion (SRD) to the `surf-data` branch.
- A Claude scheduled task runs at 6:30 am HST. It reads that branch and `render_weekend.py` draws the chart.
- Tides come from `tide_predict.py`, which uses the NOAA CO-OPS harmonic constants for station 1612340 (`noaa_1612340.json`). They match NOAA's own predictions to within about 3 minutes and 0.02 ft.

Data is public NWS/NOAA forecast output.
