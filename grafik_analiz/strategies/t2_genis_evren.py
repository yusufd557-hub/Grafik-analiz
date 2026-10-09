"""Geniş evren ailesi, araştırma turu 2 ("t2_genis_evren").

Zamana bağlı, hayatta kalan yanlılığı olmayan geniş vadeli evrende (her ay,
önceki 30 günün hacmine göre ilk 30 USDⓈ-M sürekli vadeli sözleşme)
kesitsel uzun/kısa stratejiler:

- kesitsel momentum (``mom_L[_s]``: son L günün log getirisi, son s gün atlanır),
- kısa vadeli dönüş (``rev_L``: son L günün getirisinin tersi),
- kesitsel fonlama carry'si (``fon_F``: son F günün ortalama fonlamasının tersi;
  düşük fonlamada uzun, yüksekte kısa),
- düşük oynaklık (``oyn_V``: son V günün getiri oynaklığının tersi),
- bunların eşit ağırlıklı sıra birleşimleri (``a+b``).

Mekanik:

- Bacaklar, geliştirme döneminde evrene hiç girmiş 315 sembolün hepsidir
  (``SYMBOLS``, sabit liste); ağırlık 1/315. Bacak başına pozisyon −1…1.
  Bir anda en fazla ~30 üye tutulabildiğinden brüt maruziyet en fazla ~%9,5'tir
  (harness kısıtı: sabit bacak ağırlığı, bacak başına kaldıraç yok).
- Evren ``load_universe(scope="dev")`` ile ``signal_fn`` içinde yüklenir ve
  verilen mumların son barının kapanışına **açıkça kesilir** (``ay <= son bar
  açılışı + bar uzunluğu``). t barında verilen karar t+1 barında tutulur;
  bu yüzden uygunluk t+1 barının ayının evrenine göredir (ayın evreni ay
  başında, önceki ayın son günlük mumu kapanınca bilinir).
- Yeniden dengeleme ``reb`` günde bir, sabit takvimle (kapanışı gece yarısına
  denk gelen barda, 1970-01-01'den gün sayısı mod ``reb`` == 0). Arada
  pozisyonlar sabittir; evrenden çıkan sembol hemen kapanır, yeni üye ancak
  sonraki dengelemede girer.
- Listeden kalkma: verisi, verilen verinin son barından önce biten sembolde
  son bardan bir önceki barda hedef 0 yapılır (son barda pozisyon yok, çıkış
  maliyeti ödenir). Bu bir barlık ileri bilgidir (Binance kaldırmayı önceden
  duyurur); dev döneminde evrendeyken verisi biten yalnız 3 sembol var.
- Fonlama skoru yalnız ``funding_time <= bar açılışı`` olan kayıtlarla
  hesaplanır (ihtiyatlı; ``assert_causal`` fonlamayı kesim barının açılışında keser).
- Bütün skorlar geriye dönük pencerelerle hesaplanır; ``shift(-k)``,
  ortalanmış pencere ya da tam örneklem istatistiği yoktur.
- Boyut: eşit (±1), ters oynaklık ya da sıra ağırlığı; taraflar dolar nötr
  ya da geçmiş kayan betaya göre beta nötr (BTC/ETH/SOL eşit ağırlıklı
  getiriye göre) ölçeklenir. Taraf başına en büyük pozisyon 1.

`specs()` yalnız dondurulup iç doğrulamada (dev_valid) bir kez ölçülen
yapılandırmaları döndürür (bkz. ``arastirma/tur2/t2_genis_evren/RAPOR.md``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "t2_genis_evren"

SYMBOLS = tuple(
    """
    BTCUSDT 1000BONKUSDT 1000FLOKIUSDT 1000LUNCUSDT 1000PEPEUSDT 1000RATSUSDT 1000SATSUSDT
    1000SHIBUSDT 1INCHUSDT 1MBABYDOGEUSDT 4USDT AAVEUSDT ACEUSDT ACTUSDT ADAUSDT AERGOUSDT
    AGIXUSDT AI16ZUSDT AIAUSDT AIOTUSDT AIXBTUSDT AKEUSDT ALCHUSDT ALGOUSDT ALICEUSDT ALPACAUSDT
    ALPHAUSDT ALTUSDT ANIMEUSDT ANKRUSDT APEUSDT API3USDT APTUSDT ARBUSDT ARCUSDT ARIAUSDT
    ARKUSDT ARPAUSDT ASTERUSDT ATOMUSDT AUCTIONUSDT AVAXUSDT AVNTUSDT AXSUSDT BABYUSDT BAKEUSDT
    BANDUSDT BANKUSDT BASEDUSDT BATUSDT BBUSDT BCHUSDT BEATUSDT BELUSDT BERAUSDT BIGTIMEUSDT
    BILLUSDT BIOUSDT BLURUSDT BLZUSDT BNBUSDT BNTUSDT BNXUSDT BOMEUSDT BSBUSDT BULLAUSDT BZUSDT
    CAKEUSDT CELRUSDT CFXUSDT CHRUSDT CHZUSDT CKBUSDT CLUSDT COAIUSDT COMPUSDT COTIUSDT CRVUSDT
    CTSIUSDT CYBERUSDT DASHUSDT DEFIUSDT DEGOUSDT DENTUSDT DEXEUSDT DIAUSDT DOGEUSDT DOGSUSDT
    DOTUSDT DRAMUSDT DUSKUSDT DYDXUSDT EDENUSDT EDUUSDT EGLDUSDT EIGENUSDT ENAUSDT ENJUSDT
    ENSOUSDT ENSUSDT EOSUSDT ETCUSDT ETHFIUSDT ETHUSDT EVAAUSDT EWYUSDT FARTCOINUSDT FETUSDT
    FILUSDT FLMUSDT FLOWUSDT FOLKSUSDT FRONTUSDT FTMUSDT FTTUSDT FUNUSDT GALAUSDT GALUSDT
    GASUSDT GIGGLEUSDT GMTUSDT GOATUSDT GRTUSDT GUNUSDT HBARUSDT HEMIUSDT HIFIUSDT HIGHUSDT
    HNTUSDT HOTUSDT HUSDT HYPERUSDT HYPEUSDT ICPUSDT ICXUSDT IDUSDT IMXUSDT INJUSDT INTCUSDT
    IOSTUSDT IOTAUSDT IOTXUSDT IOUSDT IPUSDT JASMYUSDT JELLYJELLYUSDT JTOUSDT JUPUSDT KAITOUSDT
    KAVAUSDT KEEPUSDT KLAYUSDT KNCUSDT KORUUSDT KSMUSDT LABUSDT LAYERUSDT LDOUSDT LENDUSDT
    LEVERUSDT LIGHTUSDT LINAUSDT LINEAUSDT LINKUSDT LITUSDT LOOMUSDT LPTUSDT LQTYUSDT LRCUSDT
    LTCUSDT LUNA2USDT LUNAUSDT LYNUSDT MAGICUSDT MANAUSDT MANTAUSDT MASKUSDT MATICUSDT MEMEUSDT
    MEWUSDT MINAUSDT MKRUSDT MMTUSDT MOODENGUSDT MOVEUSDT MRVLUSDT MTLUSDT MUSDT MUUSDT MYXUSDT
    NEARUSDT NEIROETHUSDT NEIROUSDT NEOUSDT NIGHTUSDT NMRUSDT NOTUSDT OCEANUSDT OGNUSDT OMGUSDT
    OMUSDT ONDOUSDT ONEUSDT ONGUSDT ONTUSDT OPENUSDT OPUSDT ORDIUSDT PAXGUSDT PENGUUSDT
    PEOPLEUSDT PERPUSDT PIEVERSEUSDT PIPPINUSDT PIXELUSDT PNUTUSDT POLYXUSDT POPCATUSDT
    POWERUSDT POWRUSDT PROVEUSDT PUMPUSDT QTUMUSDT RAREUSDT RAVEUSDT REDUSDT REEFUSDT RENUSDT
    RESOLVUSDT RIVERUSDT RLCUSDT RNDRUSDT ROSEUSDT RSRUSDT RUNEUSDT RVNUSDT SAGAUSDT SAMSUNGUSDT
    SANDUSDT SEIUSDT SFPUSDT SIRENUSDT SKHYNIXUSDT SKHYUSDT SKYAIUSDT SNDKUSDT SNXUSDT SNXXUSDT
    SOLUSDT SOMIUSDT SOONUSDT SOXLUSDT SOXSUSDT SPCXUSDT SPKUSDT SRMUSDT STMXUSDT STORJUSDT
    STOUSDT STRKUSDT STXUSDT SUIUSDT SUSHIUSDT SXPUSDT SYNUSDT TAOUSDT TAUSDT THETAUSDT TIAUSDT
    TLMUSDT TNSRUSDT TOMOUSDT TONUSDT TRBUSDT TRUMPUSDT TRXUSDT TSTUSDT TURBOUSDT TUTUSDT
    UMAUSDT UNFIUSDT UNIUSDT USUALUSDT UXLINKUSDT VELVETUSDT VETUSDT VINEUSDT VIRTUALUSDT
    VOXELUSDT VVVUSDT WAVESUSDT WCTUSDT WIFUSDT WLDUSDT WLFIUSDT WUSDT XAGUSDT XAIUSDT XAUUSDT
    XLMUSDT XMRUSDT XPLUSDT XRPUSDT XTZUSDT XVGUSDT YFIIUSDT YFIUSDT YGGUSDT ZBTUSDT ZECUSDT
    ZENUSDT ZILUSDT ZROUSDT ZRXUSDT 币安人生USDT
    """.split()
)
"""Geliştirme döneminde (2019-10 … 2026-09) evrene en az bir ay girmiş semboller, BTCUSDT başta."""

LEGS = tuple(("futures", s) for s in SYMBOLS)
BENCH = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
_EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
_DAY = pd.Timedelta(days=1)

DEFAULTS = dict(
    skor="mom_28",
    reb=7,
    k_oran=0.2,
    k_min=2,
    tampon=0.0,
    yan="ls",
    boyut="esit",
    notr="dolar",
    beta_gun=60,
    oyn_gun=30,
    top_n=30,
    min_uye=10,
    delist_cik=True,
)


# ---------------------------------------------------------------- yardımcılar


def _step(frame: pd.DataFrame) -> pd.Timedelta:
    diff = (pd.to_datetime(frame["close_time"], utc=True) - frame.index).median()
    return pd.Timedelta(diff).ceil("1min")


def _month_start(times: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(
        pd.to_datetime({"year": times.year, "month": times.month, "day": 1}, utc=True)
    )


def _universe(grid: pd.DatetimeIndex, step: pd.Timedelta, syms: list[str], top_n: int) -> np.ndarray:
    """Üyelik matrisi: [t, j] = j sembolü t+1 barının ayında evrende mi."""
    from grafik_analiz.research.data import load_universe

    table = load_universe(scope="dev")
    # Açık kesme: verilen mumların son barının kapanışından sonra bilinen ay yok.
    table = table[table["ay"] <= grid[-1] + step]
    table = table[table["sira"] <= top_n]
    member = (
        table.assign(v=1.0)
        .pivot_table(index="ay", columns="sembol", values="v", aggfunc="max")
        .reindex(columns=syms)
    )
    months = _month_start(grid + step)
    return member.reindex(months).fillna(0.0).to_numpy() > 0


def _funding_avg(funding: dict, syms: list[str], grid: pd.DatetimeIndex, days: float) -> np.ndarray:
    """Son `days` günün günlük ortalama fonlaması; yalnız zamanı bar açılışına eşit/eski kayıtlar."""
    out = np.full((len(grid), len(syms)), np.nan)
    g = grid.as_unit("ns").asi8
    span = int(pd.Timedelta(days=days).value)
    for j, s in enumerate(syms):
        f = funding.get(s)
        if f is None or f.empty:
            continue
        times = pd.DatetimeIndex(f.index).as_unit("ns").asi8
        rates = f["funding_rate"].to_numpy(dtype=float)
        cs = np.concatenate([[0.0], np.cumsum(rates)])
        hi = np.searchsorted(times, g, side="right")
        lo = np.searchsorted(times, g - span, side="right")
        val = (cs[hi] - cs[lo]) / days
        # Pencerenin tamamı fonlama verisinin içinde olmalı.
        ok = (g - span) >= times[0]
        out[:, j] = np.where(ok, val, np.nan)
    return out


def _factor(name: str, logc: pd.DataFrame, r1: pd.DataFrame, funding: dict, syms, grid, bpd: int) -> np.ndarray:
    parts = name.split("_")
    kind = parts[0]
    if kind in ("mom", "rev"):
        lb = int(round(float(parts[1]) * bpd))
        skip = int(round(float(parts[2]) * bpd)) if len(parts) > 2 else 0
        val = (logc.shift(skip) - logc.shift(lb)).to_numpy()
        return val if kind == "mom" else -val
    if kind == "fon":
        return -_funding_avg(funding, syms, grid, float(parts[1]))
    if kind == "oyn":
        w = int(round(float(parts[1]) * bpd))
        return -r1.rolling(w, min_periods=max(5, int(0.8 * w))).std().to_numpy()
    raise ValueError(f"bilinmeyen faktör: {name}")


def _ranks(values: np.ndarray) -> np.ndarray:
    """0…1 arası sıra yüzdesi (yüksek değer = 1)."""
    order = values.argsort(kind="mergesort")
    r = np.empty(len(values))
    r[order] = np.arange(len(values))
    return (r + 0.5) / len(values)


# ---------------------------------------------------------------- sinyal


def signal(data: dict, funding: dict, **params) -> dict:
    p = {**DEFAULTS, **params}
    legs = list(data)
    syms = [s for _, s in legs]
    first = data[legs[0]]
    step = _step(first)
    bpd = max(1, int(round(_DAY / step)))

    start = min(f.index[0] for f in data.values() if len(f))
    end = max(f.index[-1] for f in data.values() if len(f))
    grid = pd.date_range(start, end, freq=step)
    close = pd.DataFrame({s: data[leg]["close"].astype(float) for s, leg in zip(syms, legs)}).reindex(grid)
    present = close.notna().to_numpy()
    logc = np.log(close.ffill(limit=2 * bpd))
    r1 = logc.diff()

    # Uygunluk: evrende (t+1 barının ayı), t'de mum var, listeden kalkmıyor.
    elig = _universe(grid, step, syms, int(p["top_n"])) & present
    if p["delist_cik"]:
        for j, leg in enumerate(legs):
            f = data[leg]
            if len(f) and f.index[-1] < end:
                elig[grid >= f.index[-1] - step, j] = False

    # Skor: tek faktör ya da sıra birleşimi.
    names = str(p["skor"]).split("+")
    facs = [_factor(n, logc, r1, funding, syms, grid, bpd) for n in names]

    # Beta (BTC/ETH/SOL eşit ağırlıklı getiriye göre) ve oynaklık.
    need_beta = p["notr"] == "beta"
    if need_beta:
        bcols = [s for s in BENCH if s in close.columns]
        rm = r1[bcols].mean(axis=1)
        w = int(p["beta_gun"]) * bpd
        mp = max(10, int(0.8 * w))
        cov = r1.rolling(w, min_periods=mp).cov(rm)
        var = rm.rolling(w, min_periods=mp).var()
        beta = cov.div(var, axis=0).to_numpy()
    if p["boyut"] == "ters_oyn":
        w = int(p["oyn_gun"]) * bpd
        vol = r1.rolling(w, min_periods=max(5, int(0.8 * w))).std().to_numpy()

    # Dengeleme barları: kapanışı gece yarısı ve gün sayısı mod reb == 0.
    nxt = grid + step
    day_no = ((nxt - _EPOCH) // _DAY).to_numpy()
    at_midnight = (nxt == nxt.normalize())
    is_reb = at_midnight & (day_no % int(p["reb"]) == 0)

    n, m = close.shape
    target = np.zeros((n, m))
    held = np.zeros(m)
    k_oran, k_min, tampon = float(p["k_oran"]), int(p["k_min"]), float(p["tampon"])
    yan, boyut, notr = p["yan"], p["boyut"], p["notr"]
    min_uye = int(p["min_uye"])
    for i in range(n):
        if is_reb[i]:
            ok = elig[i].copy()
            for fa in facs:
                ok &= np.isfinite(fa[i])
            if need_beta:
                ok &= np.isfinite(beta[i])
            if boyut == "ters_oyn":
                ok &= np.isfinite(vol[i]) & (vol[i] > 0)
            idx = np.flatnonzero(ok)
            new = np.zeros(m)
            if len(idx) >= min_uye:
                score = np.mean([_ranks(fa[i, idx]) for fa in facs], axis=0)
                pct = _ranks(score)  # 1 = en iyi
                order = np.argsort(-pct, kind="mergesort")  # en iyiden en kötüye
                k = max(k_min, int(round(k_oran * len(idx))))
                k = min(k, len(idx) // 2)
                bn = int(round(tampon * len(idx)))
                rank_pos = np.empty(len(idx), dtype=int)
                rank_pos[order] = np.arange(len(idx))
                longs, shorts = [], []
                if yan in ("ls", "l"):
                    keep = [q for q in range(len(idx)) if held[idx[q]] > 0 and rank_pos[q] < k + bn]
                    longs = list(keep)
                    for q in order:
                        if len(longs) >= k:
                            break
                        if q not in longs:
                            longs.append(q)
                if yan in ("ls", "s"):
                    keep = [q for q in range(len(idx)) if held[idx[q]] < 0 and rank_pos[q] >= len(idx) - k - bn]
                    shorts = [q for q in keep if q not in longs]
                    for q in order[::-1]:
                        if len(shorts) >= k:
                            break
                        if q not in shorts and q not in longs:
                            shorts.append(q)
                longs = np.array(longs, dtype=int)
                shorts = np.array(shorts, dtype=int)

                def sizes(sel):
                    if len(sel) == 0:
                        return np.zeros(0)
                    if boyut == "ters_oyn":
                        s = 1.0 / vol[i, idx[sel]]
                    elif boyut == "sira":
                        s = np.abs(pct[sel] - 0.5) * 2.0
                    else:
                        s = np.ones(len(sel))
                    return s / s.max()

                sl, ss = sizes(longs), sizes(shorts)
                a = b = 1.0
                if yan == "ls" and len(sl) and len(ss):
                    if notr == "beta":
                        bl = float(np.sum(sl * np.clip(beta[i, idx[longs]], 0.2, 3.0)))
                        bs = float(np.sum(ss * np.clip(beta[i, idx[shorts]], 0.2, 3.0)))
                    else:
                        bl, bs = float(sl.sum()), float(ss.sum())
                    a, b = min(1.0, bs / bl), min(1.0, bl / bs)
                new[idx[longs]] = a * sl
                new[idx[shorts]] = -b * ss
            held = new
        held = np.where(elig[i], held, 0.0)
        target[i] = held

    out = {}
    for j, leg in enumerate(legs):
        s = pd.Series(target[:, j], index=grid)
        out[leg] = s.reindex(data[leg].index).fillna(0.0)
    return out


# ---------------------------------------------------------------- tanımlar


def make_spec(name: str, interval: str, params: dict, description: str = "") -> StrategySpec:
    if not name.startswith(FAMILY + "_"):
        raise ValueError("strateji adı aile anahtarıyla başlamalı")
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=LEGS,
        signal_fn=signal,
        params={**DEFAULTS, **params},
        description=description,
    )


FROZEN: list[tuple[str, str, dict, str]] = []
"""(ad, zaman dilimi, parametreler, açıklama) — dondurulan yapılandırmalar."""


def specs() -> list[StrategySpec]:
    """Dondurulan ve dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    return [make_spec(name, interval, dict(params), desc) for name, interval, params, desc in FROZEN]
