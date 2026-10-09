# t2_konumlanma — çalışma notları

Tur 2, protokol sürüm 2 (`GRAFIK_ANALIZ_PROTOKOL=2`). Bu dosya planı ve
dondurma kararını **iç doğrulama (dev_valid) değerlendirmesinden önce** kayda
geçirir. Sonradan eklenen bölümler tarihleriyle ayrıca işaretlenir.

## 0. Okunanlar ve bir uyarı (9 Ekim 2026, arama başlamadan önce)

- Okundu: `docs/PROTOKOL_2.md`, `docs/PROTOKOL.md`, `arastirma/SONUC_1.md`,
  `arastirma/DENETIM_1.md`, `grafik_analiz/research/*.py`.
- `SONUC_1.md` tur 1'in görülmemiş dönem (01.07.2025–30.09.2026) sonucunu ve
  o dönemde eşit ağırlıklı BTC/ETH/SOL al-tutun düştüğünü içeriyor. Bu dönem
  sürüm 2'de iç doğrulamanın içinde. Bu bilgi bir yön tercihine (ör. kısa
  ağırlıklı strateji) sebep olmamalı. Önlem: seçim kuralı aşağıda, sonuç
  görülmeden önce mekanik olarak yazıldı ve yalnız eğitim (dev_train)
  ölçülerine bakıyor. Tur 1 ailelerinin raporları (iç doğrulamaları 2024–2025'i
  kapsadığı için) fikir seçiminde kullanılmadı.

## 1. Veri gözlemleri (yalnız eğitim dönemi, 31.12.2024 öncesi)

- Konumlanma ölçüleri: BTC 2020-09'dan, ETH ve SOL **2021-12'den** başlıyor
  (arşiv böyle). Eğitimde üç coin birlikte ~3 yıl, BTC tek başına ~4,3 yıl.
- `top_hesap_oran` / `top_pozisyon_oran` 2022'de büyük ölçüde boş (çeyrek
  bazında %69–100 eksik). `taker_oran` 2022 ilk yarısında eksik ve aykırı
  değerli (300'e kadar). `genel_oran` neredeyse tam. `oi` / `oi_usdt` tam ama
  bazı kayıtlar 0 (hatalı; NaN sayılacak).
- Prim endeksi mumları BTC/ETH 2020-01'den, SOL 2020-09'dan; eksiksiz.
- Taker alım oranı vadeli mumların `taker_buy_base / volume` alanından da
  hesaplanabiliyor (bar içinde tam, gecikmesiz); metrics'teki `taker_oran`
  yerine bu kullanılacak.

## 2. Nedensellik kuralları (kodda uygulanacak)

- t barının kararı: metrics kaydı zaman damgası ≤ bar kapanışı − 10 dakika
  olan son kayıt (5 dakikalık ölçümün kapsadığı aralık belirsiz olduğundan
  ihtiyat payı). Kayıt 2 saatten eskiyse değer yok sayılır.
- Metrics ve prim, `signal_fn` içinde `scope="dev"` ile yüklenip **verilen
  verinin son barının kapanışına kadar** açıkça kesilir (assert_causal'ın
  kesmesi bu verileri de keser).
- Prim mumu: aynı açılış zamanlı prim mumunun kapanışı (barla aynı anda
  kapanır).
- Bütün normalizasyonlar geriye dönük kayan pencerelerle (z-skor = (x −
  kayan ort.) / kayan std). Tam örneklem istatistiği yok.

## 3. Denenecek fikirler (plan)

Bütün stratejiler vadeli, BTC/ETH/SOL (çoğunlukla üç coinlik sepet, bacak
başına 1/3), 1s ve 4s. Pozisyon −1/0/+1 (kaldıraç yok).

1. **oi** — fiyat/açık pozisyon (OI) olayları. k barlık fiyat değişimi ve OI
   değişiminin z-skorları.
   - `tasfiye`: OI sert düşerken fiyat sert düştüyse uzun (uzun tasfiyesi
     sonrası tepki), fiyat sert yükseldiyse kısa (kısa kapatma sonrası sönme).
   - `birikim`: OI sert artarken fiyat yönünü izle (yeni pozisyonlar yönü
     taşır).
   - `ikisi`: ikisi birlikte.
   Olaydan sonra H bar tutulur.
2. **kalabalik** — genel hesapların uzun/kısa oranının (log) z-skoru aşırı
   yüksekse kısa, aşırı düşükse uzun (karşıt). Histerezisli çıkış.
3. **prim** — prim endeksinin (n bar ortalaması) z-skoru aşırı yüksekse kısa,
   aşırı düşükse uzun (karşıt).
4. **taker** — taker alım payının z-skoru (yön parametresi: izle / karşıt).
5. **fark** — en büyük hesapların pozisyon oranı ile genel oranın z-skor farkı
   (büyük hesapları izle). Veri 2022'de eksik olduğundan ikincil.
6. Gerekirse: fiyat trendi filtresi (`ile`: uzun yalnız fiyat > SMA iken,
   kısa yalnız altındayken), bileşik puan, limit emirli giriş.

Bütçe: en fazla ~400 yapılandırma (eğitimde 1× ve 2× maliyet).

## 4. Seçim kuralı (sonuçlardan önce yazıldı)

Yalnız eğitim (dev_train) sonuçlarına bakılır:

1. Uygunluk: eğitimde 2× maliyetle net getiri > 0; alfa > 0 ve alfa t ≥ 1,5
   (1×); en az 60 işlem; 1× Sharpe ≥ 0,5.
2. Sağlamlık: parametre komşuları da (aynı tür, bir parametre bir adım
   değişmiş) çoğunlukla pozitif alfalı olmalı; tek başına sivri tepe seçilmez.
3. Sıralama: alfa t (1×). Aynı türden en fazla 2; eğitim günlük getiri
   korelasyonu 0,70'ten küçük olmalı.
4. En fazla 5 yapılandırma dondurulur; her biri iç doğrulamada bir kez
   `evaluate(spec)` ile ölçülür, `candidate_check` uygulanır, `assert_causal`
   çalıştırılır.
5. Hiçbiri uygun değilse, eğitimde alfa t'si en yüksek (ve 1× net > 0) en
   fazla 3 yapılandırma "zayıf" notuyla dondurulur; böylece olumsuz sonuç da
   ölçülmüş olur.

## 5. Arama günlüğü

(aşağıda, arama ilerledikçe)

(Önceki araştırmacı arama günlüğünü bu bölüme yazamadan durduruldu; arama
sonuçları `egitim_sonuclari.jsonl` ve deney defterinde.)

## 6. Kesinti ve devam (9 Ekim 2026, 08:46 UTC)

- Önceki çalışma kullanıcı tarafından arama sırasında durduruldu. İç
  doğrulama (dev_valid) değerlendirmesi yapılmamıştı: defterde
  (`arastirma/tur2/deneyler/t2_konumlanma.jsonl`) 454 satır var, hepsi
  `pencere == "dev_train"` (227 yapılandırma × 1× ve 2× maliyet), hepsi
  protokol 2.
- `tara.py`'deki aşamaların (1, 2a, 2b, 3, 4) hepsi tamamlanmış:
  `egitim_sonuclari.jsonl`'deki 227 satır defterdeki 227 yapılandırmayla
  birebir aynı; yarım kalmış bir tarama yok. Tekrar çalıştırılan bir şey
  yok.
- Bu çalışma kaldığı yerden devam ediyor. Defterdeki satırlar deneme
  sayılır; silinmez, değiştirilmez. Dondurma kuralı (bölüm 4) aynen
  geçerli.
- Devam planı:
  1. Veri hizalama kontrolü (yalnız eğitim dönemi): konumlanma ölçülerinin
     zaman damgasının anlamını, 5 dakikalık mumlarla karşılaştırarak
     doğrula. "Kalabalık" sinyalinin çok güçlü eğitim sonucu (alfa t ≈ 4,5)
     bir zaman damgası kaymasından gelmemeli.
  2. Kalabalık sinyalinin coin/yıl/yön kırılımı (`egitim_ayrinti.py`,
     yalnız eğitim) ve fiyat taklidiyle (`fiyat` türü) ilişkisi.
  3. Gerekirse küçük ek taramalar (prim, oi, bileşik), sonra bölüm 4'teki
     kurala göre dondurma.

## 7. Önceki aramanın özeti ve kontroller (devam, 9 Ekim 2026, yalnız eğitim)

Önceki 227 yapılandırmanın eğitim sonuçları (`egitim_sonuclari.jsonl`):

- **kalabalık** (genel hesap uzun/kısa oranının z-skoru, karşıt): açık ara en
  güçlü. 1s, w=7 gün türevlerinde alfa ≈ +0,77…+0,88/yıl, alfa t ≈ 4,3–4,6,
  beta ≈ 0, 2× maliyette de büyük artı. Bütün komşular (w 3/7/14/30/90,
  c 0,5–2,0, cx 0/0,5, 1s ve 4s) pozitif alfalı (t 2,6–4,6).
- Gecikme dayanıklılığı (aşama 2a): ölçüm 30/60/120 dk (1s) ve 60/240 dk
  (4s) geç kullanılınca alfa t 4,38/4,32/4,00 ve 3,78/3,51. Sinyal birkaç
  dakikalık zaman damgası kaymasından gelmiyor.
- Hizalama kontrolü (`hizalama.py`, `hizalama.log`, yalnız eğitim): ölçümün
  taker oranı en çok [T−5dk, T) mumuyla (k = −1, korelasyon 0,65–0,77),
  kısmen [T, T+5dk) mumuyla (0,29–0,37) örtüşüyor. Yani T damgalı kayıt T'den
  biraz sonrasını da içeriyor; koddaki 10 dakikalık ihtiyat payı bunu
  karşılıyor.
- Kırılım (`egitim_ayrinti.py`, 1s w7 c1,0): sepet her yıl artı (2020 son
  çeyrek +%22, 2021 +%148, 2022 +%137, 2023 +%134, 2024 +%113). Üç coin de
  artı ve alfası pozitif (BTC +1,09, ETH +0,46, SOL +0,93); uzun ve kısa
  taraf ayrı ayrı pozitif alfalı.
- Fiyat taklidi (aşama 2b, fiyat z-skoru momentumu): alfa t 2,5–3,0,
  Sharpe 0,9–1,2 → kalabalık sinyali fiyat momentumundan daha fazlasını
  taşıyor, ama kısmen momentuma benziyor (perakende hesaplar yükselişte
  kısa açıyor).
- Diğerleri: oi/birikim (1s k8 t12) alfa t 3,69; bileşik 3,3; fark 3,0;
  taker (izle) 2,6; oi/tasfiye ve prim (karşıt) alfasız ya da negatif.

## 8. Aşama 5 planı (çalıştırmadan önce yazıldı)

Küçük, son bir ek tarama (≈20 yapılandırma, yalnız eğitim, 1× ve 2×):

1. **Limit emir** (kalabalık 1s w7 c0,5/cx0,5 ve c1,0/cx0,0; 4s w7 c1,0/cx0,0):
   hedef değiştiği bardan sonra `limit_bar` (1 ya da 2) bar boyunca
   kararın verildiği barın kapanış fiyatından limit emir; dolmazsa piyasa
   emri. Amaç maliyeti düşürmek. 6 yapılandırma.
2. **Prim, izle yönü** (`isaret=+1`; aşama 1 yalnız karşıtı denedi): 1s
   n8/n24, 4s n2/n6 × w7/w30, c1,0. 8 yapılandırma.
3. **Kalabalık topluluğu**: w = 3, 7, 14 günlük üç kalabalık sinyalinin
   pozisyon ortalaması (c1,0, cx0,0), 1s ve 4s. 2 yapılandırma.
4. **Kalabalık + trend filtresi** (`ile`, 7 ve 30 gün SMA), 1s w7 c1,0.
   2 yapılandırma.

Bu aşamadan sonra arama biter; dondurma bölüm 4'teki kuralla yapılır.
"Fiyat" türü yalnız kontroldür (konumlanma verisi kullanmaz), dondurma
adayı sayılmaz.

## 9. Aşama 5 sonucu ve dondurma kuralının uygulanışı (seçimden önce yazıldı)

Aşama 5 (18 yapılandırma, `tara_5.log`):

- Limit emir kalabalık sinyalini çok az iyileştiriyor (1s w7 c0,5/cx0,5:
  1× +48,8 → alfa t 4,67; piyasa emriyle 4,56. 2× +14,5 / +9,5).
- Prim izle yönü: hepsi büyük zarar (alfa t −3,1…−0,1). Prim her iki yönde
  de işe yaramıyor.
- Kalabalık topluluğu (w 3-7-14): 1s alfa t 4,51, 4s 3,85.
- Trend filtresi (`ile`) kalabalık sinyalini zayıflatıyor (alfa t 3,31 /
  4,14; getiri çok daha düşük).

Arama burada biter. Toplam 245 yapılandırma (defterde 490 dev_train satırı).

Bölüm 4'teki kuralın mekanik uygulanışı (`dondurma.py`):

1. Uygunluk: eğitimde 2× net > 0; 1× alfa > 0 ve alfa t ≥ 1,5; işlem ≥ 60;
   1× Sharpe ≥ 0,5. `fiyat` (kontrol) türü aday değil.
2. Sağlamlık: aynı tür ve dilimde, tek bir parametresi farklı olan
   yapılandırmalar "komşu" sayılır. En az 2 komşu olmalı ve komşuların
   yarıdan fazlası pozitif alfalı olmalı.
3. Sıralama: 1× alfa t, büyükten küçüğe. Tür sınırında `kalabalik_top`
   kalabalık türünden sayılır (aynı fikir); limit emirli türevler de
   kendi türünden sayılır. Aynı türden en fazla 2.
4. Korelasyon: eğitim dönemi günlük net getirisi (1×), seçilmiş her
   yapılandırmayla < 0,70. Günlük getiriler yalnız 31.12.2024'e kadar
   kesilmiş veriyle hesaplanır (iç doğrulama verisi hiç kullanılmaz).
5. En fazla 5. Sıra boyunca açgözlü seçim.
6. Komşuluk karşılaştırmasında parametreler sinyal fonksiyonunun varsayılan
   değerleriyle tamamlanır (`yon=iki`, `trend_gun=0`, `filtre=yok`,
   `gecikme_dk=10`, `emir=piyasa`, `limit_bar=1`); böylece ör. limit emirli
   türevin komşusu aynı sinyalin piyasa emirli hâlidir.

## 10. Dondurma kararı (iç doğrulamadan ÖNCE, 09.10.2026 08:51 UTC)

`dondurma.py` → `dondurma.log`, `dondurma.json`. 245 yapılandırmadan 121'i
uygunluk ve sağlamlık şartını geçti. Alfa t sırasıyla açgözlü seçim (tür
başına en fazla 2, eğitim günlük getiri korelasyonu < 0,70):

| # | Yapılandırma | Eğitim 1× getiri | Sharpe | Alfa | Alfa t | Beta | İşlem | 2× getiri |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| D1 | kalabalik 1s, genel oran, w7, c0,5, cx0,5, karşıt, limit emir (1 bar) | +48,84 | 2,11 | +0,856 | 4,67 | +0,01 | 3132 | +14,53 |
| D2 | kalabalik 1s, genel oran, w30, c1,0, cx0, karşıt | +20,83 | 1,79 | +0,673 | 3,89 | +0,01 | 595 | +15,55 |
| D3 | oi 1s, birikim, k8, w30, a1,0, b1,5, 12 bar tut | +3,67 | 1,54 | +0,354 | 3,69 | −0,02 | 731 | +2,32 |
| D4 | fark 1s, w14, c0,5, cx0, büyük hesapları izle | +5,56 | 1,35 | +0,422 | 2,99 | +0,00 | 1374 | +2,45 |
| D5 | taker 4s, k12, w30, c2,0, izle | +3,55 | 1,11 | +0,374 | 2,62 | −0,02 | 368 | +2,84 |

(Getiriler kat olarak: +48,84 = %+4.884.) Eğitim günlük getiri
korelasyonları en fazla 0,591 (D1–D2). Beşi de `assert_causal`'ı varsayılan
(0,55/0,8/0,97) ve ek (0,3/0,65/0,9/0,99) kesimlerde geçti
(`nedensellik.log`).

Uyarılar (sonuç görülmeden yazıldı):

- D1 çok işlem yapıyor (eğitimde 3132); 2× maliyette getiri üçte birine
  iniyor. Maliyete en duyarlı yapılandırma bu.
- D1–D2 aynı veriye (genel hesap oranı) dayanıyor; D4 de genel oranı
  kullanıyor. Bu ölçünün davranışı değişirse üçü birlikte bozulabilir.
- Eğitim sonuçları olağanüstü yüksek. 245 denemenin en iyisi seçildiği için
  iç doğrulamada belirgin bir düşüş beklenmeli.

Her biri `dogrulama.py` ile bir kez `evaluate(spec)` (eğitim + iç doğrulama,
1× ve 2×) ile ölçülecek, `candidate_check` uygulanacak. Sonuç ne olursa olsun
parametre değişmeyecek.

## 11. İç doğrulama sonucu (dondurmadan SONRA, 09.10.2026 08:52 UTC)

`dogrulama.py` bir kez çalıştırıldı (`dogrulama.log`,
`dondurulmus_sonuclar.json`). Defter: 5 yapılandırma × (eğitim + iç
doğrulama) × (1×, 2×) = 20 yeni satır; toplam 510.

| # | dev_valid 1× | 2× | Sharpe | Alfa | Alfa t | candidate_check |
|---|---:|---:|---:|---:|---:|---|
| D1 | %−23,3 | %−58,2 | −0,11 | −0,055 | −0,16 | geçmedi |
| D2 | %+24,2 | %+5,9 | 0,503 | +0,210 | +0,67 | **geçti (sınırda)** |
| D3 | %+6,4 | %−11,0 | 0,28 | +0,051 | +0,35 | geçmedi |
| D4 | %−30,4 | %−54,4 | −0,21 | −0,096 | −0,27 | geçmedi |
| D5 | %−3,9 | %−10,4 | 0,01 | −0,002 | −0,01 | geçmedi |

Dondurmadan sonra yapılan değişiklikler: yalnız `specs()` açıklamalarına
candidate_check sonucu yazıldı (parametre ve kod mantığı değişmedi;
`evaluate(..., record=False)` ile 5 spec'in bütün sayıları farksız yeniden
üretildi). Betimleyici tanı `dogrulama_tani.py` (deftere yazmaz). Yeni arama
ya da yeniden ayar yapılmadı.
