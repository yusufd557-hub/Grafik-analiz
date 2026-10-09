# t2_bindirme — çalışma notları

Tur 2, protokol sürüm 2 (`GRAFIK_ANALIZ_PROTOKOL=2`). Aile: bindirmeler
(overlay) ve portföy kurgusu. Bu dosya planı, bileşen seçim kuralını ve
dondurma kararını **iç doğrulama (dev_valid) değerlendirmesinden önce** kayda
geçirir. Sonradan eklenen bölümler saatiyle işaretlenir.

## 0. Başlangıç durumu ve uyarılar (9 Ekim 2026, 16:59 UTC, arama başlamadan önce)

- Bu aile için önceki çalışma yok: `arastirma/tur2/t2_bindirme/` boştu,
  `arastirma/tur2/deneyler/t2_bindirme.jsonl` yok.
- Okundu: `docs/PROTOKOL_2.md`, `docs/PROTOKOL.md`, `arastirma/SONUC_1.md`,
  `arastirma/DENETIM_1.md`, `grafik_analiz/research/*.py`, tur 1 strateji
  modülleri (`trend`, `fonlama_carry`, `makine_ogrenmesi` ayrıntılı).
- **Bulaşma uyarısı:** `SONUC_1.md` tur 1'in görülmemiş dönem
  (01.07.2025–30.09.2026) sonuçlarını, `DENETIM_1.md` ve tur 1 spec
  açıklamaları tur 1 iç doğrulamasının (01.01.2024–30.06.2025) sonuçlarını ve
  korelasyonlarını içeriyor. Bu dönemlerin 2025 kısmı sürüm 2'de iç
  doğrulamanın içinde. Bu bilgiler hiçbir seçimde kullanılmayacak:
  - Portföy bileşenleri aşağıdaki mekanik kuralla, yalnız sürüm 2 eğitim
    döneminin (verinin başı – 31.12.2024) ölçüleriyle seçilir.
  - Denetimin önerdiği bileşen listesi (trend_vt, dip alımı ret4h, ML reg H4,
    formasyon F2) 2025 ilk yarısını içeren korelasyonlara dayandığı için
    **kullanılmaz**.
  - Araştırmacının (dil modeli) 2025 sonrası piyasa bilgisi de fikir, coin ve
    parametre seçiminde kullanılmaz. Evren tur 1 ile aynı (BTC/ETH/SOL).

## 1. Fikirler

Ortak çerçeve: her coin için bir **maruziyet sinyali** E(t) ∈ [0, 1] ve bu
maruziyeti uygulayan bir **yürütme biçimi**.

Maruziyet sinyalleri (hepsi geriye dönük):

- `trend`: tur 1 trend topluluğu (`trend.leg_target`, 4 fikir × 3 bakış
  süresi, yalnız alım), 0…1.
- `vol`: min(1, σ_hedef / σ_N); σ_N son N günün gerçekleşen yıllık oynaklığı
  (kapanış log getirilerinin kayan std'si). Coin başına uygulanınca ters
  oynaklık ağırlığı olur (düşük oynaklıklı coine daha çok sermaye).
- `trend_vol`: trend × vol.
- `sabit`: sabit E (E=1 al-tut, E=0 saf carry; taban çizgileri).

Yürütme biçimleri (kaldıraçsız, bacak başına pozisyon ≤ 1):

- `nakit`: yalnız spot bacaklar (her coin 1/3). Spot = E, gerisi nakit.
- `tam`: her coinde spot ve vadeli bacak (her biri 1/6). Carry açıkken spot
  = 1, vadeli = 2E − 1 (E = 0'da saf nakit-carry, E = 1'de tam uzun, uzunun
  yarısı vadeliden). Carry kapalıyken spot = min(1, 2E), vadeli =
  max(0, 2E − 1).
- `yarim`: aynı bacaklar; vadeli hiç uzun olmaz. Carry açıkken spot = 1,
  vadeli = −(1 − E) (net maruziyet E/2, korunan kısım fonlama toplar).
  Carry kapalıyken spot = E, vadeli = 0.
- Carry açık/kapalı: `fon_n = 0` ise fonlama verisi başladıktan sonra hep
  açık; değilse son `fon_n` günün ortalama fonlaması (8 saatlik eşdeğer)
  `fon_giris`'i geçince açılır, `fon_cikis`'in altına inince kapanır.
  Fonlama kaydı yalnız zaman damgası ≤ bar açılışı ise kullanılır.
- Carry'li biçimlerde coinin ilk fonlama kaydından önce pozisyon yok.
- Bant: E'deki `bant`'tan küçük değişiklikler uygulanmaz (0'a iniş her zaman
  uygulanır).

(a) **trend + carry**: `trend` sinyali × `tam`/`yarim` (4s). `nakit` biçimi
tur 1 trend stratejisinin kendisidir (kıyas).

(b) **oynaklık yönetimli maruziyet**: `vol` sinyali × `nakit` (1g). Zamanlama
için dürüst kıyas; saf beta ölçekleme olduğundan alfa şartını geçmesi
beklenmez, yine de raporlanır. Carry'li biçimleri de denenecek.

(c) **önceden kaydedilmiş eşit riskli portföy** (tur 1 dondurulmuş
yapılandırmalarından): kural bölüm 2'de.

## 2. Portföy bileşen seçim kuralı (bileşen sonuçlarından ÖNCE yazıldı)

1. **Havuz:** tur 1 dondurulmuş yapılandırmalarından (`grafik_analiz/strategies`
   tur 1 modülleri) **bütün bacakları vadeli** ve zaman dilimi 1s/4s/1g
   olanlar (19 yapılandırma). Gerekçe yapısal: portföy tek bir 1s vadeli
   spec'tir (vadeli BTC/ETH/SOL, bacak başına 1/3); spot ve vadeli
   bileşenler aynı bacakta toplanamaz, 15 dakikalık bileşen 1 saatlik
   yürütmeye sığmaz. Carry yapılandırmaları (spot+vadeli) havuz dışı.
2. Her havuz yapılandırması, aile adı `t2_bindirme` ve adı
   `t2_bindirme_bilesen_<tur 1 adı>` olacak şekilde yeniden etiketlenip
   `evaluate(windows=("dev_train",), cost_multipliers=(1.0, 2.0))` ile
   ölçülür (deftere yazılır). Günlük getiriler ayrıca verisi 31.12.2024'te
   kesilmiş bir yardımcıyla (dev_valid verisi hiç yüklenmeden) hesaplanır.
3. **Uygunluk** (hepsi gerekli):
   - eğitimde 1× ve 2× maliyetle net getiri > 0;
   - eğitimde alfa > 0 ve alfa t ≥ 1,0 (harness);
   - alfa hem 2020-01-01 – 2023-12-31 hem 2024 alt döneminde > 0 (yardımcı;
     2024 tur 1 için örneklem dışıydı, tur 1 seçim yanlılığına karşı kontrol).
4. **Sıralama:** eğitim alfa t'si (azalan).
5. **Seçim:** sırayla, daha önce seçilenlerin hepsiyle eğitim günlük getiri
   korelasyonu (2020-01-01 – 2024-12-31) 0,50'den küçükse eklenir. En fazla 4
   bileşen.
6. Uygun bileşen 2'den azsa 3. maddedeki alt dönem şartı kaldırılır; yine
   2'den azsa portföy yapılmaz.
7. **Ağırlık:** eşit risk. Bileşen k'nin çarpanı b_k = σ_hedef / σ_k
   (σ_k: 2020-01-01 – 2024-12-31 eğitim günlük getirilerinin yıllık std'si).
   Portföy vadeli bacak pozisyonu = kırp(3 · Σ_k b_k · w_kc · p_kc(t), −1, 1).
   Ölçek türleri: `sermaye` (Σ b_k = 1, kırpma neredeyse hiç devreye girmez)
   ve `hedef` (her bileşen ayrı ayrı σ_hedef'e ölçeklenir, b_k ≤ b_max;
   kaldıraç yok çünkü bacak pozisyonu ±1'de kırpılır). σ_k ve b_k
   parametredir, eğitimde hesaplanıp spec'e sabit yazılır.
8. Bileşen sinyalleri kendi zaman dilimlerinde, kendi `signal_fn`'leriyle,
   `grafik_analiz.research.data.load(..., scope="dev")` ile yüklenen ve
   **verilen 1s verinin son barının kapanışına kadar açıkça kesilen** veriyle
   hesaplanır. k bileşeninin bar kararı, kapanışı 1s barın kapanışından sonra
   olmayan son bileşen barından gelir.

## 3. Arama planı ve bütçe

- Yalnız `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))`.
- Karşılaştırma için ayrıca yardımcıyla (veri 31.12.2024'te kesik) 2020-01 –
  2024-12 alt dönem ölçüleri: yıllık getiri, 2020–2023 ve 2024 alfaları.
  Yalnız deftere yazılmış yapılandırmalar için.
- Tahmini bütçe: ~150 yapılandırma.
  - (b) vol × nakit: σ_hedef {0,4; 0,6; 0,8}, N {10, 20, 40, 80} gün,
    bant {0; 0,1}; ayrıca vol × tam/yarım.
  - (a) trend × {nakit, tam, yarim}: bakış {(10,20,40), (20,40,80),
    (40,80,160)} gün, fonlama süzgeci {hep, (3 g, 1e-4 / 0), (7 g, 0,5e-4 /
    −0,5e-4)}, bant {0; 0,15}; trend × vol birkaç.
  - Taban çizgileri: al-tut (sabit E=1, nakit), saf carry (sabit E=0, tam).
  - (c) 19 bileşen + birkaç portföy (ölçek türü, σ_hedef).

## 4. Seçim ölçütü (eğitim, sonuçlardan önce yazıldı)

Dondurulacak yapılandırma için (yaklaşım başına en iyi):

1. Eğitimde 1× ve 2× net getiri > 0, alfa > 0; alfa hem 2020–2023 hem 2024'te
   > 0.
2. İşlem sayısı: eğitimde yılda ortalama ≥ 12 işlem (iç doğrulamanın 21
   ayında 20 işlem şartını yapısal olarak karşılayabilmek için). Oynaklık
   kıyası bunu geçemeyecekse yine kıyas olarak dondurulur.
3. Sıralama: eğitim alfa t'si; eşitlikte Sharpe. Komşu parametrelerde de
   pozitif alfa (sivri tepe seçilmez).
4. En fazla 5 yapılandırma: (b) kıyası 1, (a) en fazla 2, (c) en fazla 2.

## 5. Arama günlüğü

(aşağıya her taramadan sonra eklenir)

### Tarama 1 (87 yapılandırma, 17:00–17:04 UTC) — `tarama1.py`, `tarama1.csv`

Yalnız dev_train. Not: carry'li biçimler 2020'den önce pozisyon almaz ama spot
bacaklar 2017'den başladığı için harness Sharpe'ı seyreliyor; karşılaştırma için
`alt_donem` ölçüleri (2020-01 – 2024-12) kullanıldı.

- **Taban çizgileri:** spot al-tut (nakit, E=1) 2020+ alfa −0,020 (t −0,43).
  Saf carry (tam, E=0): hep açık alfa %5,6/yıl (t 3,9); f3 süzgeci t 18,4,
  f7 süzgeci t 12,9 (harness'in carry Sharpe'ı teminat/tasfiye/dengeleme
  maliyeti yok sayıldığı için şişik; tur 1 denetimi 5.2).
- **(b) vol × nakit (24):** alfa ≈ 0 (t −1,0 … 0,85). Beta 0,37–0,66.
  Beklendiği gibi saf beta ölçekleme. En yüksek alfa t: h0,4 n40 b0,1
  (t 0,85; 2020–23 alfa −0,012, 2024 +0,113). İşlem sayısı 3 (sürekli
  pozisyon tek işlem sayılıyor) → işlem şartını yapısal olarak geçemez.
  vol × tam/yarım: alfa t ≤ 1,53, 2020–23 alfası ~0.
- **(a) trend:** bütün trend biçimlerinde 2020–2023 alfası güçlü (+0,18 …
  +0,41), **2024 alfası çoğunlukla negatif** (nakit L20 −0,07, L40 −0,12;
  tam biçimi hepsi negatif). Yalnız `yarim` + L10 (bütün süzgeçlerde) 2024'te
  pozitif (+0,012 … +0,026). `tam` biçimi vadeli uzun bacakta fonlama ödediği
  için (2020+ toplam ~%22–36 fonlama gideri) nakit biçiminden kötü.
  `yarim` + f7 süzgeci en iyi 2020+ Sharpe (L10: 1,97; alfa t 3,28).
- **trend × vol:** h0,4'te 2024 alfası pozitif (nakit +0,069, tam +0,072,
  yarım +0,069); yarımda işlem sayısı düşük (yılda 2,4).

Sonraki adım: tarama 3 (trend × vol ve yarım + L15 çevresi, 22 yapılandırma).

### Tarama 3 (22 yapılandırma, 17:05–17:07 UTC) — `tarama3.py`, `tarama3.csv`

- trend × vol (L10/L20, h 0,3/0,4/0,5, n30, bant 0,1) × {nakit, tam+f7,
  yarım+f7}: **18'inin hepsi** iki alt dönemde de pozitif alfalı. Alfa t,
  hedef oynaklık düştükçe artıyor (carry payı büyüyor): yarım h0,3 L10 t 4,66;
  tam h0,3 L10 t 3,46; nakit h0,3 L10 t 3,55.
- trend × yarım + f7, L15 (yeni bakış seti 15/30/60): t 3,41–3,49, 2024 alfası
  +0,013 / +0,020 (küçük).
- vol × yarım + f7: t 2,03 (2020–23 alfa +0,031), ama yılda 7,8 işlem.

### Tanı 1–2 (17:08–17:12 UTC) — `tani1.py`/`tani1.txt`, `tani2.py`/`tani2.csv`

Yalnız eğitim (veri 31.12.2024'te kesik), yalnız deftere yazılmış
yapılandırmalar. **Bulgu:** carry ağırlıklı biçimler fonlamanın sürekli pozitif
olduğu dönemde hiç pozisyon değiştirmiyor; harness bu durumda yeni işlem
saymıyor. Örnek: yarım h0,3 L10 f7'nin 2020+ ortalaması yılda 13,4 işlem ama
**2024'te 0 işlem**; yarım h0,4 L10 f7 2024'te 5 işlem. Bölüm 4'teki "yılda
ortalama ≥ 12 işlem" şartı bu yüzden yanıltıcı.

**Şart düzeltmesi (dev_valid'e bakılmadan, yalnız eğitim bilgisiyle):**
işlem şartı "2023'te ve 2024'te ayrı ayrı ≥ 12 işlem" olarak sıkılaştırıldı.

### Tarama 2 (19 bileşen, 17:02–17:20 UTC) — `tarama2.py`, `tarama2.csv`, `bilesen_gunluk.csv`

Tur 1 havuzunun eğitim ölçüleri (harness, 1×). Uyarı: 2017–2023 tur 1'in
kendi seçim dönemiydi (örneklem içi, seçim yanlılığı var); 2024 tur 1 için
örneklem dışıydı.

| Bileşen | Alfa | Alfa t | Beta | 2020–23 alfa | 2024 alfa |
|---|---:|---:|---:|---:|---:|
| ml clf H6 iki (egspot) | 0,405 | 4,25 | 0,10 | 0,482 | 0,187 |
| od_dip ret4h | 0,187 | 3,57 | 0,02 | 0,206 | 0,110 |
| ml reg H4 uzun (egspot) | 0,254 | 3,24 | 0,12 | 0,310 | 0,074 |
| od_dip ens4 1h | 0,095 | 3,22 | 0,03 | 0,111 | 0,030 |
| formasyon 1d ölçek234 iki | 0,425 | 2,78 | −0,05 | 0,580 | −0,043 |
| kırılım vadeli iki | 0,609 | 2,74 | −0,02 | 0,717 | 0,149 |
| formasyon üçgen/kama hacim iki | 0,309 | 2,73 | −0,01 | 0,341 | 0,179 |
| formasyon hepsi 10 bar uzun | 0,206 | 2,64 | 0,08 | 0,226 | 0,123 |
| rotasyon L21 volesit | 0,224 | 2,61 | 0,00 | 0,325 | −0,101 |
| kırılım vadeli uzun | 0,320 | 2,56 | 0,23 | 0,354 | 0,178 |
| … (trend, rotasyon, ay dönümü: 2024 alfası negatif; fonlama_negatif t 0,29) | | | | | |

### Bileşen seçimi (bölüm 2 kuralı, mekanik; `tarama4.py`, `portfoy_secimi.json`)

Alt dönem şartıyla uygun olanlar alfa t sırasıyla, korelasyon < 0,50 ile:

1. `ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot` (σ 0,239)
2. `od_dip_ret4h_fut_port3_1h` (σ 0,118)
3. `kirilim_kanal4h_vadeli_iki` (σ 0,496)
4. `formasyon_ucgen_kama_4h_hacim_iki` (σ 0,252)

Elenenler korelasyon yüzünden: ml reg H4 (ml clf ile), od_dip ens4 (od_dip ret4h
ile) vb. Seçilenler arası eğitim korelasyonları −0,11 … 0,28. (Not: tur 1
denetiminin dev_valid'e dayanan önerisiyle kısmen örtüşüyor; burada seçim
yalnız eğitim ölçüleriyle ve önceden yazılmış kuralla yapıldı.)

Portföy çeşitleri (tarama 4): eşit sermaye, eşit risk (Σb=1), eşit risk
σ_hedef 0,10 ve 0,20 (b ≤ 3).

### Tarama 4 (4 portföy, 17:12–17:18 UTC) — `tarama4.py`, `tarama4.csv`

| Çeşit | Çarpanlar (ml, od_dip, kırılım, formasyon) | Alfa | Alfa t | Beta | Sharpe | En büyük düşüş | 2020–23 alfa | 2024 alfa |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| eşit sermaye | 0,25 / 0,25 / 0,25 / 0,25 | 0,382 | 5,07 | 0,02 | 2,42 | −%10,1 | 0,435 | 0,165 |
| eşit risk, Σb=1 | 0,225 / 0,454 / 0,108 / 0,213 | 0,313 | 5,79 | 0,03 | 2,81 | −%12,7 | 0,353 | 0,151 |
| eşit risk σ 0,10 | 0,419 / 0,845 / 0,201 / 0,397 | 0,521 | 5,62 | 0,05 | 2,74 | −%17,0 | 0,583 | 0,273 |
| eşit risk σ 0,20 | 0,837 / 1,691 / 0,403 / 0,793 | 0,800 | 5,36 | 0,07 | 2,61 | −%19,6 | 0,899 | 0,402 |

Uyarı: bileşenlerin 2017–2023 dönemi tur 1'in seçim dönemiydi; bu
sayılar örneklem içi ve iyimserdir. Bileşen seçiminde 2024 alfası da şart
olduğundan 2024 de seçimde kullanıldı. Asıl ölçü dev_valid.

## 6. Dondurma kararı (dev_valid'e bakmadan, 9 Ekim 2026 17:18 UTC)

Bölüm 4 ölçütü + tanı 2'deki işlem şartı düzeltmesi (2023 ve 2024'te ayrı
ayrı ≥ 12 işlem). Dört yapılandırma donduruldu (beşinci hak kullanılmadı;
portföyün σ 0,10 çeşidi seçilen portföyle aynı bileşenler/ağırlık oranları,
yalnız ölçek farkı, iç doğrulamada yeni bilgi vermez):

1. **(b) kıyas:** `t2_bindirme_vol_nakit_1d_h0.4_n40_b0.1` — spot BTC/ETH/SOL,
   coin başına min(1, 0,4/σ_40g), bant 0,1. vol × nakit içinde en yüksek
   eğitim alfa t'si (0,85). Alfa şartını (2020–23 alfası −0,012) ve işlem
   şartını (sürekli pozisyon, eğitimde 3 işlem) geçmesi beklenmiyor; dürüst
   zamanlama kıyası olarak donduruldu.
2. **(a) trend + carry:** `t2_bindirme_trend_yarim_4h_L15_b0.15_f7` — trend
   topluluğu (4 fikir × 15/30/60 gün), yarım biçim (spot hep uzun, vadeli
   −(1−E); fonlama 7 günlük ortalaması −0,5e-4'ün altına inince carry
   kapanır), bant 0,15. Trend biçimleri içinde işlem şartını geçenlerden en
   yüksek alfa t (3,49); 2020–23 alfa 0,250, 2024 alfa 0,013 (küçük);
   2023/2024 işlem 22/17. Komşular (L10 b0,15 f7, L15 b0 f7) iki alt dönemde
   pozitif; L20 b0,15 f7'nin 2024 alfası −0,010.
3. **(a') trend × oynaklık + carry:** `t2_bindirme_trendvol_tam_4h_L10_h0.3_n30_b0.1_f7`
   — E = trend(10/20/40) × min(1, 0,3/σ_30g), tam biçim (spot 1, vadeli 2E−1,
   carry süzgeci f7), bant 0,1. İşlem şartını geçen carry'li yapılandırmalar
   içinde en yüksek alfa t (3,46); 2020–23 alfa 0,193, 2024 alfa 0,111;
   2023/2024 işlem 72/37. Komşular (L20 h0,3, L10 h0,4/h0,5 tam f7) hepsi iki
   alt dönemde pozitif. (Aynı sinyalin carry'siz nakit sürümü alfa t 3,55 ile
   biraz üstte ama aileye konu olan carry bindirmesi seçildi; ikisi aynı
   sinyal, iç doğrulamada ayrıca bakılmaz.)
4. **(c) portföy:** `t2_bindirme_portfoy_esit_risk_sermaye` — 4 bileşen,
   eşit risk (b_k ∝ 1/σ_k, Σ b = 1). Portföy çeşitleri içinde en yüksek
   eğitim alfa t'si (5,79).

Her biri `assert_causal` ile denetlenecek (portföy ve diğerleri için ek
kesimlerle), sonra `dogrulama.py` ile bir kez `evaluate(spec)` (dev_train +
dev_valid, 1× ve 2×) ve `candidate_check`. dev_valid'den sonra yeniden ayar
yapılmayacak.

### Dondurma kontrolü (17:36 UTC) — `dondurma_kontrol.py`, `dondurma_kontrol_1.log`, `dondurma_kontrol_2.log`

- Dört spec'in parametreleri defterdeki dev_train satırlarıyla birebir aynı.
- `assert_causal` varsayılan kesimler (0,55 / 0,8 / 0,97) ve ek kesimler
  (0,3 / 0,9 / 0,995; portföyde ayrıca ML aylık yeniden eğitiminden 2 saat
  sonrası, 2024-03-01 02:00) — dördü de **GEÇTİ**.
- Sıradaki adım: `dogrulama.py` (tek seferlik dev_valid).

## 7. dev_valid sonrası (17:36–17:45 UTC; dondurmadan SONRA eklendi)

`dogrulama.py` bir kez çalıştı (`dogrulama.log`, `dogrulama_sonuc.json`).
candidate_check: trend + carry (yarım L15) **GEÇTİ**, trend × vol + carry (tam
L10 h0,3) **GEÇTİ**, vol kıyası ve portföy **GEÇMEDİ**. Ayrıntılar `RAPOR.md`.
dev_valid'den sonra hiçbir parametre, kural ya da spec değiştirilmedi; yalnız
spec açıklama metinlerine sonuç yazıldı. `dogrulama_tani.py` yalnız
betimleyici döküm (aynı dondurulmuş spec'ler, yeni yapılandırma yok, deftere
yazılmadı).
