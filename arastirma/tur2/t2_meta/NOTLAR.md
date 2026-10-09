# t2_meta — çalışma notları

Tur 2, protokol sürüm 2 (`GRAFIK_ANALIZ_PROTOKOL=2`). Bu dosya planı ve
dondurma kararını **iç doğrulama (dev_valid) değerlendirmesinden önce** kayda
geçirir. Sonradan eklenen bölümler tarihleriyle ayrıca işaretlenir.

## 0. Okunanlar ve uyarılar (9 Ekim 2026, arama başlamadan önce)

- Okundu: `docs/PROTOKOL_2.md`, `docs/PROTOKOL.md`, `arastirma/SONUC_1.md`,
  `arastirma/DENETIM_1.md`, `grafik_analiz/research/*.py`, tur 1'in
  `kirilim.py`, `makine_ogrenmesi.py`, `formasyon.py` modülleri (yalnız kod).
- `SONUC_1.md` ve `DENETIM_1.md`, tur 1'in iç doğrulama (2024-01 – 2025-06) ve
  görülmemiş dönem (2025-07 – 2026-09) sonuçlarını içeriyor. Bu dönemlerin
  2025 ve sonrası kısmı sürüm 2'de iç doğrulamanın içinde. Bu bilgi bir fikir,
  coin, yön ya da parametre tercihine sebep olmamalı. Önlem: seçim kuralı
  aşağıda, arama sonuçları görülmeden önce yazıldı ve yalnız eğitim
  (dev_train) ölçülerine bakıyor. Diğer tur 2 ailelerinin raporları
  okunmadı.
- Dil modeli olarak 2025 sonrası piyasa seyrine dair genel bilgi taşıyor
  olabilirim; bu bilgi kullanılmayacak. Yön tercihi yapılmayacak: birincil
  sinyaller simetrik (uzun ve kısa) tanımlanır; yalnız alım varyantı ancak
  eğitim sonuçları gerekçe olursa dondurulur.

## 1. Fikir: meta-etiketleme

López de Prado'nun meta-etiketleme düzeni:

1. **Birincil sinyal** kuralla üretilir ve işlemin yönünü verir (olay).
2. Her olayın **kendi işlemi** sabit, ileriye doğru izlenen bir çıkış
   kuralıyla tanımlanır (üçlü bariyer: ATR katı kâr al, ATR katı zarar kes,
   en fazla H bar; ya da ATR iz süren stop + en fazla H bar). Kararlar bar
   kapanışında, işlem sonraki açılışta (harness ile aynı).
3. **Etiket** = o işlemin gerçekleşen net getirisi (gidiş-dönüş maliyeti
   0,14 % ve işlem süresindeki fonlama dahil) > 0. Etiket ancak işlem
   kapandıktan sonra (çıkış barından sonraki barın açılışında) bilinir.
4. **İkincil model** (sklearn HistGradientBoosting sınıflandırıcı ya da
   lojistik regresyon) ileriye yürüyerek eğitilir: her ay başında (ya da
   her `yeniden` ayda bir), etiketi o andan **önce** bilinen olaylarla
   (arındırma), üç coin havuzlanarak. O ayın olayları için "bu işlem
   kazandırır mı" olasılığı tahmin edilir.
5. **Karar**: olasılık eşiği geçerse işlem alınır (boyut 1 ya da olasılığa
   göre). Eşik kuralları: eğitim kümesinin taban oranı + δ, mutlak eşik, ya
   da beklenen değer (p × ort. kazanç − (1−p) × ort. kayıp > 0; ortalamalar
   eğitim etiketlerinden).

Birincil olaylar (BTC/ETH/SOL vadeli, 1h ve 4h):

- `kanal`: Donchian kırılımı (kapanış önceki n barın en yükseğini ilk kez
  geçer → uzun; en düşüğünün altına ilk kez iner → kısa).
- `donus`: büyük hareket sonrası dönüş (k barlık getirinin oynaklığa göre
  z-skoru eşiği ilk kez aşınca ters yönde).
- `fonlama`: fonlama oranı aşırılığı (son fonlamanın kayan z-skoru eşiği ilk
  kez aşınca karşıt yönde).
- `ema`: EMA kesişimi (trend; kesişim yönünde).
- Gerekirse birden çok birincil olayın havuzlanması (model "birincil türü"
  özelliğiyle).

Özellikler (olay barında, yalnız o bara kadarki veriyle):

- Oynaklık rejimi: kısa/uzun oynaklık oranı, oynaklığın kayan yüzdelik
  sırası, ATR/fiyat, bar aralığı / ATR.
- Trend: 1, 4, 24, 96 bar getirisinin oynaklığa göre z-skoru, EMA 20/50/200
  uzaklığı (ATR), Donchian konumu — **olay yönüyle çarpılmış** (yön-göreli).
- Hacim: log hacmin kayan ortalamaya farkı, işlem sayısı, taker alım payı
  (yön-göreli).
- Fonlama: son kayıt, son 3 ortalaması, 90 kayıtlık z-skoru (yalnız zaman
  damgası ≤ bar açılışı olan kayıtlar; tur 1 ML ile aynı ihtiyat).
- Konumlanma (metrics): OI'nın 1/6/24 bar log değişimi, OI'nın 30 günlük
  z-skoru, genel uzun/kısa oranı (log) ve değişimi, büyük hesap oranları.
  Zaman damgası ≤ bar kapanışı − 10 dk olan son kayıt; 2 saatten eski kayıt
  yok sayılır. Metrics `signal_fn` içinde `scope="dev"` ile yüklenip verilen
  son barın kapanışına kadar açıkça kesilir. OI = 0 kayıtları NaN.
- Prim endeksi: aynı açılış zamanlı prim mumunun kapanışı ve 7 günlük
  z-skoru (son barın kapanışına kadar açıkça kesilir).
- Zaman: barın kapanış saati (sin/cos), haftanın günü.
- BTC bağlamı: BTC'nin 24 bar getirisi z-skoru (yön-göreli).
- Olaya özgü güç (ör. kırılımın ATR cinsinden büyüklüğü), yön (+1/−1).

HGB eksik değerleri doğal işler (ETH/SOL metrics 2021-12'de başlıyor);
lojistikte eğitim kümesinin medyanıyla doldurma (yalnız eğitim satırlarına
uydurulur).

Pozisyon: coin başına sıralı; kabul edilen olay, olayın kendi çıkışına kadar
yön × boyut pozisyon açar; yeni kabul edilen olay eskisinin yerini alır.
Bacak başına 1/3 sermaye, bacak pozisyonu −1…1 (kaldıraç yok). İlk model
eğitilmeden önce pozisyon yok. Karşılaştırma için aynı takvimle "bütün
olayları al" (`model="hepsi"`) yapılandırması da ölçülür.

## 2. Arama disiplini

- Arama yalnız `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0,))`
  ile (gerektiğinde 2,0 da). dev_valid'e bakılmaz.
- Defter dışı tanı: yalnız 2025-01-01 öncesine kesilmiş veriyle olay sayısı,
  etiket taban oranı ve ileriye yürüyen AUC gibi betimleyici ölçüler; her
  biri betik + çıktı dosyasıyla klasörde tutulur ve raporda açıklanır.
- Sinyal hesaplaması harness gereği bütün dev dönemi üzerinde yapılır; ama
  dev_valid'e ait hiçbir ölçü, sinyal ya da olay istatistiği yazdırılmaz.

## 3. Dondurma kuralı (arama sonuçlarından önce yazıldı)

En fazla 5 yapılandırma. Seçim yalnız dev_train (1×) ölçüleriyle:

1. Uygunluk: dev_train net getiri > 0, alfa > 0, 2× maliyette net > 0,
   en az 60 işlem (dev_valid'de 20 işlem şartı için yeterli sıklık), ve aynı
   birincil sinyalin "hepsi" yapılandırmasına göre Sharpe artışı (meta
   modelin katkısı; yoksa meta-etiketleme iddiası yok).
2. Sıralama: dev_train alfa t-değeri; eşitlikte Sharpe.
3. Çeşitlilik: aynı birincil sinyal + aralık ikilisinden en fazla 2
   yapılandırma; komşu parametrelerde de iyi olan (tek bir dar tepe değil)
   tercih edilir.
4. Uygun yapılandırma yoksa: en iyi dev_train alfa t'li en fazla 2
   yapılandırma "negatif sonuç kontrolü" olarak yine bir kez ölçülür ve
   raporda öyle yazılır.

## 4. Günlük

### 9 Ekim 2026 — kod ve ilk kontrol

- `grafik_analiz/strategies/t2_meta.py` yazıldı. `assert_causal` (kesimler
  0,55 / 0,8 / 0,97 / 0,6123 / 0,9) üç örnek yapılandırmada geçti (4h kanal
  hgb, 4h kanal+donus+fonlama logit, 1h kanal iz hgb).
- HGB, eğitimde tamamen boş olan sütunlarda (ör. ETH/SOL konumlanma verisi
  2021-12 öncesi) hata verdi; her eğitimde en az iki farklı değeri olmayan
  sütunlar o eğitimden çıkarılıyor.
- Tanı ölçüleri (`ortak.tani_egitim`): olasılıklar nedensel olduğundan aynı
  önbellekteki tahminlerden yalnız **etiketi 2025-01-01'den önce bilinen**
  olaylarla hesaplanıyor (olay sayısı, taban oranı, AUC, kabul/red edilen
  olayların ortalama net getirisi). dev_valid olaylarına bakılmıyor.

### Tarama 1 (44 yapılandırma, `model="hepsi"`, birincil temel çizgileri)

- 4h Donchian kırılımı tek başına en iyisi: n=48 iz +%58 (alfa t 1,52),
  n=120 +%24…+%37. 1h Donchian bütün n'lerde zararda (−%38…−%82; taban oranı
  ~0,36–0,39, çok yanlış kırılım).
- 1h/4h büyük hareket dönüşü (`donus`) ve fonlama aşırılığı (`fonlama`)
  temel çizgileri çoğunlukla zararda; EMA kesişimi seyrek (4h'de < 400 olay).
- Seyrek birincillerde `min_olay=300` yüzünden model hiç başlamadı; tarama 2'de
  bunlar için `min_olay=150`.

### Tarama 2 (62 yapılandırma, hgb / logit, tam özellik, kural taban δ=0)

- Meta model kırılım olaylarında belirgin katkı yaptı (eğitim dönemi):
  - 4h kanal n=20 iz: hepsi −%33 → logit +%434 (Sharpe 1,02, alfa t 2,12),
    hgb +%243.
  - 4h kanal n=20 bariyer: hepsi −%52 → logit +%243 (Sharpe 1,04, t 2,02).
  - 4h kanal n=48 iz: hepsi +%58 → logit +%157 (t 1,53); hgb +%53.
  - 4h kanal n=120 bariyer (min_olay 150): hepsi +%51 → hgb +%124 (t 2,13).
  - 1h kanal n=48: hepsi −%80 → logit +%95…+%102 (t 1,1–1,2).
- AUC'ler zayıf (0,50–0,57) ama kabul edilen olayların ortalama net getirisi
  reddedilenlerden belirgin yüksek. Logit genelde HGB'den iyi.
- Dönüş ve fonlama birincillerinde meta model zararı küçülttü ama alfa t
  çoğunlukla negatif kaldı (en iyi: 1h fonlama hgb +%66, t 0,88).
- Karar: tarama 3, 4h kanal + logit etrafında tek boyutlu incelemeler
  (kanal uzunluğu, özellik kümesi, C, karar kuralı, çıkış, takvim, örnek
  ağırlığı, yalnız uzun) ve birkaç 1h kanal varyantı.

### Tarama 3 (60 yapılandırma, 4h kanal + logit etrafında)

- Etki geniş bir komşulukta: 4h kanal n ∈ {14, 20, 30, 48}, iz ve bariyer
  çıkışları, C ∈ {0,03 … 1}, δ ∈ {0, 0,03, 0,06}, yeniden eğitim 1/3 ay,
  genişleyen ya da 730 günlük pencere, min_olay 150/300/500 — hepsinde logit
  meta model eğitim döneminde alfa t ≈ 1,4–2,6 verdi; aynı birincilin "hepsi"
  çizgileri −%66…+%73.
- Özellik kümesi: konumlanma + prim dahil `tam` > `temel` > yalnız fiyat
  (`fiyat`) (n=20 iz: t 2,12 / 1,05 / 0,95).
- Yalnız uzun varyant alfasını kaybediyor (t 0,59; beta 0,13). Örnek ağırlığı
  (|net|) ve HGB varyantları logit'ten zayıf.
- En iyi tekil: 4h kanal n=20, bariyer tp 3 / sl 1,5 / H 60, logit tam:
  +%416, Sharpe 1,31, alfa t 2,61.

### Tarama 4–6 (topluluklar, 1h, eksik ölçüler)

- 4h topluluk (n=14,20,30,48 × bariyer H60) logit: +%288, Sharpe 1,30, alfa t
  2,51; 2×'te +%222. Yıl kırılımı (yalnız eğitim, `tani_yillik_1.txt`): 2021
  +%24, 2022 +%40, 2023 +%65, 2024 +%31; aynı topluluğun "hepsi" çizgisi 2021'de
  −%41.
- 1h kanal n=96 iz 4 / H 240 logit: +%278, Sharpe 0,93, alfa t 2,16 (2×: +%204).
- Havuzlanmış 4h kanal+donus+fonlama tek model: alfa negatif (beta 0,23) —
  elendi.
- Eksik ölçüler (tarama 6): 4h n=20 bariyer H60 2× +%321; 1h n=96 iz3 H120 2×
  +%124; 4h topluluk n=14..48 bariyer H60 "hepsi" çizgisi −%16 (Sharpe 0,13).
- Toplam: 186 benzersiz dev_train 1× yapılandırma (defterde 186 satır 1×,
  21 satır 2×).

## 5. Dondurma kararı (dev_valid değerlendirmesinden ÖNCE yazıldı)

Kural (bölüm 3) mekanik olarak uygulandı (`secim_tablosu.py`):
uygunluk = eğitimde net > 0, alfa > 0, 2× net > 0, ≥ 60 işlem, Sharpe aynı
birincilin "hepsi" çizgisinden yüksek; sıralama = eğitim alfa t; aynı
birincil + aralıktan en fazla 2.

| # | Yapılandırma | Eğitim net 1× / 2× | Sharpe | Alfa (yıllık) | Beta | Alfa t | DD | İşlem | "hepsi" Sharpe |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `t2_meta_4h_kanal_n20_b3.0-1.5-H60_logit_tam_taban0.0` | +%416,4 / +%320,7 | 1,315 | 0,324 | 0,037 | 2,605 | −%24,5 | 439 | −0,009 |
| 2 | `t2_meta_4h_kanal_top[n14-20-30-48]_n48_b3.0-1.5-H60_logit_tam_taban0.0` | +%288,2 / +%222,3 | 1,301 | 0,255 | 0,036 | 2,515 | −%24,2 | 585 | 0,13 |
| 3 | `t2_meta_1h_kanal_n96_iz4.0-H240_logit_tam_taban0.0` | +%278,3 / +%204,2 | 0,931 | 0,336 | −0,011 | 2,156 | −%32,9 | 467 | 0,258 |
| 4 | `t2_meta_1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0` | +%190,2 / +%123,7 | 0,832 | 0,268 | −0,007 | 1,916 | −%29,1 | 558 | −0,306 |
| 5 | `t2_meta_4h_ema_e20-100_b3.0-1.5-H60_logit_tam_taban0.0_min_olay150` | +%27,2 / +%20,0 | 0,458 | 0,077 | −0,019 | 1,445 | −%15,6 | 125 | 0,161 |

- 4h kanal grubunda üçüncü sıradaki (karışık çıkışlı topluluk, t 2,41) ve
  1h kanal grubunda üçüncü sıradaki (n=96 δ 0,05, t 1,87) grup sınırı
  nedeniyle alınmadı. 5. sıra, sınırlı gruplardan sonra alfa t'si en yüksek
  uygun yapılandırma (4h EMA kesişimi, t 1,45); zayıf ama kural gereği alındı.
- Hepsi vadeli BTC/ETH/SOL, bacak başına 1/3, iki yön, logit (C 0,1), tam
  özellik kümesi, aylık ileriye yürüyen eğitim, kural taban δ 0, boyut 1.
- Bu beş yapılandırma `assert_causal`'dan geçtikten sonra `evaluate(spec)` ile
  **bir kez** dev_valid'de ölçülecek; sonrasında parametre değişmeyecek.
- Nedensellik (`nedensellik.py`, `nedensellik.log`, dev_valid öncesi): beş
  yapılandırmanın hepsi `assert_causal` (9 kesim) ve 10 hedefli kesimden
  (ay başı yeniden eğitimden 1 bar sonra 4 kesim + 6 rastgele pozisyon
  değişim barı) geçti.

## 6. dev_valid sonrası (9 Ekim 2026, 18:01 UTC'de tek seferlik değerlendirme)

Bu bölüm dev_valid sonucundan **sonra** yazıldı. Hiçbir parametre, kural ya
da yapılandırma değiştirilmedi; yeni yapılandırma ölçülmedi. Yalnız
`grafik_analiz/strategies/t2_meta.py` içindeki `FROZEN_CHECK` açıklama
metinleri (candidate_check sonucu) eklendi; sinyali etkilemez.

- `dogrulama.py` → `dogrulama.log`, `dogrulama_sonuc.json`. Eğitim sayıları
  aramadakiyle birebir aynı çıktı. `yeniden_uretim.py`: son modülden
  `evaluate(record=False)` ile en büyük fark 0,0.
- candidate_check: yalnız `t2_meta_1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0`
  geçti (dev_valid 1× %+25,72, 2× %+8,53, Sharpe 0,592, alfa +0,172, alfa t
  0,78, 315 işlem; DSR 0,08). Diğer dördü Sharpe < 0,5 nedeniyle geçmedi;
  eğitimde en güçlü iki 4h yapılandırma dev_valid'de %−1,4 ve %+3,1.
- Betimleyici tanı (`dogrulama_tani.py` → `dogrulama_tani.log`): kanal
  yapılandırmalarında meta modelin sıralama gücü dev_valid'de sürdü (AUC
  0,55–0,57; kabul edilen olayların ortalama net getirisi reddedilenlerden
  yüksek), ama kabul edilen olayların ortalaması eğitimdeki +%0,6…+%1,1'den
  +%0,1…+%0,4'e indi. Geçen yapılandırmanın kazancı 2025'te (+%36,3);
  2026'nın ilk 9 ayında %−7,8.
