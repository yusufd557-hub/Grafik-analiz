# t2_meta — Meta-etiketleme ailesi, tur 2 raporu

Protokol sürüm 2 (`GRAFIK_ANALIZ_PROTOKOL=2`). Eğitim (dev_train): verinin başı –
31.12.2024. İç doğrulama (dev_valid): 01.01.2025 – 30.09.2026. Plan ve dondurma
kararı dev_valid'den önce `NOTLAR.md` dosyasına yazıldı (dondurma 17:57 UTC,
dev_valid değerlendirmesi 18:01 UTC). Kod: `grafik_analiz/strategies/t2_meta.py`.
Defter: `arastirma/tur2/deneyler/t2_meta.jsonl`.

## 1. Kısa sonuç

- 186 yapılandırma yalnız eğitim döneminde denendi; 5'i donduruldu ve
  dev_valid'de bir kez ölçüldü.
- **Bir yapılandırma `candidate_check`'i geçti:**
  `t2_meta_1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0`. dev_valid'de:
  - net getiri 1× %+25,72, 2× %+8,53;
  - Sharpe 0,592, en büyük düşüş %−35,35, 315 işlem;
  - alfa +0,172 (yıllık), beta 0,011, alfa t 0,78.

  Kanıt zayıf:
  - Deflated Sharpe 0,08.
  - Bootstrap p 0,231.
  - Kazancın tamamı 2025'te (+%36,3). 2026'nın ilk 9 ayı %−7,8.
  - Neredeyse aynı kardeşi (`iz4-H240`, korelasyon 0,85) dev_valid'de %−7,1.
- Eğitimde en güçlü iki yapılandırma (4h Donchian + meta model, eğitim
  Sharpe 1,30–1,31, alfa t 2,5–2,6) dev_valid'de %−1,4 ve %+3,1 getirdi
  (Sharpe 0,10 ve 0,19). Eğitimdeki etki büyük ölçüde örneklem dışına
  taşınmadı.
- Meta modelin olayları sıralama gücü dev_valid'de sürdü (AUC 0,55–0,57). Ama
  kabul edilen işlemlerin ortalama net getirisi maliyetlerden sonra sıfıra
  yaklaştı.

## 2. Yöntem

**Meta-etiketleme düzeni** (López de Prado):

1. **Birincil olay** kuralla üretilir ve işlemin yönünü verir. Denenen olaylar:
   - `kanal`: Donchian kırılımı. Kapanış önceki n barın en yükseğini ilk kez
     geçince uzun, en düşüğünün altına ilk kez inince kısa.
   - `donus`: büyük hareket sonrası dönüş. k barlık getirinin z-skoru
     eşiği aşınca ters yönde.
   - `fonlama`: fonlama z-skoru aşırı olunca karşıt yönde.
   - `ema`: EMA kesişimi.
2. **Olayın kendi işlemi** ileriye doğru izlenen sabit bir çıkışla tanımlanır.
   Kararlar kapanışta, işlem sonraki açılışta verilir. İki çıkış türü var:
   - Üçlü bariyer: tp × ATR kâr al, sl × ATR zarar kes, en fazla H bar.
   - ATR iz süren stop: en fazla H bar.
3. **Etiket**: o işlemin net getirisi > 0. Net getiri gidiş-dönüş %0,14
   maliyeti ve fonlamayı içerir. Etiket, çıkıştan sonraki barın açılışında
   bilinir.
4. **İkincil model** her ay başında yeniden eğitilir. Eğitimde yalnız
   etiketi o andan önce bilinen olaylar kullanılır (arındırma). Üç coinin
   olayları birlikte eğitilir. Modeller:
   - lojistik regresyon: medyan doldurma + ölçekleme; dönüştürücüler yalnız
     eğitim satırlarına uydurulur;
   - HistGradientBoosting;
   - `hepsi`: aynı takvimle bütün olaylar alınır (karşılaştırma için).
5. **Karar**: olasılık, eğitim kümesinin taban oranını (+δ) geçerse işlem
   alınır. Boyut 1'dir. Yeni kabul edilen olay eski işlemin yerini alır.
   - Vadeli BTC/ETH/SOL, bacak başına 1/3 sermaye.
   - Bacak pozisyonu −1…1 (kaldıraç yok).

**Özellikler** (olay barında; yöne bağlı olanlar olay yönüyle çarpılır):

- oynaklık rejimi;
- getiri z-skorları, EMA uzaklıkları, Donchian konumu;
- hacim, işlem sayısı, taker alım payı;
- kapanış saati ve gün;
- BTC'nin 24 bar getirisi;
- fonlama: zaman damgası ≤ bar açılışı olan kayıtlar;
- konumlanma (OI değişimi ve z-skoru, uzun/kısa oranları): zaman damgası ≤
  kapanış − 10 dk;
- prim endeksi;
- olay gücü ve yön.

Konumlanma ve prim verileri `signal_fn` içinde `scope="dev"` ile yüklenir. Bu
veriler verilen son barın kapanışına kadar açıkça kesilir.

**Nedensellik:** Dondurulan 5 yapılandırmanın hepsi şu testleri geçti
(`nedensellik.log`, dev_valid'den önce):

- `assert_causal`: varsayılan 3 kesim ve 6 ek kesim;
- 10 hedefli kesim: aylık yeniden eğitimden 1 bar sonra 4 kesim ve rastgele
  6 pozisyon değişim barı.

## 3. Arama (yalnız dev_train)

| Tarama | Yapılandırma | İçerik |
|---|---:|---|
| 1 | 44 | Birincil temel çizgileri (`hepsi`) |
| 2 | 62 | Meta model (hgb ve logit, tam özellik) |
| 3 | 60 | 4h kanal + logit etrafında tek boyutlu inceleme |
| 4 | 12 | Topluluklar ve 1h kanal |
| 5 | 7 | 1h uzun çıkış, havuzlanmış birincil, 4h EMA |
| 6 | 1 | Dondurma kuralı için eksik ölçüler (+3 satır 2×) |

Tarama 1'de 44 birincil temel çizgisi (`hepsi`) ölçüldü:

- kanal: 4h n ∈ {20, 48, 120}, 1h n ∈ {48, 120, 240};
- donus: k ∈ {4, 6, 24}, z ∈ {2,5 … 4};
- fonlama: fz ∈ {2, 3};
- EMA: (20,100), (50,200), (100,400).

Tarama 3, 4h kanal + logit etrafında şu boyutları tek tek değiştirdi:

- n ∈ {14, 20, 30, 48};
- özellik kümesi: tam, temel, fiyat;
- C ∈ {0,03, 0,1, 0,3, 1};
- δ ∈ {0, 0,03, 0,06}, ayrıca beklenen değer kuralı;
- iz k ∈ {2, 3, 4}, H ∈ {30, 60, 120};
- bariyer (tp, sl, H): (2, 1), (3, 1,5), (4, 2), H 30 ya da 60;
- yeniden eğitim 1 ya da 3 ayda bir;
- genişleyen pencere ya da 730 gün;
- min_olay ∈ {150, 300, 500};
- |net| örnek ağırlığı;
- düzenli HGB;
- yalnız uzun.

Tarama 4'te kanal uzunluğu ve çıkış toplulukları (4h) ile 1h n ∈ {96, 192}
denendi. Tarama 5'te 1h uzun çıkışlar (H 240), havuzlanmış 4h
kanal+donus+fonlama ve 4h EMA denendi.

Toplam **186 benzersiz yapılandırma**. Defterde aramadan 186 satır dev_train
1×, 21 satır 2× var. Dondurulan 5 yapılandırmanın `evaluate(spec)` tekrarı
5 satır daha ekledi.

İki dondurulmuş yapılandırma aramada `topluluk` / `agirlik` parametreleri
eklenmeden önce ölçülmüştü. Defterde bunlar varsayılan anahtar farkıyla ikinci
bir parametre kümesi gibi görünür; davranış aynıdır.

İsimlendirme hatası: `ortak.isim()`, `model="hepsi"` yapılandırmalarında
`min_olay` değerini isme eklemiyordu. Bu yüzden tarama 2'deki `min_olay=150`
`hepsi` çizgileri, tarama 1'deki `min_olay=300` olanlarla aynı adı taşıyor
(ör. `t2_meta_4h_kanal_n120_b3.0-1.5-H30_hepsi`). Defterdeki parametreler
farklıdır ve ayırt edicidir. Dondurulan yapılandırmalar bundan etkilenmedi.

Defter dışı tanı ölçüleri (olay sayısı, taban oranı, AUC, kabul ve red
edilen olayların ortalama net getirisi) yalnız etiketi 2025-01-01'den önce
bilinen olaylarla hesaplandı (`ortak.tani_egitim`, tarama logları).
Yıl/coin kırılımı da yalnız eğitim dönemiyle yapıldı (`tani_yillik_1.txt`).

### Ana eğitim (dev_train) sonuçları, 1× maliyet

| Yapılandırma | Net % | Sharpe | DD % | İşlem | Alfa | Beta | Alfa t |
|---|---:|---:|---:|---:|---:|---:|---:|
| `4h_kanal_n20_iz3.0-H60_hepsi` | −32,6 | 0,15 | −76,4 | 610 | +0,177 | −0,08 | +0,69 |
| `4h_kanal_n48_iz3.0-H60_hepsi` | +58,4 | 0,43 | −51,5 | 344 | +0,313 | −0,10 | +1,52 |
| `4h_kanal_n120_iz3.0-H60_hepsi` | +37,0 | 0,35 | −35,8 | 179 | +0,184 | −0,06 | +1,22 |
| `1h_kanal_n48_b3.0-1.5-H72_hepsi` | −80,4 | −0,60 | −81,6 | 2219 | −0,208 | −0,03 | −1,14 |
| `1h_donus_k4z3.0_b2.0-2.0-H24_hepsi` | −62,6 | −0,57 | −74,2 | 1144 | −0,162 | +0,00 | −1,29 |
| `4h_fonlama_fz2.0_b2.0-2.0-H12_hepsi` | −16,6 | −0,12 | −32,1 | 253 | −0,064 | +0,04 | −0,83 |
| `4h_kanal_n20_iz3.0-H60_logit_tam` | +433,8 | 1,02 | −30,3 | 314 | +0,385 | +0,03 | +2,12 |
| `4h_kanal_n20_iz3.0-H60_hgb_tam` | +242,9 | 0,81 | −34,3 | 352 | +0,324 | +0,00 | +1,77 |
| `4h_kanal_n20_iz3.0-H60_logit_fiyat` (konumlanma/prim yok) | +151,9 | 0,63 | −58,2 | 361 | +0,188 | +0,08 | +0,95 |
| `4h_kanal_n20_iz3.0-H60_logit_temel` | +363,8 | 0,98 | −47,5 | 331 | +0,172 | +0,18 | +1,05 |
| `4h_kanal_n20_iz3.0-H60_uzun_hepsi` | +213,3 | 0,79 | −56,8 | 285 | −0,004 | +0,26 | −0,03 |
| `4h_kanal_n20_iz3.0-H60_uzun_logit_tam` | +147,5 | 0,84 | −31,3 | 152 | +0,061 | +0,13 | +0,59 |
| `4h_kanal_n14_iz3.0-H60_logit_tam` | +621,6 | 1,13 | −32,5 | 395 | +0,422 | +0,05 | +2,22 |
| `4h_kanal_n48_iz3.0-H60_logit_tam` | +156,8 | 0,77 | −31,1 | 206 | +0,209 | +0,02 | +1,53 |
| `4h_kanal_n120_b3.0-1.5-H30_hgb_tam (min_olay 150)` | +123,7 | 1,06 | −18,3 | 188 | +0,157 | +0,02 | +2,13 |
| `4h_kanal_n20_b3.0-1.5-H60_hepsi` | −45,3 | −0,01 | −74,5 | 825 | +0,070 | −0,07 | +0,33 |
| **`4h_kanal_n20_b3.0-1.5-H60_logit_tam`** | +416,4 | 1,31 | −24,5 | 439 | +0,324 | +0,04 | +2,61 |
| `4h_kanal_top[n14-20-30-48]_b3.0-1.5-H60_hepsi` | −15,7 | 0,13 | −57,9 | 1018 | +0,141 | −0,08 | +0,75 |
| **`4h_kanal_top[n14-20-30-48]_b3.0-1.5-H60_logit_tam`** | +288,2 | 1,30 | −24,2 | 585 | +0,255 | +0,04 | +2,51 |
| `4h_kanal_top[n14..48 × iz/bariyer]_H60_hepsi` | +8,7 | 0,26 | −51,5 | 739 | +0,213 | −0,08 | +1,07 |
| `4h_kanal_top[n14..48 × iz/bariyer]_H60_logit_tam` | +327,8 | 1,21 | −25,5 | 477 | +0,288 | +0,03 | +2,41 |
| `1h_kanal_n48_iz3.0-H120_logit_tam` | +101,9 | 0,56 | −39,0 | 893 | +0,199 | +0,00 | +1,22 |
| `1h_kanal_n96_iz3.0-H120_hepsi` | −67,1 | −0,31 | −73,8 | 1041 | −0,110 | −0,02 | −0,57 |
| **`1h_kanal_n96_iz3.0-H120_logit_tam`** | +190,2 | 0,83 | −29,1 | 558 | +0,268 | −0,01 | +1,92 |
| `1h_kanal_n96_iz4.0-H240_hepsi` | +2,9 | 0,26 | −52,8 | 847 | +0,183 | −0,05 | +0,82 |
| **`1h_kanal_n96_iz4.0-H240_logit_tam`** | +278,3 | 0,93 | −32,9 | 467 | +0,336 | −0,01 | +2,16 |
| `1h_donus_k4z3.0_b2.0-2.0-H24_logit_tam (min_olay 150)` | +20,9 | 0,26 | −31,0 | 670 | +0,063 | +0,01 | +0,50 |
| `1h_fonlama_fz2.0_b0.0-3.0-H48_hgb_tam (min_olay 150)` | +66,2 | 0,67 | −18,6 | 223 | +0,067 | +0,04 | +0,88 |
| `4h_donus_k6z2.5_b2.0-2.0-H12_logit_tam (min_olay 150)` | −39,0 | −0,66 | −47,5 | 151 | −0,112 | +0,02 | −1,85 |
| `4h_kanal+donus+fonlama_b3.0-1.5-H60_logit_tam` (tek model) | +107,3 | 0,56 | −57,5 | 701 | −0,036 | +0,23 | −0,22 |
| `4h_ema_e20-100_b3.0-1.5-H60_hepsi` | +6,8 | 0,16 | −28,5 | 229 | +0,050 | −0,02 | +0,69 |
| **`4h_ema_e20-100_b3.0-1.5-H60_logit_tam (min_olay 150)`** | +27,2 | 0,46 | −15,6 | 125 | +0,077 | −0,02 | +1,45 |

Kalın satırlar dondurulan yapılandırmalardır. İsimlerdeki `t2_meta_` öneki ve
`_taban0.0` soneki kısaltıldı. Eğitim döneminin Sharpe değeri, modelin ilk
eğitiminden önceki pozisyonsuz günleri de içerir (çoğu yapılandırmada 2020'nin
bir kısmı).

Eğitimdeki gözlemler:

- Meta model **kırılım** olaylarında güçlü katkı gösterdi.
  - Aynı birincilin `hepsi` çizgisi −%80…+%58 arasındaydı.
  - Logit meta model geniş bir komşulukta alfa t 1,4–2,6 verdi: n, çıkış, C,
    δ, takvim ve pencere değişse de.
- Dönüş ve fonlama birincillerinde meta model zararı küçülttü, ama alfa
  çoğunlukla ≤ 0 kaldı.
- Konumlanma ve prim özellikleri eğitimde katkı yaptı: `tam` alfa t 2,12;
  `fiyat` 0,95.
- Yalnız uzun varyant alfasını kaybetti (beta 0,13–0,26). Bu yüzden
  dondurulanların hepsi iki yönlü.
- Yıl kırılımı yalnız eğitim döneminde yapıldı. 4h topluluk 2021–2024'ün her
  yılında pozitifti: +%24, +%40, +%65, +%31. Aynı topluluğun `hepsi` çizgisi
  2021'de −%41'di.

## 4. Dondurma

Kural `NOTLAR.md` bölüm 3'te arama sonuçlarından önce yazıldı ve
`secim_tablosu.py` ile mekanik olarak uygulandı.

**Uygunluk:** eğitimde

- net getiri > 0;
- alfa > 0;
- 2× maliyette net getiri > 0;
- en az 60 işlem;
- Sharpe, aynı birincilin `hepsi` çizgisinden yüksek.

**Sıralama:** eğitim alfa t. Aynı birincil + aralık ikilisinden en fazla 2
yapılandırma alınır.

| # | Yapılandırma | Neden |
|---|---|---|
| 1 | `t2_meta_4h_kanal_n20_b3.0-1.5-H60_logit_tam_taban0.0` | 4h kanal, alfa t en yüksek (2,61) |
| 2 | `t2_meta_4h_kanal_top[n14-20-30-48]_n48_b3.0-1.5-H60_logit_tam_taban0.0` | 4h kanal, 2. (2,51); dört kanal uzunluğunun ortalaması |
| 3 | `t2_meta_1h_kanal_n96_iz4.0-H240_logit_tam_taban0.0` | 1h kanal, 1. (2,16) |
| 4 | `t2_meta_1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0` | 1h kanal, 2. (1,92) |
| 5 | `t2_meta_4h_ema_e20-100_b3.0-1.5-H60_logit_tam_taban0.0_min_olay150` | Grup sınırından sonra uygun en yüksek alfa t (1,45); zayıf ama kural gereği |

Ortak ayarlar: logit (C 0,1), tam özellik kümesi, aylık ileriye yürüyen
eğitim, genişleyen pencere, kural taban δ 0, boyut 1, iki yön.

## 5. İç doğrulama (dev_valid) sonuçları — tek seferlik

dev_valid 638 gün.

| # | Net 1× | Net 2× | Sharpe 1× | Sharpe 2× | DD 1× | İşlem | Alfa | Beta | Alfa t | p | En iyi işlem çıkınca | candidate_check |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | %−1,38 | %−11,30 | 0,104 | −0,118 | %−29,53 | 227 | +0,0245 | 0,063 | 0,12 | 0,471 | %−9,49 | **geçmedi** (1×/2× net < 0, Sharpe < 0,5) |
| 2 | %+3,14 | %−6,34 | 0,192 | −0,040 | %−27,97 | 283 | +0,0429 | 0,042 | 0,24 | 0,428 | %−3,34 | **geçmedi** (2× net < 0, Sharpe < 0,5) |
| 3 | %−7,14 | %−17,01 | 0,027 | −0,170 | %−36,74 | 241 | +0,0073 | 0,023 | 0,03 | 0,515 | %−17,30 | **geçmedi** (1×/2× net < 0, Sharpe < 0,5) |
| 4 | %+25,72 | %+8,53 | 0,592 | 0,303 | %−35,35 | 315 | +0,1715 | 0,011 | 0,78 | 0,231 | %+15,50 | **GEÇTİ** (7/7 şart) |
| 5 | %+6,64 | %+2,50 | 0,346 | 0,173 | %−20,94 | 85 | +0,0465 | −0,020 | 0,47 | 0,320 | %+2,81 | **geçmedi** (Sharpe < 0,5) |

Eğitim sayıları dev_valid değerlendirmesinde aramadakiyle birebir aynı çıktı.
`yeniden_uretim.py`, son modülden `record=False` ile yeniden üretti; en büyük
fark 0,0.

**dev_valid günlük getiri korelasyonları:**

| Çift | Korelasyon |
|---|---:|
| 1–2 | 0,97 |
| 3–4 | 0,85 |
| 4h kanal ile 1h kanal | 0,66–0,73 |
| EMA ile diğerleri | 0,27–0,30 |

### Deflated Sharpe

- Deneme sayısı: defterde `pencere == "dev_train"` ve `maliyet_kat == 1,0`
  olan 191 satır. Bunun 186'sı arama, 5'i dondurulanların tekrarıdır.
- Bu satırların yıllık Sharpe varyansı: 0,338.
- Hesap dev_valid Sharpe, gün sayısı, çarpıklık ve basıklık ile yapıldı.

| # | DSR |
|---|---:|
| 1 | 0,024 |
| 2 | 0,031 |
| 3 | 0,019 |
| 4 | 0,084 |
| 5 | 0,048 |

Hiçbiri anlamlı değil (0,95'in çok altında).

### Al-tut kıyası (vadeli BTC/ETH/SOL eşit ağırlık; alfa kıyası)

| Dönem | Net | En büyük düşüş | Sharpe |
|---|---:|---:|---:|
| dev_train | %+3.953 | %−85,1 | 1,28 |
| dev_valid | %−18,93 | %−64,32 | 0,10 |

Dondurulanların betası iki dönemde de −0,02 ile 0,06 arasında. Getirileri
piyasa yönünden gelmiyor. Ama dev_valid'de alfaları da küçük: t 0,03–0,78.

## 6. dev_valid sonrası betimleyici tanı

Bu tanı hiçbir parametreyi değiştirmedi ve yeni yapılandırma ölçmedi
(`dogrulama_tani.py`, `dogrulama_tani.log`). Her yapılandırmanın kendi
olayları dönemlere ayrılarak incelendi.

| # | Dönem | Olay | AUC | Bütün olayların ort. net | Kabul edilenler | Reddedilenler |
|---|---|---:|---:|---:|---:|---:|
| 1 | eğitim | 1712 | 0,575 | %−0,10 | %+1,09 | %−1,08 |
| 1 | doğrulama | 782 | 0,567 | %−0,32 | %+0,10 | %−0,75 |
| 2 | eğitim | 6171 | 0,560 | %−0,00 | %+0,85 | %−0,69 |
| 2 | doğrulama | 2804 | 0,552 | %−0,27 | %+0,09 | %−0,63 |
| 3 | eğitim | 2657 | 0,548 | %−0,20 | %+0,67 | %−0,85 |
| 3 | doğrulama | 1117 | 0,549 | %−0,13 | %+0,33 | %−0,59 |
| 4 | eğitim | 2658 | 0,572 | %−0,33 | %+0,60 | %−0,98 |
| 4 | doğrulama | 1118 | 0,565 | %−0,09 | %+0,41 | %−0,76 |
| 5 | eğitim | 229 | 0,531 | %+0,18 | %+0,59 | %−0,33 |
| 5 | doğrulama | 145 | 0,508 | %+0,43 | %+0,27 | %+0,66 |

- Kırılım yapılandırmalarında meta modelin ayırma gücü örneklem dışında
  korundu:
  - AUC hemen hemen aynı kaldı.
  - Kabul edilenler hâlâ reddedilenlerden ve bütün olaylardan iyi.
  - Bu, ailenin asıl iddiasının (filtre işe yarar) zayıf biçimde
    doğrulanmasıdır.
- Ama kırılım olaylarının kendisi dev_valid'de daha kötüydü. Kabul edilen
  işlemlerin ortalaması işlem başına %0,1–0,4'e indi. Bu, Sharpe ≥ 0,5 için
  çoğu yapılandırmada yetmedi.
- EMA yapılandırmasında (5) meta model örneklem dışında ayıramadı. AUC 0,508;
  reddedilenler kabul edilenlerden iyi.
- Geçen yapılandırmanın (4) yıl kırılımı:
  - 2025: +%36,3, Sharpe 1,22. Coin bazında ETH +%77, SOL +%36, BTC −%4.
  - 2026 (ocak–eylül): %−7,8, Sharpe −0,22.
  - Uzun işlemlerin katkısı +0,107, kısa işlemlerin +0,199. Bunlar işlem
    net getirilerinin portföy payıyla toplamıdır.

## 7. Sonuç

- Meta-etiketleme, eğitim döneminde zayıf kırılım sinyallerini belirgin
  biçimde iyileştirdi:
  - aynı olaylarda `hepsi` −%45 → meta +%416;
  - alfa t 2,6;
  - beta ≈ 0.
- Bu iyileşme dev_valid'de büyük ölçüde kayboldu:
  - Eğitimin en iyi iki yapılandırması sıfır civarında kaldı.
  - Beşten yalnız biri aday şartlarını geçti, o da sınırda: Sharpe 0,59,
    2× maliyette %+8,5, alfa t 0,78, DSR 0,08.
  - Kazancı tek bir yıla (2025) ve ağırlıkla ETH'ye bağlı.
- Dürüst değerlendirme:
  - Bu aileden piyasa yönünden bağımsız, maliyet sonrası güvenilir bir alfa
    kaynağı **kanıtlanmadı**.
  - Geçen yapılandırma protokol gereği bir adaydır ve ileriye dönük takip
    seçimine girebilir.
  - Ancak çoklu deneme düzeltmesinden sonra anlamlı değil. Yakın kardeşinin
    (aynı birincil, farklı çıkış) dev_valid'de kaybettirmesi kırılgan
    olduğunu gösteriyor.

## 8. Sınırlamalar ve notlar

- `SONUC_1.md` ve `DENETIM_1.md` tur 1'in 2024–2026 sonuçlarını içeriyordu ve
  arama öncesinde okundu.
  - Bunlar fikir, coin, yön ya da parametre seçiminde kullanılmadı.
  - Bütün seçimler eğitim ölçülerine ve önceden yazılmış mekanik kurala
    dayanıyor.
  - Dil modeli olarak 2025 sonrası piyasaya dair genel bilgi taşıyor
    olabilirim. Bu yüzden birincil sinyaller simetrik tutuldu ve yalnız uzun
    varyant dondurulmadı.
- Harness, `evaluate(windows=("dev_train",))` çağrısında bile sinyalleri
  bütün dev dönemi için hesaplıyor. Arama sırasında dev_valid sinyalleri ya
  da ölçüleri yazdırılmadı.
- Konumlanma verisi ETH/SOL için 2021-12'de başlıyor (BTC 2020-09). Daha önce
  eksik değerler HGB'de doğal, logit'te eğitim medyanıyla dolduruluyor.
- Eğitim dönemi Sharpe'ı ilk model öncesindeki pozisyonsuz günleri de
  içeriyor. Bu, eğitim Sharpe'ını biraz düşürür; karşılaştırmalar aynı
  takvimle yapıldı.
- Etiket 1× maliyetle hesaplanıyor. 2× maliyet değerlendirmesinde model
  aynı.

## 9. Dosyalar

- **Kod:** `grafik_analiz/strategies/t2_meta.py`. `specs()` dondurulan 5
  yapılandırmayı döndürür.
- **Arama:**
  - `ortak.py`;
  - `tarama1.py` … `tarama6.py`, `.log` ve `.csv` çıktılarıyla;
  - `secim_tablosu.py`;
  - `tani_yillik.py` → `tani_yillik_1.txt`.
- **Dondurma ve doğrulama:**
  - `NOTLAR.md`;
  - `nedensellik.py` → `nedensellik.log`;
  - `dogrulama.py` → `dogrulama.log`, `dogrulama_sonuc.json`;
  - `yeniden_uretim.py` → `yeniden_uretim.log`;
  - `dogrulama_tani.py` → `dogrulama_tani.log`.
