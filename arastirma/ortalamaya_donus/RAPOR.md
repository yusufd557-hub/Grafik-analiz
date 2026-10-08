# Ortalamaya dönüş ailesi — araştırma raporu

Aile anahtarı: `ortalamaya_donus` · Protokol sürümü 1 · Kod:
`grafik_analiz/strategies/ortalamaya_donus.py` · Deney defteri:
`arastirma/deneyler/ortalamaya_donus.jsonl`

## Kısa sonuç

- **Saf ortalamaya dönüş (aşırı düşüşte al, aşırı yükselişte aç. sat) işe
  yaramadı.** 1 saatlik vadelide trend filtresi olmadan denenen 29
  yapılandırmanın hiçbiri dev_train'de kâr etmedi. İşlem başına **brüt** kenar
  (maliyet öncesi) çoğunlukla negatifti (medyan −%0,27). Yani sorun yalnız
  maliyet değil: bu zaman dilimlerinde aşırı hareketler kısa vadede çoğunlukla
  devam etti, geri dönmedi.
- **İşe yarayan tek varyant: yükselen trendde dip alımı (yalnız alım).**
  Kapanış 50 günlük SMA üstündeyken olağandışı sert bir düşüşten sonra alım.
  dev_train'de 91 varyantın 89'u net kârlıydı (medyan Sharpe 1,08). Aynı
  filtreyle düşen trendde rallileri açığa satmak ise zarar etti.
- 4 yapılandırma donduruldu ve dev_valid'de birer kez ölçüldü. **2'si aday
  şartlarını geçti**, 2'si 2× maliyette eksiye düştüğü için geçemedi:

| Yapılandırma | dev_valid 1× | dev_valid 2× | Sharpe | İşlem | Aday |
|---|---|---|---|---|---|
| `od_dip_ret4h_fut_port3_1h` | +%13,87 | +%10,42 | 1,09 | 66 | **geçti** |
| `od_dip_ens4_fut_port3_1h` | +%7,47 | +%4,08 | 0,86 | 140 | **geçti** |
| `od_dip_ens4_fut_port3_15m` | +%7,95 | −%1,17 | 0,64 | 400 | geçmedi |
| `od_dip_ens4_spot_port3_1h` | +%5,63 | −%0,14 | 0,64 | 144 | geçmedi |

- **Çekinceler:**
  - Deflated Sharpe çok düşük: 0,014–0,041. 169 deneme sayıldığında bu Sharpe
    değerleri şansla açıklanabilir.
  - dev_valid Sharpe'ı dev_train'in yaklaşık yarısına düştü.
  - Getirinin çoğu 2024'ün ilk yarısından geldi. 2025'in ilk yarısında dört
    yapılandırma da yaklaşık sıfırda kaldı.
  - Mutlak getiri al-tut'un çok altında: vadeli 3 coin portföyünde al-tut
    dev_valid'de +%51,8 getirdi.
  - Stratejiler zamanın yalnızca %4–29'unda pozisyondaydı ve en büyük düşüşleri
    %10'un altında kaldı.

  Bu iki aday, görülmemiş dönem için **zayıf** adaylardır.

## 1. Yöntem

- Veri yalnız `grafik_analiz.research.load(..., scope="dev")` ve
  `load_funding(..., scope="dev")` ile okundu. Holdout'a dokunulmadı.
- Bütün yapılandırmalar `evaluate(spec, windows=("dev_train",),
  cost_multipliers=(1.0,))` ile değerlendirildi; birkaçı ayrıca 2.0 ile.
  Hepsi deney defterine yazıldı. Arama sırasında dev_valid'e bakılmadı.
- Maliyetler protokoldeki gibidir: vadelide gidiş-dönüş %0,14 + fonlama,
  spotta %0,24. İşlem, sinyal barının ardından gelen barın açılışında yapılır.
- Ek tanılama:
  - `yillik.py` dev_train içinde yıllık döküm verir. Veri DEV_TRAIN_END'de
    kesildiği için dev_valid verisi sinyal hesabına bile girmez. Deftere
    yazılmaz, çünkü defterdeki aynı yapılandırmaların ayrıştırmasıdır.
  - `ortak.py`, `evaluate` çıktısından işlem başına brüt kenarı hesaplar:
    (ortalama net işlem × işlem sayısı + maliyet + fonlama) / işlem sayısı,
    bacak birimine çevrilmiş olarak.

### Sinyal yapısı

Her bacak için sapma ölçüsü (negatif değer aşırı satılmış demektir):

| `kind` | Tanım |
|---|---|
| `z` | (kapanış − SMA(n)) / std(n) |
| `vwap` | (kapanış − kayan VWAP(n)) / ATR(n) |
| `rsi` | (RSI(n) − 50) / 10 (giriş 3,5 → RSI < 15) |
| `ret` | n barlık log getiri / (hareketten önceki `vol_n` barlık bar oynaklığı × √n) |

Durum makinesinin kuralları:

- **Giriş:** skor ≤ −eşik ise alım, skor ≥ +eşik ise açığa satış.
- **Çıkış:** skor ortalamaya döner (skor ≥ −`exit`), `max_hold` bar dolar ya
  da isteğe bağlı ATR stop'u tetiklenir. `ret` ölçüsünde çıkış yalnızca süreye
  bağlıdır.
- **Rejim filtreleri:**
  - `trend_n`: kapanış SMA'nın üstündeyse yalnız alım, altındaysa yalnız açığa
    satış.
  - `trend2_n`: ikinci, daha uzun bir SMA filtresi.
  - `adx_max`: yatay piyasa filtresi.
  - `confirm`: dönüş mumu onayı.
- **Topluluk** (`components`): bileşen pozisyonlarının ortalamasıdır.
- **Pozisyon:** bacak başına 0 veya ±1. PORT3 portföyü BTC/ETH/SOL'u 1/3'er
  ağırlıkla taşır; kaldıraç yoktur.

## 2. Denenen yaklaşımlar ve parametre aralıkları (yalnız dev_train)

Toplam **165** dev_train değerlendirmesi yapıldı (1× maliyet). Bunlara bir
duman testi dahildir; bu test 1. aşamadaki bir yapılandırmanın tekrarıdır.
Benzersiz yapılandırma sayısı **164**'tür. Dondurulan 4 yapılandırmanın son
`evaluate(spec)` çağrısı deftere 4 tekrar satırı daha ekledi. Defterdeki dev_train 1× satır sayısı bu yüzden **169**'dur.

| Aşama | Betik | Ne | Yapılandırma | Net kârlı | Sharpe aralığı |
|---|---|---|---|---|---|
| 1 | `tarama1.py` | 1h vadeli PORT3, alım+açığa satış. z (n 20/50, eşik 2–3), vwap (n 24/72, eşik 2–4), rsi (n 6/14, eşik 2,5–3,5), ret (n 1/4, eşik 3–5); trend filtresi yok / 20 günlük | 48 | 10 | −1,69 … 0,52 |
| 2 | `tarama2.py` | Rejim: trend 5 / 50 gün, yalnız alım / yalnız açığa satış, ADX<20 | 25 | 11 | −1,23 … 1,26 |
| 3 | `tarama3.py` | 1h yalnız alım: filtresiz, 50 günlük filtre; `ret` ızgarası (n 1/4/8 × eşik 2,5/3/4 × tutma 6/24), vwap n 24/72/168, çıkış/tutma varyantları | 38 | 38 | 0,27 … 1,86 |
| 4 | `tarama4.py` | Aynı fikir: spot 1h (2017'den), vadeli 15m, vadeli 4h | 24 | 23 | −0,00 … 1,67 |
| 5 | `tarama5.py` | `ret` n4/eşik 3 çevresinde plato (trend 30/100 gün, n 2/6, eşik 2,5/3,5, tutma 6/24), coin bazında, ATR stop, mum onayı, 5m | 21 | 20 | 0,02 … 1,96 |
| 6 | `tarama6.py` | 4 bileşenli topluluk (1h vadeli/spot, 15m vadeli), 3 bileşenli `ret` topluluğu | 4 | 4 | 1,44 … 1,93 |
| 7 | `tarama7.py` | Topluluklara ve tek kurala 200 günlük ikinci trend filtresi | 4 | 4 | 1,19 … 2,02 |

Gruplara göre özet (164 benzersiz yapılandırma):

| Grup | Yapılandırma | Net kârlı | Medyan Sharpe | Medyan brüt kenar / işlem |
|---|---|---|---|---|
| İki yönlü, trend filtresiz (ADX dahil) | 29 | 0 | −0,89 | −%0,27 |
| Trend filtreli, iki yönlü veya yalnız açığa satış | 39 | 16 | −0,02 | +%0,14 |
| Yalnız alım, trend filtresiz | 5 | 5 | 0,37 | +%0,37 |
| Yalnız alım + yükselen trend filtresi | 91 | 89 | 1,08 | +%1,08 |

### Önemli dev_train bulguları

1. **Maliyet asıl engel değil; yön engel.** Filtresiz 1h z-skoru dönüşü
   (n=20, eşik 2,5) 2.442 işlemde işlem başına brüt **−%0,27** kaybetti.
   Net getirisi −%96,9 oldu. Eşik yükseldikçe brüt kenar daha da kötüleşti.
2. **Açığa satış tarafı zararlı.** 50 günlük trend filtresiyle beş temsilci
   kural yalnız açığa satışta çalıştırıldı. Beşi de zarar etti (Sharpe −0,46 …
   −0,26). Aynı kurallar yalnız alımda beşte beş kârlıydı (Sharpe 0,83 …
   1,26).
3. **ADX<20 (yatay piyasa) filtresi yardımcı olmadı.** Beş temsilci kuralın
   beşi de zarar etti (Sharpe −1,23 … −0,27).
4. **Yükselen trendde dip alımı geniş bir platoda pozitif.** Örnekler
   (vadeli, PORT3, 1h, yalnız alım):

| Kural | Trend | Getiri | Sharpe | MaxDD | İşlem | Brüt/işlem |
|---|---|---|---|---|---|---|
| ret n=4, eşik 3, 12 saat tut | 50 gün | +%147,0 | 1,86 | −%20,7 | 162 | %1,88 |
| ret n=4, eşik 3, 12 saat | 30 gün | +%137,1 | 1,85 | −%13,7 | 146 | %1,96 |
| ret n=4, eşik 3, 12 saat | 100 gün | +%123,7 | 1,57 | −%20,7 | 184 | %1,52 |
| ret n=2, eşik 3 | 50 gün | +%103,1 | 1,31 | −%27,8 | 223 | %1,18 |
| ret n=6, eşik 2,5 | 50 gün | +%123,2 | 1,59 | −%20,7 | 196 | %1,43 |
| ret n=1, eşik 4 | 50 gün | +%59,7 | 1,38 | −%13,7 | 138 | %1,16 |
| vwap n=72, eşik 3 | 50 gün | +%168,6 | 1,19 | −%31,2 | 271 | %1,33 |
| rsi n=6, eşik 3,5 | 50 gün | +%27,8 | 0,67 | −%18,7 | 278 | %0,41 |
| ret n=4, eşik 3 | yok | +%97,0 | 0,78 | −%42,4 | 376 | %0,76 |
| ret n=4, eşik 3, mum onayı | 50 gün | −%0,3 | 0,02 | −%17,3 | 55 | %0,20 |

5. **Coin bazında** (ret n=4, eşik 3, 50 gün):

| Coin | Sharpe | Getiri | İşlem |
|---|---|---|---|
| BTC | 0,96 | +%49,3 | 51 |
| ETH | 0,65 | +%44,7 | 74 |
| SOL | 1,77 | +%487,9 | 37 |

   SOL'un 2021 yükselişi sonucu ağırlıklı olarak taşıyor.
6. **Yıllara göre** (dev_train) bu kural:

| Yıl | Getiri |
|---|---|
| 2020 | +%7,7 |
| 2021 | +%86,4 |
| 2022 | +%4,5 |
| 2023 | +%17,8 |

   Spot sürümü 2017'den başlıyor. 2018'de −%1,1, 2019'da −%10,4 getirdi;
   o yıllarda yalnız BTC/ETH vardı. Kenar boğa piyasalarında yoğunlaşıyor.
7. **Topluluk ve 200 günlük filtre.** Dört bileşen birlikte kullanıldı: 4
   saatlik −3σ, 1 saatlik −4σ, VWAP(72) altı 3 ATR ve RSI(6)<15. Topluluk
   tek kurala göre getiriyi düzleştirdi ve MaxDD'yi %21'den %12–15'e indirdi.
   200 günlük ikinci filtre 2022'deki ayı piyasası rallilerinde alımı tamamen
   kapattı. Topluluğun 2022 sonucu −%7,8'den %0'a çıktı. Bu filtre
   dev_train'deki 2022 kaybı görüldükten sonra eklendi; seçim yine dev_train
   içindedir.

## 3. Dondurulan yapılandırmalar ve gerekçe

Arama bitince (165 dev_train değerlendirmesi) aşağıdaki 4 yapılandırma
donduruldu. Seçim yalnız dev_train sonuçlarına dayanıyor. En yüksek Sharpe'ı
seçmek yerine şunlar gözetildi: plato ortasında olmak, sade kural ve
piyasa/zaman dilimi çeşitliliği.

1. `od_dip_ens4_fut_port3_1h`: vadeli 1h, 4 bileşenli topluluk, 50 + 200
   günlük filtre. dev_train'de en yüksek Sharpe (2,02) ve en düşük düşüş
   (−%12,5) bunda. Topluluk, tek eşiğe bağımlılığı azaltır.
2. `od_dip_ens4_fut_port3_15m`: aynı topluluğun 15 dakikalık karşılığı.
   Zaman dilimi dayanıklılığını ve daha çok işlemi sınar.
3. `od_dip_ret4h_fut_port3_1h`: en sade tek kural (4 saatlik −3σ düşüş,
   50 günlük filtre, 12 saat tut). Plato komşularının hepsi kârlıydı:
   trend uzunluğu ve tutma süresi komşularında Sharpe 1,25–1,85, n ve eşik
   komşularında 0,81–1,63.
4. `od_dip_ens4_spot_port3_1h`: 1 numaranın spotta, %0,24 maliyetle
   çalıştırılması. Spot, dev_train'de 2018–2019'u da kapsadığı için ek bir
   sınama sağlar.

5m varyantı dondurulmadı. dev_train Sharpe'ı 1,96 idi ama 2022'de −%5,2
verdi ve 15m/1h sürümleriyle neredeyse aynı fikirdir.

## 4. dev_valid sonuçları (her yapılandırma tek kez, `evaluate(spec)`)

`assert_causal` dört yapılandırmada da geçti.

| Yapılandırma | Pencere | Getiri 1× | Getiri 2× | Sharpe 1× | Sharpe 2× | MaxDD 1× | İşlem | Kazanma | Pozisyonda | En iyi işlem hariç | Bootstrap p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ens4 vadeli 1h | dev_train | +%74,50 | +%63,06 | 2,02 | 1,78 | −%12,51 | 317 | %78,6 | %13,5 | +%69,6 | 0,0000 |
| | **dev_valid** | **+%7,47** | **+%4,08** | **0,86** | 0,49 | −%4,50 | 140 | %65,7 | %19,7 | +%4,9 | 0,133 |
| ens4 vadeli 15m | dev_train | +%95,41 | +%62,23 | 1,84 | 1,34 | −%17,52 | 820 | %76,5 | %21,6 | +%86,9 | 0,0002 |
| | **dev_valid** | **+%7,95** | **−%1,17** | **0,64** | −0,05 | −%9,92 | 400 | %73,8 | %29,3 | +%6,4 | 0,221 |
| ret4h vadeli 1h | dev_train | +%147,05 | +%129,09 | 1,86 | 1,73 | −%20,74 | 162 | %64,8 | %3,8 | +%126,4 | 0,0002 |
| | **dev_valid** | **+%13,87** | **+%10,42** | **1,09** | 0,85 | −%5,56 | 66 | %59,1 | %4,1 | +%9,7 | 0,072 |
| ens4 spot 1h | dev_train | +%59,47 | +%35,66 | 1,19 | 0,79 | −%10,88 | 432 | %72,7 | %12,5 | +%55,0 | 0,0004 |
| | **dev_valid** | **+%5,63** | **−%0,14** | **0,64** | 0,01 | −%5,02 | 144 | %65,3 | %19,8 | +%3,4 | 0,193 |

### candidate_check

| Yapılandırma | Eğitim > 0 | Doğrulama > 0 | 2× > 0 | Sharpe ≥ 0,5 | ≥ 20 işlem | **Aday** |
|---|---|---|---|---|---|---|
| od_dip_ens4_fut_port3_1h | ✓ | ✓ | ✓ | ✓ (0,86) | ✓ (140) | **evet** |
| od_dip_ens4_fut_port3_15m | ✓ | ✓ | ✗ (−%1,17) | ✓ (0,64) | ✓ (400) | hayır |
| od_dip_ret4h_fut_port3_1h | ✓ | ✓ | ✓ | ✓ (1,09) | ✓ (66) | **evet** |
| od_dip_ens4_spot_port3_1h | ✓ | ✓ | ✗ (−%0,14) | ✓ (0,64) | ✓ (144) | hayır |

### Deflated Sharpe (Bailey & López de Prado)

Girdiler:

- **Deneme sayısı (N):** `ledger.trials("ortalamaya_donus")` içinde
  pencere == dev_train ve maliyet_kat == 1.0 olan satırlar, yani **169**.
  Bunlardan 164'ü benzersizdir; 164 ile sonuç pratikte değişmez.
- **Varyans:** Bu satırların yıllık Sharpe varyansı **0,7886**'dır (std 0,89).
  Bu varyansla 169 denemede şansla beklenen en yüksek yıllık Sharpe yaklaşık
  **2,41**'dir.
- **Çarpıklık ve basıklık:** dev_valid günlük getirilerinden alındı; gün
  sayısı 547.

| Yapılandırma | dev_valid Sharpe | Çarpıklık | Basıklık | **DSR** |
|---|---|---|---|---|
| od_dip_ens4_fut_port3_1h | 0,86 | 1,58 | 28,4 | **0,026** |
| od_dip_ens4_fut_port3_15m | 0,64 | 1,32 | 31,0 | **0,014** |
| od_dip_ret4h_fut_port3_1h | 1,09 | 3,43 | 60,5 | **0,041** |
| od_dip_ens4_spot_port3_1h | 0,64 | 1,40 | 29,9 | **0,014** |

DSR değerlerinin hepsi 0,05'in altındadır. Çoklu deneme düzeltmesinden sonra
dev_valid Sharpe'ları istatistiksel olarak anlamlı değildir.

Varyansı büyüten etken, 1. aşamadaki çok negatif saf dönüş denemeleridir.
Bunlar da gerçek denemelerdir ve sayılmaları gerekir.

## 5. Al-tut karşılaştırması (aynı pencereler, 1× maliyet, deftere yazılmadı)

| Al-tut | dev_train getiri | dev_train Sharpe | dev_train MaxDD | dev_valid getiri | dev_valid Sharpe | dev_valid MaxDD |
|---|---|---|---|---|---|---|
| Vadeli PORT3 (2020-01'den) | +%1.593,9 | 1,29 | −%86,3 | +%51,8 | 0,75 | −%52,3 |
| Vadeli BTC | +%223,9 | 0,78 | −%79,2 | +%119,7 | 1,28 | −%35,2 |
| Vadeli ETH | +%745,3 | 1,06 | −%81,9 | −%6,7 | 0,28 | −%68,6 |
| Vadeli SOL (2020-09'dan) | +%3.312,0 | 1,45 | −%96,0 | +%32,7 | 0,65 | −%65,9 |
| Spot PORT3 (2017-08'den) | +%3.860,9 | 1,17 | −%86,1 | +%75,4 | 0,91 | −%52,1 |

Stratejilerin mutlak getirisi al-tut'un çok altındadır. dev_valid'de
pozisyonda kalma oranları %4 (tek kural) ile %29 (15m topluluk) arasındadır.
En büyük düşüşleri %4,5–9,9 iken al-tut'unki ~%52'dir.

Risk ayarlı ölçüye bakıldığında:

- Tek kuralın Sharpe'ı (1,09) vadeli PORT3 al-tut'unkinden (0,75) yüksektir.
- 1h topluluğun Sharpe'ı (0,86) da al-tut'tan yüksektir.
- 15m ve spot sürümleri (0,64) al-tut'un altındadır.

## 6. Tanılama (dev_valid ölçümünden SONRA; hiçbir parametre değişmedi)

`tanilama.py` (çıktısı `tanilama.txt`) dönem bazında getirileri verir:

| Yapılandırma | 2024 1. yarı | 2024 2. yarı | 2025 1. yarı |
|---|---|---|---|
| ens4 vadeli 1h | +%6,7 | %0,0 | +%0,7 |
| ens4 vadeli 15m | +%9,0 | −%0,9 | %0,0 |
| ret4h vadeli 1h | +%8,5 | +%5,1 | −%0,1 |
| ens4 spot 1h | +%4,4 | −%0,5 | +%1,7 |

Kenar zaman içinde zayıfladı. dev_valid getirisinin çoğu 2024'ün güçlü
ilk yarısından geldi.

İşlem başına brüt kenar (bacak birimi) dev_train'e göre küçüldü:

| Yapılandırma | dev_train | dev_valid |
|---|---|---|
| Tek kural, BTC | %1,03 | %0,88 |
| Tek kural, ETH | %0,75 | %0,71 |
| Tek kural, SOL | %5,32 | %0,55 |
| 1h topluluk, ortalama | %0,34–1,40 | %0,19–0,31 |

1h topluluğun dev_valid'deki brüt kenarı vadeli gidiş-dönüş maliyetinin
(%0,14) yalnızca 1,4–2,2 katıdır. 15m topluluğunda brüt kenar coin başına
%0,05–0,18'e, spot toplulukta %0,13–0,36'ya indi (spot gidiş-dönüş maliyeti
%0,24). Bu iki sürümün 2× maliyette eksiye düşmesinin nedeni budur.
Topluluklarda pozisyon kesirli olduğu için bu işlem başına değerler
yaklaşıktır (bkz. 9. bölüm).

dev_train'deki SOL katkısı (2021) dev_valid'de tekrarlanmadı. dev_valid
getirisi üç coine daha dengeli dağıldı.

## 7. Dürüst değerlendirme

- **Saf kısa vadeli ortalamaya dönüş:** 5m–4h aralığında, Binance standart
  maliyetleriyle bu veride kârlı bir saf dönüş stratejisi bulunamadı. Brüt
  kenar bile negatifti.
- **İki aday var:** Bulunan tek kenar "yükselen trendde sert düşüşü almak"tır.
  Bu, trend takibi ile dönüşün karışımıdır. Bu kenarla iki yapılandırma
  protokolün aday şartlarını geçti: `od_dip_ret4h_fut_port3_1h` ve
  `od_dip_ens4_fut_port3_1h`.
- **Kanıt zayıf:**
  - DSR 0,03–0,04 civarında.
  - Bootstrap p-değerleri 0,07 ve 0,13.
  - dev_valid Sharpe'ı dev_train'in yarısına indi.
  - 2025'in ilk yarısında getiri sıfıra yakın.
  - Kenar boğa rejimine bağımlı. Spot dev_train'de 2018–2019'da sıfır ya da
    negatifti.
- **Holdout beklentisi:** Görülmemiş dönemde Seviye 1'i geçme ihtimali
  belirsiz, Seviye 2'yi (istatistiksel anlamlılık) geçmesi olası
  görünmüyor.
- **Mutlak getiri:** Strateji zamanın büyük kısmında nakitte durur. Mutlak
  getiri bakımından al-tut'u yenmez. Değeri, düşük düşüş ve düşük piyasa
  maruziyetidir.
- **Bilgi çekincesi:** Araştırmacı (model) 2024–2025 kripto piyasasının genel
  seyrini eğitim bilgisinden biliyor olabilir. Yalnız alım yönü dev_train
  kanıtına dayanarak seçildi: açığa satış tarafı dev_train'de beşte beş zarar
  etti. Yine de bu genel bilginin etkisi tamamen dışlanamaz.

## 8. Dosyalar ve yeniden üretim

- `grafik_analiz/strategies/ortalamaya_donus.py`: sinyal kodu ve `specs()`.
  `specs()` dondurulan 4 yapılandırmayı döndürür.
- `ortak.py`: arama yardımcıları.
- `tarama1.py` … `tarama7.py` ve `tarama*.csv`: dev_train araması.
- `yillik.py`: dev_train içi yıllık döküm; veri DEV_TRAIN_END'de kesilir.
- `dogrulama.py`: tek seferlik dev_valid değerlendirmesi, al-tut ve DSR.
  Çıktıları `dondurulmus_sonuclar.json` ve `.pkl` dosyalarıdır.
- `yeniden_uretim.py`: `specs()`'in sonuçları birebir ürettiğini doğrular.
  `record=False` ile çalışır; dört yapılandırma da doğrulandı.
- `tanilama.py` ve `tanilama.txt`: dev_valid sonrası tanılama.

## 9. Altyapı notları

- `backtest._trades`, bir işlem diliminin net getirisinden yalnız giriş ve
  çıkış maliyetini düşer. Dilim içindeki boyut değişikliklerinin maliyeti
  işlem bazında düşülmez. Topluluk stratejilerinde pozisyon 0,25'lik
  adımlarla değişir; bu yüzden işlem bazlı ölçüler (`avg_trade`, `win_rate`,
  `total_without_best`) maliyeti eksik sayar. `od_dip_ens4_fut_port3_1h`
  dev_train'de seri bazlı maliyet 0,0678, işlemlere dağıtılan maliyet 0,0444
  çıktı. Toplam getiri, Sharpe ve MaxDD bundan etkilenmez; bunlar bar
  serisinden hesaplanır.
- Son `evaluate(spec)` çağrısı dev_train 1× satırını yeniden yazar. Bu da
  DSR'deki deneme sayısını tekrarlarla şişirir (burada 164 yerine 169).
