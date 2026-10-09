# t2_lead_lag — Öncü–izleyen (lead–lag) ilişkileri (protokol sürüm 2)

Tarih: 9 Ekim 2026. Piyasa: Binance USDⓈ-M vadeli (iki yön, fonlama dahil). Coinler: BTC, ETH, SOL.
Kod: `grafik_analiz/strategies/t2_lead_lag.py`. Deney defteri: `arastirma/tur2/deneyler/t2_lead_lag.jsonl`.
Çalışma notları ve dondurma kararı: `NOTLAR.md`. Dondurma kararı dev_valid değerlendirmesinden
önce yazıldı (NOTLAR 16:41 UTC, ilk dev_valid satırı 16:43 UTC).

## 0. Kısa sonuç

- 361 benzersiz yapılandırma denendi. Arama yalnız eğitim döneminde (dev_train, ≤ 31.12.2024) yapıldı.
- **Asıl soru olumsuz çıktı.** BTC'nin son 5–15 dakikalık hareketinden sonra ETH/SOL'ün "yetişmesi"
  maliyetten sonra kâr etmiyor. Yetişme ve lider yönü sinyallerinin 38 yapılandırmasının hepsi
  eğitimde zararda (alfa negatif). Limit emir bunu değiştirmiyor. Ters yön (ETH/SOL → BTC) ve prim
  endeksi (1h) de zararda.
- Eğitimde tutarlı çıkan tek mekanizma **spot–vadeli ayrışması**. Vadeli fiyat spota göre olağan
  dışı iskontoya düştüğünde (baz z-skoru) ya da spot son dakikalarda vadeliden belirgin daha çok
  yükseldiğinde vadeliyi almak eğitimde kâr etti. Kâr çoğunlukla likidasyon dalgalarındaki
  uzun işlemlerden geliyor. Beta ≈ 0.
- 5 yapılandırma donduruldu ve iç doğrulamada (dev_valid) bir kez ölçüldü:
  - **3'ü `candidate_check`'i geçti:** baz 5m iki yön (#1), baz 5m üç-coin yalnız uzun (#4),
    spot öncülüğü 5m yalnız uzun (#5). Net 1×: +%16,57 / +%19,81 / +%17,19; 2×: +%14,55 / +%18,90 / +%16,73.
  - **2'si geçmedi:** baz 15m iki yön (#2, −%8,72) ve spot öncülüğü iki yön (#3, −%0,76).
- Geçen adayların kanıtı zayıf:
  - Alfa t-değerleri 1,489–1,642: anlamlı değil.
  - Deflated Sharpe < 0,0001 (366 deneme satırı, 361 benzersiz). Varyans yalnız baz/spot_vadeli denemelerinden
    alınsa bile 0,0036–0,0120.
  - Kâr az sayıda olaya dayanıyor. En iyi 10 işlem çıkarılınca #1 −%3,06, #4 +%0,89, #5 +%0,77.
    #5'in 21 ayda yalnız 9 işlem günü var.
  - Üçü aynı olaylardan besleniyor. Günlük korelasyon 0,69–0,91.
  - Yalnız uzun sürümler ani düşüşte alım yapıyor. 10.10.2025'te bir 5 dakikalık barda
    portföy yaklaşık −%11,2 değer kaybetti, sonra toparlandı. Düşüş devam etseydi zarar büyük olurdu.

## 1. Kesinti ve devam

- Bu ailenin araştırması iki kez kesildi. İki kesinti de dev_valid'e bakılmadan önceydi.
  - İlk kesinti 09:09 UTC civarında kullanım sınırıyla oldu. O sırada defter yoktu; yalnız
    tanılama (Aşama 0) ve modül vardı.
  - İkinci kesinti 11:54 UTC'den sonra oldu. O sırada Aşama 1'in 3 taraması bitmişti
    (defterde 144 dev_train satırı).
- Çalışma iki kez de kaldığı yerden sürdü. Ayrıntı: `NOTLAR.md` → "Kesinti ve devam",
  "Kesinti ve devam (2)".
- `ortak.tara`, defterde aynı adla ölçülmüş yapılandırmayı yeniden çalıştırmaz. Yinelenen deneme
  satırı oluşmadı. Eski satırlar silinmedi, değiştirilmedi ve deneme sayısına dahil edildi.

## 2. Veri, hizalama, nedensellik

- İşlem bacakları vadeli 5m/15m/1h mumlarıdır. Spot mumları ve prim endeksi `signal_fn` içinde
  `research.data` yükleyicileriyle (`scope="dev"`) yüklenir. Sonra geçirilen verinin son bar
  kapanışına kesilir; böylece `assert_causal`'ın kesimi bunları da keser.
- Diğer serilerin kapanışları işlem bacağının açılış zamanlarına eşlenir. Getiri bu eşlemeden
  sonra alınır; eksik barda sinyal yoktur.
- Bir bacak t barında yalnız t'de ve öncesinde kapanmış barları kullanır. Bütün istatistikler
  `shift(1)`'li kayan pencerelerdir.
- Dondurulan 5 yapılandırma `assert_causal`'ı varsayılan (0,55/0,8/0,97) ve ek (0,3/0,62/0,9)
  kesimlerle geçti (`nedensellik.log`).

## 3. Denenen yaklaşımlar (yalnız dev_train)

Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0,))` ile ölçüldü.
Seçilenler ayrıca 2× maliyetle ölçüldü. BTC/ETH/SOL üç bacaklı yapılandırmalarda bacak başına
sermaye 1/3'tür.

Sinyal türleri:

- `yetis`: izleyenin (ETH/SOL) kayan betayla BTC'ye göre artığı. İzleyen geride kaldıysa liderin
  yönünde alınır.
- `lider`: BTC'nin son k barlık z-skoru yönünde (ya da tersine) ETH/SOL.
- `spot_vadeli` (sv): son k barda spot getirisi − vadeli getirisi, kayan std'ye göre z. Spot
  vadeliden çok yükseldiyse vadeli uzun. Kaynak seçenekleri: coinin kendisi, BTC ya da üç coinin
  ortalaması ("hepsi").
- `baz`: vadeli/spot log fiyat farkının kayan z-skoru. Vadeli iskontodaysa uzun, primdeyse kısa.
- `prim`: Binance prim endeksi (1h) z-skoru, ters yönde.
- Pozisyon son tetikten sonra `tut` bar tutulur.

| Tarama | Fikir | Parametre aralıkları | Yeni yapılandırma | Net > 0 | En iyi eğitim sonucu (Sharpe'a göre, 1×) |
|---|---|---|---:|---:|---|
| 1 | sv, piyasa emri | 15m k 1; 5m k 1/3; kaynak kendi/BTC/hepsi; eşik 3/4/5; tutma 15m 2/4/12, 5m 6/12/36 | 81 | 26 | `sv_5m_hepsi_k3_e5_t12`: +%114,46, Sharpe 1,119 |
| 2 | prim 1h; sv 1h; baz 15m/1h | prim: pencere 24/168, eşik 2/3, tutma 4/8/24; sv 1h: kendi/hepsi, eşik 3/4, tutma 2/6; baz: 5 yapılandırma | 25 | 8 | `baz_15m_kendi_w96_e4_t8`: +%138,67, Sharpe 0,910 |
| 3 | yetis, lider (ETH/SOL ← BTC), limitli yetis | 5m k 1/3, 15m k 1; eşik 3/4; lider eşiği yok/3; tutma 3/12 ve 2/6; lider yon ±1; limit 0/3 bps | 38 | 0 | En iyi net: `yetis_15m_k1_e4_l3_t2` −%34,42 (Sharpe −0,741); en iyi Sharpe: `lider_15m_k2_e4_t6_y-1` −0,456 (net −%55,69) |
| 4 | baz ızgarası | 15m: pencere 48/96/192, eşik 3,5/4/5, tutma 4/8/16; 5m: pencere 288, eşik 4/5/6, tutma 12/24/48; 1h: pencere 24/48, eşik 3/4, tutma 4/8; kaynak kendi/hepsi | 87 | 84 | `baz_15m_kendi_w192_e5_t4`: +%141,85, Sharpe 1,297 |
| 5 | sv "hepsi" komşuluğu | 5m: k 2/3/4/6, eşik 4/4,5/5/6, tutma 6/12/36/72; pencere 576 (4); 15m: k 2/3, eşik 4/5, tutma 4/12 | 70 | 69 | `sv_5m_hepsi_k6_e4.5_t72`: +%176,69, Sharpe 1,373 |
| 6 | 5 temel yapılandırmada limit emir ve yalnız uzun | limit: çıkışta 0 bps (dönüşsüz / 3 bar), her değişimde 0 bps 1 bar, 2 bps 2 bar, girişte 0 bps 1 bar; `taraf="uzun"` | 35 | 35 | `baz_5m_hepsi_w288_e5_t12_uzun`: +%135,31, Sharpe 1,626 |
| 7 | BTC bazı → ETH/SOL vadeli | 5m pencere 288 eşik 5/6; 15m pencere 192/96 | 4 | 4 | `baz_15m_BTCkaynak_iz_w192_e5_t8`: +%191,67, Sharpe 0,969 |
| 9 | Yalnız uzun komşuluğu, uzun + limit | baz 5m kendi/hepsi eşik 4/5/6 tutma 12/48; sv 5m hepsi k 3/6 eşik 4/5 tutma 12/36; 4 uzun+limit | 21 | 21 | `baz_5m_hepsi_w288_e4_t48_uzun`: +%245,42, Sharpe 1,720 |
| 8, 10 | 2× maliyet | 17 seçilmiş yapılandırma | (2×) | 17/17 | — |

Toplam 361 benzersiz yapılandırma ve 361 dev_train 1× satırı. 2× maliyet için 17 satır var.
dev_valid değerlendirmesi dondurulan 5 yapılandırmanın dev_train satırlarını bir kez daha yazdı.
Bu yüzden defterde 366 dev_train 1× satırı var.

Türlere göre özet (dev_train 1×, bütün taramalar):

| Tür | Kaynak | Zaman dilimi | Yapılandırma | Net > 0 | Alfa > 0 | Medyan Sharpe | Medyan beta |
|---|---|---|---:|---:|---:|---:|---:|
| yetis | — | 5m / 15m | 20 / 10 | %0 / %0 | %0 / %0 | −1,995 / −1,747 | +0,006 / +0,014 |
| lider | — | 5m / 15m | 4 / 4 | %0 / %0 | %0 / %0 | −3,154 / −1,460 | +0,010 / +0,004 |
| prim | — | 1h | 12 | %0 | %0 | −0,335 | +0,044 |
| sv | kendi | 5m / 15m / 1h | 18 / 9 / 4 | %5,6 / %0 / %75 | %11,1 / %0 / %100 | −0,543 / −0,982 / +0,419 | +0,003 / +0,014 / −0,016 |
| sv | BTC | 5m / 15m | 18 / 9 | %27,8 / %55,6 | %44,4 / %66,7 | −0,329 / +0,118 | −0,036 / −0,003 |
| sv | hepsi | 5m / 15m / 1h | 102 / 17 / 4 | %91,2 / %76,5 / %75 | %94,1 / %76,5 / %75 | +1,140 / +0,342 / +0,296 | −0,019 / −0,010 / −0,005 |
| baz | kendi | 5m / 15m / 1h | 22 / 36 / 11 | %100 / %100 / %72,7 | %100 / %100 / %81,8 | +1,292 / +0,946 / +0,468 | −0,009 / −0,012 / −0,021 |
| baz | hepsi | 5m / 15m / 1h | 22 / 27 / 8 | %100 / %100 / %62,5 | %100 / %100 / %62,5 | +1,189 / +0,679 / +0,255 | −0,022 / −0,035 / −0,013 |
| baz | BTC → ETH/SOL | 5m / 15m | 2 / 2 | %100 / %100 | %100 / %100 | +0,465 / +0,789 | −0,026 / −0,041 |

### Aşama 0 tanılaması (maliyetsiz, bps; strateji sonucu değil)

- BTC → ETH/SOL artık yetişmesi (`tanilama1.txt`): 5m'de |z| > 3 olaylarında sonraki barda
  +1,90…+4,79 bps, 15m'de +2,58…+6,64 bps. Yıllara göre işaret değişiyor. Taker gidiş-dönüş
  maliyeti 14 bps.
- Büyük BTC hareketinden sonra ETH/SOL'ün yönü 5m'de ortalama negatif: kısa vadeli ters dönüş var,
  yetişme yok.
- Spot–vadeli farkı (`tanilama3.txt`, |z| > 4): 5m'de 12 bar sonra yaklaşık +10…+21 bps, 15m'de
  3–12 bar sonra BTC/ETH kaynağında yaklaşık +17…+55 bps (SOL kaynağında işaret yıllara göre
  değişiyor). Maliyeti aşabilecek tek coinler arası sinyal grubu buydu.

## 4. Ana varyantların eğitim sonuçları (dev_train, 1×, piyasa emri)

| Yapılandırma | Net | Sharpe | En büyük düşüş | İşlem | Alfa (yıllık) | Beta | Alfa t |
|---|---:|---:|---:|---:|---:|---:|---:|
| `yetis_5m_k1_e4_l3_t3` | −%51,89 | −1,170 | −%54,78 | 1068 | −0,147 | +0,007 | −2,76 |
| `lider_15m_k2_e4_t6_y-1` | −%55,69 | −0,456 | −%71,23 | 2001 | −0,102 | −0,021 | −0,83 |
| `prim_1h_w168_e3_t8` | −%19,55 | −0,060 | −%54,24 | 1082 | −0,075 | +0,052 | −0,70 |
| `sv_5m_kendi_k3_e5_t6` | +%7,28 | +0,194 | −%31,87 | 523 | +0,008 | +0,009 | +0,19 |
| `sv_5m_BTC_k3_e5_t36` | +%60,89 | +0,432 | −%32,11 | 650 | +0,211 | −0,065 | +1,50 |
| `sv_5m_hepsi_k3_e5_t12` | +%114,46 | +1,119 | −%15,43 | 249 | +0,192 | −0,027 | +3,00 |
| `sv_5m_hepsi_k4_e4_t12` | +%105,37 | +1,289 | −%15,12 | 297 | +0,172 | −0,020 | +3,33 |
| `sv_5m_hepsi_k6_e4_t36` | +%191,40 | +1,299 | −%15,67 | 198 | +0,258 | −0,027 | +3,31 |
| `baz_15m_kendi_w96_e4_t8` | +%138,67 | +0,910 | −%30,20 | 949 | +0,213 | −0,016 | +2,22 |
| `baz_15m_kendi_w192_e5_t8` | +%188,94 | +1,186 | −%20,73 | 448 | +0,253 | −0,022 | +2,94 |
| `baz_5m_kendi_w288_e6_t12` | +%100,28 | +1,296 | −%23,04 | 609 | +0,155 | −0,009 | +3,10 |
| `baz_5m_hepsi_w288_e5_t12` | +%128,27 | +1,183 | −%21,26 | 420 | +0,201 | −0,022 | +3,04 |
| `baz_1h_kendi_w48_e4_t4` | +%82,40 | +0,800 | −%14,11 | 385 | +0,167 | −0,031 | +2,29 |

Tablodaki değerler aşağı yuvarlandı (ihtiyatlı).

Eğitim içi inceleme (`inceleme1*.txt`, `inceleme2a/b/c.txt`; veri 31.12.2024'te kesilerek):

- baz ve sv "hepsi" yapılandırmalarında kâr ağırlıkla uzun işlemlerden geliyor.
  - Örnek `baz_5m_kendi_w288_e6_t12`: uzun 269 işlem +0,719, kısa 340 işlem −0,027 (portföy
    düzeyinde toplam).
  - 2021–2024'ün her yılı pozitif, 2020 ≈ 0. Kazançların en büyüğü 2021'de.
- En iyi işlemler likidasyon dalgalarına denk geliyor: 19.05.2021, 07.09.2021, 12.05.2022,
  08.11.2022, 03.01.2024. Dondurulanlarda en iyi 10 işlem çıkarılınca eğitim sonucu yine pozitif
  kalıyor (+%33,75 … +%68,41).
- Limit emir neti az değiştirdi ama maliyeti üçte birine indirdi. `limt2b2`: her değişimde 2 bps
  iyi fiyatla limit, 2 bar dolmazsa piyasa emri. 2× maliyet sonuçları bu yüzden iyileşti.

## 5. Dondurulan yapılandırmalar ve gerekçe

Hepsi BTC/ETH/SOL vadeli, bacak başına 1/3 sermaye, `limit_bps=2, limit_mod="tum", limit_bar=2`.
Tasarım: 2 sinyal türü × (iki yön / yalnız uzun), artı 15m'lik bir baz sürümü.

| # | Ad (`t2_lead_lag_` önekiyle) | Açıklama |
|---|---|---|
| 1 | `baz_5m_kendi_w288_e6_t12_limt2b2` | Coinin kendi bazı, 1 günlük z, \|z\| > 6, 1 saat tut, iki yön |
| 2 | `baz_15m_kendi_w192_e5_t8_limt2b2` | Coinin kendi bazı, 2 günlük z, \|z\| > 5, 2 saat tut, iki yön |
| 3 | `sv_5m_hepsi_k6_e4_t36_limt2b2` | Üç coinin 30 dakikalık spot−vadeli getiri farkı z ortalaması \|z\| > 4, 3 saat tut, iki yön |
| 4 | `baz_5m_hepsi_w288_e5_t12_uzun_limt2b2` | Üç coinin baz z ortalaması < −5 → üçüne uzun, 1 saat tut |
| 5 | `sv_5m_hepsi_k4_e4_t12_uzun_limt2b2` | Üç coinin 20 dakikalık spot−vadeli farkı z ortalaması > 4 → üçüne uzun, 1 saat tut |

Seçim gerekçesi (yalnız dev_train):

- Bölgeler komşulukta dayanıklıydı: komşuların hepsi pozitifti.
- 2021–2024'ün her yılı pozitif, 2× maliyette pozitif, alfa t > 2,9, beta ≈ 0.
- En yüksek tek sonuç yerine bölgenin ortasından seçildi.
- Yalnız uzun sürümleri, eğitimde kârın uzun taraftan geldiği gözlemine dayanıyor. Bu seçim de
  çoklu denemeye sayıldı.
- Hepsinin aynı olaylardan beslenmesi ve yüksek korelasyonlu olması bekleniyordu. Bu risk
  dondurmadan önce yazıldı.

## 6. İç doğrulama sonuçları (dev_valid: 01.01.2025 – 30.09.2026, 638 gün)

Her yapılandırma `evaluate(spec)` ile bir kez ölçüldü (`dogrulama.py`, `dogrulama_sonuc.json`).

| # | Eğitim net / alfa | Doğr. net 1× | Doğr. net 2× | Sharpe 1× | Sharpe 2× | En büyük düşüş | İşlem | Alfa (yıllık) | Beta | Alfa t | p (bootstrap) | Maruziyet | `candidate_check` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | +%98,39 / +0,154 | **+%16,57** | +%14,55 | 1,125 | 1,002 | −%10,11 | 113 | +0,089 | +0,026 | 1,489 | 0,0404 | %0,58 | **geçti** |
| 2 | +%183,09 / +0,249 | −%8,72 | −%9,76 | −0,722 | −0,812 | −%16,35 | 80 | −0,051 | +0,014 | −0,977 | 0,8264 | %0,90 | geçmedi (net, 2×, Sharpe, alfa) |
| 3 | +%193,18 / +0,259 | −%0,76 | −%1,42 | −0,005 | −0,047 | −%15,96 | 36 | −0,002 | +0,021 | −0,025 | 0,4744 | %0,19 | geçmedi (net, 2×, Sharpe, alfa) |
| 4 | +%137,14 / +0,198 | **+%19,81** | +%18,90 | 1,246 | 1,202 | −%14,23 | 48 | +0,106 | +0,010 | 1,642 | 0,0248 | %0,11 | **geçti** |
| 5 | +%152,96 / +0,230 | **+%17,19** | +%16,73 | 1,194 | 1,173 | −%14,65 | 27 | +0,093 | +0,009 | 1,573 | 0,0308 | %0,06 | **geçti** |

Diğer ölçüler (dev_valid, 1×):

| # | Yıllık getiri | Kazanan işlem | Kâr faktörü | Toplam maliyet | Fonlama |
|---|---:|---:|---:|---:|---:|
| 1 | %9,1 | %54,8 | 1,48 | 0,0176 | −0,0001 (alındı) |
| 2 | %−5,1 | %38,7 | 0,56 | 0,0115 | −0,0018 (alındı) |
| 3 | %−0,5 | %50,0 | 0,89 | 0,0066 | +0,0010 (ödendi) |
| 4 | %10,9 | %58,3 | 3,17 | 0,0076 | 0,0000 |
| 5 | %9,5 | %81,4 | 6,20 | 0,0039 | 0,0000 |

Not: Kazanan işlem oranı ve kâr faktörü harness'ın işlem tablosundan gelir. Bu tablo limit
dolumlarında da taker maliyeti düşer; bu yüzden işlem düzeyi ölçüler ihtiyatlıdır. Portföy
getirisi gerçek (maker) maliyetle hesaplanır.

### Deflated Sharpe

- Deneme sayısı: defterdeki dev_train 1× satırları, 366 satır (361 benzersiz).
- Deneme Sharpe'larının varyansı 1,368, ortalaması 0,284, en büyüğü 1,720.
- dev_valid Deflated Sharpe: #1 0,000004; #2 0,000000; #3 0,000002; #4 0,000001; #5 < 0,000001.
- dev_train Deflated Sharpe (aynı girdilerle): hepsi < 0,000001.
- Duyarlılık (`dogrulama_dokum.txt`): varyans yalnız baz/spot_vadeli satırlarından alınırsa
  (316 satır, varyans 0,626) değerler #1 0,0120; #2 0,0000; #3 0,0011; #4 0,0102; #5 0,0036 olur.
- Sonuç: Çoklu deneme düzeltmesinden sonra hiçbir yapılandırma anlamlı değil.

### Al-tut kıyası (BTC/ETH/SOL eşit ağırlıklı vadeli, alfa kıyası)

| Dönem | Al-tut getirisi | Sharpe | En büyük düşüş |
|---|---:|---:|---:|
| dev_train (08.09.2019 – 31.12.2024) | +%3.953 | 1,28 | −%85,1 |
| dev_valid (01.01.2025 – 30.09.2026) | −%18,9 | 0,10 | −%64,3 |

- İç doğrulamada geçen üç aday al-tutun üstünde kaldı: +%16,57 … +%19,81'e karşı −%18,9.
- Ama zamanın %1'inden azında pozisyondalar. Betaları ≈ 0; getiri piyasa yönünden gelmiyor.
- Eğitimde ise al-tut çok daha fazla kazandı. Adaylar düşük maruziyetli bir olay stratejisidir.

### Yoğunlaşma ve riskler (betimleyici döküm, değerlendirmeden sonra; parametre değişmedi)

| # | Toplam (yüzdeler aşağı yuvarlandı) | En iyi 1 / 5 / 10 işlem çıkınca | En iyi gün (06.02.2026) çıkınca | En iyi ay çıkınca | İşlem olan gün |
|---|---:|---|---:|---:|---:|
| 1 | +%16,5 | +%11,5 / +%3,2 / −%3,1 | +%7,3 | +%5,2 | 78 |
| 4 | +%19,8 | +%14,6 / +%6,1 / +%0,8 | +%9,9 | +%9,9 | 16 |
| 5 | +%17,1 | +%12,1 / +%4,3 / +%0,7 | +%7,5 | +%7,5 | 9 |

- Kâr birkaç olay gününe dayanıyor. Bunlar 06.02.2026, Ekim 2025 ve Haziran 2026.
- #5'in 27 işlemi 9 olay gününden geliyor; her olayda üç coine birden giriyor. Bağımsız gözlem
  sayısı 9'dur.
- dev_valid'de en büyük anlık zarar 10.10.2025 21:15 UTC'de oldu.
  - Yalnız uzun baz yapılandırması (#4) bu barda alım yaptı. Sonraki 5 dakikalık barda portföy
    yaklaşık −%11,2 değer kaybetti.
  - Pozisyon 1 saat içinde toparlandı ve portföy düzeyinde yaklaşık +%2,3 ile kapandı. #1 ve #5 aynı olaydan etkilendi.
  - Bu, stratejinin ana riskidir: düşen bıçağı tutuyor. Düşüş sürseydi kayıp büyük olurdu.
  - Ayrıca bu tür anlarda borsada gecikme, likidite ve otomatik pozisyon kapatma (ADL) olabilir.
    Backtest bunları modellemez.
- Günlük getiri korelasyonu (dev_valid):

  | | #1 | #2 | #3 | #4 | #5 |
  |---|---:|---:|---:|---:|---:|
  | #1 | 1,00 | 0,56 | 0,61 | 0,70 | 0,69 |
  | #4 | 0,70 | 0,56 | 0,39 | 1,00 | 0,91 |
  | #5 | 0,69 | 0,59 | 0,43 | 0,91 | 1,00 |

  #4 ile #5 fiilen tek stratejidir.
- İki yönlü sürümlerde kısa işlemler dev_valid'de de zayıf kaldı: #1'de kısa 55 işlem +0,013,
  uzun 58 işlem +0,096. Kâr yine uzun taraftan geldi.
- İleriye dönük takip seçimi için `PROTOKOL_2` "iç doğrulamada en az 30 işlem" ister. #5 (27
  işlem) bu eşiğin altında kalıyor; #1 (113) ve #4 (48) eşiği geçiyor.

## 7. Dürüst sonuç

- Ailenin adını veren hipotez desteklenmedi. Coinler arası öncü–izleyen kenarı birkaç bps; 5–15
  dakikalık ufukta maliyetin altında. Limit emir maliyeti düşürüyor ama kenar yaratmıyor. Ters
  yön ve prim endeksi sinyalleri de zararda.
- Spot–vadeli ayrışmasından gelen kısa vadeli düzelme eğitimde güçlü ve geniş bir parametre
  bölgesinde pozitifti. İç doğrulamada 5 yapılandırmadan 3'ü aday şartlarını geçti. Hepsi 5m'lik
  sürümlerdi ve en çok uzun taraf çalıştı.
- Ancak:
  - İç doğrulama getirisi eğitime göre çok küçük. Geçen üç adayın yıllık getirisi eğitimde
    %14,6–20,3, iç doğrulamada %9,1–10,9.
  - Alfa anlamlı değil (t 1,489–1,642) ve Deflated Sharpe ≈ 0.
  - Sonuç birkaç olay gününe bağlı.
  - Aynı mekanizmanın 15m (#2) ve iki yönlü spot öncülüğü (#3) sürümleri iç doğrulamada kaybetti.
- Bu adaylar "kârlı strateji" sayılamaz. En fazla ileriye dönük takipte izlenmeye değer, düşük
  maruziyetli bir olay stratejisi adayıdırlar. Ana riskleri ani çöküşlerde alım yapmaktır.

## 8. Kurallar ve açıklamalar

- `unlock_holdout` çağrılmadı. `scope="holdout"`/`"all"` kullanılmadı. Veri dosyaları doğrudan
  okunmadı; veri indirilmedi.
- Bütün değerlendirmeler `evaluate()` ile deftere yazıldı. Defter yalnız ekleme ile büyüdü.
  - Toplam 398 satır: 366 dev_train 1×, 22 dev_train 2×, 10 dev_valid.
  - Dondurmadan önce dev_valid satırı yoktu.
- Defter dışı çalıştırmalar:
  1. Modüle `taraf` parametresi eklendikten sonra, defterdeki bir yapılandırmanın
     (`sv_5m_hepsi_k3_e5_t12`) dev_train sonucu `record=False` ile yeniden üretildi. Sonuç birebir
     aynıydı. Yeni deneme değildir.
  2. `inceleme.py` / `inceleme2.py`, defterde zaten ölçülmüş yapılandırmaların yıllık, yön ve
     işlem kırılımını üretti. Bunun için veriyi 31.12.2024'te keserek harness'ın
     `compute_signals` ve `backtest` fonksiyonlarını kullandılar.
  3. Tanılama betikleri (`tanilama1–3.py`) yalnız 2025 öncesi veriyle ham ilişkileri ölçtü.
  4. İlk araştırmacının yazdığı `deneme_hiz.py` (4 yapılandırma, `record=False`, yalnız
     dev_train) çalıştırılmış olabilir; çıktısı yok. Bu oturumda çalıştırılmadı.
  5. `dogrulama_dokum.py` dev_valid'i değerlendirmeden sonra yalnız betimlemek için yeniden
     hesapladı.
- dev_valid'den sonra parametre ya da seçim değişmedi. Modüldeki `SONUC` sözlüğüne yalnız sonuç
  metni eklendi; bu sinyali etkilemez.
- 2024 sonrası piyasa bilgisi (fiyatlar, olaylar) fikir, coin ya da parametre seçiminde
  kullanılmadı. 2025–2026 olay tarihleri yalnız dev_valid değerlendirmesinden sonra, verinin
  kendisinden betimleme için okundu.

## 9. Dosyalar

- `NOTLAR.md`: plan, kesintiler, dondurma kararı (dev_valid'den önce).
- `ortak.py`: kesintiye dayanıklı tarama yardımcısı.
- `tarama1–10.py/.csv/.log`: taramalar.
- `tanilama1–3.py/.txt`: Aşama 0.
- `inceleme.py`, `inceleme2.py`, `inceleme1*.txt`, `inceleme2a/b/c.txt`: eğitim içi inceleme.
- `nedensellik.py/.log`: ileri bakış denetimi.
- `dogrulama.py/.log`, `dogrulama_sonuc.json`: tek seferlik iç doğrulama.
- `dogrulama_dokum.py/.txt`: betimleyici döküm.
