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

## EK 2 — Aşama 2a gözlemleri (yalnız dev_train; 42 yeni yapılandırma, toplam 96)

- 4h spot: k=2/3 Sharpe'ı az değiştirdi (hgb_reg H12: 1,25/1,29; 2× 1,12/1,16).
  Yıllık dökümde 2018 ve 2022 negatif, kârın çoğu 2021 ve SOL bacağından → betaya
  dayalı, al-tut (aynı dönem Sharpe 1,17) ile benzer. Vadeli 4h yalnız alım 2022'de
  −%53; iki yön 2022'de yaklaşık sıfır, açığa satış kâr getirmiyor.
- **1h spot, yüksek eşik:** hgb_reg H4 k2 1× Sharpe 1,65 / 2× 1,12, en büyük düşüş
  −%16, zamanın %14'ünde pozisyonda; hgb_clf H4 k3 1,41 / 1,10 (%6 pozisyonda);
  hgb_clf H12 k3 1,41 / 1,13. Yıllık döküm (1×): hgb_reg H4 k2 bütün yıllar pozitif
  (2018 +0,10, 2019 +0,07, 2020 +0,50, 2021 +1,39, 2022 +0,10, 2023 +0,14), üç coin
  de pozitif. 2× maliyette 2022 ≈ 0. Bu, aşamaya kadar görülen tek rejimden
  bağımsız örüntü. Logit aynı ayarda daha zayıf (1,23 / 0,72).
- Vadeli 1h yalnız alım hgb_clf H12 k2: 1,27 / 1,00; 2022 −0,06.
- Aşama 2b planı (1h odaklı): H ∈ {6, 8}; özellik seti (+mum, +btc); kayan pencere
  (730/1095 gün); `esik` eşlemesi; HGB düzenlileştirme; vadelide H4 yalnız alım,
  kendi verisiyle ve spot geçmişiyle eğitim (egitim="spot"), fonlama özelliği.

## EK 3 — Aşama 2b gözlemleri (yalnız dev_train; 32 yeni, toplam 128)

- 1h spot kısa ufuk bölgesi sağlam: H ∈ {4, 6, 8}, hgb_reg/hgb_clf, k ∈ {2, 3}
  için 1× Sharpe 1,35–1,66, 2× 0,93–1,17. `+btc` biraz daha iyi (1,70 / 1,15), `+mum`
  nötr. HGB düzenlileştirme değişiklikleri benzer (1,35–1,51). Kayan pencere daha
  kötü (730 gün 1,06 / 0,47; 1095 gün 1,38 / 0,80) → genişleyen pencere kalır.
  Her bar karar (`esik`) maliyetle çöküyor (2× −0,35) → `ortusen` kalır.
- Yıllık (spot hgb_clf H6 k2): 2018–2021 ve 2023 pozitif, 2022 −0,07 (2× −0,17).
  Spot hgb_reg H4 k2 +btc: 2× maliyette 2018, 2019, 2022 hafif negatif.
- **Vadeli, spot geçmişiyle eğitim (egitim="spot")** belirgin biçimde daha iyi:
  hgb_reg H4 k3 yalnız alım 1,63 / 1,37; iki yön 1,63 / 1,25; hgb_clf H4 k2 yalnız
  alım 1,70 / 1,23. Kendi (2020 sonrası) verisiyle eğitim 1,10 / 0,75; fonlama
  özelliği eklemek değiştirmedi (1,13 / 0,84). Yıllık (hgb_reg H4 k3, 1× ve 2×):
  2020–2023 her yıl pozitif; iki yön 2022'de +0,40 (2× +0,29).
- Aşama 3 planı: vadeli egitim=spot çevresi (H 6/8, k 2/4, +btc, logit, üç ayda bir
  yeniden eğitim, iki yön), spot için üç ayda bir yeniden eğitim ve k=2,5.

## EK 4 — Aşama 3 gözlemleri ve kalan plan (yalnız dev_train; 21 yeni, toplam 149)

(Önceki oturum kullanım sınırında kesildiği için bu ek, devam eden oturumda, kayıtlı
`tarama_sonuclari.jsonl` / `tarama4_*.log` / `tani_*.log` çıktılarından yazıldı.
dev_valid hâlâ görülmedi.)

- Vadeli, spot geçmişiyle eğitim (`egitim="spot"`) bölgesi komşularda sağlam: H ∈ {4, 6, 8},
  k ∈ {2, 3, 4}, yalnız alım / iki yön, `+btc`, üç ayda bir yeniden eğitim, hgb_clf →
  1× Sharpe 1,05–1,69, 2× 0,81–1,37 (dev_train Sharpe'ı 2017–2019'daki sıfır getirili
  günleri de içerir; vadeli veri 2020'de başlar). Logit aynı ayarda daha zayıf
  (yalnız alım 1,30 / 1,04; iki yön 1,00 / 0,67). k=4 devir hızını düşürüyor ama
  Sharpe'ı da düşürüyor (1,05–1,18).
- 2020-01-01'den ölçülünce (tani_donem): hgb_reg H4 k3 yalnız alım 2,06 / 1,73,
  iki yön 2,06 / 1,58; hgb_clf H4 k3 iki yön 2,14 / 1,65. Al-tut vadeli 2020–2023
  Sharpe ≈ 1,29 (1h).
- Yıllık (tani_yillik3): hgb_reg H4 k3 iki yön ve hgb_clf H4 k3 iki yön 2020–2023 her
  yıl 1× ve 2× pozitif; 2021 en büyük katkı, 2023 küçük (+0,03…+0,18). Bacak bazında
  üç coin de pozitif, SOL ve ETH baskın, BTC en zayıf.
- Spot: üç ayda bir yeniden eğitim (re3) ve k=2,5 aylık eğitimle benzer
  (1,58 / 1,03; 1,45 / 1,07) → bölge düz, keskin bir tepe yok.
- Kalan plan (Aşama 4, küçük): vadeli egitim=spot için (a) hgb_clf komşuları
  (H4 k2/k4 iki yön, H6 k3 yalnız alım/iki yön), (b) HGB düzenlileştirme duyarlılığı
  (hgb_reg H4, it200/lr0,03/min_yaprak 500; k3 yalnız alım/iki yön), (c) aynı fikrin 4h
  sürümü (hgb_reg H6 k2 yalnız alım/iki yön; daha düşük devir hızı). Sonra seçilecek
  yapılandırmaların yıllık dökümü ve dondurma. Yeni bir özellik/model ailesi açılmayacak.

## EK 5 — Aşama 4 gözlemleri ve dondurma kararı (yalnız dev_train; 8 yeni, toplam 157; dev_valid görülmeden)

Aşama 4 (tarama5.py, egitim="spot", 1h vadeli):

| Yapılandırma | 1× Sharpe | 2× Sharpe | Not |
|---|---|---|---|
| hgb_clf H4 k2 iki yön | 1,90 | 1,21 | maliyet 1,12 (yüksek devir) |
| hgb_clf H4 k4 iki yön | 1,47 | 1,22 | |
| hgb_clf H6 k3 yalnız alım | 1,57 | 1,29 | |
| hgb_clf H6 k3 iki yön | 1,84 | 1,42 | aramadaki en yüksek 2× Sharpe |
| hgb_reg H4 k3 yalnız alım, düzenlileştirilmiş (it200/lr0,03/my500) | 1,49 | 1,24 | temel ayar 1,63 / 1,37 |
| aynı, iki yön | 1,51 | 1,17 | temel ayar 1,63 / 1,25 |
| 4h hgb_reg H6 k2 yalnız alım | 1,04 | 0,94 | 1h'den zayıf, en büyük düşüş −%63 |
| 4h hgb_reg H6 k2 iki yön | 1,00 | 0,83 | |

Düzenlileştirme değişikliği sonucu biraz düşürüyor ama bölge korunuyor; 4h sürümü zayıf.

Kısa liste tanısı (tani_secim.py → tani_secim_*.log; tahminlerin başladığı tarihten 2023 sonuna):

- Vadeli hgb_clf H6 k3 iki yön: 2020–2023 1× Sharpe 2,33 / 2× 1,80; her yıl 1× ve 2× pozitif
  (2022: +0,21 / +0,07). Bacaklar: BTC +3,5, ETH +4,5, SOL +21,1 (1×).
- Vadeli hgb_reg H4 k3 yalnız alım: 2,06 / 1,73; her yıl 1× ve 2× pozitif (2022 +0,26 / +0,19).
- Vadeli hgb_clf H6 k3 yalnız alım ve hgb_reg H8 k3 yalnız alım: 2022 2× maliyette ≈ 0 / hafif negatif.
- Spot hgb_reg H6 k3: 2018-09–2023 1,59 / 1,26; 2018–2023 **her yıl** 1× ve 2× pozitif.
- Spot hgb_reg H4 k3 +btc: 1,60 / 1,27; 2019 hafif negatif (−0,02 / −0,03), diğer yıllar pozitif.
- Spot hgb_reg H4 k2 +btc: 2× maliyette 2018, 2019, 2022 negatif → elendi.
- Spot hgb_clf H12 k3: 2022 negatif (1× −0,03, 2× −0,10) → elendi.
- Ortak zayıflık (raporda açıkça yazılacak): kârın büyük kısmı 2021'den ve SOL bacağından geliyor;
  2022 hepsinde zayıf. 2021 çıkarıldığında da toplam pozitif kalıyor (ör. vadeli hgb_clf H6 k3
  iki yön 1×: 1,83 × 1,21 × 1,24 − 1 ≈ +1,75).

**Dondurma kararı** (önceden yazılan seçim kuralına göre: 1× ve 2× pozitif, 2× Sharpe'a göre
sıralama, komşular pozitif, yılların çoğu pozitif, tek yıl taşımıyor; piyasa/model çeşitliliği):

1. `ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot` — vadeli iki yön, en yüksek 2× Sharpe.
2. `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot` — vadeli yalnız alım, regresör;
   2× Sharpe'ta ikinci, her yıl pozitif.
3. `ml_1h_sp_PORT3_hgb_reg_H6_k3.0_ortusen_uzun_temel` — spot; bütün yıllar pozitif.
4. `ml_1h_sp_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel-btc` — spotta en yüksek 2× Sharpe.

Beşinci yapılandırma dondurulmadı: kalan adaylar (vadeli H6/H8 yalnız alım, hgb_clf H4 iki yön)
seçilenlerle aynı modelin yakın komşuları ve 2022'de daha zayıf; dev_valid'e fazladan bakış
eklememek için 4'te kalındı. Dört yapılandırma birbirine yakındır (aynı fikir: spot geçmişiyle
eğitilen 1h HGB, kısa ufuk, yüksek eşik); dev_valid sonuçları bağımsız kanıt sayılmamalıdır.
Sıradaki adım: `specs()` → `nedensellik.py` (assert_causal) → `dogrulama.py` (tek sefer).

## EK 6 — Dondurma sonrası (dev_valid bir kez görüldü; hiçbir şey değiştirilmedi)

- `nedensellik.py`: dört yapılandırma `assert_causal` (0,55/0,8/0,97 ve ek 0,3 kesimi) geçti
  (nedensellik_*.log). Ardından `dogrulama.py` her birini bir kez `evaluate(spec)` ile
  değerlendirdi (dogrulama_*.log, dondurulmus/*.json). Dördü de `candidate_check` geçti.
- dev_valid'den sonra parametre, kural, özellik veya yapılandırma listesi DEĞİŞTİRİLMEDİ.
  Yalnız `specs()` açıklama metinlerine candidate_check sonucu yazıldı (sinyali etkilemez).
- Gözlemler: dev_valid'de pozisyonda kalma oranı dev_train'in çok altında (ör. vadeli hgb_reg
  H4 %13 → %4,5; spot H4 +btc %6,7 → %0,9). Kenar σ ile ölçeklenip sabit maliyet eşiğiyle
  karşılaştırıldığı için model oynaklığın yüksek olduğu coin ve dönemlerde işlem yapıyor; 1h
  medyan σ dev_valid'de 2020–21'den düşük (tani_oynaklik.log). Kârın büyük kısmı SOL bacağından.
  Vadeli iki yönlü hgb_clf'de 2× maliyette BTC ve ETH bacakları negatif, 2025'in ilk yarısı ≈ 0.

Sayım düzeltmesi: `tarama_sonuclari.jsonl` ve defter aşama sayılarını 1: 54, 2a: 44, 2b: 32,
3: 19, 4: 8 (toplam 157) olarak verir. EK 2 ve EK 3'teki ara toplamlar (96, 128) 2 eksik
yazılmıştı; doğru ara toplamlar 98 ve 130'dur. Defter: 157 × 2 dev_train satırı + dondurulan 4
yapılandırmanın 4'er satırı = 330 satır.
