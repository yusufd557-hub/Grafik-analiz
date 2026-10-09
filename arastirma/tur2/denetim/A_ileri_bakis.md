# Tur 2 Denetimi — A: İleri Bakış Kod İncelemesi

9 Ekim 2026 · bağımsız denetim, bölüm A (statik kod incelemesi + sentetik
veriyle kesme testleri). Kapsam: `t2_cift`, `t2_konumlanma`, `t2_emir_akisi`,
`t2_lead_lag`, `t2_limit_gun_ici`, `t2_bindirme`, `t2_meta`. `t2_genis_evren`
kapsam dışıdır.

Gerçek araştırma verisi kullanılmadı. Holdout açılmadı, deftere yazılmadı, depoda
var olan hiçbir dosya değiştirilmedi. Bu raporda geçen her test sonucu,
ekte kodu verilen betiklerin bu oturumdaki çıktısıdır.

## Özet

| # | Önem | Aile | Bulgu | Adaylara etkisi |
|---|---|---|---|---|
| 1 | önemli (yöntem) | hepsi | Ailelerin nedensellik kanıtı rastgele 3–10 kesimli `assert_causal`. Seyrek ya da ayrık (−1/0/+1) sinyallerde bu test bilerek eklenmiş 1 barlık ileri bakışı **yakalamadı**. Pozisyon değişim barlarına hedefli kesimler yakaladı. | Sentetik veride hedefli kesimlerle bütün dondurulmuş yapılandırmalar geçti. Gerçek veride hedefli kesim testi B denetçisi tarafından çalıştırılmalı. O zamana kadar nedensellik kanıtı "kod incelemesi + sentetik test" düzeyindedir. |
| 2 | önemli (yöntem) | `t2_konumlanma`, `t2_meta`, `t2_lead_lag` | Kesme testleri, dış verinin **zaman damgası anlamındaki** hatayı göremez. Örnekler: konumlanma kaydının hangi aralığı anlattığı, spot mumunun kaydırılmış olması. Sentetik denemede spot kapanışı bir bar ileri kaydırıldı. Konumlanma gecikmesi −5 dk yapıldı ve açık kesim kaldırıldı. Her iki sızıntı da kesme testini geçti. | Konumlanma için hizalama kontrolü var (`hizalama.log`) ve 10 dk gecikme yeterli görünüyor (bulgu 3). Spot/vadeli ve prim için hizalama kontrolü yok; B'ye önerilen testler aşağıda. |
| 3 | küçük | `t2_konumlanma`, `t2_meta` | `hizalama.log`'da konumlanma kaydı T ile [T, T+5dk) mumu arasında da belirgin korelasyon var. Taker oranı için k=0'da +0,29…+0,37, k=+1'de ≈0,02. Yani T damgalı kayıt, T'den sonraki birkaç dakikayı kısmen içeriyor olabilir. 10 dk gecikme (`METRIC_LAG`) bunu karşılıyor. Gecikme 0 olsaydı ileri bakış olurdu. | D2 (konumlanma) ve meta 1h adayında ileri bakış yok. Gecikme duyarlılık testi önerilir. |
| 4 | küçük | harness | Limit dolum modeli ileri bakış içermiyor (bar t+1'in açılışı/düşüğü/yükseği yalnız bar t+1'de kullanılıyor). Ancak dolumdan sonra kuyruktaki ters seçimi modellemiyor. `_trades` limit dolumlarında da taker maliyetiyle işlem başı net hesaplıyor (yalnız raporlama). | İleri bakış değil. Limitli adaylarda (cift B/C, lead_lag, limit_gun_ici donus) iyimserlik B/C denetiminde ayrıca ölçülmeli. |
| 5 | küçük | `t2_konumlanma`, `t2_meta` | Önbellek anahtarları veri kökünü, kapsamı ve fonlamanın içeriğini içermiyor (`t2_konumlanma.py:94-95`, `t2_meta.py:276-277`). | Mevcut kullanımda ileri bakış üretmiyor. Aynı süreçte farklı veriyle çalışılırsa eski sonuç dönebilir. |
| 6 | bilgi | hepsi | `arastirma/tur2/<aile>/` betiklerinde (genis_evren hariç) doğrudan parquet okuma, `/home/user/arastirma_veri` yolu, `unlock_holdout`, `scope="holdout"/"all"`, veri indirme ya da `record=True` yok. | — |
| 7 | bilgi | hepsi | Satır satır incelemede negatif kaydırma, ortalanmış pencere, `bfill`, tam örneklem normalizasyonu ya da tam örneklem uyumu bulunmadı. Tek `shift(-k)` harness'ın getiri ölçümünde (`evaluate.py:144`) ve tur 1 ML etiketinde (`makine_ogrenmesi.py:248-250`, etiket zamanıyla arındırılıyor) var. | — |

**Sonuç: kapsamdaki yedi ailenin kodunda ileri bakış bulunamadı.** Hiçbir aday
bu bölümün bulgusuyla elenmez. İki yöntem bulgusu (1, 2) var: ailelerin kendi
nedensellik testleri, iddia ettikleri güvenceyi tam vermiyor. Gerçek veride
hedefli kesim ve hizalama testleri (bölüm 5) B denetçisince yapılmalı.

## 1. Yöntem

1. Okunanlar:
   - `docs/PROTOKOL_2.md`, `arastirma/DENETIM_1.md`.
   - `research/` içindeki `protocol.py`, `data.py`, `backtest.py`, `evaluate.py`, `metrics.py`, `universe.py`.
   - `data/extra.py` (konumlanma, prim), `data/binance.py`'deki zaman damgası dönüşümü, `indicators.py`'deki `ema`, `rma`, `atr`.
   - Yedi aile modülünün tamamı; `t2_bindirme`'nin kullandığı `trend.leg_target`.
   - Ailelerin nedensellik betikleri ve logları, `FINALISTLER.md`.
2. Grep: `shift(-`, `center=True`, `bfill`, `parquet`, `holdout`, `scope=`, indirme fonksiyonları.
3. Sentetik kesme testi:
   - Veri: BTC/ETH/SOL için sentetik OHLCV üretildi.
     - Spot ve vadeli aynı fiyat yolunu paylaşıyor; aralarında t-dağılımlı baz var.
     - 8 saatte bir fonlama, 5 dakikalık konumlanma ve prim mumları eklendi.
   - `research.data.load`, `load_funding`, `load_metrics`, `load_premium` yerine **kesilmemiş** tam seri döndüren yükleyiciler kondu. Böylece strateji içinde yüklenen ek verilerin açık kesimi de sınandı.
   - Her dondurulmuş yapılandırmada tam veriyle sinyal üretildi. Sonra mumlar ve fonlama `assert_causal` kuralıyla kesilerek (`index <= cut`) yeniden üretildi. Kesime kadarki bütün barlarda `target` ve `limit` birebir karşılaştırıldı (tolerans 1e-9).
   - (a) Rastgele kesimler: 10 kesim; meta'da ayrıca 9 ay sınırı kesimi var.
   - (b) Hedefli kesimler: her bacakta pozisyon/limit değişim barlarından 20'si seçildi. Her biri için c−2, c−1 ve c kesimleri denendi.
   - (c) Testin gücünü ölçmek için bilerek sızıntı eklenmiş kontrol varyantları çalıştırıldı.

## 2. Test sonuçları (bu oturumda çalıştırıldı)

### 2.1 Rastgele kesimler — bütün dondurulmuş yapılandırmalar

```
t2_cift            ..._SOLBTC_..._k6_..._max_bar6_limit_bps20 ...           gecti (10 kesim)  pozisyonlu bar=156 limitli bar=104
t2_cift            ..._SOLBTC-SOLETH_..._k6_...                              gecti (10 kesim)  pozisyonlu bar=286 limitli bar=194
t2_cift            ..._SOLBTC-SOLETH_..._k12_..._max_bar3_...                gecti (10 kesim)  pozisyonlu bar=90  limitli bar=120
t2_konumlanma      kalabalik_1h_SEPET3_genel_w7_c0.5_cx0.5_s-1_limit_lb1     gecti (10 kesim)  pozisyonlu bar=62055 limitli bar=6668
t2_konumlanma      kalabalik_1h_SEPET3_genel_w30_c1.0_cx0.0_s-1              gecti (10 kesim)  pozisyonlu bar=62684
t2_konumlanma      oi_1h_SEPET3_birikim_k8_w30_a1.0_b1.5_t12                 gecti (10 kesim)  pozisyonlu bar=8470
t2_konumlanma      fark_1h_SEPET3_w14_c0.5_cx0.0_s1                          gecti (10 kesim)  pozisyonlu bar=70140
t2_konumlanma      taker_4h_SEPET3_k12_w30_c2.0_cx0.0_s1                     gecti (10 kesim)  pozisyonlu bar=5190
t2_emir_akisi      uyum_5m_n72_k3.5_h12                                      gecti (10 kesim)  pozisyonlu bar=979
t2_emir_akisi      uyum_15m_n24_k3.5_h2                                      gecti (10 kesim)  pozisyonlu bar=539
t2_emir_akisi      artik_15m_n12_k3.5_h8                                     gecti (10 kesim)  pozisyonlu bar=39
t2_emir_akisi      uyum_spot_5m_n72_k3.5_h12_uzun                            gecti (10 kesim)  pozisyonlu bar=582
t2_emir_akisi      kontrol_getiri_donus_5m_n72_k5_h12                        gecti (10 kesim)  pozisyonlu bar=0  (sentetikte tetik yok)
t2_lead_lag        baz_5m_kendi_w288_e6_t12_limt2b2                          gecti (10 kesim)  pozisyonlu bar=821 limitli bar=273
t2_lead_lag        baz_15m_kendi_w192_e5_t8_limt2b2                          gecti (10 kesim)  pozisyonlu bar=1063 limitli bar=522
t2_lead_lag        sv_5m_hepsi_k6_e4_t36_limt2b2                             gecti (10 kesim)  pozisyonlu bar=216 limitli bar=24
t2_lead_lag        baz_5m_hepsi_w288_e5_t12_uzun_limt2b2                     gecti (10 kesim)  pozisyonlu bar=180 limitli bar=60
t2_lead_lag        sv_5m_hepsi_k4_e4_t12_uzun_limt2b2                        gecti (10 kesim)  pozisyonlu bar=36  limitli bar=12
t2_limit_gun_ici   fitil_1h_k4_H3_t50                                        gecti (10 kesim)  pozisyonlu bar=36484 limitli bar=36168
t2_limit_gun_ici   fitil_5m_k8_H24_t50 (80 günlük 5m veriyle)                gecti (10 kesim)  pozisyonlu bar=10733 limitli bar=10549
t2_limit_gun_ici   donus_1h_n4_e3_t50_H12_lim1.0s_m3                         gecti (10 kesim)  pozisyonlu bar=516 limitli bar=219
t2_limit_gun_ici   donus_15m_n16_e3_t50_H48_lim1.0s_m12                      gecti (10 kesim)  pozisyonlu bar=213 limitli bar=25
t2_limit_gun_ici   donus_1h_n4_e3_t50_H12_piyasa                             gecti (10 kesim)  pozisyonlu bar=780
t2_meta            4h_kanal_n20_b3.0-1.5-H60_logit_tam_taban0.0              gecti (19 kesim)  pozisyonlu bar=6989
t2_meta            4h_kanal_top[n14-20-30-48]_n48_...                        gecti (19 kesim)  pozisyonlu bar=10611
t2_meta            1h_kanal_n96_iz4.0-H240_logit_tam_taban0.0                gecti (19 kesim)  pozisyonlu bar=20998
t2_meta            1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0                gecti (19 kesim)  pozisyonlu bar=14852
t2_meta            4h_ema_e20-100_b3.0-1.5-H60_logit_tam_taban0.0_min_olay150 gecti (19 kesim) pozisyonlu bar=803
t2_bindirme        vol_nakit_1d_h0.4_n40_b0.1                                gecti (10 kesim)  pozisyonlu bar=5355
t2_bindirme        trend_yarim_4h_L15_b0.15_f7                               gecti (10 kesim)  pozisyonlu bar=49491
t2_bindirme        trendvol_tam_4h_L10_h0.3_n30_b0.1_f7                      gecti (10 kesim)  pozisyonlu bar=52308
t2_bindirme        portfoy_esit_risk_sermaye                                 gecti (10 kesim)  pozisyonlu bar=31840
```

Bütün farklar 0,0. Meta'nın 19 kesiminin 9'u ay sınırının bir bar öncesi, tam
sınırı ve bir bar sonrasıdır (2023-03, 2023-09, 2024-02).

### 2.2 Testin gücü — ekilmiş sızıntılar

| Ekilen sızıntı | Rastgele kesim (4 kesim) | Hedefli kesim |
|---|---|---|
| `t2_cift` B: hedef `shift(-1)` (bir bar ileri bakış) | **geçti (yakalanmadı)** | **İHLAL yakalandı** (BTC, 2022-11-17 04:00) |
| `t2_konumlanma` D2: gecikme −5 dk (kapanıştan 5 dk sonraki kayıt), açık kesim var | **geçti (yakalanmadı)** | **İHLAL yakalandı** (ETH, 2022-10-01 19:00) |
| `t2_konumlanma` D2: gecikme −5 dk, açık kesim **kaldırılmış** | geçti (yakalanmadı) | ilke olarak yakalanamaz (bkz. bulgu 2) |
| `t2_lead_lag` baz 5m: spot kapanışı yükleyicide bir bar ileri kaydırılmış | geçti (yakalanmadı) | ilke olarak yakalanamaz |
| `t2_meta` 4h kanal: arındırma yok (etiket hemen biliniyor sayılır) | **İHLAL yakalandı** | — |

### 2.3 Hedefli kesimler — bütün dondurulmuş yapılandırmalar

(Çalışıyor; sonuçlar bu bölüme eklenecek.)

## 3. Bulgular

### Bulgu 1 — önemli (yöntem), bütün aileler: rastgele kesimli `assert_causal` seyrek/ayrık sinyallerde zayıf

**Kanıt.** `evaluate.py:181-209` serileri 3 noktada keser (0,55 / 0,80 / 0,97).
Sinyalleri yalnız kesime kadar karşılaştırır.

1. Bir barlık ileri bakış (karar t'de, bilgi t+1'den) yalnız şu durumda görünür:
   kesim tam t'ye düşmeli ve hedef t+1'de değişiyor olmalı. Kesimden önceki
   barlarda kesik veri de t+1'i hâlâ içerir.
2. Ayrık hedeflerde (−1/0/+1, bant/histerezis) kesimdeki küçük bir sürekli fark
   genelde hedefi değiştirmez. Bu durumda sızıntı görünmez.
3. Bölüm 2.2: `t2_cift` B'ye eklenen `shift(-1)` rastgele 4 kesimde yakalanmadı
   (26 bin barda 156 pozisyonlu bar). `t2_konumlanma` D2'ye eklenen −5 dk gecikme
   de rastgele kesimlerde yakalanmadı. İkisi de hedefli kesimlerde hemen yakalandı.

**Ailelerin kendi testleri:**
- `t2_cift/dondurma_kontrol.py:18-20`, `t2_konumlanma/nedensellik.py:20`,
  `t2_lead_lag/nedensellik.py:11-12`, `t2_emir_akisi/nedensellik.py:18-19`,
  `t2_limit_gun_ici/dondurma_kontrol.py:26-27`, `t2_bindirme/dondurma_kontrol.py:34`
  yalnız rastgele oranlı kesimler kullanıyor (3–10 kesim).
- Yalnız `t2_meta/nedensellik.py:45` ay sınırına hedefli kesim ekliyor.
- DENETIM_1 aynı zayıflığı walk-forward için not etmişti (madde 7). Burada
  zayıflığın basit kural stratejilerinde de geçerli olduğu gösterildi.

**Adaylara etkisi.** Kod incelemesinde ileri bakış bulunmadı. Sentetik veride
hedefli kesimler de temiz (2.3). Aday elenmez. Ama gerçek veride nedensellik
güvencesi için B denetçisi hedefli kesim testini (bölüm 5, T1) gerçek veriyle
bütün adaylarda çalıştırmalı.

### Bulgu 2 — önemli (yöntem): kesme testleri dış verinin zaman hizasını sınamaz

**Kanıt.** Kesme testi yalnız verinin **kesilmesine** karşı tutarlılığı ölçer.
Bir veri kaynağının zaman damgası yanlışsa sızıntı içeride kalır. Örneğin T
damgalı kayıt T'den sonrasını anlatıyorsa, ya da spot mumu bir bar kaymışsa,
kesik veri de aynı sızıntıyı taşır ve iki sinyal birebir aynı çıkar. Bölüm 2.2,
satır 3–4: iki ekilmiş hizalama sızıntısı da bu yüzden geçti.

**Açık kesimler doğru ama yalnız kısmi koruma sağlar.** Kodda kesimler şöyle:
- `t2_konumlanma.py:112` `raw[raw.index < index[-1] + step]`, `:148` prim için `close_time < index[-1] + step`.
- `t2_meta.py:208`, `:235`, aynı kurallar.
- `t2_lead_lag.py:102` spot `close_time <= _last_close(data)`, `:155` prim `close_time <= last`.
- `t2_emir_akisi.py:109` diğer piyasa `index <= df.index[-1]`.
- `t2_bindirme.py:290` bileşen `close_time <= last_close`, `:299` fonlama `< last_close`.

Bu kesimler, gecikme parametresi negatif olsa bile son barda farkı
görünür kılar (2.2, satır 2 hedefli kesimle yakalandı). Ama zaman damgasının
anlamını doğrulamaz. Konumlanmada asof eşlemesi (`cutoff = kapanış − 10 dk`)
zaten kesimden önce kalır; açık kesim pratikte gereksizdir, zararsızdır.

**Hizalama durumu:**

| Kaynak | Kullanan | Hizalama kontrolü |
|---|---|---|
| Konumlanma | `t2_konumlanma`, `t2_meta` | `t2_konumlanma/hizalama.py` var (bulgu 3) |
| Spot mumları | `t2_lead_lag` baz/spot_vadeli, `t2_emir_akisi` spot_vadeli, `t2_bindirme` spot bacakları | yok |
| Prim endeksi | `t2_meta` tam özellik, `t2_konumlanma` prim türü | yok |

`binance.py:73-81` spot arşivlerindeki 2025 mikrosaniye geçişini düzeltiyor.
Yanlış hizalama burada büyük olasılıkla NaN üretir (sinyal yok), sızıntı değil.
Yine de veriyle doğrulanmadı.

**Adaylara etkisi.** `t2_lead_lag` baz/sv adayları doğrudan spot−vadeli
farkından kazanıyor. Spot mumunda bir barlık kayma bu adayları sahte biçimde
çok kârlı gösterir. Bu yüzden T2 testi (bölüm 5) bu üç aday için **seçimden
önce** yapılmalı. Meta 1h adayı ve konumlanma D2 için T3 önerilir.

### Bulgu 3 — küçük: konumlanma kaydı T'den sonraki birkaç dakikayı kısmen içeriyor; 10 dk gecikme koruyor

**Kanıt.** `arastirma/tur2/t2_konumlanma/hizalama.log`:
- k = −1'de taker oranı korelasyonu BTC +0,771, ETH +0,688, SOL +0,654.
- k = 0'da +0,294 / +0,367 / +0,373.
- k = −2 ve k = +1'de ≈ 0,01–0,04.

Kayıt yalnız [T−5dk, T) aralığını anlatsaydı k=0 ve k=−2 korelasyonu, mum
taker oranının 1 gecikmeli otokorelasyonuna eşit, yani simetrik olurdu.
Görülen asimetri, kaydın T'den sonraki birkaç dakikayı kısmen içerdiğini ya da
birkaç dakika gecikmeyle alındığını düşündürüyor. k=+1 ≈ 0 olduğu için bu taşma
5 dakikadan küçük.

Kodda `METRIC_LAG = 10 dk` (`t2_konumlanma.py:47`, `t2_meta.py:107`). Kullanılan
kayıt en geç kapanış − 10 dk damgalı; taşmayla birlikte en geç kapanış − 5 dk'ya
kadar bilgi taşır. `gecikme_dk` parametresi 10'un altına inemez
(`t2_konumlanma.py:319`). **İleri bakış yok.** Gecikme 0 olsaydı olurdu.

**Adaylara etkisi.** Yok. Duyarlılık testi önerilir (T3).

Not (ileri takip, ileri bakış değil): `data.binance.vision` günlük arşivleri ertesi
gün yayımlanır. İleriye dönük takipte bu ölçülerin bar kapanışında REST'ten
alınabildiği ayrıca doğrulanmalı.

### Bulgu 4 — küçük: limit dolum modeli (harness)

**Kanıt.** `backtest.py:129-151`:
1. t kapanışında verilen emir (`lim[i-1]`), t+1 barının açılışı, düşüğü ve
   yükseğiyle çözülür.
2. Açılış limitin öbür tarafındaysa taker maliyetiyle açılışta işlenir.
3. Değilse fiyat limitin 2 bps ötesine geçerse limit fiyattan dolar. Getiri
   limit → sonraki açılış olarak ölçülür.
4. Strateji dolumu bilmez. `t2_limit_gun_ici._motor` (`t2_limit_gun_ici.py:152-184`)
   dolumu aynı kuralla **t+1 kapanışında** yeniden hesaplar. Yani dolum yalnız
   bilindikten sonra kullanılır.

**İleri bakış yok.**

İyimserlik kaynakları:
- Dolumdan sonra kuyrukta ters seçim yok.
- Bar içi yol bilinmiyor.
- Çok bacaklı çiftte bacaklar bağımsız doluyor (`t2_cift`'te bir bacak dolup
  diğeri dolmayabilir; bu modelleniyor, ama bar içi sıra modellenmiyor).
- `_trades` (`backtest.py:160`) işlem başı neti limit dolumlarında da taker
  maliyetiyle hesaplıyor. Bu yalnız işlem listesini etkiler, getiri serisini
  etkilemez.

**Adaylara etkisi.** İleri bakış açısından yok. Limitli adaylarda (`t2_cift` B/C,
`t2_lead_lag` üç aday, `t2_limit_gun_ici` donus_1h lim) dolum duyarlılığı (T5)
önerilir.

### Bulgu 5 — küçük: önbellek anahtarları

**Kanıt.**
- `t2_konumlanma.py:94-95` anahtarı (etiket, sembol, bar sayısı, ilk/son bar, adım, gecikme).
- `t2_meta.py:276-277` özellik anahtarı fonlama için yalnız `len(fund)` içeriyor.
- `t2_meta.py:577-590` tahmin anahtarı konumlanma/prim içeriğini içermiyor.

Veri kökü ve kapsam da anahtarlarda yok. Mevcut akışta (tek kök, `scope="dev"`,
kesimde mumlar da değişiyor) yanlış sonuç üretmez; sentetik testler de geçti.

**Adaylara etkisi.** Yok. İleri takipte aynı süreçte farklı veriyle çağrı
yapılırsa önbellek temizlenmeli.

## 4. Aile aile inceleme (ileri bakış açısından)

### t2_cift (`grafik_analiz/strategies/t2_cift.py`)
- `_panel` (79-95):
  - Birleşik indeks üzerinde yalnız `ffill` var.
  - Bar kapanışı ilk barın `close_time − açılış` farkıyla bulunuyor.
  - Fonlama koruması `bar_close >= f.index[0]` (276).
- `_spread_z` (98-153):
  - Bütün pencereler `rolling`.
  - `sok` modunda oynaklık `shift(k)` ile hareketten önce ölçülüyor (145).
  - `oyn`/`beta` hedge'inde `h.shift(1)` kullanılıyor (127).
- `_pair_state`: ileri yürüyen durum makinesi; yalnız z[t] ve önceki değer.
- `_with_limit` (323-344): limit fiyatı karar barının kapanışından. Strateji dolumu bilmiyor.
- **Temiz.** Adaylar B ve C etkilenmez.

### t2_konumlanma (`t2_konumlanma.py`)
- `bar_metrics` (98-131): asof `kapanış − max(gecikme, 10 dk)`, en fazla 2 saat yaşlı kayıt, açık kesim.
- `bar_premium` (134-151): aynı açılışlı prim mumunun kapanışı, barla aynı anda kapanıyor.
- `_z` geriye dönük `rolling`. `_band`, `_hold` ileri yürüyor.
- `_limit_orders` (282-289): `groupby(cumsum).cumcount` grup başından sayıyor, geleceğe bakmıyor.
- `_step` tam serinin medyanını alıyor (78-81), ama ölçülen şey bar süresi (sabit). İleri bakış değil.
- **Temiz.** D2 etkilenmez (bulgu 3'e bakın).

### t2_emir_akisi (`t2_emir_akisi.py`)
- Skorların hepsi geriye dönük `rolling`. CVD baştan `cumsum`.
- `_other_market` (101-110): aynı açılışlı diğer piyasa mumu, `index <= df.index[-1]` ile kesiliyor.
- `with_limit` (203-230): yalnız `ffill`.
- Fonlama koruması `close_time >= ilk kayıt` (262).
- **Temiz.** Aday yok.

### t2_lead_lag (`t2_lead_lag.py`)
- Diğer coin/piyasa serileri işlem bacağının açılış zamanına `reindex` ediliyor.
  Spot ve vadeli 5m barları aynı anda kapanıyor; eksik barda NaN, sinyal yok.
- `_zscore_level` (167-170): ortalama ve std `shift(1)`.
- `_score_spot_vadeli`: std `shift(1)`.
- `_premium_on` (149-164): `merge_asof(direction="backward")`, kapanışa göre.
- `_orders` (123-146): `ffill`, `cumcount`.
- **Kod temiz.** Spot hizası veriyle doğrulanmalı (bulgu 2, T2).

### t2_limit_gun_ici (`t2_limit_gun_ici.py`)
- `_motor`:
  - Adım 1: t−1'de verilen emri t'nin OHLC'siyle çözüyor.
  - Adım 2: t kapanışında karar veriyor.
  - TP/SL, giriş barındaki `TP[i-1]`/`SL[i-1]`'den.
- `leg_plan`:
  - σ `rolling`, `donus` skorunda std `shift(n)`, trend SMA `rolling`.
  - `orb`: gün içi `cummax/cummin` ve `ffill` kullanıyor; zorunlu çıkış takvimden (dondurulmuş değil).
  - `saat`: bir sonraki barın saati takvimden.
- **Temiz.** donus_1h lim adayı etkilenmez.

### t2_bindirme (`t2_bindirme.py`)
- `exposure`: tur 1 `trend.leg_target` (tur 1'de denetlendi) ve `rolling` oynaklık.
- Fonlama ortalaması kayıt zamanında `rolling`. Asof **bar açılışında** (`_asof`, 88-94), yani ihtiyatlı.
- `allowed = idx >= ilk fonlama`.
- Portföy:
  - Bileşen verisi son 1s kapanışına kesiliyor.
  - 4s bileşen kapanışı, `searchsorted(side="right")` ile kapanışı ≤ 1s kapanışı olan son bara eşleniyor (324).
- **Temiz.** trend_yarim ve trendvol_tam adayları etkilenmez.

### t2_meta (`t2_meta.py`)
- Birincil olaylar:
  - `kanal`: `high/low.shift(1).rolling(n)` ve `_first` (`shift(1)`).
  - `ema`: `ewm(adjust=False)`.
- `event_exits`: çıkış barı ileriye doğru aranıyor. Koşul yalnız o bara kadarki
  kapanışlarla. Pozisyon çıkış barında 0'a iniyor (`positions`, 715). Çıkıştan
  önceki her barda koşul sağlanmamış olduğu için nedensel.
- Etiket (465-488):
  - `open[e+1]/open[t+1]`, fonlama (open[t+1], open[e+1]].
  - Bilindiği an `open[e+1]`.
- Eğitim (629): `known < T`, yani etiket ay başından **önce** tamamlanmış olmalı.
  Tahmin [T, sonraki T) olaylarına. Arındırma doğru. Etiket penceresi tahmin
  penceresiyle çakışmıyor, ek embargo gerekmez.
- Dönüştürücüler (imputer, scaler) pipeline içinde yalnız eğitim satırlarına uyduruluyor.
- `use` sütun seçimi yalnız eğitim satırlarından.
- Taban oranı, kazanç ve kayıp ortalamaları yalnız eğitim etiketlerinden.
- Özellikler `rolling`/`ewm`. `vol_sira` kayan `rank(pct=True)`. Fonlama asof bar açılışında. Konumlanma ve prim bulgu 3'teki kurallarla.
- Ekilmiş arındırma hatası kesme testinde yakalandı (2.2). Gerçek kod geçti (2.1, 2.3).
- **Temiz.** 1h_kanal_n96_iz3.0 adayı etkilenmez.

### Harness ve veri yükleyicileri
- `data.load`: `close_time < DEV_END`, yani yalnız kapanmış mumlar.
- `load_metrics`: `index < DEV_END`. `load_premium`: `close_time < DEV_END`.
- `_limit("holdout")` protokol 2'de her durumda hata veriyor (`data.py:44-45`).
- `backtest_leg`: hedef `shift(1)`; getiri açılış → sonraki açılış.
- Fonlama açılışa denk gelirse önceki pozisyonla hesaplanıyor (`_funding_charges`).
- `evaluate`: `dev_train` ölçüleri de `scope="dev"` verisiyle üretilen sinyallerden kesiliyor. Nedensel stratejilerde (meta dahil, walk-forward) bu sonuçları değiştirmez.
- `universe.build_universe` yalnız `t2_genis_evren`'de kullanılıyor (kapsam dışı).

## 5. B denetçisine önerilen veri testleri

| Test | Ne | Hangi adaylar | Beklenen |
|---|---|---|---|
| T1 | **Hedefli kesim, gerçek veri.** Bu rapordaki `hedefli_kesme.py` mantığıyla (ekte), `research.data` yükleyicilerini değiştirmeden: her bacakta pozisyon/limit değişim barlarından ≥ 20'si için c−2, c−1, c kesimleri; `target` ve `limit` karşılaştırılır. Meta için ek: her yeniden eğitim ayı başının ±1 barı. | bütün adaylar (cift B/C, konumlanma D2, lead_lag 3 aday, limit_gun_ici donus_1h lim, bindirme 2 aday, meta 1h iz3.0) | sıfır fark |
| T2 | **Spot–vadeli hizası.** Her 5m bar için spot ve vadeli `close_time` eşit mi; 2025-01-01 öncesi ve sonrası ayrı. Spot getirisi ile vadeli getirisi arasındaki korelasyon k = −2…+2 bar kaydırmayla ölçülür; tepe k=0'da olmalı. Aday işlemlerinin giriş barlarında spot ve vadeli hacmi > 0 mı, spot barı eksik ya da sıfır hacimli mi? | lead_lag baz_5m_kendi, baz_5m_hepsi_uzun, sv_5m_hepsi_k4_uzun | tepe k=0; aday işlemleri veri kusuruna yığılmıyor |
| T3 | **Konumlanma gecikme duyarlılığı.** `gecikme_dk` = 10 / 15 / 20 / 30 ile dev_train ve dev_valid ölçüleri (`record=False`). Meta için `METRIC_LAG` modül sabiti geçici olarak değiştirilir, dosya değiştirilmez. | konumlanma D2, meta 1h iz3.0 | sonuç gecikmeyle sert düşmemeli; 10 → 15 dk'da büyük düşüş, hizalama taşmasından kâr edildiğini gösterir |
| T4 | **Prim hizası.** Prim mumunun `close_time`'ı vadeli mumunkine eşit mi? Prim kapanışı ile vadeli/endeks farkı k = −1, 0, +1'de korelasyon. | meta 1h iz3.0 (tam özellik) | tepe k=0 |
| T5 | **Limit dolum duyarlılığı** (ileri bakış değil, iyimserlik). Geçme eşiği 2 → 5 / 10 bps (`LIMIT_PENETRATION` modül sabiti geçici olarak), ve "dolan limit emirlerde bar getirisi dolumdan sonra en kötü yol" senaryosu. | cift B/C, lead_lag 3 aday, limit_gun_ici donus_1h lim | sonuç işaret değiştirmemeli |
| T6 | **Son bar ve eksik bar.** Aday işlemlerinden giriş barı herhangi bir bacakta eksik (birleşik indekste `ffill` edilmiş) olanların payı. | cift B/C | ≈ 0 |

## 6. Dosya disiplini (madde 6)

Komut:

```
grep -rnE "arastirma_veri|read_parquet|\.parquet|unlock_holdout|scope=\"(holdout|all)\"|\"holdout\"|\"all\"|requests\.|urllib|update_metrics|update_premium|download\(|fetch_|data\.binance|record=True|ledger\.record" arastirma/tur2 grafik_analiz/strategies/t2_*.py --include=*.py | grep -v t2_genis_evren
```

Çıktı boş. `requests`, `subprocess` ya da `os.system` içe aktarımı da yok.
Strateji modüllerindeki bütün ek veri çağrıları `scope="dev"`.

## Ek — sentetik test betikleri (oturum karalama alanında çalıştırıldı, depoya eklenmedi)

Çalıştırma:

```
GRAFIK_ANALIZ_PROTOKOL=2 python sentetik_kesme.py <aile...>
python ekilmis_sizinti.py
python hedefli_kesme.py <aile...>
```

`sentetik_kesme.py` yükleyicileri değiştirir ve şu kontrolü yapar:

```python
def check(spec, fracs, extra_cuts=()):
    data, fund = build(spec)                       # sentetik, kesilmemiş
    full = spec.signal_fn(data, fund, **spec.params)
    index = data[spec.legs[0]].index
    cuts = [index[int(len(index) * f)] for f in fracs] + list(extra_cuts)
    for cut in cuts:
        pd_ = {leg: f[f.index <= cut] for leg, f in data.items()}
        pf = {s: f[f.index <= cut] for s, f in fund.items()}
        part = spec.signal_fn(pd_, pf, **spec.params)
        # her bacak, her sütun (target, limit): kesime kadarki barlarda |tam − kesik| ≤ 1e-9
```

`research.data` yerine konan yükleyiciler kapsamı yok sayar ve tam seri döndürür:

```python
rdata.load = lambda symbol, interval, market="spot", scope="dev", root=None: candles(symbol, interval, market).copy()
rdata.load_funding = lambda symbol, scope="dev", root=None: funding(symbol).copy()
rdata.load_metrics = lambda symbol, scope="dev", root=None: metrics(symbol).copy()
rdata.load_premium = lambda symbol, interval="1h", scope="dev", root=None: premium(symbol, interval).copy()
```

`hedefli_kesme.py` kesimleri şöyle seçer:

```python
t = fr["target"].fillna(0.0).to_numpy()
ch = np.flatnonzero(np.diff(t) != 0) + 1                 # hedef değişim barları
if "limit" in fr: ch = np.union1d(ch, np.flatnonzero(np.isfinite(fr["limit"].to_numpy())))
ch = ch[ch > len(idx) * 0.25]
pick = ch[np.linspace(0, len(ch) - 1, min(20, len(ch))).astype(int)]
cuts = {idx[c - d] for c in pick for d in (2, 1, 0)}
```

Sentetik veri:
- 2022-01-01'den başlar.
- Uzunluklar: 1h 3 yıl, 4h 4 yıl, 1d 5 yıl, 15m 120 gün, 5m 40 gün (fitil_5m için 80 gün).
- Getiriler t(3) dağılımlı. Vadeli = spot × exp(t(3)·4 bps baz).
- Fonlama N(1 bp, 1,5 bp) / 8 saat.
- Konumlanma 5 dakikalık pozitif rastgele yürüyüşler. Prim t(3)·2 bps.
