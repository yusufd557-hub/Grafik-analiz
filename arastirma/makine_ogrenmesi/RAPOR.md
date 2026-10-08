# Makine öğrenmesi ailesi (`makine_ogrenmesi`) — araştırma raporu

Protokol: [`docs/PROTOKOL.md`](../../docs/PROTOKOL.md), sürüm 1. Bütün sayılar
harness'ten (`grafik_analiz.research.evaluate`, `run`, `summarize`) alınmıştır.
Getiriler net (komisyon + kayma, vadelide fonlama dahil) ve oran olarak verilir
(0,23 = %23). Görülmemiş döneme (1 Temmuz 2025 sonrası) hiç erişilmedi;
`unlock_holdout()` çağrılmadı, `scope="holdout"`/`"all"` kullanılmadı.

## Kısa sonuç

- **157 farklı yapılandırma** yalnız dev_train'de (veri başı – 31.12.2023) denendi.
  Defterde 161 dev_train satırı (1× maliyet) vardır: 157 arama + dondurulan 4
  yapılandırmanın son değerlendirmesi. dev_valid'e yalnız **4 dondurulmuş
  yapılandırma** ile, her biri **bir kez** bakıldı.
- Günlük ve 4 saatlik modeller al-tuttan ayırt edilemedi (kâr büyük ölçüde
  piyasa yönünden). Vadelide kendi (2020 sonrası) verisiyle eğitilen iki yönlü
  modeller maliyetten sonra zayıftı. Tutarlı tek bölge: **1 saatlik bar, kısa
  ufuk (4–8 bar), yüksek işlem eşiği (tahmini kenar > 3 × gidiş-dönüş maliyeti),
  HistGradientBoosting, son H kararın ortalaması kadar pozisyon**. Vadelide model
  aynı coinlerin **spot geçmişiyle** (2017'den) eğitildiğinde belirgin biçimde
  daha iyiydi.
- Dondurulan 4 yapılandırmanın **4'ü de aday şartlarını geçti** (dev_valid 1×:
  +%23,1 / +%13,2 / +%9,1 / +%3,4; 2×: +%15,2 / +%10,3 / +%8,2 / +%2,0).
- **Ancak sonuçlar güçlü kanıt değildir:**
  - Çoklu deneme düzeltmeli **Deflated Sharpe 0,25–0,91**; hiçbiri 0,95'e ulaşmıyor.
  - Kârın büyük kısmı **SOL bacağından** geliyor; BTC bacağı dev_valid'de neredeyse
    sıfır (BTC al-tut bu dönemde +%153 iken).
  - Modeller dev_valid'de dev_train'e göre **çok daha az işlem** yaptı (pozisyonda
    kalma %1–17); spot +btc yapılandırması yalnız 27 işlemle geçti.
  - 4 yapılandırma aynı fikrin varyantlarıdır (dev_valid günlük getiri
    korelasyonu 0,22–0,80).
  - Al-tut dev_valid'de çok daha fazla kazandı (spot +%75, vadeli +%52) ama −%52
    düşüş yaşadı; stratejilerin düşüşü −%2…−%9.
- En savunulabilir olanı **vadeli yalnız alım hgb_reg H4 k3** yapılandırmasıdır:
  dev_valid'in iki yarısında da pozitif (2024 +%7,5, 2025 ilk yarı +%5,3), üç
  bacak da pozitif, 2× maliyette Sharpe 1,21, blok bootstrap p = 0,016. Bu bile
  çoklu deneme düzeltmesinden sonra (DSR 0,61) anlamlı değildir. Görülmemiş
  dönemde test edilmeye değer bir aday düzeyidir, "kanıtlanmış kârlı sistem"
  değildir.

## 1. Yöntem

Kod: [`grafik_analiz/strategies/makine_ogrenmesi.py`](../../grafik_analiz/strategies/makine_ogrenmesi.py).
Bütün eğitim `signal_fn` içinde ileriye yürüyerek yapılır:

- **Modeller:** L2 düzenlileştirilmiş lojistik regresyon (`logit`, C = 0,05,
  yalnız eğitim satırlarına uydurulan ölçekleyici, ±5'te kırpma),
  `HistGradientBoostingClassifier` (`hgb_clf`), `HistGradientBoostingRegressor`
  (`hgb_reg`). HGB: 150 ağaç, öğrenme hızı 0,05, en çok 15 yaprak, yaprakta en az
  200 örnek, L2 = 1, erken durdurma yok, `random_state=0` (belirlenimci).
- **Hedef:** `H` bar ileri getiri, stratejinin t barındaki kararla gerçekten
  yakalayacağı biçimde: `open[t+1+H] / open[t+1] − 1`. Sınıflandırıcılar işaretini,
  regresör oynaklığa bölünmüş (σ_t·√H) ve ±4'te kırpılmış değerini öğrenir.
- **İleriye yürüyen eğitim ve arındırma:** Model her takvim ayı başında (ya da üç
  ayda bir) yeniden eğitilir. O ay içindeki barların tahmini, yalnız **etiketinin
  bittiği bar (t+1+H) eğitim tarihinden önce açılmış** satırlarla eğitilen modelden
  gelir. İlk tahmin, verinin başından en az 365 gün sonra ve en az 500 eğitim
  satırı varken yapılır. Eğitim penceresi genişleyen (varsayılan) ya da son 730 /
  1095 gün. Örtüşen etiketlerin etkisini azaltmak için eğitimde her `max(1, H/4)`
  barda bir satır alınır.
- **Havuz:** Aynı spec'teki üç coinin satırları tek modelde eğitilir (özellikler
  ölçekten bağımsızdır). `egitim="spot"` (yalnız vadeli): model aynı coinlerin spot
  1h satırlarıyla (2017'den) eğitilir, tahmin vadeli barların özelliklerinden
  yapılır. Spot bacaklar spec'e sıfır ağırlıkla eklenir ve pozisyonları hep 0'dır.
- **Özellikler** (yalnız t ve önceki barlar; geriye dönük pencere, `shift(+k)`,
  baştan başlayan EWM; tam örneklem normalleştirmesi yok): 1–128 bar oynaklığa
  bölünmüş getiriler, oynaklık oranları ve 500 barlık yuvarlanan sırası, EMA
  20/50/200 uzaklığı (ATR cinsinden), RSI, stokastik, Bollinger konumu/genişlik
  sırası, ADX ve DI farkı, MACD histogramı, CCI, MFI, Donchian 20/100 konumu,
  500 barlık tepeden düşüş, hacim ve işlem sayısı oranları, alıcı (taker-buy)
  payı (1/8/32 bar), mum gövde/fitil/kapanış yeri. Seçmeli: `detect_candles`
  bayraklarından net mum puanı (`+mum`), BTC'nin 4/16/64 bar getirisi (`+btc`),
  vadelide fonlama (`+fon`; yalnız kayıt zamanı ≤ bar açılışı olan kayıtlar).
- **Pozisyon:** Kenar tahmini regresörde `ŷ·σ·√H`, sınıflandırıcıda
  `(2p−1)·√(2/π)·σ·√H`. Kenar > `k` × gidiş-dönüş maliyeti (spot 0,24%, vadeli
  0,14%) ise alım; vadelide iki yönlü sürümde kenar < −`k` × maliyet ise açığa
  satış; değilse nakit. `esleme="ortusen"`: pozisyon son H kararın ortalamasıdır
  (H örtüşen alt portföy, 0…1); `esleme="esik"`: her bar yeniden karar.
  Vadelide coinin ilk fonlama kaydından önce pozisyon 0. Evren: BTC/ETH/SOL eşit
  sermaye ağırlığı (1/3); kaldıraç yok.

## 2. Arama süreci ve parametre aralıkları (yalnız dev_train)

Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))`
ile değerlendirildi (`ortak.py`), aynı ad iki kez değerlendirilmedi. Ara tanılar
(yıllık, bacak bazında) yalnız defterde zaten kayıtlı yapılandırmalar için `run()`
ile hesaplandı; seriler ölçüden önce 2024-01-01'de kesildi. Her aşamadan sonra
(dev_valid görülmeden) yazılan notlar: [`NOTLAR.md`](NOTLAR.md). Bütün satırlar:
[`tarama_sonuclari.jsonl`](tarama_sonuclari.jsonl).

| Aşama | Betik | Yapılandırma | İçerik |
|---|---|---|---|
| 1 | tarama1.py | 54 | aralık {1d, 4h, 1h} × piyasa {spot yalnız alım, vadeli iki yön} × model {logit, hgb_clf, hgb_reg} × H (1d: 4/8/16, 4h: 6/12/24, 1h: 4/12/24); k = 1 |
| 2a | tarama2.py | 44 | işlem eşiği k ∈ {2, 3}; vadelide yalnız alım |
| 2b | tarama3.py | 32 | 1h: H ∈ {6, 8}; `+mum`, `+btc`; kayan pencere 730/1095 gün; `esik` eşlemesi; HGB düzenlileştirme (yaprak 31 / min 100; 200 ağaç, lr 0,03, min 500); vadeli `egitim="spot"`, `+fon` |
| 3 | tarama4.py | 19 | vadeli egitim=spot komşuları (H 4/6/8, k 2/3/4, yalnız alım/iki yön, `+btc`, üç ayda bir eğitim, hgb_clf, logit); spot üç ayda bir eğitim, k = 2,5 |
| 4 | tarama5.py | 8 | vadeli egitim=spot hgb_clf komşuları (H4 k2/k4, H6 k3), HGB düzenlileştirme, 4h sürümü |
| **Toplam** | | **157** | |

Parametre aralıkları özetle: aralık {1h, 4h, 1d}; model {logit, hgb_clf, hgb_reg};
H {4, 6, 8, 12, 16, 24} (aralığa göre); k {1, 2, 2,5, 3, 4}; eşleme {ortusen, esik};
pencere {genişleyen, 730, 1095 gün}; yeniden eğitim {1, 3 ay}; özellik {temel,
+mum, +btc, +fon}; vadeli yön {iki, uzun}; vadeli eğitim {kendi, spot}.

## 3. dev_train sonuçları

Not: dev_train Sharpe'ı günlük net getirilerden yıllıklandırılır. `egitim="spot"`
vadeli spec'lerde birleşik getiri serisi sıfır ağırlıklı spot bacaklar yüzünden
2017-08'de başlar ve 2020'ye kadar sıfırdır; bu, dev_train Sharpe'ını aşağı çeker
(aşağıda ayrıca 2020'den ölçülen değerler verildi).

### 3.1 Grup özetleri (1× / 2× maliyet Sharpe)

| Grup | n | 1× medyan | 1× en iyi | 2× medyan | 2× en iyi | 2×'te pozitif |
|---|---|---|---|---|---|---|
| 1d spot yalnız alım | 9 | 0,77 | 0,93 | 0,75 | 0,91 | 9/9 |
| 1d vadeli iki yön | 9 | −0,11 | 0,56 | −0,12 | 0,55 | 3/9 |
| 4h spot yalnız alım | 21 | 1,09 | 1,29 | 0,94 | 1,16 | 21/21 |
| 4h vadeli iki yön (kendi verisi) | 13 | 0,51 | 0,80 | 0,31 | 0,59 | 8/13 |
| 4h vadeli yalnız alım (kendi verisi) | 4 | 0,91 | 1,03 | 0,81 | 0,90 | 4/4 |
| 4h vadeli (spot geçmişi; yalnız alım / iki yön) | 2 | 1,04 / 1,00 | 1,04 | 0,94 / 0,83 | 0,94 | 2/2 |
| 1h spot yalnız alım | 46 | 1,40 | 1,70 | 0,99 | 1,17 | 43/46 |
| 1h vadeli iki yön (kendi verisi) | 18 | 0,57 | 0,95 | 0,22 | 0,55 | 10/18 |
| 1h vadeli yalnız alım (kendi verisi) | 8 | 1,10 | 1,27 | 0,76 | 1,00 | 8/8 |
| 1h vadeli iki yön (spot geçmişi) | 13 | 1,52 | 1,90 | 1,17 | 1,42 | 13/13 |
| 1h vadeli yalnız alım (spot geçmişi) | 14 | 1,50 | 1,70 | 1,23 | 1,37 | 14/14 |

Model bazında 1× medyan Sharpe (bütün aralıklar birlikte): hgb_reg 1,29
(76 yapılandırma), hgb_clf 0,99 (47), logit 0,87 (34).

### 3.2 Ana varyantlar

| Yapılandırma | 1× getiri | 1× Sharpe | 2× getiri | 2× Sharpe | En büyük düşüş | İşlem | Pozisyonda | Toplam maliyet |
|---|---|---|---|---|---|---|---|---|
| 1d spot hgb_reg H8 k1 | +6,09 | 0,93 | +5,68 | 0,91 | −0,73 | 58 | %62 | 0,06 |
| 4h spot hgb_reg H12 k1 | +15,48 | 1,24 | +10,61 | 1,11 | −0,64 | 252 | %81 | 0,35 |
| 4h spot hgb_reg H12 k3 | +12,55 | 1,29 | +8,82 | 1,16 | −0,50 | 381 | %76 | 0,32 |
| 1h spot hgb_reg H4 k1 | +8,14 | 1,57 | +0,93 | 0,55 | −0,25 | 2951 | %33 | 1,55 |
| 1h spot hgb_reg H4 k2 | +4,26 | 1,65 | +1,98 | 1,12 | −0,16 | 1204 | %14 | 0,57 |
| 1h spot hgb_reg H4 k2, `esik` eşleme | +1,75 | 0,91 | −0,43 | −0,35 | −0,29 | 1960 | %7 | 1,57 |
| 1h spot hgb_reg H4 k2, pencere 730 gün | +2,26 | 1,06 | +0,58 | 0,47 | −0,20 | 1576 | %17 | 0,72 |
| 1h spot hgb_reg H4 k2 +btc | +4,92 | 1,70 | +2,21 | 1,15 | −0,17 | 1310 | %14 | 0,61 |
| 1h spot logit H4 k2 | +1,85 | 1,23 | +0,79 | 0,72 | −0,17 | 957 | %10 | 0,46 |
| 1h vadeli iki yön hgb_clf H12 k1 (kendi) | +1,68 | 0,82 | +0,04 | 0,22 | −0,45 | 2935 | %74 | 0,94 |
| 1h vadeli yalnız alım hgb_reg H4 k3 (kendi) | +1,49 | 1,10 | +0,80 | 0,75 | −0,32 | 1210 | %19 | 0,32 |
| aynı, +fon | +1,73 | 1,13 | +1,04 | 0,84 | −0,25 | 1007 | %18 | 0,29 |
| 1h vadeli yalnız alım hgb_reg H4 k3 (spot geçmişi) | +5,13 | 1,63 | +3,47 | 1,37 | −0,22 | 1124 | %13 | 0,31 |
| 1h vadeli iki yön hgb_reg H4 k3 (spot geçmişi) | +5,11 | 1,63 | +2,87 | 1,25 | −0,19 | 1727 | %17 | 0,46 |
| 1h vadeli iki yön hgb_clf H6 k3 (spot geçmişi) | +9,19 | 1,84 | +4,71 | 1,42 | −0,28 | 2278 | %28 | 0,58 |
| 1h vadeli yalnız alım logit H4 k3 (spot geçmişi) | +2,62 | 1,30 | +1,73 | 1,04 | −0,23 | 986 | %10 | 0,28 |
| 4h vadeli yalnız alım hgb_reg H6 k2 (spot geçmişi) | +8,21 | 1,04 | +5,96 | 0,94 | −0,63 | 583 | %56 | 0,28 |

Al-tut (dev_train, eşit ağırlık): spot 1h 2017-08'den +38,61, Sharpe 1,17,
en büyük düşüş −0,86 (sabit 0,5 pozisyon: +9,19, Sharpe 1,19, −0,59); spot,
tahminlerin başladığı 2018-09'dan Sharpe 1,17; vadeli 1h 2020'den +15,94,
Sharpe 1,29, −0,86.

Gözlemler:

- 1d ve 4h modellerin Sharpe'ı al-tut düzeyinde ya da altında, pozisyonda kalma
  çoğunlukla %60–80; 4h spot hgb_reg H12'nin yıllık dökümünde 2018 ve 2022 negatif,
  kârın çoğu 2021'den → kâr büyük ölçüde piyasa yönünden. 1d vadeli iki yön
  çoğunlukla zararda.
- 1h modellerin brüt zamanlama sinyali var ama k = 1'de maliyet sermayenin 1,5–2
  katı; işlem eşiğini 2–3 × maliyete çıkarmak ve örtüşen pozisyon kullanmak
  sonucu 2× maliyette de pozitif tuttu. Her bar yeniden karar (`esik`) ve kayan
  pencere belirgin biçimde kötü.
- Vadelide yalnız kendi (2020 sonrası) verisiyle eğitim zayıf; aynı modeli spot
  geçmişiyle eğitmek 1× Sharpe'ı 1,10'dan 1,63'e çıkardı. Fonlama özelliği katkı
  vermedi. Açığa satış tarafı yalnız spot geçmişiyle eğitimde değer kattı.
- Logit, aynı ayarlarda HGB'den belirgin biçimde zayıf.

### 3.3 Dondurulanların dev_train yıllık dökümü (tahminlerin başladığı tarihten)

[`tani_secim_vadeli.log`](tani_secim_vadeli.log), [`tani_secim_spot.log`](tani_secim_spot.log)
(getiri / yıllık Sharpe):

| Yapılandırma | Maliyet | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | Başlangıçtan Sharpe |
|---|---|---|---|---|---|---|---|---|
| Vadeli iki yön hgb_clf H6 k3 | 1× | – | – | +0,83 / 2,83 | +2,71 / 4,61 | +0,21 / 0,71 | +0,24 / 2,47 | 2,33 (2020'den) |
| | 2× | – | – | +0,58 / 2,20 | +1,88 / 3,79 | +0,07 / 0,37 | +0,17 / 1,81 | 1,80 |
| Vadeli yalnız alım hgb_reg H4 k3 | 1× | – | – | +0,37 / 2,09 | +1,93 / 4,13 | +0,26 / 0,86 | +0,21 / 2,15 | 2,06 (2020'den) |
| | 2× | – | – | +0,28 / 1,69 | +1,51 / 3,58 | +0,19 / 0,68 | +0,17 / 1,80 | 1,73 |
| Spot hgb_reg H6 k3 | 1× | +0,06 / 1,52 | +0,11 / 2,44 | +0,33 / 1,40 | +1,13 / 3,32 | +0,09 / 0,48 | +0,15 / 1,84 | 1,59 (2018-09'dan) |
| | 2× | +0,02 / 0,59 | +0,08 / 1,73 | +0,25 / 1,13 | +0,90 / 2,85 | +0,03 / 0,25 | +0,12 / 1,57 | 1,26 |
| Spot hgb_reg H4 k3 +btc | 1× | +0,08 / 2,39 | −0,02 / −0,58 | +0,36 / 1,64 | +1,03 / 3,29 | +0,13 / 0,80 | +0,04 / 1,13 | 1,60 (2018-09'dan) |
| | 2× | +0,05 / 1,58 | −0,03 / −1,17 | +0,30 / 1,44 | +0,80 / 2,80 | +0,07 / 0,50 | +0,03 / 0,80 | 1,27 |

(Spot 2018 satırı Eylül–Aralık'tır.) Bacak bazında dev_train (1×): bütün bacaklar
pozitif, ama SOL baskın (ör. vadeli hgb_reg H4 k3: BTC +0,94, ETH +3,16, SOL +15,70).

## 4. Dondurma gerekçesi

Seçim kuralı aramadan önce yazıldı (NOTLAR.md, EK 0): dev_train'de 1× ve 2×
net pozitif; 2× Sharpe'a göre sıralama; komşu parametrelerde de pozitif kalma;
dev_train yıllarının çoğunda pozitif; tek yılın getiriyi taşımaması. Karar
dev_valid görülmeden NOTLAR.md EK 5'e yazıldı:

1. **`ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot`** — aramadaki en
   yüksek 2× Sharpe (1,42); komşuları (H4 k2/k3/k4, H6 yalnız alım) 1,21–1,30;
   2020–2023 her yıl 1× ve 2× pozitif.
2. **`ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot`** — 2× Sharpe'ta
   ikinci (1,37), her yıl pozitif, regresör (model çeşitliliği), yalnız alım.
3. **`ml_1h_sp_PORT3_hgb_reg_H6_k3.0_ortusen_uzun_temel`** — spotta 2018–2023
   her yıl 1× ve 2× pozitif olan tek yakın aday.
4. **`ml_1h_sp_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel-btc`** — spotta en yüksek
   2× Sharpe (1,17).

Elenenler: spot H4 k2 +btc (2× maliyette 2018, 2019, 2022 negatif), spot
hgb_clf H12 k3 (2022 negatif), vadeli H6/H8 yalnız alım (2022 2× maliyette ≈ 0
ya da negatif). Beşinci bir yapılandırma dev_valid'e fazladan bakış eklememek için
dondurulmadı. Dondurmadan sonra dört spec `assert_causal` denetiminden (0,55 /
0,8 / 0,97 ve ek 0,3 kesimi) geçti ([`nedensellik_1.log`](nedensellik_1.log),
[`nedensellik_2.log`](nedensellik_2.log)).

## 5. dev_valid sonuçları (01.01.2024 – 30.06.2025, tek seferlik)

[`dogrulama.py`](dogrulama.py), çıktı: [`dondurulmus/`](dondurulmus/),
[`dogrulama_1.log`](dogrulama_1.log), [`dogrulama_2.log`](dogrulama_2.log).

| Yapılandırma | Maliyet | Getiri | Sharpe | En büyük düşüş | İşlem | Pozisyonda | Maliyet | p (bootstrap) | En iyi işlem çıkınca |
|---|---|---|---|---|---|---|---|---|---|
| Vadeli iki yön hgb_clf H6 k3 | 1× | +0,2314 | 1,41 | −0,089 | 320 | %17,3 | 0,067 | 0,024 | +0,2045 |
| | 2× | +0,1517 | 0,98 | −0,091 | 320 | %17,3 | 0,134 | 0,083 | +0,1266 |
| Vadeli yalnız alım hgb_reg H4 k3 | 1× | +0,1316 | 1,50 | −0,035 | 112 | %4,5 | 0,025 | 0,016 | +0,1008 |
| | 2× | +0,1032 | 1,21 | −0,036 | 112 | %4,5 | 0,051 | 0,043 | +0,0733 |
| Spot hgb_reg H6 k3 | 1× | +0,0341 | 0,76 | −0,029 | 55 | %2,8 | 0,014 | 0,173 | +0,0219 |
| | 2× | +0,0197 | 0,45 | −0,030 | 55 | %2,8 | 0,028 | 0,290 | +0,0078 |
| Spot hgb_reg H4 k3 +btc | 1× | +0,0909 | 1,88 | −0,022 | 27 | %0,9 | 0,008 | 0,0004 | +0,0604 |
| | 2× | +0,0822 | 1,79 | −0,023 | 27 | %0,9 | 0,016 | 0,001 | +0,0522 |

Aynı yapılandırmaların dev_train değerleri (son değerlendirme, §3 ile aynı):
1×/2× getiri +9,19/+4,71, +5,13/+3,47, +3,18/+2,02, +2,45/+1,63; Sharpe
1,84/1,42, 1,63/1,37, 1,46/1,15, 1,46/1,17.

**candidate_check:** dördü de bütün şartları geçti (dev_train net > 0, dev_valid
net > 0, 2× maliyette net > 0, Sharpe ≥ 0,5, en az 20 işlem). Spot H6 k3 Sharpe
şartını küçük farkla (0,76), spot H4 +btc işlem şartını küçük farkla (27) geçti.

Yıl ve bacak dökümü (dev_valid, 1× / 2×):

| Yapılandırma | 2024 | 2025 (ilk yarı) | BTC bacağı | ETH bacağı | SOL bacağı |
|---|---|---|---|---|---|
| Vadeli iki yön hgb_clf H6 k3 | +0,229 / +0,175 | +0,002 / −0,020 | +0,004 / −0,017 | +0,007 / −0,046 | +0,785 / +0,576 |
| Vadeli yalnız alım hgb_reg H4 k3 | +0,075 / +0,058 | +0,053 / +0,043 | +0,013 / +0,006 | +0,130 / +0,113 | +0,245 / +0,180 |
| Spot hgb_reg H6 k3 | +0,029 / +0,020 | +0,005 / −0,000 | +0,000 / −0,002 | +0,025 / +0,017 | +0,075 / +0,042 |
| Spot hgb_reg H4 k3 +btc | +0,061 / +0,057 | +0,028 / +0,024 | +0,001 / +0,000 | +0,030 / +0,024 | +0,253 / +0,231 |

(Bacak getirileri bacağın kendi sermayesine göredir; portföye katkısı 1/3'tür.)

dev_valid günlük getiri korelasyonu (1×): vadeli hgb_reg ile spot H6 0,80, spot
+btc ile spot H6 0,74, vadeli hgb_reg ile spot +btc 0,68; vadeli iki yönlü hgb_clf
diğerleriyle 0,22–0,40.

## 6. Deflated Sharpe (dev_valid)

[`dsr.py`](dsr.py) → [`dsr_sonuc.json`](dsr_sonuc.json). Deneme sayısı = defterde
`pencere == "dev_train"` ve `maliyet_kat == 1.0` olan satırlar = **161**; bu
satırların yıllık Sharpe varyansı = **0,2324**; dev_valid günlük getirileri
(547 gün) ve `summarize`'ın çarpıklık/basıklık değerleri. Bu ayarla şansla
beklenen en yüksek yıllık Sharpe ≈ **1,30**.

| Yapılandırma | dev_valid Sharpe | Çarpıklık | Basıklık | DSR | Düzeltmesiz PSR(0) |
|---|---|---|---|---|---|
| Vadeli iki yön hgb_clf H6 k3 | 1,41 | −1,93 | 58,3 | **0,55** | 0,94 |
| Vadeli yalnız alım hgb_reg H4 k3 | 1,50 | 3,70 | 55,4 | **0,61** | 0,98 |
| Spot hgb_reg H6 k3 | 0,76 | 1,31 | 72,7 | **0,25** | 0,83 |
| Spot hgb_reg H4 k3 +btc | 1,88 | 11,04 | 156,4 | **0,91** | 1,00 |

Hiçbiri 0,95 düzeyine ulaşmıyor. Spot +btc'nin yüksek DSR'ı dikkatle okunmalı:
yalnız 27 işlem var ve günlük getirilerin çarpıklığı 11'dir; DSR formülü pozitif
çarpıklığı ödüllendirdiği için birkaç büyük kazançlı gün sonucu yukarı itiyor.

## 7. Al-tut karşılaştırması (aynı pencereler)

[`al_tut.py`](al_tut.py) → [`al_tut_dev_train_dev_valid.csv`](al_tut_dev_train_dev_valid.csv)
(1h, BTC/ETH/SOL eşit ağırlık, vadelide fonlama kaydından önce 0):

| Pencere | Al-tut | Getiri | Sharpe | En büyük düşüş |
|---|---|---|---|---|
| dev_train | spot (2017-08'den) | +38,61 | 1,17 | −0,86 |
| dev_train | spot, sabit 0,5 | +9,19 | 1,19 | −0,59 |
| dev_train | vadeli (2020'den) | +15,94 | 1,29 | −0,86 |
| dev_valid | spot | +0,754 | 0,91 | −0,52 |
| dev_valid | spot, sabit 0,5 | +0,436 | 0,92 | −0,30 |
| dev_valid | vadeli | +0,518 | 0,75 | −0,52 |
| dev_valid | vadeli, sabit 0,5 | +0,335 | 0,77 | −0,30 |

dev_valid'de coin bazında al-tut: spot BTC +1,53, ETH +0,09, SOL +0,52; vadeli BTC
+1,20, ETH −0,07, SOL +0,33. Al-tut 2024'te +0,92 (spot), 2025 ilk yarısında −0,08.

Stratejiler al-tuttan **çok daha az getiri** ama (spot H6 hariç) **daha yüksek
Sharpe** ve çok daha küçük düşüş verdi; zamanın yalnız %1–17'sinde pozisyondalar.
Al-tutun dev_valid getirisinin çoğunu sağlayan BTC yükselişinden stratejiler
neredeyse hiç pay almadı.

## 8. Zayıf yönler ve riskler

- **SOL bağımlılığı:** Kenar σ ile ölçeklenip sabit maliyet eşiğiyle
  karşılaştırıldığı için model en oynak coinde ve dönemde işlem yapıyor. dev_valid
  kârının çoğu SOL bacağından; vadeli iki yönlü sürümde 2× maliyette BTC ve ETH
  bacakları negatif.
- **Oynaklık rejimine bağımlılık:** 1h medyan σ (BTC/ETH/SOL) 2020–21'de
  %0,64/%0,83/%1,41, dev_valid'de %0,46/%0,61/%0,83 ([`tani_oynaklik.log`](tani_oynaklik.log)).
  İşlem sayısı ve pozisyonda kalma buna paralel düştü; düşük oynaklıkta strateji
  neredeyse hiç işlem yapmıyor.
- **dev_train kârı 2021'de yoğun**, 2022 bütün yapılandırmalarda zayıf.
- **Çoklu deneme:** 157 yapılandırma denendi; DSR'lar anlamlı değil. Dondurulan
  dördü aynı fikrin varyantları; birlikte geçmeleri bağımsız dört kanıt değildir.
- **Az işlem:** Spot +btc (27 işlem) ve spot H6 (55 işlem) için dev_valid ölçüleri
  birkaç işleme dayanıyor.
- İşlem düzeyindeki ölçüler aynı yöndeki pozisyon büyüklüğü değişimlerinin
  maliyetini işleme yazmıyor (harness notu); günlük getiri ölçüleri bunları içerir.

## 9. Sonuç

Makine öğrenmesi ailesinde maliyet sonrası kâr yalnız tek bir dar bölgede
bulundu: 1 saatlik barda, kısa ufuklu, HGB ile tahmin edilen kenarın maliyetin
3 katını aştığı nadir anlarda işlem. Bu bölge dev_train'de geniş bir komşulukta
pozitifti ve dondurulan dört yapılandırmanın dördü de dev_valid aday şartlarını
geçti. Ancak dev_valid kârı küçük (spot +%3–9, vadeli +%13–23), büyük ölçüde SOL'den
geliyor, çoklu deneme düzeltmesinden sonra anlamlı değil (DSR 0,25–0,91) ve al-tutun
getirisinin çok altında kaldı. Günlük ve 4 saatlik ML modelleri ile vadelide kendi
verisiyle eğitilen iki yönlü modeller al-tuta değer katmadı.

Görülmemiş dönem için finalist adayı olarak en savunulabilir yapılandırma
**`ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot`**'tır (iki yarıda ve üç
bacakta da pozitif, 2× maliyette Sharpe 1,21, p = 0,016). Vadeli iki yönlü hgb_clf
daha yüksek getiri verdi ama 2025'in ilk yarısında sıfır ve SOL dışı bacaklarda
2× maliyette negatif. Spot yapılandırmaları çok az işlemle geçti. Hiçbiri
"kârlı olduğu kanıtlanmış" değildir; düşük oynaklık dönemlerinde neredeyse hiç
işlem yapmamaları beklenmelidir.

## 10. Dosyalar ve yeniden üretim

- Strateji modülü: `grafik_analiz/strategies/makine_ogrenmesi.py` (`specs()` dondurulan
  4 yapılandırmayı döndürür; açıklamalarında candidate_check sonucu yazılıdır).
- Arama: `ortak.py`, `tarama1.py` … `tarama5.py`, günlükler `tarama*_*.log`,
  sonuçlar `tarama_sonuclari.jsonl`; deney defteri `arastirma/deneyler/makine_ogrenmesi.jsonl`
  (157 yapılandırma × 2 maliyet dev_train + 4 dondurulmuş × (2 dev_train + 2 dev_valid) = 330 satır).
- Tanılar: `tani.py`, `tani_donem.py`, `tani_secim.py`, `tani_ozellik.py`,
  `al_tut.py`, `al_tut_ayni_donem.py`.
- Dondurma sonrası: `nedensellik.py`, `dogrulama.py`, `dsr.py`, `yeniden_uretim.py`
  ([`yeniden_uretim_1.log`](yeniden_uretim_1.log), [`yeniden_uretim_2.log`](yeniden_uretim_2.log):
  `run()` ile dört yapılandırmanın bütün sayıları aynen yeniden üretildi).
- Çalışma süresi: 1h spec başına sinyal hesabı ≈ 100–170 sn (2 iş parçacığı);
  `assert_causal` ≈ 6–9 dk.

Çalıştırma ortamı: `GRAFIK_ANALIZ_ARASTIRMA=/home/user/arastirma_veri OMP_NUM_THREADS=2`.

## 11. Harness ile ilgili notlar (değiştirilmedi)

- `assert_causal` fonlamayı kesim barının **açılış** zamanında keser (`f.index <= cut`).
  Protokol fonlamanın bar kapanışına kadar kullanılmasına izin verdiği için, 1d (ve 4h)
  barda gün içinde kaydedilen fonlamayı kapanışta kullanan doğru bir strateji yanlış
  alarm alır. Bu ailede fonlama özelliği ihtiyatlı olarak bar açılışına hizalandı.
- Sıfır ağırlıklı bacaklar (`egitim="spot"` için yalnız veri girdisi olarak eklenen spot
  bacaklar) birleşik getiri serisini 2017-08'e uzatır; vadeli stratejinin dev_train
  ölçüleri 2017–2019 arasındaki sıfır getirili günleri de içerir (başlangıç tarihi 2017,
  Sharpe aşağı, pozisyonda kalma oranı seyrelir). Bir stratejinin başka bir piyasanın
  verisini bacak eklemeden okuyabileceği bir yol yok.
- Deflated Sharpe'ta deneme Sharpe'ları farklı uzunlukta dev_train pencerelerinden
  (spot 2017'den, vadeli 2020'den) gelir; ayrıca formül yüksek pozitif çarpıklığı
  ödüllendirir (spot +btc: 27 işlem, çarpıklık 11, DSR 0,91).
- İşlem düzeyindeki ölçüler aynı yöndeki büyüklük değişimlerinin maliyetini işleme
  yazmaz; `ortusen` eşlemede pozisyon sık sık büyüklük değiştirdiği için işlem bazlı
  kazanma oranı ve ortalama işlem iyimserdir (günlük getiri ölçüleri doğrudur).
