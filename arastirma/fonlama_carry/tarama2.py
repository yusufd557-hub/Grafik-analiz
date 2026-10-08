"""2. aşama: carry inceltme (eşikler 0,01% kütle noktasından uzak), aralık kontrolü (1s/1d),
ve fonlama uçlarından yönlü sinyal (yalnız vadeli). Yalnız dev_train, 1× ve 2× maliyet."""
from ortak import tara

satirlar = []
# --- carry inceltme (4s)
for u in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "SEPET3"):
    for n in (1, 3, 7):
        for giris, cikis in ((0.5e-4, 0.0), (0.5e-4, -0.5e-4), (0.9e-4, 0.0), (0.9e-4, 0.5e-4), (1.5e-4, 0.5e-4)):
            satirlar.append(("carry", u, "4h", {"n": n, "giris": giris, "cikis": cikis, "son_neg": False}))
# --- aralık kontrolü: sepet, n=3, (0.5e-4, 0) ve her zaman açık
for iv in ("1h", "1d"):
    satirlar.append(("carry", "SEPET3", iv, {"n": 3, "giris": 0.5e-4, "cikis": 0.0, "son_neg": False}))
    satirlar.append(("carry", "SEPET3", iv, {"n": 0, "giris": 0.0, "cikis": 0.0, "son_neg": False}))
tara(satirlar, "tarama2_carry.csv")

satirlar = []
# --- yönlü (vadeli), 4s
for u in ("BTCUSDT", "ETHUSDT", "SEPET3"):
    for n in (1, 3):
        for filtre in ("yok", "ile"):
            for tut in (2, 7):
                base = {"n": n, "filtre": filtre, "m": 100, "tut": tut}
                for alt in (0.0, -0.5e-4):  # A: kalabalık kısa -> uzun
                    satirlar.append(("yonlu", u, "4h", {**base, "olcek": "mutlak", "yon": "uzun", "alt": alt, "ust": 1.0}))
                for ust in (3e-4, 6e-4):  # B: kalabalık uzun -> kısa
                    satirlar.append(("yonlu", u, "4h", {**base, "olcek": "mutlak", "yon": "kisa", "alt": -1.0, "ust": ust}))
                # C: yüzdelik sıra, iki yön
                satirlar.append(("yonlu", u, "4h", {**base, "olcek": "yuzdelik", "W": 180, "yon": "iki", "alt": 0.1, "ust": 0.9}))
tara(satirlar, "tarama2_yonlu.csv")
