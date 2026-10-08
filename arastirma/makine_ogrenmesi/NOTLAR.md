# Makine öğrenmesi ailesi — çalışma notları

Bu dosya arama boyunca, sonuçlar görüldükçe ve **dev_valid görülmeden** yazılır.
Her ek, yazıldığı aşamayı belirtir.

## EK 0 — Plan (hiçbir değerlendirme yapılmadan önce, 8 Ekim 2026)

Amaç: BTC/ETH/SOL için maliyet sonrası kârlı bir ML sinyali olup olmadığını
yalnız dev_train ile aramak.

Model ve eğitim (hepsi `signal_fn` içinde, ileriye yürüyen):

- Modeller: L2 düzenlileştirilmiş lojistik regresyon (`logit`), HistGradientBoosting
  sınıflandırıcı (`hgb_clf`), HistGradientBoosting regresör (`hgb_reg`).
- Hedef: `H` bar sonraki getiri, stratejinin gerçekten yakalayacağı biçimde:
  `open[t+1+H] / open[t+1] - 1`. Sınıflandırıcılarda işaret, regresörde
  oynaklığa bölünmüş (σ_t·√H) ve ±4'te kırpılmış büyüklük. H ≥ 4 bar.
- Yeniden eğitim: takvim ayı başlarında (her `yeniden` ayda bir). Eğitim satırı
  yalnız etiketinin bittiği bar (`t+1+H`) eğitim tarihinden **önce** başlamışsa
  kullanılır (arındırma). İlk tahmin, havuzdaki verinin başından en az
  `min_gun` gün sonra ve en az `min_satir` eğitim satırı varsa.
- Eğitim penceresi: genişleyen ya da son `pencere_gun` gün.
- Havuz: aynı spec'teki coinlerin satırları birlikte eğitilir (özellikler
  ölçekten bağımsız seçilir).
- Belirlenimcilik: HGB'de `early_stopping=False`, `random_state=0`.

Özellikler (nedensel; geriye dönük pencere, `shift(+k)`, baştan EWM):
çok ufuklu oynaklığa bölünmüş getiriler, oynaklık düzeyi/oranı, EMA uzaklıkları
(ATR cinsinden), RSI, stokastik, Bollinger konumu/genişliği, ADX ve DI farkı,
MACD histogramı, CCI, MFI, Donchian konumu, tepeden düşüş, hacim oranları,
alıcı (taker-buy) payı, işlem sayısı oranı, mum gövde/fitil oranları. Seçmeli:
`detect_candles` bayraklarından net mum puanı, vadelide fonlama (yalnız
kayıt zamanı ≤ bar kapanışı), BTC'nin getirileri (çapraz özellik).

Pozisyon: kenar tahmini `edge` (regresörde ŷ·σ·√H, sınıflandırıcıda
(2p−1)·√(2/π)·σ·√H). `edge > k × gidiş-dönüş maliyeti` ise alım,
`edge < −k × maliyet` ise (vadeli iki yönde) açığa satış, yoksa nakit.
Eşleme: `esik` (her bar yeniden karar) ya da `ortusen` (son H kararın
ortalaması, H alt portföy). Vadelide coinin ilk fonlama kaydından önce
pozisyon 0. Evren: varsayılan BTC/ETH/SOL eşit ağırlık (PORT3).

Arama aşamaları (yalnız `windows=("dev_train",)`, maliyet 1× ve 2×):

1. Geniş harita: aralık {1h, 4h, 1d} × piyasa {spot uzun, vadeli iki yön} ×
   model {logit, hgb_clf, hgb_reg} × H (3 değer), varsayılan ayarlar
   (genişleyen pencere, k=1, `ortusen`).
2. Umut veren bölgede: k, eşleme, pencere, özellik seti, HGB düzenlileştirme,
   vadeli yalnız alım.
3. Sağlamlık: seçilen noktanın komşuları, yıllara göre döküm (dev_train içinde).

Seçim kuralı (önceden): dev_train'de 1× ve 2× maliyette net pozitif; 2×
Sharpe'a göre sıralama; komşu parametrelerde de pozitif kalma; dev_train
yıllarının çoğunda pozitif; tek yılın getiriyi taşımaması. Yalnız alım
yapılandırmalarında al-tutla karşılaştırma (dev_train) ve sabit 0,5 pozisyon
kıyası dikkate alınır. En fazla 5 yapılandırma dondurulur, her biri dev_valid'de
bir kez değerlendirilir. Hiçbiri seçim kuralını sağlamazsa bu da raporlanır.

## EK 1 — Aşama 1 gözlemleri (yalnız dev_train; 54 yapılandırma)

- Uygulama notu: `assert_causal` fonlamayı kesim barının **açılış** zamanında
  keser. 1d barda gün içi (08:00, 16:00) fonlama kayıtları kapanışta bilinse de
  kesimde düştüğü için denetim yanlış alarm verdi. Fonlama özellikleri bu yüzden
  ihtiyatlı biçimde "kayıt zamanı ≤ bar açılışı" ile hizalandı (1h/4h'de fark
  yok). Bu değişiklik ilk değerlendirmeden önce yapıldı.
- Al-tut (dev_train, PORT3): spot 4h Sharpe 1,15 (+35,1); tahminlerin başladığı
  2018-09'dan itibaren spot Sharpe 1,17 (+21,8); vadeli 2021–2023 Sharpe 1,23.
- Vadeli iki yön: 27 yapılandırmanın hiçbiri güçlü değil; 1× Sharpe en çok 0,82
  (1h hgb_clf H12), 2× Sharpe en çok 0,55 (1d hgb_reg H16, yalnız 30 işlem).
  Açığa satış tarafı ML ile de değer katmıyor gibi.
- Spot yalnız alım: 4h hgb_reg H12 1× 1,24 / 2× 1,11; 4h logit H12 1,11 / 1,00.
  Bunlar al-tut Sharpe'ı düzeyinde; kâr büyük ölçüde betadan.
- 1h spot H4: 1× Sharpe 1,20–1,34, zamanın yalnız %31–38'inde pozisyonda, en
  büyük düşüş −%31/−%35; ama toplam maliyet sermayenin 1,7–2,0 katı ve 2×
  maliyette Sharpe ≈ 0,1. Brüt zamanlama sinyali var gibi, maliyet engel.
- 1d: veri az; hiçbir varyant al-tutu geçmedi.
- Sonraki adım (2a): işlem eşiği k ∈ {2, 3} ile devir hızını düşürmek; vadelide
  yalnız alım.
