# t2_emir_akisi — Emir akışı dengesizliği (tur 2) — Rapor

Protokol sürüm 2 (`docs/PROTOKOL_2.md`). Aile anahtarı `t2_emir_akisi`.
Strateji kodu: `grafik_analiz/strategies/t2_emir_akisi.py`. Defter:
`arastirma/tur2/deneyler/t2_emir_akisi.jsonl`. Çalışma notları ve dondurma
kararı: `NOTLAR.md`. Çalışma iki kez kesildi ve kaldığı yerden sürdürüldü
(bkz. `NOTLAR.md`, "Kesinti ve devam" bölümleri); hiçbir tarama baştan
alınmadı, defter satırları silinmedi.

## Sonuç

**Dondurulan beş yapılandırmanın hiçbiri `candidate_check`'i geçmedi.**
Eğitim döneminde (dev_train) çok güçlü görünen kenar, iç doğrulamada
(dev_valid) neredeyse tamamen kayboldu. İşlem başına brüt kenar 64–180 bps'ten
9–28 bps'e indi; maliyet (vadelide 13–14, spotta 24 bps/işlem) bunun çoğunu
ya da tamamını yiyor. En iyi dev_valid sonucu akışsız kontrolündür (%+3,98,
Sharpe 0,36); akış kullanan sürümler bu kontrolden iyi değil.

Ana bulgu: Mum verisindeki taker alım/satım dengesizliğinin (CVD) bu
ailede bulunan kenarı, büyük ölçüde **aşırı fiyat düşüşünden sonraki
tepkidir** (çöküş sonrası alım). İşlem sayısı eşlenmiş akışsız fiyat dönüşü
kontrolü dev_train'de aynı sonucu verdi (Sharpe 2,29'a karşı 2,26; günlük
korelasyon 0,79). Akışın tek başına (fiyattan arındırılmış) devam sinyali
dev_train'de pozitifti ama kârın %99'u en iyi 20 günden geliyordu ve
dev_valid'de zarar etti.

## Veri ve tanımlar

- Mumlardaki `taker_buy_base` ve `volume` (Binance, vadeli ve spot,
  BTC/ETH/SOL; 5m, 15m, 1h).
- Bar dengesizliği `imb = (2·taker_buy_base − volume) / volume`; kümülatif
  hacim deltası `CVD = Σ (2·taker_buy_base − volume)`; n barlık akış
  `Σ_n delta / Σ_n hacim`.
- Bütün z-skorları L barlık kayan pencereyle (varsayılan L = 2000) hesaplandı.
  Hiçbir tam örneklem istatistiği, ortalanmış pencere ya da `shift(-k)`
  kullanılmadı.
- Skor türleri:
  - `akis`: akış z-skoru.
  - `patlama`: tek bar dengesizlik z-skoru, isteğe bağlı hacim şartı.
  - `uyumsuzluk`: akış z − n barlık getiri z (CVD–fiyat uyumsuzluğu).
  - `akis_artik`: akışın aynı n barlık getiriyle açıklanamayan kısmı
    (kayan regresyon artığı), z-skoru.
  - `cvd_aralik`: CVD'nin ve fiyatın n barlık aralık içindeki konum farkı.
  - `spot_vadeli`: spot akışı − vadeli akışı, z-skoru.
  - Kontroller (akışsız): `getiri` (n barlık getiri z) ve `getiri_artik`.
- Kural: |S| > k olunca tetik. `devam` S yönünde, `donus` tersine pozisyon
  alır. Pozisyon son tetikten sonra `hold` bar tutulur.
- Seçenekler: tek yön, `exit_z` erken çıkış ve limit emir (giriş ve/veya
  çıkış).
- Piyasa: vadeli PORT3 (BTC/ETH/SOL eşit ağırlık, her bacak −1…1). Bir sürüm
  spot PORT3 (yalnız uzun).

## Denenen yaklaşımlar ve yapılandırma sayısı

Hepsi `evaluate(spec, windows=("dev_train",), ...)` ile ölçüldü. dev_valid'e
arama sırasında bakılmadı.

| Aşama | Betik | İçerik | Yapılandırma |
|---|---|---|---:|
| 1 — kenar haritası | `tarama1.py` | akis, patlama, uyumsuzluk, cvd_aralik, spot_vadeli; 5m/15m/1h; n {1…288}, k {2, 3} (cvd_aralik {0,5, 0,8}), hold 5m {12, 48, 288}, 15m {4, 16, 96}, 1h {1, 6, 24}; devam yönü | 288 |
| 2a — kontroller | `tarama2.py` | getiri dönüş (akışsız), akis_artik devam, getiri_artik dönüş | 135 |
| 2b — inceltme (1× ve 2×) | `tarama3.py` | uyumsuzluk ve akis_artik, 5m/15m; n {12…144}, k {2,5, 3, 3,5}, hold {2…48} | 117 |
| 2c — kontrol ve dayanıklılık (1× ve 2×) | `tarama4.py` | işlem sayısı eşlenmiş getiri dönüş k {4, 5}; L {1000, 4000}, k 4, uzun/kısa, exit_z; limit emir (giriş 0/10/30 bps, çıkış 10 bps); spot; 1h uyumsuzluk | 61 |
| Doğrulama | `dogrulama.py` | 5 dondurulmuş yapılandırmanın tek değerlendirmesi | (5 tekrar) |

- Defterde 799 satır var: 606 dev_train 1×, 183 dev_train 2×, 5 dev_valid 1×
  ve 5 dev_valid 2×.
- Benzersiz yapılandırma sayısı 594.
  - 601 arama satırının 7'si önceki aşamaların tekrarıdır.
  - Kalan 5 satır, dondurulanların doğrulamadaki dev_train tekrarıdır.
- Tanılar defter dışında yapıldı ve yalnız dev_train verisini kullandı:
  - `tani1.py`: olay bazlı akış katkısı.
  - `tani2.py`: kârın yoğunlaşması, yön ayrımı ve korelasyon.

## dev_train sonuçları (ana varyantlar)

Hepsi vadeli PORT3, piyasa emri, 1× maliyet. Aksi yazılmadıkça L = 2000.
"Brüt/işlem", bacak başına işlemin ortalama brüt getirisidir. Bu satırlarda
maliyet ve fonlama işlem başına yaklaşık 13–14 bps'tir.

**Aşama 1:**

- `akis` (CVD z-skoru, devam):
  - 5m ve 15m'de brüt kenar yaklaşık 0 (−2…+3 bps/işlem); hepsi zararda.
  - 1h n72 k2 h24: %+90, Sharpe 0,74, alfa %+13. Komşuları zayıf.
- `patlama`: kenar yok.
- `cvd_aralik` ve `spot_vadeli` devam: çoğunlukla negatif.
- `uyumsuzluk` devam: tek güçlü bölge. Beta ≈ 0.
  - 5m n72 k3 h12: %+299, Sharpe 1,76, alfa %+28, brüt 72 bps.

**Aşama 2a–2c (seçilmiş satırlar):**

| Yapılandırma | Getiri | Sharpe | Düşüş | İşlem | Alfa | Beta | Alfa t | Brüt/işlem | 2× getiri |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| uyumsuzluk 5m n72 k3,5 h12 | %+449,8 | 2,26 | %−16,1 | 398 | %+36,5 | −0,01 | 5,23 | 140 bps | %+356,7 |
| uyumsuzluk 5m n72 k3,5 h12, L1000 / L4000 | %+311 / %+382 | 1,79 / 1,82 | | 380 / 437 | %+31 / %+33 | | | 126 / 119 | |
| uyumsuzluk 5m n72 k3,5 h12, yalnız uzun / yalnız kısa | %+380 / %+14 | 2,14 / 0,65 | | 224 / 174 | %+34 / %+3 | | | 221 / 36 | |
| uyumsuzluk 15m n24 k3,5 h2 | %+369,2 | 2,02 | %−20,2 | 479 | %+32,4 | −0,00 | 4,55 | 110 bps | %+275,2 |
| uyumsuzluk 5m n36 k3,5 h24 | %+461 | 1,93 | %−23,4 | 692 | %+37,7 | −0,01 | 4,50 | 88 bps | %+306 |
| uyumsuzluk k=2,5 (5m n72 h12) | %+182 | 1,12 | %−25,1 | 1362 | %+22,4 | 0,00 | 2,46 | 36 bps | %+49 |
| akis_artik 15m n12 k3,5 h8 | %+173,8 | 1,48 | %−12,3 | 625 | %+23,5 | −0,02 | 3,71 | 64 bps | %+104,6 |
| akis_artik 15m n12 k3,5 h8, L1000 / L4000 | %+104 / %+165 | 1,36 / 1,50 | | 639 / 643 | %+16 / %+23 | | | 48 / 61 | |
| akis_artik 5m n144 k3 h24 | %+199 | 1,44 | %−11,2 | 865 | %+26,4 | −0,03 | 3,71 | 54 bps | %+100 |
| akis_artik 5m n144 k3 h24, L1000 / L4000 | %+28 / %+18 | 0,37 / 0,29 | | 1165 / 710 | %+9 / %+3 | | | 22 / 22 | |
| **kontrol:** getiri dönüş 5m n72 k3 h12 (aynı k) | %+126 | 0,87 | | 1645 | %+19 | −0,01 | | 29 bps | |
| **kontrol:** getiri dönüş 5m n72 k5 h12 (işlem sayısı eşlenmiş) | %+413,2 | 2,29 | %−17,7 | 296 | %+35,2 | −0,01 | 5,34 | 180 bps | %+347,0 |
| **kontrol:** getiri dönüş 15m n24 k5 h2 | %+159,5 | 1,85 | %−17,3 | 292 | %+20,8 | −0,01 | 4,37 | 111 bps | %+126,5 |
| uyumsuzluk 5m n72 k3,5 h12, giriş limiti 0 / 10 / 30 bps | %+449 / %+419 / %+391 | 2,25 / 2,20 / 2,22 | | 398 / 391 / 368 | | | | | |
| uyumsuzluk spot 5m n72 k3,5 h12, yalnız uzun | %+290,0 | 2,21 | %−14,6 | 321 | %+29,4 | −0,01 | 5,20 | 153 bps (maliyet 24) | %+201,7 |
| akis_artik spot 15m n12 k3,5 h8, yalnız uzun | %+17,3 | 0,40 | %−10,4 | 285 | %+3,6 | −0,01 | 1,23 | 41 bps | %−6,6 |
| uyumsuzluk 1h n6 k3 h1 | %+111 | 1,29 | %−22,1 | 476 | %+15 | 0,01 | 2,66 | 60 bps | %+69 |

**Gözlemler (dev_train):**

- Brüt kenarın maliyeti aştığı tek bölge çok seyrek tetiklenen eşiklerdir
  (k ≥ 3). k = 2–2,5 ve kısa n ile işlem sayısı 2–5 katına çıkıyor. Bu
  bölgede brüt kenar 0–35 bps/işleme düşüyor ve 2× maliyette çoğu zararda.
  Kısa vadede (5m/15m) saf akış devamı ya da tek bar patlaması maliyeti
  karşılamıyor.
- Kâr uzun yönden geliyor. Uyumsuzluk 5m'de uzun işlemler toplam %+156,
  kısa işlemler %+13 getirdi.
- Kâr az sayıda günde yoğunlaşıyor. Uyumsuzluk 5m'de 225 aktif günün en iyi
  10'u toplam log getirinin %46'sını, en iyi 20'si %68'ini veriyor.
  akis_artik 15m'de en iyi 20 gün %99'unu veriyor. En iyi günler bilinen
  ani düşüş günleri, örneğin 2020-03-13, 2021-05-19 ve 2021-09-07.
- Akışın katkısı (`tani1.log`, 5m n72, 3 coin, dev_train):
  - `uyumsuzluk > 3,5` barlarının kârı, aynı anda fiyat z < −4 olan barlardan
    geliyor: +139 bps ileri getiri, n = 1822.
  - Fiyat düşmeden akışın güçlü olduğu barlar −32 bps getirdi (n = 787).
  - Fiyat z < −4 olaylarında akışa göre üçte birlikler monoton değil
    (+56 / +19 / +115 bps).
  - Bu nedenle akışın aşırı fiyat dönüşüne ek bilgisi küçük ve belirsiz.
- Limit emir sonucu pek değiştirmiyor (Sharpe 2,20–2,25), çünkü brüt kenar
  maliyetin yaklaşık 10 katı. Belirgin ters seçilim de görülmedi.
- Dayanıklılık:
  - Uyumsuzluk L, k, exit_z ve limit değişikliklerine dayanıklı (Sharpe
    1,79–2,25).
  - akis_artik 15m n12 dayanıklı. akis_artik 5m n144 dayanıksız (L1000:
    0,37; L4000: 0,29) ve elendi.
  - 15m n48 ve 1h n12 zayıf.

## Dondurma gerekçesi

Karar `NOTLAR.md`'ye 16:34 UTC'de, ilk dev_valid satırından (16:35:41 UTC)
önce yazıldı. Yalnız dev_train'e dayanır.

1. **`t2_emir_akisi_uyum_5m_n72_k3.5_h12`**: Ailenin en güçlü bölgesinin
   merkezi. L, k, exit_z ve limit komşuları da güçlü.
2. **`t2_emir_akisi_uyum_15m_n24_k3.5_h2`**: Farklı zaman dilimi. 1 ile
   dev_train günlük korelasyonu 0,59.
3. **`t2_emir_akisi_artik_15m_n12_k3.5_h8`**: Fiyattan arındırılmış saf akış
   sinyali. L'ye dayanıklı.
4. **`t2_emir_akisi_uyum_spot_5m_n72_k3.5_h12_uzun`**: Spot uygulaması;
   kaldıraç, açığa satış ve fonlama yok.
5. **`t2_emir_akisi_kontrol_getiri_donus_5m_n72_k5_h12`**: Önceden kayda
   geçirilmiş **akışsız kontrol**. 1 ile karşılaştırılarak akışın dev_valid'de
   ek katkı yapıp yapmadığı ölçülür.

`assert_causal` beşinde de geçti: varsayılan 3 kesim ve ek 4 kesim
(`nedensellik.log`).

## dev_valid sonuçları (01.01.2025 – 30.09.2026, tek değerlendirme)

Kaynak: `dogrulama_sonuc.json`, `dogrulama.log`, `dogrulama_kenar.log`.

| Yapılandırma | Maliyet | Getiri | Sharpe | En büyük düşüş | İşlem | Alfa (yıllık) | Beta | Alfa t |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| uyum 5m n72 k3,5 h12 (vadeli) | 1× | %+2,09 | 0,18 | %−20,94 | 147 | %+1,58 | 0,000 | 0,23 |
| | 2× | %−4,68 | −0,26 | %−23,04 | 147 | %−2,35 | 0,000 | −0,35 |
| uyum 15m n24 k3,5 h2 (vadeli) | 1× | %+2,57 | 0,18 | %−13,40 | 144 | %+2,12 | −0,004 | 0,25 |
| | 2× | %−4,10 | −0,16 | %−15,10 | 144 | %−1,74 | −0,003 | −0,20 |
| artik 15m n12 k3,5 h8 (vadeli) | 1× | %−3,24 | −0,35 | %−9,70 | 217 | %−1,69 | −0,011 | −0,45 |
| | 2× | %−12,56 | −1,49 | %−15,93 | 217 | %−7,48 | −0,012 | −1,96 |
| uyum spot 5m n72 k3,5 h12 (uzun) | 1× | %−5,34 | −0,43 | %−15,80 | 139 | %−3,06 | 0,027 | −0,61 |
| | 2× | %−15,30 | −1,32 | %−19,44 | 139 | %−9,44 | 0,032 | −1,84 |
| kontrol getiri dönüş 5m n72 k5 h12 | 1× | %+3,98 | 0,36 | %−15,94 | 79 | %+2,47 | 0,001 | 0,47 |
| | 2× | %+0,21 | 0,05 | %−16,02 | 79 | %+0,36 | 0,002 | 0,07 |

Ek ölçüler (dev_valid, 1×):

| Yapılandırma | Bootstrap p | En iyi işlem çıkınca | Kazanan işlem | Brüt/işlem (dev_train → dev_valid) | Maliyet+fonlama/işlem |
|---|---:|---:|---:|---:|---:|
| uyum 5m | 0,385 | %−0,65 | %52 | 140,5 → 18,1 bps | 13,7 bps |
| uyum 15m | 0,375 | %−0,12 | %53 | 109,7 → 20,5 bps | 13,7 bps |
| artik 15m | 0,686 | %−5,68 | %35 | 63,7 → 9,5 bps | 13,9 bps |
| uyum spot | 0,723 | %−9,27 | %45 | 153,2 → 12,6 bps | 24,0 bps |
| kontrol | 0,302 | %−0,49 | %61 | 180,1 → 28,4 bps | 13,9 bps |

**Ayrıntılar (betimleyici, dev_valid'den sonra; parametre değişmedi):**

- **İşlem sıklığı:** Hemen hemen aynı kaldı. Uyum 5m günde 0,23 işlem yaptı
  (dev_train'de 0,22). Tetikler gelmeye devam etti, ama tetik sonrası tepki
  zayıfladı.
- **Yön (uyum 5m):**
  - Uzun: 87 işlem, toplam net %+5,4, brüt +32 bps/işlem. dev_train'de
    yaklaşık +220 bps/işlem idi.
  - Kısa: 60 işlem, toplam net %−3,3, brüt −3 bps/işlem.
- **Bacaklar (uyum 5m):** BTC %+14,2, ETH %−16,1, SOL %+7,3.
- **Günlük korelasyon (dev_valid):**
  - uyum 5m ↔ kontrol: 0,79.
  - uyum 5m ↔ uyum 15m: 0,87.
  - artik ↔ diğerleri: −0,12…0,32.

## candidate_check

| Şart | uyum 5m | uyum 15m | artik 15m | uyum spot | kontrol |
|---|---|---|---|---|---|
| Eğitimde net > 0 | geçti | geçti | geçti | geçti | geçti |
| Doğrulamada net > 0 | geçti | geçti | **geçmedi** | **geçmedi** | geçti |
| Doğrulamada 2× net > 0 | **geçmedi** | **geçmedi** | **geçmedi** | **geçmedi** | geçti (%+0,21) |
| Doğrulamada Sharpe ≥ 0,5 | **geçmedi** (0,18) | **geçmedi** (0,18) | **geçmedi** | **geçmedi** | **geçmedi** (0,36) |
| Doğrulamada ≥ 20 işlem | geçti | geçti | geçti | geçti | geçti |
| Eğitimde alfa > 0 | geçti | geçti | geçti | geçti | geçti |
| Doğrulamada alfa > 0 | geçti (%+1,6) | geçti (%+2,1) | **geçmedi** | **geçmedi** | geçti (%+2,5) |
| **Aday** | **hayır** | **hayır** | **hayır** | **hayır** | **hayır** |

## Deflated Sharpe

- **Deneme sayısı:** defterdeki `pencere == "dev_train"` ve
  `maliyet_kat == 1.0` satırları, yani 606 satır (594 benzersiz yapılandırma).
- **Denemelerin Sharpe dağılımı:** varyans 4,60, ortalama −0,37, en büyük
  2,29 (yıllık).
- **Şansla beklenen en büyük Sharpe:** yaklaşık 6,7 (yıllık).
- **Sonuç:** Beş yapılandırmanın Deflated Sharpe değeri dev_valid Sharpe'ı
  ile **0,0000**. 594 benzersiz deneme sayısıyla da sonuç 0,0000. Kayan
  nokta değeri 1e−20 düzeyinde.
- **dev_train Sharpe'ı ile de** DSR 0,0000 (örn. 2,26 için).
- **Not:** Varyansı yüksek turnover'lı, çok negatif Sharpe'lı ilk
  taramalar şişiriyor. Bu yüzden ölçü bu ailede ayırt edici değil. Ama
  dev_valid Sharpe'ları zaten ≤ 0,36 olduğundan sonuç değişmez.

## Al-tut karşılaştırması (BTC/ETH/SOL eşit ağırlık; alfa kıyası)

| Kıyas | Dönem | Getiri | Sharpe | En büyük düşüş |
|---|---|---:|---:|---:|
| Vadeli PORT3 | dev_train (2019-09-08'den) | %+3953 | 1,28 | %−85,1 |
| Vadeli PORT3 | dev_valid | %−18,93 | 0,10 | %−64,3 |
| Spot PORT3 | dev_train (2017-08-17'den) | %+6322 | 1,11 | %−87,9 |
| Spot PORT3 | dev_valid | %−18,94 | 0,10 | %−64,3 |

- dev_valid'de piyasa %−19 düştü ve en büyük düşüşü %−64 oldu.
  Stratejilerin iki tanesi yaklaşık %+2–4 kazandı.
- Bu fark piyasa yönünden bağımsızdır: stratejiler zamanın yalnız
  %0,6–3,4'ünde pozisyondaydı ve beta ≈ 0.
- Fark alfa olarak da anlamlı değil: alfa t ≤ 0,47, bootstrap p ≥ 0,30.

## Dürüst değerlendirme

1. **dev_train'deki güçlü sonuç büyük ölçüde geçmiş bir rejimin ürünüydü.**
   - 2020–2024'te çöküş sonrası 1–6 saatlik tepki çok güçlüydü: uzun işlem
     başına yaklaşık 2 %.
   - 2025–2026'da tetik sıklığı aynı kaldı, ama tepki maliyetin hemen
     üstünde ya da altında kaldı.
   - En yüksek dev_train alfa t değerleri (4,5–5,3), çoklu denemeye ve
     kârın az sayıda güne yoğunlaşmasına karşı korumuyor.
2. **Emir akışı ek bilgi katmadı.**
   - İşlem sayısı eşlenmiş akışsız kontrol dev_train'de aynı sonucu verdi.
   - dev_valid'de kontrol, akışlı sürümden biraz daha iyiydi (%+3,98'e
     karşı %+2,09).
   - Saf akış sinyali (`akis_artik`) ve spot sürümü dev_valid'de zararda.
3. **Kısa vadede (5m/15m) akış devamı, tek bar dengesizlik patlaması ve
   klasik CVD–fiyat aralık uyumsuzluğu maliyeti karşılamıyor.** İşlem
   başına brüt kenar 0–20 bps, piyasa emri maliyeti 14 bps. Limit emir
   (maker %0,02) maliyeti işlem başına yaklaşık 10 bps azaltır. Ama
   kenarı olmayan bir sinyali kârlı yapmaya yetmiyor; kenarı olan seyrek
   sinyallerde ise sonucu değiştirmiyor.
4. **Sınırlama:** Maliyet modeli çöküş anlarında da 2 bps kayma varsayıyor.
   - Bu aile tam o anlarda işlem yapıyor; gerçek kayma muhtemelen daha
     büyük.
   - dev_train sonuçları bu yüzden de iyimser.
   - dev_valid'de 2× maliyette bile sonuçlar negatif ya da sıfıra yakın.
5. **Bu aileden ileriye dönük takibe aday çıkmadı.**

## Dosyalar

- `NOTLAR.md`: plan, aşama kayıtları, kesinti notları, dondurma kararı
  (dev_valid'den önce) ve sonuç notu.
- `ortak.py`: değerlendirme ve tanı yardımcısı.
- `tarama1.py` … `tarama4.py`: tarama betikleri. Her birinin `.csv` ve
  `.log` çıktıları var.
  - `tarama1.csv` başlığı 25 sütunlu; sonradan eklenen bacak sütunları
    başlıksız. Okurken `tarama2.csv` başlığı kullanılmalı.
- `tani1.py` / `tani1.log`: olay bazlı akış katkısı (dev_train).
- `tani2.py` / `tani2.log`: yoğunlaşma, yön ve korelasyon (dev_train).
- `nedensellik.py` / `nedensellik.log`: `assert_causal` ve defter eşleşmesi.
- `dogrulama.py` / `dogrulama.log` / `dogrulama_sonuc.json`: tek seferlik
  dev_valid değerlendirmesi, `candidate_check`, DSR ve al-tut.
- `dogrulama_kenar.py` / `dogrulama_kenar.log`: işlem başına brüt kenar ve
  maliyet (betimleyici).
