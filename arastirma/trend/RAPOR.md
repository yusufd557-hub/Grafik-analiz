# Trend takibi ailesi — araştırma raporu

Aile anahtarı: `trend` · Protokol sürümü 1 · Kod: `grafik_analiz/strategies/trend.py`
Betikler: `arastirma/trend/` · Deney defteri: `arastirma/deneyler/trend.jsonl`

## Kısa sonuç

- 185 farklı yapılandırma yalnızca eğitim döneminde (dev_train, 2023 sonuna kadar) denendi.
  En fazla 5 yapılandırma donduruldu ve iç doğrulamada (dev_valid, 01.01.2024–30.06.2025) **bir kez** ölçüldü.
- Dondurulan 5 yapılandırmadan **4'ü protokolün aday şartlarını geçti.** Bunlar spot ve vadelide yalnız alım
  yapan, BTC/ETH/SOL portföyündeki trend topluluklarıdır. Doğrulamada maliyet sonrası net getirileri
  +%26,5 ile +%42,7 arasında, Sharpe oranları 0,60 ile 0,91 arasındadır. İki kat maliyette de kârlı kaldılar.
  Alım-satım (açığa satışlı) vadeli yapı şartları geçemedi (−%3,3).
- **Ancak sonuç güçlü değil:**
  - Doğrulama döneminde dört aday da al-tutun gerisinde kaldı (spot al-tut +%73,7, Sharpe 0,90).
  - Sermayenin yarısıyla al-tut (sabit 0,5 pozisyon) en az onlar kadar iyiydi: +%42,0 ile +%42,6
    arası getiri, Sharpe 0,90, en büyük düşüş −%27 ile −%29 arası. Üç adaydan daha çok kazandırdı,
    `_vt` adayıyla ise yaklaşık eşit kaldı.
  - Deflated Sharpe 0,29–0,42 (anlamlılık için ≥ 0,95 beklenir). Blok bootstrap p değerleri 0,14–0,23.
  - Doğrulamadaki kârın büyük kısmı piyasa yönünden geliyor (beta ≈ 0,45, korelasyon ≈ 0,78).
- Eğitim dönemindeki üstünlük (Sharpe 1,7 / al-tut 1,1) neredeyse tamamen 2018 ve 2022 ayı
  piyasalarından kaçınmaktan geliyordu. Doğrulama döneminde böyle uzun bir düşüş yaşanmadı. Bu yüzden
  trend filtresi burada değer katmadı.
- **Dürüst değerlendirme:** Bu stratejiler maliyetler sonrası kâr etti ve aday şartlarını geçti. Ama
  zamanlama becerisinin şanstan ayrılabildiğine dair istatistiksel kanıt yok. Bunlar "uzun ayı
  piyasalarında zararı sınırlayan, piyasaya bağlı yalnız alım" stratejileri olarak görülmeli.

## Yöntem

- Bütün değerlendirmeler ortak motorla yapıldı: `grafik_analiz.research.evaluate`. Sinyal barın
  kapanışında hesaplanır, işlem bir sonraki barın açılışında yapılır.
- Maliyetler: spotta taraf başına %0,10 komisyon + %0,02 kayma; vadelide %0,05 + %0,02, fonlama ayrıca.
  Her sonuç iki kat maliyetle de hesaplandı.
- Arama sırasında yalnızca `windows=("dev_train",)` kullanıldı, maliyet katları 1× ve 2×.
- Plan ve seçim kuralı aramadan önce `NOTLAR.md` dosyasına yazıldı. Dondurma kararı da dev_valid'e
  bakılmadan önce aynı dosyaya eklendi.
- Kaldıraç yok:
  - Spotta bacak başına pozisyon 0…1, vadelide −1…1.
  - Portföyde üç bacak eşit ağırlıklıdır (her biri 1/3).
  - SOL verisi başlamadan önce (2020-08) onun payı nakitte bekler.
- Bütün sinyaller nedenseldir:
  - Yalnızca geriye dönük pencereler ve `shift(+k)` kullanılır.
  - Donchian kırılımı ve yeniden dengeleme bandı baştan ileri doğru yürür.
  - Dondurulan 5 yapılandırmanın hepsi `assert_causal` denetiminden geçti.

### Sinyal bileşenleri

Her bileşen −1…1 arası değer verir. Spotta ve yalnız alım modunda negatif değerler 0'a kırpılır.

| Bileşen | Kural |
|---|---|
| `tsmom` | N günlük getirinin işareti |
| `sma` | kapanış − N günlük basit ortalama, işareti |
| `emax` | EMA(N/4) − EMA(N), işareti |
| `donch` | Kapanış, önceki N günün en yükseğini geçince alım. Önceki N/2 günün en düşüğünün altına inince çıkış. Alım-satımda tersi açığa satış. İsteğe bağlı ATR iz süren stop. |

- Topluluk sinyali, seçilen bileşen × bakış süresi çiftlerinin ortalamasıdır.
- Bakış süreleri gün cinsindendir. 4h'te ×6 bar, 1h'te ×24 bar olarak uygulanır.
- İsteğe bağlı oynaklık hedefleme: pozisyon × min(1, hedef / 30 günlük gerçekleşen yıllık oynaklık).
- İsteğe bağlı yeniden dengeleme bandı: banttan küçük pozisyon değişiklikleri yapılmaz. Sıfıra iniş ve
  yön değişimi her zaman uygulanır.

## Denenenler ve parametre aralıkları (185 yapılandırma)

| Aşama | İçerik | Sayı |
|---|---|---|
| s1 | 1d, PORT3. 4 fikir × bakış süresi {10, 20, 40, 80, 160, topluluk(10…160)} × {spot yalnız alım, vadeli alım-satım} | 48 |
| s2 | Aynısı 4h | 48 |
| s3 | Tek coinler (BTC, ETH, SOL), 1d, topluluk(10…160): 4 fikir + 4 fikirlik topluluk × {spot, vadeli alım-satım}. Ayrıca 4 fikirlik topluluk PORT3 1d/4h. | 34 |
| s4 | Oynaklık hedefi {0,4; 0,6; 0,8} + band 0,1. Vadeli yalnız alım. Dar topluluk (20, 40, 80). Donchian + ATR stop {2,5; 4}. Vadeli alım-satım + oynaklık hedefi. 1d ve 4h. | 44 |
| s5 | (20, 40, 80) × 4 fikir topluluğu üzerinde: oynaklık hedefi, vadeli yalnız alım ve alım-satım, 1h, band 0,15 | 11 |

- Deney defterinde `pencere=="dev_train"` ve `maliyet_kat==1.0` koşulunu sağlayan **190 satır** var.
  Bunun 185'i aramadan, 5'i dondurulan yapılandırmaların son değerlendirmesinden geliyor.
  Son 5 satır, aramadaki aynı yapılandırmaların tekrarıdır.
- Deflated Sharpe hesabında görevde istendiği gibi 190 kullanıldı.
- 190 denemenin yıllık Sharpe varyansı 0,149. Bu durumda şansla beklenen en yüksek yıllık Sharpe ≈ 1,06'dır.

## Eğitim dönemi (dev_train) sonuçları

### Al-tut kıyası (aynı motor ve maliyetlerle; strateji değildir, deney defterine yazılmadı)

| Piyasa / evren | Başlangıç | Toplam getiri | Sharpe | En büyük düşüş |
|---|---|---|---|---|
| Spot BTC 1d | 2017-08-17 | +%886 | 0,86 | −%83 |
| Spot ETH 1d | 2017-08-17 | +%655 | 0,81 | −%94 |
| Spot SOL 1d | 2020-08-11 | +%2981 | 1,42 | −%96 |
| Spot PORT3 1d | 2017-08-17 | +%3089 | 1,12 | −%86 |
| Spot PORT3 4h | 2017-08-17 | +%3514 | 1,15 | −%86 |
| Vadeli PORT3 1d | 2019-09-08 | +%1403 | 1,20 | −%85 |
| Vadeli PORT3 4h | 2020-01-01 | +%1514 | 1,28 | −%86 |

### Fikir × bakış süresi (PORT3, yıllık Sharpe, 1× maliyet)

Spot yalnız alım, 1d (al-tut 1,12):

| Fikir | 10 | 20 | 40 | 80 | 160 | top.(10…160) | top.(20,40,80) |
|---|---|---|---|---|---|---|---|
| tsmom | 1,56 | 1,47 | 1,59 | 1,26 | 1,17 | 1,42 | 1,57 |
| sma | 1,39 | 1,54 | 1,72 | 1,42 | 1,32 | 1,46 | 1,62 |
| emax | 1,54 | 1,57 | 1,70 | 1,51 | 1,17 | 1,49 | 1,68 |
| donch | 1,31 | 1,67 | 1,63 | 1,52 | 1,33 | 1,50 | 1,73 |
| 4 fikir | | | | | | 1,48 | 1,68 |

Spot yalnız alım, 4h (al-tut 1,15):

| Fikir | 10 | 20 | 40 | 80 | 160 | top.(10…160) | top.(20,40,80) |
|---|---|---|---|---|---|---|---|
| tsmom | 1,43 | 1,56 | 1,62 | 1,25 | 1,21 | 1,43 | 1,59 |
| sma | 1,46 | 1,65 | 1,69 | 1,39 | 1,31 | 1,51 | 1,64 |
| emax | 1,55 | 1,64 | 1,68 | 1,50 | 1,16 | 1,49 | 1,69 |
| donch | 1,39 | 1,68 | 1,68 | 1,63 | 1,37 | 1,57 | 1,78 |
| 4 fikir | | | | | | 1,51 | 1,70 |

Vadeli alım-satım (vadeli al-tut 1d: 1,20; 4h: 1,28):

| Fikir | 1d: 10 | 20 | 40 | 80 | 160 | top. | 4h: 10 | 20 | 40 | 80 | 160 | top. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tsmom | 0,80 | 0,83 | 0,97 | 0,35 | 0,73 | 0,93 | 0,64 | 0,89 | 1,01 | 0,59 | 0,87 | 0,96 |
| sma | 0,61 | 0,55 | 1,06 | 0,59 | 0,95 | 0,79 | 0,80 | 1,01 | 1,14 | 0,70 | 0,94 | 0,95 |
| emax | 0,66 | 0,86 | 1,00 | 0,79 | 0,94 | 0,98 | 0,88 | 1,05 | 0,94 | 1,04 | 1,14 | 1,14 |
| donch | 0,59 | 0,90 | 0,82 | 0,62 | 0,77 | 0,82 | 0,76 | 1,20 | 1,13 | 1,08 | 1,05 | 1,11 |

### Bulgular

- **Spot yalnız alım, PORT3:** Temel ızgarada (ATR stop'suz, oynaklık hedefsiz) bütün fikirler ve
  bakış süreleri al-tutun üstünde (Sharpe 1,16–1,78).
  En büyük düşüş −%36 ile −%65 arasında (al-tut −%86). En iyi bölge 20–80 gündür, geniş bir düzlüktür.
  10 ve 160 gün belirgin biçimde zayıf.
- **Tek coinler (1d, topluluk):**
  - BTC: Sharpe 0,93–1,06 (al-tut 0,86), en büyük düşüş ≈ −%50.
  - ETH: 0,79–0,94 (al-tut 0,81).
  - SOL: 1,88–2,01 (al-tut 1,42).
  - En büyük düşüş belirgin biçimde azalıyor: BTC −%48…−%55 (al-tut −%83), ETH −%46…−%56
    (al-tut −%94), SOL −%58…−%67 (al-tut −%96). İşlem sayısı tek coinde yılda 4–14, yani doğrulamada
    20 işlem şartı için yetersiz.
- **Vadeli alım-satım:** 73 yapılandırmanın Sharpe ortalaması 0,86, en iyisi 1,20. Vadeli al-tutun
  (1,20–1,28) üstüne çıkamadı. Açığa satış ayağı eğitim döneminde değer katmadı. Bu ayak yükselen
  piyasada fonlama alıyor, ama fiyat kaybı daha büyük.
- **Vadeli yalnız alım:** Sharpe 1,42–1,78. Fonlama maliyeti yılda yaklaşık %10–11 (eğitim döneminde
  toplam ≈ %39–48).
- **Oynaklık hedefleme:** Sharpe'ı pek değiştirmedi (1,41–1,69). En büyük düşüşü azalttı: hedef 0,4'te
  −%31…−%34, hedef 0,6'da −%41…−%46. Getiriyi de orantılı olarak düşürdü.
- **ATR iz süren stop:** 1d'de nötr ya da hafif olumlu (Donchian 20 gün: stop'suz 1,67, ATR 2,5 ile 1,75). 4h'te kötü sonuç verdi (Sharpe 0,79–1,34). Nedeni: ATR 4 saatlik
  barlardan hesaplandığı için stop çok dar kaldı.
- **1h:** Sharpe benzer (1,64 / 1,76). Maliyet duyarlılığı daha yüksek: spotta 2× maliyette getiri
  %43 → %30 kat.
- 185 yapılandırmadan yalnızca 2'sinin eğitim getirisi ≤ 0. İkisi de vadeli alım-satım.

## Dondurulan yapılandırmalar ve gerekçe

Seçim kuralı aramadan önce yazıldı (`NOTLAR.md`):

1. Eğitimde 1× ve 2× maliyette net getiri > 0.
2. Portföy toplamında yılda ≥ 20 işlem.
3. Birincil ölçü eğitim Sharpe'ı. Keskin tepe yerine düzlük ve topluluk tercih edilir.
4. Yalnız alım stratejileri al-tuttan daha yüksek Sharpe ve daha küçük düşüş göstermeli.
5. Mümkün olduğunca farklı yapılar seçilir.

Bu kurallara göre:

- 20–80 gün düzlüğünün ortası olan **4 fikir × (20, 40, 80) gün = 12 bileşenli topluluk** seçildi.
  Tek bakış süreli tepeler (ör. sma 40 gün 1,72) seçilmedi.
- Yalnız Donchian ya da yalnız EMA toplulukları da seçilmedi, çünkü yılda 8–14 işlemle 2. şartı
  karşılamıyorlar.

| # | Ad | Piyasa | Bar | Mod | Ek |
|---|---|---|---|---|---|
| 1 | `trend_ens_spot_port3_1d` | spot PORT3 | 1d | yalnız alım | — |
| 2 | `trend_ens_spot_port3_4h` | spot PORT3 | 4h | yalnız alım | band 0,15 (2× maliyette daha iyi: %4863'e karşı %4332) |
| 3 | `trend_ens_spot_port3_4h_vt` | spot PORT3 | 4h | yalnız alım | hedef oynaklık 0,6, 30 gün, band 0,1 (risk azaltılmış) |
| 4 | `trend_ens_vadeli_port3_4h_alim` | vadeli PORT3 | 4h | yalnız alım | eğitimde en yüksek Sharpe (1,78) |
| 5 | `trend_ens_vadeli_port3_4h_ls_vt` | vadeli PORT3 | 4h | alım-satım | hedef oynaklık 0,6, band 0,1 |

5 numaralı yapı, eğitimde vadeli al-tutun Sharpe'ının altındaydı (1,19'a karşı 1,28). Tek iki yönlü
yapı olduğu için bilgi amaçlı alındı. Bu, dondurma notunda dev_valid'den önce yazıldı.

## İç doğrulama (dev_valid, 01.01.2024–30.06.2025) — tek seferlik ölçüm

`evaluate(spec)` her yapılandırma için bir kez çalıştırıldı (`dogrulama.py`). Sonuçlar
`dogrulama_sonuc.json` dosyasında.

### Ana tablo

| Ad | Eğitim getiri 1× / 2× | Eğitim Sharpe | Eğitim düşüş | Doğr. getiri 1× | Doğr. getiri 2× | Doğr. Sharpe 1× / 2× | Doğr. düşüş | Doğr. işlem | p (bootstrap) | Deflated Sharpe | Aday |
|---|---|---|---|---|---|---|---|---|---|---|---|
| trend_ens_spot_port3_1d | +%4907 / +%4452 | 1,68 | −%52,7 | **+%32,5** | +%28,4 | 0,69 / 0,64 | −%33,8 | 36 | 0,20 | 0,326 | GEÇTİ |
| trend_ens_spot_port3_4h | +%5400 / +%4863 | 1,74 | −%48,9 | **+%38,6** | +%34,2 | 0,77 / 0,72 | −%33,3 | 66 | 0,18 | 0,361 | GEÇTİ |
| trend_ens_spot_port3_4h_vt | +%1410 / +%1289 | 1,69 | −%41,8 | **+%42,7** | +%38,7 | 0,91 / 0,85 | −%29,9 | 66 | 0,14 | 0,425 | GEÇTİ |
| trend_ens_vadeli_port3_4h_alim | +%1630 / +%1500 | 1,78 | −%50,1 | **+%26,5** | +%22,1 | 0,60 / 0,54 | −%34,1 | 62 | 0,23 | 0,287 | GEÇTİ |
| trend_ens_vadeli_port3_4h_ls_vt | +%322 / +%279 | 1,19 | −%52,3 | **−%3,3** | −%8,9 | 0,12 / 0,02 | −%41,1 | 180 | 0,43 | 0,126 | GEÇMEDİ |

### Ek bilgiler

- **En iyi tek işlem çıkarılınca doğrulama getirisi:** 1: +%17,5 · 2: +%24,6 · 3: +%28,2 · 4: +%15,2 · 5: −%13,5.
- **Doğrulamadaki maliyetler:** spotta toplam %2,8–3,2. Vadeli yalnız alımda maliyet %3,6, fonlama %11,2.
- **Aday şartları (`candidate_check`):** İlk dört yapılandırma bütün maddeleri geçti: eğitim > 0,
  doğrulama > 0, 2× maliyette > 0, Sharpe ≥ 0,5, işlem ≥ 20. Beşinci yapılandırma getiri, 2× getiri
  ve Sharpe maddelerinden kaldı.
- **Deflated Sharpe parametreleri:**
  - Deneme sayısı 190.
  - Deneme Sharpe varyansı 0,149.
  - Gün sayısı ve dev_valid günlük getirilerin çarpıklık/basıklık değerleri `summarize` çıktısından alındı.
  - Bütün değerler 0,95 eşiğinin çok altında. Doğrulama Sharpe'ları (0,60–0,91), 190 denemede şansla
    beklenen en yüksek değerin (≈ 1,06) altında.

### Al-tut kıyası (aynı pencere, aynı maliyetler)

| Kıyas | Doğr. getiri | Sharpe | En büyük düşüş |
|---|---|---|---|
| Spot PORT3 al-tut 1d / 4h | +%73,7 / +%74,3 | 0,90 / 0,90 | −%49,1 / −%51,5 |
| Vadeli PORT3 al-tut 4h | +%50,8 | 0,75 | −%52,1 |
| Spot PORT3 yarı al-tut (sabit 0,5) 1d / 4h | +%42,0 / +%42,6 | 0,90 / 0,91 | −%27,1 / −%29,3 |
| Vadeli PORT3 yarı al-tut 4h | +%32,7 | 0,75 | −%29,4 |
| Tek coin spot al-tut: BTC / ETH / SOL | +%153,4 / +%8,9 / +%52,2 | 1,47 / 0,43 / 0,75 | −%28 / −%64 / −%60 |

Eğitimde yarı al-tut: spot 1d +%760, Sharpe 1,12, en büyük düşüş −%58. Trend stratejileri eğitimde bu
kıyası açıkça geçiyordu (Sharpe 1,7, getiri 6 kat fazla).

### Piyasaya bağlılık (`piyasa_iliskisi.py`, betimleyici)

Ölçüm: günlük getirilerin aynı evrendeki al-tut ile korelasyonu ve betası.

| Ad | Ort. pozisyon eğitim / doğr. | Korelasyon eğitim / doğr. | Beta eğitim / doğr. |
|---|---|---|---|
| spot_port3_1d | 0,40 / 0,53 | 0,78 / 0,77 | 0,45 / 0,45 |
| spot_port3_4h | 0,40 / 0,53 | 0,77 / 0,78 | 0,44 / 0,46 |
| spot_port3_4h_vt | 0,30 / 0,47 | 0,73 / 0,77 | 0,28 / 0,38 |
| vadeli_port3_4h_alim | 0,47 / 0,54 | 0,77 / 0,79 | 0,44 / 0,47 |
| vadeli_port3_4h_ls_vt | 0,46 / 0,57 | 0,02 / 0,03 | 0,01 / 0,02 |

## Yorum ve sonuç

1. **Protokol açısından:** 4 yapılandırma aday oldu. Maliyet sonrası ve iki kat maliyette kârlı
   kaldılar, Sharpe ≥ 0,5 ve en az 20 işlem şartlarını sağladılar.
   - En dengelisi `trend_ens_spot_port3_4h_vt`: doğrulamada Sharpe 0,91, en büyük düşüş −%30.
2. **Al-tuta göre:** Doğrulama döneminde trend stratejileri al-tutu geçemedi.
   - Getirileri al-tutun yaklaşık yarısı kadar.
   - Sharpe en iyi durumda al-tutla eşit (0,91'e karşı 0,90).
   - Düşüşleri daha küçük, ama bu ortalama pozisyonun ≈ 0,5 olmasından kaynaklanıyor.
   - Sabit yarı pozisyonla al-tut, `_vt` dışındaki üç adaydan daha yüksek getiri ve daha küçük
     düşüş verdi. `_vt` ile yaklaşık eşitti: +%42,7 / −%29,9'a karşı 4h yarı al-tut +%42,6 / −%29,3.
   - Yani 2024–2025'te zamanlama değer katmadı. Sonucu piyasaya maruz kalma miktarı belirledi.
3. **Eğitim üstünlüğünün kaynağı:** 2018 ve 2022'deki uzun düşüşlerde nakde geçmek. Bu üstünlük, benzer
   bir ayı piyasasında tekrar edebilir. Doğrulama dönemi bu açıdan bir test sağlamadı, çünkü dönem genel
   olarak yükselen ve dalgalı bir piyasaydı.
4. **İstatistiksel anlamlılık yok:** Deflated Sharpe 0,29–0,42, bootstrap p 0,14–0,23. Bu sonuçlar 190
   denemelik bir aramada şansla da çıkabilir.
5. **Alım-satım vadeli trend:** Hem eğitimde (al-tutun altında) hem doğrulamada (zarar) başarısız.
   Bu evrende açığa satışlı trend takibi desteklenmiyor.
6. **Öneri:**
   - Finalist seçilirse en savunulabilir aday `trend_ens_spot_port3_4h_vt` olur. Gerekçeler: en yüksek
     doğrulama Sharpe'ı, en küçük düşüş, en yüksek Deflated Sharpe.
   - Ama beklenti "piyasayı yenen sistem" değil, "uzun düşüşlerde riski azaltan yalnız alım" olmalı.
   - Görülmemiş dönemde (2025-07 → 2026-09) al-tut ve yarı al-tut ile birlikte raporlanmalı.

## Protokol notları ve sınırlamalar

- dev_valid'e yalnızca dondurulan 5 yapılandırma için bir kez bakıldı. Ardından parametre veya kural
  değişmedi. Yalnızca `specs()` açıklama metinleri sonuçları içerecek biçimde güncellendi.
- Al-tut ve yarı al-tut kıyasları `evaluate(record=False)` ile hesaplandı. Strateji olmadıkları için
  deneme sayılmadı.
  - Yarı al-tut ve piyasa ilişkisi analizi dev_valid sonucundan sonra eklendi. Betimleyicidir, seçimi
    etkilemedi.
- Yeniden üretilebilirlik denetimi `evaluate(record=False)` ile yapıldı. Aynı dondurulmuş
  yapılandırmalar aynı sayıları verdi, deftere yazılmadı.
- Kod denemesi sırasında bir test sinyalinin bütün geliştirme dönemi üzerindeki pozisyon oranı yazdırıldı.
  Bu sırada getiri veya performans bilgisi görülmedi.
- Eşit ağırlıklı PORT3'te SOL verisi 2020-08'de başlıyor. Ondan önce sermayenin 1/3'ü nakitte. Al-tut
  kıyası da aynı biçimde hesaplandı.
- Vadeli 1d verisi 2019-09 (BTC) ve 2019-11 (ETH) tarihinde başlıyor, fonlama kaydı ise 2020-01-01'de.
  İlk aylarda fonlama düşülmüyor. Etkisi küçük, dondurulan vadeli yapılandırmalar zaten 4h ve 2020'den başlıyor.
- Harness'in işlem sayısı aynı yöndeki kesintisiz pozisyon dilimlerini sayar. Topluluk ve oynaklık
  hedeflemedeki boyut değişiklikleri ayrı işlem sayılmaz.
  - Bu değişikliklerin maliyeti günlük net getiride vardır.
  - İşlem bazlı ölçüler (kazanma oranı, en iyi işlem) ise bu ara maliyetleri içermez, biraz iyimserdir.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `NOTLAR.md` | Aramadan önce yazılan plan, seçim kuralı ve dondurma kararı |
| `arama.py` | Arama aşamaları (s1–s5), yalnız dev_train |
| `sonuclar_train.csv` | 185 yapılandırmanın dev_train özetleri |
| `ozet.py` | Sonuç tablosunu filtreleyip gösterir |
| `al_tut.py`, `al_tut_*.csv` | Al-tut kıyası |
| `dogrulama.py`, `dogrulama_sonuc.json` | Tek seferlik dev_valid ölçümü, aday şartları, Deflated Sharpe |
| `piyasa_iliskisi.py` | Ortalama pozisyon, korelasyon/beta, yarı al-tut kıyası |
