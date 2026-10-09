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

## Kesinti ve devam (9 Ekim 2026, 08:45 UTC)

- Önceki çalışma kullanıcı tarafından 07:06 UTC civarında, tarama 2 sürerken durduruldu.
  dev_valid'e hiç bakılmadı; defterde (`arastirma/tur2/deneyler/t2_cift.jsonl`) yalnız
  dev_train satırları var: 378 satır = 189 yapılandırma × (1×, 2×).
  - Tarama 1: 162 yapılandırmanın hepsi defterde.
  - Tarama 2: 156 yapılandırmanın ilk 27'si defterde (1h ETH/BTC `bir` 18 + `oyn` 9);
    `tarama2.csv` yalnız ilk 20 satırı içeriyor (her 10 yapılandırmada bir yazılıyordu).
- Çalışma sıfırdan başlatılmadı. Defterdeki 189 yapılandırma deneme sayısına dahildir
  (Deflated Sharpe için), satırlar silinmez/değiştirilmez.
- Devam yöntemi: `ortak.tara` artık defterde aynı ad ve aynı parametrelerle zaten
  bulunan yapılandırmaları yeniden değerlendirmez; ölçülerini defterden alır (yinelenen
  deneme satırı oluşmaz). Tarama 2'nin kalan 129 yapılandırması bu şekilde çalıştırılır.
- Bu devamda `load_universe()` hâlâ kullanılamıyor (geniş evren indirmesi 08:44'te
  yeniden başlamış, sürüyor).

### Tarama 2 sonucu (156 yapılandırma; 27'si kesintiden önce, 129'u devamda)

- ETH/BTC: 1h ve 4h'te bütün yapılandırmalar negatif (brüt dönüş 0–10 bp, maliyet 28 bp).
- SOL çiftleri, 1h, `bir`, z_in 4 (seyrek olay, maruziyet %1–2): birkaç yapılandırma pozitif.
  En iyisi `1h_SOLBTC_bir_sok_k6_z4_tutma6`: eğitim +%27,1, 2× +%11,4, Sharpe 0,46,
  188 işlem, alfa +%7,6, beta −0,02. Komşuları (k3, tutma 3, SOLETH) +%4…+%23 / Sharpe 0,13–0,34;
  z_in 3 hemen her yerde negatif. 4h: hepsi negatif.
- Yıllık döküm (`tanilama3.txt`, yalnız eğitim): kâr 2021–2022'de; 2023 negatif, 2024 karışık.
  Maliyet brüt kazancın yaklaşık 1/3–1/2'si. Fonlama etkisi ihmal edilebilir (kısa tutma).

### Tarama 3 planı

Şok sönümlenmesi (1h, bir, k 3/6, z_in 3/4, tutma 3/6) × çift (SOLBTC, SOLETH, üçlü
portföy) × emir tipi (piyasa; limit 5 bp/1 bar her değişimde; limit 10 bp/2 bar her
değişimde; limit 5 bp/1 bar yalnız girişte). Amaç: maliyeti (28 bp → ~8 bp) düşürmenin
seçici dolum kaybına (adverse selection) değip değmediğini görmek.

### Tarama 3 sonucu (96 yapılandırma; 24'ü tarama 2'den defterde)

- Limit emir (her değişimde, 10 bp, 2 bar sonra piyasa) maliyeti kabaca 1/3'e indiriyor
  (SOLBTC k6 z4 tutma 6: maliyet 0,132 → 0,041) ve brütü de biraz artırıyor:
  eğitim +%27,1 → +%40,3, Sharpe 0,46 → 0,61, 2× +%34,7. Yalnız girişte limit daha zayıf.
- Üçlü portföy ETH/BTC yüzünden zayıf (en iyi Sharpe 0,31).

### Tarama 4 sonucu (105 yapılandırma; 9'u defterde)

- z_in 5: SOLBTC k6 tutma 6 limit 10/2 → +%60,6, Sharpe 1,08, 108 işlem (bacak bazında;
  çift işlemi ≈ 54). SOLBTC+SOLETH k6 z5 tutma 6 → Sharpe 0,85, 163 işlem;
  k12 z5 tutma 3 → 0,92, 102 işlem.
- Limit ofseti: 20 bp > 10 bp > 5 bp (SOLBTC k6 z4 h6: 0,72 / 0,61 / 0,52); bar sayısı 2–3 ≈ aynı.
- Yıllık döküm (`tanilama4.txt`): kâr ağırlıkla 2021–2022; 2023 sıfır/negatif, 2024 küçük
  pozitif. Her yıl pozitif olan tek yapılandırma SOLBTC+SOLETH k12 z5 tutma 3
  (+2,6/+9,2/+5,2/+3,0/+2,2%).
- `tanilama5.txt` (OI değişimi × şok dönüşü, 2021-12 sonrası eğitim): işaretler k ve ufka
  göre çelişkili (n 60–130), OI filtresi kurulmadı.

### Tarama 5 sonucu (128 yapılandırma): trend yönünde geri çekilme

- Kısa pencereli düzey z + uzun pencereli trend filtresi. En iyi: 4h SOLBTC z_win 12 z_in 2,5
  rejim 180 eşik 0 → +%15,4, Sharpe 0,41, 82 işlem; z_win 30 z_in 2 → +%29,3 / 0,40.
  ETH/BTC, SOL/ETH ve portföyler ~0 ya da negatif. Zayıf; ana aday değil.

### Tarama 6 planı (duyarlılık; sonuçlardan önce yazıldı)

Öncü şok yapılandırmaları (1h, bir, limit her değişimde):
- A: SOLBTC k6 z4 tutma 6, limit 20 bp/2 bar
- B: SOLBTC k6 z5 tutma 6, limit 10/2
- C: SOLBTC+SOLETH k6 z5 tutma 6, limit 10/2
- D: SOLBTC+SOLETH k12 z5 tutma 3, limit 10/2

Duyarlılık: her biri için vol_win 250 ve 1000 (merkez 500), z_in 4,5; B/C/D için limit 20/2.
Karar kuralı: dondurulacak yapılandırmalar ızgara merkezinden (vol_win 500) seçilir; bir
komşuda Sharpe < 0 ise (uçurum) o aday elenir. Limit ofseti (10/20 bp) eğitim Sharpe'ına
göre seçilebilir (maliyet/dolum parametresi; mekanizması belli).

### Tarama 6 sonucu (19 satır; 15 yeni yapılandırma, 4 merkez defterden)

| Aday | merkez Sharpe | vol_win 250 | vol_win 1000 | z_in ±0,5 | limit 20 |
|---|---:|---:|---:|---:|---:|
| A SOLBTC k6 z4 h6 l20 | 0,72 | 0,72 | **−0,09** | 0,76 (z4,5) | — |
| B SOLBTC k6 z5 h6 l10 | 1,08 | 0,87 | 0,43 | 0,70 (z4,5) | 1,10 |
| C SOLBTC+SOLETH k6 z5 h6 l10 | 0,85 | 0,66 | 0,11 | 0,78 (z4,5) | 0,88 |
| D SOLBTC+SOLETH k12 z5 h3 l10 | 0,92 | 1,02 | 0,55 | 0,69 (z4,5) | 0,91 |

Kural gereği A elendi (vol_win 1000'de Sharpe < 0). B, C, D kaldı. vol_win 1000'de hepsi
zayıflıyor: oynaklık penceresi kısa olmalı (yakın dönem oynaklığına göre şok). Limit ofseti:
B ve C için 20 bp (biraz daha iyi), D için 10 bp.

### Tanılama 6 (geniş evren, betimleyici)

`tanilama6.txt`: o ay evrende olan 97 altcoin/BTC çifti (indirmesi biten semboller), 4h şok
sonrası dönüş. Medyan pozitif (+20…+118 bp) ama ortalama işaret değiştiriyor ve yıllara göre
çok oynak (büyük şokların bir kısmı devam ediyor, kalın kuyruk). Ayrıca 4h'te BTC/ETH/SOL şok
yapılandırmaları (tarama 2) negatifti. Geniş evren stratejisi kurulmadı. (Ek not: harness'te
bacak ağırlıkları sabit olduğundan ~300 bacaklı bir evrende her bacağın sermaye payı ~1/300
olurdu.)

## DONDURMA KARARI (dev_valid'e bakmadan, 9 Ekim 2026)

Toplam eğitim araması bu noktada: defterde 189 (kesinti öncesi) + 129 (tarama 2 kalanı) + 80
(tarama 3) + 95 (tarama 4) + 128 (tarama 5) + 15 (tarama 6) = 636 benzersiz yapılandırma
(dev_train, 1× ve 2×; defterle doğrulandı — ilk yazımdaki 629 hesap hatasıydı).

Dondurulan 3 yapılandırma (hepsi 1h, `hedge="bir"`, `z_tur="sok"`, `vol_win=500`,
`z_exit=None`, limit emir her pozisyon değişiminde `limit_mod="tum"`, `limit_bar=2`):

| Kod | Çiftler | k | z_in | tutma | limit bps | Eğitim getiri / 2× / Sharpe / işlem / alfa |
|---|---|---:|---:|---:|---:|---|
| B | SOLBTC | 6 | 5,0 | 6 | 20 | +%65,5 / +%61,3 / 1,10 / 108 / +%12,1 |
| C | SOLBTC+SOLETH | 6 | 5,0 | 6 | 20 | +%31,0 / +%29,0 / 0,88 / 163 / +%6,6 |
| D | SOLBTC+SOLETH | 12 | 5,0 | 3 | 10 | +%24,0 / +%22,9 / 0,92 / 102 / +%4,8 |

Gerekçe:
- Eğitimde tutarlı tek mekanizma: SOL içeren yayılımlarda 6–12 saatlik çok büyük (≥ 5σ) şokların
  sonraki 3–6 saatte kısmen geri dönmesi. ETH/BTC'de yok. Düzey z-skoru (klasik çift) ve trend
  yönünde geri çekilme eğitimde negatif ya da zayıf.
- Limit emir maliyeti üçte birine indiriyor; 2× maliyette de getiri pozitif kalıyor.
- Duyarlılık (tarama 6): vol_win 250 / z_in 4,5 komşuları pozitif, vol_win 1000 zayıf ama ≥ 0.
- D, eğitimin her yılında pozitif olan tek yapılandırma; B en yüksek Sharpe; C ikisinin arası
  (iki çift, daha çok işlem).
- Riskler (önceden kayıt): kârın çoğu 2021–2022'den; 2023'te B ve C negatif/sıfır. Olaylar
  seyrek (maruziyet %0,3–0,9), iç doğrulamada 20 işlem sınırına yakın kalınabilir. B/C/D aynı
  mekanizma ve kısmen aynı işlemler: bağımsız 3 deneme değildir. SOL'ün protokol evreninde
  bulunması (DENETIM_1 bölüm 7) bu aileye de uygulanır.
- 4. ve 5. hak kullanılmadı: kalan fikirlerin (trend yönünde geri çekilme Sharpe ≤ 0,41,
  ETH/BTC, geniş evren) eğitim kanıtı dondurmaya yetmiyor.

Sonraki adımlar: `specs()` bu üç yapılandırmayı döndürecek; `assert_causal`; eğitim içi döküm
(yıllık, çift/bacak, fonlama payı); sonra `dogrulama.py` ile her biri için tek bir
`evaluate(spec)` ve `candidate_check`. dev_valid sonrası değişiklik yapılmayacak.

dev_valid değerlendirmesi başlatıldı: 2026-10-09T08:59:24Z (`dogrulama.py`, tek seferlik). `dondurma_kontrol.log`: üç yapılandırma defterle birebir eşleşiyor, `assert_causal` varsayılan ve ek kesimlerde geçti.

## dev_valid sonrası (9 Ekim 2026, 08:59 UTC; değişiklik yapılmadı)

- B: +%7,50 (2× +%6,77), Sharpe 0,91, 28 işlem, alfa +%4,24 (t 1,20) → candidate_check GEÇTİ.
- C: +%4,33 (2× +%3,80), Sharpe 0,73, 55 işlem, alfa +%2,49 (t 0,96) → GEÇTİ.
- D: +%0,56 (2× +%0,25), Sharpe 0,19, 41 işlem → GEÇMEDİ (Sharpe < 0,5).
- B ve C'de en iyi tek işlem çıkarılınca dev_valid getirisi negatif (−%0,52 / −%0,99).
  DSR 0,001–0,002 (639 deneme satırı). B ile C'nin dev_valid günlük korelasyonu 0,91.
- dev_valid'e bakıldıktan sonra parametre, kod ya da arama değişmedi; yalnız `specs()`
  açıklamalarına sonuç yazıldı ve betimleyici döküm/korelasyon hesaplandı (deftere yazılmadan).
