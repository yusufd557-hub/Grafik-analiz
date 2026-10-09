"""Aşama 3 (dev_train): fitil + trend filtresi yüzeyi (1× ve 2×), ana donus adaylarının 2× sonucu."""
import sys

from grafik_analiz.research.evaluate import evaluate
from grafik_analiz.strategies import t2_limit_gun_ici as lg
from ortak import degerlendir, done, memo_signal

grup = sys.argv[1]
CSV = f"tarama3_{grup}.csv"
bitti = done(CSV)


def run(name, interval, **p):
    if "t2_limit_gun_ici_" + name in bitti:
        return
    degerlendir(name, interval, CSV, cost2=True, **p)


def sadece_2x(name, interval, **p):
    """Daha önce 1× değerlendirilmiş yapılandırmanın yalnız 2× satırı (1× satırı tekrarlanmaz)."""
    spec = lg.make_spec(name, interval, **p)
    spec.signal_fn = memo_signal
    m = evaluate(spec, windows=("dev_train",), cost_multipliers=(2.0,))["dev_train"][2.0]
    print(f"2x {spec.name:60s} ret {m['total_return']*100:+8.1f}% sh {m['sharpe']:+5.2f} dd {m['max_drawdown']*100:+6.1f}% a {m['alfa']*100:+6.1f}% t {m['alfa_t']:+5.2f}", flush=True)


T = dict(trend_gun=50, trend_mod="ile")
if grup == "F1":
    for k in (2.5, 3, 3.5, 4):
        for H in (1, 3, 6, 12):
            if (k, H) in ((3, 6), (3, 1)):
                continue
            run(f"fitil_1h_k{k}_H{H}_t50", "1h", yontem="fitil", k=k, H=H, sig_n=168, **T)
    for tg in (30, 100):
        run(f"fitil_1h_k3_H3_t{tg}", "1h", yontem="fitil", k=3, H=3, sig_n=168, trend_gun=tg, trend_mod="ile")
    run("fitil_1h_k3_H3_t50_s336", "1h", yontem="fitil", k=3, H=3, sig_n=336, **T)
    for k in (4, 5):
        for H in (8, 16):
            run(f"fitil_15m_k{k}_H{H}_t50", "15m", yontem="fitil", k=k, H=H, sig_n=96, **T)
if grup == "F5":
    for k in (4, 6, 8):
        for H in (12, 24, 48):
            if (k, H) == (6, 24):
                continue
            run(f"fitil_5m_k{k}_H{H}_t50", "5m", yontem="fitil", k=k, H=H, sig_n=288, **T)
if grup == "X2":
    b1 = dict(yontem="donus", n=4, esik=3, vol_n=500, yon="uzun", trend_gun=50, trend_mod="ile", H=12, sig_n=168)
    sadece_2x("donus_1h_n4_e3_t50_H12_piyasa", "1h", giris="piyasa", **b1)
    sadece_2x("donus_1h_n4_e3_t50_H12_lim1.0s_m3", "1h", giris="limit", d_sig=1.0, m=3, **b1)
    b15 = dict(yontem="donus", n=16, esik=3, vol_n=2000, yon="uzun", trend_gun=50, trend_mod="ile", H=48, sig_n=96)
    sadece_2x("donus_15m_n16_e3_t50_H48_piyasa", "15m", giris="piyasa", **b15)
    sadece_2x("donus_15m_n16_e3_t50_H48_lim1.0s_m12", "15m", giris="limit", d_sig=1.0, m=12, **b15)
    sadece_2x("fitil_1h_k3_H6_t50", "1h", yontem="fitil", k=3, H=6, sig_n=168, **T)
    sadece_2x("fitil_1h_k3_H1_t50", "1h", yontem="fitil", k=3, H=1, sig_n=168, **T)
    sadece_2x("fitil_5m_k6_H24_t50", "5m", yontem="fitil", k=6, H=24, sig_n=288, **T)
