# t2_konumlanma — Konumlanma verisi ailesi (araştırma turu 2)

Protokol sürüm 2 (`GRAFIK_ANALIZ_PROTOKOL=2`, `docs/PROTOKOL_2.md`).
Eğitim (dev_train): verinin başı – 31.12.2024. İç doğrulama (dev_valid):
01.01.2025 – 30.09.2026. 30.09.2026 sonrası veri kullanılmadı.
Plan ve dondurma kararı: [`NOTLAR.md`](NOTLAR.md). Kod:
`grafik_analiz/strategies/t2_konumlanma.py`.

## 1. Kısa sonuç

- 245 yapılandırma yalnız eğitim döneminde denendi. Defterde 250
  `dev_train` 1× satırı var; 5'i dondurulanların `evaluate(spec)` tekrarı.
- Eğitimde çok güçlü bir sinyal bulundu: genel hesapların uzun/kısa oranına
  karşı pozisyon ("kalabalık"). Alfa t 4,7'ye kadar çıktı, beta ≈ 0.
- Bu sinyal iç doğrulamada büyük ölçüde kayboldu. 5 dondurulmuş
  yapılandırmadan yalnız biri (**D2**) `candidate_check`'i geçti.
- D2 de sınırda geçti:
  - Sharpe 0,503 (eşik 0,5).
  - Alfa t 0,67.
  - Deflated Sharpe 0,004.
  - En iyi tek işlem çıkınca getiri %+0,6.
- Kârın çoğu tek bir yarıyıldan (2026 ilk yarı) ve SOL bacağından geliyor.
- Sonuç: D2 protokolün aday şartlarını mekanik olarak karşılıyor. Ama
  istatistiksel kanıt yok denecek kadar zayıf. Eğitimdeki güçlü sonuç büyük
  ölçüde örneklem içi idi.

## 2. Veri ve nedensellik

- Bacaklar: BTC/ETH/SOL USDⓈ-M sürekli vadeli. Bacak başına 1/3 sermaye.
  Pozisyon −1…+1, kaldıraç yok.
- Konumlanma ölçüleri (`load_metrics`, 5 dakikalık):
  - BTC 2020-09'dan, ETH ve SOL 2021-12'den başlıyor.
  - Eğitimde üç coin birlikte ~3 yıl, BTC tek başına ~4,3 yıl.
- Bar t kararında kullanılan kayıt:
  - Zaman damgası ≤ bar kapanışı − 10 dk olan son kayıt.
  - 2 saatten eski kayıt yok sayılır.
  - Ölçüler `signal_fn` içinde `scope="dev"` ile yüklenir. Verilen mumların
    son barının kapanışına kadar açıkça kesilir.
- Prim endeksi: barla aynı açılış zamanlı prim mumunun kapanışı. Aynı
  biçimde kesilir.
- Taker alım payı: vadeli mumun kendi `taker_buy_base / volume` alanı.
- Normalizasyonlar yalnız geriye dönük kayan pencerelerle yapıldı.
- **Hizalama kontrolü** (`hizalama.py`, `hizalama.log`, yalnız eğitim):
  - Ölçümün taker oranı en çok [T−5dk, T) mumuyla örtüşüyor
    (korelasyon 0,65–0,77).
  - [T, T+5dk) mumuyla da kısmen örtüşüyor (0,29–0,37). T damgalı kayıt,
    T'den sonraki birkaç dakikayı da içeriyor.
  - 10 dakikalık ihtiyat payı bu yüzden gerekli ve yeterli.
- **Gecikme testi:** Kalabalık sinyali, ölçüm 30/60/120 dk geç
  kullanılınca da eğitimde güçlü kaldı (1s alfa t 4,38 / 4,32 / 4,00).
  Sonuç bir zaman damgası kaymasından gelmiyor.
- Dondurulan 5 yapılandırma `assert_causal`'ı geçti. Varsayılan kesimler:
  0,55 / 0,8 / 0,97. Ek kesimler: 0,3 / 0,65 / 0,9 / 0,99
  (`nedensellik.log`).

## 3. Denenen yaklaşımlar ve parametre aralıkları

Hepsi üç coinlik sepet, 1s ve 4s. Eğitimde 1× ve 2× maliyetle ölçüldü
(`tara.py`, `egitim_sonuclari.jsonl`, `tara_5.log`). Aşamalar:

- Aşama 1: kaba ızgara, 108 yapılandırma.
- Aşama 2a: gecikme testi, 5.
- Aşama 2b: fiyat kontrolü, 4.
- Aşama 3: komşuluklar, 112 (10'u aşama 1 ile ortak).
- Aşama 4: bileşik, 8.
- Aşama 5: kesintiden sonra, 18.

| Fikir (tür) | Açıklama | Aralıklar | Sayı |
|---|---|---|---:|
| `oi` / tasfiye | OI sert düşerken fiyat sert hareket ettiyse ters yönde | k 1s {4,12,24} / 4s {1,3,6}; b {1,5; 2,5}; a 1,0; tut 1s {12,48} / 4s {3,12}; w 30 g | 24 |
| `oi` / birikim | OI sert artarken fiyat yönünde | aşama 1 aralıkları + k 1s {8,12,16} / 4s {2,3,4}; b {1,5; 2,0}; tut 1s {6,12,24} / 4s {2,3,6} | 58 |
| `kalabalik` | Genel hesap uzun/kısa oranının (log) z-skoru; karşıt | w {3,7,14,30,90} g; giriş c {0,5…2,0}; çıkış cx {0; 0,5} | 46 |
| `kalabalik` (diğer oranlar) | En büyük hesapların hesap/pozisyon oranı, karşıt | w 7, c 1,0 | 4 |
| `kalabalik` gecikme | Ölçüm 30–240 dk geç | 1s {30,60,120}, 4s {60,240} | 5 |
| `kalabalik` limit emir | Kapanıştan limit, 1–2 bar, sonra piyasa | 1s ve 4s, 3 sinyal × 2 | 6 |
| `kalabalik_top` | w 3-7-14 ortalaması | 1s, 4s | 2 |
| `kalabalik` + trend | Uzun yalnız SMA üstünde, kısa altında | SMA 7 ve 30 gün | 2 |
| `prim` / karşıt | Prim endeksi ortalamasının z-skoru, karşıt | n 1s {8,24} / 4s {2,6}; w {7,30,90}; c {1,2} | 24 |
| `prim` / izle | Aynı, izle yönü | n aynı; w {7,30}; c 1 | 8 |
| `taker` / izle | Taker alım payının z-skoru, izle | k 1s {6,12,24,48} / 4s {1,3,6,12}; c {1,0…2,5}; w 30 | 24 |
| `taker` / karşıt | Aynı, karşıt | k 1s {6,24} / 4s {1,6}; c {1,2} | 8 |
| `fark` | Büyük hesap pozisyon oranı z − genel oran z; büyükleri izle | w {7,14,30}; c {0,5…2,0} | 22 |
| `bilesik` | (−kalabalık z + taker z) / 2 | w 7; taker k 1s {24,48} / 4s {6,12}; c {0,5; 1,0} | 8 |
| `fiyat` (kontrol) | Yalnız fiyat z-skoru, momentum; konumlanma verisi yok | w {7,30}; c 1 | 4 |
| **Toplam** | | | **245** |

## 4. Eğitim (dev_train) sonuçları

Her tür için sayı, pozitif alfalı oran, medyan alfa t ve en iyi
yapılandırma (1× maliyet). Getiriler toplam, eğitim dönemi boyunca.

| Tür | Sayı | Alfa > 0 | Medyan alfa t | 2× net > 0 | En iyinin getirisi | Sharpe | En büyük düşüş | Alfa | Beta | Alfa t | İşlem |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| kalabalık (genel) | 46 | %100 | 3,62 | %100 | %+4.451,6 | 2,07 | %−38,9 | +0,838 | +0,007 | 4,56 | 3142 |
| kalabalık limit | 6 | %100 | 4,30 | %100 | %+4.884,0 | 2,11 | %−38,7 | +0,856 | +0,007 | 4,67 | 3132 |
| kalabalık topluluk | 2 | %100 | 4,18 | %100 | %+2.999,8 | 2,06 | %−37,4 | +0,737 | +0,013 | 4,51 | 1522 |
| kalabalık + trend | 2 | %100 | 3,72 | %100 | %+837,2 | 1,69 | %−26,3 | +0,531 | −0,038 | 4,14 | 1154 |
| kalabalık (büyük hesap oranları) | 4 | %100 | 2,22 | %75 | %+886,3 | 1,62 | %−30,1 | +0,506 | +0,000 | 3,61 | 1047 |
| oi / birikim | 58 | %98 | 1,54 | %79 | %+367,3 | 1,54 | %−22,6 | +0,354 | −0,021 | 3,69 | 731 |
| bileşik | 8 | %100 | 3,17 | %100 | %+1.490,5 | 1,52 | %−39,5 | +0,626 | +0,013 | 3,31 | 1363 |
| fark | 22 | %100 | 2,17 | %100 | %+555,7 | 1,35 | %−35,9 | +0,422 | +0,003 | 2,99 | 1374 |
| taker / izle | 24 | %83 | 1,29 | %79 | %+355,3 | 1,11 | %−26,0 | +0,374 | −0,019 | 2,62 | 368 |
| oi / tasfiye | 24 | %50 | −0,01 | %29 | %+20,8 | 0,61 | %−10,1 | +0,037 | +0,003 | 1,24 | 90 |
| prim / karşıt | 24 | %21 | −0,56 | %0 | %+107,7 | 0,54 | %−73,5 | +0,136 | +0,129 | 0,59 | 1666 |
| prim / izle | 8 | %0 | −1,50 | %0 | %−90,3 | −0,50 | %−95,7 | −0,024 | −0,236 | −0,10 | 670 |
| taker / karşıt | 8 | %0 | −3,24 | %0 | %−86,5 | −1,35 | %−89,0 | −0,287 | −0,066 | −2,42 | 531 |
| fiyat (kontrol) | 4 | %100 | 2,61 | %100 | %+1.518,0 | 1,18 | %−58,9 | +0,859 | −0,083 | 2,96 | 238 |

Gözlemler (yalnız eğitim):

- **Kalabalık sinyali** açık ara en güçlüsüydü. 65 türevinin (genel oran 46, limit 6,
  topluluk 2, trend 2, büyük hesap oranları 4, gecikme 5) hepsi pozitif
  alfalıydı.
  - Sepet her yıl kazandı: 2020 (Eylül–Aralık) %+22, 2021 %+148, 2022 %+137,
    2023 %+134, 2024 %+113 (`egitim_ayrinti.py`).
  - Üç coin ve iki yön de ayrı ayrı pozitif alfalıydı.
  - İşlemlerin yalnız %37–44'ü kazanıyor; kâr büyük kazançlardan geliyor.
    Momentum benzeri bir profil.
- **Fiyat kontrolü:** Yalnız fiyatla yapılan momentum taklidi daha zayıftı
  (alfa t 2,5–3,0, Sharpe 0,9–1,2). Kalabalık sinyali eğitimde fiyat
  momentumunun ötesinde bilgi taşıyor gibi görünüyordu.
- **Zayıf ya da negatif kalanlar:**
  - Prim endeksi her iki yönde de değersizdi.
  - OI tasfiye fikri değersizdi.
  - Taker karşıt yön değersizdi.
- **Ek varyantlar:**
  - Limit emir maliyeti biraz düşürdü (2× getiri %+951 → %+1.453).
  - Trend filtresi sinyali zayıflattı.

## 5. Dondurma

Kural, sonuçlardan önce yazıldı (`NOTLAR.md` bölüm 4 ve 9). Mekanik
uygulama `dondurma.py` ile yapıldı (`dondurma.log`, `dondurma.json`).

1. **Uygunluk:** Eğitimde 2× net > 0; 1× alfa > 0 ve alfa t ≥ 1,5; işlem
   ≥ 60; Sharpe ≥ 0,5. Fiyat kontrolü aday değil.
2. **Sağlamlık:** Tek parametresi farklı komşular en az 2 tane olmalı ve
   yarıdan fazlası pozitif alfalı olmalı. 245 yapılandırmadan 121'i
   uygunluğu ve sağlamlığı geçti.
3. **Sıralama:** Alfa t'ye göre. Aynı türden en fazla 2.
4. **Korelasyon:** Eğitim günlük getirisi seçilenlerle < 0,70 olmalı.
   Getiriler 31.12.2024'te kesilmiş veriyle hesaplandı.
5. **Sayı:** En fazla 5.

Sırada D1'den sonra gelen 17 kalabalık türevi (1s ve 4s, w3–w14) D1 ile
0,74–0,999 korelasyonluydu. Bu yüzden ikinci kalabalık seçimi daha yavaş w30
türevine düştü. Bileşik türevler seçilenlerle 0,78–0,89 korelasyon
nedeniyle elendi.

| # | Yapılandırma | Fikir |
|---|---|---|
| D1 | `t2_konumlanma_kalabalik_1h_SEPET3_genel_w7_c0.5_cx0.5_s-1_limit_lb1` | Genel oran 7 günlük z > 0,5 kısa, < −0,5 uzun; limit emir (1 bar), sonra piyasa |
| D2 | `t2_konumlanma_kalabalik_1h_SEPET3_genel_w30_c1.0_cx0.0_s-1` | Genel oran 30 günlük z > 1 kısa, < −1 uzun; işaret değişince çık |
| D3 | `t2_konumlanma_oi_1h_SEPET3_birikim_k8_w30_a1.0_b1.5_t12` | 8 saatte OI z > 1,5 ve fiyat hareketi > 1 std ise fiyat yönünde 12 saat |
| D4 | `t2_konumlanma_fark_1h_SEPET3_w14_c0.5_cx0.0_s1` | Büyük hesap pozisyon oranı z − genel oran z (14 g) > 0,5 uzun, < −0,5 kısa |
| D5 | `t2_konumlanma_taker_4h_SEPET3_k12_w30_c2.0_cx0.0_s1` | 48 saatlik taker alım payı z > 2 uzun, < −2 kısa |

Eğitim günlük getiri korelasyonları en fazla 0,591 (D1–D2). Dondurma notu
08:51 UTC'de yazıldı; ilk dev_valid defter satırı 08:52:31 UTC.

## 6. Sonuçlar: eğitim ve iç doğrulama

Her yapılandırma bir kez `evaluate(spec)` ile ölçüldü (`dogrulama.py`,
`dogrulama.log`, `dondurulmus_sonuclar.json`).

### Eğitim (dev_train)

| # | Getiri 1× | Getiri 2× | Sharpe | En büyük düşüş | İşlem | Alfa | Beta | Alfa t |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D1 | %+4.884,0 | %+1.452,7 | 2,11 | %−38,7 | 3132 | +0,856 | +0,007 | 4,67 |
| D2 | %+2.082,9 | %+1.554,5 | 1,79 | %−36,0 | 595 | +0,673 | +0,015 | 3,89 |
| D3 | %+367,3 | %+232,2 | 1,54 | %−22,6 | 731 | +0,354 | −0,021 | 3,69 |
| D4 | %+555,7 | %+245,4 | 1,35 | %−35,9 | 1374 | +0,422 | +0,003 | 2,99 |
| D5 | %+355,3 | %+283,6 | 1,11 | %−26,0 | 368 | +0,374 | −0,019 | 2,62 |

### İç doğrulama (dev_valid), 1× maliyet

| # | Getiri | Sharpe | En büyük düşüş | İşlem | Alfa | Beta | Alfa t | Bootstrap p | En iyi işlem çıkınca |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D1 | %−23,27 | −0,105 | %−55,1 | 1579 | −0,055 | +0,115 | −0,16 | 0,574 | %−29,1 |
| D2 | **%+24,23** | **0,503** | %−29,7 | 340 | **+0,210** | −0,018 | 0,67 | 0,265 | %+0,6 |
| D3 | %+6,37 | 0,277 | %−20,6 | 382 | +0,051 | +0,052 | 0,35 | 0,362 | %−1,6 |
| D4 | %−30,44 | −0,211 | %−53,1 | 904 | −0,096 | −0,042 | −0,27 | 0,613 | %−42,4 |
| D5 | %−3,88 | 0,012 | %−23,3 | 149 | −0,002 | +0,078 | −0,01 | 0,511 | %−11,0 |

### İç doğrulama, 2× maliyet

| # | Getiri | Sharpe | En büyük düşüş | Alfa |
|---|---:|---:|---:|---:|
| D1 | %−58,21 | −0,853 | %−71,0 | −0,401 |
| D2 | %+5,92 | 0,284 | %−32,1 | +0,120 |
| D3 | %−11,00 | −0,247 | %−28,0 | −0,051 |
| D4 | %−54,39 | −0,720 | %−66,1 | −0,336 |
| D5 | %−10,36 | −0,165 | %−26,4 | −0,042 |

### candidate_check

| Şart | D1 | D2 | D3 | D4 | D5 |
|---|---|---|---|---|---|
| Eğitimde net > 0 | ✓ | ✓ | ✓ | ✓ | ✓ |
| İç doğrulamada net > 0 | ✗ | ✓ | ✓ | ✗ | ✗ |
| İç doğrulamada 2× net > 0 | ✗ | ✓ | ✗ | ✗ | ✗ |
| İç doğrulamada Sharpe ≥ 0,5 | ✗ | ✓ (0,503) | ✗ | ✗ | ✗ |
| İç doğrulamada ≥ 20 işlem | ✓ | ✓ | ✓ | ✓ | ✓ |
| Eğitimde alfa > 0 | ✓ | ✓ | ✓ | ✓ | ✓ |
| İç doğrulamada alfa > 0 | ✗ | ✓ | ✓ | ✗ | ✗ |
| **Aday** | **hayır** | **evet** | **hayır** | **hayır** | **hayır** |

## 7. Deflated Sharpe

Hesap `dogrulama.py` ile yapıldı. Deneme sayısı, defterde
`pencere=="dev_train"` ve `maliyet_kat==1.0` olan satırlardır: **250**
(245 benzersiz). Bu satırların yıllık Sharpe varyansı 0,7648 (ortalama
0,71, en yüksek 2,11). dev_valid 638 gün. Çarpıklık ve basıklık dev_valid
günlük getirilerinden alındı.

| # | dev_valid Sharpe | Çarpıklık | Basıklık | DSR |
|---|---:|---:|---:|---:|
| D1 | −0,105 | 0,93 | 7,12 | 0,0003 |
| D2 | 0,503 | 1,24 | 9,98 | 0,0040 |
| D3 | 0,277 | 2,87 | 27,72 | 0,0015 |
| D4 | −0,211 | 0,44 | 7,19 | 0,0002 |
| D5 | 0,012 | 0,55 | 20,83 | 0,0006 |

Hiçbiri 0,95'e yaklaşmıyor. D2'nin Sharpe'ı, 250 denemenin en iyisinden
şansla beklenen düzeyin çok altında.

## 8. Al-tut kıyası

Kıyas: BTC/ETH/SOL vadeli, eşit ağırlıklı al-tut, brüt (maliyet ve fonlama
yok). Kaynak: `benchmark_daily`.

| Dönem | Getiri | Sharpe | En büyük düşüş |
|---|---:|---:|---:|
| Eğitim (08.09.2019 – 31.12.2024) | %+3.953,4 | 1,28 | %−85,1 |
| İç doğrulama (01.01.2025 – 30.09.2026) | %−18,93 | 0,10 | %−64,3 |

İç doğrulamada D2 (%+24,2, düşüş %−29,7) ve D3 (%+6,4) al-tutun üstünde
kaldı. Ancak:

- Betaları ≈ 0. Kıyasın düşmesinden kazanmadılar, ondan etkilenmediler.
- Alfaları istatistiksel olarak sıfırdan ayırt edilemiyor: t 0,67 ve 0,35.

## 9. Dondurma sonrası betimleyici tanı

`dogrulama_tani.py`, `dogrulama_tani.log`. Deftere yazmaz; hiçbir seçim ya
da parametre bu çıktıya göre değişmedi.

- **D1:** Sinyal iç doğrulamada maliyet öncesi hâlâ %+43 kazandırdı. Ama
  1.579 işlemin maliyeti bunu %−23'e çevirdi. Eğitimdeki brüt kenarın
  küçük bir parçası kaldı.
- **D2, coin bazında:** BTC %+20, ETH %−27, SOL %+55.
- **D2, dönem bazında:**
  - 2025 ilk yarı %+4, 2025 ikinci yarı %−17.
  - 2026 ilk yarı %+52, 2026 3. çeyrek %−6.
  - Kârın tamamı fiilen 2026 ilk yarısından geliyor.
  - En iyi tek işlem çıkınca getiri %+0,6.
- **D4:** SOL'da %+58, BTC'de %−49, ETH'de %−74. Büyük hesapları izleme
  fikri genelleşmedi.
- **D3 ve D5:** Maliyet öncesi küçük artı, maliyet sonrası sıfır civarı ya
  da eksi.

## 10. Dürüst sonuç

- Konumlanma verisi eğitimde olağanüstü sonuçlar verdi. Kontroller bunun
  bir veri hatası ya da ileri bakıştan kaynaklandığına dair iz bulmadı:
  hizalama, gecikme ve `assert_causal`.
- Ama 245 denemenin en iyileri iç doğrulamada büyük ölçüde çöktü:
  - Eğitim alfası 0,35–0,86/yıl iken iç doğrulamada −0,10…+0,21/yıl.
  - Alfa t 2,6–4,7'den −0,3…+0,7'ye düştü.
- Tek aday D2, şartları en dar farkla geçti (Sharpe 0,503). Kârı tek bir
  yarıyıla ve tek coine dayanıyor. Deflated Sharpe 0,004. İleriye dönük
  takipte yeni bilgi sağlayabilir, ama bugünkü kanıtla **kârlı bir strateji
  bulunduğu söylenemez.**
- Eğitimdeki güçlü sinyal muhtemelen dönemine özgüydü. "Perakende hesaplara
  karşı dur" davranışı 2025–2026'da aynı güçte sürmedi.

## 11. Kesinti ve devam

- Önceki araştırmacı arama sırasında durduruldu. O noktada 227 yapılandırma
  (aşama 1–4) tamamlanmıştı ve iç doğrulamaya hiç bakılmamıştı.
- Bu çalışma defteri ve sonuç dosyasını olduğu gibi devraldı. Yarım kalan
  bir tarama yoktu; hiçbir şey yeniden çalıştırılmadı. NOTLAR bölüm 6'ya
  bakın.
- Eklenenler:
  - Hizalama kontrolü.
  - Aşama 5 (18 yapılandırma).
  - Mekanik dondurma, tek seferlik iç doğrulama ve tanı.

## 12. Dosyalar

| Dosya | İçerik |
|---|---|
| `NOTLAR.md` | Plan, seçim kuralı, kesinti/devam, dondurma kararı (iç doğrulamadan önce) |
| `tara.py`, `egitim_sonuclari.jsonl`, `tara_5.log` | Eğitim taraması (aşama 1–5) |
| `egitim_ayrinti.py` | Eğitim içi coin/yıl/yön kırılımı |
| `hizalama.py`, `hizalama.log` | Konumlanma ölçüsü zaman damgası kontrolü (eğitim) |
| `dondurma.py`, `dondurma.log`, `dondurma.json` | Mekanik dondurma |
| `nedensellik.py`, `nedensellik.log` | `assert_causal` |
| `dogrulama.py`, `dogrulama.log`, `dondurulmus_sonuclar.json` | Tek seferlik iç doğrulama, candidate_check, DSR, al-tut |
| `dogrulama_tani.py`, `dogrulama_tani.log` | Dondurma sonrası betimleyici tanı |
| `../deneyler/t2_konumlanma.jsonl` | Deney defteri (510 satır: 490 arama + 20 dondurulmuş değerlendirme) |
