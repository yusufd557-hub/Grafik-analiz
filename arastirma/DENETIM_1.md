# Bağımsız Denetim 1 — Strateji araştırması (8 aile)

Tarih: 8 Ekim 2026 · Kapsam: `docs/PROTOKOL.md` (sürüm 1), `grafik_analiz/research/*.py`,
`grafik_analiz/strategies/*.py`, `arastirma/deneyler/*.jsonl`, ailelerin `arastirma/<aile>/`
klasörleri ve araştırmacıların yapılandırılmış raporları.

Denetçi bu çalışmada görülmemiş döneme (holdout) erişmedi, `unlock_holdout()` çağırmadı,
`scope="holdout"`/`"all"` kullanmadı, veri dosyalarını doğrudan okumadı ve bu dosya
dışında depodaki hiçbir dosyayı değiştirmedi. Bütün yeniden çalıştırmalar
`evaluate(..., record=False)` ile yapıldı. Denetimden önce ve sonra deney defterlerinin
md5 özetleri karşılaştırıldı; değişmediler.

---

## 0. Kısa sonuç

| Madde | Sonuç |
|---|---|
| 1. Holdout erişim kaydı | `arastirma/holdout_kayit.jsonl` **yok**; git geçmişinde de hiç olmadı. Kritik ihlal yok. |
| 2. Defter disiplini | 8 ailenin hepsi en fazla 5 yapılandırmayı dev_valid'de ölçtü (toplam 33). Raporlanan `configurations_evaluated` ve `dev_valid_looks` değerleri defterle birebir tutuyor. Defterler yalnız ekleme ile büyüdü (git: 0 silinen satır). dev_valid'e bakıldıktan sonra yeni arama satırı yok. |
| 3. Kod incelemesi | İleri bakış bulunmadı. İzinli yollar dışında yazılmış dosya yok. |
| 4. Nedensellik ve yeniden üretim | 33 spec'in hepsi `assert_causal`'ı varsayılan ve ek kesimlerle geçti. Formasyon için olay bazlı, ML için ay başı arındırma testleri de geçti. dev_valid 1×/2× getirileri en fazla 0,005 yüzde puan farkla yeniden üretildi (eşik 0,5 yp). |
| 5. Testler | `pytest tests -q`: **49 geçti**, 0 başarısız (2 uyarı). |
| 6. Denenmeyen yaklaşımlar | Bölüm 6'da 12 somut öneri. |

Kurallara aykırı bir davranış bulunmadı. Ama aday kanıtı zayıf:

- 15 aday var, ancak bunlar yaklaşık 7 bağımsız kümeye denk geliyor. Trend'in 4 adayı birbiriyle 0,99–1,00, kırılımın 2 adayı 0,99 korelasyonlu.
- Trend adaylarının dev_valid alfası yaklaşık 0; getirileri al-tut betasından (yaklaşık 0,45) geliyor.
- Hiçbir adayın alfası çoklu deneme düzeltmesinden sonra anlamlı değil. En yüksek düzeltilmemiş alfa t-değeri 2,30 ve o da 27 işlemli, aşırı çarpık bir ML adayına ait (bkz. bölüm 4.3).
- Görülmemiş dönem, dil modeli araştırmacıların eğitim bilgisiyle kısmen örtüşüyor (bkz. bölüm 7).

---

## 1. Holdout erişim kaydı

- `arastirma/holdout_kayit.jsonl` dosyası yok. `git log --all -- arastirma/holdout_kayit.jsonl` boş.
- `arastirma/` ve `grafik_analiz/strategies/` altındaki hiçbir betik `unlock_holdout`,
  `scope="holdout"`, `scope="all"`, `_UNLOCKED`, `read_parquet`, `CandleStore` ya da
  `research_data_dir` kullanmıyor. `DEV_END` ya da kilit monkeypatch edilmiyor.
- Betiklerde görülen 2025-07 sonrası tarih dizgileri yalnız `DEV_END` için dışlayıcı üst sınır olarak kullanılıyor (`("2025-01-01","2025-07-01")`).
- Mevsimsellik `tani_valid.log` dosyasında "2025-07" satırı var. Bu, Temmuz ay dönümü penceresinin 27–30 Haziran 2025 kısmıdır ve dev döneminin içindedir.
- Testler holdout'u yalnız `tmp_path` altındaki sentetik veriyle açıyor. Test çalıştırmasından sonra depoda kayıt dosyası oluşmadı.

**Sonuç: ihlal yok.**

---

## 2. Defter disiplini

Kaynak: `arastirma/deneyler/<aile>.jsonl`. Benzersiz yapılandırma, `parametreler` alanının
(aralık ve bacaklar dahil) eşsiz değeridir.

| Aile | Satır | dev_train 1× satır | Benzersiz yapılandırma (defter / rapor) | dev_valid yapılandırma (defter / rapor) | Durum |
|---|---:|---:|---:|---:|---|
| trend | 390 | 190 | 185 / 185 | 5 / 5 | uyumlu |
| rotasyon | 506 | 248 | 243 / 243 | 5 / 5 | uyumlu |
| ortalamaya_donus | 189 | 169 | 164 / 164 | 4 / 4 | uyumlu |
| kirilim | 708 | 351 | 348 / 348 | 3 / 3 | uyumlu |
| fonlama_carry | 848 | 420 | 416 / 416 | 4 / 4 | uyumlu |
| mevsimsellik | 260 | 126 | 122 / 122 | 4 / 4 | uyumlu |
| makine_ogrenmesi | 330 | 161 | 157 / 157 | 4 / 4 | uyumlu |
| formasyon | 604 | 298 | 294 / 294 | 4 / 4 | uyumlu |
| **Toplam** | **3.835** | **1.963** | **1.929** | **33** | |

Ek kontroller:

- Her dev_valid yapılandırmasının parametreleri, arama sırasında dev_train'de değerlendirilmiş bir yapılandırmayla birebir aynı.
- dev_valid'e ilk bakıştan sonra deftere yazılan dev_train satırları yalnızca dondurulan yapılandırmaların `evaluate(spec)` tekrarlarıdır. dev_valid'den sonra arama yapılmamış.
- Her dev_valid yapılandırması defterde tam olarak bir kez var (1× ve 2× satırı).
- Bütün satırlarda `protokol == "1"` ve `aile` doğru. Git'te defterler yalnız ekleme ile büyüdü. Makine öğrenmesi defterinin commit edilmemiş farkı +32 satır, −0 satır.
- Dosya zaman damgaları defterle tutarlı. Dondurma notu ya da `dogrulama.py`, ilk dev_valid satırından önce yazılmış:

  | Aile | Dondurma notu / betiği | İlk dev_valid satırı |
  |---|---|---|
  | trend | NOTLAR 11:17:10 | 11:17:46 |
  | kırılım | NOTLAR 11:34:51 | 11:35:24 |
  | mevsimsellik | NOTLAR 14:10:46 | 14:11:01 |
  | fonlama | dogrulama.py 14:11:58 | 14:12:01 |
  | formasyon | dogrulama.py 14:31:53 | 14:31:55 |
  | rotasyon | dogrulama.py 11:18:14 | 11:18:15 |
  | ortalamaya dönüş | dogrulama.py 11:32:44 | 11:32:55 |
  | makine öğrenmesi | dogrulama.py 18:56 | 19:42:12 |

**Sonuç:** Hiçbir aile 5 dev_valid sınırını aşmadı. Raporlanan sayılar defterle tutarlı.

Not: Aile içi Deflated Sharpe'lar yalnız o ailenin denemelerini sayıyor. Programın bütününde
yaklaşık 1.929 benzersiz yapılandırma denendi ve 33 yapılandırma dev_valid'de ölçüldü.
Finalistler bu 33 yapılandırma arasından dev_valid sonucuna bakılarak seçilirse, dev_valid artık
temiz bir örneklem dışı tahmin değildir (bkz. bölüm 7).

---

## 3. Kod incelemesi (ileri bakış ve dosya disiplini)

Her `grafik_analiz/strategies/<aile>.py` satır satır okundu. Ayrıca kullandıkları
`indicators.py`, `pivots.zigzag`, `patterns/chart.py` ve `patterns/base.py` incelendi. Aranan
riskler şunlardı:

- negatif `shift`
- ortalanmış pencere
- tam örneklem istatistiği, normalleştirme ya da model uydurma
- zaman damgasından önce fonlama kullanımı
- t+1 barı verisi
- ML etiket sızıntısı
- bacakların hayatta kalan yanlılığı

| Aile | Bulgu |
|---|---|
| trend | Bütün bileşenler geriye dönük: `shift(+n)`, `rolling`, EMA, Donchian `high.shift(1)`, baştan yürüyen durum makinesi, bant. Oynaklık hedefleme geriye dönük std kullanıyor. Sorun yok. |
| rotasyon | Skorlar `shift(lookback)` ile hesaplanıyor; yeniden dengeleme takvime bağlı (seri kısalınca değişmiyor). Vadeli bacakta ilk fonlama kaydından önce pozisyon açılmıyor (`close_time ≥ ilk kayıt`). Sorun yok. |
| ortalamaya_donus | Sapma ölçüleri geriye dönük; `ret` ölçüsünde oynaklık `shift(n)` ile hareketten önce alınıyor. Durum makinesi baştan yürüyor. Vadeli 1h/15m veri 2020-01-01'de başladığı için fonlama boşluğu yok. Sorun yok. |
| kirilim | Kanal `shift(1)`; hacim tabanı `shift(1)`; gün içi değerler önceki günün `shift(1)` değerleri; ATR iz stop barın kendi yüksek/düşüğünü kapanışta kullanıyor (o anda biliniyor). `_bar_minutes` tam örneklem medyanı, ama yalnız bar aralığını buluyor (zararsız). Sorun yok. |
| fonlama_carry | Fonlama `zaman damgası ≤ bar açılışı` ile kullanılıyor (kapanış şartından da sıkı). Zaman pencereli toplamlar geriye dönük. Pozisyonlar ilk fonlama kaydından sonra. Sorun yok. |
| mevsimsellik | Takvim sinyalleri bir sonraki barın başlangıç zamanına bakıyor (önceden biliniyor). Uyarlamalı yöntemler `searchsorted(..., "left") − 1` ile kesinlikle önceki gün ve ayları kullanıyor. Fonlama penceresi S − 8 saatteki oranı kullanıyor. Sorun yok. |
| makine_ogrenmesi | Aylık ileriye yürüyen eğitim. Eğitim satırı şartı `known_ns < ay_başı`; etiket `open[t+1+H]` ve bilinme zamanı `index[t+1+H]`, yani arındırma doğru. Özellikler geriye dönük; fonlama ≤ bar açılışı; ölçekleyiciler yalnız eğitim satırına uyduruluyor; HGB deterministik (`random_state=0`). `shift(-(1+H))` yalnız etikette kullanılıyor ve eğitim maskesiyle korunuyor. Sorun yok. |
| formasyon | Zigzag pivotları kesinleşme barında biliniyor. Formasyon `detected_index` barından itibaren aranıyor. Kırılım ilk kapanış aşımı. `outcome` alanları kullanılmıyor; çıkışlar ileri yönde kapanışla izleniyor. `merge_scales` önce tespit edileni tutuyor. Sorun yok. Önbellek anahtarı kesik seriyi ayırt ediyor. |

Hayatta kalan yanlılığı: Bütün aileler protokolün sabitlediği BTC/ETH/SOL evrenini kullanıyor.
SOL, 2026'da bilinen başarısı nedeniyle seçilmiş bir coin. Birçok adayın kârı ağırlıkla SOL
bacağından geliyor: ML vadeli iki yön, formasyon F1/F2, ortalamaya dönüşün 2021 dev_train
katkısı. Bu araştırmacı hatası değil, protokol düzeyinde bir yanlılık (bkz. bölüm 7).

Dosya disiplini (`git status`, `git diff --stat 3024bcf..HEAD`):

- Araştırma commit'lerinde ve çalışma ağacında değişen her dosya şu izinli yollardan birinde: `arastirma/<aile>/`, `arastirma/deneyler/<aile>.jsonl`, `grafik_analiz/strategies/<aile>.py`.
- `grafik_analiz/research/*.py`, `docs/PROTOKOL.md` ve `tests/` araştırma başladıktan sonra değişmedi.
- Makine öğrenmesi ailesinin son çalışması (spec'ler, RAPOR, dondurulmuş sonuçlar) henüz commit edilmemiş. Bunlar izinli yollarda.

Defter dışı ya da sınırda kalan bakışlar (hepsi araştırmacılar tarafından açıklanmış; küçük):

- **fonlama_carry `mekanik_kontrol.py`:** Aramadan önce bir BTC carry yapılandırmasının 2020-01 – 2025-06 arası toplam fonlama tutarını yazdırmış (−0,6027). Bu sayı dev_valid'i de kapsıyor ve carry getirisinin neredeyse tamamı fonlama olduğu için dolaylı performans bilgisidir.
- **mevsimsellik:** Defter dışında 660 betimleyici keşif hücresi var (saat, gün, ay dönümü yüzeyi). Bunlar ham veride 2024 öncesine kesilerek hesaplandı ama deftere yazılmadı. Protokoldeki "her yapılandırma deftere yazılır" kuralıyla tam uyumlu değil. Araştırmacı bunu ihtiyatlı bir DSR varyantında saydı.
- **kirilim `sinyal_testi.py`, trend duman testi:** Bütün dev dönemi üzerinde pozisyon oranlarını (uzun %, kısa %) yazdırmışlar. Performans bilgisi yok.
- **rotasyon ve ortalamaya_donus:** `NOTLAR.md` yok. Dondurma gerekçesinin dev_valid'den önce yazıldığı yalnız `dogrulama.py` dosyasının zaman damgasıyla doğrulanabiliyor.
- **makine_ogrenmesi:** `tani_oynaklik.log` dosyasını üreten betik kaydedilmemiş (dondurma sonrası, betimleyici).
- **rotasyon:** Yapılandırılmış raporda vadeli spec'lerin `buy_hold_dev_valid_return` değeri 0 yazılmış. Bu değer hesaplanmamış; 0 diye raporlanmamalı.

---

## 4. Nedensellik ve yeniden üretim

### 4.1 Yöntem

`grafik_analiz.strategies.all_specs()` 33 spec döndürdü. Her biri için:

1. `assert_causal(spec)`: varsayılan kesimler 0,55, 0,80 ve 0,97.
2. Ek kesimlerle `assert_causal`:
   - ML dışı aileler: 0,3, 0,5, 0,65, 0,7, 0,75, 0,85, 0,9, 0,93, 0,99.
   - ML: 0,9 ve 0,995.
3. `evaluate(spec, record=False)`: dev_train ve dev_valid, 1× ve 2× maliyet.

Ek hedefli testler:

- **Formasyon (olay bazlı):** 2023-06 sonrasındaki her pozisyon değişim barında seri tam o barda kesildi ve geçmiş sinyaller karşılaştırıldı.
- **Makine öğrenmesi (arındırma):** Seri, aylık yeniden eğitim anından 2 bar sonra (2024-03-01 02:00 UTC) kesildi. Etiket arındırması hatalı olsaydı bu kesim farkı gösterirdi; rastgele kesimler bunu genelde yakalayamaz.

### 4.2 Sonuçlar

| Aile | Spec | Nedensellik (varsayılan / ek) | dev_valid 1× rapor → yeniden | dev_valid 2× rapor → yeniden | En büyük fark (yp) | Sharpe | İşlem | Aday |
|---|---|---|---|---|---:|---:|---:|---|
| trend | `trend_ens_spot_port3_1d` | geçti / geçti | +32,51 → +32,51 | +28,39 → +28,39 | 0,000 | 0,69 | 36 | GEÇTİ |
| trend | `trend_ens_spot_port3_4h` | geçti / geçti | +38,63 → +38,63 | +34,22 → +34,22 | 0,000 | 0,77 | 66 | GEÇTİ |
| trend | `trend_ens_spot_port3_4h_vt` | geçti / geçti | +42,69 → +42,69 | +38,70 → +38,70 | 0,000 | 0,91 | 66 | GEÇTİ |
| trend | `trend_ens_vadeli_port3_4h_alim` | geçti / geçti | +26,53 → +26,53 | +22,07 → +22,07 | 0,000 | 0,60 | 62 | GEÇTİ |
| trend | `trend_ens_vadeli_port3_4h_ls_vt` | geçti / geçti | -3,28 → -3,28 | -8,88 → -8,88 | 0,000 | 0,12 | 180 | geçmedi |
| rotasyon | `rotasyon_spot_top1_L14_gunluk` | geçti / geçti | +9,63 → +9,63 | +5,84 → +5,84 | 0,002 | 0,42 | 44 | geçmedi |
| rotasyon | `rotasyon_spot_top2_L28_gunluk` | geçti / geçti | -4,09 → -4,09 | -7,67 → -7,67 | 0,005 | 0,04 | 47 | geçmedi |
| rotasyon | `rotasyon_vadeli_uzunkisa_karma28` | geçti / geçti | -39,22 → -39,22 | -40,73 → -40,73 | 0,004 | -1,70 | 54 | geçmedi |
| rotasyon | `rotasyon_vadeli_uzunkisa_L21_volesit` | geçti / geçti | -6,92 → -6,92 | -12,75 → -12,75 | 0,004 | -0,25 | 148 | geçmedi |
| rotasyon | `rotasyon_oran_SOLBTC_n50_yukari` | geçti / geçti | -27,62 → -27,62 | -29,77 → -29,77 | 0,004 | -1,22 | 42 | geçmedi |
| ortalamaya_donus | `od_dip_ens4_fut_port3_1h` | geçti / geçti | +7,47 → +7,47 | +4,08 → +4,08 | 0,000 | 0,86 | 140 | GEÇTİ |
| ortalamaya_donus | `od_dip_ens4_fut_port3_15m` | geçti / geçti | +7,95 → +7,95 | -1,17 → -1,17 | 0,000 | 0,64 | 400 | geçmedi |
| ortalamaya_donus | `od_dip_ret4h_fut_port3_1h` | geçti / geçti | +13,87 → +13,87 | +10,42 → +10,42 | 0,000 | 1,09 | 66 | GEÇTİ |
| ortalamaya_donus | `od_dip_ens4_spot_port3_1h` | geçti / geçti | +5,63 → +5,63 | -0,14 → -0,14 | 0,000 | 0,64 | 144 | geçmedi |
| kirilim | `kirilim_kanal4h_spot` | geçti / geçti | +47,56 → +47,56 | +42,11 → +42,11 | 0,000 | 1,13 | 47 | GEÇTİ |
| kirilim | `kirilim_kanal4h_vadeli_iki` | geçti / geçti | +6,00 → +6,00 | +1,68 → +1,68 | 0,000 | 0,29 | 89 | geçmedi |
| kirilim | `kirilim_kanal4h_vadeli_uzun` | geçti / geçti | +47,36 → +47,36 | +44,29 → +44,29 | 0,000 | 1,13 | 45 | GEÇTİ |
| fonlama_carry | `fonlama_carry_sepet3_hizli` | geçti / geçti | +4,50 → +4,50 | +4,01 → +4,01 | 0,000 | 7,36 | 12 | geçmedi |
| fonlama_carry | `fonlama_carry_sepet3_yavas_dusuk` | geçti / geçti | +7,49 → +7,49 | +7,42 → +7,42 | 0,000 | 13,10 | 2 | geçmedi |
| fonlama_carry | `fonlama_carry_btc_surekli` | geçti / geçti | +7,39 → +7,39 | +7,39 → +7,39 | 0,000 | 13,58 | 0 | geçmedi |
| fonlama_carry | `fonlama_negatif_uzun_sepet3` | geçti / geçti | -13,17 → -13,17 | -14,18 → -14,18 | 0,000 | -0,68 | 25 | geçmedi |
| mevsimsellik | `tom_1d_fut_PORT3_a4_b5` | geçti / geçti | -44,23 → -44,23 | -45,61 → -45,61 | 0,004 | -0,98 | 54 | geçmedi |
| mevsimsellik | `tom_1d_spot_PORT3_a4_b5` | geçti / geçti | -42,21 → -42,21 | -44,64 → -44,64 | 0,004 | -0,91 | 54 | geçmedi |
| mevsimsellik | `tom_1d_fut_PORT2_a4_b5` | geçti / geçti | -40,51 → -40,51 | -41,98 → -41,98 | 0,004 | -1,01 | 36 | geçmedi |
| mevsimsellik | `tomk_1d_fut_PORT3_a2-5_b2-5` | geçti / geçti | -36,21 → -36,21 | -37,80 → -37,80 | 0,004 | -0,94 | 54 | geçmedi |
| makine_ogrenmesi | `ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot` | geçti / geçti | +23,14 → +23,14 | +15,17 → +15,17 | 0,005 | 1,41 | 320 | GEÇTİ |
| makine_ogrenmesi | `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot` | geçti / geçti | +13,16 → +13,16 | +10,32 → +10,32 | 0,001 | 1,50 | 112 | GEÇTİ |
| makine_ogrenmesi | `ml_1h_sp_PORT3_hgb_reg_H6_k3.0_ortusen_uzun_temel` | geçti / geçti | +3,41 → +3,41 | +1,97 → +1,97 | 0,005 | 0,76 | 55 | GEÇTİ |
| makine_ogrenmesi | `ml_1h_sp_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel-btc` | geçti / geçti | +9,09 → +9,09 | +8,22 → +8,22 | 0,003 | 1,88 | 27 | GEÇTİ |
| formasyon | `formasyon_ucgen_kama_4h_trend_uzun` | geçti / geçti | +24,78 → +24,78 | +22,54 → +22,54 | 0,004 | 1,00 | 39 | GEÇTİ |
| formasyon | `formasyon_ucgen_kama_4h_hacim_iki` | geçti / geçti | +30,72 → +30,72 | +27,41 → +27,41 | 0,004 | 1,13 | 55 | GEÇTİ |
| formasyon | `formasyon_hepsi_4h_trend_10bar_uzun` | geçti / geçti | +24,54 → +24,54 | +20,12 → +20,12 | 0,002 | 1,12 | 78 | GEÇTİ |
| formasyon | `formasyon_hepsi_1d_olcek234_iki` | geçti / geçti | +7,50 → +7,50 | +5,61 → +5,61 | 0,001 | 0,31 | 39 | geçmedi |

Bütün 33 spec varsayılan ve ek kesimlerde `assert_causal`'ı geçti.

Yeniden üretim:

- dev_valid 1× ve 2× getirilerindeki en büyük fark 0,005 yüzde puan. Bu fark yalnız raporlardaki yuvarlamadan geliyor; eşik 0,5 yp.
- dev_train getirileri, Sharpe ve işlem sayıları da birebir aynı.
- `candidate_check` sonuçları raporlarla aynı: 15 aday geçiyor (trend 4, ortalamaya dönüş 2, kırılım 2, makine öğrenmesi 4, formasyon 3), 18 yapılandırma geçmiyor.

Hedefli testler:

- **Formasyon, olay bazlı:** 4 spec'te 2023-06 sonrasındaki her pozisyon değişim barında kesim yapıldı (112 + 155 + 225 + 83 = 575 kesim). **Hiç fark yok.** Kırılım olayları yalnız o bara kadarki veriyle aynen bulunuyor.
- **Makine öğrenmesi, arındırma:** Kesim, aylık yeniden eğitimden hemen sonraya kondu.
  - `…hgb_reg_H4…_egspot`: 2024-03-01 02:00 ve 2024-09-01 01:00 kesimleri.
  - `…hgb_clf_H6…_egspot`: 2024-03-01 02:00 kesimi.
  - `…hgb_reg_H4…temel-btc`: 2024-03-01 02:00 kesimi.

  Hepsi **geçti**. Etiketi eğitim anından sonra belli olan satırlar eğitime girmiyor.

**Sonuç: ileri bakış bulunamadı; yeniden üretim uyumsuzluğu yok.**

### 4.3 Aday kalitesi (betimleyici, dev_valid zaten bakılmış veriyle)

`candidate_check` geçen 15 aday için dev_valid günlük getirileri spot PORT3 al-tut'a göre
regresyonla incelendi:

| Aday | Al-tut betası | Korelasyon | Yıllık alfa | Alfa t | Bootstrap p | DSR (aile tarifi) | En iyi işlem çıkınca | Maruziyet |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `trend_ens_spot_port3_1d` | 0,45 | 0,77 | %0,0 | 0,00 | 0,201 | 0,326 | %17,5 | %92,5 |
| `trend_ens_spot_port3_4h` | 0,46 | 0,78 | %2,7 | 0,14 | 0,177 | 0,361 | %24,6 | %93,9 |
| `trend_ens_spot_port3_4h_vt` | 0,38 | 0,77 | %6,9 | 0,42 | 0,141 | 0,425 | %28,2 | %93,9 |
| `trend_ens_vadeli_port3_4h_alim` | 0,47 | 0,79 | %-3,7 | -0,20 | 0,230 | 0,287 | %15,2 | %93,9 |
| `kirilim_kanal4h_spot` | 0,23 | 0,56 | %16,3 | 0,93 | 0,087 | 0,010 | %28,3 | %41,7 |
| `kirilim_kanal4h_vadeli_uzun` | 0,23 | 0,56 | %16,3 | 0,93 | 0,089 | 0,010 | %27,3 | %41,5 |
| `od_dip_ret4h_fut_port3_1h` | 0,02 | 0,16 | %7,8 | 1,18 | 0,072 | 0,041 | %9,7 | %4,1 |
| `od_dip_ens4_fut_port3_1h` | 0,03 | 0,34 | %3,2 | 0,72 | 0,133 | 0,026 | %4,9 | %19,6 |
| `formasyon_ucgen_kama_4h_trend_uzun` | 0,12 | 0,46 | %9,4 | 0,81 | 0,106 | 0,101 | %12,3 | %28,5 |
| `formasyon_ucgen_kama_4h_hacim_iki` | -0,01 | -0,05 | %20,1 | 1,44 | 0,110 | 0,141 | %16,9 | %37,7 |
| `formasyon_hepsi_4h_trend_10bar_uzun` | 0,09 | 0,41 | %10,5 | 1,01 | 0,096 | 0,128 | %15,5 | %19,9 |
| `ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot` | 0,04 | 0,22 | %12,4 | 1,53 | 0,024 | 0,551 | %20,4 | %17,3 |
| `ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot` | 0,02 | 0,17 | %7,5 | 1,67 | 0,016 | 0,608 | %10,1 | %4,5 |
| `ml_1h_sp_PORT3_hgb_reg_H6_k3.0_ortusen_uzun_temel` | 0,01 | 0,13 | %1,9 | 0,79 | 0,173 | 0,253 | %2,2 | %2,8 |
| `ml_1h_sp_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel-btc` | 0,00 | 0,00 | %5,8 | 2,30 | 0,000 | 0,908 | %6,0 | %0,9 |

(Alfa, günlük getirilerin spot PORT3 al-tut getirisine regresyonundan; t-değeri otokorelasyon ve çoklu deneme için düzeltilmemiş. "En iyi işlem çıkınca" harness'in `total_without_best` ölçüsüdür.)

- **Trend adayları fiilen tek strateji.** Aralarındaki korelasyon 0,99–1,00. Al-tut betası 0,38–0,47, yıllık alfa yaklaşık 0 (t −0,20 … 0,42). dev_valid getirisi piyasa yönünden geliyor.
- **Kırılım spot ve vadeli adayları aynı fikrin kopyası** (korelasyon 0,99). Trend adaylarıyla korelasyonları da 0,76–0,77.
- **ML'in üç yalnız alım adayı** (vadeli reg H4, spot reg H6, spot reg H4+btc) birbiriyle 0,68–0,80 korelasyonlu. Formasyon F1 ile F3 arasındaki korelasyon 0,62.
- Korelasyon ≥ 0,6 eşiğiyle 15 aday yaklaşık **7 bağımsız kümeye** iniyor:
  - trend ve kırılım
  - formasyon F1/F3
  - formasyon F2
  - dip alımı topluluğu
  - dip alımı ret4h
  - ML yalnız alım
  - ML iki yön
- **Hiçbir aday çoklu deneme düzeltmesinden sonra anlamlı değil.**
  - Düzeltilmemiş alfa t-değeri en yüksek olanlar ML adayları: 1,53, 1,67 ve 2,30. Formasyon F2'de 1,44.
  - Spot+btc ML adayının değeri (t 2,30, p 0,000, DSR 0,91) güvenilir değil: yalnız 27 işlem var, zamanın %0,9'unda pozisyonda, günlük çarpıklık 11.
- Bootstrap p-değerleri ve Deflated Sharpe değerleri raporlananlarla aynı çıktı. Bütün adaylarda DSR 0,95'in altında. 0,95'i geçen tek yapılandırmalar aday olamayan carry yapılandırmaları; onların Sharpe değeri araç varsayımlarıyla şişiyor (bkz. 5.2).

---

## 5. Testler ve harness gözlemleri

### 5.1 Test sonucu

```
QT_QPA_PLATFORM=offscreen /home/user/venv/bin/python -m pytest tests -q
49 passed, 2 warnings
```

Uyarılar `stats.skew/kurtosis` hassasiyet uyarısıdır (sentetik sabit seri). Strateji
modülleri için ayrı test yok. Ailelerin nedensellik garantisi yalnız `assert_causal`'a ve bu
denetimdeki ek testlere dayanıyor.

### 5.2 Harness gözlemleri

Araştırmacıların bildirdiği gözlemler kodda doğrulandı.

| Gözlem | Etki | Önem |
|---|---|---|
| `combine()` bacakları her bar maliyetsiz olarak sabit ağırlığa dengeliyor. | Çok bacaklı stratejilerde ve al-tut sepetinde küçük, ölçülmemiş fark. Carry'de teminat aktarımı ve tasfiye riski hiç modellenmiyor, bu yüzden Sharpe 7–13 gerçekçi değil. | önemli (carry için) |
| `_trades` yalnız giriş ve çıkış maliyetini işleme yazıyor. | Kesirli ya da topluluk pozisyonlarında işlem düzeyindeki ölçüler (`win_rate`, `total_without_best`) iyimser. Günlük ölçüler doğru. | küçük |
| `total_without_best` bacak düzeyinde hesaplanıyor. | Hedge'li stratejide anlamsız; carry'de dev_train'de −%36 / −%83. Holdout Seviye 1 şart 4 buna dayanıyor. | önemli (holdout için) |
| İşlem sayımı aynı yöndeki kesintisiz dilimlere göre yapılıyor ve `entry_time` ile pencereye atanıyor. | Boyut değişimi işlem sayılmıyor; pencere sınırındaki işlem eksik sayılıyor. 20 işlem şartı düşük cirolu stratejileri (carry) yapısal olarak dışlıyor. | küçük |
| Vadeli 1d verisi fonlamadan önce başlıyor (BTC 2019-09, ETH 2019-11). | Korumasız 1d vadeli stratejide fonlamasız aylar oluşur. Dondurulan 1d vadeli spec'lerin hepsinde koruma var; etkilenen yok. | küçük |
| `assert_causal` fonlamayı kesim barının açılışında kesiyor ve yalnız 3 kesim noktasına bakıyor. | Bar içi fonlamayı meşru kullanan stratejide yanlış alarm verir. Olay bazlı ve walk-forward stratejilerde zayıf bir test: ay başı arındırma hatasını rastgele kesimler genelde yakalamaz. | önemli (yöntem) |
| Deflated Sharpe tarifi aile içi bütün denemelerin Sharpe varyansını kullanıyor; dev_train varyansıyla dev_valid Sharpe'ını karşılaştırıyor. | Kötü keşif denemeleri varyansı şişirip DSR'yi sıfıra itiyor. Ailelerin kendi aralarında karşılaştırılamıyor. Aileler arası toplam deneme sayısı hesaba katılmıyor. | küçük |
| `summarize()['days']` takvim aralığı veriyor (gözlem sayısı − 1). | Önemsiz. | küçük |
| `exposure` ölçüsü "sıfır olmayan pozisyon oranı" demek. | Trend adaylarında %93 görünüyor ama ortalama büyüklük daha küçük; yanıltıcı olabilir. | küçük |
| Eksik barlarda (spot 4h: 9, spot 1h: 28, SOL vadeli: 2) aradaki getiri boşluk öncesi bara yazılıyor. | Hedge'li stratejide yapay oynaklık oluşuyor. | küçük |
| Sıfır ağırlıklı bacaklar (ML spot eğitimi) birleşik indeksi 2017'ye uzatıyor. | dev_train Sharpe ve maruziyet seyreliyor; dev_valid etkilenmiyor. | küçük |

---

## 6. Hiçbir ailenin denemediği, ayrı aramaya değer yaklaşımlar

Defterlerdeki parametre dağılımına göre durum şöyle:

- 5 dakikalık bar neredeyse hiç denenmedi (ortalamaya dönüş, 2 yapılandırma).
- Rotasyon yalnız 1d'de denendi.
- Ortalamaya dönüş yalnız tek varlıkta denendi.
- Mevsimselliğin 122 denemesinin 93'ü ay dönümüydü.

Öneriler:

1. **Çift ya da yayılım ortalamaya dönüşü (piyasa nötr):** ETH/BTC, SOL/ETH ve SOL/BTC log-yayılımı. Kayan OLS ile hedge oranı; 1h/4h z-skoru > 2'de giriş, 0'da çıkış; vadeli iki bacak, fonlama dahil. Rotasyon oranı yalnız trend (momentum) olarak denedi; ortalamaya dönüş ailesi yalnız tek coinle çalıştı.
2. **Saf oynaklık yönetimli maruziyet:** Zamanlama sinyali yok; pozisyon = min(1, σ_hedef / σ_30g). Ayrıca coinler arası ters oynaklık ağırlıklandırması. Trend adaylarının alfası yaklaşık 0 olduğu için doğru kıyas budur. Yalnız sabit 0,5 kıyası yapıldı.
3. **Trend + carry bindirmesi:** Trend topluluğu "kapalı" iken nakit yerine nakit-carry (spot uzun + vadeli kısa) tutulur, "açık" iken spot uzun. Fonlama ailesinin `kaplama` türü fonlama eşiğine dayalıydı; trend topluluğuyla sürülen sürüm denenmedi.
4. **Önceden kaydedilmiş strateji portföyü:** Düşük korelasyonlu zayıf adaylar eşit risk payıyla tek yapılandırma olarak birleştirilir. Örneğin trend_vt, dip alımı ret4h, ML vadeli reg H4 ve formasyon F2; aralarındaki dev_valid korelasyonu −0,05 ile 0,24 arasında. Bu yeni bir yapılandırma sayılmalı ve kuralları dev_valid'e bakmadan yazılmalı.
5. **Perp–spot baz ya da prim endeksi ortalamaya dönüşü (gün içi):** `premiumIndexKlines` / `markPriceKlines` (data.binance.vision) ile primin z-skoru. Yalnız sıçramada carry'ye girilir, prim normale dönünce çıkılır. Fonlama eşiklerinden farklı, daha yüksek frekanslı bir göreli değer işlemi.
6. **Açık pozisyon ve tasfiye verisi:** Binance UM `metrics` dosyaları: OI, uzun/kısa oranları, taker oranı; yaklaşık 2021-12'den itibaren var. Fiyat ↑ + OI ↓ (kısa kapanışı) ile fiyat ↑ + OI ↑ ayrımı, OI sıçraması sonrası dönüş.
7. **Emir akışı dengesizliği:** Veride `taker_buy_base` var ama yalnız ML özelliği olarak kullanıldı. 5m–1h kümülatif delta z-skoruyla devam ya da dönüş kuralları ayrı ve basit bir aile olarak denenebilir.
8. **BTC→ETH/SOL gecikmeli tepki (lead–lag), 5m/15m:** Son 5–15 dakikalık BTC hareketinden sonra ETH/SOL'un yetişme getirisi. Maliyete en duyarlı fikir olduğu için 9. maddeyle birlikte denenmeli.
9. **Maker (limit emir) yürütme duyarlılığı:** Gün içi aileler (ortalamaya dönüş, saat mevsimselliği, 15m kırılım) taker + 2 bp maliyetle öldü. İhtiyatlı bir maker modeliyle yeniden ölçülebilir: emir yalnız bir sonraki bar limit fiyatın ötesine geçerse dolar; vadeli maker ücreti %0,02. Bu bir protokol değişikliği olur ve yeni sürüm olarak yazılmalı.
10. **Makro olay takvimi:** FOMC, ABD TÜFE ve tarım dışı istihdam günleri. Takvim önceden bilinir. Hipotezler: FOMC öncesi 24 saatlik getiri kayması, TÜFE açıklamasından (13:30 UTC) sonra açılış aralığı kırılımı. Mevsimsellik ailesi takvim olarak yalnız ay, gün ve saati denedi.
11. **Geniş ve zamana bağlı (point-in-time) evren ile kesitsel faktörler:** Her ay hacme göre ilk 20–30 USDT-M perp, kaldırılan coinler dahil (hayatta kalan yanlılığı olmadan). Kesitsel momentum, kesitsel fonlama carry'si (en düşük fonlamada uzun, en yüksekte kısa), düşük oynaklık. Üç coinle kesitsel test istatistiksel olarak çok zayıf. Protokol sürüm 2 gerekir.
12. **Meta-etiketleme (meta-labeling):** Kırılım (Donchian 90) ve formasyon kırılım olaylarında birincil sinyal kuralla üretilir. ML yalnız "bu sinyal alınsın mı" ve boyut kararını verir; özellikler oynaklık rejimi, fonlama ve hacim. ML ailesi doğrudan yön tahmini yaptı; olay koşullu filtre denenmedi.

Ayrıca: vadeli takvim yayılımı ya da çeyreklik vadeli baz carry'si (veri setinde yok), ve
trend için ileriye yürüyen bakış süresi uyarlaması da denenmedi.

---

## 7. Finalist seçimi için uyarılar

1. **Görülmemiş dönem dil modeli açısından kör değil.** Araştırmacılar (ve finalist seçecek ajanlar) eğitim verisinde 2024–2026 piyasa seyrine dair genel bilgi taşıyor. Araştırmacıların çoğu bunu sınırlama olarak açıkça yazmış. Adayların neredeyse hepsinin yalnız alım olması, dev_valid'in güçlü yükseliş dönemiyle uyumlu.

   Holdout dönemi (2025-07 – 2026-09) de bu bilgiyle kısmen örtüşebilir. Bu yüzden:
   - Finalistler, sonuç bilgisinden etkilenmeyen mekanik ve önceden yazılmış bir kuralla seçilmeli. Örnek kural: her bağımsız fikir kümesinden dev_train Sharpe'ı en yüksek olan, en fazla 3 küme.
   - Asıl bağımsız kanıt ileriye dönük takip (2026-10 sonrası) olmalı.
2. **Beta ile geçme riski.** Seviye 1 şartları mutlak getiriye bakıyor. Betası yaklaşık 0,45 olan bir trend adayı yükselen piyasada geçer, düşen piyasada kalır. Holdout raporunda al-tut betasına göre arındırılmış getiri ve beta eşleştirilmiş al-tut kıyası da verilmeli (şart değil, raporlama).
3. **Kopyalar.** Trend'in 4 adayı tek aday, kırılımın 2 adayı tek aday sayılmalı (trendle korelasyonu da 0,77). ML'in üç yalnız alım adayı (0,68–0,80) ve formasyon F1/F3 (0,62) aynı fikrin varyantları. Finalistler mümkünse farklı kümelerden seçilmeli. dev_valid günlük getirilerinde korelasyonlar şöyle:

   - ML adayları, formasyon F2 ve dip alımı ret4h, trend ve kırılımla zayıf korelasyonlu (en fazla 0,24).
   - Dip alımı topluluğunun trendle korelasyonu 0,45–0,47.
   - İki dip alımı adayı arasındaki korelasyon 0,54.
4. **Seviye 2 eşiği.** 3 finalistte p < 0,0167 gerekir. dev_valid'de bu eşiğin altında kalan iki aday var:
   - ML vadeli reg H4: p = 0,016, eşiğin hemen altında.
   - ML spot reg H4+btc: p = 0,000. Bu değer 27 işlem ve 11 çarpıklıkla güvenilir değil.

   ML vadeli iki yön adayı 0,024'te. Diğer adaylar 0,07–0,23 aralığında. Holdout dönemi 15 ay; benzer etki büyüklükleriyle Seviye 2'nin geçilmesi beklenmemeli.
5. **`total_without_best` (Seviye 1 şart 4).** Hedge'li ya da çok bacaklı finalistte bu ölçü bacak düzeyinde ve yanıltıcı. Holdout'tan önce portföy düzeyinde tanımlanması önerilir (protokol sürüm notu ile).

---

## 8. Bulgu listesi (önem derecesiyle)

| # | Aile | Bulgu | Önem |
|---|---|---|---|
| 1 | genel | Holdout erişimi, 5'ten fazla dev_valid bakışı, ileri bakış ya da yeniden üretim uyumsuzluğu **yok**. | — |
| 2 | genel (protokol) | Görülmemiş dönem ve dev_valid, dil modeli araştırmacıların eğitim bilgisiyle örtüşüyor. Adayların neredeyse hepsi yalnız alım. Holdout bu açıdan kör değil. | önemli |
| 3 | genel (protokol) | Aday şartları beta ile geçilebiliyor. Trend adaylarının alfası yaklaşık 0. Hiçbir adayın alfası çoklu deneme düzeltmesinden sonra anlamlı değil. Bütün adaylarda DSR < 0,95. | önemli |
| 4 | genel (protokol) | Aileler arası 33 dev_valid bakışı yapıldı ve yaklaşık 1.929 yapılandırma denendi. Finalistler dev_valid'e göre seçilirse seçim yanlılığı oluşur. Aile içi DSR toplam denemeyi saymıyor. | önemli |
| 5 | genel (protokol) | BTC/ETH/SOL evreni sonradan seçilmiş (SOL'da hayatta kalan yanlılığı). Birçok adayın kârı SOL bacağından geliyor. | önemli |
| 6 | genel (harness) | `total_without_best` bacak düzeyinde hesaplanıyor; hedge'li ya da çok bacaklı finalistte Seviye 1 şart 4 yanıltıcı olur. | önemli |
| 7 | genel (harness) | `assert_causal` yalnız 3 kesim noktasına bakıyor; walk-forward ve olay bazlı stratejiler için zayıf. Bu denetimde ek testlerle telafi edildi. | önemli |
| 8 | fonlama_carry | Carry Sharpe'ı (7–13) araç varsayımlarıyla şişik: maliyetsiz yeniden dengeleme, teminat ve tasfiye riski yok, nakit faizi yok. `mekanik_kontrol.py` aramadan önce dev_valid'i kapsayan toplam fonlama tutarını yazdırdı. | küçük |
| 9 | mevsimsellik | 660 betimleyici keşif hücresi defter dışında kaldı. Açıklanmış; aile aday üretmedi. | küçük |
| 10 | rotasyon | `NOTLAR.md` yok (dondurma zamanı yalnız `dogrulama.py` zaman damgasıyla doğrulanabiliyor). Vadeli al-tut değeri hesaplanmadan 0 diye raporlanmış. | küçük |
| 11 | ortalamaya_donus | `NOTLAR.md` yok. `yeniden_uretim.py` dev_valid'i aynı yapılandırmalarla `record=False` olarak yeniden hesapladı (yeni bilgi eklemiyor). | küçük |
| 12 | makine_ogrenmesi | Son çalışma commit edilmemiş. `tani_oynaklik.log`'un betiği yok. Spot+btc adayı 27 işlem ve %0,9 maruziyetle kırılgan; DSR'si çarpıklıkla şişiyor. | küçük |
| 13 | trend, kirilim | Trend'in 4 adayı (korelasyon 0,99–1,00) ve kırılımın 2 adayı (0,99) kopya. Duman testleri bütün dev dönemi için pozisyon oranlarını yazdırdı (performans bilgisi yok). | küçük |
| 14 | formasyon | Ek bulgu yok. 575 olay bazlı kesimde fark çıkmadı. | — |
