# t2_lead_lag — çalışma notları

Protokol sürüm 2 (`docs/PROTOKOL_2.md`). Aile anahtarı `t2_lead_lag`.
Defter: `arastirma/tur2/deneyler/t2_lead_lag.jsonl`. Modül:
`grafik_analiz/strategies/t2_lead_lag.py`.

## Plan (9 Ekim 2026, hiçbir strateji sonucu görülmeden önce yazıldı)

Soru: BTC'nin son 5–15 dakikalık hareketinden sonra ETH/SOL yetişiyor mu (ya da
tersi)? BTC spot ile vadeli arasında ve prim endeksinde öncü–izleyen ilişkisi
var mı? Bütün işlemler USDⓈ-M vadeli (iki yön), fonlama dahil.

Hizalama: bütün bacaklar aynı zaman diliminde (5m/15m), aynı açılış zamanlı
mumlar. Bir bacak t barında yalnız diğer coinlerin t barına kadar (t dahil,
aynı anda kapanan) mumlarını kullanır. Eksik bar varsa o barda sinyal yok.
Bilgi bacağı (örneğin yalnız işaret için kullanılan BTC) sıfır ağırlıklı bacak
olarak verilir ya da `research.data.load(scope="dev")` ile yüklenip geçirilen
verinin son barına kesilir.

Aşama 0 — tanılama (yalnız eğitim verisi, 31.12.2024'e kadar kesilmiş): ham
öncü–izleyen ilişkisinin büyüklüğü (bir sonraki barın açılıştan açılışa
getirisinin BTC'nin son 1–3 barlık getirisine ve izleyenin kendi getirisine
regresyonu, büyük BTC hareketlerinde koşullu ortalama, yıllara göre).
Amaç: kenarın bps cinsinden büyüklüğünü maliyetle (taker gidiş-dönüş 14 bps,
maker 4 bps) karşılaştırmak. Strateji değerlendirmesi değil; strateji
sonuçları yalnız `evaluate()` ile alınır.

Sinyal türleri (hepsi geriye dönük kayan pencerelerle):

1. `yetis` (catch-up): izleyen coin için artık hareket
   e = r_lider(k bar) · β − r_izleyen(k bar); β kayan OLS/oynaklık oranı.
   Lider, oynaklığa göre büyük bir hareket yaptıysa (|z| > eşik) ve izleyen
   geride kaldıysa izleyen lider yönünde alınır. Tutma: h bar ya da artık
   kapanınca.
2. `lider` (yön): izleyen, liderin son k barlık getirisinin z-skoru yönünde
   (izleyenin kendi hareketi dikkate alınmadan) tutulur.
3. `ters` yön: ETH/SOL hareketinin BTC'yi öncülemesi.
4. `spot_vadeli`: BTC (ve coinin kendi) spot getirisi − vadeli getirisi
   (aynı bar) z-skoru → vadeli yönü.
5. `prim`: prim endeksi (1h) z-skoru → vadeli yönü (prim yüksekse vadeli
   pahalı: kısa; ya da devam). 1h zaman diliminde.

Yürütme: piyasa emri ve limit emir (giriş ve/veya çıkış; sinyal barının
kapanışından `bps` uzakta; dolmazsa sonraki barlarda yeniden denenir,
çıkışta belirli bar sonra piyasa emrine dönüş isteğe bağlı).

Aşamalar (yalnız dev_train, `evaluate(spec, windows=("dev_train",),
cost_multipliers=(1.0,))`, gerektiğinde 2.0):

- Aşama 1 — kaba ızgara: sinyal türü × zaman dilimi × eşik × tutma, piyasa ve
  limit yürütme.
- Aşama 2 — umut veren bölgelerde komşu parametreler, limit uzaklığı, yıllara
  göre tutarlılık (eğitim içinde, veriyi 31.12.2024'te keserek).
- Aşama 3 — en fazla 5 yapılandırma dondurulur (gerekçe aşağıya, dev_valid
  değerlendirmesinden **önce** yazılır), her biri `evaluate(spec)` ile bir kez
  ölçülür, `candidate_check` ve `assert_causal` uygulanır.

Seçim ölçütleri (dev_train): net getiri > 0, alfa > 0, 2× maliyette net > 0,
yeterli işlem, eğitim içi yıllarda tutarlılık, komşu parametrelerde
dayanıklılık. Hiçbiri yoksa en iyi dürüst denemeler dondurulur ve sonuç
olumsuz raporlanır.
