# Limit emirli gün içi stratejiler (`t2_limit_gun_ici`) — araştırma raporu

Protokol sürüm 2 ([`docs/PROTOKOL_2.md`](../../../docs/PROTOKOL_2.md)). Bütün sayılar
harness'ten (`grafik_analiz.research.evaluate`, `backtest`, `summarize`) alındı.
Getiriler nettir: komisyon, kayma ve fonlama dahil. Kod:
[`grafik_analiz/strategies/t2_limit_gun_ici.py`](../../../grafik_analiz/strategies/t2_limit_gun_ici.py).
Deney defteri: `arastirma/tur2/deneyler/t2_limit_gun_ici.jsonl`. Çalışma notları ve
dev_valid'den önce yazılan dondurma kararı: [`NOTLAR.md`](NOTLAR.md).

## Kısa sonuç

- Tur 1'de taker maliyetiyle ölen gün içi fikirler, sürüm 2'nin limit emir
  modeliyle yeniden sınandı:
  - ortalamaya dönüş (5m/15m/1h),
  - açılış aralığı kırılımı (ORB),
  - saat etkileri.

  Bunlara bir de "fitil yakalama" eklendi: her bar, kapanışın k·σ altına
  bekleyen alış limiti.
- **152 farklı yapılandırma** yalnız dev_train'de denendi. **5 yapılandırma**
  donduruldu ve dev_valid'de birer kez ölçüldü.
- **ORB, saat pencereleri, iki yönlü saf dönüş ve açığa satış fitili limitle de
  zarar etti.** Limit emir bu fikirleri kurtarmadı. Dolan emirler ağırlıkla fiyat
  aleyhe gittiğinde doldu (ters seçilim). Bu fikirlerin brüt kenarı zaten sıfır
  ya da negatifti.
- dev_train'de pozitif alfalı tek tema **yükselen trendde (kapanış > 50 günlük
  SMA) düşüş alımı** oldu. Bu temanın iki biçimi vardı: limitli dönüş sinyali
  ve derin fitil limiti. dev_train sonuçları: Sharpe 1,7–1,9, alfa t 3,4–4,0,
  beta 0,01–0,03.
- **dev_valid'de yalnız 1 yapılandırma `candidate_check`'i geçti:**
  `t2_limit_gun_ici_donus_1h_n4_e3_t50_H12_lim1.0s_m3`.

  | Ölçü | Değer |
  |---|---|
  | Getiri 1× / 2× | %+7,18 / %+5,74 |
  | Sharpe | 0,81 |
  | En büyük düşüş | %−4,91 |
  | İşlem | 45 |
  | Alfa / t | %+4,06 / 1,06 |
  | Beta | 0,006 |

  Diğer dördü geçmedi: iki fitil, 15m dönüş ve piyasa emirli kontrol.
- **Kanıt zayıf.** Geçen yapılandırmanın alfa t değeri 1,06, bootstrap p değeri
  0,09. Deflated Sharpe ≈ 0 (N=157). Aynı sinyalin piyasa emirli kontrolü
  dev_valid'de %−1,74 getirdi; yani sinyalin kendi kenarı bu dönemde yaklaşık
  sıfırdı. Kâr, limit girişin yaklaşık 1σ fiyat avantajından geldi. Tek dönem,
  45 işlem ve tek bir yapılandırma için bu sonuç şansla açıklanabilir.

## 1. Yöntem

### 1.1 Limit emir modeli ve motor

Harness kuralları (`research.backtest._backtest_limit`):

- Emir bir sonraki barda verilir.
- Açılışta piyasanın öbür tarafındaysa piyasa emri sayılır.
- Değilse yalnız fiyat limitin 2 bps ötesine geçerse limit fiyattan dolar.
  Vadeli maker komisyonu %0,02, kayma yoktur.
- Dolmayan emir bar sonunda iptal olur.

Sinyal fonksiyonu emrin dolup dolmadığını harness'ten öğrenemez. Bu yüzden
ailenin motoru (`_motor`) dolum kuralını birebir tekrarlar. Dolum, barın
açılışı ve düşüğü/yükseğiyle belirlendiği için barın kapanışında bilinir.
Böylece durum makinesi gerçek pozisyonu izler ve şunlara karar verebilir:

- dolmayan emri `m` bar yeniden vermek,
- dolan pozisyonu `H` bar sonra kapatmak.

Motorun pozisyonunun harness pozisyonuyla aynı olduğu iki yerde doğrulandı:

- sentetik veride (`motor_testi.py`),
- her arama değerlendirmesinde gerçek veride (`ortak.degerlendir`, dev_train'e
  kesilmiş veriyle).

### 1.2 Arama düzeni

- Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0,))`
  ile değerlendirildi. Aşama 3–4'te ayrıca 2.0 maliyet katı kullanıldı. Hepsi
  deftere yazıldı.
- Tanı ölçüleri aynı sinyallerle hesaplandı. Veri ve sinyaller hesaptan önce
  31.12.2024'te kesildi. dev_valid'e bakılmadı. Tanı ölçüleri:
  - dolum oranı,
  - dolan ve dolmayan emirlerin "açılışta piyasa emriyle girilseydi" H bar
    getirisi (ters seçilim),
  - dolan emirlerin limit fiyattan H bar getirisi,
  - yıllık ve bacak bazında getiri.
- Evren: vadeli BTC/ETH/SOL, eşit ağırlık (1/3), kaldıraçsız, pozisyon 0/±1.

## 2. Denenen yaklaşımlar ve parametre aralıkları (yalnız dev_train)

| Aşama | Betik | Yeni yapılandırma | İçerik |
|---|---|---|---|
| 1 | `tarama1.py` | 62 | Dört grup (aşağıda) |
| 2 | `tarama2.py` | 52 | donus 1h komşuluğu ve 15m/5m karşılıkları; fitil 1h komşuluğu; derin 5m/15m |
| 3 | `tarama3.py` | 25 | fitil + trend yüzeyi (1h k 2,5–4 × H 1–12; 5m k 4–8 × H 12–48; 15m), trend 30/100, 1× ve 2×. Ayrıca 7 eski yapılandırmanın yalnız 2× satırı. |
| 4 | `tarama4.py` | 9 | Yüzey kenarı: 1h k=4,5; 5m k=10; 5m trend 30/100 (1× ve 2×) |
| Son | `dogrulama.py` | (5) | Dondurulanların tek seferlik dev_train + dev_valid değerlendirmesi |

Aşama 1'in dört grubu:

- **fitil:** 5m k ∈ {2, 3, 4, 6} × H ∈ {1, 6, 24} ve hedef kâr; 15m k ∈ {2, 3, 4};
  1h k ∈ {2, 3}; açığa satış ve iki yön kontrolleri.
- **donus:** 1h/15m/5m, giriş piyasa emri (kontrol) ya da limit (0,25–1σ, m bar
  deneme); iki yönlü saf dönüş.
- **ORB:** 15m, açılış aralığı 1/2/4 saat; giriş piyasa emri, seviye limiti,
  10 bps limit ya da ters yön.
- **saat:** 21–23 UTC, 22–23 UTC alım; 02–03 UTC açığa satış; limit giriş ve
  çıkış.

Defter: 217 satır.

| Satır türü | Sayı |
|---|---:|
| dev_train 1× | 157 (152 benzersiz + 5 dondurma tekrarı) |
| dev_train 2× | 50 |
| dev_valid 1× | 5 |
| dev_valid 2× | 5 |

### 2.1 Gruplara göre dev_train özeti (152 yapılandırma, 1×)

| Grup | Sayı | Net > 0 | Medyan Sharpe | En iyi | En kötü | Medyan alfa | Medyan beta |
|---|---:|---:|---:|---:|---:|---:|---:|
| fitil 5m, yalnız alım, trendsiz | 19 | 7 | −0,76 | 1,19 | −15,62 | %−27 | 0,08 |
| fitil 5m, yalnız alım, 50 gün trend | 14 | 14 | 1,68 | 1,98 | 0,50 | %20 | 0,02 |
| fitil 15m, trendsiz | 12 | 4 | −0,21 | 1,02 | −6,94 | %−9 | 0,07 |
| fitil 15m, trend | 4 | 4 | 1,36 | 1,46 | 1,29 | %17 | 0,04 |
| fitil 1h, trendsiz | 19 | 18 | 1,03 | 1,66 | −0,43 | %14 | 0,10 |
| fitil 1h, trend | 23 | 23 | 1,48 | 1,96 | 0,98 | %17 | 0,03 |
| fitil 5m açığa satış (2) / iki yön (1) | 3 | 0 | −5,92 / −4,39 | −4,39 | −6,95 | %−130 / %−126 | −0,09 / −0,01 |
| donus 1h, alım, trend, limit | 20 | 20 | 1,73 | 1,98 | 0,88 | %19 | 0,02 |
| donus 1h, alım, trend, piyasa | 5 | 5 | 1,28 | 1,81 | 1,16 | %12 | 0,02 |
| donus 1h, alım, trendsiz, limit | 1 | 1 | 0,97 | | | %11 | 0,12 |
| donus 15m, alım, trend, limit / piyasa | 4 / 2 | 4 / 2 | 1,07 / 1,06 | 1,71 / 1,62 | 0,52 / 0,50 | %11 / %12 | 0,03 |
| donus 5m, alım, trend, limit / piyasa | 4 / 2 | 4 / 2 | 1,40 / 1,57 | 1,66 / 1,92 | 1,21 / 1,21 | %16 / %20 | 0,03–0,04 |
| donus iki yönlü (15m, 5m) | 4 | 0 | | −0,16 | −2,42 | %−8 … %−63 | 0,01–0,03 |
| ORB 15m | 12 | 0 | −1,00 | −0,40 | −1,85 | %−44 | −0,09 |
| saat 15m | 4 | 0 | −1,31 | −0,52 | −1,92 | %−25 | 0,06 |

### 2.2 Ana varyantların dev_train sonuçları (1×)

| Yapılandırma | Getiri | Sharpe | Düşüş | İşlem | Alfa (t) | Beta |
|---|---:|---:|---:|---:|---:|---:|
| fitil 5m k=2 H=1 | %−100,0 | −15,62 | %−100,0 | 63.728 | %−405,5 (−36,8) | 0,08 |
| fitil 5m k=6 H=24 | %+132,5 | 0,95 | %−37,3 | 2.971 | %+10,7 (1,25) | 0,07 |
| fitil 1h k=3 H=6 | %+326,2 | 1,10 | %−51,8 | 2.162 | %+16,0 (1,28) | 0,15 |
| fitil 1h k=3 H=6, trend 50 | %+372,6 | 1,93 | %−26,4 | 1.191 | %+27,3 (3,70) | 0,04 |
| fitil 5m k=6 H=24, trend 50 | %+287,1 | 1,98 | %−18,1 | 1.555 | %+24,5 (3,93) | 0,03 |
| fitil 5m açığa satış k=3 H=6 | %−100,0 | −6,95 | %−100,0 | 16.963 | %−169,6 (−15,4) | −0,12 |
| donus 1h trend, piyasa | %+181,7 | 1,81 | %−20,7 | 215 | %+18,7 (3,57) | 0,02 |
| donus 1h trend, limit 1σ, 3 bar | %+230,9 | 1,87 | %−20,7 | 189 | %+22,0 (3,74) | 0,02 |
| donus 1h trendsiz, limit 1σ | %+186,0 | 0,97 | %−43,0 | 430 | %+10,5 (1,01) | 0,12 |
| donus 15m (n=16, H=48), piyasa | %+240,6 | 1,62 | %−24,5 | 282 | %+22,0 (3,13) | 0,03 |
| donus 15m (n=16, H=48), limit 1σ | %+263,0 | 1,71 | %−22,0 | 265 | %+23,6 (3,37) | 0,03 |
| donus 5m (n=48, H=144), piyasa | %+348,0 | 1,92 | %−29,7 | 320 | %+27,3 (3,80) | 0,03 |
| donus 5m (n=48, H=144), limit 2σ | %+203,4 | 1,66 | %−30,0 | 273 | %+20,2 (3,27) | 0,03 |
| donus 15m iki yönlü, piyasa / limit | %−75,9 / %−30,9 | −0,91 / −0,16 | | 3.810 / 3.313 | %−27,6 / %−7,8 | 0,03 |
| ORB 15m 2 saat: piyasa / seviye limiti / 10 bps limit | %−98,9 / %−96,9 / %−97,9 | −1,08 / −0,98 / −1,02 | | ~4.250–5.140 | %−57 / %−43 / %−46 | −0,1 |
| saat 21–23 UTC alım: piyasa / limit | %−67,9 / %−49,3 | −0,95 / −0,52 | | ~5.200 | %−29,2 / %−20,7 | 0,08 |

Okuma notları:

- Fitil yalnız çok derin seviyelerde kârlı. Trendsiz sürümlerde kârın çoğu
  2021 ve SOL bacağından geliyor; BTC bacağı çoğunlukla zararda. 50 günlük
  trend filtresi düşüşü yarıya indiriyor ve alfa t değerini yaklaşık üç katına
  çıkarıyor.
- 1h dip alımında limitle piyasa emri arasındaki fark küçük. 15m'de limit
  biraz daha iyi. 5m'de limit daha kötü: düşük dolum ve ters seçilim.
- 2× maliyet (dev_train, Sharpe; piyasa → limit):
  - donus 1h: 1,66 → 1,80
  - donus 15m: 1,46 → 1,61

  Fitil sonuçları (2×): 1h k=3 H=6 trend 1,51; 5m k=6 H=24 trend 1,33;
  1h k=3 H=1 trend 0,96.

### 2.3 Dolum oranı ve ters seçilim (dev_train)

Bölüm: sinyal ve onu izleyen `m` bar yeniden deneme. "Piyasa getirisi":
sinyalden sonraki açılışta girilip H bar tutulsaydı elde edilecek brüt getiri.
Kaynak: `tani_secilim.log` ve `tani_dogrulama.log`.

| Yapılandırma | Dolum (bölüm) | Dolan: piyasa getirisi | Dolmayan: piyasa getirisi | Dolan: limitten getiri | Toplam brüt: hepsi piyasa / dolanlar limit |
|---|---:|---:|---:|---:|---:|
| donus 1h, 1σ, 3 bar | %76 | +155 bps | +102 bps | +209 bps | 3,54 / 3,94 |
| donus 1h, 2σ, 3 bar | %31 | +86 | +133 | +231 | 3,70 / 2,26 |
| donus 15m, 1σ, 12 bar | %72 | +134 | +173 | +164 | 5,34 / 4,34 |
| donus 5m, 2σ, 36 bar | %38 | +110 | +201 | +134 | 12,15 / 3,67 |
| donus 15m iki yönlü, 1σ | %73 | −18 | +66 | +7 | 2,05 / 2,29 |
| ORB 15m 2 saat, seviye limiti | %79 | −23 | +88 | +2 | 0,17 / 0,66 |
| saat 21–23, 3 bps limit | %79 | 0 | +30 | +3 | 4,13 / 1,62 |

Fitil (her bar emir; "piyasa getirisi" emrin verildiği barın açılışından):

| Yapılandırma | Dolum (emir başına) | Dolan | Dolmayan | Dolan: limitten |
|---|---:|---:|---:|---:|
| fitil 5m k=2 H=1 | %4,4 | −49 bps | +2 | −0,4 |
| fitil 5m k=6 H=24 | %0,2 | −97 | +3 | +19 |
| fitil 1h k=3 H=6 | %1,9 | −198 | +11 | +32 |
| fitil 1h k=4 H=3, trend (dondurulan) | %0,91 | −245 | +8 | +60 |
| fitil 5m k=8 H=24, trend (dondurulan) | %0,096 | −103 | +4 | +52 |

Rastgele yürüyüşte 2 bps geçme şartı, dolan emrin limitten getirisini yaklaşık
−2 bps yapar. Sığ fitil limitleri (k=2) buna yakın sonuç verdi. Kenar ancak
derin seviyelerde ve birkaç saatlik tutmada ortaya çıktı.

Ters seçilim her yöntemde var. Dolan emirler, dolmayanlara göre sistematik
olarak daha kötü anlarda doluyor. Tek istisna 1h dip alımında 1σ mesafe:
dev_train'de dolan bölümler dolmayanlardan iyiydi.

## 3. Dondurulan yapılandırmalar ve gerekçe

Karar dev_valid'den önce [`NOTLAR.md`](NOTLAR.md) bölüm 4'e yazıldı.

| # | Ad | Kural | Gerekçe |
|---|---|---|---|
| 1 | `t2_limit_gun_ici_fitil_1h_k4_H3_t50` | 1h. Kapanış 50 günlük SMA üstünde iken her saat kapanışın 4σ altına alış limiti (σ: 168 saatlik). Dolarsa 3 saat tut, piyasa emriyle çık. | 1h k × H yüzeyinde (k 2,5–4,5 × H 1–12) iç noktalar arasında 3×3 komşuluk ortalama Sharpe'ı en yüksek nokta (1,697). Tek başına en iyi nokta (k=3,5 H=6, 1,96) seçilmedi. |
| 2 | `t2_limit_gun_ici_fitil_5m_k8_H24_t50` | 5m. Aynı fikir; 8σ (σ: 288 bar), 2 saat tut. | 5m yüzeyinde (k 4–10 × H 12–48) komşuluk ortalaması en yüksek (1,738). Bacakları en dengeli olan da bu. |
| 3 | `t2_limit_gun_ici_donus_1h_n4_e3_t50_H12_lim1.0s_m3` | 4 saatlik getiri ≤ −3σ ve trend yukarı iken kapanışın 1σ altına alış limiti, 3 saat denenir. 12 saat tut. | donus 1h limit platosunun merkezi; komşuları Sharpe 1,63–1,98. |
| 4 | `t2_limit_gun_ici_donus_15m_n16_e3_t50_H48_lim1.0s_m12` | Aynı kuralın 15m karşılığı, 1σ (15m), 12 bar deneme. | İnce zaman diliminde limit yerleştirmenin etkisini sınar. |
| 5 | `t2_limit_gun_ici_donus_1h_n4_e3_t50_H12_piyasa` | 3 numaranın piyasa emirli sürümü. | **Kontrol:** limit etkisini dev_valid'de önceden kayıtlı ölçmek için. Bu kural tur 1'in `od_dip_ret4h_fut_port3_1h` kuralıyla aynıdır. |

Dondurulanların dev_train ayrıntısı (1×):

| # | Yıllık getiri 2020 / 21 / 22 / 23 / 24 | Bacak BTC / ETH / SOL |
|---|---|---|
| 1 | +11,8 / +113,6 / −13,2 / +18,5 / +7,8 % | +40,5 / +46,8 / +669,3 % |
| 2 | +7,2 / +75,3 / −11,4 / +41,4 / +21,2 % | +104,6 / +106,8 / +377,3 % |
| 3 | +11,7 / +115,3 / +0,5 / +17,1 / +16,9 % | +77,3 / +115,2 / +689,7 % |
| 4 | +19,2 / +118,4 / +2,0 / +20,5 / +13,4 % | +31,5 / +150,2 / +1.039,8 % |
| 5 | +7,7 / +86,4 / +4,4 / +17,8 / +14,0 % | +73,6 / +66,6 / +542,9 % |

Dondurmadan önce yapılan kontroller (`dondurma_kontrol.log`):

- Parametreler defterdeki arama satırlarıyla aynı.
- `assert_causal` varsayılan kesimlerde ve ek kesimlerde (0,3, 0,5, 0,7, 0,9,
  0,99) geçti.
- dev_train günlük getiri korelasyonları:
  - fitil 1h – fitil 5m: 0,61
  - donus 1h limit – piyasa: 0,93
  - donus 1h – donus 15m: 0,66
  - fitil – donus: −0,05 … 0,32

## 4. dev_valid sonuçları (01.01.2025 – 30.09.2026, her yapılandırma bir kez)

`dogrulama.py` → `dogrulama.log`, `dogrulama_sonuc.json`. dev_train değerleri
arama satırlarıyla birebir aynı çıktı.

| # | Pencere | Getiri 1× | Getiri 2× | Sharpe 1× / 2× | En büyük düşüş 1× | İşlem | Alfa 1× (yıllık) | Beta | Alfa t | Bootstrap p |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 fitil 1h | dev_train | %+164,95 | %+121,23 | 1,76 / 1,46 | %−16,43 | 601 | %+17,77 | 0,020 | 3,51 | 0,0004 |
| | **dev_valid** | **%+2,76** | **%−1,97** | **0,30 / −0,17** | **%−8,44** | **157** | **%+1,68** | **0,007** | **0,39** | 0,343 |
| 2 fitil 5m | dev_train | %+185,38 | %+126,97 | 1,92 / 1,52 | %−17,59 | 763 | %+20,35 | 0,011 | 4,04 | 0,0000 |
| | **dev_valid** | **%−5,89** | **%−10,19** | **−0,46 / −0,84** | **%−13,18** | **156** | **%−3,31** | **0,015** | **−0,63** | 0,718 |
| 3 donus 1h limit | dev_train | %+230,92 | %+212,69 | 1,87 / 1,80 | %−20,74 | 189 | %+22,00 | 0,024 | 3,74 | 0,0000 |
| | **dev_valid** | **%+7,18** | **%+5,74** | **0,81 / 0,66** | **%−4,91** | **45** | **%+4,06** | **0,006** | **1,06** | 0,090 |
| 4 donus 15m limit | dev_train | %+263,04 | %+235,29 | 1,71 / 1,61 | %−21,95 | 265 | %+23,62 | 0,029 | 3,37 | 0,0000 |
| | **dev_valid** | **%−5,05** | **%−7,00** | **−0,54 / −0,77** | **%−11,52** | **69** | **%−2,91** | **0,013** | **−0,75** | 0,767 |
| 5 donus 1h piyasa (kontrol) | dev_train | %+181,69 | %+154,83 | 1,81 / 1,66 | %−20,74 | 215 | %+18,70 | 0,023 | 3,57 | 0,0000 |
| | **dev_valid** | **%−1,74** | **%−4,15** | **−0,18 / −0,46** | **%−8,34** | **53** | **%−0,93** | **0,009** | **−0,25** | 0,622 |

dev_valid'de pozisyonda kalma oranı (1×): %1,8 / %1,4 / %2,4 / %3,8 / %2,9.
Toplam maliyet: 0,047 / 0,047 / 0,014 / 0,021 / 0,025. Fonlama ≤ 0,001.

### 4.1 candidate_check

| Şart | 1 fitil 1h | 2 fitil 5m | 3 donus 1h limit | 4 donus 15m limit | 5 donus 1h piyasa |
|---|---|---|---|---|---|
| Eğitimde net > 0 | evet | evet | evet | evet | evet |
| Doğrulamada net > 0 | evet | hayır | evet | hayır | hayır |
| Doğrulamada 2× net > 0 | hayır | hayır | evet | hayır | hayır |
| Doğrulamada Sharpe ≥ 0,5 | hayır (0,30) | hayır | evet (0,81) | hayır | hayır |
| Doğrulamada ≥ 20 işlem | evet (157) | evet (156) | evet (45) | evet (69) | evet (53) |
| Eğitimde alfa > 0 | evet | evet | evet | evet | evet |
| Doğrulamada alfa > 0 | evet | hayır | evet | hayır | hayır |
| **Aday** | **hayır** | **hayır** | **EVET** | **hayır** | **hayır** |

### 4.2 Deflated Sharpe

Girdiler:

- Deneme sayısı N: defterde `pencere == "dev_train"` ve `maliyet_kat == 1.0`
  olan satırlar, yani **157** (152 benzersiz yapılandırma ve 5 dondurma tekrarı).
- Varyans: bu satırların yıllık Sharpe varyansı **4,882** (std 2,21).
- Çarpıklık ve basıklık: dev_valid günlük getirileri, 638 gün.

| # | dev_valid Sharpe | Çarpıklık | Basıklık | **DSR** | Bağlam: PSR (N=1, düzeltmesiz) |
|---|---:|---:|---:|---:|---:|
| 1 | 0,30 | 0,85 | 36,2 | **0,0000** | 0,655 |
| 2 | −0,46 | 4,07 | 93,9 | **0,0000** | 0,283 |
| 3 | 0,81 | 3,19 | 101,4 | **0,0000** | 0,869 |
| 4 | −0,54 | −2,52 | 57,9 | **0,0000** | 0,229 |
| 5 | −0,18 | 0,08 | 91,7 | **0,0000** | 0,407 |

Varyansı aşama 1'deki çok kötü keşif denemeleri büyütüyor. Örneğin 5m k=2 H=1
fitilinin Sharpe'ı −15,6. Bu denemeler gerçektir ve sayılmalıdır. Çoklu deneme
düzeltmesinden sonra hiçbir sonuç anlamlı değildir. Düzeltmesiz PSR bile
adayda 0,87'dir, yani 0,95'in altındadır.

### 4.3 Al-tut kıyası

Vadeli BTC/ETH/SOL, eşit ağırlık, 1h; fonlama dahil. Deftere yazılmadı.

| Pencere | Al-tut getiri | Sharpe | En büyük düşüş | BTC / ETH / SOL |
|---|---:|---:|---:|---|
| dev_train (2020-01 – 2024-12) | %+2.751,1 | 1,26 | %−86,3 | %+535,5 / %+984,5 / %+5.433,9 |
| dev_valid | %−22,1 | 0,06 | %−65,5 | %−17,0 / %−24,5 / %−37,3 |

Stratejiler zamanın yalnız %1–5'inde pozisyonda ve betaları 0,01–0,03.
dev_train'de mutlak getiride al-tut'un çok gerisinde kaldılar; düşüşleri
%16–22 idi. dev_valid'de al-tut %−22,1 kaybetti. Aday +%7,2 getirdi ve en
büyük düşüşü %−4,9 oldu. Ancak beta ≈ 0 olduğu için bu fark, stratejinin
piyasayı "yendiğini" değil, piyasada neredeyse hiç bulunmadığını gösterir.

## 5. dev_valid sonrası betimleyici tanı (parametre değişmedi)

Kaynak: `tani_dogrulama.py` ve `tani_dogrulama.log`. Ayrıntılar `dogrulama.log`
dosyasındadır.

dev_valid'de bacak ve yıl bazında getiri:

| # | BTC / ETH / SOL | 2025 / 2026 (9 ay) |
|---|---|---|
| 1 | %−0,55 / %−3,28 / %+11,92 | %+2,78 / %−0,02 |
| 2 | %−8,54 / %−17,36 / %+8,75 | %−3,95 / %−2,02 |
| 3 | %+5,05 / %+4,04 / %+11,52 | %+3,94 / %+3,12 |
| 4 | %−0,33 / %−1,63 / %−14,16 | %−8,83 / %+4,15 |
| 5 | %−0,32 / %−4,38 / %−1,55 | %−2,36 / %+0,63 |

Limit girişin dev_valid'deki etkisi (bölüm düzeyi):

| Yapılandırma | Bölüm | Dolum | Dolan: piyasa getirisi | Dolmayan: piyasa getirisi | Dolan: limitten | Toplam brüt: hepsi piyasa / dolanlar limit |
|---|---:|---:|---:|---:|---:|---:|
| 3 donus 1h | 60 | %75 | +4 bps | +8 bps | +55 bps | 0,030 / 0,249 |
| 4 donus 15m | 109 | %63 | −24 | −23 | −12 | −0,258 / −0,085 |

Dip alımı sinyalinin kendisi dev_valid'de yaklaşık sıfır kenar verdi. Bütün
bölümler piyasa emriyle alınsaydı ortalama +0,5 bps olurdu. 1h adayın kârı,
limit girişin 1σ fiyat avantajından geldi. Ters seçilim bu dönemde de
görülmedi: dolan ve dolmayan bölümler benzerdi.

Fitil emirlerinin dolum oranı ve dolum sonrası getirisi:

| Yapılandırma | Dolum (dev_train → dev_valid) | Dolum sonrası limitten getiri (dev_train → dev_valid) |
|---|---|---:|
| 1h | %0,91 → %0,75 | +60 → +15 bps |
| 5m | %0,096 → %0,061 | +52 → −2 bps |

Bu getiriler maker giriş + taker çıkış maliyetini (yaklaşık 9 bps, 2×'te
18 bps) 1h'de zar zor karşıladı, 5m'de karşılamadı. Kâr yine SOL bacağından
geldi.

## 6. Dürüst değerlendirme

- **Limit emir, kenarı olmayan gün içi fikirleri kurtarmıyor.** ORB, saat
  etkileri, iki yönlü saf dönüş ve sığ fitil limitleri limitle de zarar etti.
  Maker komisyonu düşük; ama dolum, fiyat aleyhe gittiğinde gerçekleşiyor. 2 bps
  geçme şartı da her dolumda yaklaşık 2 bps maliyet ekliyor. Ölçülen ters
  seçilim büyük: dolan emirler, dolmayanlardan bölüm başına 30–110 bps daha
  kötü. Bu fark çoğu durumda limitin fiyat avantajını yiyor.
- **Limit, kenarı olan bir sinyalde maliyeti ve giriş fiyatını iyileştirebiliyor.**
  Bunun için mesafe ılımlı olmalı (yaklaşık 1σ) ve zaman dilimi 1 saat
  olmalı. 1h dip alımında limit, dev_train'de Sharpe'ı 1,81'den 1,87'ye
  çıkardı. dev_valid'de kontrol %−1,74 iken limitli sürüm %+7,18 getirdi.
  Daha derin limitlerde (2σ) ve 5m/15m'de dolmayan iyi işlemlerin kaybı
  ağır bastı.
- **Tek aday zayıf:** `t2_limit_gun_ici_donus_1h_n4_e3_t50_H12_lim1.0s_m3`.
  - 45 işlem; alfa t 1,06; bootstrap p 0,09; DSR ≈ 0.
  - dev_train'den dev_valid'e Sharpe 1,87'den 0,81'e düştü.
  - Sinyalin kendisi dev_valid'de kenar göstermedi. Kâr, limit girişin fiyat
    avantajına ve 45 işlemlik tek bir örnekleme dayanıyor.
  - Bu kural tur 1'in `od_dip_ret4h_fut_port3_1h` kuralının limit girişli
    biçimidir. Bağımsız bir yeni fikir değildir.
- **Fitil yakalama:** dev_train'deki güçlü sonuç (alfa t 3,5–4,0) dev_valid'de
  tekrarlanmadı (alfa t 0,39 ve −0,63). Kâr dev_train'de ağırlıkla 2021 ve
  SOL'dan geliyordu. Bu, yüzey seçiminde aşırı uyum ya da rejim
  bağımlılığıyla tutarlı.
- Bu aileden çıkan tek aday, ileriye dönük takip için en fazla "zayıf aday"
  sayılabilir. Kârlı bir sistem kanıtı değildir.

### Bilgi çekincesi

Görevin gereği olarak tur 1 raporları okundu. Bu raporlar tur 2'nin dev_valid
dönemiyle örtüşen sonuçlar içeriyor:

- tur 1 dev_valid'inin 2025 ilk yarısı,
- tur 1 görülmemiş dönemi.

Örneğin tur 1 dip alımı kuralının 2025 ilk yarısı sonucu bu raporlarda yazıyor.
Fikir, parametre ve dondurma seçimleri yalnız tur 2 dev_train sonuçlarına
dayandırıldı. 5 numaralı kontrolün o kural olması yalnız kontrol amacıyladır.
Yine de bu bilginin ve modelin 2025–2026 piyasasına dair genel bilgisinin
etkisi tamamen dışlanamaz.

## 7. Dosyalar

- `grafik_analiz/strategies/t2_limit_gun_ici.py`: motor, yöntemler ve `specs()`.
  `specs()` dondurulan 5 yapılandırmayı döndürür; candidate_check sonucu
  açıklamalarda yazılıdır.
- `ortak.py`: arama yardımcısı. Kaydı `evaluate` ile yapar; tanı dev_train'e
  kesilir ve motor ile harness pozisyonunun eşitliği kontrol edilir.
- `motor_testi.py`: sentetik veride motor doğrulaması.
- Arama betikleri ve çıktıları:
  - `tarama1.py` → `tarama1*.csv`, `tarama1_*.log`
  - `tarama2.py` → `tarama2_*.csv`, `tarama2_*.log`
  - `tarama3.py` → `tarama3_*.csv`, `tarama3_*.log`
  - `tarama4.py` → `tarama4_*.csv`, `tarama4_*.log`

  Tanı sütunları:
  - `fill_rate`: emir başına dolum oranı.
  - `mo_fill_mkt_bps` / `mo_miss_mkt_bps`: dolan ve dolmayan emirlerin piyasa
    getirisi.
  - `mo_fill_lim_bps`: dolan emirlerin limitten getirisi.
- `tani_secilim.py` ve `tani_secilim_liste.json` → `tani_secilim.log`: dev_train
  bölüm düzeyi ters seçilim.
- `dondurma_kontrol.py` → `dondurma_kontrol.log`.
- `dogrulama.py` → `dogrulama.log`, `dogrulama_sonuc.json`.
- `tani_dogrulama.py` → `tani_dogrulama.log`, `tani_dogrulama.json`: dev_valid
  sonrası tanı.

## 8. Altyapı notları

1. `_backtest_limit`, işlem listesini (`_trades`) taker maliyetiyle hesaplıyor.
   Maker dolumlarda işlem düzeyi ölçüler maliyeti fazla gösteriyor:
   `win_rate`, `avg_trade`, `best_trade`, `total_without_best`. Bar serisinden
   hesaplanan getiri, Sharpe ve düşüş doğrudur.
2. Sinyal fonksiyonu dolum bilgisini alamıyor. "Dolmazsa bırak", "dolduktan H
   bar sonra çık" gibi kurallar için strateji, harness'in dolum kuralını
   kendisi tekrarlamak zorunda. Tekrarlanması gerekenler:
   - `LIMIT_PENETRATION`,
   - açılışta piyasa emrine dönüş kuralı.

   Kural değişirse strateji sessizce ayrışır. Bu ailede eşitlik her çalıştırmada
   kontrol edildi.
3. Bacak başına bar başına tek emir verilebiliyor. Aynı anda alış ve satış
   kotasyonu ya da aynı anda hedef kâr ve stop emri ifade edilemiyor.
4. Deflated Sharpe tarifinde varyans ailenin bütün denemelerinden alınıyor.
   Keşif aşamasındaki çok negatif denemeler bu varyansı büyütüyor; sonuçta
   bütün yapılandırmalarda DSR 0 çıkıyor ve ölçü ayırt edici olmuyor.
5. Araştırma verisinin zaman indeksi `datetime64[ms, UTC]`. `Index.asi8`
   milisaniye döndürür; nanosaniye varsayan kod sessizce yanlış çalışır. Bu
   ailenin ilk sürümünde bu hata vardı ve sentetik testte yakalandı.
