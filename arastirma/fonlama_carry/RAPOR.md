# Fonlama ve carry ailesi — araştırma raporu

Aile: `fonlama_carry` (vadeli fonlama oranına dayanan stratejiler: nakit-carry ve fonlama
uçlarından yönlü sinyaller). Protokol: `docs/PROTOKOL.md`, sürüm 1. Bütün sayılar ortak
araştırma aracından (`grafik_analiz.research`) alındı. Kod: `grafik_analiz/strategies/fonlama_carry.py`.

## Sonuç (kısaca)

**Aday şartlarını geçen yapılandırma yok.**

- **Nakit-carry** (aynı coinde spot uzun + sürekli vadeli kısa) iç doğrulama döneminde
  (01.01.2024 – 30.06.2025) de maliyetler düşüldükten sonra kârlı kaldı. Dondurulan üç carry
  yapılandırması 18 ayda +%4,50, +%7,49 ve +%7,39 kazandı. Bu yıllık %3,0–4,9 eder. En büyük
  düşüş %0,15'ten küçüktü. İki kat maliyetle de kârdaydılar (+%4,01, +%7,42, +%7,39).
  Getirinin neredeyse tamamı fonlamadan geldi. Fiyat/baz katkısı ±%0,15 içindeydi.
- Buna rağmen üçü de **"iç doğrulamada en az 20 işlem" şartını geçemedi** (12, 2 ve 0 işlem).
  Carry düşük cirolu bir stratejidir: pozisyona girip aylarca kalır. Bu yapı, protokolün
  işlem sayısı şartıyla uyuşmuyor. Diğer dört şart (eğitimde net > 0, doğrulamada net > 0,
  2× maliyette net > 0, Sharpe ≥ 0,5) üçünde de geçti.
- **Yönlü fonlama sinyalleri** iç doğrulamada başarısız oldu. Dondurulan yapılandırma, fonlama
  negatifken (kalabalık kısa) vadeli uzun açıyordu. Sonuç −%13,17 (2×: −%14,18), Sharpe
  −0,68 oldu. Eğitimde de yönlü sinyaller coinden coine tutarsızdı. Fonlama çok yüksekken
  açığa satış, eğitim döneminde bütün coinlerde ağır zarar etti.
- Aynı iç doğrulama döneminde BTC spot al-tut +%153,40, ETH +%8,92, SOL +%52,19, üç coinin
  eşit ağırlıklı sepeti +%73,67 kazandı. Carry'nin getirisi bunların çok altındadır. Carry'nin
  amacı fiyat riskini sıfıra yaklaştırmaktır, al-tut ile yarışmak değildir.

## 1. Kurallar ve uyum

- Yalnız `scope="dev"` verisi kullanıldı. `unlock_holdout()` çağrılmadı. Araştırma verisi
  klasörü doğrudan okunmadı, veri indirilmedi.
- Tarama sırasında her yapılandırma
  `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))` ile değerlendirildi ve
  deftere (`arastirma/deneyler/fonlama_carry.jsonl`) yazıldı. Dört yapılandırma yalnız eğitim
  sonuçlarıyla donduruldu ve her biri `evaluate(spec)` ile **bir kez** değerlendirildi
  (`dogrulama.py`). Ardından `candidate_check()` uygulandı. dev_valid sonucuna bakıldıktan sonra
  hiçbir kural ya da parametre değişmedi. Yalnızca `specs()` açıklama metnine candidate_check
  sonucu yazıldı.
- Bazı tanılarda `run(spec, "dev")` kullanıldı (`ortak.py: ayristir`, `tani_sol.py`): yıllık
  döküm, getiri ayrıştırması ve düşüş tanısı. Bu hesaplarda seriler hemen 01.01.2024'te
  kesildi. Kullanılan yapılandırmaların hepsi önceden `evaluate()` ile deftere yazılmıştı.
- **Açıklanması gereken küçük bir istisna:** Taramadan önce yazılan mekanik kontrol
  (`mekanik_kontrol.py`), bir yapılandırmanın (BTC carry) kısa pozisyondayken aldığı fonlamanın
  toplamını bütün geliştirme dönemi için (2020-01 → 2025-06) bir kez yazdırdı (−0,6027). Amaç
  fonlamanın işaretini doğrulamaktı. Bu sayı iç doğrulama dönemini ayrı göstermez ve seçimde
  kullanılmadı. Sonraki bütün tanılar 2024 öncesiyle sınırlandı.
- Al-tut karşılaştırmaları `evaluate(..., record=False)` ile hesaplandı (`al_tut.py`). Bunlar
  strateji denemesi olmadığı için deftere yazılmadı. İç doğrulama dönemi al-tut değerleri ancak
  dondurmadan sonra hesaplandı.
- Dondurulan dört yapılandırmanın hepsi `assert_causal` denetiminden geçti: varsayılan kesim
  noktalarında ve 10 ek kesim noktasında (0,2…0,99) (`nedensellik.py`).
- `yeniden_uretim.py`, `specs()`'in dondurulmuş eğitim sonuçlarını birebir ürettiğini denetler
  (`record=False`, yalnız dev_train).
- Kaldıraç yok. Spot pozisyonlar 0…1, vadeli pozisyonlar −1…1 aralığında. Bacak ağırlıkları
  eşit ve toplamları 1: tek coin carry'de 0,5/0,5, üç coinlik sepette her bacak 1/6.

### Nedensellik ve veri ayrıntıları

- Bir fonlama kaydı, zaman damgası barın **açılış** zamanına eşit ya da ondan önceyse
  kullanılır. Bu, "kapanış zamanından önce" şartından daha sıkıdır. BTC/ETH kayıtları
  00/08/16 UTC'dedir, bu yüzden 1s ve 4s barlarda iki şart aynı sonucu verir. Günlük barlarda
  08:00 ve 16:00 kayıtları bir gün gecikmeyle kullanılır.
- Fonlama özelliği: son `n` gündeki fonlama kayıtlarının toplamı / (3n), yani 8 saatlik
  eşdeğer ortalama oran. Pencere zamana dayalıdır, çünkü SOL'un fonlama aralığı 9–18 Kasım
  2022'de 2 saate inmişti. İlk `n` gün değer üretilmez.
- Coinin ilk fonlama kaydından önce hiçbir bacakta pozisyon açılmaz. BTC/ETH için bu 2020-01-01,
  SOL için 2020-09-13'tür. Böylece fonlamasız vadeli günler ve korumasız spot kullanılmadı.
- Carry'de iki bacağın sinyali, spot ve vadeli bar indekslerinin birleşimi üzerinde hesaplanır.
  SOL vadeli 4s verisinde eğitim döneminde 30 eksik bar vardır (1s'de 120).

## 2. Denenen yaklaşımlar ve parametre aralıkları

Eşikler 8 saatlik eşdeğer fonlama oranıdır. 1e-4 = %0,01 / 8 saat ≈ yıllık %10,95.

**A) Nakit-carry (`kind="carry"`).** Her coinde spot uzun + vadeli kısa. `n` günlük ortalama
fonlama `giris` eşiğini geçince girilir. `cikis` eşiğinin altına inince çıkılır. `son_neg`
açıksa, son yayımlanan kayıt negatif olunca da çıkılır. `n=0`, ilk fonlama kaydından sonra
sürekli pozisyon demektir.
- 1. aşama (`tarama1.py`, 4s): evren {BTC, ETH, SOL, 3'lü sepet} × [sürekli + n ∈ {1, 3, 7, 14}
  × (giriş, çıkış) ∈ {(0, 0), (1e-4, 0), (1e-4, 5e-5), (2e-4, 0), (2e-4, 1e-4), (3e-4, 1e-4)}
  × son_neg ∈ {hayır, evet}] = **196** yapılandırma.
- 2. aşama (`tarama2.py`). Binance fonlaması çoğu zaman tam %0,01'dir, yani 1e-4'te bir kütle
  noktası vardır. 1e-4'e eşit bir eşik ortalamanın kayan nokta gürültüsüne bağlı kalır. Bu
  yüzden eşikler bu noktadan uzaklaştırıldı: n ∈ {1, 3, 7} × (giriş, çıkış) ∈ {(0,5e-4, 0),
  (0,5e-4, −0,5e-4), (0,9e-4, 0), (0,9e-4, 0,5e-4), (1,5e-4, 0,5e-4)}, 4 evren = **60**. Ayrıca
  aralık kontrolü (sepet, 1s ve 1d) = **4**.
- 3. aşama (`tarama3.py`): sepette 1d bar, `son_neg` açık ve SOL'suz BTC+ETH sepeti, eşik
  (1,5e-4, 0,5e-4), n ∈ {1, 3} = **6**.

**B) Fonlama uçlarından yönlü sinyal (`kind="yonlu"`, yalnız vadeli; `tarama2.py`).** Evren
{BTC, ETH, 3'lü vadeli sepet}, 4s. n ∈ {1, 3}, filtre ∈ {yok, ile}, tutma ∈ {2, 7} gün. `ile`
filtresinde uzun yalnız kapanış 100 günlük SMA'nın üstündeyken, kısa yalnız altındayken açılır.
Her biri için:
- kalabalık kısa → uzun: ortalama fonlama < alt, alt ∈ {0, −0,5e-4};
- kalabalık uzun → kısa: ortalama fonlama > üst, üst ∈ {3e-4, 6e-4};
- yüzdelik sıra, iki yön: son 180 günlük kayıtlar içindeki sıra < 0,1 ise uzun, > 0,9 ise kısa.

Toplam 3 × 2 × 2 × 2 × 5 = **120** yapılandırma.

**C) Kaplama (`kind="kaplama"`, `tarama3.py`).** Spot hep uzun. Vadeli bacak fonlama yüksekken
−1 (nötr carry), değilken `uzun_poz` ∈ {0, 1}. İsteğe bağlı trend filtresi: kapanış 100 günlük
SMA'nın altındaysa da vadeli −1, yani düşüş trendinde nakit yerine carry tutulur. Evren {BTC,
ETH, sepet}, n=3, koruma eşiği ∈ {3e-4, 5e-4} (çıkış 1,5e-4), filtre ∈ {yok, trend}. Ayrıca
kontrol olarak fonlama korumasız, yalnız trend varyantı. Toplam 24 + 6 = **30**.

## 3. Deneme sayısı

| | Sayı |
|---|---|
| dev_train'de değerlendirilen benzersiz yapılandırma | **416** (196 + 64 + 120 + 6 + 30) |
| Defterde `pencere=="dev_train"` ve `maliyet_kat==1.0` satırı | **420** (416 + dondurulan 4'ün son değerlendirmesindeki tekrar satırları) |
| dev_valid'de değerlendirilen yapılandırma | **4** |

Deflated Sharpe için görevde istenen sayı (420) kullanıldı. 404 satırın Sharpe değeri
sonludur. 16 yapılandırmada hiç işlem yoktu, Sharpe'ları NaN'dır. Bunlar sayıya dahil,
varyansa dahil değildir. Yıllık Sharpe varyansı 5,784'tür, ortalaması 2,927, en büyüğü 6,703.
Buna göre şansla beklenen en büyük yıllık Sharpe (SR0) **7,21**'dir (`dsr.py`).

## 4. dev_train sonuçları (1× maliyet)

**Önemli not:** Spot verisi 2017-08'de başladığı için dev_train penceresi 2017-08-17'de açılır.
Carry ve kaplama ise ancak 2020'den sonra pozisyon alabilir. Bu yüzden aradaki sıfır getirili
günler yıllık getiriyi (CAGR) ve Sharpe'ı düşürür. Örneğin hızlı sepet carry'nin araç CAGR'ı
%3,73'tür. Aynı toplam getiri 2020–2023 için yıllıklandırılırsa %6,0 olur.

### 4.1 Gruplara göre özet

Tam liste `ozet_dev_train.csv` dosyasındadır. Burada temsilî gruplar var.

| Grup | Evren | n | Net > 0 | Sharpe min / medyan / maks | 2×'te net > 0 | Maks. DD medyanı |
|---|---|---|---|---|---|---|
| Carry sürekli (4s) | BTC | 1 | 1 | 6,70 | 1 | −%1,4 |
| Carry sürekli (4s) | ETH | 1 | 1 | 6,40 | 1 | −%1,3 |
| Carry sürekli (4s) | SOL | 1 | 0 | −0,10 | 0 | −%27,6 |
| Carry sürekli (4s/1s/1d) | Sepet | 3 | 3 | 0,89 / 0,99 / 1,05 | 3 | −%10,1 |
| Carry, giriş > 1e-4 | BTC | 7 | 7 | 5,01 / 5,23 / 5,69 | 7 | −%1,0 |
| Carry, giriş > 1e-4 | ETH | 7 | 7 | 5,54 / 5,59 / 5,73 | 7 | −%0,8 |
| Carry, giriş > 1e-4 | SOL | 7 | 7 | 4,10 / 4,51 / 4,66 | 7 | −%0,8 |
| Carry, giriş > 1e-4 | Sepet | 9 | 9 | 5,31 / 5,56 / 5,68 | 9 | −%0,8 |
| Carry, giriş > 1e-4 | BTC+ETH sepeti | 2 | 2 | 5,73 / 5,88 / 6,03 | 2 | −%0,8 |
| Carry, eşik tam 1e-4 (kütle noktası) | Sepet | 16 | 16 | 3,62 / 5,26 / 6,23 | 16 | −%0,8 |
| Carry, giriş < 1e-4 | Sepet | 14 | 14 | 1,61 / 3,23 / 5,01 | 12 | −%1,8 |
| Carry, giriş < 1e-4 | SOL | 12 | 12 | 0,34 / 1,17 / 1,68 | 8 | −%4,7 |
| Carry, giriş 0 + son kayıt negatifse çık | 4 evren | 16 | 0 | −1,76 … −0,21 | 0 | −%19…−%26 |
| Yönlü: negatif fonlamada uzun, filtre yok | BTC | 8 | 8 | 0,48 / 1,09 / 1,39 | 8 | −%24,7 |
| Yönlü: negatif fonlamada uzun, filtre yok | ETH | 8 | 7 | 0,19 / 0,42 / 0,83 | 5 | −%57,4 |
| Yönlü: negatif fonlamada uzun, filtre yok | Sepet | 8 | 8 | 0,71 / 0,88 / 1,04 | 8 | −%53,1 |
| Yönlü: negatif fonlamada uzun, trend ile | Sepet | 8 | 8 | 0,47 / 0,65 / 0,83 | 8 | −%30,3 |
| Yönlü: yüksek fonlamada kısa, filtre yok | BTC | 8 | 1 | −0,30 / 0,00 / 0,26 | 1 | −%57,6 |
| Yönlü: yüksek fonlamada kısa, filtre yok | ETH | 8 | 0 | −0,97 / −0,73 / −0,65 | 0 | −%89,5 |
| Yönlü: yüksek fonlamada kısa, filtre yok | Sepet | 8 | 0 | −1,56 / −1,09 / −0,89 | 0 | −%85,3 |
| Yönlü: yüzdelik iki yön, trend ile | BTC | 4 | 4 | 0,99 / 1,46 / 1,61 | 4 | −%14,6 |
| Yönlü: yüzdelik iki yön, trend ile | ETH | 4 | 1 | −0,21 / 0,02 / 0,42 | 1 | −%50,3 |
| Kaplama, trend, uzun_poz 0 | BTC / ETH / Sepet | 2 / 2 / 2 | hepsi | 1,27 / 0,70 / 1,00 (medyan) | hepsi | −%17,7 / −%34,5 / −%34,1 |
| Kaplama kontrolü (yalnız trend, fonlama koruması yok) | BTC / ETH / Sepet | 2 / 2 / 2 | hepsi | 1,02 / 0,81 / 1,25 (medyan) | hepsi | −%32,8 / −%58,7 / −%46,8 |

Eğitim dönemi al-tut (aynı pencere, `al_tut.py`):

| | Net getiri | Sharpe | Maks. DD |
|---|---|---|---|
| BTC spot (2017-08'den) | +%885,53 | 0,86 | −%83,20 |
| ETH spot | +%654,65 | 0,81 | −%93,97 |
| SOL spot (2020-08'den) | +%2980,57 | 1,42 | −%96,27 |
| BTC/ETH/SOL spot eşit ağırlık | +%3089,15 | 1,12 | −%85,46 |
| BTC vadeli uzun, fonlama dahil (2020-01'den) | +%221,40 | 0,78 | −%79,07 |
| BTC/ETH/SOL vadeli uzun eşit ağırlık, fonlama dahil | +%1514,33 | 1,28 | −%85,55 |

### 4.2 Eğitim döneminde görülenler

1. **Carry'nin getirisi fonlamadan geliyor, fiyattan değil.** BTC sürekli carry 2020–2023'te
   +%34,25 kazandı. Ayrıştırma (`ayristirma1.txt`, aritmetik toplamlar): alınan fonlama +%29,95,
   fiyat/baz −%0,35, maliyet −%0,10. Spot ve vadeli bacakların fiyat getirileri birbirini
   götürdü (+%132,6 ve −%132,95). Eşikli varyantlarda fiyat/baz katkısı −%0,02…+%1,45, maliyet
   %1,1–5,2 arasındaydı.
2. **Getiri yıllara çok dengesiz dağıldı.** Hızlı sepet carry 2020'de +%6,54, 2021'de
   +%16,81, 2022'de +%0,02, 2023'te +%1,46 kazandı. BTC sürekli carry 2020'de +%8,56, 2021'de
   +%16,58, 2022'de +%2,11, 2023'te +%3,89 kazandı. Fonlama boğa piyasasında yüksektir. 2022
   ayı piyasasında eşikli carry neredeyse hiç pozisyon almadı.
3. **SOL sürekli carry zarar etti.** −%6,54, en büyük düşüş −%27,6. 2022'de SOL fonlaması
   uzun süre negatifti: yıllık ortalama −%35,6, kayıtların %45,8'i negatif. Kasım 2022'de 2
   saatlik kayıtlarda oran −%2'ye kadar indi. Kısa vadeli bacak bu dönemde fonlama ödedi.
   Fonlama eşikli çıkış bu riski eğitimde önledi: eşikli SOL varyantlarının hepsi kârdaydı.
4. **Düşük eşik ve "son kayıt negatifse çık" kuralı ciroyu patlatıyor.** Giriş 0 ve son kayıt
   kuralıyla 4 yılda 288–1299 işlem oldu. Bu varyantların hepsi zarar etti (−%1,8…−%13,5). Sepet
   carry'de bir gidiş-dönüş, sermayenin yaklaşık %0,19'u kadar maliyettir (0,5 × %0,24 +
   0,5 × %0,14). Taban fonlamayla bu maliyet ancak yaklaşık 13 günde geri kazanılır.
5. **Bar aralığı az etkili.** Sepet n=3, (0,5e-4, 0) için Sharpe 4s'de 3,23, 1s'de 2,84,
   1d'de 5,01 oldu. Fark, fazla işlemin maliyetinden ve SOL vadeli verisindeki eksik barlardan
   geliyor (bkz. §8). (1,5e-4, 0,5e-4) eşiğinde 4s ve 1d neredeyse aynıydı: 5,56 / 5,31 ve
   5,62 / 5,51.
6. **Yönlü fonlama sinyalleri coinden coine tutarsız.**
   - Fonlama yüksekken açığa satış eğitimde bütün coinlerde kaybettirdi (ETH −%65…−%93, sepet
     −%70…−%90). Bu sırada +%20…+%56 fonlama alınmıştı. Yüksek fonlama, 2020–2021 boğa
     piyasasında tepe işareti değildi.
   - Negatif fonlamada uzun, BTC'de iyi göründü (Sharpe 0,48–1,39), ETH'de zayıftı
     (0,19–0,83). Sepette 0,71–1,04 ile tutarlıydı, ama Sharpe vadeli sepet al-tutun (1,28)
     altında kaldı ve düşüşler derindi (−%33…−%76).
7. **Kaplama, fonlamanın uzun pozisyonu iyileştirdiğini göstermedi.** Fonlama korumalı ve
   trend filtreli varyant BTC'de kontrolden iyiydi (Sharpe 1,34'e karşı 1,08). ETH'de (0,66'ya
   karşı 0,86) ve sepette (0,98'e karşı 1,29) kontrolden kötüydü.

## 5. Dondurulan yapılandırmalar ve seçim gerekçesi

Seçim yalnız dev_train sonuçlarıyla, dev_valid'e bakılmadan yapıldı. Ölçütler şunlardı:
- Komşu parametrelerin de iyi olduğu düz bir bölge.
- 2× maliyette Sharpe'ın korunması.
- Eşiklerin 1e-4 kütle noktasından uzak olması.
- Yıllık işlem sayısından dev_valid'de en az 20 işlem beklenmesi. Bu bir carry için zordur.
- Yaklaşım çeşitliliği.

Beş yerine dört yapılandırma donduruldu.

| # | Ad | Parametreler | Seçim nedeni (dev_train) |
|---|---|---|---|
| 1 | `fonlama_carry_sepet3_hizli` | carry, sepet, 4s, n=1, giriş 1,5e-4, çıkış 0,5e-4 | Ana aday. (1,5e-4, 0,5e-4) bölgesi her evrende düz ve güçlüydü. Sepet Sharpe'ı n=1/3/7 için 5,56 / 5,62 / 5,53, 2×'te 4,77 / 5,03 / 5,15. Aynı bölgede en çok işlemi n=1 yaptı (aktif yıllarda 20–30), bu yüzden işlem şartını geçme olasılığı en yüksekti. |
| 2 | `fonlama_carry_sepet3_yavas_dusuk` | carry, sepet, 4s, n=7, giriş 0,5e-4, çıkış −0,5e-4 | Farklı bir yapı: taban fonlamada da pozisyonda kalır, yalnız 7 günlük ortalama negatife dönünce çıkar. Eğitimde en yüksek sepet getirisi (+%33,21). 2022'de de kârdaydı (+%1,47). Yılda 10–16 işlem. |
| 3 | `fonlama_carry_btc_surekli` | carry, BTC, 4s, sürekli | Referans: düz nakit-carry primi iç doğrulamada sürüyor mu? Tek işlemi 2020'deki giriştir, bu yüzden işlem sayısı şartını **yapısal olarak** geçemez. Bu baştan biliniyordu. |
| 4 | `fonlama_negatif_uzun_sepet3` | yönlü, vadeli sepet, 4s, n=1, alt −0,5e-4, tutma 2 gün, filtre yok | (b) hipotezinin en tutarlı temsilcisi. Sepette bütün 8 "negatif fonlamada uzun, filtre yok" varyantı kârlıydı (Sharpe 0,71–1,04). n=3 komşusu biraz daha yüksek Sharpe verdi (1,04), ama 2022 dışındaki yıllarda yalnız 9–11 işlem yaptı. Seçilen n=1 aynı yıllarda 18–26 işlem yaptı (Sharpe 0,99). |

## 6. Dondurulan yapılandırmalar: sonuçlar

### 6.1 dev_train (dönem başı 2017-08-17; carry pozisyonları 2020'den itibaren)

| # | Net getiri | CAGR (araç) | 2020–23 yıllık | Sharpe | Maks. DD | İşlem | 2× net | 2× Sharpe | Alınan fonlama | Maliyet | Fiyat/baz |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | +%26,30 | %3,73 | %6,0 | 5,56 | −%0,76 | 74 | +%23,49 | 4,77 | +%25,14 | %2,25 | +%0,48 |
| 2 | +%33,21 | %4,60 | %7,4 | 4,13 | −%1,41 | 52 | +%31,16 | 3,86 | +%29,78 | %1,55 | +%0,50 |
| 3 | +%34,25 | %4,73 | %7,6 | 6,70 | −%1,41 | 2 | +%34,12 | 6,65 | +%29,95 | %0,10 | −%0,35 |
| 4 | +%240,22 | %35,82 | — | 0,99 | −%42,32 | 135 | +%219,44 | 0,95 | +%19,88 | %6,30 | +%135,42 |

Fonlama, maliyet ve fiyat/baz sütunları ağırlıklı aritmetik toplamlardır (sermaye oranı).
4 numaranın penceresi 2020-01-01'de başlar, çünkü yalnız vadeli bacakları vardır.

### 6.2 dev_valid (01.01.2024 – 30.06.2025, 547 gün) — tek değerlendirme

| # | Net getiri | CAGR | Sharpe | Maks. DD | İşlem | Maruziyet | 2× net | 2× Sharpe | Alınan fonlama | Maliyet | Fiyat/baz |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **+%4,50** | %2,99 | 7,36 | −%0,15 | **12** | 0,35 | +%4,01 | 5,69 | +%4,73 | %0,48 | +%0,15 |
| 2 | **+%7,49** | %4,94 | 13,10 | −%0,12 | **2** | 1,00 | +%7,42 | 12,76 | +%7,25 | %0,06 | +%0,03 |
| 3 | **+%7,39** | %4,88 | 13,58 | −%0,11 | **0** | 1,00 | +%7,39 | 13,58 | +%7,07 | %0,00 | +%0,06 |
| 4 | **−%13,17** | −%9,00 | −0,68 | −%26,96 | 25 | 0,19 | −%14,18 | −0,74 | +%0,22 | %1,17 | −%11,92 |

Çeyreklere göre dev_valid net getirisi:

| # | 2024Ç1 | 2024Ç2 | 2024Ç3 | 2024Ç4 | 2025Ç1 | 2025Ç2 |
|---|---|---|---|---|---|---|
| 1 | +%2,98 | +%0,48 | %0,00 | +%0,98 | +%0,01 | %0,00 |
| 2 | +%3,08 | +%1,31 | +%0,54 | +%1,61 | +%0,40 | +%0,36 |
| 3 | +%2,80 | +%1,24 | +%0,45 | +%1,60 | +%0,65 | +%0,45 |
| 4 | %0,00 | %0,00 | +%4,00 | +%0,92 | −%16,39 | −%1,07 |

1 numaranın işlemleri: 2024Ç1'de 2, Ç2'de 4, Ç4'te 6. Bu yapılandırma 2024 yazında ve 2025'te
neredeyse hiç pozisyon almadı, çünkü fonlama 1,5e-4 eşiğinin altındaydı. 2 numara bütün dönem
boyunca pozisyondaydı, tek çıkış/giriş 2025Ç2'deydi. 4 numaranın kaybı büyük ölçüde SOL
bacağından geldi: fiyat −%17,2, ağırlıklı.

### 6.3 candidate_check

| # | Eğitim net > 0 | Doğr. net > 0 | Doğr. 2× net > 0 | Doğr. Sharpe ≥ 0,5 | Doğr. işlem ≥ 20 | **Aday** |
|---|---|---|---|---|---|---|
| 1 | evet | evet | evet | evet | **hayır (12)** | **hayır** |
| 2 | evet | evet | evet | evet | **hayır (2)** | **hayır** |
| 3 | evet | evet | evet | evet | **hayır (0)** | **hayır** |
| 4 | evet | **hayır** | **hayır** | **hayır** | evet (25) | **hayır** |

### 6.4 Deflated Sharpe

Hesap: deneme sayısı N = 420, yıllık Sharpe varyansı 5,784, SR0 = 7,21. Günlük getiri sayısı,
çarpıklık ve basıklık dev_valid `summarize` çıktısından alındı.

| # | dev_valid Sharpe | Çarpıklık | Basıklık | **DSR** | DSR (yalnız carry denemeleri, N=269, varyans 3,704, SR0=5,51) |
|---|---|---|---|---|---|
| 1 | 7,36 | 2,44 | 16,14 | **0,591** | 0,998 |
| 2 | 13,10 | 2,85 | 16,55 | **1,000** | 1,000 |
| 3 | 13,58 | 2,14 | 11,16 | **1,000** | 1,000 |
| 4 | −0,68 | −0,63 | 24,66 | **0,000** | 0,000 |

Yorum:
- Ailenin denemeleri iki farklı türü karıştırıyor: carry (Sharpe ~4–7, çok düşük oynaklık) ve
  yönlü stratejiler (Sharpe ~−1…1,6). Bu yüzden varyans ve SR0 yüksek çıktı. Sağdaki sütun
  bilgi içindir, protokolün istediği sayı soldakidir.
- Carry'nin 7–13 düzeyindeki Sharpe değerleri, %0,35–0,40 yıllık oynaklığın sonucudur. Aracın
  modellemediği uç riskler (bkz. §8) bu oynaklığa yansımaz. Sharpe'lar olağanüstü bir beceriyi
  değil, ölçülmeyen riski taşıyan bir primi gösteriyor.

## 7. Al-tut karşılaştırması (aynı pencereler)

| | dev_train net | dev_train Sharpe | dev_valid net | dev_valid Sharpe | dev_valid maks. DD |
|---|---|---|---|---|---|
| BTC spot | +%885,53 | 0,86 | +%153,40 | 1,47 | −%28,10 |
| ETH spot | +%654,65 | 0,81 | +%8,92 | 0,43 | −%63,75 |
| SOL spot | +%2980,57 | 1,42 | +%52,19 | 0,75 | −%59,77 |
| BTC/ETH/SOL spot eşit ağırlık | +%3089,15 | 1,12 | +%73,67 | 0,90 | −%49,07 |
| BTC vadeli uzun, fonlama dahil | +%221,40 | 0,78 | +%119,71 | 1,28 | −%33,02 |
| BTC/ETH/SOL vadeli uzun, fonlama dahil | +%1514,33 | 1,28 | +%50,83 | 0,75 | −%52,07 |
| Nakit (araçta faizsiz) | %0 | — | %0 | — | %0 |

Carry stratejileri al-tutun çok altında getiri verdi, ama fiyat riski neredeyse sıfırdı:
dev_valid'de en büyük düşüş %0,15'in altında kaldı, BTC al-tutta −%28,10. Yönlü strateji
(4) hem al-tuttan hem nakitten kötüydü.

## 8. Sınırlamalar ve araçla ilgili notlar

- **İşlem sayısı ve "en iyi işlem çıkınca" ölçüsü hedge'li bacaklara uygun değil.** Her bacağın
  aynı yöndeki dilimi ayrı işlem sayılır, yani bir carry girişi 2 işlemdir. "En iyi işlem
  çıkarılınca getiri" ölçüsü, korunan bacağın karşı işlemini çıkarmadan yalnız bir bacağı
  çıkarır. Örneğin 1 numaranın dev_train'de bu değeri −%36,63, 3 numaranınki −%83,04 çıkıyor.
  Bu sayılar anlamsızdır. Görülmemiş dönem Seviye 1 şartlarından biri bu ölçüdür.
- **Eksik barlar hedge'i geçici olarak bozuyor.** SOL vadeli verisinde eksik barlar vardır
  (eğitimde 4s'de 30, 1s'de 120), spotta da birkaç tane. Boşluk boyunca o bacağın getirisi
  boşluk öncesi tek bara yazılır, öteki bacak getirisini bar bar yazar. Toplam etki ikinci
  derecedir, ama günlük getiri ve düşüş ölçülerinde yapay dalgalanma doğar
  (`tani_sol.py`: 2022-02-26 ve 2022-04-01 boşlukları).
- **Bacakların tek tek yeniden dengelenmesi ücretsiz.** `combine()` bacakları her bar sabit
  ağırlığa dengeler ve bunun için maliyet düşmez. Gerçek bir carry'de fiyat yükseldikçe kısa
  vadeli bacağın teminatı azalır, spottan vadeli hesaba aktarım ve yeniden dengeleme gerekir.
  Örneğin dev_valid'de BTC +%153 yükseldi. Bu işlemlerin maliyeti ve teminat riski
  modellenmedi.
- **Uç riskler modellenmedi:** borsa ve karşı taraf riski, otomatik kaldıraç azaltma (ADL),
  USDT riski, fonlama tavanı ve aralık değişiklikleri. Ayrıca araç nakdi faizsiz sayar.
  2024–2025'te kısa vadeli dolar faizleri yıllık birkaç yüzde düzeyindeydi (araç dışı bilgi).
  Bu yüzden carry'nin nakde göre gerçek fazlası, tablodaki yıllık %3–5'ten daha küçüktür.
- **Eğitim penceresinin başı:** Spot verisi 2017'de, vadeli ve fonlama 2020'de başladığı için
  eğitim CAGR'ı ve Sharpe'ı sıfır günlerle seyreliyor (§4).
- **`assert_causal` ve fonlama:** Denetim, fonlama serisini kesim barının açılış zamanında
  keser. Kesim barının içinde kalan bir kaydı meşru olarak kapanışta kullanan strateji yanlışlıkla
  ileri bakışlı görünebilir. Örnekler: günlük barda 08:00/16:00 kayıtları, 4s barda SOL'un
  2 saatlik kayıtları. Bu aile kayıtları yalnız açılış zamanına kadar kullandığı için etkilenmedi.

## 9. Dürüst sonuç

- Protokole göre bu ailede **kârlı aday yok.**
- Ekonomik olarak ölçülen şey şudur: nakit-carry primi 2024 – Haziran 2025'te sürdü. Maliyet
  sonrası, nakde göre (faizsiz) yıllık yaklaşık %3–5 verdi ve fiyat riski çok düşüktü. Getirinin
  kaynağı fonlamaydı. Fiyat/baz katkısı sıfıra yakındı. Eşikli giriş/çıkış, sürekli carry'den
  daha iyi değildi: dev_valid'de +%4,50'ye karşı +%7,39–7,49. Eşikli versiyon, fonlamanın
  düştüğü 2024 yazı ve 2025'te pozisyon dışında kaldı.
- Carry, protokolün en az 20 işlem şartını yapısı gereği karşılamıyor. Aday listesine ancak
  bilerek ciro artırılarak girebilirdi. Bu, maliyeti artırır ve ekonomik mantığa aykırıdır;
  denenmedi.
- Fonlama uçlarına dayalı yönlü sinyaller (kalabalık kısa → uzun, kalabalık uzun → kısa) eğitimde
  tutarsızdı ve dondurulan temsilci iç doğrulamada %13,17 kaybetti. Fonlamanın tek başına
  yön tahmini için işe yaradığına dair kanıt bulunamadı.

## 10. Dosyalar

| Dosya | İçerik |
|---|---|
| `veri_kontrol.py`, `veri_kontrol2.py` | Fonlama ve bar verisi kontrolü (yalnız dev_train) |
| `mekanik_kontrol.py` | Pozisyon zamanlaması ve fonlama işareti kontrolü (§1'deki istisna) |
| `ortak.py`, `goster.py` | Tarama ve ayrıştırma yardımcıları |
| `tarama1.py`, `tarama2.py`, `tarama3.py` ve `.csv` / `.log` çıktıları | dev_train taramaları |
| `ayristirma1.py`–`ayristirma3.py`, `.txt` | dev_train yıllık döküm ve fonlama/fiyat/maliyet ayrıştırması |
| `tani_sol.py` | SOL carry düşüş tanısı (dev_train) |
| `ozet.py`, `ozet_dev_train.csv`, `ozet.txt` | Grup özeti |
| `nedensellik.py`, `nedensellik.txt` | assert_causal |
| `dogrulama.py`, `dogrulama.txt`, `dondurulmus_sonuclar.json` | Dondurulan yapılandırmaların tek değerlendirmesi |
| `dsr.py`, `dsr.txt`, `dsr.json` | Deflated Sharpe |
| `al_tut.py`, `al_tut.txt`, `al_tut_*.csv` | Al-tut karşılaştırması |
| `yeniden_uretim.py` | `specs()` yeniden üretim denetimi |
