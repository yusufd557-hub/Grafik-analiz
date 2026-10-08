# Kârlı Strateji Araştırması — Ön Kayıt Protokolü

Sürüm 1 · 8 Ekim 2026 · strateji sonuçlarından **önce** yazıldı.

Bu belge, bir stratejinin "kârlı" sayılması için neyi geçmesi gerektiğini
sonuçlar görülmeden önce sabitler. Sayısal değerler kodda
`grafik_analiz/research/protocol.py` dosyasındadır. Bu kurallar sonuçlara
bakılarak değiştirilmez. Değişirse yeni sürüm olarak yazılır ve eski
sonuçlar ayrı tutulur.

## Kapsam

- **Coinler:** BTCUSDT, ETHUSDT, SOLUSDT.
- **Piyasalar:** Binance spot (yalnız alım) ve USDⓈ-M vadeli (alım ve açığa
  satış, fonlama dahil).
- **Zaman dilimleri:** 5 dakika, 15 dakika, 1 saat, 4 saat, günlük.
- **Strateji aileleri:** trend takibi, momentum ve göreli güç,
  ortalamaya dönüş, kırılım/oynaklık, fonlama ve carry, mevsimsellik, makine
  öğrenmesi, grafik formasyonları.
- **Kaldıraç:** yok. Bacak başına pozisyon sermayenin en fazla 1 katıdır.

## Dönemler

| Dönem | Tarihler | Kullanım |
|---|---|---|
| Geliştirme / eğitim | verinin başı – 31.12.2023 | Kuralların ve parametrelerin seçimi |
| Geliştirme / iç doğrulama | 01.01.2024 – 30.06.2025 | Eğitimde seçilen parametrelerin kontrolü |
| Görülmemiş dönem | 01.07.2025 – 30.09.2026 | Finalistlerin tek seferlik testi |
| İleriye dönük | 01.10.2026 sonrası | Önceden kaydedilen sinyallerle sanal işlem |

Görülmemiş döneme erişim kodla kilitlidir (`research/data.py`). Kilidin her
açılışı gerekçesiyle `arastirma/holdout_kayit.jsonl` dosyasına yazılır.

**Bilinen sınırlama:** Görülmemiş dönem, bu projede strateji geliştirmek için
kullanılmadı. Ancak 1. aşamadaki formasyon istatistikleri bütün veriyi
kapsıyordu. Önceki projeler (v53-backtest, yeni) de bu tarihleri inceledi.
Tamamen bağımsız ölçüm ileriye dönük takiptir.

## İşlem simülasyonu (bütün stratejiler için aynı)

1. Strateji, bir barın **kapanışında** bilinen veriyle hedef pozisyonu
   söyler (spotta 0…1, vadelide −1…1, sermayenin katı).
2. İşlem bir sonraki barın **açılışında** yapılır.
3. Her pozisyon değişiminde değişen tutar × (komisyon + kayma) düşülür.
4. Vadelide fonlama anında açık pozisyon × fonlama oranı ödenir veya alınır.
5. Birden çok bacak sabit sermaye ağırlıklarıyla birleştirilir.
6. Her strateji ileri bakış denetiminden geçer (`assert_causal`): seri
   kısaltıldığında geçmiş sinyaller değişmemelidir.

## Maliyetler

| Piyasa | Komisyon (taraf başına) | Kayma (taraf başına) | Toplam gidiş-dönüş |
|---|---|---|---|
| Spot | %0,10 | %0,02 | %0,24 |
| Vadeli | %0,05 | %0,02 | %0,14 + fonlama |

Bu değerler Binance'in standart (VIP 0, piyasa emri) oranlarıdır. Her sonuç
ayrıca **iki kat maliyetle** de hesaplanır.

## Aday şartları (geliştirme dönemi)

Parametreler yalnızca eğitim döneminde seçilir. Bir yapılandırma şu şartları
geçerse aday olur:

1. Eğitim döneminde net getiri > 0.
2. İç doğrulamada net getiri > 0.
3. İç doğrulamada iki kat maliyetle net getiri > 0.
4. İç doğrulamada yıllık Sharpe ≥ 0,5 (günlük net getirilerden).
5. İç doğrulamada en az 20 işlem.

Değerlendirilen her yapılandırma deney defterine (`arastirma/deneyler/`)
yazılır. Böylece kaç deneme yapıldığı bilinir ve Deflated Sharpe
(Bailey & López de Prado, 2014) raporlanır.

## Finalist seçimi

Adaylar bağımsız olarak denetlenir: kod incelemesi, ileri bakış, maliyet ve
aşırı uyum kontrolü. Görülmemiş dönem açılmadan önce **en fazla 3 finalist**
yazılı gerekçeyle seçilir ve `arastirma/FINALISTLER.md` dosyasına kaydedilir.

## Görülmemiş dönem şartları

Finalistler görülmemiş dönemde, kuralları ve parametreleri değiştirilmeden,
**bir kez** ölçülür.

**Seviye 1 — kârlı:**

1. Net getiri > 0.
2. İki kat maliyetle net getiri > 0.
3. En az 20 işlem.
4. En iyi tek işlem çıkarıldığında getiri hâlâ > 0.

**Seviye 2 — istatistiksel olarak anlamlı:** Seviye 1'e ek olarak, günlük net
getirilerin blok bootstrap (10 günlük bloklar, 5.000 örnek) ile hesaplanan
"ortalama ≤ 0" olasılığı 0,05 / finalist sayısından küçük olmalıdır.

Al-tut ve nakit karşılaştırması raporlanır, şart değildir.

Görülmemiş dönem sonucundan sonra kural veya parametre değişirse strateji
yeni bir sürüm olur. Yeni sürüm yalnızca ileriye dönük takiple
değerlendirilir.

## İleriye dönük takip

Seviye 1'i geçen her strateji için:

- Her kapanmış barda sinyal, zaman damgasıyla **önce** kaydedilir.
- Sanal işlem bir sonraki barın açılışında yapılır; sonuç kayıttan sonra
  hesaplanır.
- Değerlendirme en az 90 gün ve 30 işlem sonra yapılır. Seviye 1
  şartlarıyla aynı ölçüler kullanılır.
