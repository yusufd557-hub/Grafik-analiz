"""Tanılama 3 (yalnız eğitim, veri 31.12.2024'te kesilir): tarama 2'de deftere yazılmış dört şok
yapılandırmasının yıllık dökümü. Bu kod `tanilama3.txt` üretilirken komut satırından aynen çalıştırıldı."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import egitim_dokumu  # noqa: E402

for cift, hedge, k, zin, hold in [('SOLBTC', 'bir', 6, 4.0, 6), ('SOLBTC', 'bir', 6, 4.0, 3), ('SOLETH', 'bir', 3, 4.0, 6), ('SOLETH', 'oyn', 6, 4.0, 6)]:
    p = dict(ciftler=[cift], hedge=hedge, z_tur='sok', k=k, vol_win=500, z_in=zin, z_exit=None, max_bar=hold)
    if hedge == 'oyn':
        p['hedge_win'] = 500
    d = egitim_dokumu('1h', p)
    print(cift, hedge, k, zin, hold, json.dumps({k: d[k] for k in ['yillik', 'yillik_brut_toplam', 'yillik_maliyet', 'yillik_fonlama']}))
