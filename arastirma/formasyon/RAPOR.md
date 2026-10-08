# Grafik ve mum formasyonları ailesi (`formasyon`) — araştırma raporu

Protokol: [`docs/PROTOKOL.md`](../../docs/PROTOKOL.md), sürüm 1. Bütün sayılar
harness'ten (`grafik_analiz.research.evaluate`, `run`, `summarize`) alınmıştır.
Getiriler net (komisyon + kayma, vadelide fonlama dahil) ve oran olarak verilir
(0,25 = %25). Görülmemiş döneme (1 Temmuz 2025 sonrası) hiç erişilmedi;
`unlock_holdout()` çağrılmadı, veri dosyaları doğrudan okunmadı.

## Kısa sonuç

- **294 farklı yapılandırma** yalnız dev_train'de denendi (defterde 298
  dev_train 1× satırı var: 294 arama + dondurulan 4'ün son değerlendirmesi).
  dev_valid'e yalnız **4 dondurulmuş yapılandırma** ile, her biri **bir kez**
  bakıldı.
- **Mum formasyonları** (çekiç, yutan, harami, yıldız, doji, cımbız vb.) 1h ve
  4h'de maliyetten sonra zarar etti; 1d'de spotta görülen kâr al-tut betasıydı.
  Bu ailenin ilk olumsuz bulgusu budur. **1h grafik formasyonları** da
  maliyetle eridi. İkili/üçlü tepe-dip, omuz-baş-omuz, dikdörtgen ve bayrak
  kırılımları 1h/4h'de zayıf ya da negatifti.
- Umut veren tek bölge **4h üçgen ve kama kırılımları** (ve 4h bütün
  formasyonlar + EMA200 trend filtresi) oldu. Dondurulan 4 yapılandırmadan
  **3'ü aday şartlarını geçti** (hepsi 4h, vadeli):

  | Yapılandırma | dev_valid 1× | 2× | Sharpe | En büyük düşüş | İşlem | DSR |
  |---|---|---|---|---|---|---|
  | F1 üçgen+kama, EMA200, yalnız alım | +0,248 | +0,225 | 1,00 | −0,129 | 39 | 0,10 |
  | F2 üçgen+kama, hacim, iki yön | +0,307 | +0,274 | 1,13 | −0,186 | 55 | 0,14 |
  | F3 bütün tipler, EMA200, 10 bar, yalnız alım | +0,245 | +0,201 | 1,12 | −0,093 | 78 | 0,13 |
  | F4 1d bütün tipler, iki yön (geçmedi) | +0,075 | +0,056 | 0,31 | −0,413 | 39 | 0,02 |

- **Ancak kanıt zayıf:** dev_valid blok bootstrap p ≈ 0,10–0,11; Deflated
  Sharpe 0,10–0,14 (0,95 eşiğinin çok altında). Üç adayın dev_valid kârının
  büyük kısmı tek coinden geliyor (F1 ve F2'de SOL, F3'te BTC); F1'in kârı
  tamamen 2024'ten. Hiçbiri dev_valid'de al-tut'tan fazla kazandırmadı (vadeli
  al-tut +0,508), ama düşüşleri çok daha küçük (−0,09…−0,19'a karşı −0,52).
  Bu sonuçlar "kârlı strateji bulundu" anlamına gelmez; en fazla görülmemiş
  dönemde test edilmeye değer zayıf adaylardır.

## 1. Yaklaşım ve kurallar

Kod: [`grafik_analiz/strategies/formasyon.py`](../../grafik_analiz/strategies/formasyon.py).

**Grafik formasyonları (`yontem="grafik"`):** ATR(14) eşikli zigzag
(`pivots.zigzag`) + `patterns.chart.detect_chart_patterns`; birden çok ölçek
`merge_scales` ile birleştirilir (`analysis.py` ile aynı yol; varsayılan
ölçekler 2 ve 4 ATR). Formasyonun kırılımı `breakout_index` barının
kapanışında bilinir; hedef pozisyon o bardan verilir, işlem harness tarafından
bir sonraki açılışta yapılır. Hedef (ölçülen hareket) ve stop seviyeleri
kırılım barında hesaplanan değerlerdir. Formasyon nesnesinin kırılım sonrası
sonuç alanları (`outcome`, yüksek/düşük ile hesaplanır) **kullanılmadı**;
çıkış ileri yönde yalnız kapanışlarla izlendi.

**Mum formasyonları (`yontem="mum"`):** `patterns.candles.detect_candles`;
sinyal formasyon barının kapanışında, yönü formasyonun klasik eğilimi.

**Çıkışlar (kapanışla; kapanış seviyenin ötesine geçince o barda hedef 0,
çıkış sonraki açılışta):**

| `cikis` | Kural |
|---|---|
| `hedef` | Formasyon hedefi (`hedef_k` × ölçülen hareket) ya da stopu; en fazla formasyon süresi max(2 × genişlik, 10) bar (ya da `max_bar`) |
| `stop_sure` | Yalnız stop + süre |
| `sure` | Sabit `max_bar` (grafik) / `tutma` (mum) bar |
| `atr` (mum) | Giriş kapanışından `stop_k` × ATR stop, `hedef_atr` × ATR hedef, en fazla `tutma` bar |

**Filtreler:** trend (alım için kapanış > EMA(`trend_n`), açığa satış için
kapanış < EMA), hacim (sinyal barı hacmi > `hacim_k` × önceki 20 barın
ortalaması), eğilim uyumu (iki yönlü kırılabilen kama/üçgende yalnız klasik
eğilim yönü), tip grupları.

**Yön ve çakışma:** `uzun` (yalnız alım; düşüş sinyali açık alımı kapatır),
`iki` (alım + açığa satış), `kisa`. Pozisyondayken gelen yeni sinyal eski
işlemin yerini alır (aynı yönse seviye ve süre yenilenir). Aynı barda çelişen
yönler yok sayılır. Pozisyon büyüklüğü 1 (kaldıraç yok). Vadeli bacaklarda
coinin ilk fonlama kaydından önce pozisyon 0. Evren: BTC/ETH/SOL eşit
ağırlık (PORT3; coin listelenmeden önce payı nakitte — harness `combine`).

Nedensellik: `assert_causal` dondurulan dördünde varsayılan kesimlerle ve ek
olarak 0,3/0,5/0,71/0,9/0,999 kesimleriyle geçti; modül içi önbellek (yalnız
hız için, içerik anahtarlı) her denetimden önce boşaltıldı
([`nedensellik.txt`](nedensellik.txt)). Arama öncesinde de 3 örnek
yapılandırmada geçti ([`sinyal_testi.py`](sinyal_testi.py)).

## 2. Arama süreci (yalnız dev_train)

dev_train: verinin başı – 31.12.2023 (spot 2017-08'den, vadeli 2020-01'den,
SOL 2020-08/09'dan). Her yapılandırma `evaluate(spec,
windows=("dev_train",), cost_multipliers=(1.0, 2.0))` ile değerlendirildi;
aynı yapılandırma iki kez değerlendirilmedi. Yıllık/bacak/yön tanıları
defterde kayıtlı yapılandırmalar için `run()` ile, seri 2024-01-01 öncesine
kesilerek yapıldı. Plan ve her aşama sonrası kararlar dev_valid görülmeden
[`NOTLAR.md`](NOTLAR.md)'ye yazıldı. README'deki 1. aşama formasyon
istatistikleri (görülmemiş dönemi de kapsadığı için) okunmadı ve tip seçiminde
kullanılmadı.

| Aşama | Betik | Yapılandırma | İçerik |
|---|---|---|---|
| 1 | `tarama1.py` | 132 | (a) bütün grafik tipleri: 1h/4h/1d × {spot alım, vadeli iki yön} × çıkış {hedef/stop, 20 bar} × trend {yok, EMA200}; (b) 8 grafik tip grubu (ikili, üçlü, OBO, üçgen, kama, dikdörtgen, bayrak, fincan) × 1h/4h/1d × 2 piyasa, hedef/stop; (c) 10 mum grubu (uç doji, çekiç/asılı adam, ters çekiç/kayan yıldız, yutan, harami, delen/kara bulut, sabah/akşam yıldızı, asker/karga, marubozu, cımbız) × 1h/4h/1d × 2 piyasa, 10 bar tutma |
| 2 | `tarama2.py` | 125 | 4h üçgen/kama/üçgen+kama × {vadeli iki, vadeli alım, spot} × çıkış {hedef ×1/×1,5/×2, stop+süre, 20 bar}; filtreler (EMA200, hacim 1,5, eğilim uyumu) ve ölçekler {(2), (4), (2,3,4), (1,5,3)}; 4h bütün tipler + EMA {100, 200, 400} × çıkış {10/20/40 bar, stop+süre, hedef ×1/×2}, hacim; 1d bütün tipler × çıkış {hedef ×0,5/1/1,5/2, stop+süre, 10/20/40 bar} × 3 piyasa-yön, ölçekler, hacim, eğilim; 1d marubozu {5/10/20 bar, ATR 2/4/20} |
| 3 | `tarama3.py` | 37 | Kısa listedeki 5 bölgenin komşuları (EMA 100/400, hedef ×1,5, hacim 1,25/1,5/2, stop+süre, ölçekler, tip alt kümeleri, 5/15 bar, yalnız açığa satış, ATR stop 1,5/2/3, hedef 3/4/6, tutma 10/20/30) |
| Son | `dogrulama.py` | 4 | Dondurulanların tek seferlik dev_train + dev_valid değerlendirmesi |

Deney defteri `arastirma/deneyler/formasyon.jsonl`: dev_train 1× 298, dev_train
2× 298, dev_valid 1× 4, dev_valid 2× 4 satır. Bütün arama satırları
[`tarama_sonuclari.jsonl`](tarama_sonuclari.jsonl) dosyasında da var.

### 2.1 Yöntem × aralık × piyasa-yön özeti (294 arama yapılandırması, dev_train)

Sharpe: günlük net getiriden yıllık. "Poz. 1×/2×": net getirisi pozitif olan
yapılandırma oranı. Kaynak: [`ozet.txt`](ozet.txt).

| Yöntem | Aralık | Piyasa-yön | Sayı | Medyan Sharpe | En iyi | Poz. 1× | Poz. 2× | Medyan işlem |
|---|---|---|---|---|---|---|---|---|
| grafik | 1h | spot alım | 12 | 0,16 | 0,68 | 0,58 | 0,25 | 355 |
| grafik | 1h | vadeli iki | 12 | −0,36 | 0,32 | 0,17 | 0,08 | 532 |
| grafik | 4h | spot alım | 40 | 1,07 | 1,64 | 0,95 | 0,95 | 159,5 |
| grafik | 4h | vadeli alım | 46 | 1,18 | 1,67 | 1,00 | 1,00 | 113 |
| grafik | 4h | vadeli iki | 44 | 0,57 | 1,42 | 0,82 | 0,77 | 183,5 |
| grafik | 4h | vadeli açığa satış | 1 | 0,06 | 0,06 | 0,00 | 0,00 | 62 |
| grafik | 1d | spot alım | 19 | 0,66 | 1,73 | 0,89 | 0,89 | 32 |
| grafik | 1d | vadeli alım | 9 | 1,20 | 1,83 | 1,00 | 1,00 | 41 |
| grafik | 1d | vadeli iki | 34 | 0,79 | 1,64 | 0,82 | 0,82 | 60,5 |
| mum | 1h | spot alım | 10 | −0,28 | 0,12 | 0,20 | 0,00 | 1535 |
| mum | 1h | vadeli iki | 10 | −0,51 | 0,42 | 0,10 | 0,10 | 2074 |
| mum | 4h | spot alım | 10 | 0,30 | 0,58 | 0,70 | 0,20 | 377 |
| mum | 4h | vadeli iki | 10 | −0,05 | 0,58 | 0,20 | 0,10 | 531 |
| mum | 1d | spot alım | 13 | 0,61 | 1,03 | 0,85 | 0,77 | 44 |
| mum | 1d | vadeli alım | 4 | 0,75 | 0,90 | 1,00 | 1,00 | 26 |
| mum | 1d | vadeli iki | 20 | 0,50 | 1,03 | 0,70 | 0,70 | 46 |

Kıyas için dev_train al-tut (PORT3, 1×): spot +35,1 (Sharpe 1,15, en büyük
düşüş −0,86); vadeli +15,1 (Sharpe 1,28, −0,86). Yalnız alım yapan
yapılandırmalarda pozitif getiri bu yüzden kendi başına zayıf kanıttır; iki
yönlü sonuçlar ve açığa satış tarafının ayrı sonucu daha ayırt edicidir.

### 2.2 Aşama 1 tip grupları (dev_train Sharpe 1×, filtresiz)

Grafik formasyonları (hedef/stop çıkışı):

| Grup | 1h spot | 1h vadeli iki | 4h spot | 4h vadeli iki | 1d spot | 1d vadeli iki |
|---|---|---|---|---|---|---|
| ikili tepe/dip | −0,69 | −0,43 | 0,18 | −0,96 | −0,06 | −0,16 |
| üçlü tepe/dip | 0,35 | −0,53 | 0,50 | −0,39 | 0,07 | 0,12 |
| OBO / ters OBO | −0,15 | −0,46 | −0,19 | −0,43 | 0,48 | 0,94 (11 işlem) |
| üçgen | 0,12 | 0,31 | **1,09** | **1,05** | 0,44 | 0,38 |
| kama | 0,35 | 0,10 | **1,05** | 0,36 | 0,27 | 1,05 (20 işlem) |
| dikdörtgen | −0,22 | −0,47 | −0,60 | −1,18 | 0,24 | 0,69 (1 işlem) |
| bayrak | −0,43 | −0,90 | 0,18 | −0,32 | 0,17 | 0,09 |
| fincan-kulp | 0,40 (1 işlem) | 0,32 | 0,36 | 0,73 (2 işlem) | – | – |

Mum formasyonları (10 bar tutma):

| Grup | 1h spot | 1h vadeli iki | 4h spot | 4h vadeli iki | 1d spot | 1d vadeli iki |
|---|---|---|---|---|---|---|
| uç doji | −0,38 | −0,71 | −0,39 | −0,30 | 0,23 | 0,25 |
| çekiç / asılı adam | −1,16 | −1,52 | 0,27 | 0,09 | 0,17 | −0,18 |
| ters çekiç / kayan yıldız | −0,26 | −0,31 | 0,33 | −0,68 | 0,69 | −0,24 |
| yutan | −1,16 | −1,45 | 0,58 | 0,15 | 0,89 | 0,00 |
| harami | −0,50 | −1,31 | 0,32 | −0,72 | −0,22 | −0,67 |
| delen / kara bulut | −0,30 | −0,84 | −0,23 | −0,44 | 0,35 | −0,94 |
| sabah / akşam yıldızı | 0,01 | −0,27 | 0,14 | −0,02 | 0,31 | 0,42 |
| üç asker / üç karga | 0,12 | 0,42 | 0,50 | 0,58 | 1,03 (5 işlem) | 0,11 |
| marubozu | 0,10 | −0,21 | 0,47 | −0,08 | 0,95 | 0,87 |
| cımbız | −0,06 | −0,24 | 0,08 | 0,21 | −0,10 | −0,98 |

Okuma: mum formasyonları vadeli iki yönde neredeyse hep negatif ya da sıfıra
yakın; spot alımda 1d'de pozitif olanlar al-tut Sharpe'ının (1,12–1,15)
altında. 1h'de toplam maliyet kârı aşıyor. Grafik formasyonlarında yalnız
4h üçgen ve kama (ve 1d'de az işlemli bazı gruplar) öne çıktı.

### 2.3 Daraltılan bölgeler (dev_train Sharpe 1×)

4h üçgen+kama, vadeli yalnız alım, hedef/stop:

| Değişiklik | Sharpe | İşlem |
|---|---|---|
| filtresiz | 1,31 | 155 |
| **EMA200 (F1)** | **1,51** | 93 |
| EMA100 / EMA400 | 1,54 / 1,46 | 98 / 89 |
| EMA200 + hedef ×1,5 | 1,35 | 88 |
| EMA200 + hacim 1,5 | 1,67 | 56 |
| EMA200 + stop+süre | 1,15 | 82 |
| EMA200 + ölçek (2,3,4) | 1,21 | 104 |
| EMA200, yalnız üçgen / yalnız kama / + dikdörtgen | 1,30 / 1,17 / 1,40 | 64 / 39 / 97 |
| hacim 1,5 (EMA'sız) | 1,57 | 84 |

4h üçgen+kama, vadeli iki yön, hedef/stop:

| Değişiklik | Sharpe | İşlem |
|---|---|---|
| filtresiz | 0,76 | 282 |
| hacim 1,25 / **1,5 (F2)** / 2,0 | 1,07 / **1,20** / 1,12 | 186 / 146 / 95 |
| hacim 1,5 + EMA200 | 1,42 | 90 |
| hacim 1,5 + hedef ×1,5 | 1,18 | 144 |
| hacim 1,5, yalnız açığa satış | 0,06 | 62 |
| EMA200 | 1,11 | 161 |
| eğilim uyumu | 0,88 | 217 |

4h bütün tipler + EMA200, vadeli yalnız alım, sabit tutma:

| Tutma | 5 | **10 (F3)** | 15 | 20 | 40 |
|---|---|---|---|---|---|
| Sharpe | 1,17 | **1,64** | 1,20 | 1,27 | 0,93 |

10 barda EMA100 1,48, EMA400 1,52, + hacim 1,5 1,45, yalnız üçgen+kama 1,52.
10 bar yerel bir tepedir; komşular ~1,2.

1d bütün tipler, vadeli iki yön, hedef/stop, zigzag ölçekleri:

| Ölçekler | (2,4) | (2,3) | **(2,3,4) (F4)** | (1,5,2,3,4) | (1,5,3) | (3) | (3,4) |
|---|---|---|---|---|---|---|---|
| Sharpe | 1,04 | 1,39 | **1,33** | 1,06 | 0,90 | 0,57 | 0,48 |

(2,3,4) ile: hedef ×1,5 1,42, yalnız alım 1,47, spot alım 1,19, yalnız
üçgen+kama 1,33.

Elenenler: 1d stop+süre (uzun tutma) yapılandırmaları 1,6–1,8 Sharpe
gösterdi ama kârın neredeyse tamamı SOL'un 2021 yükselişinden geliyordu
(SOL bacağı ×75–×200) ve yılda ~9–15 işlem vardı. 4h kama spot stop+süre
(1,64) kârını büyük ölçüde 2021'den aldı. 1d marubozu (vadeli iki yön, ATR
çıkışı 1,03; komşuları 0,88–1,03) yılda ~11 işlem ürettiği için ön yazılı
"yılda ~15+ işlem" ölçütünü karşılamadı ve dondurulmadı.

## 3. Dondurulan yapılandırmalar ve gerekçe

| Kısa ad | Ad | Aralık | Piyasa-yön | Parametreler |
|---|---|---|---|---|
| F1 | `formasyon_ucgen_kama_4h_trend_uzun` | 4h | vadeli, yalnız alım | `{"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "uzun", "cikis": "hedef", "trend_n": 200}` |
| F2 | `formasyon_ucgen_kama_4h_hacim_iki` | 4h | vadeli, alım + açığa satış | `{"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "iki", "cikis": "hedef", "hacim_k": 1.5}` |
| F3 | `formasyon_hepsi_4h_trend_10bar_uzun` | 4h | vadeli, yalnız alım | `{"yontem": "grafik", "tipler": "hepsi", "yon": "uzun", "cikis": "sure", "max_bar": 10, "trend_n": 200}` |
| F4 | `formasyon_hepsi_1d_olcek234_iki` | 1d | vadeli, alım + açığa satış | `{"yontem": "grafik", "tipler": "hepsi", "yon": "iki", "cikis": "hedef", "olcekler": [2.0, 3.0, 4.0]}` |

Hepsi BTC/ETH/SOL vadeli eşit ağırlık. Gerekçe (dev_valid görülmeden
`NOTLAR.md` EK 3'te yazıldı): dev_train'de 1× ve 2× maliyette pozitif;
komşu parametrelerde pozitif; 2020–2023'ün her yılında ve her coinde pozitif;
yılda ≥ 18 işlem; aralarında düşük korelasyon (dev_train günlük: F1–F3 0,52,
diğer çiftler 0,12–0,41). Vadeli al-tut PORT3'e dev_train betası: F1 0,13,
F2 −0,01, F3 0,09, F4 −0,07. F1 ve F3 aynı fikrin (trend yönünde formasyon
kırılımı) iki çıkış biçimidir; F2 ve F4 iki yönlüdür. Spot eşdeğerleri (aynı
kural spotta) ayrıca dondurulmadı. 5 hakkın 4'ü kullanıldı.

dev_train yıllık tanısı (1×, getiri / Sharpe; kaynak
[`tani_dondurulan_dev_train.txt`](tani_dondurulan_dev_train.txt)):

| | 2020 | 2021 | 2022 | 2023 | BTC / ETH / SOL bacak getirisi | Alım / açığa satış net toplamı |
|---|---|---|---|---|---|---|
| F1 | +0,25 / 1,32 | +0,99 / 2,33 | +0,07 / 0,45 | +0,35 / 1,51 | +1,31 / +0,97 / +5,37 | +1,43 / – |
| F2 | +0,02 / 0,22 | +0,80 / 1,82 | +0,44 / 1,74 | +0,20 / 0,97 | +3,58 / +1,36 / +0,47 | +1,30 / +0,02 |
| F3 | +0,18 / 1,43 | +0,62 / 1,74 | +0,08 / 0,75 | +0,65 / 2,64 | +0,16 / +1,85 / +7,49 | +1,31 / – |
| F4 | +0,32 / 1,30 | +1,25 / 2,34 | +0,31 / 0,78 | +0,49 / 1,46 | +3,32 / +1,85 / +4,24 | +2,12 / +0,24 |

(Bacak getirileri bacağın kendi sermayesine göre; yön toplamları portföy
ağırlıklı işlem net getirilerinin toplamıdır.)

## 4. dev_valid sonuçları (01.01.2024 – 30.06.2025, tek değerlendirme)

Kaynak: [`dondurulmus_sonuclar.json`](dondurulmus_sonuclar.json),
[`dogrulama.txt`](dogrulama.txt).

| Yapılandırma | Pencere | Maliyet | Net getiri | Sharpe | En büyük düşüş | İşlem | Bootstrap p | Piyasada |
|---|---|---|---|---|---|---|---|---|
| F1 | dev_train | 1× | +2,577 | 1,508 | −0,243 | 93 | 0,001 | 0,31 |
| F1 | dev_train | 2× | +2,425 | 1,461 | −0,250 | 93 | 0,001 | 0,31 |
| F1 | **dev_valid** | **1×** | **+0,248** | **0,996** | **−0,129** | **39** | 0,106 | 0,28 |
| F1 | **dev_valid** | **2×** | **+0,225** | 0,923 | −0,132 | 39 | 0,121 | 0,28 |
| F2 | dev_train | 1× | +2,185 | 1,202 | −0,298 | 146 | 0,005 | 0,53 |
| F2 | dev_train | 2× | +1,975 | 1,140 | −0,301 | 146 | 0,009 | 0,53 |
| F2 | **dev_valid** | **1×** | **+0,307** | **1,130** | **−0,186** | **55** | 0,110 | 0,38 |
| F2 | **dev_valid** | **2×** | **+0,274** | 1,030 | −0,192 | 55 | 0,133 | 0,38 |
| F3 | dev_train | 1× | +2,401 | 1,643 | −0,130 | 199 | 0,000 | 0,20 |
| F3 | dev_train | 2× | +2,100 | 1,529 | −0,134 | 199 | 0,001 | 0,20 |
| F3 | **dev_valid** | **1×** | **+0,245** | **1,122** | **−0,093** | **78** | 0,096 | 0,20 |
| F3 | **dev_valid** | **2×** | **+0,201** | 0,950 | −0,096 | 78 | 0,139 | 0,20 |
| F4 | dev_train | 1× | +4,786 | 1,326 | −0,355 | 72 | 0,005 | 0,74 |
| F4 | dev_train | 2× | +4,596 | 1,304 | −0,355 | 72 | 0,005 | 0,74 |
| F4 | **dev_valid** | **1×** | **+0,075** | **0,315** | **−0,413** | **39** | 0,330 | 0,92 |
| F4 | **dev_valid** | **2×** | **+0,056** | 0,283 | −0,417 | 39 | 0,348 | 0,92 |

dev_train başlangıcı: F1–F3 2020-01-01 (vadeli 4h), F4 2019-09-08 (vadeli 1d
verisi; ilk fonlama kaydı olan 2020-01-01'e kadar pozisyon 0).

### candidate_check

| Şart | F1 | F2 | F3 | F4 |
|---|---|---|---|---|
| dev_train net > 0 | ✓ | ✓ | ✓ | ✓ |
| dev_valid net > 0 | ✓ | ✓ | ✓ | ✓ |
| dev_valid 2× maliyette net > 0 | ✓ | ✓ | ✓ | ✓ |
| dev_valid Sharpe ≥ 0,5 | ✓ (1,00) | ✓ (1,13) | ✓ (1,12) | ✗ (0,31) |
| dev_valid ≥ 20 işlem | ✓ (39) | ✓ (55) | ✓ (78) | ✓ (39) |
| **Aday** | **EVET** | **EVET** | **EVET** | **HAYIR** |

### Deflated Sharpe (Bailey & López de Prado)

Resmi hesap (görevde tanımlandığı gibi; [`dsr.py`](dsr.py),
[`dsr.txt`](dsr.txt)): deneme sayısı = defterde `pencere=="dev_train"` ve
`maliyet_kat==1.0` satırları = **298** (Sharpe'ı tanımlı 296; işlem üretmeyen 2
satırın Sharpe'ı boş); bu satırların yıllık Sharpe varyansı = **0,4675**
(ortalama 0,60, medyan 0,72, en yüksek 1,83); dev_valid günlük getiri sayısı
547; çarpıklık/basıklık dev_valid günlük getirilerinden (`summarize`).

| Yapılandırma | dev_valid Sharpe | Çarpıklık | Basıklık | **DSR** |
|---|---|---|---|---|
| F1 | 0,996 | 2,567 | 25,69 | **0,1005** |
| F2 | 1,130 | 1,293 | 11,99 | **0,1415** |
| F3 | 1,122 | 3,065 | 37,17 | **0,1281** |
| F4 | 0,315 | 0,554 | 12,49 | **0,0205** |

DSR 0,10–0,14: 298 denemenin en iyisinin şansla bu Sharpe'a ulaşması
dışlanamıyor. Duyarlılık (resmi değil, yalnız bilgi; `dogrulama_tani.json`):
deneme Sharpe varyansı yalnız 4h grafik denemelerinden alınırsa (134 deneme,
varyans 0,293) DSR F1 0,23 / F2 0,29 / F3 0,28 / F4 0,06; deneme sayısı da
134'e indirilirse 0,29 / 0,35 / 0,34 / 0,09. Her iki hesapta da 0,95 eşiğinin
çok altında.

## 5. Al-tut karşılaştırması (aynı pencereler, 1× maliyet)

Kaynak: [`al_tut.py`](al_tut.py), [`al_tut.txt`](al_tut.txt) (`run()` ile,
deftere yazılmadı; vadelide coinin ilk fonlama kaydından önce pozisyon 0).
dev_valid al-tut değerleri dondurmadan sonra hesaplandı.

| Pencere | Piyasa (aralık) | BTC | ETH | SOL | PORT3 getiri (Sharpe, en büyük düşüş) |
|---|---|---|---|---|---|
| dev_train | spot (4h) | +8,75 | +6,40 | +33,30 | +35,14 (1,15, −0,86) |
| dev_train | vadeli (4h) | +2,21 | +7,36 | +32,83 | +15,14 (1,28, −0,86) |
| dev_train | vadeli (1d) | +2,22 | +7,38 | +33,91 | +16,67 (1,26, −0,85) |
| dev_valid | spot (4h) | +1,534 | +0,089 | +0,522 | +0,743 (0,90, −0,515) |
| dev_valid | vadeli (4h) | +1,197 | −0,067 | +0,327 | **+0,508 (0,75, −0,521)** |
| dev_valid | vadeli (1d) | +1,198 | −0,067 | +0,328 | +0,504 (0,74, −0,498) |

Vadeli al-tut PORT3 (4h) dev_valid yılları: 2024 +0,677 (Sharpe 1,15), 2025
ilk yarı −0,100 (0,03).

- dev_train'de al-tut stratejilerin hepsinden çok daha fazla kazandırdı
  (vadeli +15,1'e karşı +2,2…+4,8); stratejilerin Sharpe'ı (1,2–1,6) al-tut'a
  (1,28) yakın ya da biraz üstünde, düşüşleri çok daha küçük (−0,13…−0,36'ya
  karşı −0,86).
- dev_valid'de üç aday da vadeli al-tut'un getirisinin altında (+0,25…+0,31'e
  karşı +0,51) ama Sharpe'ları daha yüksek (1,00–1,13'e karşı 0,75) ve
  düşüşleri çok daha küçük (−0,09…−0,19'a karşı −0,52). F2'nin al-tut ile
  günlük korelasyonu −0,05 (beta −0,01): getirisi piyasa yönünden bağımsız.

## 6. Dondurma sonrası tanılar (seçimi değiştirmez)

Kaynak: [`dogrulama_tani.py`](dogrulama_tani.py),
[`dogrulama_tani.json`](dogrulama_tani.json). Aynı spec'lerle `run()`,
dev_valid parçalara ayrıldı.

| | F1 | F2 | F3 | F4 |
|---|---|---|---|---|
| 2024 getiri / Sharpe (işlem) | +0,259 / 1,46 (26) | +0,172 / 1,09 (34) | +0,212 / 1,53 (55) | −0,103 / −0,13 (26) |
| 2025 ilk yarı getiri / Sharpe (işlem) | −0,009 / −0,04 (13) | +0,116 / 1,21 (21) | +0,028 / 0,43 (23) | +0,198 / 1,09 (13) |
| Bacak BTC / ETH / SOL getiri | −0,04 / −0,01 / +0,92 | +0,01 / +0,04 / +0,94 | +0,47 / −0,01 / +0,26 | +0,02 / +0,47 / −0,43 |
| Alım işlemleri: sayı / net toplam | 39 / +0,26 | 26 / +0,22 | 78 / +0,25 | 19 / +0,30 |
| Açığa satış işlemleri: sayı / net toplam | – | 29 / +0,10 | – | 20 / −0,23 |
| Kazanma oranı / kâr faktörü | 0,46 / 1,71 | 0,49 / 1,61 | 0,53 / 1,57 | 0,41 / 1,10 |
| En iyi işlem çıkınca getiri | +0,123 | +0,169 | +0,155 | −0,061 |
| Toplam maliyet / fonlama (1×) | 0,018 / 0,021 | 0,026 / −0,005 | 0,036 / 0,020 | 0,018 / 0,025 |
| Al-tut ile günlük korelasyon / beta | 0,46 / 0,12 | −0,05 / −0,01 | 0,41 / 0,09 | 0,00 / 0,00 |

dev_valid günlük getiri korelasyonu: F1–F3 0,62, F1–F2 0,20, F2–F3 0,15,
F4 ile diğerleri 0,06–0,18.

- F1'in dev_valid kârının tamamı 2024'ten ve SOL bacağından; BTC ve ETH
  bacakları yaklaşık sıfır/negatif. 2025'in ilk yarısında başabaş.
- F2 iki dönemde ve iki yönde de pozitif tek yapılandırma; dev_train'de
  açığa satış tarafı başabaştı (+0,02), dev_valid'de +0,10. Ama kâr yine
  çoğunlukla SOL bacağından (BTC +0,01, ETH +0,04).
- F3'te kâr BTC (+0,47) ve SOL (+0,26) bacaklarından; ETH ≈ 0. 2025 ilk
  yarısı zayıf pozitif.
- F1 ile F3 aynı fikrin iki biçimidir (korelasyon 0,62); finalist seçilirse
  bağımsız iki aday sayılmamalıdır.
- F4 dev_valid'de neredeyse sürekli piyasada (0,92) ve açığa satış tarafı
  zarar etti (−0,23); en iyi işlem çıkınca negatif.

## 7. Sonuç

1. **Mum formasyonları** (Binance standart maliyetleriyle) 1h ve 4h'de kârlı
   değil; vadeli iki yönde neredeyse hepsi negatif. 1d'de spot alım
   sonuçları al-tut betasından öteye geçmiyor. Bu ailenin ana olumsuz
   bulgusudur. İkili/üçlü tepe-dip, OBO, dikdörtgen ve bayrak kırılımları da
   1h/4h'de değer üretmedi; 1h'de her şey maliyetle eridi.
2. **4h üçgen ve kama kırılımları** (vadeli; trend ya da hacim filtresiyle)
   ve **4h bütün formasyonlar + EMA200 + kısa tutma**, dev_train ve dev_valid'de
   pozitif, 2× maliyette de pozitif ve aday şartlarını geçti (F1, F2, F3).
   Al-tut'tan daha az kazandırdılar ama düşüşleri çok daha küçük ve Sharpe'ları
   biraz daha yüksekti.
3. **İstatistiksel kanıt zayıf:** DSR 0,10–0,14, bootstrap p ≈ 0,10–0,11.
   dev_valid kârları tek coine (çoğunlukla SOL) dayanıyor ve 18 aylık,
   39–78 işlemlik küçük bir örneklem. Bu adaylar "kârlı" sayılmamalı; ancak
   görülmemiş dönemde Seviye 1/2 şartlarıyla test edilmeye aday olabilirler.
   Finalist seçilirse en savunulabilir olanı F2'dir (iki yön, al-tut betası
   ≈ 0, iki dönemde de pozitif); F1 ve F3 tek fikir olarak ele alınmalı.
4. 1d iki yönlü formasyon stratejisi (F4) dev_train'deki iyi görünümüne
   rağmen dev_valid'de başarısız oldu (Sharpe 0,31, açığa satış zararda): bu,
   dev_train sonuçlarının dev_valid'e ne kadar zayıf taşındığının bir örneğidir.

## 8. Protokol notları ve sınırlamalar

- Parametre seçimi yalnız dev_train ile yapıldı; dev_valid'e yalnız dondurulan
  4 yapılandırma ile bir kez bakıldı (`dogrulama.py`, yeniden çalıştırmada
  değerlendirilmiş spec'i atlayacak biçimde yazıldı). dev_valid sonrası hiçbir
  kural/parametre değiştirilmedi. Sonradan yalnız spec açıklama metinlerine
  candidate_check sonucu yazıldı (sayıları etkilemez).
- Yeniden üretim (`yeniden_uretim.py`, [`yeniden_uretim.txt`](yeniden_uretim.txt)):
  `specs()` dev_train 1× ve 2× sayılarını birebir üretti (`record=False`,
  dev_valid'e ikinci bakış yok).
- Dondurma sonrası tanılar (`dogrulama_tani.py`) ve al-tut kıyası `run()` ile
  hesaplandı, deftere yazılmadı; seçimi etkilemedi.
- Harness işlem sayımı aynı yöndeki kesintisiz pozisyon dilimlerini sayar:
  pozisyondayken gelen aynı yönlü yeni formasyon sinyali ayrı işlem
  sayılmaz. Günlük getiri ölçüleri bundan etkilenmez.
- README'deki 1. aşama formasyon istatistikleri (bütün veri) okunmadı. Diğer
  ailelerin raporlarından yalnız `kirilim/RAPOR.md` biçim örneği olarak
  okundu; içeriği seçimde kullanılmadı.
- Sınırlama: araştırmacının (modelin) kripto piyasasının 2024–2025 seyrine
  dair genel bilgisi vardır; bu bilgi seçimi bilinçli olarak etkilemedi ama
  tamamen dışlanamaz. Bağımsız ölçüm görülmemiş dönem ve ileriye dönük
  takiptir.
- PORT3'te SOL listelenmeden önceki dönemde 1/3 pay nakitte durur (harness
  `combine` davranışı); `combine` her bar maliyetsiz yeniden dengeleme varsayar.
- Deneme sayısı 298, aynı yapılandırmanın arama satırı ile son değerlendirme
  satırını ayrı sayar (benzersiz yapılandırma 294).

## Dosyalar

| Dosya | İçerik |
|---|---|
| `NOTLAR.md` | Aramadan önce yazılan plan ve her aşama sonrası kararlar (EK 1–3) |
| `ortak.py` | `evaluate()` sarmalayıcı, yinelenen deneme önleme, dev_train tanısı |
| `sinyal_testi.py` | Sinyal doğruluk testleri ve örnek `assert_causal` (getiri hesaplamaz) |
| `tarama1.py`, `tarama2.py`, `tarama3.py` (+ `.log`) | Arama aşamaları |
| `tarama_sonuclari.jsonl` | Bütün arama satırları (dev_train 1× ve 2×) |
| `tani.py`, `tani_dondurulan_dev_train.txt` | dev_train yıllık/bacak/yön tanısı |
| `korelasyon.py` | Kısa listenin dev_train korelasyonu ve betası |
| `ozet.py`, `ozet.txt` | Arama özeti tabloları |
| `nedensellik.py`, `nedensellik.txt` | `assert_causal` |
| `dogrulama.py`, `dogrulama.txt`, `dondurulmus_sonuclar.json` | Tek seferlik dev_valid değerlendirmesi ve candidate_check |
| `dsr.py`, `dsr.txt`, `dsr.json` | Deflated Sharpe |
| `dogrulama_tani.py`, `dogrulama_tani.txt`, `dogrulama_tani.json` | Dondurma sonrası tanılar, DSR duyarlılığı |
| `al_tut.py`, `al_tut.txt`, `al_tut_*.csv` | Al-tut kıyası |
| `yeniden_uretim.py`, `yeniden_uretim.txt` | `specs()` sayılarının yeniden üretimi (dev_train) |
