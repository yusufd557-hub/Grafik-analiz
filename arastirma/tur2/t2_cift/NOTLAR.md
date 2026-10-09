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

### Tarama 1 (162 yapılandırma, 09.10 07:00)

Temel düzey z-skoru (z_win 1h: 48/168/500, 4h: 30/90/180; z_in 1,5/2/2,5; çıkış z=0;
hedge bir/oyn/ols; üç çift tek tek; piyasa emri). **Hiçbir yapılandırma eğitimde
pozitif değil** (en iyi Sharpe −0,07). Maliyet öncesi brüt getiri de bütün
yapılandırmalarda negatif. Fonlama genelde lehte (SOL çiftlerinde 4 yılda +%10–30),
ama brüt zararı kapatmıyor.

Betimleyici tanılama (`tanilama.txt`, yalnız eğitim verisi): yayılımların varyans
oranı 1 günden uzun ufuklarda 1'in üstünde (1h VR(500) 1,19–1,27; 4h VR(180) 1,34–1,48):
yayılımlar bu ufuklarda trend yapıyor, ortalamaya dönmüyor. Çok kısa ufukta
(1–6 saat) hafif dönüş var (1h birinci gecikme otokorelasyonu −0,01…−0,025, VR(6) 0,94–0,96).

`tanilama2.txt` (yalnız eğitim verisi, betimleyici): büyük kısa vadeli yayılım
şokundan (son k bar hareketi > 3–4σ) sonra 1–6 saatlik ortalama dönüş SOL
çiftlerinde 10–80 bp, ETH/BTC'de 0–10 bp; 24 saatte işaret tersine dönüyor (devam).
Çift gidiş-dönüş maliyeti piyasa emriyle yaklaşık 28 bp (bacak başına notional 1).

### Tarama 2 planı

Yayılım şoku sönümlenmesi (`z_tur="sok"`): son k barlık yayılım hareketi /
(hareketten önceki 500 barlık oynaklık × √k) > z_in ise ters yönde gir, `max_bar` bar
sonra çık (z çıkışı yok, durdurma yok). Çıkıştan sonra |z| < z_in olmadan yeni giriş yok.
1h: k 1/3/6, z_in 3/4, tutma 3/6/12, hedge bir/oyn(500); 4h: k 1/2, z_in 3/4, tutma 1/3.
