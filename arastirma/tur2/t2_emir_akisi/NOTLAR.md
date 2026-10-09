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
