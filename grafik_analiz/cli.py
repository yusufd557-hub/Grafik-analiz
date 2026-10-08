"""Komut satırı.

    python -m grafik_analiz guncelle                 # bütün coin ve zaman dilimleri
    python -m grafik_analiz guncelle --coin BTC --dilim 4h 1d
    python -m grafik_analiz analiz --coin ETH --dilim 4h
    python -m grafik_analiz istatistik --coin SOL --dilim 1h
    python -m grafik_analiz uygulama                 # masaüstü uygulaması
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .config import INTERVALS, SYMBOLS, validate_interval, validate_symbol


def _store():
    from .data import CandleStore

    return CandleStore()


def cmd_update(args: argparse.Namespace) -> int:
    store = _store()
    for symbol in args.coin:
        for interval in args.dilim:
            store.update(symbol, interval, progress=print)
    return 0


def _load(symbol: str, interval: str, refresh: bool) -> pd.DataFrame:
    store = _store()
    frame = store.update(symbol, interval) if refresh else store.load(symbol, interval)
    if frame.empty:
        frame = store.update(symbol, interval, progress=print)
    return frame


def cmd_analyze(args: argparse.Namespace) -> int:
    from .analysis import analyze
    from .report import summary_text

    for symbol in args.coin:
        for interval in args.dilim:
            result = analyze(_load(symbol, interval, args.yenile), symbol, interval)
            print(summary_text(result))
            print()
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    from .analysis import analyze
    from .report import DIRECTION_NAMES, percent

    for symbol in args.coin:
        for interval in args.dilim:
            result = analyze(_load(symbol, interval, args.yenile), symbol, interval)
            print(f"{symbol} · {interval} · {len(result.frame):,} mum")
            print("Hedef payı = hedef / (hedef + stop). Kıyas = aynı kırılımlarda rastgele hareketin payı, S/(H+S).")
            print(
                f"{'Formasyon':22s} {'yön':10s} {'tespit':>7s} {'kırılım':>8s} {'hedef':>6s} {'stop':>5s} "
                f"{'süre':>5s} {'hedef payı':>11s} {'%95 aralık':>12s} {'kıyas':>6s}"
            )
            for _, row in result.formation_stats.iterrows():
                print(
                    f"{row['name']:22s} {DIRECTION_NAMES[row['direction']]:10s} {row['detected']:7d} {row['breakouts']:8d} "
                    f"{row['target']:6d} {row['stop']:5d} {row['timeout']:5d} {percent(row['hit_rate']):>11s} "
                    f"{percent(row['ci_low']) + '–' + percent(row['ci_high']):>12s} {percent(row['baseline']):>6s}"
                )
            print()
    return 0


def cmd_app(_args: argparse.Namespace) -> int:
    from .app.main import main as app_main

    return app_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grafik_analiz", description="Kripto grafik analizi")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_market_args(p: argparse.ArgumentParser, many_default: bool) -> None:
        p.add_argument(
            "--coin",
            nargs="+",
            default=list(SYMBOLS) if many_default else ["BTCUSDT"],
            type=validate_symbol,
            help="coin(ler): BTC, ETH, SOL ...",
        )
        p.add_argument(
            "--dilim",
            nargs="+",
            default=list(INTERVALS) if many_default else ["4h"],
            type=validate_interval,
            help=f"zaman dilimi(leri): {', '.join(INTERVALS)}",
        )

    p = sub.add_parser("guncelle", help="mum verisini indir / güncelle")
    add_market_args(p, many_default=True)
    p.set_defaults(func=cmd_update)

    for name, func, help_text in (
        ("analiz", cmd_analyze, "son durumun grafik analizi"),
        ("istatistik", cmd_stats, "formasyonların geçmiş hedef oranları"),
    ):
        p = sub.add_parser(name, help=help_text)
        add_market_args(p, many_default=False)
        p.add_argument("--yenile", action="store_true", help="önce veriyi güncelle")
        p.set_defaults(func=func)

    p = sub.add_parser("uygulama", help="masaüstü uygulamasını aç")
    p.set_defaults(func=cmd_app)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
