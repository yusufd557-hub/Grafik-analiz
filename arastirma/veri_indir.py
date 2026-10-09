"""Araştırma verisini sıfırdan indirir (başka bir makinede yeniden üretim için).

Spot ve vadeli BTC/ETH/SOL mumları (5m–1d), fonlama, vadeli konumlanma
ölçüleri, prim endeksi ve isteğe bağlı olarak geniş vadeli evren. Var olan
dosyalar yalnız eksik kısımdan tamamlanır.

Çalıştırma:
    GRAFIK_ANALIZ_ARASTIRMA=<veri> python arastirma/veri_indir.py [--evren]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from grafik_analiz.data import FUTURES, SPOT, CandleStore
from grafik_analiz.data.extra import update_metrics, update_premium
from grafik_analiz.research.protocol import research_data_dir

SEMBOLLER = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
BASLANGIC = {"5m": "2020-01", "15m": "2019-01", "1h": "2017-08", "4h": "2017-08", "1d": "2017-08"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evren", action="store_true", help="geniş vadeli evreni de indir")
    args = parser.parse_args()
    root = research_data_dir()
    print(f"veri klasörü: {root}", flush=True)

    for market in (SPOT, FUTURES):
        store = CandleStore(root, market=market)
        for sym in SEMBOLLER:
            for iv in ("1d", "4h", "1h", "15m", "5m"):
                t = time.time()
                store.update(sym, iv, start=BASLANGIC[iv], progress=lambda m: print(m, flush=True) if ("hazır" in m or "alınamadı" in m) else None)
                print(f"   {market} {sym} {iv} {time.time() - t:.0f}s", flush=True)
            if market == FUTURES:
                store.update_funding(sym, progress=lambda m: print(m, flush=True))

    for sym in SEMBOLLER:
        t = time.time()
        m = update_metrics(root, sym)
        print(f"{sym} konumlanma {len(m)} {time.time() - t:.0f}s", flush=True)
        for iv in ("1h", "4h"):
            p = update_premium(root, sym, iv)
            print(f"{sym} prim {iv} {len(p)}", flush=True)

    if args.evren:
        subprocess.run([sys.executable, "-m", "grafik_analiz.research.universe", "indir"], check=True)
    print("BITTI", flush=True)


if __name__ == "__main__":
    main()
