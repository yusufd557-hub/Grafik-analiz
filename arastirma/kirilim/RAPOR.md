# Kırılım ve oynaklık ailesi (`kirilim`) — araştırma raporu

Protokol: [`docs/PROTOKOL.md`](../../docs/PROTOKOL.md), sürüm 1. Bütün sayılar
harness'ten (`grafik_analiz.research.evaluate`, `run`, `summarize`) alınmıştır.
Getiriler net (komisyon + kayma, vadelide fonlama dahil), oran olarak verilir
(0,48 = %48). Görülmemiş döneme (1 Temmuz 2025 sonrası) hiç erişilmedi.

## Kısa sonuç

- 348 farklı yapılandırma dev_train'de denendi; defterde 351 dev_train satırı
  var (dondurulan 3'ün son değerlendirmesi dahil). dev_valid'e yalnız **3 dondurulmuş yapılandırma** ile,
  her biri **bir kez** bakıldı.
- 15m ve 1h'deki kırılım yöntemleri (sıkışma, NR, günlük açılış aralığı,
  Williams, kısa kanal) maliyetten sonra ya zarar etti ya da 2× maliyette
  çöktü. Tek sağlam bölge **4h Donchian kanal kırılımı + hacim teyidi + geniş
  ATR iz süren stop** oldu.
- Dondurulan 3 yapılandırmadan **2'si aday şartlarını geçti** (spot yalnız alım
  ve vadeli yalnız alım; dev_valid'de 1× maliyetle +%47,6 / +%47,4, 2× maliyetle
  +%42,1 / +%44,3, Sharpe 1,13 / 1,13, en büyük düşüş −%14,2 / −%15,2).
  Vadeli alım + açığa satış sürümü geçemedi (Sharpe 0,29).
- **Ancak:** geçen iki yapılandırma aynı kuralın iki piyasadaki kopyasıdır
  (günlük getiri korelasyonu 0,99). Çoklu deneme düzeltmeli Deflated Sharpe
  ≈ 0,01'dir (anlamlı değil); dev_valid blok bootstrap p ≈ 0,09'dur. dev_valid
  kârının neredeyse tamamı 2024'ten gelir; 2025'in ilk yarısı yaklaşık sıfırdır.
  Al-tut'tan daha az getiri, daha yüksek Sharpe ve çok daha küçük düşüş
  vermiştir. Bu, "kesin kârlı bir sistem" kanıtı değil, görülmemiş dönemde
  test edilmeye değer bir aday düzeyidir.

## 1. Denenen yaklaşımlar

Kod: [`grafik_analiz/strategies/kirilim.py`](../../grafik_analiz/strategies/kirilim.py).
Bütün sinyaller t barının kapanışında yalnız t ve önceki verilerle hesaplanır
(geriye dönük pencereler, `shift(+k)`, önceki tamamlanmış gün değerleri, baştan
ileri yürüyen durum makinesi). İşlem bir sonraki barın açılışında yapılır.
Spotta yalnız alım; vadelide `yon="iki"` alım + açığa satış, `yon="uzun"` yalnız
alım. Varsayılan evren PORT3: BTC/ETH/SOL eşit sermaye ağırlığı (1/3), coin henüz
listelenmemişse o pay nakitte.

| Yöntem | Giriş | Çıkış seçenekleri |
|---|---|---|
| `kanal` | Kapanış > önceki `n` barın en yükseği (açığa satış: < en düşüğü); isteğe bağlı hacim > `hacim_k` × önceki `n` bar ort. hacmi | `n_cikis` çıkış kanalı; ATR(14) × `atr_k` iz süren stop (pozisyon içindeki en uç fiyattan) |
| `sikisma` | Bollinger(20, 2) Keltner(20, `kc_k`×ATR) içinde en az `min_sik` bar; sıkışma son 3 bar içinde bittiyse kapanış üst/alt bandın dışına çıkınca | Orta banda dönüş veya ATR iz |
| `nr` | Önceki bar son `nr_n` barın en dar aralıklısı (NR4/NR7) ve kapanış onun en yükseği/en düşüğü dışında | `max_bar` zaman stopu veya ATR iz |
| `acilis` | 00:00 UTC'den sonraki ilk `or_saat` saatin aralığı; aralık bitince kapanış aralık dışına çıkınca (günde yön başına en çok 1 giriş); isteğe bağlı dar aralık filtresi (aralık ≤ 0,5 × önceki günlerin günlük ATR'si) | Gün sonu (son barın kapanışında kapat); isteğe bağlı karşı uç stopu |
| `williams` | Gün açılışı ± `k` × önceki günün aralığı kapanışla geçilince | Gün sonu; isteğe bağlı gün açılışına dönüş stopu |

Ortak filtreler: trend (kapanış `trend_n` barlık EMA'nın doğru tarafında),
oynaklık rejimi (ATR/fiyat'ın son `rejim_n` bar içindeki yüzdelik sırası
`vol_alt`…`vol_ust` arasında).

## 2. Arama süreci ve parametre aralıkları (yalnız dev_train)

dev_train: verinin başı – 31.12.2023 (spot 4h/1h/1d 17.08.2017'den, spot 15m
2019'dan; vadeli 2020'den; SOL 2020-08/09'dan). Her yapılandırma
`evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))` ile
değerlendirildi; aynı yapılandırma iki kez denenmedi. Ara tanılar (yıl, bacak,
yön) defterde zaten kayıtlı yapılandırmalar için `run()` ile hesaplandı ve
seriler hesaplamadan önce 2024-01-01 öncesine kesildi. Çalışma notları ve her
aşamanın sonrasında (dev_valid görülmeden) yazılan kararlar:
[`NOTLAR.md`](NOTLAR.md).

| Aşama | Betik | Yapılandırma | İçerik |
|---|---|---|---|
| 1 | `tarama1.py` | 144 | 5 yöntem × 15m/1h/4h/1d × spot/vadeli PORT3, ders kitabı değerleri: kanal n ∈ {20, 60}, çıkış {n/2 kanal, 3×ATR}, hacim_k ∈ {0, 1,5}; sıkışma min_sik ∈ {4, 12}, çıkış {orta, 2,5×ATR}; NR ∈ {4, 7}, çıkış {6 bar, 3×ATR}; açılış aralığı 1/2/4 saat, stop {yok, karşı uç}, dar aralık filtresi {yok, 0,5}; Williams k ∈ {0,3, 0,5, 0,7}, stop {yok, açılış} |
| 2 | `tarama2.py` | 179 yeni | 4h kanal yüzeyi n ∈ {30, 45, 60, 90, 120} × atr_k ∈ {2, 3, 4} × hacim_k ∈ {0, 1,25, 1,5, 2} (spot ve vadeli iki yön); vadeli yalnız alım; oynaklık rejimi (vol_ust 0,5/0,8, vol_alt 0,2/0,5) ve trend filtresi (EMA 200/600); 1d kanal n ∈ {10, 20, 40}; 4h/1h sıkışma + geniş ATR; Williams + trend filtresi; 1d NR7 |
| 3 | `tarama3.py` | 25 | atr_k ∈ {5, 6} (ızgara sınırı kontrolü), vol_ust eşik (0,7/0,8/0,9) ve rejim_n (540/1080/2160) duyarlılığı, vadeli yalnız alım + atr_k=4 |
| Son | `dogrulama.py` | 3 | Dondurulanların tek seferlik dev_train + dev_valid değerlendirmesi |

Deney defteri `arastirma/deneyler/kirilim.jsonl`: 351 satır dev_train 1×,
351 dev_train 2×, 3 dev_valid 1×, 3 dev_valid 2×. Bütün arama satırları
`tarama_sonuclari.jsonl` dosyasında da var.

### 2.1 Yöntem bazında dev_train özeti (348 arama yapılandırması)

Sharpe: günlük net getiriden yıllık. "Poz. 1×/2×": net getirisi pozitif olan
yapılandırma oranı.

| Yöntem | Aralık | Yön | Sayı | Medyan Sharpe | En iyi Sharpe | Poz. 1× | Poz. 2× | Medyan işlem |
|---|---|---|---|---|---|---|---|---|
| kanal | 15m | spot | 8 | −1,38 | 0,15 | 0,00 | 0,00 | 4583 |
| kanal | 15m | vadeli iki | 8 | −2,49 | −0,44 | 0,00 | 0,00 | 7777 |
| kanal | 1h | spot | 8 | 0,61 | 1,17 | 1,00 | 0,50 | 1329 |
| kanal | 1h | vadeli iki | 8 | −0,21 | 0,46 | 0,12 | 0,00 | 1886 |
| kanal | 4h | spot | 81 | 1,51 | 1,96 | 1,00 | 1,00 | 214 |
| kanal | 4h | vadeli iki | 86 | 0,97 | 1,47 | 0,97 | 0,91 | 262 |
| kanal | 4h | vadeli uzun | 12 | 1,28 | 1,84 | 1,00 | 1,00 | 164 |
| kanal | 1d | spot | 6 | 1,65 | 1,77 | 1,00 | 1,00 | 66 |
| kanal | 1d | vadeli iki | 6 | 0,90 | 0,97 | 1,00 | 1,00 | 93 |
| sikisma | 15m | spot / vadeli | 4 / 4 | −1,93 / −2,68 | −1,43 / −2,04 | 0 / 0 | 0 / 0 | 2968 / 5367 |
| sikisma | 1h | spot | 7 | 0,83 | 1,03 | 1,00 | 0,57 | 584 |
| sikisma | 1h | vadeli iki | 4 | 0,04 | 0,35 | 0,50 | 0,00 | 1352 |
| sikisma | 4h | spot | 12 | 0,80 | 1,03 | 1,00 | 1,00 | 216 |
| sikisma | 4h | vadeli iki | 12 | 0,10 | 0,38 | 0,50 | 0,42 | 307 |
| nr | 1h | spot / vadeli | 4 / 4 | −1,11 / −1,47 | 0,20 / −0,78 | 0 / 0 | 0 / 0 | 4384 / 4859 |
| nr | 4h | spot | 4 | 0,63 | 0,96 | 0,75 | 0,50 | 1067 |
| nr | 4h | vadeli iki | 4 | −0,82 | 0,14 | 0,00 | 0,00 | 1177 |
| nr | 1d | spot | 6 | 0,93 | 1,19 | 1,00 | 0,83 | 155 |
| nr | 1d | vadeli iki | 6 | 0,99 | 1,18 | 0,67 | 0,67 | 152 |
| acilis | 15m | spot | 12 | 0,47 | 0,60 | 0,83 | 0,00 | 3283 |
| acilis | 15m | vadeli iki | 12 | −0,54 | −0,06 | 0,00 | 0,00 | 4153 |
| williams | 15m | spot | 6 | 1,00 | 1,28 | 1,00 | 0,50 | 1701 |
| williams | 15m | vadeli iki | 6 | 0,19 | 0,32 | 0,50 | 0,00 | 2727 |
| williams | 1h | spot | 12 | 1,13 | 1,30 | 1,00 | 0,83 | 1298 |
| williams | 1h | vadeli iki | 6 | 0,37 | 0,52 | 0,67 | 0,00 | 2446 |

Okuma notları:

- dev_train'de al-tut çok güçlüydü (spot PORT3 4h net getiri +35,1 yani
  %3.514, Sharpe 1,15; vadeli PORT3 +15,1 yani %1.514, Sharpe 1,28). Bu yüzden spotta (yalnız alım) 1×
  maliyette pozitif sonuç kendi başına zayıf bir kanıttır; vadeli iki yön ve
  2× maliyet sütunu daha ayırt edicidir.
- 15m'de bütün yöntemler maliyetle eridi (dev_train boyunca toplam maliyet
  çoğunlukla sermayenin 1,5–5 katı). Günlük açılış aralığı (ORB) ve Williams
  vadelide iki yönde hiçbir yapılandırmada 2× maliyete dayanmadı. Spotta açılış
  aralığı 2× maliyette hep zarar; Williams spotta 2× maliyette çoğunlukla
  pozitif kaldı ama 2× Sharpe en çok 0,55 (incelenen k=0,7 örneğinde 2022'de
  zarar; kâr büyük ölçüde yalnız alım betası).
- 1h sıkışma (spot) 1× Sharpe 1,03 ama 2× maliyette 2023 negatif; dondurulmadı.
- Oynaklık rejimi filtresi: vadeli 4h kanal (n=60, atr_k=3) için `vol_ust=0,8`
  Sharpe'ı 1,01'den 1,31'e çıkardı, ama düzlük merkezinde (n=90, atr_k=4)
  0,7/0,8/0,9 eşikleri 1,00/1,25/1,11 verdi (filtresiz 1,26) ve `rejim_n=2160`
  ile 0,64'e düştü → kararsız, elendi. Trend filtresi (EMA 200/600) spotta
  Sharpe'ı düşürdü (1,54 → 1,53 / 1,40), vadelide çok az değiştirdi
  (1,01 → 1,05 / 1,07); eklenmedi.

### 2.2 4h kanal yüzeyi (dev_train Sharpe 1×, hacim_k = 1,25)

| n | atr_k=2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|
| Spot 30 | 0,97 | 1,47 | 1,73 | – | – |
| Spot 45 | 0,87 | 1,43 | 1,59 | – | – |
| Spot 60 | 1,02 | 1,58 | 1,68 | 1,75 | 1,60 |
| **Spot 90** | 0,81 | 1,49 | **1,69** | – | – |
| Spot 120 | 0,93 | 1,56 | 1,78 | 1,96 | 1,89 |
| Vadeli iki 30 | 0,20 | 0,89 | 1,11 | – | – |
| Vadeli iki 45 | 0,43 | 0,98 | 1,14 | – | – |
| Vadeli iki 60 | 0,55 | 1,07 | 1,22 | 1,30 | 1,10 |
| **Vadeli iki 90** | 0,59 | 1,13 | **1,26** | – | – |
| Vadeli iki 120 | 0,66 | 1,23 | 1,31 | 1,47 | 1,37 |

Hacim teyidinin etkisi (n=90, atr_k=4; hacim_k 0 / 1,25 / 1,5 / 2): spot
1,55 / 1,69 / 1,73 / 1,54; vadeli iki 1,14 / 1,26 / 1,16 / 1,08. Vadeli yalnız
alım (atr_k=4, hacim_k=1,25): n=60 1,84, n=90 1,81. Yüzey düzgün; tepe
atr_k ≈ 4–5 civarında, ızgaranın içinde.

### 2.3 Dondurulanların dev_train yıllık tanısı (1× maliyet, getiri / Sharpe)

| Yapılandırma | 2017* | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|
| Spot | +0,33 / 2,46 | +0,12 / 0,63 | +0,36 / 1,31 | +0,78 / 2,15 | +2,77 / 2,80 | −0,14 / −0,79 | +0,99 / 2,17 |
| Vadeli iki | – | – | – | +0,86 / 1,49 | +1,34 / 1,78 | +0,12 / 0,50 | +0,74 / 1,70 |
| Vadeli uzun | – | – | – | +0,62 / 1,98 | +2,70 / 2,77 | −0,14 / −0,73 | +0,91 / 2,07 |

\* 2017: 17 Ağustos'tan itibaren. Bacak bazında (dev_train, 1×) üç coin de her
üç yapılandırmada pozitif. Vadeli iki yönde açığa satış işlemlerinin
portföy ağırlıklı net toplamı −0,13 (90 işlem); kârın tamamı alım tarafından,
açığa satış yalnız 2022'de dengeleyici.

## 3. Dondurulan yapılandırmalar ve gerekçe

Üçü de aynı kural: **4h, Donchian(90) kırılımı, hacim > 1,25 × önceki 90 bar
ortalaması, en uç fiyattan 4 × ATR(14) geri çekilince çıkış, BTC/ETH/SOL eşit
ağırlık.**

| Ad | Piyasa | Yön | Parametreler |
|---|---|---|---|
| `kirilim_kanal4h_spot` | spot | yalnız alım | `{"yontem": "kanal", "n": 90, "atr_n": 14, "atr_k": 4.0, "hacim_k": 1.25}` |
| `kirilim_kanal4h_vadeli_iki` | vadeli | alım + açığa satış | aynı |
| `kirilim_kanal4h_vadeli_uzun` | vadeli | yalnız alım | aynı + `"yon": "uzun"` |

Gerekçe (dev_valid görülmeden `NOTLAR.md` EK 3'te yazıldı): yüzeyin en yüksek
noktası değil, düz bölgenin ortası seçildi (n=90 ve atr_k=4'ün bütün komşuları
pozitif ve 2× maliyette kârlı); dev_train'de her coin pozitif; yıllar çoğunlukla
pozitif. Üç yapılandırma, açığa satış tarafının ve piyasa (spot/vadeli)
farkının dev_valid'de değer katıp katmadığını ayırmak için seçildi. Diğer
yöntemlerde 2× maliyete dayanıklı bir bölge bulunmadığından dondurulmadı. 5
hakkın yalnız 3'ü kullanıldı. `assert_causal` (varsayılan kesimler ve ek olarak
0,3/0,5/0,71/0,9/0,999) üçünde de geçti (`nedensellik.py`).

## 4. dev_valid sonuçları (01.01.2024 – 30.06.2025, tek değerlendirme)

| Yapılandırma | Pencere | Maliyet | Net getiri | Sharpe | En büyük düşüş | İşlem | Bootstrap p |
|---|---|---|---|---|---|---|---|
| Spot | dev_train | 1× | +21,99 | 1,691 | −0,293 | 158 | 0,000 |
| Spot | dev_train | 2× | +19,26 | 1,628 | −0,304 | 158 | 0,000 |
| Spot | **dev_valid** | **1×** | **+0,476** | **1,127** | **−0,142** | **47** | 0,087 |
| Spot | **dev_valid** | **2×** | **+0,421** | 1,029 | −0,148 | 47 | 0,108 |
| Vadeli iki | dev_train | 1× | +7,51 | 1,263 | −0,401 | 198 | 0,003 |
| Vadeli iki | dev_train | 2× | +6,76 | 1,219 | −0,410 | 198 | 0,004 |
| Vadeli iki | **dev_valid** | **1×** | **+0,060** | **0,285** | **−0,262** | **89** | 0,353 |
| Vadeli iki | **dev_valid** | **2×** | **+0,017** | 0,206 | −0,284 | 89 | 0,393 |
| Vadeli uzun | dev_train | 1× | +8,90 | 1,809 | −0,281 | 108 | 0,000 |
| Vadeli uzun | dev_train | 2× | +8,41 | 1,772 | −0,289 | 108 | 0,000 |
| Vadeli uzun | **dev_valid** | **1×** | **+0,474** | **1,130** | **−0,152** | **45** | 0,089 |
| Vadeli uzun | **dev_valid** | **2×** | **+0,443** | 1,075 | −0,157 | 45 | 0,099 |

### candidate_check

| Şart | Spot | Vadeli iki | Vadeli uzun |
|---|---|---|---|
| dev_train net > 0 | ✓ | ✓ | ✓ |
| dev_valid net > 0 | ✓ | ✓ | ✓ |
| dev_valid 2× maliyette net > 0 | ✓ | ✓ | ✓ |
| dev_valid Sharpe ≥ 0,5 | ✓ (1,13) | ✗ (0,29) | ✓ (1,13) |
| dev_valid ≥ 20 işlem | ✓ (47) | ✓ (89) | ✓ (45) |
| **Aday** | **EVET** | **HAYIR** | **EVET** |

### Deflated Sharpe (Bailey & López de Prado)

Resmi hesap (görevde tanımlandığı gibi): deneme sayısı = defterde
`pencere=="dev_train"` ve `maliyet_kat==1.0` satırları = **351**; bu
satırların yıllık Sharpe varyansı = **1,016**; dev_valid günlük getiri sayısı
547; çarpıklık/basıklık dev_valid günlük getirilerinden (`summarize`).

| Yapılandırma | dev_valid Sharpe | Çarpıklık | Basıklık | **DSR** |
|---|---|---|---|---|
| Spot | 1,127 | 1,383 | 13,38 | **0,0098** |
| Vadeli iki | 0,285 | 0,362 | 10,38 | **0,0005** |
| Vadeli uzun | 1,130 | 1,560 | 13,52 | **0,0095** |

DSR ≈ 0,01: 351 denemenin en iyisinin şansla bu Sharpe'a ulaşması olasılığı
dışlanamıyor. Duyarlılık (resmi değil, yalnız bilgi): deneme Sharpe varyansı
15m'deki çok kötü denemeler yüzünden şişkin; varyans yalnız 4h kanal
denemelerinden alınırsa (0,176) DSR spot 0,445, vadeli uzun 0,446, vadeli iki
0,122 olur (deneme sayısı da 182'ye indirilirse 0,489 / 0,491 / 0,145). Her iki
hesapta da 0,95 eşiğinin çok altında.

## 5. Al-tut karşılaştırması (aynı pencereler, 4h veri, 1× maliyet)

| Pencere | Piyasa | BTC | ETH | SOL | PORT3 (Sharpe, MDD) |
|---|---|---|---|---|---|
| dev_train | spot | +8,75 | +6,40 | +33,30 | +35,14 (1,15, −0,86) |
| dev_train | vadeli | +2,21 | +7,36 | +32,83 | +15,14 (1,28, −0,86) |
| dev_valid | spot | +1,534 | +0,089 | +0,522 | **+0,743 (0,90, −0,515)** |
| dev_valid | vadeli | +1,197 | −0,067 | +0,327 | **+0,508 (0,75, −0,521)** |

dev_valid'de spot strateji al-tut'un getirisinin altında (+0,476'ya karşı
+0,743) ama Sharpe'ı daha yüksek (1,13'e karşı 0,90) ve düşüşü çok daha küçük
(−0,142'ye karşı −0,515). Vadeli yalnız alım, vadeli al-tut ile yaklaşık aynı
getiriyi (+0,474'e karşı +0,508) üçte bir düşüşle verdi. dev_train'de de durum
benzer: al-tut daha çok kazandırdı, strateji daha iyi risk/getiri verdi.

## 6. Dondurma sonrası tanılar (seçimi değiştirmez; `dogrulama_tani.py`)

| | Spot | Vadeli iki | Vadeli uzun |
|---|---|---|---|
| 2024 getiri / Sharpe | +0,485 / 1,61 | +0,236 / 0,82 | +0,441 / 1,50 |
| 2025 (6 ay) getiri / Sharpe | −0,006 / 0,07 | −0,142 / −0,58 | +0,023 / 0,31 |
| Bacak BTC / ETH / SOL getiri | +0,34 / +0,59 / +0,35 | −0,11 / +0,63 / −0,33 | +0,26 / +0,70 / +0,34 |
| Piyasada kalma oranı | 0,42 | 0,62 | 0,42 |
| Kazanma oranı / kâr faktörü | 0,47 / 2,03 | 0,35 / 1,14 | 0,49 / 2,11 |
| En iyi işlem çıkınca getiri | +0,283 | −0,084 | +0,273 |
| Toplam maliyet / fonlama | 0,038 / 0 | 0,042 / 0,054 | 0,021 / 0,062 |
| Al-tut ile günlük korelasyon / beta | 0,56 / 0,23 | 0,07 / 0,04 | 0,56 / 0,23 |

- Vadeli iki yönde açığa satış işlemleri (44) portföy ağırlıklı −0,33 net
  kaybettirdi; alım tarafı (45 işlem) +0,47. dev_train'deki "açığa satış
  yaklaşık başabaş" gözlemi dev_valid'de "açığa satış zararlı"ya döndü.
- Spot ile vadeli uzun arasında günlük getiri korelasyonu 0,99: bunlar iki
  bağımsız aday değil, tek fikrin iki uygulamasıdır.
- Kârın büyük kısmı 2024'te; 2025'in ilk yarısında stratejiler yaklaşık
  başabaş. Örneklem (18 ay, ~45 işlem) küçük.

## 7. Sonuç

1. Kısa vadeli (15m–1h) kırılım ve oynaklık fikirleri — sıkışma, NR4/NR7,
   00:00 UTC açılış aralığı, Williams oynaklık kırılımı — Binance standart
   maliyetleriyle dev_train'de bile kârlı değil veya 2× maliyete dayanıksız.
   Bu ailenin ana olumsuz bulgusu budur.
2. 4h Donchian(90) + hacim teyidi + 4×ATR iz stopu, yalnız alım yönünde
   (spot veya vadeli) dev_train ve dev_valid'de pozitif, 2× maliyette de
   pozitif ve aday şartlarını geçti. Bu, bir "trend yakalama" kuralıdır: piyasa
   yükselişlerinin bir kısmını alır, düşüşlerin çoğunda nakitte kalır. Al-tut'a
   göre getirisi daha düşük, düşüşü çok daha küçüktür.
3. İstatistiksel kanıt zayıf: DSR ≈ 0,01, bootstrap p ≈ 0,09. dev_valid kârı
   büyük ölçüde 2024 boğa piyasasına bağlı. Görülmemiş dönemde (Seviye 1/2)
   test edilmeden kârlı sayılmamalı; finalist seçilirse iki aday tek fikir
   olarak ele alınmalı (biri seçilmeli).
4. Açığa satış kolu değer katmadı; dev_valid'de zarar etti.

## 8. Protokol notları ve sınırlamalar

- Parametre seçimi yalnız dev_train ile yapıldı; dev_valid'e yalnız dondurulan 3
  yapılandırma ile bir kez bakıldı. dev_valid sonrası hiçbir kural/parametre
  değiştirilmedi. Sonradan yalnız spec açıklama metinlerine candidate_check
  sonucu yazıldı (sayıları etkilemez).
- Yeniden üretim kontrolü (`yeniden_uretim.py`) yalnız dev_train penceresinde,
  `record=False` ile yapıldı (dev_valid'e ikinci bakış yok).
- Al-tut kıyası `run()` ile hesaplandı ve deftere yazılmadı (strateji değil,
  kıyas). dev_valid al-tut değerleri dondurmadan sonra hesaplandı.
- Diğer ailelerin raporları okunmadı.
- Sınırlama: araştırmacının (modelin) kripto piyasasının 2024–2025 seyrine dair
  genel bilgisi vardır; bu bilgi seçimi bilinçli olarak etkilemedi ama tamamen
  dışlanamaz. Bağımsız ölçüm görülmemiş dönem ve ileriye dönük takiptir.
- PORT3'te SOL listelenmeden önceki dönemde 1/3 pay nakitte durur (harness
  `combine` davranışı); dev_train'in 2017–2020 kısmı bu yüzden 2 coinlik.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `NOTLAR.md` | Aramadan önce yazılan plan ve her aşama sonrası kararlar |
| `ortak.py` | `evaluate()` sarmalayıcı, yinelenen deneme önleme, dev_train tanısı |
| `tarama1.py`, `tarama2.py`, `tarama3.py` | Arama aşamaları |
| `tarama_sonuclari.jsonl` | Bütün arama satırları (dev_train 1× ve 2×) |
| `tani.py` | dev_train yıllık/bacak/yön tanısı |
| `nedensellik.py` | `assert_causal` |
| `dogrulama.py`, `dondurulmus_sonuclar.json` | Tek seferlik dev_valid değerlendirmesi, candidate_check, DSR |
| `dogrulama_tani.py`, `dogrulama_tani.json` | Dondurma sonrası tanılar ve DSR duyarlılığı |
| `al_tut.py`, `al_tut_dev_train_dev_valid.csv` | Al-tut kıyası |
| `yeniden_uretim.py` | `specs()` sayılarının yeniden üretimi (dev_train) |
| `veri_kontrol.py`, `sinyal_testi.py` | Veri ve sinyal doğruluk testleri (getiri hesaplamaz) |
