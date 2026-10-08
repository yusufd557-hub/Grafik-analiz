"""3. aşama: carry dayanıklılık varyantları ve 'kaplama' (spot uzun + fonlamaya göre vadeli koruma).
Yalnız dev_train, 1× ve 2× maliyet."""
from ortak import tara

satirlar = []
# --- carry dayanıklılık: 1d bar, son kayıt negatifse çıkış, BTC+ETH sepeti
for n in (1, 3):
    satirlar.append(("carry", "SEPET3", "1d", {"n": n, "giris": 1.5e-4, "cikis": 0.5e-4, "son_neg": False}))
    satirlar.append(("carry", "SEPET3", "4h", {"n": n, "giris": 1.5e-4, "cikis": 0.5e-4, "son_neg": True}))
    satirlar.append(("carry", "SEPET2", "4h", {"n": n, "giris": 1.5e-4, "cikis": 0.5e-4, "son_neg": False}))
tara(satirlar, "tarama3_carry.csv")

satirlar = []
# --- kaplama: fonlama yüksekken vadeli kısa (nötr carry), değilken vadeli uzun_poz; isteğe bağlı trend
for u in ("BTCUSDT", "ETHUSDT", "SEPET3"):
    for ust in (3e-4, 5e-4):
        for uzun_poz in (0.0, 1.0):
            for filtre in ("yok", "trend"):
                satirlar.append(("kaplama", u, "4h", {"n": 3, "ust": ust, "ust_cikis": 1.5e-4, "uzun_poz": uzun_poz, "filtre": filtre, "m": 100}))
    # kontrol: fonlama korumasız, yalnız trend (düşüş trendinde nakit yerine carry)
    for uzun_poz in (0.0, 1.0):
        satirlar.append(("kaplama", u, "4h", {"n": 3, "ust": 1.0, "ust_cikis": 1.0, "uzun_poz": uzun_poz, "filtre": "trend", "m": 100}))
tara(satirlar, "tarama3_kaplama.csv")
