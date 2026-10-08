# Formasyon ailesi — çalışma notları (aramadan önce yazıldı)

Tarih: 8 Ekim 2026. Bu not, herhangi bir strateji sonucu görülmeden önce
yazıldı. Sonradan eklenenler "EK" başlığıyla, o ana kadar yalnız dev_train
görülmüş olarak yazılır.

README.md'deki 1. aşama formasyon istatistikleri bütün veriyi (görülmemiş
dönem dahil) kapsadığı için okunmadı ve formasyon tipi seçiminde
kullanılmayacak. Tip seçimi yalnız dev_train değerlendirmeleriyle yapılır.

## Kurallar (bütün yapılandırmalar için)

- Grafik formasyonları: `zigzag` (ATR(14) eşikli) + `detect_chart_patterns`,
  ölçekler `merge_scales` ile birleştirilir (`analysis.py` ile aynı yol).
  Sinyal formasyonun `breakout_index` barının kapanışında bilinir; hedef
  pozisyon o bardan itibaren verilir (işlem sonraki açılışta).
- Mum formasyonları: `detect_candles`; sinyal formasyon barının kapanışında.
- Çıkışlar yalnız kapanışlarla: kapanış hedefin/stopun ötesine geçince o barda
  hedef 0 (çıkış sonraki açılışta), ya da sabit tutma süresi.
- Aynı barda çelişen yönlü sinyaller yok sayılır. Pozisyondayken gelen yeni
  sinyal eski işlemin yerini alır (aynı yönse seviyeler/süre yenilenir; ters
  yönse vadelide yön değişir, yalnız alım modunda pozisyon kapanır).
- Vadeli bacaklarda coinin ilk fonlama kaydından önce pozisyon 0.
- Evren: BTC/ETH/SOL eşit ağırlık (PORT3). Kaldıraç yok.

## Plan

1. Aşama 1 (ders kitabı değerleri, geniş tarama; yalnız dev_train, 1× ve 2×):
   a. Grafik formasyonları, bütün tipler: 1h/4h/1d × {spot yalnız alım,
      vadeli iki yön} × çıkış {formasyon hedef/stop + formasyon süresi,
      sabit 20 bar} × trend filtresi {yok, EMA200}.
   b. Grafik formasyon grupları (ikili, üçlü, OBO, üçgen, kama, dikdörtgen,
      bayrak, fincan) ayrı ayrı: 1h/4h/1d × {spot, vadeli iki yön}, hedef/stop
      çıkışı, filtresiz.
   c. Mum formasyonu grupları (uç doji, çekiç/asılı adam, ters çekiç/kayan
      yıldız, yutan, harami, delen/kara bulut, sabah/akşam yıldızı, asker/karga,
      marubozu, cımbız): 1h/4h/1d × {spot, vadeli iki yön}, 10 bar sabit tutma,
      filtresiz.
2. Aşama 2 (daraltma, yalnız dev_train): aşama 1'de 2× maliyette de pozitif
   olan bölgelerin komşu parametreleri: çıkış türü ve süresi, hedef katı,
   trend ve hacim filtresi, zigzag ölçekleri, tip birleşimleri. Amaç tek bir
   sivri nokta değil, geniş bir kârlı bölge.
3. Aşama 3: en fazla 5 yapılandırma dondurulur, `assert_causal`, dev_valid'de
   tek değerlendirme, `candidate_check`, Deflated Sharpe.

Toplam deneme hedefi: birkaç yüz (en fazla ~500).

## Dondurma ölçütleri (yalnız dev_train ile)

- dev_train'de 1× ve 2× maliyetle net getiri > 0.
- Spot (yalnız alım) sonuçlar al-tut betası nedeniyle şişebilir: piyasada
  kalma oranına göre al-tut ile kıyaslanır; vadeli iki yön ve açığa satış
  tarafının ayrı sonucu daha ayırt edici sayılır.
- Komşu parametrelerde de pozitif (kararlılık), çoğu yılda ve coinlerin
  çoğunda pozitif.
- dev_valid'de ≥ 20 işlem şartı için dev_train'de yılda yeterli işlem
  (portföyde yılda ~15+) olmalı.
- Çeşitlilik: mümkünse farklı formasyon türü / zaman dilimi / piyasa.

Yıllık, bacak ve yön bazlı tanılar defterde zaten kayıtlı yapılandırmalar
için `run()` ile hesaplanır ve sonuç serisi 2024-01-01 öncesine kesilir.

## EK 1 — Aşama 1 sonrası (yalnız dev_train görüldü)

Aşama 1: 132 yapılandırma (PORT3). Bulgular:

- 1h'de neredeyse her şey maliyetle eridi (grafik formasyonlarında da mumlarda
  da 2× maliyette negatif). 1h bundan sonra aranmayacak.
- Mum formasyonları 1h/4h'de vadeli iki yönde hep zarar; 1d spotta pozitif
  olanlar (yutan, ters çekiç) al-tut betası (Sharpe < al-tut 1,12–1,15).
  Tek istisna 1d marubozu (vadeli iki yön Sharpe 0,87, iki yön de pozitif) —
  bu bir "büyük gövdeli momentum barı" sinyali; küçük bir daraltma yapılacak.
- Grafik formasyonları: 4h üçgenler hem spot alımda (1,09) hem vadeli iki
  yönde (1,05; açığa satış tarafı da pozitif) iyi; 4h kamalar spotta 1,05 ama
  vadeli iki yönde 0,36 (açığa satış zararlı). 4h bütün tipler + EMA200 trend +
  20 bar tutma spotta 1,24, 2017–2023 her yıl pozitif. 1d bütün tipler vadeli
  iki yön (hedef/stop) 1,04, 2020–2023 her yıl ve iki yön pozitif.
  İkili/üçlü tepe-dip, OBO, dikdörtgen, bayrak 1h/4h'de zayıf/negatif; fincan
  neredeyse hiç kırılım üretmiyor.
- 1d spot alım (1,27) yılda ~8 işlem: dev_valid'de 20 işlem şartını
  karşılaması zor.

Aşama 2 planı: (A) 4h konsolidasyon formasyonları (üçgen, kama, birleşimi)
× {vadeli iki, vadeli uzun, spot} × çıkış {hedef ×1/1,5/2, stop+süre, 20 bar};
ardından filtreler (trend, hacim, eğilim uyumu) ve zigzag ölçekleri.
(B) 4h bütün tipler + trend filtresi: çıkış ve trend uzunluğu. (C) 1d bütün
tipler: çıkış türleri, ölçekler (işlem sayısını artırmak için 1,5/3), filtre.
(D) 1d marubozu: tutma süresi, ATR çıkışı, yön.

## EK 2 — Aşama 2 sonrası (yalnız dev_train görüldü)

Aşama 2: 125 yeni yapılandırma (toplam 257). Bulgular (dev_train, 1×):

- 4h üçgen+kama kırılımları: vadeli yalnız alım + EMA200 (1,51) veya + hacim
  1,5 (1,57); her yıl ve her coin pozitif. Vadeli iki yönde açığa satış tarafı
  yaklaşık başabaş (hacim 1,5: +0,02; EMA200: +0,06); iki yön toplam 1,11–1,20.
  Spotta stop+süre çıkışı 1,49 ama kârın çoğu 2021'den.
- 4h bütün tipler + EMA200 + kısa sabit tutma: vadeli alım 10 bar 1,64 (20 bar
  1,27, 40 bar 0,93); spot 10 bar 1,26 / 20 bar 1,24 / 40 bar 1,36. Her yıl
  pozitif ama BTC bacağı zayıf.
- 1d stop+süre (uzun tutma) 1,6–1,8 görünüyor ama kârın neredeyse tamamı
  SOL'un 2021 yükselişinden (SOL bacağı ×75–×200) ve dev_train'de yılda ~9–15
  işlem: sağlam sayılmadı, dondurulmayacak.
- 1d bütün tipler, vadeli iki yön, hedef/stop, ölçekler (2,3,4): 1,33, 72
  işlem, her yıl, her coin ve iki yön de pozitif. Komşular (varsayılan ölçek
  1,04; hedef ×1,5 1,15; 4 ölçek 1,06) pozitif.
- 1d marubozu, vadeli iki yön, ATR çıkışı (2× stop, 4× hedef, 20 bar): 1,03,
  her yıl ve iki yön pozitif (ETH ≈ 0).

Kısa liste (dondurma adayları; aşama 3'te yalnız komşu kontrolü):
F1 4h vadeli alım üçgen+kama + EMA200 (hedef/stop); F2 4h vadeli iki yön
üçgen+kama + hacim; F3 4h vadeli alım bütün tipler + EMA200 + 10 bar;
F4 1d vadeli iki yön bütün tipler ölçek (2,3,4) hedef/stop; F5 1d marubozu
vadeli iki yön ATR çıkışı.

## EK 3 — Aşama 3 sonrası ve dondurma kararı (yalnız dev_train görüldü)

Aşama 3: 37 yeni yapılandırma (toplam 294). Komşu kontrolleri (dev_train
Sharpe 1×):

- F1 (4h vadeli alım üçgen+kama EMA200 hedef/stop, 1,51): EMA100 1,54, EMA400
  1,46, hedef ×1,5 1,35, + hacim 1,5 1,67 (yalnız 56 işlem), stop+süre 1,15,
  ölçek (2,3,4) 1,21, yalnız üçgen 1,30, yalnız kama 1,17, + dikdörtgen 1,40.
  Düz bölge.
- F2 (4h vadeli iki yön üçgen+kama hacim 1,5, 1,20): hacim 1,25 1,07, 2,0
  1,12, + EMA200 1,42, hedef ×1,5 1,18. Yalnız açığa satış 0,06 (≈ 0): açığa
  satış tarafının dev_train'de kendi başına getirisi yok.
- F3 (4h vadeli alım bütün tipler EMA200 10 bar, 1,64): 5 bar 1,17, 15 bar
  1,20, 20 bar 1,27, 40 bar 0,93; EMA100 1,48, EMA400 1,52, + hacim 1,45,
  yalnız üçgen+kama 1,52. 10 bar yerel bir tepe; komşular ~1,2.
- F4 (1d vadeli iki yön bütün tipler ölçek (2,3,4) hedef/stop, 1,33): ölçek
  (2,3) 1,39, (2,4) 1,04, (1,5,2,3,4) 1,06, (1,5,3) 0,90; ölçek 2'siz (3),
  (3,4) 0,57 / 0,48 (az işlem). Hedef ×1,5 1,42, yalnız alım 1,47, yalnız
  üçgen+kama 1,33.
- F5 (1d marubozu ATR): stop/hedef/süre komşuları 0,88–1,03, düz; ama
  dev_train'de yılda ~11 işlem (portföy). Ön yazılı "yılda ~15+ işlem"
  ölçütünü karşılamadığı için dondurulmadı.

dev_train (2020–2023) günlük getiri korelasyonları: F1–F3 0,52; diğer
çiftler 0,12–0,41. Vadeli al-tut PORT3'e beta: F1 0,13, F2 −0,01, F3 0,09,
F4 −0,07.

**Dondurulanlar (4; dev_valid'e bunlarla ve bir kez bakılacak):**

| Ad | Aralık | Piyasa | Parametreler |
|---|---|---|---|
| `formasyon_ucgen_kama_4h_trend_uzun` (F1) | 4h | vadeli, yalnız alım | `{"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "uzun", "cikis": "hedef", "trend_n": 200}` |
| `formasyon_ucgen_kama_4h_hacim_iki` (F2) | 4h | vadeli, alım + açığa satış | `{"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "iki", "cikis": "hedef", "hacim_k": 1.5}` |
| `formasyon_hepsi_4h_trend_10bar_uzun` (F3) | 4h | vadeli, yalnız alım | `{"yontem": "grafik", "tipler": "hepsi", "yon": "uzun", "cikis": "sure", "max_bar": 10, "trend_n": 200}` |
| `formasyon_hepsi_1d_olcek234_iki` (F4) | 1d | vadeli, alım + açığa satış | `{"yontem": "grafik", "tipler": "hepsi", "yon": "iki", "cikis": "hedef", "olcekler": [2.0, 3.0, 4.0]}` |

Hepsi BTC/ETH/SOL eşit ağırlık (PORT3). Gerekçe: dev_train'de 1× ve 2×
maliyette pozitif; komşularında pozitif; her yıl (2020–2023) ve her coinde
pozitif; yılda ≥ 18 işlem; aralarında düşük korelasyon. F1 ile F3 aynı fikrin
(trend yönünde formasyon kırılımı) iki çıkış biçimi; F2 ve F4 iki yönlü ve
al-tut betası ≈ 0. Spot eşdeğerleri (aynı kural spotta) ayrıca dondurulmadı.

## EK 4 — dev_valid sonrası (tek değerlendirme yapıldı)

Dondurulan 4 yapılandırma `dogrulama.py` ile bir kez değerlendirildi. F1, F2,
F3 candidate_check'i geçti; F4 geçmedi (dev_valid Sharpe 0,31). Sonuçlardan
sonra hiçbir kural ya da parametre değiştirilmedi; yalnız `specs()`
açıklamalarına candidate_check sonucu yazıldı. Ayrıntılar: `RAPOR.md`.
