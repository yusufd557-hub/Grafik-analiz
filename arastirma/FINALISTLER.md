# Finalistler

Protokol: [`docs/PROTOKOL.md`](../docs/PROTOKOL.md) (sürüm 1). Bu belge görülmemiş
dönem açılmadan **önce** yazıldı ve commit edildi.

## Seçim kuralı (sonuçlara bakmadan önce sabitlendi)

Bağımsız denetim ([`DENETIM_1.md`](DENETIM_1.md)), görülmemiş dönemin dil modeli
araştırmacıların eğitim bilgisiyle örtüşebileceğini belirtti ve finalistlerin
mekanik bir kuralla seçilmesini önerdi. Kural:

1. **Uygunluk:**
   - Aday şartlarını geçmiş olmak (`candidate_check`).
   - İleri bakış denetimini geçmiş olmak (`assert_causal`).
   - Denetimde yeniden üretilmiş olmak.
   - İç doğrulamada (01.01.2024–30.06.2025) **en az 30 işlem** yapmış olmak.
     Gerekçe: görülmemiş dönem 15 aydır ve en az 20 işlem şartı vardır. 18
     aylık iç doğrulamada 30'dan az işlem yapan bir yapılandırma bu şartı
     muhtemelen karşılayamaz. Denetim, 27 işlemli ve %0,9 maruziyetli bir
     yapılandırmayı bu nedenle kırılgan buldu.
2. **Puan:** iç doğrulamada **iki kat maliyetle** yıllık Sharpe oranı
   (günlük net getirilerden).
3. **Çeşitlilik:** Adaylar puana göre büyükten küçüğe sıralanır. Bir aday
   yalnızca iç doğrulamadaki günlük net getirisinin, daha önce seçilmiş
   bütün finalistlerle korelasyonu 0,70'ten küçükse seçilir. Böylece
   birbirinin kopyası olan yapılandırmalar ayrı finalist sayılmaz.
4. En fazla **3** finalist seçilir.
5. Görülmemiş dönemde her finalist protokoldeki Seviye 1 ve Seviye 2
   şartlarıyla, parametreleri değiştirilmeden, **bir kez** ölçülür. Seviye 2
   için anlamlılık eşiği 0,05 / finalist sayısıdır.
6. Eşit ağırlıklı BTC/ETH/SOL al-tut (aynı piyasa) karşılaştırma için
   raporlanır; şart değildir.

## Uygulama

Kural `arastirma/finalist_secimi.py` ile yalnız geliştirme dönemi verisiyle
uygulanır. Sonuç bu belgenin altına eklenir.

## Sonuç (yalnız geliştirme dönemi verisiyle, kural uygulandı)

İç doğrulama dönemi 01.01.2024–30.06.2025. Sıralama: iki kat maliyetle Sharpe.

| # | Yapılandırma | Aile | Net (1×) | Net (2×) | Sharpe (2×) | İşlem | En büyük düşüş | Karar |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | `ml_1h_sp_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel-btc` | makine_ogrenmesi | %+9,1 | %+8,2 | 1,79 | 27 | %-2,2 | elendi: 27 işlem < 30 |
| 2 | `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot` | makine_ogrenmesi | %+13,2 | %+10,3 | 1,21 | 112 | %-3,5 | FİNALİST |
| 3 | `kirilim_kanal4h_vadeli_uzun` | kirilim | %+47,4 | %+44,3 | 1,08 | 45 | %-15,2 | FİNALİST |
| 4 | `formasyon_ucgen_kama_4h_hacim_iki` | formasyon | %+30,7 | %+27,4 | 1,03 | 55 | %-18,6 | FİNALİST |
| 5 | `kirilim_kanal4h_spot` | kirilim | %+47,6 | %+42,1 | 1,03 | 47 | %-14,2 | elendi: 3 finalist dolu |
| 6 | `ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot` | makine_ogrenmesi | %+23,1 | %+15,2 | 0,98 | 320 | %-8,9 | elendi: 3 finalist dolu |
| 7 | `formasyon_hepsi_4h_trend_10bar_uzun` | formasyon | %+24,5 | %+20,1 | 0,95 | 78 | %-9,3 | elendi: 3 finalist dolu |
| 8 | `formasyon_ucgen_kama_4h_trend_uzun` | formasyon | %+24,8 | %+22,5 | 0,92 | 39 | %-12,9 | elendi: 3 finalist dolu |
| 9 | `od_dip_ret4h_fut_port3_1h` | ortalamaya_donus | %+13,9 | %+10,4 | 0,85 | 66 | %-5,6 | elendi: 3 finalist dolu |
| 10 | `trend_ens_spot_port3_4h_vt` | trend | %+42,7 | %+38,7 | 0,85 | 66 | %-29,9 | elendi: 3 finalist dolu |
| 11 | `trend_ens_spot_port3_4h` | trend | %+38,6 | %+34,2 | 0,71 | 66 | %-33,3 | elendi: 3 finalist dolu |
| 12 | `trend_ens_spot_port3_1d` | trend | %+32,5 | %+28,4 | 0,64 | 36 | %-33,8 | elendi: 3 finalist dolu |
| 13 | `trend_ens_vadeli_port3_4h_alim` | trend | %+26,5 | %+22,1 | 0,54 | 62 | %-34,1 | elendi: 3 finalist dolu |
| 14 | `od_dip_ens4_fut_port3_1h` | ortalamaya_donus | %+7,5 | %+4,1 | 0,49 | 140 | %-4,5 | elendi: 3 finalist dolu |
| 15 | `ml_1h_sp_PORT3_hgb_reg_H6_k3.0_ortusen_uzun_temel` | makine_ogrenmesi | %+3,4 | %+2,0 | 0,45 | 55 | %-2,9 | elendi: 3 finalist dolu |

Finalistlerin iç doğrulamadaki günlük getiri korelasyonları:

- `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot` – `kirilim_kanal4h_vadeli_uzun`: 0,17
- `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot` – `formasyon_ucgen_kama_4h_hacim_iki`: 0,08
- `kirilim_kanal4h_vadeli_uzun` – `formasyon_ucgen_kama_4h_hacim_iki`: 0,04

**Finalistler:** `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot`, `kirilim_kanal4h_vadeli_uzun`, `formasyon_ucgen_kama_4h_hacim_iki`.
Seviye 2 anlamlılık eşiği: 0,05 / 3 = 0,0167.
