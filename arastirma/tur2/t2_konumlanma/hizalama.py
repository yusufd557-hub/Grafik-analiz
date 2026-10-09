"""Veri hizalama kontrolü (yalnız eğitim dönemi, 31.12.2024 öncesi).

Konumlanma ölçüsünün zaman damgası T hangi 5 dakikalık aralığı anlatıyor?
Ölçülerin değişimi, açılış zamanı T + k·5dk olan 5 dakikalık vadeli mumla
karşılaştırılır (k = −4…+3). En yüksek korelasyonun k'si hizalamayı gösterir:
k = −1 → ölçü [T−5dk, T) aralığını anlatıyor (T anında biliniyor);
k ≥ 0 → ölçü T'den sonraki aralığı da içeriyor (ileri bakış riski).

Strateji performansı hesaplanmaz.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research.data import load, load_metrics
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION


def main() -> None:
    assert PROTOCOL_VERSION == "2"
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        m = load_metrics(sym, scope="dev")
        m = m[m.index < DEV_TRAIN_END]
        c = load(sym, "5m", "futures", scope="dev")
        c = c[c.index < DEV_TRAIN_END]
        vol = c["volume"].astype(float)
        tb = c["taker_buy_base"].astype(float)
        candle_taker = np.log(tb / (vol - tb)).replace([np.inf, -np.inf], np.nan)
        candle_ret = np.log(c["close"].astype(float) / c["open"].astype(float))
        candle_absret = candle_ret.abs()
        tk = np.log(m["taker_oran"].where(m["taker_oran"] > 0))
        tk = tk.where(tk.abs() < 3)
        oi = np.log(m["oi"].where(m["oi"] > 0))
        doi = oi - oi.shift(1)
        doi = doi.where(m.index.to_series().diff() == pd.Timedelta(minutes=5))
        g = np.log(m["genel_oran"].where(m["genel_oran"] > 0))
        dg = (g - g.shift(1)).where(m.index.to_series().diff() == pd.Timedelta(minutes=5))
        print(f"== {sym}  ölçü {m.index[0]} … {m.index[-1]} ({len(m)} kayıt)")
        print("   k  corr(taker_oran, mum taker)  corr(ΔlogOI, mum |getiri|)  corr(Δlog genel_oran, mum getiri)")
        for k in range(-4, 4):
            idx = m.index + pd.Timedelta(minutes=5 * k)
            a = candle_taker.reindex(idx).to_numpy()
            b = candle_absret.reindex(idx).to_numpy()
            r = candle_ret.reindex(idx).to_numpy()
            c1 = pd.Series(tk.to_numpy()).corr(pd.Series(a))
            c2 = pd.Series(doi.to_numpy()).corr(pd.Series(b))
            c3 = pd.Series(dg.to_numpy()).corr(pd.Series(r))
            print(f"  {k:+d}  {c1:+.3f}                       {c2:+.3f}                      {c3:+.3f}")


if __name__ == "__main__":
    main()
