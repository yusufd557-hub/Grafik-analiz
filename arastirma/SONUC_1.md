# Görülmemiş Dönem Sonucu — Protokol Sürüm 1

Test zamanı: 8 Ekim 2026, 20:49 UTC (tek seferlik; kayıt `holdout_kayit.jsonl`).
Dönem: 01.07.2025 – 30.09.2026 (457 gün). Finalistler ve seçim kuralı:
[`FINALISTLER.md`](FINALISTLER.md). Ham sonuçlar: `holdout_sonuc.json`.

## Sonuç

**Hiçbir finalist Seviye 1 (kârlı) şartlarını geçemedi.** Protokole göre bu
araştırma turundan "kârlı" sayılan bir sistem çıkmadı. İleriye dönük takip
yalnız Seviye 1'i geçen stratejiler için öngörüldüğünden bu tur için
başlatılmadı.

| Finalist | Net (1×) | Net (2×) | Sharpe | En büyük düşüş | İşlem | Kazanan işlem | En iyi işlem çıkınca | p | Al-tut (aynı piyasa) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kirilim_kanal4h_vadeli_uzun` | %+9,8 | %+7,8 | 0,49 | %−26,8 | 40 | %30 | %−2,4 | 0,33 | %−13,7 (düşüş %−64,9) |
| `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot` | %+0,9 | %−0,4 | 0,18 | %−6,7 | 57 | %54 | %−1,3 | 0,38 | %−13,6 (düşüş %−65,5) |
| `formasyon_ucgen_kama_4h_hacim_iki` | %−12,5 | %−14,7 | −0,60 | %−14,8 | 55 | %36 | %−16,9 | 0,77 | %−13,7 (düşüş %−64,9) |

## Şart bazında

| Şart | Kırılım | Makine öğrenmesi | Formasyon |
|---|---|---|---|
| Net getiri > 0 | geçti | geçti | geçmedi |
| İki kat maliyetle net > 0 | geçti | geçmedi | geçmedi |
| En az 20 işlem | geçti (40) | geçti (57) | geçti (55) |
| En iyi tek işlem çıkınca > 0 | geçmedi | geçmedi | geçmedi |
| Seviye 2: p < 0,0167 | geçmedi (0,33) | geçmedi (0,38) | geçmedi (0,77) |

## Gözlemler

- Görülmemiş dönemde piyasa düştü. Eşit ağırlıklı BTC/ETH/SOL vadeli al-tut
  %−13,7 getirdi ve en büyük düşüşü %−65 oldu.
- Kırılım stratejisi aynı dönemde %+9,8 kazandı; en büyük düşüşü %−26,8.
  Ancak kazancın tamamından fazlası en iyi tek işlemden (%+12,6) geldi. O
  işlem çıkarılınca sonuç %−2,4. İşlemlerin %30'u kazandı. Bootstrap
  p = 0,33: sonuç şansla açıklanabilir.
- Makine öğrenmesi stratejisi zamanın %2,5'inde pozisyondaydı. Net %+0,9
  kazandı, iki kat maliyette zarara döndü.
- Formasyon stratejisi %−12,5 kaybetti.
- İç doğrulamada en güçlü görünen yapılandırmaların görülmemiş dönemde bu
  sonuçları vermesi, denetimin uyarısıyla tutarlı. Uyarıya göre iç
  doğrulamadaki kâr büyük ölçüde yükselen piyasanın betasından geliyordu ve
  çoklu deneme düzeltmesinden sonra hiçbir aday anlamlı değildi.

## Bu turdan kalanlar

- Görülmemiş dönem (01.07.2025 – 30.09.2026) bu tur için kullanıldı. Bundan
  sonraki stratejiler için bağımsız bir test dönemi değildir; yeni
  stratejiler yalnız ileriye dönük takiple değerlendirilebilir.
- 8 ailede toplam yaklaşık 1.930 yapılandırma denendi. Deney defterleri
  `deneyler/`, aile raporları `<aile>/RAPOR.md`, denetim `DENETIM_1.md`
  dosyalarındadır.
- Denetimin listelediği denenmemiş yaklaşımlar `DENETIM_1.md` içindedir.
