# Trend ailesi — arama planı (sonuçlardan ÖNCE yazıldı)

Yazılış: 2026-10-08, hiçbir yapılandırma değerlendirilmeden önce.

## Fikirler
- tsmom: N günlük getirinin işareti (zaman serisi momentumu).
- sma: kapanış > N günlük basit ortalama (fiyat-ortalama filtresi).
- emax: EMA(N/4) > EMA(N) kesişimi.
- donch: Donchian/turtle kırılımı; giriş N gün, çıkış N/2 gün kanalı (isteğe bağlı ATR iz süren stop).
- Topluluk (ENS): birden çok bakış süresinin (10, 20, 40, 80, 160 gün) sinyal ortalaması.
- Oynaklık hedefleme: boyut = min(1, hedef_oynaklık / gerçekleşen_oynaklık), yeniden dengeleme bandı ile.
- Spot: yalnız alım (piyasada / nakit). Vadeli: alım-satım (−1…1) ve yalnız alım.
- Evren: tek coin (BTC, ETH, SOL) ve eşit ağırlıklı 3 coin portföyü (PORT3).
- Zaman dilimi: 1d ve 4h (bakış süreleri gün cinsinden, 4h'te ×6 bar).

## Aşamalar (yaklaşık deneme bütçesi ≤ ~300 dev_train denemesi)
1. 1d, 4 fikir × 6 bakış (10,20,40,80,160,ENS) × {spot PORT3, vadeli PORT3 alım-satım}.
2. Aynısı 4h.
3. Tek coinlerde ENS varyantları (1d).
4. Oynaklık hedefleme / band, vadeli yalnız alım, fikirler arası topluluk.

## Seçim kuralı (yalnız dev_train ile)
1. dev_train 1× ve 2× maliyette net getiri > 0.
2. dev_train'de yıllık işlem sayısı (portföy toplamı) ≥ 20 → 18 aylık doğrulamada beklenen ≥ 30 işlem.
3. Birincil ölçü: dev_train yıllık Sharpe (1×). Tek bir keskin tepe yerine komşu bakış
   sürelerinin de iyi olduğu düzlükler ve topluluk sinyalleri tercih edilir.
4. Yalnız alım stratejileri al-tut ile aynı pencerede karşılaştırılır: Sharpe daha yüksek ve
   en büyük düşüş belirgin biçimde daha küçük olmalı.
5. En fazla 5 yapılandırma dondurulur; mümkünse farklı yapılar (spot portföy, vadeli portföy, 1d/4h).
6. Dondurulanlar dev_valid'de bir kez değerlendirilir; sonrasında ayar yapılmaz.

Al-tut kıyası `evaluate(record=False)` ile hesaplanır (deneme sayılmaz, strateji değildir).

## Dondurma kararı (dev_valid'e bakmadan önce yazıldı)

Arama bitti: 185 dev_train denemesi (aşamalar s1–s5, `arama.py`). Sonuç tablosu `sonuclar_train.csv`.

dev_train gözlemleri:
- Spot yalnız alım PORT3: bütün fikirlerde ve bakış sürelerinde Sharpe ≈ 1,2–1,8 (al-tut 1,12),
  en büyük düşüş ≈ −%40…−%65 (al-tut −%85). En iyi bölge 20–80 gün; 10 ve 160 gün daha zayıf.
- Vadeli alım-satım PORT3: Sharpe 0,35–1,20, vadeli al-tutun (1,20–1,28) altında. Açığa satış ayağı
  eğitim döneminde değer katmadı.
- Vadeli yalnız alım: Sharpe 1,4–1,8 (vadeli al-tut 1,20–1,28), fonlama yılda ≈ %10 maliyet.
- Oynaklık hedefleme Sharpe'ı pek değiştirmedi, düşüşü azalttı.
- 4h'te ATR stop'u 4h ATR'si ile ölçüldüğü için çok dar kaldı, kötüleşti.

Dondurulan 5 yapılandırma (hepsi 4 fikir × (20, 40, 80) gün = 12 bileşenli topluluk):
1. trend_ens_spot_port3_1d — spot, PORT3, 1d, yalnız alım.
2. trend_ens_spot_port3_4h — spot, PORT3, 4h, yalnız alım, band 0,15.
3. trend_ens_spot_port3_4h_vt — spot, PORT3, 4h, yalnız alım, hedef oynaklık 0,6 (30 gün), band 0,1.
4. trend_ens_vadeli_port3_4h_alim — vadeli, PORT3, 4h, yalnız alım.
5. trend_ens_vadeli_port3_4h_ls_vt — vadeli, PORT3, 4h, alım-satım, hedef oynaklık 0,6, band 0,1.
   (Eğitimde vadeli al-tutun Sharpe'ının altında; tek iki yönlü yapı olduğu için bilgi amaçlı alındı.)

Gerekçe: tek bakış süreli keskin tepeler (ör. sma 40 gün) yerine düzlüğün ortasındaki topluluk;
işlem sıklığı ≥ 20/yıl; 2× maliyette eğitim getirisi pozitif; farklı yapılar.
