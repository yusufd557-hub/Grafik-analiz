"""dev_train yıllık / bacak / yön tanısı (defterde kayıtlı yapılandırmalar; seri 2024 öncesine kesilir)."""
import json
import sys

from ortak import done_keys, train_diagnostics

def fmt(x):
    return "  -  " if x is None else f"{x:+.2f}"

def diag(name_sub_list):
    rows = done_keys()
    for sub in name_sub_list:
        hits = [r for r in rows.values() if r["name"] == sub]
        if not hits:
            print("yok:", sub); continue
        r = hits[0]
        d = train_diagnostics(r["interval"], r["market"], r["universe"], r["params"])[1.0]
        print(f"\n== {r['name']}  ret1={r['ret1']:.2f} sh1={r['sharpe1']:.2f} sh2={r['sharpe2']:.2f} n={r['trades']}")
        print("  yıllar:", "  ".join(f"{y}:{fmt(v['ret'])}/{fmt(v['sharpe'])}({v['trades']})" for y, v in d["years"].items()))
        print("  bacak:", "  ".join(f"{k.split(':')[1][:3]}:{fmt(v['ret'])}/{fmt(v['sharpe'])}({v['trades']})" for k, v in d["legs"].items()))
        print("  yön:", "  ".join(f"{k}: n={v['n']} toplam={v['sum_net']:+.2f} ort={v['mean_net']:+.4f} kaz={v['win']:.2f}" for k, v in d["dirs"].items()))

if __name__ == "__main__":
    diag(sys.argv[1:])
