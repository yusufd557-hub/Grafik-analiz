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

## Kesinti ve devam (2) (9 Ekim 2026, 16:30 UTC)

Çalışma ikinci kez kesildi (son kayıt 11:54 UTC; oturum yaklaşık 16:27
UTC'de yeniden başladı). Baştan başlanmadı; devralınan durum:

- Aşama 1 taramaları tamamdı: `tarama1` (spot_vadeli 5m/15m, 81
  yapılandırma), `tarama2` (prim 1h, spot_vadeli 1h, baz 15m/1h, 25),
  `tarama3` (yetis/lider 5m/15m, limitli yetis dahil, 38). Defterde 144 satır,
  hepsi `dev_train`, maliyet katı 1,0. Günlükler ve csv'ler tam (yarım
  kalmış tarama yok).
- `inceleme.py` ile eğitim içi yıllık inceleme yapılmıştı (`inceleme1.txt`,
  `inceleme1b.txt`).
- dev_valid'e hiç bakılmadı; dondurma kararı yoktu.

Aşama 1'den çıkan tablo (yalnız dev_train, 1×):

- `yetis` ve `lider` (coinler arası öncü–izleyen): bütün 38 yapılandırma
  zararda (net −%34 … −%100), alfa negatif; limit emir maliyeti azaltıyor ama
  kenar yok. Tanılamadaki birkaç bps'lik kenar maliyetin altında.
- `prim` (1h): 12 yapılandırmanın hepsi zararda.
- `spot_vadeli`: tek coin kaynaklı ("kendi") 5m/15m sinyaller çoğunlukla
  zararda. Üç coinin ortalaması ("hepsi") 5m k=3 e=5: net +%99 … +%162,
  Sharpe ≈ 1,1, alfa t ≈ 2,8–3,0, ama yalnız 249 işlem (≈ 83 olay × 3 coin),
  kazancın büyük kısmı 2021 ve uzun işlemlerden; en iyi 10 işlem çıkınca
  +%34. BTC kaynaklı 5m k=3 e=5 de pozitif (+%36 … +%61) ama en iyi 5 işlem
  çıkınca negatif.
- `baz` 15m w=96 e=4 t=8: net +%139, Sharpe 0,91, alfa t 2,23 (949 işlem) —
  yalnız iki komşusu ölçülmüştü.
- `spot_vadeli` 1h kendi e=3 t=6: +%56, Sharpe 0,57.

### Aşama 2 planı (bu oturum, dev_valid görülmeden önce)

1. `baz` taraması: 5m/15m/1h, kaynak ∈ {kendi, hepsi}, pencere, eşik, tutma.
2. `spot_vadeli` "hepsi" komşuluğu: k ∈ {2, 3, 4, 6}, eşik ∈ {4, 4,5, 5, 6},
   tutma; pencere 288/576.
3. Yön kısıtı (`taraf="uzun"`): eğitimde kâr uzun işlemlerden geliyor; yalnız
   uzun varyantı ayrı yapılandırma olarak ölçülür (seçim yalnız dev_train).
4. Limit emir: giriş/çıkış/tüm, 0–5 bps, piyasa emrine dönüş 1–6 bar.
5. Umut veren bölgelerde 2× maliyet ve eğitim içi yıllık tutarlılık.
6. Dondurma ölçütleri yukarıdaki planla aynı.

### Aşama 2 sonuçları (yalnız dev_train)

- `tarama4` (baz, 87 yeni): 1h hariç neredeyse bütün yapılandırmalar
  pozitif; 5m/15m'de net +%35 … +%224, Sharpe 0,5–1,3, alfa t 1,0–3,2, beta
  ≈ 0. Kâr ağırlıkla uzun işlemlerden (vadeli spota göre iskontoluyken
  alış); 2021–2024'ün her yılı pozitif, 2020 ≈ 0.
- `tarama5` (spot_vadeli "hepsi" komşuluğu, 70 yeni): k ≥ 3 ve eşik ≥ 4
  bölgesinin tamamı pozitif (Sharpe 0,5–1,4); k = 2 ve düşük eşik zayıf.
- `tarama6` (limit ve yalnız-uzun, 35): limit emir neti az değiştiriyor,
  maliyeti 1/3'e indiriyor (tüm değişimlerde 2 bps, 2 bar sonra piyasa
  emri: `limt2b2`). Yalnız-uzun 5m baz ve sv k=4'te Sharpe'ı artırıyor.
- `tarama7` (BTC bazı → ETH/SOL, 4): pozitif ama coinin kendi bazından zayıf.
- `tarama8`/`tarama10` (2× maliyet, 17): hepsi pozitif.
- `tarama9` (yalnız-uzun komşuluğu + uzun/limit birleşimi, 22 yeni): 18
  komşunun hepsi pozitif (Sharpe 1,15–1,72).
- Eğitim içi yıllık inceleme: `inceleme2a/b/c.txt`. En iyi işlemler
  likidasyon dalgalarında (2021-05-19, 2021-09-07, 2022-05-12, 2022-11-08,
  2024-01-03); en iyi 10 işlem çıkınca bile seçilenlerin hepsi pozitif
  kalıyor (+%34 … +%68).

Defter: 361 dev_train 1× satırı + 17 dev_train 2× satırı; dev_valid satırı yok.

## Dondurma kararı (9 Ekim 2026, dev_valid değerlendirmesinden ÖNCE)

Beş yapılandırma donduruldu. Hepsi USDⓈ-M vadeli BTC/ETH/SOL, bacak başına
1/3 sermaye, limit emir (`limit_bps=2, limit_mod="tum", limit_bar=2`: her
pozisyon değişimi sinyal barının kapanışından 2 bps iyi fiyatla limit emirle
denenir, 2 bar dolmazsa piyasa emri). Seçim yalnız dev_train'e göre; tasarım
2 sinyal türü × (iki yön / yalnız uzun) + 15m'lik bir baz sürümü:

| # | Ad (`t2_lead_lag_` önekiyle) | Tür | dev_train 1× net / Sharpe / alfa / alfa t / işlem | 2× net / Sharpe |
|---|---|---|---|---|
| 1 | `baz_5m_kendi_w288_e6_t12_limt2b2` | baz, coinin kendi bazı, iki yön | +%98,4 / 1,29 / +0,155 / 3,12 / 606 | +%80,0 / 1,12 |
| 2 | `baz_15m_kendi_w192_e5_t8_limt2b2` | baz 15m, kendi, iki yön | +%183,1 / 1,17 / +0,250 / 2,92 / 446 | +%164,3 / 1,10 |
| 3 | `sv_5m_hepsi_k6_e4_t36_limt2b2` | spot öncülüğü, üç coin ortalaması, iki yön | +%193,2 / 1,29 / +0,260 / 3,30 / 198 | +%183,3 / 1,26 |
| 4 | `baz_5m_hepsi_w288_e5_t12_uzun_limt2b2` | baz, üç coin ortalaması, yalnız uzun | +%137,2 / 1,66 / +0,198 / 4,15 / 195 | +%129,7 / 1,62 |
| 5 | `sv_5m_hepsi_k4_e4_t12_uzun_limt2b2` | spot öncülüğü, üç coin, yalnız uzun | +%153,0 / 1,36 / +0,230 / 3,65 / 132 | +%147,6 / 1,34 |

Gerekçe:

- Bölgeler komşulukta dayanıklı (bütün komşular pozitif), 2021–2024'ün her
  yılında pozitif, 2× maliyette pozitif, alfa t > 2,9, beta ≈ 0.
- En yüksek tek sonuç yerine bölgenin ortasından seçildi (ör. baz 5m kendi
  e6/t12; e4–e6 ve t12–t48 arası hepsi pozitif).
- İki yönlü sürümler (1–3) aile tanımına uygun ana sınama; yalnız-uzun
  sürümler (4–5) eğitimde kârın uzun taraftan geldiği gözlemine dayanıyor ve
  bu seçim bir çoklu deneme olarak raporlanır.
- Hepsi aynı olaylardan (likidasyon dalgası, vadeli iskontosu) beslendiği
  için birbirleriyle yüksek korelasyonlu olmaları beklenir; bağımsız kanıt
  sayılmazlar.

Riskler (önceden yazılır): kâr az sayıda büyük olaya bağlı; dev_valid'de
böyle olay olmazsa sonuç sıfıra yakın ya da negatif çıkabilir. Yalnız-uzun
sürümler ani düşüşlerin devam ettiği durumda zarar eder.

Sonraki adım: `dogrulama.py` her yapılandırmayı bir kez `evaluate(spec)` ile
ölçer, `candidate_check` ve `assert_causal` uygular. Sonuçtan sonra parametre
değişmez.
