# t2_cift — Çift / yayılım ortalamaya dönüşü (protokol sürüm 2)

Tarih: 9 Ekim 2026. Piyasa: Binance USDⓈ-M vadeli. Coinler: BTC, ETH, SOL.
Kod: `grafik_analiz/strategies/t2_cift.py`. Deney defteri: `arastirma/tur2/deneyler/t2_cift.jsonl`.
Çalışma notları ve dondurma kararı: `NOTLAR.md`. Dondurma kararı dev_valid'den önce yazıldı.

## 0. Kısa sonuç

- 636 benzersiz yapılandırma denendi. Arama yalnız eğitim döneminde (dev_train) yapıldı.
- Klasik çift ticareti eğitimde hiç kâr etmedi. Bu yöntem, yayılımın kayan ortalamaya
  dönmesini bekler (düzey z-skoru). 162 yapılandırmanın hepsi zarar etti, maliyet öncesi
  bile. Nedeni: BTC/ETH/SOL yayılımları 1 günden uzun ufuklarda trend yapıyor (varyans
  oranı > 1).
- Eğitimde tutarlı çıkan tek mekanizma, SOL içeren yayılımlardaki çok büyük kısa vadeli
  şokların birkaç saat içinde kısmen geri dönmesidir. Şok, 6–12 saatte 5σ'yı aşan
  harekettir. Limit emirle maliyet üçte birine iner.
- 3 yapılandırma donduruldu ve iç doğrulamada (dev_valid) bir kez ölçüldü:
  - **B ve C `candidate_check`'i geçti.**
  - **D geçmedi.** Sharpe 0,19 kaldı.
- Ama geçen iki adayın kanıtı zayıf:
  - Getiriler küçük: B %+7,50, C %+4,33. Strateji zamanın %1'inden azında pozisyonda.
  - En iyi tek işlem çıkarılınca iki adayın da iç doğrulama getirisi negatife dönüyor.
  - Alfa t-değerleri 1,20 ve 0,96, yani anlamlı değil.
  - Deflated Sharpe 0,001–0,002.
  - B ile C'nin günlük korelasyonu 0,91: fiilen tek strateji.
  - B'nin 28 işlemi, ileriye dönük takip seçimindeki 30 işlem eşiğinin altında.
- Fonlama farkının sonuca katkısı ihmal edilebilir:
  - Dondurulanlarda iç doğrulamada %0,1–0,2 fonlama alındı.
  - Yavaş klasik çiftlerde SOL çiftleri eğitimde %13–20 fonlama aldı, ama brüt zararı
    kapatmadı.

## 1. Kesinti ve devam

- Bu ailenin ilk araştırmacısı kullanıcı tarafından tarama 2 sırasında durduruldu (07:06 UTC).
  - O ana kadar defterde 189 yapılandırma vardı: tarama 1'in 162'si ve tarama 2'nin 27'si.
  - Satırların hepsi dev_train satırıydı.
- Çalışma 08:45 UTC'de kaldığı yerden sürdürüldü. Ayrıntı: `NOTLAR.md` → "Kesinti ve devam".
- `ortak.tara`, defterde aynı ad ve parametrelerle bulunan yapılandırmaları yeniden
  değerlendirmez; ölçülerini defterden alır. Böylece yinelenen deneme satırı oluşmadı.
- Eski satırlar silinmedi, değiştirilmedi ve deneme sayısına dahil edildi.

## 2. Denenen yaklaşımlar (yalnız dev_train, ≤ 31.12.2024)

Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))` ile
ölçüldü. Bütün bacaklar vadelidir ve fonlama bacak bacak hesaplandı. Çiftlerin tamamı piyasa
nötrdür (çift başına uzun A + kısa B).

| Tarama | Fikir | Parametre aralıkları | Yapılandırma (yeni) | Net > 0 | En iyi eğitim sonucu |
|---|---|---|---:|---:|---|
| 1 | Klasik düzey z-skoru: kayan ortalamadan sapınca gir, z = 0'da çık | 1h/4h; ETHBTC, SOLBTC, SOLETH; hedge `bir` (1:1), `oyn` (oynaklık oranı), `ols` (kayan düzey OLS); z penceresi 1h 48/168/500, 4h 30/90/180; z_in 1,5/2/2,5 | 162 | 0 | 4h SOLETH oyn: %−18,4, Sharpe −0,07 |
| 2 | Yayılım şoku sönümlenmesi: son k barlık hareket / önceki 500 bar oynaklığı·√k > z_in ise ters yönde gir, sabit süre tut | 1h: k 1/3/6, z_in 3/4, tutma 3/6/12; 4h: k 1/2, z_in 3/4, tutma 1/3; hedge bir/oyn; 3 çift; piyasa emri | 156 (27'si kesintiden önce) | 11 | 1h SOLBTC bir k6 z4 tutma 6: %+27,1, Sharpe 0,46 |
| 3 | Şok + limit emir + üçlü portföy | SOLBTC, SOLETH, üçlü; k 3/6; z_in 3/4; tutma 3/6; limit: yok, 5 bp/1 bar, 10 bp/2 bar (her değişimde), 5 bp/1 bar (yalnız girişte) | 80 | 39 | SOLBTC k6 z4 tutma 6, limit 10/2: %+40,3, Sharpe 0,61 |
| 4 | Şok inceltme (limit 10/2) + limit parametreleri | SOLBTC, SOLETH, SOLBTC+SOLETH; k 3/6/12; z_in 3,5/4/5; tutma 3/6/12; ayrıca limit bps 5/10/20 × bar 1/2/3 | 95 | 69 | SOLBTC k6 z5 tutma 6: %+60,6, Sharpe 1,08 |
| 5 | Trend yönünde geri çekilme: kısa pencereli düzey z, yalnız uzun pencereli yayılım trendi yönünde | 1h: z penceresi 24/48, uzun pencere 500/1500; 4h: 12/30, uzun pencere 180/500; z_in 2/2,5; eşik 0/1; 3 çift + üçlü; limit 10/2 | 128 | 13 | 4h SOLBTC z12 z_in 2,5 rejim 180: %+15,4, Sharpe 0,41 |
| 6 | Öncü şok yapılandırmalarının duyarlılığı | vol_win 250/1000, z_in 4,5, limit 20 bp | 15 | 18/19 | SOLBTC k6 z5 tutma 6 limit 20/2: %+65,5, Sharpe 1,10 |

Defterde toplam 636 benzersiz yapılandırma var; her biri 1× ve 2× olmak üzere 1272 dev_train
satırı. dev_valid değerlendirmesi dondurulan 3 yapılandırmanın dev_train satırlarını bir kez
daha yazdı. Bu yüzden defterde 639 dev_train 1× satırı var.

Betimleyici tanılamalar deftere yazılmadı. Hepsi yalnız eğitim verisiyle yapıldı:

- `tanilama.txt`: yayılım getirisi otokorelasyonu ve varyans oranları.
  - 1h'te VR(6) 0,94–0,96: çok kısa ufukta hafif dönüş var.
  - VR(500) 1,19–1,27; 4h'te VR(180) 1,34–1,48: uzun ufukta trend var.
- `tanilama2.txt`: 3–4σ'lık yayılım şokundan sonraki dönüş.
  - SOL çiftlerinde 1–6 saatte 10–80 bp dönüş var.
  - ETH/BTC'de 0–10 bp.
  - 24 saatte işaret tersine dönüyor; şok devam ediyor.
  - Piyasa emriyle çift gidiş-dönüş maliyeti yaklaşık 28 bp (yayılım biriminde).
- `tanilama3.txt` ve `tanilama4.txt`: şok yapılandırmalarının yıllık dökümü (bkz. bölüm 3).
- `tanilama5.txt`: açık pozisyon (OI) değişimi ile şok dönüşü arasındaki ilişki.
  - ETH/SOL ölçüleri 2021-12'de başlıyor.
  - İşaretler k ve ufka göre çelişkili çıktı (n 60–130), bu yüzden OI filtresi kurulmadı.
- `tanilama6.txt`: geniş evren (97 altcoin/BTC çifti, 4h, o ay evrende olanlar).
  - Şok sonrası medyan dönüş pozitif.
  - Ortalama ise yıldan yıla işaret değiştiriyor: kalın kuyruk var, büyük şokların bir kısmı
    devam ediyor.
  - 4h'te BTC/ETH/SOL şokları da negatifti. Bu yüzden geniş evren stratejisi kurulmadı.

### Ana varyantların eğitim sonuçları (1× maliyet, alfa/beta harness'ten)

| Varyant | Eğitim net | 2× | Sharpe | En büyük düşüş | İşlem | Alfa (yıllık) | Beta |
|---|---:|---:|---:|---:|---:|---:|---:|
| Klasik z, 4h SOLETH oyn z90 z_in 2,5 (tarama 1'in en iyisi) | %−18,4 | %−24,8 | −0,07 | %−44,7 | 142 | %−3,9 | 0,021 |
| Klasik z, 4h ETHBTC bir z180 z_in 2,5 | %−32,9 | %−36,9 | −0,38 | %−46,1 | 88 | %−6,5 | −0,000 |
| Şok, 1h ETHBTC bir k6 z4 tutma 3 (piyasa) | %−12,8 | %−26,0 | −0,52 | %−16,6 | 234 | %−1,1 | −0,014 |
| Şok, 1h SOLBTC bir k6 z4 tutma 6 (piyasa) | %+27,1 | %+11,4 | 0,46 | %−18,4 | 188 | %+7,6 | −0,018 |
| Aynısı, limit 10 bp/2 bar | %+40,3 | %+34,7 | 0,61 | %−17,7 | 188 | %+9,8 | −0,020 |
| Şok, 1h üçlü portföy k6 z4 tutma 3, limit 10/2 | %+14,3 | %+9,3 | 0,31 | %−14,4 | 539 | %+5,4 | −0,019 |
| Trend yönünde geri çekilme, 4h SOLBTC z12 z_in 2,5 | %+15,4 | %+13,5 | 0,41 | %−15,6 | 82 | %+3,3 | −0,002 |

Bütün çift yapılandırmalarının piyasa betası sıfıra yakın (−0,03…+0,08). Kâr ya da zarar
piyasanın yönünden gelmiyor. Klasik z-skorunda alfa eğitimin her varyantında negatif.

## 3. Neden bu üç yapılandırma donduruldu

Dondurma kararı `NOTLAR.md`'de, dev_valid'den önce yazıldı.

1. **Mekanizma:** SOL içeren yayılımlarda 6–12 saatlik çok büyük şoklar sonraki 3–6 saatte kısmen
   geri dönüyor. Bu, eğitimde art arda üç taramada (2, 3, 4) görüldü. ETH/BTC'de görülmedi.
2. **Limit emir:** Kapanışın 10–20 bp ötesine 2 bar limit emir verildi, dolmazsa piyasa emri.
   - Maliyet yaklaşık üçte birine indi.
   - 2× maliyette de getiri pozitif kaldı.
3. **Duyarlılık (tarama 6):** Önceden yazılan kural şuydu: bir komşuda Sharpe < 0 ise aday elenir.
   - A elendi (SOLBTC k6 z4 limit 20; vol_win 1000'de Sharpe −0,09).
   - B, C ve D'nin bütün komşuları ≥ 0 çıktı. vol_win 1000 hepsinde zayıf (0,11–0,55).
4. **Yıllık döküm (eğitim):**
   Yıllar 2020 / 2021 / 2022 / 2023 / 2024, kaynak `egitim_dokum.txt`:
   - B'nin kârı ağırlıkla 2021–2022'den: %+4,87 / +17,30 / +31,03 / −1,33 / +4,06.
   - C: %+3,03 / +11,85 / +18,68 / −3,80 / −0,43.
   - D her yıl pozitif: %+2,57 / +9,15 / +5,24 / +3,00 / +2,20.
5. Kalan iki hak kullanılmadı. Diğer fikirlerin eğitim kanıtı dondurmaya yetmedi:
   - trend yönünde geri çekilmede Sharpe ≤ 0,41 ve sağlam değil,
   - ETH/BTC hep negatif,
   - geniş evren tanılaması tutarsız.

Dondurulan yapılandırmaların ortak ayarları: 1h, `hedge="bir"`, `z_tur="sok"`, `vol_win=500`,
`z_exit=None`, `limit_bar=2`, `limit_mod="tum"`.

| Kod | Çiftler | k | z_in | Tutma (bar) | Limit (bps) | Bacaklar |
|---|---|---:|---:|---:|---:|---|
| B | SOL/BTC | 6 | 5,0 | 6 | 20 | BTC, SOL (½ + ½) |
| C | SOL/BTC + SOL/ETH | 6 | 5,0 | 6 | 20 | BTC, ETH, SOL (⅓ her biri) |
| D | SOL/BTC + SOL/ETH | 12 | 5,0 | 3 | 10 | BTC, ETH, SOL (⅓ her biri) |

Tam adlar `specs()` içinde; ad ve parametreler defterdeki arama satırlarıyla birebir aynı
(`dondurma_kontrol.log`). `assert_causal` üçünde de geçti. Kesimler varsayılan 0,55 / 0,8 /
0,97 ve ek olarak 0,3 / 0,5 / 0,65 / 0,75 / 0,9 / 0,99.

Not: harness'in "işlem" sayısı **bacak bazındadır**. Bir çift işlemi en az iki işlem sayılır;
örneğin B'deki 28 işlem 14 çift işlemidir.

## 4. İç doğrulama (dev_valid, 01.01.2025–30.09.2026) — tek bakış

Değerlendirme `dogrulama.py` ile 08:59 UTC'de bir kez çalıştırıldı. Ham sonuç
`dogrulama_sonuc.json`, çıktı `dogrulama.log`.

### Eğitim (aynı çalıştırma, 1×)

| Kod | Net | 2× | Sharpe | En büyük düşüş | İşlem | Alfa | Beta | Alfa t | Maruziyet |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B | %+65,50 | %+61,33 | 1,10 | %−12,26 | 108 | %+12,09 | −0,014 | 2,84 | %0,80 |
| C | %+31,00 | %+28,95 | 0,88 | %−8,80 | 163 | %+6,64 | −0,009 | 2,36 | %0,94 |
| D | %+24,01 | %+22,87 | 0,92 | %−4,35 | 102 | %+4,80 | −0,003 | 2,23 | %0,33 |

### İç doğrulama, 1× maliyet

| Kod | Net | Sharpe | En büyük düşüş | İşlem | Alfa | Beta | Alfa t | En iyi işlem | En iyi işlem çıkınca | Bootstrap p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B | %+7,50 | 0,91 | %−2,81 | 28 | %+4,24 | 0,001 | 1,20 | %+8,06 | %−0,52 | 0,081 |
| C | %+4,33 | 0,73 | %−3,26 | 55 | %+2,49 | −0,001 | 0,96 | %+5,37 | %−0,99 | 0,097 |
| D | %+0,56 | 0,19 | %−2,00 | 41 | %+0,36 | −0,004 | 0,27 | %+0,89 | %−0,32 | 0,385 |

### İç doğrulama, 2× maliyet

| Kod | Net | Sharpe | En büyük düşüş | Alfa | Alfa t |
|---|---:|---:|---:|---:|---:|
| B | %+6,77 | 0,83 | %−2,90 | %+3,85 | 1,10 |
| C | %+3,80 | 0,64 | %−3,30 | %+2,20 | 0,86 |
| D | %+0,25 | 0,09 | %−2,04 | %+0,18 | 0,14 |

### candidate_check

| Şart | B | C | D |
|---|---|---|---|
| Eğitimde net > 0 | ✓ | ✓ | ✓ |
| İç doğrulamada net > 0 | ✓ | ✓ | ✓ |
| İç doğrulamada 2× net > 0 | ✓ | ✓ | ✓ |
| İç doğrulamada Sharpe ≥ 0,5 | ✓ (0,91) | ✓ (0,73) | ✗ (0,19) |
| İç doğrulamada ≥ 20 işlem | ✓ (28) | ✓ (55) | ✓ (41) |
| Eğitimde alfa > 0 | ✓ | ✓ | ✓ |
| İç doğrulamada alfa > 0 | ✓ | ✓ | ✓ |
| **Aday** | **evet** | **evet** | hayır |

### İç doğrulama dökümü (betimleyici, sonradan)

| Kod | 2025 | 2026 (Ocak–Eylül) | Bacak işlemleri | Fonlama (alınan) | Maliyet |
|---|---:|---:|---|---:|---:|
| B | %+2,70 | %+4,67 | BTC 14, SOL 14 | %0,20 | %0,69 |
| C | %+2,57 | %+1,71 | BTC 14, ETH 18, SOL 23 | %0,12 | %0,50 |
| D | %+1,48 | %−0,91 | BTC 12, ETH 10, SOL 19 | %0,09 | %0,32 |

İç doğrulamada günlük getiri korelasyonu (`dogrulama_korelasyon.txt`): B–C 0,91, B–D 0,19,
C–D 0,37.

## 5. Deflated Sharpe

- **Deneme sayısı:** defterdeki `pencere == "dev_train"` ve `maliyet_kat == 1.0` satırları,
  yani **639**. Bunların 636'sı benzersiz; 3'ü dondurulanların dev_valid çalıştırmasındaki tekrarı.
- **Sharpe varyansı:** bu satırların yıllık Sharpe varyansı 0,6319 (std 0,795). Bu varyansla 639
  denemede şansla beklenen en yüksek yıllık Sharpe yaklaşık 2,49.
- **Çarpıklık ve basıklık:** dev_valid günlük getirilerinden; 638 gün.

| Kod | dev_valid Sharpe | Çarpıklık | Basıklık | DSR (639) | DSR (636) |
|---|---:|---:|---:|---:|---:|
| B | 0,91 | 14,17 | 274,7 | 0,0013 | 0,0013 |
| C | 0,73 | 11,37 | 262,7 | 0,0022 | 0,0022 |
| D | 0,19 | −3,65 | 150,2 | 0,0015 | 0,0015 |

Çoklu deneme düzeltmesinden sonra hiçbir sonuç anlamlı değildir.

## 6. Al-tut karşılaştırması

Kıyas, BTC/ETH/SOL eşit ağırlıklı vadeli al-tuttur (harness'in alfa kıyası, günlük).

| Dönem | Al-tut getirisi | Al-tut Sharpe | Al-tut en büyük düşüş | B | C | D |
|---|---:|---:|---:|---:|---:|---:|
| Eğitim (2020-01 – 2024-12) | %+3.953 | 1,28 | %−85,1 | %+65,50 | %+31,00 | %+24,01 |
| İç doğrulama | %−18,93 | 0,10 | %−64,3 | %+7,50 | %+4,33 | %+0,56 |

- Stratejiler piyasa nötrdür (beta ≈ 0) ve sermayenin çok küçük bir bölümünü çok kısa süre
  kullanır. Maruziyet %0,3–1.
- Bu yüzden mutlak getirileri al-tutla doğrudan kıyaslanamaz. Karşılaştırılabilir ölçü alfadır.
- Düşüşler çok küçüktür: %2–3 iç doğrulamada, %4–12 eğitimde.

## 7. Fonlama farkının payı

Fonlamanın payı stratejinin tutma süresine bağlı.

**Dondurulan şok stratejileri (tutma 3–6 saat):** fonlama etkisi ihmal edilebilir.

- Eğitimde alınan fonlama: B %0,25, C %0,18, D %0,28. Aynı dönemde net getiri %24–66.
- İç doğrulamada alınan fonlama: %0,09–0,20.
- B'nin iç doğrulama getirisinin yaklaşık %2,7'si fonlamadan geliyor.
- Kâr SOL bacağının brüt hareketinden geliyor:
  - B eğitimde SOL bacağı brüt +0,585, BTC bacağı −0,019.
  - BTC ve ETH bacakları hedge görevi görüyor, kâr üretmiyor.

**Yavaş klasik çiftler (tarama 1, günler–haftalar):** fonlama belirgin ama zararı kapatmıyor.

| Aralık | Çift | Ortalama net | Ortalama alınan fonlama | Ortalama maliyet |
|---|---|---:|---:|---:|
| 1h | ETHBTC | %−80,1 | %+3,3 | %53,0 |
| 1h | SOLBTC | %−85,2 | %+12,8 | %42,8 |
| 1h | SOLETH | %−83,7 | %+17,0 | %43,8 |
| 4h | ETHBTC | %−65,9 | %+2,9 | %20,5 |
| 4h | SOLBTC | %−80,1 | %+15,0 | %16,7 |
| 4h | SOLETH | %−71,0 | %+19,5 | %16,9 |

## 8. Dürüst değerlendirme

1. **Klasik çift ticareti bu üç coinde çalışmıyor.** Bu yöntem, kayan ortalamaya dönüş, sabit ya
   da kayan hedge oranı ve z-skoru girişlerinden oluşuyor.
   - Eğitimde 162 yapılandırmanın hepsi zarar etti, maliyet öncesi bile.
   - Bu yayılımlar eşbütünleşik davranmıyor; günler–haftalar ölçeğinde trend yapıyor.
2. **Kalan küçük etki, SOL'ün çok büyük kısa vadeli göreli hareketlerinin kısmen geri dönmesidir.**
   - Yalnız limit emirle maliyeti kısınca kâra dönüyor.
   - Eğitimdeki kârın çoğu 2021–2022'den geliyor. Bu yıllar SOL'ün çok oynak olduğu dönem.
3. **İç doğrulamada B ve C şartları geçti, ama sonuç kırılgan:**
   - Getiri az sayıda işlemden geliyor: B'de 14 çift işlemi, C'de yaklaşık 28.
   - En iyi tek işlem çıkarılınca iki adayın getirisi de negatif.
   - Alfa t-değeri 1,2 ve 1'in altında.
   - Bootstrap p 0,08–0,10.
   - DSR 0,001–0,002. 639 denemede bu Sharpe değerleri şansla açıklanabilir.
   - B ile C aynı stratejinin iki sürümü (korelasyon 0,91); iki bağımsız kanıt sayılmamalı.
   - En tutarlı görünen D iç doğrulamada başarısız oldu. 2026'da negatif.
4. **İleriye dönük takip:**
   - Protokol 2'ye göre takip seçimi, iç doğrulamada en az 30 işlem yapmış adaylarla sınırlı.
     B (28 işlem) bu eşiğin altında; C (55) eşiği geçiyor.
   - C seçilirse beklenti mütevazı olmalı. Strateji yılda birkaç düzine kısa işlem yapar.
     Kârı az sayıda büyük şoka bağlıdır.
5. **Modelleme varsayımları:** Limit emirlerin dolumu harness'in modeline dayanıyor (fiyatın
   limiti 2 bps geçmesi, maker %0,02).
   - Büyük şok anlarında gerçek dolum ve kuyruk önceliği daha kötü olabilir.
   - Limit emir kullanılmayan aynı kurallar (tarama 2) eğitimde belirgin biçimde daha zayıftı.
6. **Hayatta kalan yanlılığı:** Sonuçlar SOL'e dayanıyor. SOL'ün protokolün sabit evreninde
   bulunması (DENETIM_1, bölüm 7) bu aile için de bir yanlılık kaynağı.

## 9. Dosyalar

- `NOTLAR.md`: plan, arama günlüğü, kesinti ve devam, dondurma kararı (dev_valid öncesi) ve
  dev_valid sonrası not.
- `ortak.py`: tarama yardımcıları; defterden devam ve eğitim içi döküm.
- Taramalar: `tarama1.py` … `tarama6.py`, karşılıkları `.csv` ve `.log`.
  - `tarama2_kesik.log`: kesintiye uğrayan ilk çalıştırmanın günlüğü.
- Tanılamalar: `tanilama*.py` ve karşılıkları `.txt`. Hepsi betimleyici, yalnız eğitim.
- Kontroller ve sonuçlar:
  - `dondurma_kontrol.py/.log`: defter eşleşmesi ve `assert_causal`.
  - `egitim_dokum.py/.txt/.json`: eğitim içi yıllık, bacak ve fonlama dökümü.
  - `dogrulama.py/.log`, `dogrulama_sonuc.json`: tek seferlik iç doğrulama.
  - `dogrulama_korelasyon.py/.txt`: iç doğrulama korelasyonu.
