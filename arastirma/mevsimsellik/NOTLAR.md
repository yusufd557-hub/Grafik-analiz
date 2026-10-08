# Mevsimsellik — çalışma notları (dev_valid görülmeden önce yazıldı)

Bu dosya dondurma kararını dev_valid sonuçlarından **önce** kayda geçirir.
Bütün sayılar yalnız dev_train (2024-01-01 öncesi) verisinden gelir.

## Keşif (betimsel, deftere yazılmaz; hücre sayısı muhafazakâr DSR'ye eklenir)

| Betik | İncelenen hücre | Bulgu |
|---|---|---|
| `kesif1_saat.py` | 144 | UTC saat etkileri en çok ~5 bp/saat (t ≤ 3), yıllara göre kararsız. 21–22 UTC pozitif, 02–03 UTC negatif. Vadeli gidiş-dönüş maliyeti 14 bp, spot 24 bp: günlük işlemle karşılanamaz. |
| `kesif2_gun_ay.py` | 168 | Haftanın günü zayıf (t < 2,3). Ay dönümü (son 3 + ilk 3 gün) BTC/ETH spotta diğer günlerden belirgin yüksek (t ≈ 2–3, yılların 6/7'sinde). |
| `kesif3_fonlama_ny.py` | 126 | Fonlama sonrası ilk saat, yüksek pozitif fonlamada ETH +17 bp (t 3,5) — maliyetin hemen üstü; NY 17–19 saatleri ~13 bp/gün (maliyetin altında). Not: keşifte k=0 koşulu fonlama anının kendi oranını kullandı; stratejide yalnız bir önceki (bilinen) oran kullanılır. |
| `kesif4_ay_donumu.py` | 222 | Ay dönümü yüzeyi geniş plato; iki alt dönemde de var (2017–2020, 2021–2023); ay ortası (10–15) ≈ 0. |
| Toplam | 660 | |

`tani1.py` plasebo: aynı 6 günlük pencere ayın X. gününe kaydırılınca X=1
(ay dönümü) 28 konum içinde 1. (spot ve vadeli). Konumlar örtüştüğü için bağımsız
karşılaştırma sayısı ~5'tir.

## Harness taraması (yalnız dev_train, 1× ve 2× maliyet)

- `tarama1.py` (41): bütün yöntemler. Saat, NY saati, uyarlamalı saat,
  fonlama penceresi maliyetle eridi; haftanın günü zayıf ya da al-tut kopyası
  (Perşembesiz: MDD −0,83); uyarlamalı ay içi gün seçimi zayıf (Sharpe 0,18–0,61).
  Ay dönümü PORT3: spot (3,3) Sharpe 1,60, vadeli (3,3) 1,91; 2× maliyette 1,52 / 1,86.
- `tarama2.py` (74 yeni): a, b = 1..6 yüzeyi (spot, vadeli PORT3): 72 yapılandırmanın
  hepsi 1× ve 2× maliyette pozitif, Sharpe 1,09–2,02. Tek taraflı pencereler (yalnız
  ay sonu / yalnız ay başı) de pozitif ama daha zayıf. PORT2 (BTC+ETH) 8 yapılandırma.
- `tarama3.py` (4): ±4/±8 saat kaydırma, Sharpe 1,81–2,01 — zamanlamaya duyarlı değil.
- `tarama4.py` (3): kademeli topluluk (a, b ∈ 2..5) ve seçilen pencerenin PORT2 sürümü.

Toplam 122 yapılandırma (defterde 122 dev_train 1× satırı, dondurma öncesi).

## Seçim kuralı (`secim.py`, sonucu görülmeden yazıldı)

a, b ∈ {2..5} iç noktaları arasında, 3×3 komşuluk dev_train 1× Sharpe ortalaması
(spot ve vadeli PORT3 ortalaması) en yüksek olan seçilir → **(a, b) = (4, 5)**.
İlk 7 nokta arasındaki fark 0,035'ten küçüktür (düz plato); bu yüzden tek
pencere seçimine bağlı kalmayan **kademeli topluluk** da dondurulur.

## Dondurulan yapılandırmalar (4)

1. `tom_1d_fut_PORT3_a4_b5` — kurala göre seçilen pencere, vadeli yalnız alım, BTC/ETH/SOL eşit.
2. `tom_1d_spot_PORT3_a4_b5` — aynı kural, spot.
3. `tom_1d_fut_PORT2_a4_b5` — aynı kural, vadeli, yalnız BTC+ETH (SOL'un 2021 etkisi dışarıda).
4. `tomk_1d_fut_PORT3_a2-5_b2-5` — kademeli topluluk, vadeli PORT3.

Hepsi aynı takvim etkisine dayanır; günlük getirileri yüksek korelasyonludur.
Bu dört yapılandırma dev_valid'de **bir kez** `evaluate(spec)` ile ölçülecek ve
sonuca bakılarak değiştirilmeyecek.

## Beklenti ve riskler (önceden)

- Ay dönümü etkisi hisse senedi piyasalarında bilinen bir anomalidir ve zamanla
  zayıflamıştır; kripto için dev_train'de güçlü görünmesi kısmen 2021 boğa
  piyasasından (özellikle SOL) gelir.
- dev_valid 18 ay = ~18 ay dönümü. Tek coinde 18 işlem 20'nin altındadır; bu
  yüzden yalnız portföyler donduruldu (PORT2: ~36, PORT3: ~54 işlem).
- 18 gözlemle Sharpe tahmininin standart hatası büyüktür (~0,8); dev_valid'de
  zayıf sonuç etkinin yok olduğunu, güçlü sonuç da kesin olduğunu kanıtlamaz.
