# İleriye Dönük Sanal Takip

Son güncelleme: 2026-10-10 15:16 UTC. Kurallar: `grafik_analiz/forward/tracker.py`.
Sinyaller her 4 saatlik mum kapanınca **önce** kaydedilir; sonuç sonraki mumlarla hesaplanır.
Maliyetler araştırma protokolüyle aynıdır (spot %0,12, vadeli %0,07 taraf başına; fonlama dahil).

| Strateji | Takip başlangıcı | Kayıt (zamanında) | Net (1×) | Net (2×) | En büyük düşüş | İşlem | Son hedef |
|---|---|---:|---:|---:|---:|---:|---|
| `kirilim_kanal4h_vadeli_uzun` | 2026-10-08 16:00 | 11 (10) | %+0,00 | %+0,00 | %+0,00 | 0 | vadeli BTC +0,00, vadeli ETH +0,00, vadeli SOL +0,00 |
| `fonlama_carry_sepet3_hizli` | 2026-10-08 16:00 | 11 (10) | %+0,00 | %+0,00 | %+0,00 | 0 | spot BTC +0,00, vadeli BTC +0,00, spot ETH +0,00, vadeli ETH +0,00, spot SOL +0,00, vadeli SOL +0,00 |
| `fonlama_carry_sepet3_yavas_dusuk` | 2026-10-08 16:00 | 11 (10) | %-0,10 | %-0,20 | %-0,01 | 6 | spot BTC +1,00, vadeli BTC -1,00, spot ETH +1,00, vadeli ETH -1,00, spot SOL +1,00, vadeli SOL -1,00 |
| `fonlama_carry_btc_surekli` | 2026-10-08 16:00 | 11 (10) | %-0,09 | %-0,18 | %-0,01 | 2 | spot BTC +1,00, vadeli BTC -1,00 |

## Notlar

- `kirilim_kanal4h_vadeli_uzun`: Protokol 1 finalisti; görülmemiş dönemde Seviye 1'i geçemedi. Bilgi amaçlı takip.
- `fonlama_carry_sepet3_hizli`: Fonlama/carry; aday şartlarından işlem sayısını geçemedi. Bilgi amaçlı takip.
- `fonlama_carry_sepet3_yavas_dusuk`: Fonlama/carry; aday şartlarından işlem sayısını geçemedi. Bilgi amaçlı takip.
- `fonlama_carry_btc_surekli`: Fonlama/carry; aday şartlarından işlem sayısını geçemedi. Bilgi amaçlı takip.

Protokole göre bir değerlendirme en az 90 gün ve 30 işlem sonra yapılır; daha kısa sürelerdeki sonuçlar
yalnız durum bilgisidir.
