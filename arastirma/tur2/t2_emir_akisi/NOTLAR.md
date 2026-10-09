# t2_emir_akisi — çalışma notları

Protokol sürüm 2 (`docs/PROTOKOL_2.md`). Aile anahtarı `t2_emir_akisi`.
Defter: `arastirma/tur2/deneyler/t2_emir_akisi.jsonl`.

## Plan (9 Ekim 2026, hiçbir sonuç görülmeden önce yazıldı)

Veri: mumlardaki `taker_buy_base` ve `volume`. Bar başına alıcı-taker
dengesizliği `imb = (2·taker_buy_base − volume) / volume` (−1…1),
kümülatif hacim deltası `CVD = Σ (2·taker_buy_base − volume)`.

Sinyal skoru S (pozitif = akış fiyata göre alım yönünde):

1. `akis`: n barlık normalleştirilmiş CVD değişimi
   `Σ_n delta / Σ_n hacim`, L barlık kayan z-skoru.
2. `patlama`: tek bar dengesizliğinin z-skoru, isteğe bağlı hacim şartı
   (hacim / L barlık ortalama hacim ≥ v).
3. `uyumsuzluk`: akış z-skoru − n barlık getiri z-skoru (CVD–fiyat
   uyumsuzluğu; akış güçlü, fiyat zayıfsa pozitif).
4. `cvd_aralik`: klasik CVD uyumsuzluğu; fiyatın ve CVD'nin n barlık aralık
   içindeki konumu farkı.
5. `spot_vadeli`: spot akışı − vadeli akışı (aynı coin, aynı zaman dilimi),
   z-skoru. Diğer piyasanın mumları `research.data.load(scope="dev")` ile
   yüklenir ve geçirilen verinin son barına kesilir.

Kural: |S| > k olduğunda tetik. `devam` = S yönünde, `donus` = S'nin tersine
pozisyon. Pozisyon son tetikten sonra `hold` bar tutulur (yeni tetik süreyi
uzatır, ters tetik yön değiştirir). İsteğe bağlı: yalnız uzun / yalnız kısa,
z-skoru normale dönünce erken çıkış.

Yürütme: piyasa emri (protokol maliyeti) ve limit emir (giriş ve/veya çıkış;
sinyal barının kapanışından `bps` uzakta, çıkışta belirli bar sonra piyasa
emrine dönüş).

Aşamalar (yalnız dev_train, `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0,))`):

- Aşama 1 — kenar haritası: vadeli, BTC/ETH/SOL eşit ağırlıklı, piyasa emri,
  5m/15m/1h; her sinyal türü için kaba ızgara. Her yapılandırma için işlem
  başına brüt getiri, işlem başına maliyet ve net ölçülür. Devam ve dönüş
  ayrı ayrı denenir.
- Aşama 2 — brüt kenarı maliyetin üstünde ya da yakınında olan bölgelerde:
  eşik, tutma süresi, çıkış kuralı, limit emir yürütmesi, spot sürümleri.
- Aşama 3 — en fazla 5 yapılandırma dondurulur (gerekçe aşağıya, dev_valid
  değerlendirmesinden **önce** yazılır), her biri `evaluate(spec)` ile bir kez
  ölçülür, `candidate_check` ve `assert_causal` uygulanır.

Seçim ölçütleri (dev_train): net getiri > 0, alfa > 0, 2× maliyette net > 0,
yeterli işlem, alt dönemlerde (yıllar) tutarlılık, komşu parametrelerde
dayanıklılık. Hiçbiri yoksa en iyi dürüst denemeler dondurulur ve sonuç
olumsuz raporlanır.

## Aşama kayıtları

(aşağıya eklenir)

## Kesinti ve devam (9 Ekim 2026, 11:45 UTC)

Önceki çalışma oturumu kullanım sınırı nedeniyle arama ortasında durdu
(son defter satırı 09:08:28 UTC). Hiçbir dev_valid değerlendirmesi yapılmadı;
defterdeki 288 satırın hepsi `dev_train`, maliyet 1× satırıdır. Bu oturumda iş
baştan başlatılmadan kaldığı yerden sürdürülüyor; mevcut 288 satır deneme olarak
sayılır (silinmez, değiştirilmez).

Durum kontrolü:

- `tarama1.py` beş grubu da bitirmiş: akis 72, patlama 36, uyumsuzluk 54,
  cvd_aralik 54, spot_vadeli 72 = 288 yapılandırma; `tarama1.csv` 288 satır +
  başlık; defterle birebir. Kesik kalan tarama yok, yeniden çalıştırma gerekmiyor.
- `patlama` (`vol_v=None`) yapılandırmaları tanım gereği `akis` (n=1) ile aynı
  sinyali üretiyor (12 yinelenen satır); defterde ayrı deneme olarak kalıyor.
- Modüle kesinti öncesinde `akis_artik` (fiyatla açıklanamayan akış) ve
  `getiri` (akışsız fiyat kontrolü) türleri eklenmiş, ama henüz hiç
  değerlendirilmemiş.

### Aşama 1 özeti (dev_train, vadeli PORT3, piyasa emri, devam yönü)

- `akis` (CVD z-skoru, devam): 5m ve 15m'de işlem başına brüt kenar yaklaşık
  0 (−2…+3 bps), maliyet yaklaşık 14 bps → hepsi zararda. 1h'de uzun pencere +
  uzun tutma bölgesi pozitif (n72 k2 h24: %+90, Sharpe 0,74, alfa %+13,
  brüt 83 bps/işlem, 301 işlem), komşuları zayıf.
- `patlama` (tek bar dengesizlik sıçraması): kenar yok; hacim şartlı sürümde
  işlem sayısı çok az (≤48).
- `uyumsuzluk` (akış z − getiri z, devam): en güçlü bölge. 5m n72/n288 k3,
  15m n24 k3, 1h n6 k3 yapılandırmalarında brüt 60–160 bps/işlem, beta ≈ 0,
  alfa %+15…+28. Ama skor büyük ölçüde getiri z-skorunun tersi; yani kenar
  akıştan değil, aşırı fiyat hareketinin geri dönüşünden geliyor olabilir.
  Bu yüzden Aşama 2'nin ilk işi akışsız fiyat kontrolüdür.
- `cvd_aralik` devam: büyük ölçüde negatif brüt (dönüş yönü fiyat aralığı
  momentumuna denk; beta yüksek).
- `spot_vadeli` devam: negatif; n72 1h'de brüt −25…−56 bps (dönüş yönü
  denenebilir).

### Aşama 2 planı (devam eden oturum, sonuçlar görülmeden önce)

1. Kontrol: `getiri` + `mode="donus"` (akışsız, aşırı fiyat hareketinden dönüş),
   `uyumsuzluk` ızgarasıyla aynı n/k/hold. Akış, fiyat dönüşüne bir şey
   katıyor mu?
2. `akis_artik` devam: fiyatla açıklanamayan akış tek başına öngörü taşıyor mu?
3. Akış katkısı varsa: koşullu kurallar (fiyat aşırı düştü + akış satış
   yönünde değil gibi), eşik/L/çıkış/yön inceltmesi, limit emir yürütmesi,
   spot sürümü, 2× maliyet.
4. Yıllara, coinlere ve komşu parametrelere göre dayanıklılık; en iyi işlem
   etkisi; işlem başına brüt kenar / maliyet oranı.

### Aşama 2a sonuçları (kontroller; 135 yapılandırma, `tarama2.csv`)

- `getiri` dönüş (akışsız fiyat kontrolü, 54): aynı n/k/hold'da `uyumsuzluk`
  devamdan belirgin zayıf. Örn. 5m n72 k3 h12: %+126 / Sharpe 0,87 / brüt
  29 bps (uyumsuzluk: %+299 / 1,76 / 72 bps); 5m n288 k3 h12: %−2 (uyumsuzluk
  %+144); 1h n6 k3 h24: %−9 (uyumsuzluk %+271). Pozitif olan fiyat dönüşü
  sonuçları SOL ve 2021 ağırlıklı (SOL bacağı %+1200), BTC çoğunlukla negatif.
  → Akış, fiyat dönüşünün üstüne bilgi katıyor.
- `akis_artik` devam (fiyatla açıklanamayan akış, 54): k=3'te pozitif bölge
  15m n24 (h4: %+105, Sharpe 1,24, 5 yılın hepsi pozitif, 3 bacak pozitif;
  h16: %+168, Sharpe 1,27, 5 yıl pozitif, 3 bacak pozitif), 5m n72 (h12:
  %+67, Sharpe 0,83, 5 yıl pozitif; h48: %+97). k=2 hep zayıf/negatif.
  Beta ≈ 0. Akışın kendisinde (fiyattan bağımsız) devam kenarı var.
- `getiri_artik` dönüş (akışla açıklanamayan fiyat hareketi, yalnız k=3, 27):
  pozitif sonuçlar fiyat dönüşü gibi SOL/2021 ağırlıklı, yıllar arası
  tutarsız.

### Aşama 2b planı (inceltme; sonuçlar görülmeden önce)

Odak: `akis_artik` devam ve `uyumsuzluk` devam. Her yapılandırma 1× ve 2×
maliyetle (dev_train). Izgara:

- `akis_artik` 15m: n {12, 24, 48} × k {2.5, 3, 3.5} × hold {4, 8, 16, 32}.
- `akis_artik` 5m: n {36, 72, 144} × k {2.5, 3, 3.5} × hold {12, 24, 48}.
- `uyumsuzluk` 15m: n {12, 24, 48} × k {2.5, 3, 3.5} × hold {2, 4, 8}.
- `uyumsuzluk` 5m: n {36, 72, 144} × k {2.5, 3, 3.5} × hold {6, 12, 24}.
- Merkez noktalarda L {1000, 4000}, `exit_z` erken çıkış, tek yön (uzun /
  kısa) ayrıştırması, limit emir yürütmesi ve spot sürümü ayrı adımda.

## Kesinti ve devam (2) (9 Ekim 2026, 16:30 UTC)

Çalışma ikinci kez durdu (kullanım sınırı/oturum kesintisi; son defter satırı
11:54 UTC). Hiçbir dev_valid değerlendirmesi yapılmadı; defterde 657 satır var,
hepsi `dev_train` (288 + 135 satır 1×; Aşama 2b'nin 117 yapılandırması 1× ve 2×
= 234 satır). Kaldığı yerden sürdürülüyor; mevcut satırlar deneme sayılır,
silinmez, değiştirilmez.

Durum kontrolü:

- `tarama3.py` dört grubu da bitirmiş: artik15 36, artik5 27, uyum15 27,
  uyum5 27 = 117 yapılandırma; `tarama3.csv` 117 satır + başlık; defterle
  birebir (117 × 2 satır). Kesik tarama yok.
- `tarama1.csv` başlığı 25 sütunlu, bacak sütunları (`leg_*`) olan satırlar
  28 alanlı; dosya bozuk değil, okurken başlık `tarama2.csv`'den alınmalı.

### Aşama 2b sonuçları (dev_train, vadeli PORT3, piyasa emri; `tarama3.csv`)

- `uyumsuzluk` devam: k=3,5 bölgesi 5m ve 15m'de her n'de güçlü ve komşu
  parametrelerde düzgün. Örn. 5m n72 k3,5 h12: %+450, Sharpe 2,26, düşüş
  %−16, 398 işlem, alfa %+36,5 (t 5,2), beta −0,01, brüt 140 bps/işlem,
  2× maliyette %+357; yılların hepsi pozitif (2020 +34, 2021 +140, 2022 +20,
  2023 +16, 2024 +22 %). 15m n24 k3,5 h2: %+369, Sharpe 2,02, 479 işlem.
  15m n48 belirgin zayıf (Sharpe 0,7–1,0). k=2,5 işlem sayısını 2–3 katına
  çıkarıyor, brüt/işlem 20–60 bps'e düşüyor, 2× maliyette çoğu zararda.
- `akis_artik` devam: k ≥ 3'te 5m n144 ve 15m n12/n24 bölgeleri pozitif,
  yıllar arası tutarlı (5m n144 k3 h24: %+199, Sharpe 1,44, alfa %+26,
  865 işlem, brüt 54 bps). 15m n48 ve k=2,5 zayıf/negatif.
- Uyarı: Aşama 2a'daki "akışsız fiyat dönüşü" kontrolü aynı k ile yapıldı;
  `uyumsuzluk` skorunun ölçeği farklı olduğundan aynı k'da işlem sayısı
  2–2,5 kat az (örn. 5m n72 k3 h12: getiri 1645, uyumsuzluk 693 işlem).
  Adil karşılaştırma için işlem sayısı eşlenmiş kontrol gerekiyor.

### Aşama 2c planı (sonuçlar görülmeden önce yazıldı)

Hepsi dev_train, 1× ve 2× maliyet:

1. Eşlenmiş kontrol: `getiri` dönüş, k {4, 5}, merkez noktalarda
   (5m n72 h12, 5m n36 h24, 5m n144 h12, 15m n24 h2, 15m n24 h4).
   Akış, eşit sıklıktaki aşırı fiyat dönüşüne bilgi katıyor mu?
2. Dayanıklılık (uyumsuzluk 5m n72 k3,5 h12; 15m n24 k3,5 h2; 5m n36 k3,5 h24;
   akis_artik 5m n144 k3 h24; 15m n12 k3,5 h8): L {1000, 4000}, k 4,
   tek yön (uzun / kısa), `exit_z` 0.
3. Limit emir yürütmesi (uyumsuzluk 5m n72 k3,5 h12 ve 15m n24 k3,5 h2):
   giriş limiti 0 / 10 / 30 bps, çıkış piyasa; giriş piyasa + çıkış limiti
   10 bps (zaman aşımı 3 bar). Ters seçilim (dolmayan işlemlerin iyi
   olanlar olması) ölçülür.
4. Spot sürümü (yalnız uzun, spot maliyeti) aynı merkezlerde.
5. 1h uyumsuzluk: n {6, 12} × k {3, 3,5} × hold {1, 3}.

### Aşama 2c sonuçları (dev_train, 1× ve 2×; `tarama4.csv`, `tani1.log`, `tani2.log`)

61 yapılandırma (`tarama4.py`: kontrol 10, dayanım 30, limit 8, spot 5, 1h 8).
Bu aşamadan sonra defterde 779 satır: 601 dev_train 1×, 178 dev_train 2×.

- **Eşlenmiş kontrol (en önemli bulgu):** akışsız fiyat dönüşü, işlem sayısı
  eşlenince `uyumsuzluk` kadar iyi. 5m n72 h12: getiri dönüş k5 %+413,
  Sharpe 2,29, 296 işlem, alfa %+35 (uyumsuzluk k3,5: %+450, 2,26, 398 işlem,
  alfa %+36,5). 15m n24 h2: getiri k5 Sharpe 1,85 / uyumsuzluk 2,02.
  5m n36 h24: getiri k5 1,91 / uyumsuzluk 1,93. Günlük getiri korelasyonu
  uyumsuzluk 5m ↔ getiri k5 = 0,79. Tanı 1: `uyumsuzluk > 3,5` olaylarının
  kârı, aynı anda fiyat z-skoru < −4 olan olaylardan geliyor (+139 bps,
  n=1822 bar); fiyat düşüşü olmadan akış güçlü olan olaylar −32 bps (n=787).
  Fiyat z < −4 olaylarında akış üçte birliklerine göre ileri getiri monoton
  değil (+56 / +19 / +115 bps). **Sonuç: uyumsuzluk kenarının çoğu aşırı
  fiyat düşüşünden dönüş (çöküş sonrası tepki); akışın ek katkısı küçük ve
  belirsiz.**
- `akis_artik` (fiyattan arındırılmış akış, devam): 15m n12 k3,5 h8 L'ye
  dayanıklı (L1000 Sharpe 1,36, L4000 1,50, k4 1,52); 5m n144 k3 h24 L'ye
  dayanıksız (L1000 0,37, L4000 0,29) → elendi. Kenarın tamamına yakını uzun
  yönde (uzun %+163, kısa %+5). Spot sürümü çalışmıyor (Sharpe 0,40).
  Kâr çok yoğun: en iyi 20 gün toplam log getirinin %99'u.
- Yön: bütün merkezlerde kenar uzun yönde (çöküş sonrası alım); kısa yön
  küçük pozitif (Sharpe 0,2–0,7).
- `exit_z` 0: küçük iyileşme (5m n72: Sharpe 2,25 / %+470), merkez korunur.
- Limit emir: giriş limiti 0/10/30 bps ya da çıkış limiti 10 bps sonucu
  pek değiştirmiyor (5m n72: Sharpe 2,20–2,25; 15m n24: 1,95–2,00). Brüt
  kenar (100–140 bps/işlem) maliyetin (13–14 bps/işlem) çok üstünde
  olduğundan limit emre gerek yok; ters seçilim de görülmedi.
- Spot (yalnız uzun): uyumsuzluk 5m n72 k3,5 h12 %+290, Sharpe 2,21,
  321 işlem, alfa %+29, 2× %+202.
- 1h uyumsuzluk: n6 k3 h1 Sharpe 1,29; n12 zayıf (0,28–0,52). 5m/15m'nin
  gerisinde.
- Yoğunlaşma (tani2): bütün adaylarda kârın büyük kısmı az sayıda çöküş
  gününden geliyor (uyumsuzluk 5m: en iyi 10 gün %46, en iyi 20 gün %68;
  aktif gün 225 / ~1650). 2× maliyet testi geçiliyor ama çöküş anlarında
  gerçek kayma 2 bps'ten büyük olabilir; bu, varsayımın en zayıf yeri.

## Dondurma kararı (9 Ekim 2026, dev_valid değerlendirmesinden ÖNCE yazıldı)

Seçim yalnız dev_train sonuçlarına dayanır. Beş yapılandırma:

| # | Ad | Piyasa | Aralık | Parametreler | Gerekçe (dev_train) |
|---|---|---|---|---|---|
| 1 | `t2_emir_akisi_uyum_5m_n72_k3.5_h12` | vadeli PORT3 | 5m | uyumsuzluk, n72, L2000, k3,5, devam, hold 12, iki yön, piyasa emri | Ailenin en güçlü bölgesinin merkezi: %+450, Sharpe 2,26, alfa %+36,5 (t 5,2), 2× %+357, 5 yılın hepsi pozitif; L, k, exit_z, limit komşuları Sharpe 1,79–2,25. |
| 2 | `t2_emir_akisi_uyum_15m_n24_k3.5_h2` | vadeli PORT3 | 15m | uyumsuzluk, n24, L2000, k3,5, devam, hold 2 | Farklı zaman dilimi (1 ile korelasyon 0,59): %+369, Sharpe 2,02, alfa %+32; L1000/L4000 1,68/1,78, k4 1,77. |
| 3 | `t2_emir_akisi_artik_15m_n12_k3.5_h8` | vadeli PORT3 | 15m | akis_artik, n12, L2000, k3,5, devam, hold 8 | Fiyattan arındırılmış saf akış sinyali: %+174, Sharpe 1,48, alfa %+23,5, 2× %+105, 5 yıl pozitif; L1000/L4000 1,36/1,50, k4 1,52. (5m n144 L'ye dayanıksız olduğu için seçilmedi.) |
| 4 | `t2_emir_akisi_uyum_spot_5m_n72_k3.5_h12_uzun` | spot PORT3 | 5m | uyumsuzluk, n72, L2000, k3,5, devam, hold 12, yalnız uzun | Spot (kaldıraçsız, fonlamasız) uygulama: %+290, Sharpe 2,21, alfa %+29, 2× %+202. |
| 5 | `t2_emir_akisi_kontrol_getiri_donus_5m_n72_k5_h12` | vadeli PORT3 | 5m | getiri (akışsız), n72, L2000, k5, dönüş, hold 12 | **Akışsız kontrol**, önceden kayda geçirilmiş: işlem sayısı eşlenmiş fiyat dönüşü (%+413, Sharpe 2,29). 1 ile karşılaştırılarak akışın dev_valid'de ek katkı yapıp yapmadığı ölçülür. |

Her biri `evaluate(spec)` ile bir kez (dev_train + dev_valid, 1× ve 2×)
değerlendirilir, ardından `candidate_check`; `assert_causal` değerlendirmeden
önce çalıştırılır. Deflated Sharpe: deneme sayısı = defterdeki
`pencere == "dev_train"` ve `maliyet_kat == 1.0` satırları. dev_valid'den sonra
parametre değişikliği yapılmaz.

Beklenti (önceden yazılıyor): Kâr çöküş günlerine bağlı olduğundan dev_valid
sonucu bu dönemdeki ani düşüşlerin sayısına çok duyarlı olacak; az çöküş
olursa işlem sayısı ve getiri düşük kalabilir. 1 ile 5 arasındaki fark,
akışın ek bilgisinin ölçüsüdür.
