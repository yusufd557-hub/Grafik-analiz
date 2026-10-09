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

## Kesinti ve devam (9 Ekim 2026, 11:45 UTC)

Önceki araştırmacının oturumu kullanım sınırı nedeniyle arama sırasında
(09:09 UTC civarı) kesildi; çalışma bu noktadan sürdürülüyor, baştan
başlanmadı. Devralınan durum:

- Aşama 0 tanılamaları tamamdı: `tanilama1.py/.txt` (ham öncü–izleyen
  regresyonu), `tanilama2.py/.txt` (kayan betalı artık ve ufuk tepkisi),
  `tanilama3.py/.txt` (spot–vadeli getiri farkı ve prim endeksi). Hepsi
  yalnız < 2025-01-01 verisiyle.
- `grafik_analiz/strategies/t2_lead_lag.py` yazılmıştı (türler: `yetis`,
  `spot_vadeli`, `baz`, `prim`; limit emir yardımcıları). `specs()` boş.
- `deneme_hiz.py` (4 yapılandırma, `record=False`, yalnız dev_train) yazılmıştı.
  Çıktısı kaydedilmemiş; çalıştırılıp çalıştırılmadığı bilinmiyor. Bu betik
  defter dışı olduğu için **bundan sonra çalıştırılmayacak**; bütün
  değerlendirmeler deftere yazılır (`record=True`). Olası bir defter dışı
  bakış raporda açıklanacak.
- Defter (`arastirma/tur2/deneyler/t2_lead_lag.jsonl`) yoktu: hiçbir
  yapılandırma `evaluate()` ile ölçülmemişti, dev_valid'e hiç bakılmamıştı.

### Aşama 0 özeti (eğitim verisi, maliyetsiz, bps; strateji sonucu değil)

- Coinler arası yetişme (BTC→ETH/SOL artığı): 5m'de |z|>3–4 olaylarında
  sonraki 1–3 barda +1…+5 bps, 15m'de +3…+8 bps; yıllara göre işaret
  değişiyor. Piyasa emri gidiş-dönüş maliyeti 14 bps → tek başına maliyeti
  karşılamıyor. Büyük BTC hareketinden sonra ETH/SOL'ün yönü (artık
  olmadan) 5m'de ortalama negatif (kısa vadeli ters dönüş), yetişme değil.
  Ters yön (ETH/SOL→BTC) ≈ 0.
- Spot–vadeli getiri farkı (spot vadeliden çok yükseldiyse vadeli uzun):
  15m'de |z|>4 olaylarında 3–12 bar sonra +18…+55 bps (BTC kaynağı → SOL
  vadeli en büyük; ETH kaynağı → SOL vadeli yıllara göre tutarlı). 5m'de
  |z|>4'te 12 barda +10…+20 bps. Maliyeti aşabilecek tek coinler arası
  sinyal grubu.
- Prim endeksi (1h) düzeyi yüksekse vadeli sonraki 1–8 saatte düşüyor:
  BTC −7…−15 bps, ETH −5…−11 bps, yılların çoğunda aynı işaret. Karşıt
  yön sinyali; kısa tarafta fonlama da alınır.

### Devam planı (değişiklikler, strateji sonucu görülmeden önce)

- Modül düzeltmeleri: (i) diğer serilerin getirisi önce işlem bacağının
  açılış zamanlarına eşlenip sonra farkı alınır (eksik barda iki barlık
  getiri karışmasın); (ii) spot mumları sıfır ağırlıklı bacak yerine
  `research.data.load(..., "spot", scope="dev")` ile yüklenir ve geçirilen
  vadeli verinin son bar zamanına kesilir (15m/1h'de spot verisi vadeliden
  önce başladığı için sıfır ağırlıklı bacak birleşik indeksi 2019'a/2017'ye
  uzatıp dev_train Sharpe'ını seyreltiyordu).
- Aşama 1 (kaba ızgara, dev_train 1×; seçilenler 2×):
  - A `spot_vadeli` 5m/15m: kaynak ∈ {kendi, BTC, hepsi}, k ∈ {1, 3},
    eşik ∈ {3, 4, 5}, tutma 5m {6, 12, 36} / 15m {2, 4, 12} bar; piyasa emri ve
    çıkışta limit emir.
  - B `prim` 1h: pencere ∈ {24, 168}, eşik ∈ {2, 3}, tutma ∈ {4, 8, 24};
    piyasa emri ve limit emir.
  - C `yetis` 5m/15m: az sayıda temsilci yapılandırma (lider eşiği, limit
    emir dahil) — olumsuz sonucu belgelemek için.
  - D `baz` 15m/1h: vadeli/spot log fiyat farkı düzeyi, birkaç yapılandırma.
- Her tarama `tarama_*.py` + `.csv` + `.log` olarak kaydedilir; defterde adı
  olan yapılandırma yeniden çalıştırılmaz (kesintiye dayanıklı).
