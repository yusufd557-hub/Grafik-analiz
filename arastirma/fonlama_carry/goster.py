import sys, json
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
d = pd.read_csv(sys.argv[1])
p = d.params.apply(json.loads)
keys = sys.argv[2].split(',')
for k in keys:
    d[k] = p.apply(lambda x: x.get(k))
d['ret'] = (d.getiri*100).round(1); d['ret2'] = (d.getiri_2x*100).round(1); d['dd'] = (d.maxdd*100).round(1)
d['S'] = d.sharpe.round(2); d['S2'] = d.sharpe_2x.round(2); d['fon'] = (-d.fonlama*100).round(1); d['mal'] = (d.maliyet*100).round(1)
d['isl_yil'] = (d.islem/((pd.Timestamp('2024-01-01', tz='UTC')-pd.to_datetime(d.baslangic)).dt.days/365.25)).round(1)
for (u, iv), g in d.groupby(['universe', 'interval'], sort=False):
    print('==', u, iv)
    print(g[keys + ['ret', 'S', 'dd', 'islem', 'isl_yil', 'fon', 'mal', 'ret2', 'S2']].to_string(index=False))
