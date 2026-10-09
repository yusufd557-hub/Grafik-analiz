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
