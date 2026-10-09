# Tur 2 Denetimi — Bölüm D: Adayların güvenilirliği

9 Ekim 2026. Protokol sürüm 2 (`GRAFIK_ANALIZ_PROTOKOL=2`). Kapsam yedi aile:
`t2_cift`, `t2_konumlanma`, `t2_emir_akisi`, `t2_lead_lag`, `t2_limit_gun_ici`,
`t2_bindirme`, `t2_meta`. `t2_genis_evren` kapsam dışıdır.

Bu bölümde holdout açılmadı, `scope="holdout"` ya da `scope="all"` kullanılmadı,
30.09.2026 sonrası veri kullanılmadı. Deftere hiçbir satır yazılmadı. Bütün
hesaplar `evaluate` ile aynı adımlarla yapıldı: `load_data`, `compute_signals`,
`backtest`, `summarize`, `alpha_beta`. Değerlendirme `record=False` eşdeğeridir.
Veri `arastirma/veri_indir.py` ile sıfırdan indirildi.

Bölüm 3'teki duyarlılık çalıştırmaları **aday değildir**. Bunlar yalnız dolum ve
maliyet varsayımlarının etkisini ölçer.

## 0. Kısa sonuç

1. **Yeniden üretim tam.** 32 dondurulmuş yapılandırmanın hepsi yeniden hesaplandı.
   dev_train ve dev_valid getirileri, Sharpe, işlem sayısı ve alfa aile
   raporlarıyla aynı çıktı. `candidate_check`'i **10 yapılandırma** geçti. Bunlar
   raporlarda yazılanların aynısı.
2. **10 aday aslında 5 bağımsız bahis.** dev_valid günlük korelasyonları şöyle:
   - iki bindirme adayı 0,96;
   - iki çift adayı 0,91;
   - üç lead–lag adayı 0,69–0,91;
   - konumlanma D2 ile meta 0,62.
3. **Hiçbir aday çoklu deneme düzeltmesinden sonra anlamlı değil.** Aile içi
   deneme sayısıyla Deflated Sharpe en fazla 0,094. Tur 2'nin yedi ailesindeki
   2.345 denemeyle hepsi 0,0000.
   - Dondurulan 32 yapılandırmada eğitim Sharpe'ı ile iç doğrulama Sharpe'ı
     arasındaki sıra korelasyonu −0,22. Eğitimde iyi görünmek iç doğrulamada
     iyi olmayı öngörmedi.
   - 7 ailenin 4'ünde eğitimin en iyisi iç doğrulamada aile medyanının altında
     kaldı.
4. **Hiçbir adayın kârı piyasa betasından gelmiyor.** Sabit beta korumasından
   sonra getiriler neredeyse aynı kalıyor. Ama birçok adayın getirisi büyük
   piyasa hareketi günlerine bağlı. Treynor–Mazuy dışbükeylik t değerleri
   4–12 arasında: konumlanma D2, meta, lead–lag ve bindirme.
5. **Yoğunlaşma ağır.** En iyi 10 gün çıkarılınca 10 adayın 10'unda da iç
   doğrulama getirisi negatife dönüyor. En iyi 5 gün çıkarılınca 9'unda negatif.
6. **Limit emir varsayımı üç ailede belirleyici.**
   - `t2_limit_gun_ici` adayının kârının tamamı limit girişten geliyor. Aynı
     sinyal piyasa emriyle %−1,74.
   - Lead–lag `baz_5m_kendi` adayı, dolum için gereken geçiş 2 bps'ten 10 bps'e
     çıkınca %+16,6'dan %+7,8'e düşüyor. 25 bps'te %+0,4.
   - Çift adayları 25 bps'te %+3,1 ve %+1,6'ya iniyor.
7. **Karar:** 10 adaydan **hiçbiri "güvenilir" değil.** 6'sı "zayıf", 4'ü
   "güvenilir değil" (bölüm 7).
   - En iyi durumdaki küme lead–lag spot–vadeli baz kümesi: Sharpe 1,1–1,25,
     bootstrap p 0,025–0,040, eğitimin her yılı pozitif.
   - Bu kümenin kârı da 9–78 olay gününe dayanıyor. Tek bir gün (06.02.2026)
     yaklaşık +%9 getiriyor. Sonuç dolum varsayımına duyarlı.

## 1. Adaylar ve kısaltmalar

Aday tanımı: protokol 2'nin yedi şartlı `candidate_check`'i. Bu denetimde dev_valid
(01.01.2025–30.09.2026) ve dev_train için yeniden hesaplandı.

| Kod | Aile | Yapılandırma | Eğitim net | dev_valid 1× | dev_valid 2× | Sharpe | İşlem | Alfa (yıllık) | Alfa t | Beta | Bootstrap p |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| K1 | bindirme | `t2_bindirme_trend_yarim_4h_L15_b0.15_f7` | %+747,9 | %+13,77 | %+11,57 | 0,584 | 55 | %+7,45 | 0,93 | 0,163 | 0,245 |
| K2 | bindirme | `t2_bindirme_trendvol_tam_4h_L10_h0.3_n30_b0.1_f7` | %+442,9 | %+18,84 | %+16,00 | 0,686 | 98 | %+10,14 | 1,08 | 0,177 | 0,222 |
| K3 | çift | `t2_cift_1h_SOLBTC-SOLETH_..._k6_..._z_in5.0_max_bar6_limit_bps20.0...` (C) | %+31,0 | %+4,33 | %+3,80 | 0,725 | 55 | %+2,49 | 0,96 | −0,001 | 0,097 |
| K4 | çift | `t2_cift_1h_SOLBTC_..._k6_..._z_in5.0_max_bar6_limit_bps20.0...` (B) | %+65,5 | %+7,50 | %+6,77 | 0,909 | 28 | %+4,24 | 1,20 | 0,001 | 0,081 |
| K5 | konumlanma | `t2_konumlanma_kalabalik_1h_SEPET3_genel_w30_c1.0_cx0.0_s-1` (D2) | %+2.082,9 | %+24,23 | %+5,92 | 0,503 | 340 | %+21,04 | 0,67 | −0,018 | 0,265 |
| K6 | lead–lag | `t2_lead_lag_baz_5m_hepsi_w288_e5_t12_uzun_limt2b2` (#4) | %+137,2 | %+19,81 | %+18,91 | 1,247 | 48 | %+10,63 | 1,64 | 0,010 | 0,025 |
| K7 | lead–lag | `t2_lead_lag_baz_5m_kendi_w288_e6_t12_limt2b2` (#1) | %+98,4 | %+16,58 | %+14,55 | 1,125 | 113 | %+8,94 | 1,49 | 0,026 | 0,040 |
| K8 | lead–lag | `t2_lead_lag_sv_5m_hepsi_k4_e4_t12_uzun_limt2b2` (#5) | %+153,0 | %+17,19 | %+16,73 | 1,195 | 27 | %+9,32 | 1,57 | 0,009 | 0,031 |
| K9 | limit gün içi | `t2_limit_gun_ici_donus_1h_n4_e3_t50_H12_lim1.0s_m3` | %+230,9 | %+7,18 | %+5,74 | 0,809 | 45 | %+4,06 | 1,06 | 0,006 | 0,090 |
| K10 | meta | `t2_meta_1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0` | %+190,2 | %+25,72 | %+8,53 | 0,592 | 315 | %+17,15 | 0,78 | 0,011 | 0,231 |

`t2_emir_akisi` ailesinden aday çıkmadı; diğer 22 dondurulmuş yapılandırma da
şartları geçemedi. Kıyas (BTC/ETH/SOL eşit ağırlıklı vadeli al-tut) dev_valid'de
%−18,93, dev_train'de %+3.953.

Not: K4 (28) ve K8 (27), `FINALISTLER.md`'deki 30 işlem eşiğinin altında kalıyor.

## 2. Yoğunlaşma (dev_valid, 1× maliyet)

"En iyi k gün çıkınca": dev_valid'in en iyi k günlük getirisi çıkarılıp kalan
günler bileşik toplanınca elde edilen getiri. "En iyi 10 günün payı":
log getiri toplamı içinde en iyi 10 günün payı. %100'ü geçmesi, geri kalan
günlerin toplamının negatif olduğu anlamına gelir.

| Kod | Toplam | En iyi 1 gün çıkınca | 5 gün | 10 gün | En iyi 10 günün payı (log) | En iyi 10 gün / bütün kazançlı günler | Aktif gün | İşlem günü | En iyi gün |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| K1 | %+13,77 | %+8,31 | %−6,57 | %−17,23 | %247 | %22 | 625 | 48 | 08.05.2025 (%+5,05) |
| K2 | %+18,84 | %+10,76 | %−6,47 | %−18,62 | %219 | %24 | 626 | 73 | 19.08.2026 (%+7,30) |
| K3 | %+4,33 | %+0,76 | %−2,51 | %−3,89 | %194 | %97 | 27 | 21 | 20.01.2025 (%+3,54) |
| K4 | %+7,50 | %+2,48 | %−2,44 | %−4,53 | %164 | %99 | 20 | 14 | 20.01.2025 (%+4,90) |
| K5 | %+24,23 | %+6,54 | %−23,43 | %−44,69 | %373 | %18 | 631 | 243 | 05.02.2026 (%+16,60) |
| K6 | %+19,81 | %+9,96 | %−1,40 | %−5,50 | %131 | %100 | 16 | 16 | 06.02.2026 (%+8,96) |
| K7 | %+16,58 | %+7,39 | %+0,12 | %−5,67 | %138 | %71 | 78 | 78 | 06.02.2026 (%+8,56) |
| K8 | %+17,19 | %+7,56 | %−1,17 | %−2,58 | %116 | %100 | 9 | 9 | 06.02.2026 (%+8,96) |
| K9 | %+7,18 | %+3,86 | %−3,56 | %−6,53 | %197 | %83 | 40 | 31 | 20.01.2025 (%+3,20) |
| K10 | %+25,72 | %+12,48 | %−18,75 | %−40,05 | %324 | %29 | 429 | 199 | 19.08.2026 (%+11,77) |

### Çeyrek ve yıl dökümü (bileşik getiri, %)

| Kod | 25Ç1 | 25Ç2 | 25Ç3 | 25Ç4 | 26Ç1 | 26Ç2 | 26Ç3 | 2025 | 2026 (9 ay) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| K1 | −6,39 | +7,22 | +10,10 | −4,25 | −5,55 | −2,00 | +16,17 | +5,81 | +7,53 |
| K2 | −4,48 | +6,38 | +8,90 | −6,63 | −5,73 | −0,87 | +23,08 | +3,32 | +15,01 |
| K3 | +2,93 | +0,40 | −0,30 | −0,46 | +0,22 | −0,03 | +1,52 | +2,57 | +1,71 |
| K4 | +4,09 | +0,50 | −0,89 | −0,94 | +1,35 | −0,20 | +3,49 | +2,70 | +4,67 |
| K5 | +4,23 | +0,17 | +5,84 | −21,71 | +30,43 | +16,55 | −5,54 | −13,48 | +43,59 |
| K6 | −1,64 | −0,14 | 0,00 | +5,74 | +10,81 | +4,10 | 0,00 | +3,86 | +15,35 |
| K7 | +1,62 | +0,70 | +0,88 | −0,66 | +9,92 | +2,91 | +0,49 | +2,55 | +13,68 |
| K8 | −2,58 | +0,33 | 0,00 | +8,23 | +10,79 | 0,00 | 0,00 | +5,78 | +10,79 |
| K9 | +3,71 | −0,41 | +2,60 | −1,91 | +0,81 | +0,40 | +1,88 | +3,94 | +3,12 |
| K10 | +24,75 | +4,33 | +6,72 | −1,86 | +0,75 | −14,65 | +7,25 | +36,32 | −7,78 |

7 çeyrekte pozitif çeyrek sayısı: K1 3, K2 3, K3 4, K4 4, K5 5, K6 3 (2 çeyrek
işlemsiz), K7 6, K8 3 (3 çeyrek işlemsiz), K9 5, K10 5.

### Bacak (coin) katkısı

Bacağın ağırlıklı bar net getirilerinin toplamı (toplamsal, yüzde puan).
Parantez içinde bacağın işlem sayısı.

| Kod | BTC | ETH | SOL | Not |
|---|---:|---:|---:|---|
| K1 | spot −1,59 (3) / vadeli +3,71 (4) | spot −1,67 (5) / vadeli +12,17 (13) | spot +0,39 (17) / vadeli +1,54 (13) | Kâr vadeli kısa bacaklardan, en çok ETH'den; spot bacaklar eksi. Alınan fonlama %1,08. |
| K2 | spot −1,44 / vadeli +4,91 | spot −0,74 / vadeli +11,67 | spot −0,16 / vadeli +5,06 | Aynı yapı; ETH vadeli baskın. |
| K3 | −0,16 (14) | +1,31 (18) | +3,16 (23) | SOL bacağı baskın. |
| K4 | −0,48 (14) | — | +7,86 (14) | Kârın tamamı SOL bacağından; BTC yalnız koruma. |
| K5 | +10,44 (88) | −1,33 (142) | +27,61 (110) | Maliyet 15,94 yp, ödenen fonlama 1,23 yp. |
| K6 | +4,02 (16) | +7,09 (16) | +8,53 (16) | 16 olay günü; her olayda üç coin birlikte. |
| K7 | +1,67 (30) | +5,62 (59) | +9,29 (24) | |
| K8 | +2,69 (9) | +5,95 (9) | +8,66 (9) | 9 olay günü. |
| K9 | +1,77 (17) | +1,46 (14) | +4,02 (14) | |
| K10 | −3,46 (119) | +13,77 (109) | +19,27 (87) | Maliyet 14,70 yp. |

**Bulgu:** Bütün adaylarda kâr ya ağırlıkla SOL'den, ya da ETH vadeli kısa
bacaktan geliyor. İki bindirme adayında bu bacak ETH vadeli kısadır. SOL'ün
protokolün sabit evreninde olması (hayatta kalan yanlılığı, `DENETIM_1` bölüm 7)
sonuçları etkileyebilir.

## 3. Piyasa rejimi (dev_valid)

dev_valid'de kıyas %−18,93 getirdi. 324 gün yükselişti, 314 gün düşüştü.

- Beta ve alfa, harness'in `alpha_beta` hesabıdır.
- Yukarı ve aşağı beta, kıyasın pozitif ve negatif günlerinde ayrı ayrı yapılan
  OLS'tir.
- TM γ, Treynor–Mazuy regresyonundaki m² katsayısıdır:
  r = a + b·m + γ·m². γ > 0, kazancın büyük piyasa hareketlerine (iki yönde de)
  bağlı olduğunu gösterir.
- Sabit beta koruması: r − β·m.
- Kayan beta koruması: önceki 90 günün betasıyla, ileriye bakmadan.

| Kod | Beta | Alfa | Alfa t | Korelasyon | Yukarı gün ort. | Aşağı gün ort. | Yukarı beta | Aşağı beta (se) | TM γ (t) | Betanın toplam katkısı | Sabit beta korumalı | Kayan beta korumalı |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| K1 | 0,163 | %+7,45 | 0,93 | 0,68 | +44,3 bps | −41,0 bps | 0,171 | 0,089 (0,013) | 0,38 (4,14) | +1,69 yp | %+12,80 (Sh 0,70) | %+15,91 (Sh 0,83) |
| K2 | 0,177 | %+10,14 | 1,08 | 0,65 | +49,3 | −44,6 | 0,189 | 0,086 (0,015) | 0,46 (4,25) | +1,83 | %+17,82 (0,82) | %+18,27 (0,83) |
| K3 | −0,001 | %+2,49 | 0,96 | −0,03 | −0,4 | +1,8 | 0,000 | 0,004 (0,006) | 0,01 (0,26) | −0,01 | %+4,34 (0,73) | %+3,75 (0,63) |
| K4 | 0,001 | %+4,24 | 1,20 | 0,02 | +0,3 | +2,1 | 0,007 | 0,006 (0,009) | 0,05 (1,27) | +0,01 | %+7,49 (0,91) | %+6,83 (0,83) |
| K5 | −0,018 | %+21,04 | 0,67 | −0,03 | +10,9 | +0,4 | 0,209 | −0,382 (0,061) | 2,91 (8,38) | −0,18 | %+24,46 (0,51) | %+6,53 (0,30) |
| K6 | 0,010 | %+10,63 | 1,64 | 0,07 | +2,5 | +3,4 | 0,051 | −0,012 (0,009) | 0,41 (5,54) | +0,11 | %+19,69 (1,24) | %+17,09 (1,06) |
| K7 | 0,026 | %+8,94 | 1,49 | 0,19 | +4,2 | +0,7 | 0,061 | 0,023 (0,008) | 0,28 (4,00) | +0,27 | %+16,29 (1,13) | %+15,15 (1,00) |
| K8 | 0,009 | %+9,32 | 1,57 | 0,07 | +2,1 | +3,1 | 0,050 | −0,016 (0,007) | 0,42 (6,23) | +0,09 | %+17,09 (1,19) | %+13,46 (0,92) |
| K9 | 0,006 | %+4,06 | 1,06 | 0,07 | +1,8 | +0,4 | 0,002 | 0,017 (0,008) | −0,08 (−1,80) | +0,06 | %+7,12 (0,80) | %+6,50 (0,73) |
| K10 | 0,011 | %+17,15 | 0,78 | 0,02 | +4,8 | +4,6 | 0,278 | −0,288 (0,038) | 2,76 (11,94) | +0,12 | %+25,58 (0,59) | %+16,74 (0,44) |

Yorum:

- **Basit bir koruma sonucu açıklamıyor.** Kıyası adayın betasıyla açığa satmak
  getiriyi en fazla 1–2 yp değiştiriyor. Bindirme adaylarında sabit beta
  korumalı getiri %+12,8 ve %+17,8. Düşen piyasada pozitif beta, getiriye
  ortalamada katkı değil, kayıp olarak yansıdı.
- **Ama kâr piyasa hareketinin büyüklüğüne bağlı.**
  - K5 ve K10 yükselişte pozitif, düşüşte negatif betalı. Yukarı beta 0,21 ve
    0,28; aşağı beta −0,38 ve −0,29. Bu, uzun oynaklık ya da trend profili.
    γ'nın t değeri 8,4 ve 11,9.
  - Kayan beta korumasından sonra K5 %+6,5 (Sharpe 0,30), K10 %+16,7 (0,44)
    kalıyor. Kârın bir kısmı zamana göre değişen yönlü maruziyetten geliyor.
- **Bindirme (K1, K2):** trend zamanlaması nedeniyle aşağı beta (0,09) yukarı
  betanın (0,17–0,19) yaklaşık yarısı.
  - Doğrusal alfa büyük ölçüde bu asimetriden geliyor (TM γ t ≈ 4,1–4,3).
  - Bu, genel bir trend zamanlama primidir. Bindirmeye özgü bir kenar
    olduğunu göstermez.
  - Düşen ama sert dalgalanan bir dönemde (dev_valid) bu profil avantajlıdır.
- **Lead–lag (K6–K8):** beta ≈ 0. Ama kâr büyük hareket günlerinde (çöküş anında
  uzun) geliyor; γ t değeri 4,0–6,2.
- **K3, K4 ve K9:** piyasa hareketiyle neredeyse ilişkisiz (γ t 0,3–1,8). Ama
  kâr az sayıda günde.

## 4. Maliyet ve yürütme

### 4.1 Maliyet katı (dev_valid)

| Kod | 1× | 2× | 3× (duyarlılık) | Sharpe 1× / 2× / 3× | Toplam maliyet (1×) | Ödenen fonlama | Maliyet öncesi (yaklaşık) | Maruziyet |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| K1 | %+13,77 | %+11,57 | %+9,41 | 0,58 / 0,51 / 0,43 | 1,95 yp | −1,08 (alındı) | +15,6 | %97 |
| K2 | %+18,84 | %+16,00 | %+13,23 | 0,69 / 0,60 / 0,52 | 2,41 | −0,71 | +21,3 | %98 |
| K3 | %+4,33 | %+3,80 | %+3,29 | 0,73 / 0,65 / 0,56 | 0,50 | −0,12 | +4,7 | %1,0 |
| K4 | %+7,50 | %+6,77 | %+6,04 | 0,91 / 0,83 / 0,75 | 0,69 | −0,20 | +7,9 | %0,6 |
| K5 | %+24,23 | %+5,92 | **%−9,69** | 0,50 / 0,28 / 0,07 | 15,94 | +1,23 | +53,8 | %96 |
| K6 | %+19,81 | %+18,91 | %+18,01 | 1,25 / 1,20 / 1,16 | 0,76 | 0,00 | +19,5 | %0,1 |
| K7 | %+16,58 | %+14,55 | %+12,56 | 1,13 / 1,00 / 0,88 | 1,76 | −0,01 | +17,6 | %0,6 |
| K8 | %+17,19 | %+16,73 | %+16,27 | 1,20 / 1,17 / 1,15 | 0,39 | 0,00 | +16,8 | %0,06 |
| K9 | %+7,18 | %+5,74 | %+4,33 | 0,81 / 0,66 / 0,51 | 1,35 | +0,03 | +8,5 | %2,4 |
| K10 | %+25,72 | %+8,53 | **%−6,32** | 0,59 / 0,30 / 0,02 | 14,70 | +1,31 | +46,1 | %48 |

"Maliyet öncesi", günlük net getirilerin toplamına maliyet ve fonlamanın
eklenmesidir (toplamsal, yaklaşık). "Maruziyet", pozisyonda geçen bar oranıdır.

**Bulgu:** K5 ve K10 yüksek cirolu. Maliyet, maliyet öncesi kârın yaklaşık üçte
birini yiyor. 3× maliyette ikisi de zarara dönüyor. Gerçekçi bir kayma
belirsizliği (2 bps varsayımı) bu iki adayın sonucunu tek başına
değiştirebilir.

### 4.2 Limit emir dolumları (dev_valid)

Harness'in `_backtest_limit` döngüsü denetim betiğinde bire bir kopyalandı. Her
bacakta kopyanın pozisyonu harness pozisyonuyla aynı çıktı (`replica_ok`). Her
pozisyon değişim girişimi dört gruba ayrıldı:

- piyasa emri (limit yok);
- hemen işleyen limit;
- dolan limit;
- dolmayan limit (iptal; o barda pozisyon değişmez).

| Kod | Bacak | Piyasa | Hemen | Doldu | Dolmadı | Dolum / limit denemesi | Cironun maker payı |
|---|---|---:|---:|---:|---:|---:|---:|
| K3 | BTC / ETH / SOL | 3 / 2 / 3 | 0 / 0 / 0 | 25 / 34 / 52 | 8 / 5 / 16 | %76 / %87 / %76 | %89 / %94 / %94 |
| K4 | BTC / SOL | 3 / 2 | 0 / 0 | 25 / 26 | 8 / 8 | %76 / %76 | %89 / %93 |
| K6 | BTC / ETH / SOL | 2 / 1 / 1 | 0 / 3 / 0 | 30 / 28 / 31 | 10 / 5 / 4 | %75 / %85 / %89 | %94 / %88 / %97 |
| K7 | BTC / ETH / SOL | 3 / 4 / 0 | 1 / 4 / 1 | 55 / 108 / 45 | 16 / 21 / 3 | %77 / %84 / %94 | %92 / %92 / %98 |
| K8 | BTC / ETH / SOL | 2 / 0 / 0 | 0 / 0 / 0 | 16 / 18 / 18 | 8 / 2 / 1 | %67 / %90 / %95 | %89 / %100 / %100 |
| K9 | BTC / ETH / SOL | 17 / 14 / 14 | 0 / 0 / 0 | 17 / 14 / 14 | 12 / 15 / 20 | %59 / %48 / %41 | %50 / %50 / %50 |

- K3, K4, K6, K7 ve K8'de ciroların %88–100'ü maker dolumla gerçekleşiyor.
- K9'da girişlerin hepsi limit, çıkışların hepsi piyasa emri. Limit girişlerin
  %41–59'u doluyor.

### 4.3 Dolum varsayımına duyarlılık (aday değil, `record=False`)

Spec parametreleri ya da harness sabiti yalnız bellekte değiştirildi; dosyalar
değişmedi. Dört varyant ölçüldü:

- **Piyasa emri:** çift ve lead–lag'de `limit_bps=None`, limit gün içinde
  `giris="piyasa"`. Sonuncusu, ailenin önceden kayıtlı kontrolüyle aynı
  kuraldır.
- **Daha sıkı dolum:** limitin dolması için gereken geçiş 2 bps yerine 10 bps
  ve 25 bps (`LIMIT_PENETRATION`). Limit gün içi modülünün motoru da aynı
  değerle yamalandı.
- **Maker = taker:** limit dolumları taker komisyonu ve 2 bps kayma öder.

| Kod | Temel 1× | Piyasa emri 1× / 2× | Geçiş 10 bps | Geçiş 25 bps | Dolumda taker maliyeti |
|---|---:|---:|---:|---:|---:|
| K3 | %+4,33 (Sh 0,73) | %+4,17 / %+2,63 | %+3,26 (0,54) | %+1,57 (0,28) | %+3,30 (0,57) |
| K4 | %+7,50 (0,91) | %+6,56 / %+4,49 | %+5,91 (0,73) | %+3,06 (0,40) | %+6,14 (0,77) |
| K6 | %+19,81 (1,25) | %+21,71 / %+19,01 | %+12,34 (0,83) | %+7,37 (0,61) | %+18,04 (1,16) |
| K7 | %+16,58 (1,13) | %+16,78 / %+10,79 | %+7,83 (0,58) | %+0,43 (0,07) | %+12,55 (0,89) |
| K8 | %+17,19 (1,20) | %+18,52 / %+17,03 | %+12,34 (0,86) | %+7,60 (0,67) | %+16,18 (1,15) |
| K9 | %+7,18 (0,81) | **%−1,74 / %−4,15** | %+6,22 (0,71) | %+3,73 (0,45) | %+6,38 (0,73) |

Aynı varyantlar dev_train'de de ölçüldü. Bazı sonuçlar:

- K7'de 25 bps geçişle dev_train getirisi %+98,4'ten %+2,3'e iniyor (Sharpe
  0,10).
- K9'da piyasa emriyle dev_train %+181,7.

Yorum:

- **K9:** Sinyal tek başına dev_valid'de kenar göstermiyor; piyasa emriyle
  zarar. Kâr, 1σ altındaki limit girişinin fiyat avantajından geliyor. Bu
  avantaj ancak emirlerin yaklaşık yarısı dolduğunda oluşuyor. Ters seçilimin
  harness'in bar verisiyle ölçülebildiğinden büyük olması durumunda sonuç
  kaybolur.
- **K7:** Kâr maker dolumun fiyatına duyarlı. Dolum için gereken geçiş 10 bps
  olunca yarıya, 25 bps olunca sıfıra iniyor. 5m'de, bazın aşırı açıldığı
  çöküş anlarında kapanış fiyatından limit emrin 2 bps geçişle dolduğunu
  varsaymak iyimser olabilir.
- **K6 ve K8:** Piyasa emriyle de sonuç aynı ya da daha iyi. Bu iki adayın kârı
  limit varsayımından değil, olay seçiminden geliyor. Ancak 10 bps geçişte
  sonuç üçte bir azalıyor; ana çöküş barlarında dolum sırası belirleyici.
- **K3 ve K4:** Piyasa emriyle 2× maliyette %+2,6 ve %+4,5'e iniyor. Getiriler
  zaten çok küçük.

## 5. Çoklu deneme

### 5.1 Deflated Sharpe

`grafik_analiz.research.metrics.deflated_sharpe` ile hesaplandı. Girdiler:
dev_valid Sharpe'ı, 638 gün, dev_valid çarpıklık ve basıklığı.

- **Aile:** deneme sayısı N, defterde `pencere == "dev_train"` ve
  `maliyet_kat == 1.0` olan satırlar. Varyans bu satırların yıllık Sharpe
  varyansı. Aile raporlarının tarifiyle aynı.
- **Tur:** yedi ailenin aynı satırlarının toplamı, N = 2.345. Havuz Sharpe
  varyansı 2,372. Bu varyans, `t2_emir_akisi` (4,60) ve `t2_limit_gun_ici`
  (4,88) ailelerindeki çok kötü keşif denemeleriyle büyüyor.
- **SR0:** N denemede şansla beklenen en yüksek yıllık Sharpe.

| Kod | N aile | Varyans | SR0 | DSR (aile) | DSR (tur, N=2.345) | PSR (N=1, düzeltmesiz) | Eğitim Sharpe sırası ailede | Çarpıklık | Basıklık |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| K1 | 136 | 0,391 | 1,65 | 0,076 | 0,0000 | 0,78 | 25/136 (üst %18) | 1,1 | 11,5 |
| K2 | 136 | 0,391 | 1,65 | 0,095 | 0,0000 | 0,83 | 20/136 (%15) | 1,8 | 17,2 |
| K3 | 639 | 0,632 | 2,48 | 0,002 | 0,0000 | 0,88 | 8/639 (%1,3) | 11,4 | 262,7 |
| K4 | 639 | 0,632 | 2,48 | 0,001 | 0,0000 | 0,96 | 1/639 (%0,2) | 14,2 | 274,7 |
| K5 | 250 | 0,765 | 2,48 | 0,004 | 0,0000 | 0,75 | 24/250 (%9,6) | 1,2 | 10,0 |
| K6 | 366 | 1,368 | 3,46 | 0,0000 | 0,0000 | 0,997 | 2/366 (%0,5) | 14,1 | 263,2 |
| K7 | 366 | 1,368 | 3,46 | 0,0000 | 0,0000 | 0,98 | 46/366 (%13) | 12,8 | 268,2 |
| K8 | 366 | 1,368 | 3,46 | 0,0000 | 0,0000 | 0,998 | 22/366 (%6) | 16,9 | 361,3 |
| K9 | 157 | 4,882 | 5,93 | 0,0000 | 0,0000 | 0,87 | 11/157 (%7) | 3,2 | 101,4 |
| K10 | 191 | 0,338 | 1,60 | 0,084 | 0,0000 | 0,79 | 46/191 (%24) | 2,5 | 17,6 |

### 5.2 Varsayımlara duyarlılık

Deneme varyansı keşif denemeleriyle şiştiği için ayrıca daha hoşgörülü
girdilerle hesaplandı:

- varyans 0,256: dondurulan 32 yapılandırmanın dev_valid Sharpe varyansı;
- varyans 0,391: en düşük aile varyanslarından biri, bindirme;
- etkin deneme sayısı N ∈ {10, 32, 100, 2.345}.

| Kod | N=10, V=0,256 | N=32, V=0,256 | N=100, V=0,256 | N=100, V=0,391 | N=2.345, V=0,256 |
|---|---:|---:|---:|---:|---:|
| K1 | 0,39 | 0,26 | 0,18 | 0,09 | 0,06 |
| K2 | 0,44 | 0,30 | 0,21 | 0,11 | 0,07 |
| K3 | 0,45 | 0,29 | 0,18 | 0,08 | 0,05 |
| K4 | 0,59 | 0,39 | 0,24 | 0,10 | 0,05 |
| K5 | 0,35 | 0,23 | 0,15 | 0,07 | 0,05 |
| K6 | **0,84** | 0,66 | 0,47 | 0,23 | 0,13 |
| K7 | 0,74 | 0,55 | 0,38 | 0,19 | 0,11 |
| K8 | 0,83 | 0,63 | 0,42 | 0,17 | 0,08 |
| K9 | 0,51 | 0,36 | 0,26 | 0,14 | 0,09 |
| K10 | 0,39 | 0,26 | 0,17 | 0,09 | 0,05 |

En hoşgörülü varsayımda bile (yalnız 10 etkin deneme) hiçbir aday 0,95'e
yaklaşmıyor. En yüksek değer K6'da 0,84.

Lead–lag adaylarının düzeltmesiz PSR'si (0,98–0,998) yüksek. Bunun nedeni çok
yüksek pozitif çarpıklık (12–17). Formül, pozitif çarpıklığı Sharpe'ın
güvenilirliğini artıran bir etken olarak sayar. Bu, 9–78 olay gününe dayanan
bir seride iyimser bir okumadır.

### 5.3 Aşırı uyum (PBO tarzı) görünüm

Tam CSCV için her denemenin günlük getirisi gerekir; defterde yok. Bu yüzden
dondurulan 32 yapılandırma üzerinden tek bölmeli bir görünüm hesaplandı:

- **Ortalama Sharpe:** eğitimde 1,53, iç doğrulamada 0,23. Dondurulanların
  %66'sının iç doğrulama Sharpe'ı > 0. Hiçbirinin iç doğrulama alfa t'si 2'yi
  geçmiyor.
- **Sıra korelasyonu (Spearman):** eğitim Sharpe'ı ile iç doğrulama Sharpe'ı
  arasında −0,22 (p 0,22). Alfa t için −0,03. Eğitim sırası iç doğrulama
  sırasını öngörmedi.
- **Eğitimin en iyisi:** her ailenin eğitimde en iyi dondurulan yapılandırması,
  7 ailenin 4'ünde iç doğrulamada aile medyanının altında kaldı. Bu, PBO ≈ 0,57
  tahminine karşılık gelir. 0,5 civarı, seçimin rastgele seçimden iyi
  olmadığını gösterir.

| Aile | Eğitimin en iyisi | Onun dev_valid Sharpe'ı | Aile dev_valid medyanı | Medyan altında |
|---|---|---:|---:|---|
| bindirme | `portfoy_esit_risk_sermaye` | −0,11 | 0,29 | evet |
| çift | B (K4) | 0,91 | 0,73 | hayır |
| emir akışı | `kontrol_getiri_donus_5m` | 0,36 | 0,18 | hayır |
| konumlanma | D1 (`kalabalik_w7`) | −0,11 | 0,01 | evet |
| lead–lag | #4 (K6) | 1,25 | 1,13 | hayır |
| limit gün içi | `fitil_5m_k8` | −0,46 | −0,18 | evet |
| meta | `4h_kanal_n20` | 0,10 | 0,19 | evet |

Lead–lag, çift ve emir akışı ailelerinde eğitimin en iyisi iç doğrulamada da ailenin
üstünde kaldı (emir akışında yine de aday çıkmadı). Lead–lag ve çiftte seçim sürecinin zayıf ama tutarlı bir bilgi
taşıdığı görülüyor. Konumlanma, limit gün içi ve meta ailelerinde eğitimin en
güçlü sonuçları iç doğrulamada kayboldu.

## 6. Bağımlılık: adaylar arası korelasyon (dev_valid günlük getiri, 1×)

|  | K1 | K2 | K3 | K4 | K5 | K6 | K7 | K8 | K9 | K10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| K1 | 1,00 | **0,96** | −0,09 | −0,04 | 0,19 | −0,04 | 0,05 | −0,05 | 0,10 | 0,26 |
| K2 | **0,96** | 1,00 | −0,08 | −0,03 | 0,23 | −0,05 | 0,06 | −0,05 | 0,11 | 0,30 |
| K3 | −0,09 | −0,08 | 1,00 | **0,91** | −0,05 | −0,04 | −0,05 | −0,04 | 0,40 | −0,06 |
| K4 | −0,04 | −0,03 | **0,91** | 1,00 | −0,02 | 0,01 | 0,01 | 0,01 | 0,38 | −0,02 |
| K5 | 0,19 | 0,23 | −0,05 | −0,02 | 1,00 | 0,01 | −0,03 | 0,01 | −0,07 | **0,62** |
| K6 | −0,04 | −0,05 | −0,04 | 0,01 | 0,01 | 1,00 | **0,70** | **0,91** | −0,05 | −0,02 |
| K7 | 0,05 | 0,06 | −0,05 | 0,01 | −0,03 | **0,70** | 1,00 | **0,69** | 0,07 | −0,08 |
| K8 | −0,05 | −0,05 | −0,04 | 0,01 | 0,01 | **0,91** | **0,69** | 1,00 | −0,06 | −0,03 |
| K9 | 0,10 | 0,11 | 0,40 | 0,38 | −0,07 | −0,05 | 0,07 | −0,06 | 1,00 | −0,03 |
| K10 | 0,26 | 0,30 | −0,06 | −0,02 | **0,62** | −0,02 | −0,08 | −0,03 | −0,03 | 1,00 |

Fiilen aynı bahis olan kümeler (korelasyon ≥ 0,6):

1. **Trendle zamanlanmış carry:** K1 ve K2 (0,96).
2. **SOL yayılım şoku dönüşü:** K3 ve K4 (0,91). İkisinin de en iyi günü
   20.01.2025. K9 ile korelasyonları 0,38–0,40; üçü de 20.01.2025'te en büyük
   kazancını yaptı.
3. **Konumlanma ve meta:** K5 ve K10 (0,62). İkisi de yüksek cirolu, iki yönlü
   ve dışbükey profilli. Ortak aktif gün sayısı 425.
4. **Spot–vadeli baz ayrışması (çöküşte alım):** K6, K7 ve K8 (0,69–0,91).
   K8'in 9 olay gününün 7'si K6'nın da olay günü. 06.02.2026 üçünün de en iyi
   günü.
5. **Trendde dip alımı, limit giriş:** K9.

Seyrek işlem yapan adaylarda (K3, K4, K6, K8) korelasyon katsayısı çok az
sayıda ortak aktif güne dayanıyor. Bu yüzden katsayının kendisi de belirsiz.

## 7. Kalıcılık (dev_train → dev_valid ve yıl yıl)

### 7.1 Dönem karşılaştırması

| Kod | Eğitim Sharpe | Eğitim alfa | Eğitim alfa t | dev_valid Sharpe | dev_valid alfa | dev_valid alfa t | Sharpe oranı (valid/eğitim) |
|---|---:|---:|---:|---:|---:|---:|---:|
| K1 | 1,66 | %+21,4 | 3,49 | 0,58 | %+7,5 | 0,93 | 0,35 |
| K2 | 1,68 | %+18,5 | 3,46 | 0,69 | %+10,1 | 1,08 | 0,41 |
| K3 | 0,88 | %+6,6 | 2,36 | 0,73 | %+2,5 | 0,96 | 0,82 |
| K4 | 1,10 | %+12,1 | 2,84 | 0,91 | %+4,2 | 1,20 | 0,83 |
| K5 | 1,79 | %+67,3 | 3,89 | 0,50 | %+21,0 | 0,67 | 0,28 |
| K6 | 1,66 | %+19,8 | 4,15 | 1,25 | %+10,6 | 1,64 | 0,75 |
| K7 | 1,29 | %+15,5 | 3,12 | 1,13 | %+8,9 | 1,49 | 0,87 |
| K8 | 1,36 | %+23,0 | 3,65 | 1,20 | %+9,3 | 1,57 | 0,88 |
| K9 | 1,87 | %+22,0 | 3,74 | 0,81 | %+4,1 | 1,06 | 0,43 |
| K10 | 0,83 | %+26,8 | 1,92 | 0,59 | %+17,2 | 0,78 | 0,71 |

### 7.2 Yıl yıl Sharpe (alfa t)

Kıyasa göre yıllık regresyon. Yalnız pozisyon alınan yıllar.

| Kod | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|---|
| K1 | 2,63 (1,98) | 3,58 (1,81) | −1,18 (−0,50) | 2,33 (−0,27) | 1,24 (0,14) | 0,45 (0,55) | 0,79 (0,80) |
| K2 | 3,21 (2,72) | 3,51 (1,73) | −1,54 (−0,96) | 2,46 (0,17) | 1,68 (1,00) | 0,30 (0,33) | 1,10 (1,16) |
| K3 | 1,29 (1,27) | 1,20 (1,85) | 2,31 (2,11) | −0,60 (−0,62) | −0,16 (−0,26) | 0,62 (0,62) | 1,20 (1,05) |
| K4 | 1,27 (1,26) | 1,23 (1,90) | 2,28 (2,10) | −0,09 (−0,08) | 1,04 (0,95) | 0,53 (0,52) | 1,72 (1,48) |
| K5 | 1,34 (1,28) | 3,10 (3,08) | 1,85 (2,08) | 2,74 (2,26) | 0,93 (1,32) | −0,14 (−0,14) | 1,37 (1,20) |
| K6 | 1,00 (1,23) | 3,14 (3,89) | 0,76 (0,66) | 2,08 (2,54) | 1,23 (1,36) | 0,73 (0,74) | 1,71 (1,48) |
| K7 | −0,34 (−0,35) | 1,35 (2,08) | 1,99 (1,94) | 2,43 (2,33) | 0,98 (1,06) | 0,47 (0,46) | 1,69 (1,48) |
| K8 | 1,00 (1,23) | 2,21 (3,16) | 1,05 (0,82) | 1,74 (1,89) | 1,12 (1,22) | 1,16 (1,18) | 1,35 (1,17) |
| K9 | 1,91 (1,80) | 2,98 (2,31) | 0,21 (0,26) | 2,40 (2,25) | 2,11 (1,90) | 0,63 (0,62) | 2,09 (1,80) |
| K10 | 0,29 (0,03) | 0,40 (−0,59) | 0,98 (0,41) | 1,42 (0,56) | 1,30 (1,03) | 1,22 (1,22) | −0,22 (−0,19) |

Gözlemler:

- **Bindirme (K1, K2):**
  - Alfanın büyüğü 2020–2021'den geliyor.
  - 2022'de iki aday da zarar etti (Sharpe −1,2 / −1,5). Oysa 2022 düşen bir
    yıldı ve dev_valid'e benzer bir rejimdi.
  - 2023'te alfa ≈ 0. Getiri betadan geliyor (beta 0,32–0,34).
  - Düşen piyasada korumanın kazandırdığı varsayımı 2022'de tutmadı.
- **Konumlanma D2 (K5):** Eğitimin her yılı güçlüydü. dev_valid'de 2025 negatif
  (%−13,5). Kârın tamamı 2026'nın ilk yarısından geliyor: 26Ç1 +%30, 26Ç2 +%17.
- **Meta (K10):** 2021 alfası negatif, 2025 +%36, 2026 %−7,8. Yıllar arasında
  tutarlılık zayıf.
- **Lead–lag (K6–K8) ve K9:**
  - 2021–2024'ün her yılında pozitifler.
  - dev_valid'in iki yılında da pozitifler.
  - Sharpe oranı (valid/eğitim) K6–K8'de 0,75–0,88, en kalıcı grup bu.
  - Ama yıllık olay sayısı az: K8'de 2025'te 7, 2026'da 2 aktif gün.
- **Çift (K3, K4):** 2023 eğitimde negatif; kârın çoğu 2021–2022'den.

## 8. Hüküm

Ölçütler:

- **Güvenilir:** çoklu deneme düzeltmesinden sonra da anlamlı; birkaç güne
  bağlı değil; maliyet ve yürütme varsayımlarına dayanıklı; yıllar arasında
  tutarlı.
- **Zayıf:** pozitif ve kısmen tutarlı, ama istatistiksel olarak ayırt
  edilemiyor ya da varsayımlara duyarlı.
- **Güvenilir değil:** sonuç bir döneme, birkaç güne ya da maliyet
  varsayımına bağlı; eğitimden iç doğrulamaya belirgin çöküş var.

| Kod | Hüküm | Lehte | Aleyhte |
|---|---|---|---|
| K6 `baz_5m_hepsi_uzun` | **zayıf** (grubun en iyisi) | Sharpe 1,25; bootstrap p 0,025; 3× maliyette %+18,0; piyasa emriyle %+21,7; eğitimin her yılı pozitif; Sharpe oranı 0,75 | Yalnız 16 olay günü; en iyi gün (06.02.2026) +%9; en iyi 5 gün çıkınca %−1,4; DSR aile 0,0000, hoşgörülü 0,47 (N=100); 10 bps geçişte %+12,3; çöküşte alım riski (10.10.2025 bar içi yaklaşık −%11); K8 ile 0,91 aynı bahis |
| K7 `baz_5m_kendi` | **zayıf** | 113 işlem, 78 olay günü; Sharpe 1,13; p 0,040; Sharpe oranı 0,87 | Dolum varsayımına çok duyarlı: 10 bps geçişte %+7,8, 25 bps'te %+0,4; piyasa emri 2× maliyette %+10,8; en iyi 10 gün çıkınca %−5,7; DSR ≈ 0 |
| K8 `sv_5m_hepsi_uzun` | **zayıf** | Sharpe 1,20; p 0,031; maliyete dayanıklı | Yalnız 9 olay günü; 27 işlem (takip eşiği 30'un altında); K6'nın kopyası (0,91) |
| K1 `trend_yarim` | **zayıf** | 55 işlem, sürekli maruziyet; sabit beta korumalı %+12,8; 3× maliyette %+9,4 | Alfa t 0,93; en iyi 10 gün çıkınca %−17,2; doğrusal alfa trend zamanlama dışbükeyliğinden (TM t 4,1); 2022'de zarar, 2023'te alfa ≈ 0; araştırmacının dönem bilgisiyle bulaşma riski (aile raporu bölüm 2); K2 ile 0,96 |
| K2 `trendvol_tam` | **zayıf** | 98 işlem; sabit beta korumalı %+17,8; 3× maliyette %+13,2 | K1 ile aynı bahis; alfa t 1,08; en iyi 10 gün çıkınca %−18,6; 26Ç3 tek başına +%23,1 (dönem toplamından fazla) |
| K9 `donus_1h_limit` | **zayıf** | Beta ≈ 0; 7 çeyreğin 5'i pozitif; 25 bps geçişte %+3,7 | Sinyal kendi başına kenarsız (piyasa emriyle %−1,74); limit dolum oranı %41–59; alfa t 1,06; en iyi 5 gün çıkınca %−3,6; tur 1 kuralının limitli biçimi |
| K4 `cift B` | **güvenilir değil** | Beta ≈ 0; maliyete dayanıklı | 14 olay günü, 28 işlem; kazançların %99'u en iyi 10 günde; en iyi gün çıkınca %+2,5, 5 gün çıkınca %−2,4; DSR 0,001; 25 bps geçişte %+3,1 |
| K3 `cift C` | **güvenilir değil** | Beta ≈ 0 | %+4,3 toplam; en iyi gün çıkınca %+0,8; kazançların %97'si en iyi 10 günde; K4 ile aynı bahis |
| K5 `konumlanma D2` | **güvenilir değil** | Eğitimde her yıl pozitif | 2025 %−13,5, kâr tek yarıyıldan; 3× maliyette %−9,7; Sharpe 0,503 (eşik 0,5); alfa t 0,67; kayan beta korumalı %+6,5; ailenin 4 kardeşi iç doğrulamada çöktü |
| K10 `meta 1h kanal iz3` | **güvenilir değil** | Meta filtrenin AUC'si korundu (aile raporu) | 2025 %+36, 2026 %−7,8; 3× maliyette %−6,3; 2× maliyette en iyi işlem çıkınca negatif; alfa t 0,78; kardeşi `iz4-H240` %−7,1 |

Hüküm dağılımı: **güvenilir 0, zayıf 6, güvenilir değil 4.** Bağımsız bahis
olarak sayıldığında: lead–lag baz kümesi, bindirme kümesi ve K9 zayıf; çift
kümesi ve konumlanma/meta kümesi güvenilir değil.

Bu tablo, `FINALISTLER.md` kuralını değiştirmez. Kural mekaniktir ve denetim
yalnız "kritik ihlal ya da ileri bakış" durumunda çıkarma öngörür. Bu bölümde
ikisinden de iz bulunmadı. Bulgular, ileriye dönük takipte beklentiyi ayarlamak
içindir:

- adaylar düşük betalı ama dışbükey ya da olay bağımlı;
- ileriye dönük takipte 90 gün içinde birkaç olay günü bile çıkmayabilir.

## 9. Tur 1–2'de denenmemiş, tur 3'te sınanabilecek yaklaşımlar

`DENETIM_1` bölüm 6'nın 12 önerisinden 11'i tur 2'de denendi:

| Öneri | Tur 2'deki aile |
|---|---|
| Çift ve yayılım ortalamaya dönüşü | `t2_cift` |
| Oynaklık yönetimi, trend + carry, portföy | `t2_bindirme` |
| Baz ve prim endeksi | `t2_lead_lag` (`baz`, `prim`) ve `t2_konumlanma` (`prim`) |
| Açık pozisyon ve konumlanma | `t2_konumlanma` |
| Emir akışı | `t2_emir_akisi` |
| Lead–lag | `t2_lead_lag` |
| Limit emir | `t2_limit_gun_ici` |
| Geniş evren | `t2_genis_evren` (sürüyor) |
| Meta-etiketleme | `t2_meta` |

Kalanlar ve yeni öneriler:

1. **Makro olay takvimi (DENETIM_1 önerisi 10, hâlâ denenmedi):** FOMC, ABD
   TÜFE ve tarım dışı istihdam saatleri önceden bilinir. Açıklama öncesi
   ve sonrası getiri ve oynaklık kayması ile açıklama sonrası 15m kırılım
   sınanabilir. Tarihler sonuçlardan önce sabit bir listeye yazılmalı.
2. **Tasfiye (likidasyon) verisi ile çöküş anı alımı:** Lead–lag kümesinin
   kenarı, çöküş anlarında spot–vadeli ayrışmasından geliyor gibi görünüyor.
   Doğrudan tasfiye hacmi, bu olayları daha erken ya da daha seçici
   yakalayabilir. Binance zorunlu tasfiye akışı geçmişte sınırlıdır; veri
   kaynağının önce doğrulanması gerekir.
3. **Opsiyon piyasası verisi:** Deribit DVOL, 25-delta çarpıklık, vade yapısı.
   Rejim ya da filtre olarak kullanılabilir. Örneğin:
   - bindirme kümesinin trend zamanlamasını oynaklık primiyle koşullamak;
   - çöküşte alım olaylarını ima edilen oynaklık sıçramasına göre seçmek.
4. **Borsalar arası fonlama ve baz farkı:** Binance–Bybit–OKX sürekli vadeli
   fonlama ve fiyat farkı. Tek borsalı carry'den farklı, piyasa nötr bir göreli
   değer işlemi.
5. **Çeyreklik vadeli takvim yayılımı:** Vadeli baz carry'si. DENETIM_1'de
   "veri setinde yok" diye not edildi; hâlâ denenmedi.
6. **Zincir üstü ve stablecoin akışları:** Borsalara net stablecoin girişi ve
   USDT/USDC arz değişimi. Günlük frekansta piyasa yönü ya da oynaklık
   filtresi.
7. **Emir defteri derinliği:** Binance `bookDepth` ve `bookTicker` arşivleri.
   İki kullanımı var:
   - limit dolum gerçekçiliğini doğrulamak (bu denetimde en büyük belirsizlik);
   - derinlik dengesizliğini sinyal olarak sınamak.
8. **İşlem düzeyi veriyle yürütme denetimi (yöntem):** `aggTrades` ile limit
   dolumlarının ve çöküş anı kaymasının yeniden hesaplanması. K6–K9'un
   sonuçları buna bağlı. Yeni aday aramadan önce mevcut adaylar için
   yapılabilir.
9. **Faktör kıyası (yöntem):** Alfayı yalnız piyasa betasına göre değil şu
   faktörlere göre de ölçmek:
   - genel bir zaman serisi trend faktörüne (bindirme için);
   - uzun oynaklık ya da straddle getirisine (dışbükey adaylar için).

   Bu bölümdeki TM γ sonuçları, piyasa betasına göre alfanın bu adaylar için
   eksik bir ölçü olduğunu gösteriyor.
10. **Çok bölmeli doğrulama (yöntem):** Tek eğitim/iç doğrulama bölmesi yerine
    birleşik arındırılmış çapraz doğrulama (CPCV). Arama sırasında her denemenin
    günlük getirisi saklanırsa gerçek PBO hesaplanabilir. Olay stratejileri
    için anlamlılık, olay sayısına göre bootstrap ile ölçülmeli.
11. **Bağımsız zayıf kümelerden önceden kayıtlı portföy:** Tur 2'nin bağımsız
    kümelerinden (lead–lag baz, bindirme, K9) eşit risk paylı tek bir
    yapılandırma kurulabilir. Aralarındaki korelasyon −0,05…0,11.
    - Kural, iç doğrulama sonuçlarına bakılmadan yazılmalı.
    - Ancak bu kümeler zaten iç doğrulamaya göre seçilmiş adaylardan geliyor.
      Bu yüzden ancak ileriye dönük takipte değerlendirilebilir.

## 10. Yöntem ve dosyalar

- **Çalışma ortamı:** Python sanal ortamı `requirements.txt` ile kuruldu.
  `GRAFIK_ANALIZ_PROTOKOL=2` ve `GRAFIK_ANALIZ_ARASTIRMA=~/arastirma_veri`
  kullanıldı. Veri `arastirma/veri_indir.py` ile indirildi (`--evren` yok;
  çıktı "BITTI").
- **Yeniden hesap:** Her ailenin modülü ayrı ayrı içe aktarıldı
  (`importlib.import_module(...).specs()`); `all_specs()` kullanılmadı.
- **Yardımcı betikler:** Deponun dışında, oturumun geçici klasöründe tutuldu
  ve depoya eklenmedi:
  - yeniden hesap: `evaluate` ile aynı adımlar, deftere yazmaz;
  - limit döngüsü kopyası ve pozisyon eşitlik kontrolü;
  - duyarlılık çalıştırmaları (parametre ya da sabit yalnız bellekte değişti);
  - analiz.
- **Tanımlar:**
  - Bütün getiriler net: komisyon, kayma ve fonlama dahil.
  - "Toplam" bileşik getiridir.
  - Bacak katkıları toplamsaldır.
  - dev_valid 638 günlük gözlem içerir.
- **Dokunulmayanlar:** Depodaki hiçbir dosya değiştirilmedi; yalnız bu rapor
  eklendi.
