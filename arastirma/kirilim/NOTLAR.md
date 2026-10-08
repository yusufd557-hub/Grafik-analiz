# Kırılım ailesi — çalışma notları (aramadan önce yazıldı)

Tarih: 8 Ekim 2026. Bu not, herhangi bir strateji sonucu görülmeden önce
yazıldı. Sonradan eklenenler tarihli ve "EK" başlığıyla yazılır.

## Plan

1. Aşama 1 (geniş, kaba ızgara; yalnız dev_train, 1× ve 2× maliyet):
   beş yöntem (`kanal`, `sikisma`, `nr`, `acilis`, `williams`) ders kitabı
   parametreleri etrafında, 15m/1h/4h (gerekirse 1d), spot (yalnız alım) ve
   vadeli (alım/açığa satış), tek coin ve 3 coinlik eşit ağırlıklı portföy
   (PORT3).
2. Aşama 2 (daraltma): aşama 1'de dev_train'de umut veren 2–3 yöntemin
   komşu parametreleri ve filtreleri (trend, oynaklık rejimi, hacim). Amaç
   tek bir en iyi nokta değil, geniş bir kârlı bölge bulmak.
3. Aşama 3: en fazla 5 yapılandırmanın dondurulması, `assert_causal`,
   dev_valid'de tek değerlendirme, `candidate_check`.

Toplam deneme hedefi: birkaç yüz (en fazla ~500) yapılandırma.

## Dondurma ölçütleri (yalnız dev_train ile)

- dev_train'de 2× maliyetle net getiri > 0.
- dev_train yıllık Sharpe (1×) yüksek olsun; ama tek bir sivri nokta değil,
  komşu parametrelerde de pozitif olsun (parametre kararlılığı).
- Yıllara bölündüğünde (yalnız dev_train yılları) çoğu yılda pozitif olsun;
  kârın tek bir boğa yılından gelmemesi tercih edilir.
- PORT3 ise coinlerin çoğunda ayrı ayrı pozitif olsun.
- Spot (yalnız alım) yapılandırmalarda al-tut ile karşılaştırma yapılır;
  al-tut'un düşük maruziyetli kopyası olmaktan öte bir değer (daha düşük
  düşüş, daha iyi Sharpe) aranır.
- Çeşitlilik: mümkünse farklı yöntem / piyasa / zaman diliminden seçilir.

Yıllık ve bacak bazlı tanılar, defterde zaten kayıtlı yapılandırmalar için
`run()` ile hesaplanır ve sonuç serisi hesaplamadan önce 2024-01-01 öncesine
kesilir (dev_valid'e bakılmaz).

## EK 1 — Aşama 1 sonrası (yalnız dev_train görüldü)

Aşama 1: 144 yapılandırma. 15m'de bütün yöntemler maliyet yüzünden ağır
zarar etti; 1h vadeli çoğunlukla negatif. En iyi bölge: 4h Donchian kanal
kırılımı + hacim teyidi (özellikle ATR iz süren stop ile), hem spot hem
vadelide. Yıllık tanıda `kanal_4h_spo ... atr_k=3, hacim_k=1.5, n=60` 2017–2023
her yıl pozitif; vadeli eşi 2020–2023 her yıl pozitif. Williams ve 1h sıkışma
1× maliyette iyi ama 2× maliyette zayıf. 1d NR7 + ATR iz, fiilen sürekli
piyasada (trend takibine yakın).

Aşama 2 planı: 4h kanalın yüzeyi (n × atr_k × hacim_k; spot, vadeli iki yön),
vadeli yalnız alım, oynaklık rejimi ve trend filtreleri, 1d kanal, 4h/1h
sıkışma + geniş ATR çıkışı, Williams + trend filtresi, 1d NR7 varyantları.

## EK 2 — Aşama 2 sonrası (yalnız dev_train görüldü)

Aşama 2: 184 yeni yapılandırma (toplam 323). 4h kanal yüzeyi geniş ve düzgün
pozitif: Sharpe atr_k ile artıyor (2 < 3 < 4), hacim_k 1,25–1,5 hafif yardımcı,
n (30–120) etkisi küçük. Vadeli iki yönde açığa satış tarafı 2020–2023
toplamında yaklaşık başabaş; kâr uzun taraftan, açığa satış 2022'de dengeleyici.
Oynaklık rejimi filtresi `vol_ust=0.8` vadelide Sharpe'ı artırdı (tek nokta).
Sıkışma, Williams, NR, açılış aralığı ya maliyete dayanıksız ya da yalnız
spotta (beta) pozitif — elendi.

Aşama 3 planı (küçük): atr_k ∈ {5, 6} ile en iyinin ızgara sınırında olup
olmadığı; `vol_ust` filtresinin eşik ve `rejim_n` duyarlılığı; vadeli yalnız
alım + atr_k=4.

## EK 3 — Aşama 3 ve dondurma kararı (dev_valid'e BAKILMADAN yazıldı)

Aşama 3: 25 yapılandırma (toplam 348 dev_train denemesi). atr_k=5 civarında
tepe, 6'da düşüş: en iyi nokta ızgaranın içinde. `vol_ust` filtresi eşik ve
`rejim_n` değişince kararsız (rejim_n=2160'ta Sharpe 0,64) → elendi. Vadeli
yalnız alım + atr_k=4 güçlü (Sharpe ≈ 1,8, MDD ≈ −%28).

Dondurulan 3 yapılandırma (hepsi 4h, PORT3 eşit ağırlık, Donchian n=90,
ATR(14) × 4 iz süren stop, hacim teyidi 1,25 × önceki 90 bar ort.):

1. `kirilim_kanal4h_spot` — spot, yalnız alım.
2. `kirilim_kanal4h_vadeli_iki` — vadeli, alım + açığa satış.
3. `kirilim_kanal4h_vadeli_uzun` — vadeli, yalnız alım.

Gerekçe: dev_train yüzeyinin düz bölgesinin ortası (en yüksek nokta değil);
komşu n (60/120), atr_k (3/5) ve hacim_k (0/1,5) değerleri de pozitif ve 2×
maliyette kârlı. Üçü aynı kuralın farklı piyasa/yön uygulaması: açığa satış
tarafının dev_valid'de değer katıp katmadığı da böylece görülür. Diğer
yöntemler (sıkışma, NR, açılış aralığı, Williams, 15m/1h) dev_train'de ya
zararlı ya da 2× maliyete dayanıksız olduğu için dondurulmadı. 5 hakkın
yalnız 3'ü kullanıldı (dev_valid'de gereksiz bakış yapmamak için).
