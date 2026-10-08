# Takvim / mevsimsellik ailesi (`mevsimsellik`) — araştırma raporu

Protokol: [`docs/PROTOKOL.md`](../../docs/PROTOKOL.md), sürüm 1. Bütün sayılar
harness'ten (`grafik_analiz.research.evaluate`, `run`, `summarize`) alınmıştır.
Getiriler net (komisyon + kayma, vadelide fonlama dahil) ve oran olarak verilir
(0,48 = %48; 12,53 = %1.253). Görülmemiş döneme (1 Temmuz 2025 sonrası) hiç
erişilmedi. `unlock_holdout()` çağrılmadı.

## Kısa sonuç

- **Sonuç olumsuz: aday yok.** Dondurulan 4 yapılandırmanın hiçbiri aday
  şartlarını geçmedi.
- Gün içi etkiler (UTC saati, New York saati, fonlama anı çevresi, uyarlamalı
  saat seçimi) brüt olarak en çok birkaç baz puandır. Vadeli gidiş-dönüş maliyeti
  14 bp, spot 24 bp olduğu için **hepsi maliyetle eridi**. dev_train'de 1×
  maliyette en iyisi Sharpe 0,49 (fonlama penceresi), 2× maliyette hepsi zararda.
- Haftanın günü etkileri zayıf ya da al-tutun kopyası.
- dev_train'de tek güçlü etki **ay dönümüydü**: ayın son birkaç günü ile sonraki
  ayın ilk birkaç günü. 96 ay dönümü yapılandırmasının hepsi 1× ve 2× maliyette
  kârlıydı (Sharpe 1,09–2,02). Plasebo kaydırmasında 28 konum içinde 1. oldu.
- Bu etki dev_valid'de (2024-01 – 2025-06) **tersine döndü**. Dondurulan 4
  yapılandırma 1× maliyette −%36 ile −%44 arası, Sharpe −0,91 ile −1,01 arası
  sonuç verdi. En büyük düşüş −%50 ile −%58 arasıydı. Aynı dönemde al-tut kârlıydı
  (spot PORT3 +%73,7). Deflated Sharpe bütün dondurulmuş yapılandırmalar için 0'dır.
- Ders: dev_train'de çok yıllı, maliyete dayanıklı ve plasebo testini geçen bir
  takvim etkisi bile 18 aylık yeni veride tutmadı. Tek bir takvim etkisine dayalı
  strateji önerilmez.

## 1. Denenen yaklaşımlar

Kod: [`grafik_analiz/strategies/mevsimsellik.py`](../../grafik_analiz/strategies/mevsimsellik.py)
(`sinyal`, `make_spec`).

Bütün sinyaller nedenseldir. Takvim sinyalleri yalnız **bir sonraki barın
başlangıç zamanına** bakar; takvim önceden bilinir. Uyarlamalı yöntemler yalnız
geçmiş günlerin/ayların getirisini kullanır ve tahmin günü/ayı hariç tutulur.
Fonlama koşulunda yalnız pencere başlamadan önce kaydedilmiş oran kullanılır.
Vadeli bacakta coinin ilk fonlama kaydından önce pozisyon 0'dır (BTC 1d vadeli
2019-09'dan başlar, fonlama 2020-01-01'den). Spotta yalnız alım, vadelide alım
ve isteğe bağlı açığa satış vardır. Kaldıraç yoktur. PORT3 = BTC/ETH/SOL eşit
sermaye (1/3; SOL verisi başlamadan önce payı nakitte). PORT2 = BTC+ETH.

| Yöntem | Kural |
|---|---|
| `ay_donumu` | Ayın son `a` günü + sonraki ayın ilk `b` günü (UTC) alım, diğer günler nakit. İsteğe bağlı `kayma_saat` ile pencere saat olarak kaydırılır. `yon="uzun_kisa"`: pencere dışında açığa satış. |
| `ay_donumu_kademeli` | a ∈ [a_alt, a_ust], b ∈ [b_alt, b_ust] pencerelerinin ortalaması. Kademeli pozisyon (0,25 / 0,5 / 0,75 / 1) tek bir (a, b) seçimine bağlı kalmaz. |
| `hafta_gunu` | Seçilen haftanın günlerinde (UTC) alım. |
| `saat` | Seçilen saatlerde alım (vadelide ayrıca seçilen saatlerde açığa satış). Saat dilimi UTC ya da America/New_York (yaz saati dahil). İsteğe bağlı yalnız hafta içi. |
| `fonlama` | Fonlama anı S (00/08/16 UTC) çevresindeki [S + bas_dk, S + bas_dk + tut_dk) penceresi. Bir önceki fonlama oranı > `esik` ise alım (ya da açığa satış). |
| `uyarlamali_saat` | Her saat için son L günün o saatteki getiri ortalaması > `esik_bp` ise alım, < −`esik_bp` ise açığa satış (ileriye yürüyen tahmin). |
| `uyarlamali_ay` | Ay içi her gün konumu için geçmiş ayların ortalaması − genel ortalama > `esik_bp` ise alım (ileriye yürüyen tahmin, en az 12 ay). |

## 2. Keşif (betimsel, yalnız dev_train)

Strateji değerlendirmesi değildir ve deftere yazılmaz. Veri `load(scope="dev")`
ile yüklendi ve hemen 2024-01-01 öncesine kesildi. Bar getirisi backtest ile
aynıdır (açılıştan sonraki açılışa). İncelenen hücre sayısı muhafazakâr
Deflated Sharpe'a eklenmiştir.

| Betik | Hücre | Bulgu |
|---|---|---|
| `kesif1_saat.py` | 144 | 24 UTC saati × 3 coin × spot/vadeli. Saat ortalamaları en çok ~5 bp/saat (t ≤ 3,0). İşaret yıllara göre kararsız. En kararlı olanlar: 22 UTC (BTC spot 6/7, ETH spot 7/7 yıl pozitif) ve 02 UTC (BTC/ETH spot 1/7 yıl pozitif). |
| `kesif2_gun_ay.py` | 168 | Haftanın günü: t < 2,3; Perşembe BTC/ETH spotta negatif (−23 / −32 bp, t ≈ −1). Ay dönümü [−3, +3]: pencere günleri BTC spot 46 bp/gün (diğerleri 10), ETH spot 76 (diğerleri 7). Fark t ≈ 2,0 / 3,0. Yılların 6/7'sinde pencere > diğer günler. Hafta sonu: daha düşük oynaklık, getiri farkı yok. |
| `kesif3_fonlama_ny.py` | 126 | Yüksek pozitif fonlamadan (> %0,03) sonraki ilk saat: ETH +17 bp (t 3,5), BTC +6 bp, SOL +15 bp. New York 17–19 (hafta içi): ~13 bp/gün. ABD seansı ve açılış saati: ≈ 0. |
| `kesif4_ay_donumu.py` | 222 | Ay dönümü yüzeyi (a, b = 0..6) geniş bir plato. Etki iki alt dönemde de var (2017–2020 ve 2021–2023). Ay ortası (10–15. günler) ≈ 0. Ayın son cuması çapası daha net değil. |
| **Toplam** | **660** | |

Not: Keşifte fonlama koşulu (k=0) fonlama anının kendi oranını kullandı. Bu
oran barın kapanışında henüz kaydedilmemiştir. Stratejide yalnız bir önceki
(bilinen) oran kullanıldı.

`tani1.py` plasebo testi: aynı 6 günlük pencere ayın X. gününe göre kaydırıldı
(pencere içi − dışı, 3 coin ortalaması, brüt). X=1 (ay dönümü) 28 konum içinde
spotta da vadelide de 1. oldu (spot 70 bp, ortanca −7 bp). Konumlar örtüştüğü için
bağımsız karşılaştırma sayısı yaklaşık 5'tir.

## 3. Arama (yalnız dev_train, harness)

Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))`
ile değerlendirildi. Aynı yapılandırma iki kez değerlendirilmedi (`ortak.degerlendir`).
Yıllık tanılar (`yillik`, `train_backtest`) yalnız deftere yazılmış yapılandırmalar
için hesaplandı. Veri hesaplamadan önce 2024-01-01 öncesine kesildi.

| Aşama | Betik | Yeni yapılandırma | İçerik |
|---|---|---|---|
| 1 | `tarama1.py` | 41 | Bütün yöntemler. Ay dönümü (a, b) ∈ {(1,3), (2,2), (3,3), (4,4), (5,5)} ve uzun_kısa. Hafta günü {Cmt+Paz, hafta içi, Perşembesiz, Pzt+Çar}. Saatler {UTC 21–22, NY 17–18 hafta içi, keşif pozitif saatleri, 21–22 alım + 2–3 açığa satış}. Fonlama eşiği {0,0003, 0,0005}, pencere {0–60, 0–120, 0–30 dk (15m), −60–0 açığa satış}. Uyarlamalı saat L ∈ {90, 365}, eşik {5, 10} bp. Uyarlamalı ay L ∈ {genişleyen, 24 ay}, eşik {20, 50} bp. |
| 2 | `tarama2.py` | 74 | Ay dönümü yüzeyi a, b = 1..6 (spot ve vadeli PORT3). Tek taraflı pencereler (0,3), (3,0), (0,4), (4,0). PORT2 (3,3), (4,4), (3,4), (4,3). |
| 3 | `tarama3.py` | 4 | Zamanlama duyarlılığı: 4h barlar, pencere ±4 / ±8 saat kaydırılmış (3,3). |
| 4 | `tarama4.py` | 3 | Kademeli topluluk (a, b ∈ 2..5) spot ve vadeli. Seçilen pencerenin (4,5) vadeli PORT2 sürümü. |
| Son | `dogrulama.py` | (4) | Dondurulan 4 yapılandırmanın tek seferlik dev_train + dev_valid değerlendirmesi. |

**Toplam 122 farklı yapılandırma.** Deney defteri
`arastirma/deneyler/mevsimsellik.jsonl` şunları içerir: 126 dev_train 1× satırı,
126 dev_train 2× satırı (4'ü dondurulanların son değerlendirmesi), 4 dev_valid 1×
ve 4 dev_valid 2× satırı. Bütün arama satırları `tarama_sonuclari.jsonl`
dosyasında da var.

### 3.1 Yöntem bazında dev_train özeti (122 yapılandırma)

Sharpe: günlük net getiriden yıllık. "Poz. 1×/2×": net getirisi pozitif olan
yapılandırma oranı. Maliyet: dönem boyunca ödenen toplam komisyon + kayma
(sermayenin katı).

| Yöntem | Aralık | Piyasa | Evren | Sayı | Medyan Sharpe | En iyi | En kötü | Poz. 1× | Poz. 2× | Medyan işlem | Medyan maliyet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ay_donumu | 1d | vadeli | PORT3 | 40 | 1,66 | 2,02 | 1,19 | 1,00 | 1,00 | 138 | 0,06 |
| ay_donumu | 1d | spot | PORT3 | 36 | 1,34 | 1,60 | 1,09 | 1,00 | 1,00 | 195 | 0,15 |
| ay_donumu | 1d | vadeli | PORT2 | 5 | 1,60 | 1,71 | 1,55 | 1,00 | 1,00 | 98 | 0,07 |
| ay_donumu | 1d | spot | PORT2 | 4 | 1,27 | 1,38 | 1,14 | 1,00 | 1,00 | 154 | 0,18 |
| ay_donumu (±4/8 sa kayma) | 4h | vadeli | PORT3 | 4 | 1,88 | 2,01 | 1,81 | 1,00 | 1,00 | 138 | 0,06 |
| ay_donumu_kademeli | 1d | vadeli / spot | PORT3 | 1 / 1 | 1,93 / 1,54 | | | 1 / 1 | 1 / 1 | 138 / 195 | 0,06 / 0,15 |
| ay_donumu uzun_kısa | 1d | vadeli | PORT3 | 1 | 0,18 | | | 0 | 0 | 274 | 0,13 |
| hafta_gunu | 1d | vadeli | PORT3 | 4 | 0,81 | 1,25 | 0,44 | 1,00 | 0,75 | 591 | 0,28 |
| hafta_gunu | 1d | spot | PORT3 | 4 | 0,64 | 1,17 | 0,18 | 0,75 | 0,75 | 844 | 0,67 |
| saat | 1h | vadeli | PORT3 | 4 | −1,44 | −0,41 | −5,00 | 0 | 0 | 6181 | 2,88 |
| saat | 1h | spot | PORT3 | 3 | −2,44 | −1,49 | −7,77 | 0 | 0 | 5890 | 4,71 |
| fonlama | 1h / 15m | vadeli | PORT3 | 5 | 0,15 (1h) | 0,49 | −0,75 | 0,40 | 0 | 1598 | 0,75 |
| uyarlamali_saat | 1h | vadeli / spot | PORT3 | 4 / 1 | −5,28 / −4,59 | −3,28 | −6,78 | 0 | 0 | 23474 / 8577 | 10,95 / 6,86 |
| uyarlamali_ay | 1d | spot | PORT3 | 4 | 0,21 | 0,52 | −0,14 | 0,50 | 0 | 1041 | 0,83 |
| uyarlamali_ay | 1d | vadeli | PORT3 | 1 | 0,61 | | | 1 | 1 | 650 | 0,30 |

### 3.2 Ana varyantların dev_train sonuçları (1× maliyet; parantezde 2×)

| Yapılandırma | Net getiri | Sharpe | En büyük düşüş | İşlem |
|---|---|---|---|---|
| `saat_1h_fut_PORT3_utc21_22` (21–22 UTC alım) | −0,690 (−0,955) | −1,21 (−3,37) | −0,73 | 4121 |
| `saat_1h_fut_PORT3_ny17_18_hi` (NY 17–19, hafta içi) | −0,299 (−0,823) | −0,41 (−2,33) | −0,54 | 2944 |
| `saat_1h_fut_PORT3_kesif_poz_neg` (keşifte seçilmiş 12 saat alım + 4 saat açığa satış) | −1,000 (−1,000) | −5,00 (−12,53) | −1,00 | 41205 |
| `fon_1h_fut_PORT3_e0.0005_b0_t60` | +0,175 (−0,255) | 0,49 (−0,76) | −0,11 | 978 |
| `fon_1h_fut_PORT3_e0.0003_b0_t60` | −0,049 (−0,549) | −0,05 (−1,63) | −0,17 | 1598 |
| `usaat_1h_fut_PORT3_L365_e10` | −0,972 (−1,000) | −3,28 (−7,40) | −0,97 | 9758 |
| `uay_1d_fut_PORT3_L0_e20` (ileriye yürüyen ay içi gün seçimi) | +0,862 (+0,375) | 0,61 (0,39) | −0,64 | 650 |
| `dow_1d_fut_PORT3_hs` (yalnız hafta sonu) | +1,208 (+0,678) | 0,76 (0,55) | −0,36 | 590 |
| `dow_1d_spot_PORT3_persiz` (Perşembe hariç her gün) | +31,229 (+15,420) | 1,17 (1,00) | −0,84 | 844 |
| `dow_1d_spot_PORT3_pzt_car` | −0,102 (−0,766) | 0,18 (−0,31) | −0,77 | 1681 |
| `tom_1d_fut_PORT3_a3_b3_uzunkisa` | −0,487 (−0,548) | 0,18 (0,14) | −0,76 | 274 |
| `tom_1d_spot_PORT3_a3_b3` | +12,460 (+10,533) | 1,60 (1,52) | −0,28 | 195 |
| `tom_1d_fut_PORT3_a3_b3` | +8,062 (+7,505) | 1,91 (1,86) | −0,27 | 138 |
| `tom_1d_fut_PORT3_a3_b0` (yalnız ay sonu 3 gün) | +2,012 (+1,829) | 1,47 (1,40) | −0,14 | 136 |
| `tom_1d_fut_PORT3_a0_b3` (yalnız ay başı 3 gün) | +1,829 (+1,657) | 1,19 (1,13) | −0,25 | 135 |

Okuma notları:

- Gün içi takvim etkileri maliyeti karşılayamaz. Seçilen saatlerde her gün
  girip çıkmak vadelide yılda ~%51, spotta ~%88 maliyet demektir. Keşifte
  seçilmiş 16 saatlik al-sat düzeni dev_train'de sermayenin 19 katı maliyet ödedi.
  Fonlama penceresi brüt olarak maliyetin hemen üstündedir; 2× maliyette hep zarar eder.
- "Perşembesiz" yalnız bir günü dışarıda bırakan al-tuttur (al-tut spot PORT3:
  30,89, Sharpe 1,12, düşüş −0,86). Ayrı bir takvim etkisi göstermez.
- İleriye yürüyen ay içi gün seçimi (`uyarlamali_ay`) zayıftır. Geçmiş aylara
  bakarak "iyi günleri" seçmek dev_train içinde bile güvenilir değildi. Bu,
  sonradan seçilmiş takvim hücrelerine karşı bir uyarıdır.
- Ay dönümü yıllık (1× maliyet, dev_train): spot PORT3 (3,3) 2017 +0,13,
  2018 +0,04, 2019 +0,26, 2020 +0,28, 2021 +4,29, 2022 −0,07, 2023 +0,44.
  Vadeli (4,5) 2020 +0,44, 2021 +3,92, 2022 +0,26, 2023 +0,52. Bileşik toplamın
  büyük kısmı 2021'den gelir (SOL pencere içinde ×13). 2021 dışarıda bırakılınca
  da pozitiftir.
- ±4/±8 saat kaydırma Sharpe'ı 1,81–2,01 arasında tuttu. Etki UTC gün sınırına
  duyarlı görünmüyordu.

## 4. Dondurma kararı (dev_valid görülmeden önce)

Gerekçe [`NOTLAR.md`](NOTLAR.md) dosyasına dev_valid'den önce yazıldı.

- Maliyetten sonra kârlı ve kararlı tek etki ay dönümüydü. Diğer yöntemlerden
  hiçbiri dondurulmadı.
- Pencere seçim kuralı (`secim.py`, kuralın çıktısı görülmeden yazıldı): a, b ∈
  {2..5} iç noktaları arasında, 3×3 komşuluğun dev_train 1× Sharpe ortalaması
  (spot ve vadeli PORT3 ortalaması) en yüksek olan seçilir. Sonuç **(a, b) = (4, 5)**
  oldu (komşuluk ortalaması 1,632). İlk 7 nokta 1,597–1,632 aralığındaydı (düz
  plato). Bu yüzden tek pencereye bağlı kalmayan kademeli topluluk da donduruldu.
- Tek coinde dev_valid'de en çok ~18 işlem olur (20 şartı). Bu yüzden yalnız
  portföyler donduruldu.

| # | Ad | Piyasa | Evren | Kural |
|---|---|---|---|---|
| 1 | `tom_1d_fut_PORT3_a4_b5` | vadeli, yalnız alım | BTC/ETH/SOL | Son 4 gün + ilk 5 gün |
| 2 | `tom_1d_spot_PORT3_a4_b5` | spot | BTC/ETH/SOL | Son 4 gün + ilk 5 gün |
| 3 | `tom_1d_fut_PORT2_a4_b5` | vadeli, yalnız alım | BTC+ETH | Son 4 gün + ilk 5 gün (SOL'un 2021 etkisi dışarıda) |
| 4 | `tomk_1d_fut_PORT3_a2-5_b2-5` | vadeli, yalnız alım | BTC/ETH/SOL | Kademeli: a, b = 2..5 ortalaması |

Dördü de aynı etkiye dayanır ve günlük getirileri yüksek korelasyonludur. Hepsi
`assert_causal` denetiminden geçti.

## 5. Sonuçlar: dev_train ve dev_valid (tek seferlik `evaluate(spec)`)

dev_train: spot 17.08.2017 – 31.12.2023; vadeli 08.09.2019 – 31.12.2023 (pozisyon
2020-01-01'den itibaren). dev_valid: 01.01.2024 – 30.06.2025 (547 gün). Sonuçlar
`dondurulmus_sonuclar.json` dosyasındadır.

| Yapılandırma | dev_train 1× getiri / Sharpe / düşüş | dev_train 2× getiri / Sharpe | dev_valid 1× getiri | dev_valid 2× getiri | dev_valid Sharpe 1× / 2× | dev_valid düşüş | dev_valid işlem | dev_valid p (bootstrap) |
|---|---|---|---|---|---|---|---|---|
| `tom_1d_fut_PORT3_a4_b5` | 12,528 / 1,86 / −0,267 | 11,693 / 1,82 | **−0,442** | −0,456 | −0,98 / −1,03 | −0,576 | 54 | 0,887 |
| `tom_1d_spot_PORT3_a4_b5` | 15,224 / 1,41 / −0,371 | 12,897 / 1,34 | **−0,422** | −0,446 | −0,91 / −0,99 | −0,568 | 54 | 0,862 |
| `tom_1d_fut_PORT2_a4_b5` | 8,789 / 1,71 / −0,253 | 8,146 / 1,66 | **−0,405** | −0,420 | −1,01 / −1,06 | −0,533 | 36 | 0,887 |
| `tomk_1d_fut_PORT3_a2-5_b2-5` | 8,137 / 1,93 / −0,211 | 7,575 / 1,88 | **−0,362** | −0,378 | −0,94 / −1,00 | −0,501 | 54 | 0,890 |

dev_valid ek bilgiler (1×): piyasada kalma oranı 0,30 / 0,30 / 0,30 / 0,33.
Toplam maliyet 0,025 / 0,043 / 0,025 / 0,025. Ödenen fonlama 0,051 / 0 / 0,052 / 0,041.
İşlem kazanma oranı 0,39 / 0,37 / 0,36 / 0,35.

### 5.1 candidate_check

| Yapılandırma | Eğitim net > 0 | Doğrulama net > 0 | 2× net > 0 | Sharpe ≥ 0,5 | İşlem ≥ 20 | **Aday** |
|---|---|---|---|---|---|---|
| `tom_1d_fut_PORT3_a4_b5` | evet | hayır | hayır | hayır | evet (54) | **hayır** |
| `tom_1d_spot_PORT3_a4_b5` | evet | hayır | hayır | hayır | evet (54) | **hayır** |
| `tom_1d_fut_PORT2_a4_b5` | evet | hayır | hayır | hayır | evet (36) | **hayır** |
| `tomk_1d_fut_PORT3_a2-5_b2-5` | evet | hayır | hayır | hayır | evet (54) | **hayır** |

### 5.2 Deflated Sharpe (`dsr.py`)

Yöntem: deneme sayısı N = defterde `pencere=="dev_train"` ve `maliyet_kat==1.0`
olan satırlar = **126** (122 farklı yapılandırma + dondurulan 4'ün son
değerlendirmesi). Varyans: bu satırların yıllık Sharpe varyansı = **2,993**
(std 1,73). Çarpıklık/basıklık: dev_valid günlük getirileri (summarize). Gün
sayısı 547.

| Yapılandırma | dev_valid Sharpe | Çarpıklık | Basıklık | DSR (N=126) | Muhafazakâr DSR (N=126+660 keşif hücresi) |
|---|---|---|---|---|---|
| `tom_1d_fut_PORT3_a4_b5` | −0,98 | −0,25 | 26,1 | 0,0000 | 0,0000 |
| `tom_1d_spot_PORT3_a4_b5` | −0,91 | −0,23 | 26,1 | 0,0000 | 0,0000 |
| `tom_1d_fut_PORT2_a4_b5` | −1,01 | −0,66 | 19,5 | 0,0000 | 0,0000 |
| `tomk_1d_fut_PORT3_a2-5_b2-5` | −0,94 | 1,11 | 39,5 | 0,0000 | 0,0000 |

Bilgi için (`tani_valid.py`): dev_train Sharpe'ları için DSR iki şekilde hesaplandı.

- Ailenin bütün denemeleriyle: dört yapılandırmada da 0,0000. Maliyetle eriyen
  gün içi denemelerin Sharpe değerleri −17 ile −3 arasındadır. Bunlar varyansı
  şişirir ve beklenen en büyük Sharpe yıllık ~4,5 olur.
- Yalnız ay dönümü denemelerinin varyansıyla (N=96, std 0,28): 0,994 / 0,965 /
  0,986 / 0,998.

Yani aile içi çoklu deneme düzeltmesiyle bile dev_train'de "anlamlı" görünen
etki, yeni veride tutmadı.

## 6. Al-tut karşılaştırması (aynı pencereler, 1d, 1× maliyet; `al_tut.py`)

| Piyasa | Evren | dev_train getiri / Sharpe / düşüş | dev_valid getiri / Sharpe / düşüş |
|---|---|---|---|
| spot | PORT3 | 30,892 / 1,12 / −0,855 | **0,737** / 0,90 / −0,491 |
| spot | PORT2 | 10,193 / 0,89 / −0,879 | 0,718 / 0,91 / −0,480 |
| vadeli | PORT3 | 16,673 / 1,26 / −0,853 | **0,504** / 0,74 / −0,498 |
| vadeli | PORT2 | 4,878 / 0,94 / −0,772 | 0,482 / 0,74 / −0,489 |
| spot | BTC / ETH / SOL | 8,86 / 6,55 / 29,81 | 1,534 / 0,089 / 0,522 |

Vadeli al-tut, ilk fonlama kaydından önce pozisyon 0 olacak şekilde hesaplandı
(stratejilerle aynı başlangıç). dev_train'de ay dönümü stratejileri PORT3'te
al-tuttan az getiri verdi (vadeli 12,53'e karşı 16,67; spot 15,22'ye karşı 30,89).
BTC+ETH vadelide ise al-tuttan fazla getiri verdi (8,79'a karşı 4,88). Her
durumda Sharpe daha yüksek, düşüş çok daha küçüktü. dev_valid'de al-tut
pozitifken (+%48 ile +%74) ay dönümü stratejileri −%36 ile −%44 kaybetti. Düşüşleri
de al-tut düzeyine çıktı (−%50 ile −%58). Bunu, sermayenin yalnız ~%30'unu
piyasada tutarak yaptılar.

## 7. dev_valid'de ne oldu (dondurma sonrası betimsel tanı; hiçbir şey değiştirilmedi)

`tani_valid.py`: (4,5) penceresi içi ve dışı ortalama günlük brüt getiri (spot, bp).

| Coin | dev_train içi / dışı | dev_valid içi / dışı |
|---|---|---|
| BTC | 36,5 / 9,4 | −8,6 / 32,8 |
| ETH | 59,3 / 4,6 | −37,3 / 27,5 |
| SOL | 94,2 / 37,3 | −31,5 / 38,7 |

dev_valid'deki 19 ay dönümü penceresinin yalnız 8'i pozitifti (PORT3 brüt,
medyan −%2,4). İlk pencere (1–5 Ocak 2024) ve son pencere (27–30 Haziran 2025)
kısmidir. En kötü pencereler şunlardı: Temmuz/Ağustos 2024 dönümü (−%25,1),
Mayıs/Haziran 2025 dönümü (−%11,5), Ocak/Şubat 2025 dönümü (−%11,4) ve Mart/Nisan
2025 dönümü (−%9,1). En iyisi Şubat/Mart 2024 dönümüydü (+%19,5). Etki zayıflamakla
kalmadı, işaret değiştirdi. Kayıplar birkaç sert ay dönümünde yoğunlaştı. ~18
gözlemle bu şans olabilir; ama aynı mantıkla dev_train'deki etki de birkaç büyük
ayın şansı olabilir.

## 8. Sonuç

1. **Bu aileden aday çıkmadı.** Protokole göre hiçbir yapılandırma finalist
   adaylığına önerilmez.
2. Gün içi mevsimsellik (saat, seans, fonlama anı) kripto majörlerde birkaç baz
   puanlık bir etkidir. Standart Binance maliyetleriyle (VIP 0, piyasa emri) tek
   başına işlenemez. Bu sonuç dev_train'de zaten açıktı; dev_valid'e taşınmadı.
3. Ay dönümü etkisi dev_train'de yüzeyin her noktasında, 2× maliyette, alt
   dönemlerde ve plasebo testinde güçlüydü. Yine de dev_valid'de tersine döndü.
   Olası açıklamalar: (a) dev_train etkisi büyük ölçüde 2017–2021 boğa
   piyasalarının birkaç ay dönümüne denk gelen sıçramalarından oluşan bir rastlantıydı
   (keşifte bile en iyi 3 ay dönümü çıkınca pencere ortalaması %24–35 düşüyordu). (b) Bilinen bir
   anomali olarak arbitrajla ortadan kalktı. (c) Yalnız 18 ay dönümü içeren
   doğrulama dönemi şanssızdı. Eldeki veriyle bunlar ayırt edilemez. Hiçbiri,
   etkiye para bağlamak için yeterli güven vermez.
4. dev_valid'e bakıldıktan sonra hiçbir kural veya parametre değiştirilmedi. Etkiyi
   "kurtarmak" için yeni pencere, filtre veya coin seçimi denenmedi; denenseydi
   dev_valid'de seçim olurdu.

## 9. Dosyalar

| Dosya | İçerik |
|---|---|
| `NOTLAR.md` | dev_valid'den önce yazılan çalışma notları ve dondurma kararı |
| `ortak.py` | dev_train'e kesilmiş veri, tek seferlik `degerlendir`, yıllık tanı yardımcıları |
| `kesif1_saat.py`, `kesif2_gun_ay.py`, `kesif3_fonlama_ny.py`, `kesif4_ay_donumu.py` | Betimsel keşif (yalnız dev_train), `kesif1_saat.csv` |
| `smoke.py` | Sinyal zamanlaması ve `assert_causal` duman testi (performans hesaplamaz) |
| `tarama1.py` … `tarama4.py`, `*.log`, `tarama_sonuclari.jsonl` | Harness taraması (yalnız dev_train) |
| `tani1.py` | Al-tut (dev_train), yıllık kararlılık, plasebo |
| `secim.py`, `secim.log` | Pencere seçim kuralı |
| `dogrulama.py`, `dogrulama.log`, `dondurulmus_sonuclar.json` | Tek seferlik dev_train + dev_valid değerlendirmesi ve candidate_check |
| `al_tut.py`, `al_tut_dev_train_dev_valid.csv` | Al-tut karşılaştırması |
| `dsr.py`, `dsr.json` | Deflated Sharpe |
| `tani_valid.py`, `tani_valid.log` | Dondurma sonrası betimsel dev_valid tanısı |
| `yeniden_uretim.py` | `specs()`'in raporlanan dev_train sayılarını ürettiğinin kontrolü (deftere yazmaz) |
