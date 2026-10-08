"""dev_train sonuç tablosunu (sonuclar_train.csv) okunur biçimde gösterir.

Kullanım:  python arastirma/trend/ozet.py [filtre_ifadesi]
Örnek:     python arastirma/trend/ozet.py "market=='spot' and interval=='1d'"
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent

if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_colwidth", 60)
    df = pd.read_csv(HERE / "sonuclar_train.csv")
    if len(sys.argv) > 1:
        df = df.query(sys.argv[1])
    cols = ["name", "sharpe1", "sharpe2", "ret1", "ret2", "cagr1", "maxdd1", "vol1", "trades_per_year", "exposure", "costs1", "funding1"]
    print(df[cols].round(3).to_string(index=False))
