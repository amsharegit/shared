"""Harmonic tide prediction for NOAA station 1612340 (Honolulu) from NOAA's published constants.
Usage: python3 tide_predict.py constants.json YYYY-MM-DD [ndays]  -> prints JSON {hourly:[[iso_hst, ft]], hilo:[[iso_hst, ft, 'H'|'L']]}
Heights in feet above MLLW, times in HST (UTC-10). Node factors per Schureman (1958)."""
import json, sys, math
from datetime import datetime, timedelta, timezone

R = math.radians
DOODSON = {  # T s h p N' p1 offset(deg)
 'M2':(2,0,0,0,0,0,0),'S2':(2,2,-2,0,0,0,0),'N2':(2,-1,0,1,0,0,0),'K2':(2,2,0,0,0,0,0),
 'K1':(1,1,0,0,0,0,-90),'O1':(1,-1,0,0,0,0,90),'P1':(1,1,-2,0,0,0,90),'Q1':(1,-2,0,1,0,0,90),
 'J1':(1,2,0,-1,0,0,-90),'OO1':(1,3,0,0,0,0,-90),'2N2':(2,-2,0,2,0,0,0),'MU2':(2,-2,2,0,0,0,0),
 'NU2':(2,-1,2,-1,0,0,0),'L2':(2,1,0,-1,0,0,180),'T2':(2,2,-3,0,0,1,0),'LAM2':(2,1,-2,1,0,0,180),
 'R2':(2,2,-1,0,0,-1,180),'SA':(0,0,1,0,0,0,0),'MM':(0,1,0,-1,0,0,0),'MF':(0,2,0,0,0,0,0),
 'RHO':(1,-2,2,-1,0,0,90),'2Q1':(1,-3,0,2,0,0,90),'S1':(1,1,-1,0,0,0,0),
 'M1':(1,0,0,1,0,0,-90),'M3':(3,0,0,0,0,0,180),'2SM2':(2,4,-4,0,0,0,0),
}
COMPOUND = {'M4':{'M2':2},'M6':{'M2':3},'MS4':{'M2':1,'S2':1},'MN4':{'M2':1,'N2':1},'MK3':{'M2':1,'K1':1}}
NODE_GROUP = {'N2':'M2','2N2':'M2','MU2':'M2','NU2':'M2','LAM2':'M2','L2':'M2','M3':'M2',
              'Q1':'O1','2Q1':'O1','RHO':'O1','M1':'O1'}

def astro(t):
    T = (t - datetime(2000,1,1,12,tzinfo=timezone.utc)).total_seconds()/86400/36525
    s = 218.3165 + 481267.8813*T; h = 280.4661 + 36000.7698*T
    p = 83.3535 + 4069.0137*T; N = 125.0445 - 1934.1363*T; p1 = 282.9384 + 1.7195*T
    ut = t.hour + t.minute/60 + t.second/3600
    tau = 15*ut + 180 + h - s
    return tau, s, h, p, N, p1

def fu(name, N):
    n = R(N); c = math.cos; sn = math.sin
    base = {
     'M2':(1.0004-0.0373*c(n)+0.0002*c(2*n), -2.14*sn(n)),
     'K1':(1.0060+0.1150*c(n)-0.0088*c(2*n)+0.0006*c(3*n), -8.86*sn(n)+0.68*sn(2*n)-0.07*sn(3*n)),
     'O1':(1.0089+0.1871*c(n)-0.0147*c(2*n)+0.0014*c(3*n), 10.80*sn(n)-1.34*sn(2*n)+0.19*sn(3*n)),
     'K2':(1.0241+0.2863*c(n)+0.0083*c(2*n)-0.0015*c(3*n), -17.74*sn(n)+0.68*sn(2*n)-0.04*sn(3*n)),
     'J1':(1.0129+0.1676*c(n)-0.0170*c(2*n)+0.0016*c(3*n), -12.94*sn(n)+1.34*sn(2*n)-0.19*sn(3*n)),
     'OO1':(1.1027+0.6504*c(n)+0.0317*c(2*n)-0.0014*c(3*n), -36.68*sn(n)+4.02*sn(2*n)-0.57*sn(3*n)),
     'MM':(1.0000-0.1300*c(n)+0.0013*c(2*n), 0.0),
     'MF':(1.0429+0.4135*c(n)-0.0040*c(2*n), -23.74*sn(n)+2.68*sn(2*n)-0.38*sn(3*n)),
    }
    if name in COMPOUND:
        f, u = 1.0, 0.0
        for k, m in COMPOUND[name].items():
            fk, uk = fu(k, N); f *= fk**m; u += uk*m
        return f, u
    if name in base: return base[name]
    if name in NODE_GROUP: return base[NODE_GROUP[name]]
    return 1.0, 0.0

def V(name, a):
    if name in COMPOUND:
        return sum(V(k, a)*m for k, m in COMPOUND[name].items())
    d = DOODSON[name]; tau, s, h, p, N, p1 = a
    return d[0]*tau + d[1]*s + d[2]*h + d[3]*p + d[4]*(-N) + d[5]*p1 + d[6]

def height(t, cons, z0):
    a = astro(t); total = z0
    for name, amp, g, _ in cons:
        f, u = fu(name, a[4])
        total += f*amp*math.cos(R(V(name, a) + u - g))
    return total

def predict(cons, z0, start_utc, hours, step_min=6):
    out = []; t = start_utc
    for _ in range(int(hours*60/step_min)+1):
        out.append((t, height(t, cons, z0))); t += timedelta(minutes=step_min)
    return out

def extrema(series):
    ex = []
    for i in range(1, len(series)-1):
        (t0,y0),(t1,y1),(t2,y2) = series[i-1], series[i], series[i+1]
        if (y1 > y0 and y1 >= y2) or (y1 < y0 and y1 <= y2):
            den = y0 - 2*y1 + y2; dx = 0.5*(y0-y2)/den if den else 0
            tt = t1 + (t2-t1)*dx; yy = y1 - 0.25*(y0-y2)*dx
            ex.append((tt, yy, 'H' if y1 > y0 else 'L'))
    return ex

if __name__ == '__main__':
    c = json.load(open(sys.argv[1])); cons = c['hc']; z0 = c['msl_above_mllw']
    day = datetime.strptime(sys.argv[2], '%Y-%m-%d'); nd = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    HST = timezone(timedelta(hours=-10))
    start = day.replace(tzinfo=HST).astimezone(timezone.utc) - timedelta(hours=1)
    ser = predict(cons, z0, start, 24*nd + 2)
    hourly = [(t.astimezone(HST).strftime('%Y-%m-%dT%H:%M'), round(y, 3)) for t, y in ser
              if t.astimezone(HST).minute % 6 == 0 and day.date() <= t.astimezone(HST).date() < (day + timedelta(days=nd)).date()]
    hilo = [(t.astimezone(HST).strftime('%Y-%m-%dT%H:%M'), round(y, 2), k) for t, y, k in extrema(ser)
            if day.date() <= t.astimezone(HST).date() < (day + timedelta(days=nd)).date()]
    print(json.dumps({'station': c['station'], 'datum': 'MLLW', 'tz': 'HST', 'series_6min': hourly, 'hilo': hilo}))
