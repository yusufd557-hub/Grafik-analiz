# Rotasyon ailesi — araştırma raporu

Aile: `rotasyon` (BTC, ETH ve SOL arasında kesitsel momentum / göreli güç).
Protokol: `docs/PROTOKOL.md`, sürüm 1. Bütün sayılar ortak araştırma aracından
(`grafik_analiz.research`) alındı.

## Sonuç (kısaca)

**Aday şartlarını geçen yapılandırma yok.** Eğitim döneminde (2023 sonuna
kadar) güçlü görünen beş yapılandırma donduruldu ve iç doğrulama döneminde
(01.01.2024 – 30.06.2025) birer kez ölçüldü. Dördü zarar etti. Biri (spot,
haftalık en güçlü coin) kârda kaldı, ama Sharpe 0,42 ile 0,5 eşiğinin altında
kaldı. En iyi tek işlemi çıkarınca da zarardaydı. Aynı dönemde BTC al-tut
+%153,40, üç coinin eşit ağırlıklı sepeti +%73,67 kazandı.

Eğitim döneminde de rotasyonun kendine ait bir katkısı görülmedi. Spot
rotasyonun kârının kaynağı, düşen coinden nakde geçmekti (zaman serisi
momentumu). Kesitsel seçimin katkısı yoktu. Aynı filtreyle üç coinin hepsini
tutan kontrol, en güçlü 1–2 coini seçen rotasyonla aynı ya da daha yüksek
Sharpe verdi (aşağıda 4.2). Vadeli piyasa nötr uzun/kısa ise eğitimde her yıl
kârlıydı. Bu yapı iç doğrulamada en çok kaybeden yapılandırma oldu (−%39,22).

## 1. Kurallar ve uyum

- Yalnız `scope="dev"` verisi kullanıldı. `unlock_holdout()` çağrılmadı.
  Araştırma verisi klasörü doğrudan okunmadı, veri indirilmedi.
- Tarama sırasında bütün değerlendirmeler
  `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))` ile yapıldı ve deftere
  (`arastirma/deneyler/rotasyon.jsonl`) yazıldı. Sonra beş yapılandırma donduruldu. Her biri
  `evaluate(spec)` ile bir kez değerlendirildi (`dogrulama.py`). Ardından `candidate_check()`
  uygulandı. dev_valid sonucuna bakıldıktan sonra hiçbir kural ya da parametre değişmedi.
- Bazı yapılandırmaların eğitim içi yıllık dökümü için `run(spec, "dev")` kullanıldı
  (`ortak.py: yillik / yillik_islem`). Getiri serisi hemen 01.01.2024'te kesildi. Bu
  yapılandırmaların hepsi önceden `evaluate()` ile deftere yazılmıştı.
- Al-tut karşılaştırmaları `evaluate(..., record=False)` ile hesaplandı. Strateji denemesi
  sayılmadıkları için deftere yazılmadılar.
- Dondurulan beş yapılandırmanın hepsi `assert_causal` denetiminden geçti. Bu denetim
  varsayılan kesim noktalarında ve ayrıca 9 ek kesim noktasında (0,2…0,99) yapıldı.
- Bacak ağırlıkları eşittir, toplamları 1'dir. Spot pozisyonlar 0…1, vadeli pozisyonlar
  −1…1 aralığındadır. Kaldıraç yoktur.

## 2. Denenen yaklaşımlar ve parametre aralıkları

Bütün sinyaller günlük (1d) mumlarla ve kapanış fiyatlarıyla hesaplandı. Kod
`grafik_analiz/strategies/rotasyon.py` dosyasındadır. Yeniden dengeleme takvime bağlıdır.
`every=7` için karar pazar kapanışında verilir, işlem pazartesi açılışında yapılır.
Verisi henüz olmayan coin seçilemez (SOL spot 2020-08, SOL vadeli 2020-09). Vadeli
bacaklarda, coinin ilk fonlama kaydından önce pozisyon açılmaz. Böylece vadeli 1d
verisinin fonlamasız ilk ayları (2019-09 → 2020-01) maliyetsiz sayılmaz.

**A) Spot rotasyon (BTC/ETH/SOL, her bacak sermayenin 1/3'ü).** Her yeniden dengelemede
skoru en yüksek `top_k` coin tutulur.
- Geriye bakış L (lookback): 7, 14, 28, 56, 91 gün.
- Skor: `getiri` (L günlük log getiri) veya `risk` (getiri / oynaklık).
- Seçilen coin sayısı top_k: 1 veya 2.
- Yeniden dengeleme: her gün (1) veya her hafta (7).
- Filtre: `yok`, `mutlak` (L günlük getiri > 0) veya `ma100` (kapanış > 100 günlük SMA).
- 1. aşamada 5×2×2×2×3 = 120 yapılandırma.

**B) Vadeli piyasa nötr uzun/kısa (BTC/ETH/SOL vadeli).** En güçlü coinde +1, en zayıf
coinde −1. Her bacak sermayenin 1/3'üdür. Fonlama dahildir.
- L: 7, 14, 28, 56, 91.
- Skor: getiri veya risk.
- Yeniden dengeleme: 1 veya 7 gün.
- Mod: `ls` (her zaman uzun/kısa) veya `ls_trend` (uzun yalnız SMA100 üstünde, kısa yalnız
  SMA100 altında).
- 1. aşamada 40 yapılandırma.

**C) Oran trendi (vadeli çift, her bacak 1/2).** ALT/BAZ oranı n günlük SMA'sının
üstündeyse ALT uzun ve BAZ kısa açılır.
- Çiftler: ETH/BTC, SOL/BTC, SOL/ETH.
- n: 20, 50, 100, 200.
- Mod: `ls` (ortalamanın altında tersi) veya `yukari` (ortalamanın altında nakit).
- Yeniden dengeleme: 1 veya 7 gün.
- 1. aşamada 48 yapılandırma.

**2. aşama (30 yapılandırma).** Kontroller ve sağlam bölgelerin çevresi denendi:
- Kontrol 1, yalnız zaman serisi momentumu: top_k=3 + mutlak filtre, kesitsel seçim yok.
- Kontrol 2, SOL'suz evren: spot BTC/ETH rotasyonu ve vadeli BTC/ETH uzun/kısa.
- Haftalık dengeleme ile her gün uygulanan mutlak filtre (`gunluk_filtre`).
- Birleşik skor `karma`: L/2, L ve 2L ufuklarının √ufuk ile ölçeklenmiş ortalaması.
- Vadeli uzun/kısada L=21/42 ve 3 günlük dengeleme.

**3. aşama (5 yapılandırma).** Vadeli uzun/kısada iki tarafın 30 günlük oynaklığı
eşitlendi (`vol_esit=30`).

## 3. Deneme sayısı

| | Sayı |
|---|---|
| dev_train'de değerlendirilen benzersiz yapılandırma | **243** (120 + 40 + 48 + 30 + 5) |
| Defterde `pencere=="dev_train"` ve `maliyet_kat==1.0` satırı | **248** (243 + dondurulan 5'in son değerlendirmesindeki tekrar satırları) |
| dev_valid'de değerlendirilen yapılandırma | **5** |

Deflated Sharpe hesabında görevde istenen sayı (248) kullanıldı. 248 satırın yıllık
Sharpe varyansı 0,1925, ortalaması 1,071, en büyüğü 1,808'dir. Bu sayıyla, şansla
beklenen en büyük yıllık Sharpe (SR0) 1,24 çıkıyor.

## 4. dev_train sonuçları (2017-08 → 2023-12, 1× maliyet)

### 4.1 Gruplara göre özet

| Grup | n | Net > 0 | Sharpe min / medyan / maks | 2×'te net > 0 | Yıllık ciro medyanı | Maks. DD medyanı |
|---|---|---|---|---|---|---|
| Spot rot. top1, filtre yok | 20 | 20 | 0,98 / 1,32 / 1,55 | 20 | 12,9 | −%46 |
| Spot rot. top1, mutlak | 22 | 22 | 1,22 / 1,46 / 1,67 | 22 | 9,7 | −%34 |
| Spot rot. top1, mutlak + günlük filtre | 3 | 3 | 1,59 / 1,62 / 1,81 | 3 | 9,8 | −%34 |
| Spot rot. top1, ma100 | 20 | 20 | 0,94 / 1,17 / 1,38 | 20 | 10,5 | −%40 |
| Spot rot. top2, filtre yok | 20 | 20 | 0,93 / 1,13 / 1,29 | 20 | 7,8 | −%73 |
| Spot rot. top2, mutlak | 22 | 22 | 1,21 / 1,51 / 1,73 | 22 | 13,1 | −%48 |
| Spot rot. top2, mutlak + günlük filtre | 3 | 3 | 1,56 / 1,75 / 1,76 | 3 | 14,1 | −%49 |
| Spot rot. top2, ma100 | 20 | 20 | 1,18 / 1,31 / 1,42 | 20 | 9,6 | −%53 |
| **Kontrol: üç coin + mutlak filtre (seçim yok)** | 3 | 3 | 1,45 / 1,60 / 1,75 | 3 | 8,4 | −%55 |
| Kontrol: spot BTC/ETH top1 (SOL'suz) | 3 | 3 | 0,98 / 1,14 / 1,35 | 3 | 10,0 | −%41 |
| Vadeli U/K `ls`, getiri | 17 | 17 | 0,44 / 0,84 / 1,25 | 17 | 25,5 | −%40 |
| Vadeli U/K `ls`, karma | 4 | 4 | 0,95 / 1,15 / 1,20 | 4 | 31,9 | −%34 |
| Vadeli U/K `ls`, oynaklık eşit | 5 | 5 | 0,78 / 1,05–1,26 / 1,47 | 5 | 13–48 | −%13…−%25 |
| Vadeli U/K `ls`, risk skoru | 10 | 8 | −0,29 / 0,45 / 0,70 | 8 | 30,8 | −%44 |
| Vadeli U/K `ls_trend` | 20 | 19 | 0,09 / 0,35–0,63 / 0,73 | 19 | 20–22 | −%53…−%57 |
| Kontrol: vadeli U/K yalnız BTC/ETH | 3 | 3 | 0,25 / 0,31 / 0,47 | 3 | 24,4 | −%32 |
| Oran ETH/BTC `ls` | 8 | 4 | −0,29 / 0,10 / 0,48 | 3 | 24,4 | −%42 |
| Oran ETH/BTC `yukari` | 8 | 8 | 0,21 / 0,48 / 0,83 | 8 | 12,3 | −%26 |
| Oran SOL/BTC `ls` | 8 | 8 | 0,33 / 0,85 / 1,08 | 8 | 19,3 | −%58 |
| Oran SOL/BTC `yukari` | 8 | 8 | 1,19 / 1,31 / 1,64 | 8 | 9,5 | −%36 |
| Oran SOL/ETH `ls` | 8 | 8 | 0,49 / 0,69 / 0,97 | 8 | 17,4 | −%53 |
| Oran SOL/ETH `yukari` | 8 | 8 | 1,13 / 1,24 / 1,46 | 8 | 8,6 | −%32 |

Yıllık ciro, ağırlıklı pozisyon değişimlerinin yıllık toplamıdır: maliyet / (taraf
başına maliyet) / yıl. Ayrıntılı sonuçlar `tarama1.csv`, `tarama2.csv` ve `tarama3.csv`
dosyalarındadır.

Eğitim dönemi al-tut (aynı pencere):

| | Net getiri | Sharpe | Maks. DD |
|---|---|---|---|
| BTC spot | +%885,53 | 0,86 | −%83,20 |
| ETH spot | +%654,65 | 0,81 | −%93,97 |
| SOL spot (2020-08'den) | +%2980,57 | 1,42 | −%96,27 |
| BTC/ETH/SOL eşit ağırlık (her bar dengelenmiş) | +%3089,15 | 1,12 | −%85,46 |
| BTC vadeli uzun, fonlama dahil (2019-09'dan) | +%125,03 | 0,63 | −%78,93 |

### 4.2 Eğitim döneminde görülenler

1. **Spot rotasyonun kârı kesitsel seçimden gelmiyor.** Spot yapılandırmaların hepsi
   kârlıydı. Bunun nedeni, dönemin güçlü yükseliş yıllarını (2017, 2020, 2021, 2023)
   kapsamasıdır. Belirleyici olan filtredir: `mutlak` filtrenin Sharpe medyanı 1,47,
   filtresiz varyantlarınki 1,17'dir. Aynı filtreyle üç coinin hepsini tutan kontrol
   (L=28) Sharpe 1,75 verdi. Bu, en güçlü coini (1,62) veya en güçlü iki coini (1,73)
   seçen rotasyona eşit ya da daha yüksektir. Geriye bakış, skor türü, dengeleme sıklığı
   ve top_k'ya göre medyan Sharpe farkları küçüktü (1,22–1,35). Kesitsel seçimin kendi
   katkısı bu veride ayırt edilemedi.
2. **Spot rotasyon yıldan yıla dengesizdi.** Haftalık top1/L14/günlük filtre yapılandırması
   2018'de +%7,2, 2022'de −%6,2 getirdi. Kârın çoğu 2020 (+%95,9), 2021 (+%184,1) ve
   2023 (+%88,3) yıllarından geldi.
3. **Vadeli uzun/kısa SOL'a bağlıydı.** Uzun/kısa (`ls`, getiri skoru) eğitimde her yıl
   kârlıydı. Örneğin karma L28 haftalık: 2020 +%56,4, 2021 +%93,2, 2022 +%20,8, 2023
   +%12,5. Ancak yalnız BTC/ETH ile Sharpe 0,25–0,47'ye düştü. Kârın büyük kısmı SOL'un
   2021 yükselişi ve 2022 çöküşüyle geldi. Sonuç geriye bakışa duyarlıydı: medyan Sharpe
   L=21'de 1,24, L=28'de 1,10, L=42'de 0,47, L=56'da 0,57. Yıllık getiri 2020–2021'den
   2023'e doğru azaldı.
4. **ETH/BTC oran trendi zayıftı.** `ls` modunda Sharpe medyanı 0,10'du. SOL oranlarının
   `yukari` modu güçlü göründü (1,13–1,64). Bu kâr neredeyse tamamen 2021'den geliyordu:
   SOL/BTC n50 için 2021 +%531,6, 2022 −%16,1, 2023 +%100,3. Bu yaklaşımın SOL verisi
   eğitimde yalnız üç yıldı.

## 5. Dondurulan yapılandırmalar ve seçim gerekçesi

Seçim yalnız dev_train sonuçlarıyla, dev_valid'e bakılmadan yapıldı. Ölçütler:
- Komşu parametrelerin de iyi olduğu bir bölgede olmak.
- 2× maliyette Sharpe'ın korunması.
- Yıllık döküm.
- Eğitimdeki işlem sıklığından, dev_valid'de en az 20 işlem beklenmesi. Örneğin haftalık
  top1 + mutlak filtre (L28 karma) yılda yalnız ~10–13 işlem yapıyordu. Bu yüzden günlük
  filtreli varyant seçildi.
- Yaklaşım çeşitliliği: iki spot rotasyon, iki vadeli uzun/kısa, bir oran trendi.

| # | Ad | Parametreler | Seçim nedeni (dev_train) |
|---|---|---|---|
| 1 | `rotasyon_spot_top1_L14_gunluk` | spot ×3, L=14, getiri, top_k=1, haftalık, mutlak, günlük filtre | En yüksek spot Sharpe (1,81). En düşük düşüş (−%22,4). Ayı yıllarında en iyisi. ~20 işlem/yıl. |
| 2 | `rotasyon_spot_top2_L28_gunluk` | spot ×3, L=28, getiri, top_k=2, haftalık, mutlak, günlük filtre | top2 bölgesinin ortası (1,76; komşular 1,51–1,75). ~22 işlem/yıl. |
| 3 | `rotasyon_vadeli_uzunkisa_karma28` | vadeli ×3, karma (14/28/56), haftalık, `ls` | Geriye bakış duyarlılığına karşı karma skor. Her yıl kârlı. Düşük ciro (14/yıl). |
| 4 | `rotasyon_vadeli_uzunkisa_L21_volesit` | vadeli ×3, L=21, getiri, günlük, `ls`, vol_esit=30 | En yüksek uzun/kısa Sharpe (1,47). En düşük düşüş (−%12,9). |
| 5 | `rotasyon_oran_SOLBTC_n50_yukari` | vadeli SOL+BTC, n=50, `yukari`, günlük | SOL oranlarının `yukari` bölgesi (1,13–1,64) geniş ve tutarlıydı. |

Bilinen bir eksiklik var: 1 ve 4, kendi gruplarındaki en yüksek eğitim Sharpe'ı olduğu için
seçildi. Bu seçim yanlılığı Deflated Sharpe'ta hesaba katılır.

## 6. Dondurulan yapılandırmalar: eğitim ve iç doğrulama sonuçları

### 6.1 dev_train (1× ve 2× maliyet)

| # | Net getiri | CAGR | Sharpe | Maks. DD | İşlem | 2× net | 2× Sharpe | Yıllık ciro | Fonlama (toplam) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | +%1647,21 | %56,68 | 1,808 | −%22,44 | 127 | +%1479,10 | 1,749 | 13,2 | — |
| 2 | +%5487,84 | %88,04 | 1,764 | −%50,20 | 136 | +%4915,84 | 1,722 | 14,1 | — |
| 3 | +%310,64 | %38,76 | 1,190 | −%35,76 | 93 | +%293,46 | 1,159 | 14,2 | %22,96 ödendi |
| 4 | +%239,66 | %32,79 | 1,469 | −%12,91 | 342 | +%193,46 | 1,305 | 48,4 | %5,95 ödendi |
| 5 | +%961,63 | %72,95 | 1,637 | −%28,57 | 56 | +%921,53 | 1,613 | 12,8 | %1,65 ödendi |

### 6.2 dev_valid (01.01.2024 – 30.06.2025, 546 gün)

| # | Net getiri | 2× net | Sharpe | 2× Sharpe | Maks. DD | İşlem | Yıllık ciro | Bootstrap p | En iyi işlem çıkınca | Aday |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **+%9,63** | +%5,84 | 0,425 | 0,297 | −%24,73 | 44 | 19,6 | 0,317 | −%3,26 | Hayır (Sharpe < 0,5) |
| 2 | −%4,09 | −%7,67 | 0,039 | −0,052 | −%35,00 | 47 | 21,2 | 0,469 | −%17,64 | Hayır |
| 3 | −%39,22 | −%40,73 | −1,696 | −1,787 | −%39,91 | 54 | 24,1 | 0,987 | −%45,02 | Hayır |
| 4 | −%6,92 | −%12,75 | −0,252 | −0,544 | −%20,08 | 148 | 61,7 | 0,634 | −%12,91 | Hayır |
| 5 | −%27,62 | −%29,77 | −1,221 | −1,344 | −%34,84 | 42 | 28,8 | 0,922 | −%36,66 | Hayır |

`candidate_check` ayrıntısı:
- **1:** eğitim net > 0 ✔, doğrulama net > 0 ✔, 2× net > 0 ✔, Sharpe ≥ 0,5 ✘ (0,425),
  işlem ≥ 20 ✔ → aday değil.
- **2–5:** doğrulama net > 0 ✘, 2× net > 0 ✘, Sharpe ✘; yalnız eğitim ve işlem sayısı ✔
  → aday değil.

dev_valid içinde yarım yıllık getiriler:

| # | 2024 H1 | 2024 H2 | 2025 H1 |
|---|---|---|---|
| 1 | +%19,16 | −%4,42 | −%3,74 |
| 2 | +%0,47 | −%1,71 | −%2,89 |
| 3 | −%23,04 | −%0,82 | −%20,37 |
| 4 | −%8,84 | −%5,76 | +%8,35 |
| 5 | −%5,12 | −%13,65 | −%11,66 |

### 6.3 Deflated Sharpe

Girdiler:
- Deneme sayısı N = 248.
- Deneme Sharpe'larının varyansı 0,1925 (yıllık).
- dev_valid günlük getirileri: n = 546 gün, çarpıklık ve basıklık `summarize` çıktısından.

Hesap `grafik_analiz.research.deflated_sharpe` ile yapıldı (`analiz.py`).

| # | dev_valid Sharpe | Çarpıklık | Basıklık | DSR (dev_valid) | Bilgi: DSR (dev_train Sharpe ile) |
|---|---|---|---|---|---|
| 1 | 0,425 | 1,084 | 12,222 | **0,156** | 0,930 |
| 2 | 0,039 | 0,455 | 8,496 | **0,070** | 0,901 |
| 3 | −1,696 | −0,901 | 7,707 | **0,0001** | 0,456 |
| 4 | −0,252 | 0,755 | 16,617 | **0,035** | 0,683 |
| 5 | −1,221 | 0,145 | 8,016 | **0,0014** | 0,814 |

Hiçbiri 0,95'e yaklaşmıyor. Eğitim Sharpe'ı ile hesaplanan DSR bile 0,95'in altında.
Bu, 243 denemenin en iyisinin (1,81) şans beklentisinin (SR0 ≈ 1,24) çok üstünde
olmadığını gösteriyor.

## 7. Al-tut karşılaştırması (dev_valid, aynı pencere, 1× maliyet)

| | Net getiri | Sharpe | Maks. DD |
|---|---|---|---|
| BTC spot | +%153,40 | 1,47 | −%28,10 |
| ETH spot | +%8,92 | 0,43 | −%63,75 |
| SOL spot | +%52,19 | 0,75 | −%59,77 |
| BTC/ETH/SOL eşit ağırlık | +%73,67 | 0,90 | −%49,07 |
| BTC vadeli uzun (fonlama dahil) | +%119,78 | 1,28 | −%29,39 |
| Nakit | %0 | — | %0 |

Spot rotasyonlar (1, 2) ana sermayenin en fazla 1/3'ünü (1) veya 2/3'ünü (2) bir
coine yatırabiliyor. Buna rağmen düşüşleri (−%24,73, −%35,00) BTC al-tut ile
karşılaştırılabilir düzeydeydi, getirileri ise çok düşüktü. Piyasa nötr uzun/kısa (3, 4)
ve oran stratejisi (5) için doğru karşılaştırma nakittir (%0). Üçü de nakdin altında kaldı.

## 8. Değerlendirme

- **Neden çalışmadı?** Üç coinlik bir evrende "göreli güç", tek bir oranın (çoğu zaman
  SOL'un BTC'ye göre) trendine indirgeniyor. Eğitim döneminde bu oranın büyük ve kalıcı
  trendleri vardı: SOL 2021'de yükseldi, 2022'de çöktü. 2024 – 2025 H1'de liderlik
  sık değişti, oran trendleri kısa sürdü ve geri döndü. Uzun/kısa ve oran stratejileri
  bu dönemde art arda ters pozisyona yakalandı. İşlemlerin kazanma oranı %39–41 idi;
  kâr faktörü 0,57–0,92 aralığındaydı.
- **Spot rotasyonun eğitimdeki başarısı** büyük ölçüde boğa piyasalarında yatırımda
  kalıp düşüşlerde nakde geçmekten geldi. Bu, trend takibi ailesinin konusudur. Kontrol
  deneyi bunu eğitim döneminde gösterdi. dev_valid'de BTC'nin tek başına önde gittiği
  bir piyasada rotasyon, sermayenin küçük bir kısmıyla ve sık geçişlerle al-tut'un çok
  gerisinde kaldı.
- **Maliyet** belirleyici değildi. Dört yapılandırma 1× maliyette de zarardaydı.
  Kârda kalan 1 numarada maliyet dev_valid'de toplam %3,52 tuttu.
- **Dürüst sonuç:** Bu ailede, protokolün aday şartlarını geçen ve finalist olarak
  önerilebilecek bir strateji bulunamadı. Görülmemiş dönem için bu aileden aday
  önerilmiyor.

## 9. Araç (harness) hakkında notlar

Bunlar değiştirilmedi, yalnız not edildi:

1. `combine()` bacakları her barda sabit sermaye ağırlığına maliyetsiz yeniden dengeler
   (sabit karışım). Çok bacaklı stratejilerde bacaklar arası dengeleme ücretsiz sayılır.
   Eşit ağırlıklı al-tut sepetine de bu yüzden bir dengeleme getirisi eklenir.
   Etkinin küçük olması beklenir, ama ölçülmedi.
2. Bacak ağırlıkları sabit olduğu için bir rotasyon "bütün sermayeyi en güçlü coine"
   koyamaz. Üç bacakta tek coinin payı en fazla 1/3'tür. Bu, aile için yapısal bir
   sınırlamadır. Sharpe ve getirinin işareti etkilenmez, getiri büyüklüğü etkilenir.
3. Vadeli 1d mumları 2019-09'dan, fonlama kayıtları 2020-01'den başlıyor. Araç, fonlama
   kaydı olmayan dönemde vadeli pozisyonu fonlamasız sayar ve uyarı vermez. Bu ailede
   pozisyonlar ilk fonlama kaydından önce 0 tutuldu.
4. İşlem sayısı bacak başına aynı yönlü kesintisiz dilimlerden hesaplanır. Aynı yönde
   boyut değişimi (ör. oynaklık eşitleme) yeni işlem sayılmaz, ama maliyet düşülür. Çok
   bacaklı stratejilerde bir geçiş birden fazla işlem sayılabilir.
5. Dönemler arası işlemler giriş zamanına göre sayılır. dev_train'de açılıp dev_valid'de
   kapanan işlem dev_valid sayısına girmez.
6. Son `evaluate(spec)` çağrısı dev_train satırlarını deftere yeniden yazar. Bu yüzden
   deneme sayısı (248), benzersiz yapılandırma sayısından (243) 5 fazladır. Bu ihtiyatlı
   yönde bir sapmadır.

## 10. Dosyalar

| Dosya | İçerik |
|---|---|
| `grafik_analiz/strategies/rotasyon.py` | Sinyal fonksiyonları ve `specs()`: dondurulan 5 yapılandırma (hiçbiri aday değil) |
| `arastirma/rotasyon/tarama1.py`, `tarama2.py`, `tarama3.py` | dev_train taramaları; sonuçlar `tarama*.csv` |
| `arastirma/rotasyon/ortak.py` | Tarama ve eğitim içi yıllık döküm yardımcıları |
| `arastirma/rotasyon/yillik1.py`, `yillik2.py` | Kısa listenin eğitim içi yıllık getirileri ve işlem sayıları |
| `arastirma/rotasyon/nedensellik.py` | Dondurulan yapılandırmaların `assert_causal` denetimi |
| `arastirma/rotasyon/dogrulama.py` | Tek seferlik dev_valid değerlendirmesi; sonuçlar `dondurulmus_sonuclar.json` (+ `.pkl`) |
| `arastirma/rotasyon/analiz.py` | Deflated Sharpe, al-tut, yarım yıllık döküm; sonuçlar `analiz.json` |
| `arastirma/rotasyon/yeniden_uretim.py` | Modülün dev_train sayılarını yeniden ürettiğinin denetimi (deftere yazmaz) |
| `arastirma/rotasyon/veri_kontrol.py`, `smoke.py` | Veri kapsamı ve sinyal duman testi (getiri hesaplamaz) |
| `arastirma/deneyler/rotasyon.jsonl` | Deney defteri (506 satır) |

Not: Bu araştırmayı yapan modelin genel bilgisi, 2024–2025 piyasa tarihini (ör. ETH/BTC
oranının düşüşü) kapsıyor. Bu bilgi seçimde kullanılmadı. Seçim yalnız dev_train
tablolarıyla yapıldı ve gerekçesi 5. bölümde yazılı.
