"""Analiz sonucunu okunur metne çeviren yardımcılar (komut satırı ve uygulama ortak)."""

from __future__ import annotations

import math

from .analysis import AnalysisResult
from .config import INTERVAL_NAMES
from .patterns.base import BROKEN, FORMING, Formation
from .stats import lookup

DIRECTION_NAMES = {1: "yükseliş", -1: "düşüş", 0: "iki yönlü"}


def price(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "–"
    if abs(value) >= 1000:
        return f"{value:,.0f}".replace(",", ".")
    if abs(value) >= 1:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:.4f}".replace(".", ",")


def num(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def scale_name(scale: float) -> str:
    return "küçük ölçek" if scale <= 2.0 else "büyük ölçek"


def percent(value: float | None, digits: int = 0) -> str:
    if value is None or not math.isfinite(value):
        return "–"
    return f"%{100 * value:.{digits}f}".replace(".", ",")


def history_text(result: AnalysisResult, f: Formation, direction: int) -> str:
    row = lookup(result.formation_stats, f.key, direction)
    if row is None or row["decided"] == 0:
        return "geçmişte hedef ya da stopa ulaşmış örnek yok"
    return (
        f"geçmiş: hedef/stopa ulaşan {int(row['decided'])} kırılımın {percent(row['hit_rate'])} kadarı hedefte bitti "
        f"(%95 aralık {percent(row['ci_low'])}–{percent(row['ci_high'])}; rastgele hareket kıyası {percent(row['baseline'])}); "
        f"{int(row['timeout'])} kırılımda süre doldu"
    )


def formation_lines(result: AnalysisResult, f: Formation) -> list[str]:
    t = result.as_of
    status = f.status_at(t)
    when = result.frame.index[f.detected_index].strftime("%Y-%m-%d %H:%M")
    lines = [
        f"{f.name} ({scale_name(f.scale)}) — {status} "
        f"(tespit {when} UTC, beklenen yön: {DIRECTION_NAMES[f.bias]})"
    ]
    if status == FORMING:
        for d, lv in f.pending_levels(t).items():
            lines.append(
                f"   {DIRECTION_NAMES[d]} kırılımı: kapanış {price(lv['trigger'])} "
                f"{'üstünde' if d > 0 else 'altında'} → hedef {price(lv['target'])}, stop {price(lv['stop'])}"
            )
            lines.append(f"   {history_text(result, f, d)}")
    elif status == BROKEN and f.breakout_index is not None:
        bwhen = result.frame.index[f.breakout_index].strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"   {DIRECTION_NAMES[f.direction]} kırılımı {bwhen} UTC, giriş {price(f.breakout_price)} → "
            f"hedef {price(f.target)}, stop {price(f.stop)}"
        )
        lines.append(f"   {history_text(result, f, f.direction)}")
    return lines


def summary_text(result: AnalysisResult, candle_bars: int = 20) -> str:
    out: list[str] = []
    name = INTERVAL_NAMES.get(result.interval, result.interval)
    close = float(result.frame["close"].iloc[-1])
    out.append(f"{result.symbol} · {name} · son kapanış {price(close)} ({result.last_time:%Y-%m-%d %H:%M} UTC)")
    out.append("")
    out.append("Göstergeler")
    for label, text in result.indicator_snapshot():
        out.append(f"  {label}: {text}")

    out.append("")
    out.append("Aktif formasyonlar")
    active = result.active_formations()
    if not active:
        out.append("  Kırılım bekleyen veya sonucu açık formasyon yok.")
    for f in active:
        out.extend("  " + line for line in formation_lines(result, f))

    out.append("")
    out.append("Destek / direnç")
    if not result.levels:
        out.append("  Belirgin seviye yok.")
    for lv in sorted(result.levels, key=lambda x: -x.price):
        dist = (lv.price / close - 1) * 100
        dist_text = f"{dist:+.2f}".replace(".", ",")
        out.append(f"  {lv.kind:7s} {price(lv.price):>12s}  (%{dist_text}, {lv.touches} dokunuş)")
    for tl in result.trendlines:
        out.append(f"  trend çizgisi ({tl.kind}): şu an {price(tl.value_at(result.as_of))}, {tl.touches} dokunuş")
    if result.fib is not None:
        fib = result.fib
        levels = ", ".join(f"{num(r, 3)}: {price(v)}" for r, v in fib.levels.items() if 0 < r < 1)
        out.append(f"  Fibonacci ({price(fib.start_price)} → {price(fib.end_price)}): {levels}")

    out.append("")
    out.append(f"Son {candle_bars} bardaki mum formasyonları")
    events = result.candle_events(max(0, result.as_of - candle_bars + 1))
    if not events:
        out.append("  Yok.")
    stats = result.candle_stats.set_index("key")
    for e in events:
        when = result.frame.index[e.index].strftime("%Y-%m-%d %H:%M")
        row = stats.loc[e.spec.key]
        if e.spec.bias != 0 and row["count"] > 0:
            extra = (
                f"geçmişte {int(row['count'])} örnekte {result.config.candle_horizon} bar sonra "
                f"{DIRECTION_NAMES[e.spec.bias]} oranı {percent(row['success'])} (taban {percent(row['base'])})"
            )
        else:
            extra = "yön belirtmez"
        out.append(f"  {when}  {e.spec.name} — {extra}")
    return "\n".join(out)
