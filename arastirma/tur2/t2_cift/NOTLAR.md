# t2_cift — çalışma notları

Aile: çift / yayılım ortalamaya dönüşü, piyasa nötr, vadeli (protokol sürüm 2).
Bu dosya iç doğrulama (dev_valid) değerlendirmesinden **önce** yazılır ve
dondurma kararı da burada, dev_valid'e bakmadan kaydedilir.

## Başlangıç durumu (9 Ekim 2026)

- Bu aile için önceki bir çalışma yok: `arastirma/tur2/t2_cift/` boştu,
  `arastirma/tur2/deneyler/t2_cift.jsonl` yoktu.
- Veri kontrolü (yükleyicilerle): vadeli 1h ve 4h BTC/ETH 2020-01-01'den,
  SOL 2020-09-14'ten; fonlama BTC/ETH 2020-01-01, SOL 2020-09-13'ten.
  SOL vadelide 2 boşluk var (2 ve 3 günlük).
- `load_universe()` şu an çalışmıyor: `evren.parquet` henüz yok (indirme
  sürüyor). `available_symbols("futures", "4h")` yalnız BTC/ETH/SOL
  döndürüyor. Geniş evren çiftleri ancak veri tamamlanırsa denenebilir.

## Plan

1. Sinyal: üç çift (ETH/BTC, SOL/BTC, SOL/ETH) için log fiyat yayılımı.
   Hedge oranı seçenekleri (hepsi geriye dönük):
   - `bir`: 1:1 dolar nötr, yayılım = log A − log B.
   - `oyn`: oynaklık oranı σA/σB (kayan pencere, getirilerden).
   - `beta`: B'ye göre kayan OLS getiri betası.
   - `ols`: kayan pencerede log fiyat düzeyi OLS'u (A = c + h·B), z = artık / artık std.
   `oyn` ve `beta` için yayılım, bir önceki barın oranıyla hedge'lenmiş
   getirilerin kümülatif toplamıdır (işlem gören portföyün değeri).
2. z-skoru: kayan ortalama ve std (pencere L). Giriş |z| > z_in, çıkış z
   işaret değiştirince (z_out), durdurma |z| > z_stop ya da en fazla
   bekleme süresi. Durdurmadan sonra |z| < z_in olana kadar yeni giriş yok.
   Hedge oranı girişte dondurulur (işlem boyunca pozisyon sabit, gereksiz
   dengeleme maliyeti yok).
3. Rejim filtresi (yapı kırılması): uzun pencereli z (yayılımın uzun vadeli
   trendi) aşırıysa ya da kayan AR(1) yarı ömrü uzunsa giriş yok.
4. Çoklu çift portföyü: üç çift, coin başına net pozisyon (her çiftin bacak
   başı notional'ı sermayenin 1/6'sı; coin pozisyonu en fazla 1).
5. Limit emir: giriş (ve isteğe bağlı çıkış) emirleri kapanış ± ofset ile
   k bar boyunca limit, sonra piyasa emri.
6. 1h ve 4h.
7. Arama yalnız `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))`.
   Eğitim içi alt dönem dökümleri (yıllık, çift bazında, fonlama payı) yalnız
   veriyi 31.12.2024'te kesen bir yardımcı ile hesaplanır; bu yardımcı
   yalnız önceden deftere yazılmış yapılandırmalar için kullanılır.
8. Seçim ölçütü (eğitim): 1× Sharpe, 2× maliyette pozitif getiri, alfa > 0,
   yeterli işlem sayısı (eğitimde ≥ 60), yıllar arasında tutarlılık
   (tek bir yıla dayanmamak), komşu parametrelerde sağlamlık.
9. En fazla 5 yapılandırma dondurulur, `assert_causal` uygulanır, dev_valid'de
   bir kez ölçülür.

## Arama günlüğü

(aşağıda, her taramadan sonra eklenir)
