# t2_bindirme — Bindirmeler ve portföy kurgusu (Tur 2, protokol sürüm 2)

9 Ekim 2026. Plan, bileşen seçim kuralı ve dondurma kararı iç doğrulamadan
önce [`NOTLAR.md`](NOTLAR.md) dosyasına yazıldı (dondurma 17:18 UTC, ilk
dev_valid satırı 17:36 UTC). Kod: `grafik_analiz/strategies/t2_bindirme.py`.
Defter: `arastirma/tur2/deneyler/t2_bindirme.jsonl`.

## 1. Kısa sonuç

- Dört yapılandırma donduruldu ve iç doğrulamada (01.01.2025–30.09.2026) bir
  kez ölçüldü. **İkisi `candidate_check`'i geçti.** İkisi de trend ile
  zamanlanmış nakit-carry bindirmesi:
  - `t2_bindirme_trend_yarim_4h_L15_b0.15_f7`: 1× +%13,77, 2× +%11,57,
    Sharpe 0,58, alfa +%7,45 (t 0,93), beta 0,16, 55 işlem.
  - `t2_bindirme_trendvol_tam_4h_L10_h0.3_n30_b0.1_f7`: 1× +%18,84,
    2× +%16,00, Sharpe 0,69, alfa +%10,14 (t 1,08), beta 0,18, 98 işlem.
- Bu iki yapılandırmanın iç doğrulama günlük getiri korelasyonu **0,958**.
  Fiilen **tek bir fikir**.
- Kanıt zayıf:
  - Alfa t değerleri yaklaşık 1; istatistiksel olarak anlamlı değil.
  - Deflated Sharpe 0,076 ve 0,0945 (136 deneme). 0,95 eşiğinin çok altında.
  - Kâr birkaç güne yoğun. En iyi 10 gün çıkarılınca iki yapılandırmanın
    da iç doğrulama getirisi negatif (−%17,2 ve −%18,6).
- Kıyas ve portföy geçemedi:
  - Oynaklık yönetimli kıyas: −%13,31, alfa −%4,26.
  - Tur 1 bileşenlerinden kurulan eşit riskli portföy: −%1,50, alfa
    −%0,65. Eğitimdeki alfa t'si 5,79 idi; iç doğrulamada sıfıra indi.
- Al-tut (BTC/ETH/SOL eşit ağırlık) aynı dönemde %−18,9. En büyük düşüşü
  %−64,3.

## 2. Kurallar ve bir bulaşma uyarısı

- Bütün değerlendirmeler `evaluate()` ile yapıldı ve deftere yazıldı.
  Arama yalnız dev_train ile yapıldı.
- Ek alt dönem ölçüleri `ortak.py` yardımcısıyla hesaplandı:
  - 2020–2023 ve 2024 alfası.
  - Yıllık getiri ve yıllık işlem sayısı.
  - Bu yardımcı veriyi ve fonlamayı 31.12.2024'te keserek çalışır; dev_valid
    verisi yüklenmez.
- Holdout açılmadı, veri dosyaları doğrudan okunmadı, veri indirilmedi.
- **Bulaşma:** Araştırmacı başlangıçta okuması istenen `SONUC_1.md` ve
  `DENETIM_1.md` dosyalarını okudu. Bu dosyalar şunları içeriyor:
  - Tur 1 görülmemiş döneminde (2025-07 – 2026-09) piyasanın düştüğü bilgisi.
  - Tur 1 iç doğrulamasının (2024 – 2025-06) sonuçları.

  Bu dönemler sürüm 2'nin iç doğrulamasıyla örtüşüyor. Önlemler:
  - Portföy bileşenleri önceden yazılmış mekanik bir kuralla seçildi.
  - Bütün seçimler eğitim ölçüleriyle (alfa t, alt dönem alfası, işlem
    sayısı) yapıldı.
  - Denetimin dev_valid'e dayanan bileşen önerisi kullanılmadı.

  Yine de geçen iki yapılandırma düşük betalı ve trendle zamanlanmış korumalı
  (hedge). Bu tür stratejiler düşen piyasada avantajlıdır. Tasarım
  kararlarının bu bilgiden tamamen bağımsız olduğu kanıtlanamaz. Bu kararlar:
  - tarama 3'e hedef oynaklık 0,3'ün eklenmesi;
  - işlem şartının sıkılaştırılması.

  İkisinin de gerekçesi eğitim sonuçlarıdır; bkz. NOTLAR bölüm 5.

## 3. Yaklaşımlar

Ortak çerçeve: her coin için maruziyet sinyali E(t) ∈ [0, 1] ve onu kaldıraçsız
uygulayan bir yürütme biçimi.

**Sinyaller** (hepsi geriye dönük):

- `trend`: tur 1 trend topluluğu (N günlük getiri işareti, SMA üstü,
  EMA(N/4) > EMA(N), Donchian; N üç bakış süresi).
- `vol`: min(1, σ_hedef / σ_N). Coin başına uygulandığı için ters oynaklık
  ağırlığıdır.
- `trend_vol`: trend × vol.
- `sabit`: al-tut ve saf carry taban çizgileri.

**Yürütme biçimleri:**

- `nakit`: yalnız spot, her coin 1/3.
- `tam`: her coinde spot ve vadeli bacak, her biri 1/6.
  - Carry açıkken spot = 1, vadeli = 2E − 1.
  - Carry kapalıyken spot = min(1, 2E), vadeli = max(0, 2E − 1).
  - E = 0 iken saf nakit-carry, E = 1 iken tam uzun (uzunun yarısı vadeliden).
- `yarim`: aynı bacaklar; vadeli hiç uzun olmaz.
  - Carry açıkken spot = 1, vadeli = −(1 − E).
  - Carry kapalıyken spot = E, vadeli = 0.
  - Net maruziyet E/2; trendin kapalı kısmı nakit-carry'dir. Bu, görev
    tanımındaki "trend kapalıyken carry, açıkken spot uzun" kurgusu.
- **Carry süzgeci:**
  - `hep`: fonlama verisi başlayınca hep açık.
  - `f3`: 3 günlük ortalama fonlama 8 saatte 1e-4'ü geçince açık, 0'ın
    altında kapalı.
  - `f7`: 7 günlük ortalama 0,5e-4'ü geçince açık, −0,5e-4'ün altında kapalı.
  - Fonlama kaydı yalnız zaman damgası ≤ bar açılışı ise kullanılır.

**(a) Trend + carry:** trend × {nakit, tam, yarım}, 4 saatlik. Ayrıca
trend × vol × {nakit, tam, yarım}.

**(b) Oynaklık yönetimli maruziyet** (zamanlama yok; dürüst kıyas):
vol × nakit, günlük. Ayrıca vol × tam/yarım.

**(c) Önceden kaydedilmiş eşit riskli portföy:**

- Havuz: tur 1 dondurulmuş yapılandırmalarından bütün bacakları vadeli ve
  zaman dilimi 1s/4s/1g olan 19 yapılandırma.
- Seçim kuralı (bileşen sonuçlarından önce yazıldı):
  - eğitimde 1× ve 2× net > 0;
  - alfa > 0 ve alfa t ≥ 1;
  - 2020–23 ve 2024 alfaları > 0;
  - alfa t sırasıyla, korelasyon < 0,50 ile en fazla 4 bileşen.
- Ağırlık: b_k ∝ 1/σ_k.
- Uygulama: 1 saatlik vadeli BTC/ETH/SOL spec'i. Bileşenler kendi zaman
  dilimlerinde hesaplanır. Veri, verilen 1s verinin son kapanışına kadar
  açıkça kesilir.
- Vadeli bacak pozisyonu = kırp(3 · Σ b_k · w_kc · p_kc, −1, 1).

## 4. Parametre aralıkları ve deneme sayısı

| Tarama | Yapılandırma | İçerik |
|---|---:|---|
| 1 | 87 | Taban çizgileri:<br>• al-tut<br>• saf carry × {hep, f3, f7}<br>vol × nakit:<br>• σ_hedef {0,4; 0,6; 0,8}<br>• N {10, 20, 40, 80} gün<br>• bant {0; 0,1}<br>vol × {tam, yarım}:<br>• σ_hedef {0,4; 0,6}<br>• N {20, 40}<br>trend × {nakit, tam, yarım}:<br>• bakış {10/20/40, 20/40/80, 40/80/160} gün<br>• süzgeç {hep, f3, f7}<br>• bant {0; 0,15}<br>trend × vol:<br>• L20, σ_hedef {0,4; 0,6; 0,8} |
| 2 | 19 | Tur 1 bileşen havuzu, aynen |
| 3 | 22 | trend × vol:<br>• L10/L20<br>• σ_hedef {0,3; 0,4; 0,5}<br>• {nakit, tam+f7, yarım+f7}<br>trend × yarım + f7, L15 (15/30/60)<br>vol × {tam, yarım} + f7 |
| 4 | 4 | Portföy: eşit sermaye; eşit risk Σb=1; eşit risk σ 0,10 ve 0,20 |
| **Toplam** | **132 değerlendirme, 131 benzersiz yapılandırma** | Bir yapılandırma iki taramada tekrarlandı. |

Defterdeki dev_train 1× satırı: 136. Bunlar 132 arama satırı ve dondurulan
4 yapılandırmanın `evaluate(spec)` tekrarıdır. dev_valid'e 4 yapılandırma bir
kez bakıldı (8 satır: 1× ve 2×).

## 5. Eğitim (dev_train) sonuçları — ana varyantlar

Harness ölçüleri, 1× maliyet. Alfa ve beta, aynı piyasadaki BTC/ETH/SOL eşit
ağırlıklı al-tuta göre hesaplandı.

- Nakit biçimli spot yapılandırmalarının penceresi 2017-08'de başlar.
- Carry'li yapılandırmalar 2020'den önce pozisyon almaz. Spot bacak 2017'den
  başladığı için harness Sharpe'ı seyrelir.
- Portföy 2020-01'de başlar.
- Alt dönem alfaları (2020–23 ve 2024) yardımcıyla hesaplandı (2020+).

| Yapılandırma | Net 1× | Net 2× | Sharpe | Alfa | Alfa t | Beta | İşlem | Alfa 2020–23 | Alfa 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `altut_nakit_1d` | +%5967,9 | +%5960,6 | 1,15 | +%4,1 | 0,82 | 0,85 | 3 | −%2,7 | −%0,0 |
| `carry_saf_tam_4h_hep` | +%30,3 | +%30,2 | 1,29 | +%5,6 | 3,94 | −0,01 | 6 | +%5,9 | +%6,5 |
| `carry_saf_tam_4h_f3` | +%36,4 | +%33,3 | 6,59 | +%5,9 | 18,38 | −0,00 | 74 | +%6,4 | +%5,7 |
| `carry_saf_tam_4h_f7` | +%42,1 | +%39,9 | 4,65 | +%6,7 | 12,85 | −0,00 | 52 | +%7,2 | +%6,5 |
| `vol_nakit_1d_h0.4_n40_b0.1` | +%1067,2 | +%1051,4 | 1,14 | +%4,4 | 0,85 | 0,39 | 3 | −%1,2 | +%11,3 |
| `vol_nakit_1d_h0.6_n20_b0.1` | +%1681,6 | +%1635,3 | 1,05 | +%0,9 | 0,15 | 0,55 | 3 | −%3,3 | −%1,7 |
| `vol_nakit_1d_h0.8_n40_b0.1` | +%2858,1 | +%2833,3 | 1,10 | +%3,5 | 0,50 | 0,64 | 3 | −%4,3 | +%3,1 |
| `vol_yarim_1d_h0.4_n40_f7` | +%302,5 | +%297,6 | 1,30 | +%6,3 | 2,03 | 0,21 | 39 | +%3,1 | +%7,9 |
| `vol_tam_1d_h0.4_n40_f7` | +%859,0 | +%849,0 | 1,14 | +%6,1 | 0,97 | 0,42 | 53 | −%1,0 | +%9,2 |
| `trend_nakit_4h_L10_b0.15` | +%8025,8 | +%6450,6 | 1,69 | +%34,7 | 3,49 | 0,36 | 292 | +%41,1 | −%2,1 |
| `trend_nakit_4h_L20_b0.15` | +%7762,4 | +%6930,4 | 1,65 | +%33,2 | 3,35 | 0,38 | 141 | +%40,5 | −%5,9 |
| `trend_nakit_4h_L40_b0.15` | +%2936,8 | +%2773,4 | 1,34 | +%22,0 | 2,12 | 0,36 | 81 | +%32,4 | −%10,2 |
| `trend_tam_4h_L20_b0.15_f7` | +%3084,3 | +%2889,8 | 1,45 | +%31,1 | 2,59 | 0,43 | 302 | +%37,1 | −%8,8 |
| `trend_yarim_4h_L10_b0.15_f7` | +%658,5 | +%612,2 | 1,61 | +%20,0 | 3,25 | 0,20 | 173 | +%23,1 | +%1,8 |
| **`trend_yarim_4h_L15_b0.15_f7`** | +%747,9 | +%710,1 | 1,66 | +%21,4 | 3,49 | 0,21 | 135 | +%25,0 | +%1,3 |
| `trend_yarim_4h_L20_b0.15_f7` | +%675,1 | +%645,8 | 1,59 | +%19,2 | 3,18 | 0,21 | 118 | +%22,5 | −%1,0 |
| `trendvol_nakit_4h_L10_h0.3_n30_b0.1` | +%569,5 | +%521,1 | 1,71 | +%15,3 | 3,55 | 0,13 | 178 | +%15,8 | +%8,7 |
| **`trendvol_tam_4h_L10_h0.3_n30_b0.1_f7`** | +%442,9 | +%417,1 | 1,67 | +%18,5 | 3,46 | 0,14 | 197 | +%19,3 | +%11,1 |
| `trendvol_yarim_4h_L10_h0.3_n30_b0.1_f7` | +%183,0 | +%174,1 | 2,00 | +%12,6 | 4,66 | 0,07 | 67 | +%13,3 | +%8,8 |
| `trendvol_tam_4h_L10_h0.4_n30_b0.1_f7` | +%635,1 | +%588,5 | 1,55 | +%20,4 | 2,99 | 0,19 | 326 | +%21,0 | +%11,8 |
| `trendvol_tam_4h_L20_h0.3_n30_b0.1_f7` | +%442,5 | +%424,2 | 1,62 | +%17,1 | 3,25 | 0,16 | 174 | +%18,3 | +%6,7 |
| `portfoy_esit_sermaye` | +%617,3 | +%471,8 | 2,42 | +%38,2 | 5,07 | 0,02 | 1367 | +%43,5 | +%16,5 |
| **`portfoy_esit_risk_sermaye`** | +%441,6 | +%337,6 | 2,81 | +%31,3 | 5,79 | 0,03 | 1757 | +%35,3 | +%15,1 |
| `portfoy_esit_risk_h0.10` | +%1495,7 | +%990,4 | 2,74 | +%52,1 | 5,62 | 0,05 | 1757 | +%58,3 | +%27,3 |
| `portfoy_esit_risk_h0.20` | +%6192,7 | +%3358,0 | 2,61 | +%80,0 | 5,35 | 0,07 | 1757 | +%89,9 | +%40,2 |

Gözlemler (eğitim):

- **Oynaklık yönetimi tek başına alfa üretmedi.**
  - vol × nakit yapılandırmalarının alfa t'si −1,0 ile 0,85 arasında.
  - Beta σ_hedef ile ölçekleniyor. Bu saf beta ölçeklemedir.
  - Pozisyon sürekli olduğu için harness yalnız 3 işlem sayıyor.
- **Trend alfası 2020–2023'te güçlüydü, 2024'te kayboldu.**
  - 2020–23 alfası +%22 … +%41; 2024 alfası çoğunlukla negatif.
  - `tam` biçimi trend açıkken vadeli uzun bacakta fonlama ödüyor (2020+
    toplam %22–36). Bu yüzden nakit biçiminden kötü.
  - Yarım biçim carry ile 2024 alfasını sıfırın biraz üstünde tuttu.
- **Trend × oynaklık (σ_hedef ≤ 0,4) iki alt dönemde de pozitif alfalı.**
  - Hedef oynaklık düştükçe alfa t yükseliyor, çünkü carry payı büyüyor.
- **Saf carry eğitimde en yüksek alfa t'yi verdi**, ama:
  - Harness'te teminat, tasfiye ve bacaklar arası dengeleme maliyeti yok;
    bu yüzden Sharpe şişik.
  - Tur 1'in fonlama ailesinin fikri.
  - Dondurulmadı (plan bölüm 4).
- **Tanı 2 (eğitim): carry ağırlıklı biçimler sürekli pozitif fonlamada hiç
  pozisyon değiştirmiyor.**
  - Örnek: yarım h0,3 L10 f7 2024'te 0 işlem yaptı.
  - Bu nedenle işlem şartı, dev_valid'den önce, "2023 ve 2024'te ayrı ayrı
    ≥ 12 işlem" olarak sıkılaştırıldı.

## 6. Dondurulan yapılandırmalar ve gerekçe

Seçim ölçütü (NOTLAR bölüm 4 ve 6):

- Eğitimde 1× ve 2× net > 0.
- Alfa hem 2020–23 hem 2024'te > 0.
- 2023 ve 2024'te ayrı ayrı ≥ 12 işlem.
- Sıralama eğitim alfa t'sine göre; komşu parametrelerde pozitif alfa.

| # | Yapılandırma | Yaklaşım | Seçilme gerekçesi (yalnız eğitim) |
|---|---|---|---|
| 1 | `t2_bindirme_vol_nakit_1d_h0.4_n40_b0.1` | (b) kıyas | vol × nakit içinde en yüksek alfa t (0,85). Şartları geçmesi beklenmiyordu. |
| 2 | `t2_bindirme_trend_yarim_4h_L15_b0.15_f7` | (a) trend + carry | Trend biçimlerinde şartları geçenler içinde en yüksek alfa t (3,49). 2024 alfası küçük (+%1,3). 2023/2024 işlem: 22/17. |
| 3 | `t2_bindirme_trendvol_tam_4h_L10_h0.3_n30_b0.1_f7` | (a') trend × vol + carry | Carry'li ve işlem şartını geçenler içinde en yüksek alfa t (3,46). 2024 alfası +%11,1. Komşuları da pozitif. |
| 4 | `t2_bindirme_portfoy_esit_risk_sermaye` | (c) portföy | Portföy çeşitlerinde en yüksek alfa t (5,79). |

Beşinci hak kullanılmadı. Portföyün σ 0,10 çeşidi aynı bileşen ve ağırlık
oranlarına sahip, yalnız ölçeği farklı.

Portföy bileşenleri ve çarpanları:

| Bileşen | Çarpan |
|---|---:|
| `ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot` | 0,225 |
| `od_dip_ret4h_fut_port3_1h` | 0,454 |
| `kirilim_kanal4h_vadeli_iki` | 0,108 |
| `formasyon_ucgen_kama_4h_hacim_iki` | 0,213 |

Bileşenler arası eğitim korelasyonu −0,11 … 0,28.

**Nedensellik:** Dördü de `assert_causal`'ı geçti.

- Kesimler: 0,55, 0,8, 0,97, 0,3, 0,9 ve 0,995.
- Portföyde ayrıca ML aylık yeniden eğitiminden 2 saat sonrası
  (2024-03-01 02:00 UTC).
- Dosyalar: `dondurma_kontrol_1.log`, `dondurma_kontrol_2.log`.

Dondurulan parametreler defterdeki eğitim satırlarıyla birebir aynı. Eğitim
ölçüleri dogrulama çalışmasında aynen yeniden üretildi.

## 7. İç doğrulama (dev_valid, 01.01.2025–30.09.2026) — tek seferlik

| Yapılandırma | Net 1× | Net 2× | Sharpe 1× | Sharpe 2× | En büyük düşüş 1× | İşlem | Alfa | Beta | Alfa t | Bootstrap p | DSR | candidate_check |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `vol_nakit_1d_h0.4_n40_b0.1` | −%13,31 | −%13,60 | −0,01 | −0,02 | −%55,27 | 0 | −%4,26 | 0,64 | −0,69 | 0,50 | 0,014 | **GEÇMEDİ** |
| `trend_yarim_4h_L15_b0.15_f7` | +%13,77 | +%11,57 | 0,58 | 0,51 | −%16,25 | 55 | +%7,45 | 0,16 | 0,93 | 0,24 | 0,076 | **GEÇTİ** |
| `trendvol_tam_4h_L10_h0.3_n30_b0.1_f7` | +%18,84 | +%16,00 | 0,69 | 0,60 | −%19,10 | 98 | +%10,14 | 0,18 | 1,08 | 0,22 | 0,0945 | **GEÇTİ** |
| `portfoy_esit_risk_sermaye` | −%1,50 | −%4,73 | −0,11 | −0,41 | −%9,11 | 297 | −%0,65 | −0,00 | −0,14 | 0,57 | 0,010 | **GEÇMEDİ** |

2× maliyetle alfa:

| Yapılandırma | Alfa (2×) |
|---|---:|
| `vol_nakit` | −%4,46 |
| `trend_yarim` | +%6,33 |
| `trendvol_tam` | +%8,76 |
| `portfoy` | −%2,56 |

Şart bazında:

- **vol kıyası** geçemediği şartlar:
  - net getiri;
  - 2× maliyette net getiri;
  - Sharpe;
  - işlem sayısı (0);
  - dev_valid alfası.
- **Portföy** geçemediği şartlar:
  - net getiri;
  - 2× maliyette net getiri;
  - Sharpe;
  - dev_valid alfası.

  İşlem şartını geçti (297).
- **İki trend + carry yapılandırması** yedi şartın hepsini geçti. Sharpe
  0,58 ve 0,69; eşik 0,5'e yakın.

**Deflated Sharpe:**

- Deneme sayısı: defterdeki `pencere=="dev_train"` ve `maliyet_kat==1.0`
  satırları, 136.
- Eğitim Sharpe varyansı: 0,391.
- Sharpe, gün sayısı, çarpıklık ve basıklık iç doğrulamanın 1× ölçüleri.
- Hiçbiri anlamlı değil. En yüksek değer 0,0945.

**Al-tut kıyası** (aynı dönem, eşit ağırlıklı BTC/ETH/SOL):

| Piyasa | Getiri | Sharpe | En büyük düşüş |
|---|---:|---:|---:|
| Spot | −%18,94 | 0,10 | −%64,31 |
| Vadeli | −%18,93 | 0,10 | −%64,32 |

Geçen iki yapılandırma al-tutun 32,7 ve 37,8 puan üstünde. Bunun büyük kısmı düşük
betadan (0,16–0,18) geliyor. Alfa pozitif ama t ≈ 1.

**İç doğrulama günlük getiri korelasyonları** (betimleyici):

| Yapılandırma çifti | Korelasyon |
|---|---:|
| trend+carry ile trend×vol+carry | 0,958 |
| vol kıyası ile iki trend yapılandırması | 0,70 |
| portföy ile trend yapılandırmaları | 0,35–0,39 |

## 8. Betimleyici döküm (dev_valid'den sonra; yeniden ayar yok)

Kaynak: `dogrulama_tani.py`, `dogrulama_tani.txt`.

**Kâr fonlamadan değil, trendle zamanlanmış korumadan geldi.**

- İç doğrulamada toplam fonlama geliri küçük:
  - trend+carry: +%1,08;
  - trend×vol+carry: +%0,71.
- Spot bacaklar sürekli uzun ve toplamda hafif zararda.
- Vadeli kısa bacaklar düşüşlerde büyük ve kazançlı. ETH vadeli bacağının
  katkısı yaklaşık +%12 (ağırlıklı bar getirilerinin toplamı).

**Dönem dağılımı:**

| Dönem | trend+carry | trend×vol+carry | Vadeli al-tut |
|---|---:|---:|---:|
| 2025 ilk yarı | +%0,4 | +%1,6 | −%8,7 |
| 2025 ikinci yarı | +%5,4 | +%1,7 | −%6,1 |
| 2026 Ocak–Eylül | +%7,5 | +%15,0 | −%5,4 |

**Yoğunlaşma:**

- En iyi 5 gün toplamı +%20,1 / +%24,6.
- En iyi 10 gün çıkarılınca getiri −%17,2 / −%18,6.
- Harness'in `total_without_best` ölçüsü (en iyi tek işlem çıkınca) farklı:
  - trend+carry: 1× +%1,4, 2× −%0,55;
  - trend×vol+carry: 1× +%9,1, 2× +%6,5.

  İleriye dönük takipte Seviye 1'in 4. şartı bu ölçüye dayanıyor. Hedge'li
  ve çok bacaklı stratejide bu ölçü yanıltıcı olabilir (tur 1 denetimi 5.2).

**Portföy:** tur 1 bileşenlerinin eğitimdeki yüksek alfası (tur 1'in kendi
seçim dönemi 2017–2023 dahil) iç doğrulamaya taşınmadı. 297 işlemde maliyet
%3,3, net −%1,5.

## 9. Dürüst sonuç

1. **Oynaklık yönetimi tek başına alfa vermiyor.** Eğitimde alfa ≈ 0,
   iç doğrulamada −%4,3. Zamanlama stratejileri için kıyas bu.
2. **Tur 1 bileşenlerinin önceden kaydedilmiş eşit riskli portföyü
   başarısız oldu.** Eğitimde alfa t 5,79 idi. Bileşenlerin 2017–2023
   performansı tur 1'de seçim yanlılığıyla şişmişti; 2024 alfası şartı bunu
   ayıklamaya yetmedi.
3. **Trend ile zamanlanmış nakit-carry bindirmesi şartları geçti**, ama:
   - İki aday tek fikir (korelasyon 0,958).
   - Alfa t ≈ 1, DSR < 0,1.
   - Sharpe eşiğe yakın (0,58 / 0,69).
   - Kâr birkaç düşüş gününe yoğun.
   - İç doğrulama düşen bir piyasaydı (al-tut −%19, düşüş −%64). Düşük betalı
     ve trendle korunan bir yapı bu ortamda doğal olarak avantajlı.
   - Eğitimde trend alfasının 2024'te kaybolduğu da biliniyor.
   - Araştırmacının bu dönemin düşüşle geçtiğini önceden bilmesi tam olarak
     dışlanamaz (bölüm 2).

   Bu sonuç "kârlı ve piyasadan bağımsız" iddiası için yeterli değil.
   Yalnız ileriye dönük takip karar verebilir.
4. Harness sınırlamaları, carry'li yapılandırmaların gerçek uygulamasını
   etkiler:
   - Bacaklar her bar maliyetsiz dengeleniyor.
   - Spot/vadeli teminat aktarımı ve tasfiye riski yok.
   - Nakit faizi yok.

## 10. Dosyalar

| Dosya | İçerik |
|---|---|
| `NOTLAR.md` | Plan, seçim kuralı, arama günlüğü, dondurma kararı (dev_valid'den önce) |
| `ortak.py` | Eğitim içi yardımcılar (veri 31.12.2024'te kesik) |
| `tarama1.py`–`tarama4.py`, `tarama*.csv`, `tarama*.log` | Taramalar |
| `bilesen_gunluk.csv` | Bileşen eğitim günlük getirileri |
| `portfoy_secimi.json` | Mekanik bileşen seçimi |
| `tani1.*`, `tani2.*` | Eğitim içi işlem sayısı tanıları |
| `dondurma_kontrol.py`, `dondurma_kontrol_*.log` | Parametre eşleşmesi ve `assert_causal` |
| `dogrulama.py`, `dogrulama.log`, `dogrulama_sonuc.json` | Tek seferlik dev_valid |
| `dogrulama_tani.py`, `dogrulama_tani.txt` | dev_valid sonrası betimleyici döküm |
