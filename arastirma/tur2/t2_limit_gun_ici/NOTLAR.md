# t2_limit_gun_ici — çalışma notları

Protokol sürüm 2 (`docs/PROTOKOL_2.md`). Aile anahtarı `t2_limit_gun_ici`.
Bu dosya aramadan önce başladı; her aşamanın kararı dev_valid'e bakılmadan
yazılır. Dondurma kararı dev_valid değerlendirmesinden **önce** buraya
yazılacak.

## 0. Okunanlar ve bilgi çekincesi

- `docs/PROTOKOL_2.md`, `docs/PROTOKOL.md`, `arastirma/SONUC_1.md`,
  `arastirma/DENETIM_1.md`, `grafik_analiz/research/*.py`, tur 1 raporları
  (`ortalamaya_donus`, `kirilim`, `mevsimsellik`).
- Tur 1 raporları, tur 1'in dev_valid'i (2024-01 – 2025-06) ve görülmemiş
  dönemi (2025-07 – 2026-09) hakkında sonuç içeriyor. Bu dönemlerin
  2025-01 sonrası kısmı tur 2'nin dev_valid'idir. Bu bilgi fikir, coin ya da
  parametre seçiminde **kullanılmayacak**; seçimler yalnız tur 2 dev_train
  (verinin başı – 31.12.2024) sonuçlarına dayanacak. Okunmuş olması bir
  sınırlama olarak raporda yazılacak.

## 1. Fikir

Tur 1'de gün içi fikirler (ortalamaya dönüş 5m/15m, açılış aralığı kırılımı,
saat etkileri) çoğunlukla taker maliyeti (vadeli %0,07/taraf) yüzünden öldü.
Sürüm 2'nin limit emir modeli: emir bir sonraki barda limit fiyattan, fiyat
limitin 2 bps ötesine geçerse dolar; vadeli maker %0,02/taraf, kayma yok;
dolmazsa iptal.

Limit emrin iki etkisi var:

1. **Maliyet ve fiyat avantajı:** giriş daha iyi fiyattan ve ucuz.
2. **Ters seçilim:** emir, fiyat aleyhe gidince dolar. Dolan işlemler, dolmayanlara
   göre daha kötü sonuç verebilir. 2 bps geçme şartı rastgele yürüyüşte bile
   işlem başına yaklaşık −2 bps beklenen kayıp demektir.

Her yöntem için ölçülecek (yalnız dev_train):

- dolum oranı (verilen giriş emirlerinin dolan payı),
- dolan ve dolmayan emirlerin aynı ufuktaki "piyasa emriyle girilseydi" getirisi
  (ters seçilim = dolanların bu getirisi − dolmayanlarınki),
- dolan emirlerin limit fiyattan ölçülen brüt getirisi,
- aynı sinyalin piyasa emriyle yürütülen kontrol sürümü.

## 2. Yöntemler (plan)

Vadeli PORT3 (BTC/ETH/SOL eşit ağırlık), 5m / 15m / 1h. Pozisyon 0 / ±1.

1. `fitil` — bekleyen derin limit (fitil yakalama): pozisyon yokken her bar
   kapanışında kapanış × (1 − k·σ) seviyesine alış limiti (σ: son N barın log
   getiri std'si). Dolarsa: H bar tut, piyasa ile çık; ya da giriş × (1 + tp·σ)
   satış limiti, H bar zaman stopu. Yön: yalnız alım, yalnız açığa satış ya da
   trend yönünde.
2. `donus` — tur 1 ortalamaya dönüş sinyali (n barlık getiri / hareket öncesi
   oynaklık ≤ −eşik), girişi limitle: kapanış × (1 − d·σ) ya da sabit bps
   altına; m bar boyunca yeniden dener. Çıkış süre ya da hedef limiti.
   Kontrol: aynı sinyal piyasa emriyle.
3. `orb` — günlük açılış aralığı kırılımı (UTC), girişi kırılan seviyeye geri
   çekilmede limitle; gün sonu çıkış.
4. `saat` — saat etkisi (UTC saat penceresinde pozisyon), giriş ve çıkış
   limitle.

Arama: önce her yöntem için kaba ızgara (dev_train, 1×), sonra yalnız
dev_train'de umut veren bölgelerin komşuluğu ve 2× maliyet. Toplam birkaç yüz
yapılandırmayı geçmeyecek.

## 3. Aşama notları

(aşağıya eklenir)

### Aşama 1 (tarama1.py; 62 yapılandırma; dev_train, 1×)

Motor önce sentetik veride doğrulandı (`motor_testi.py`): motorun izlediği
pozisyon backtest'inkiyle birebir aynı, seri kısaltılınca geçmiş sinyaller
değişmiyor. `ortak.degerlendir` her çalıştırmada aynı kontrolü gerçek veride de
yapıyor (dev_train'e kesilmiş veriyle).

Bulgular (yalnız dev_train):

- **fitil 5m/15m:** k=2–3σ'da limit dolumları rastgele yürüyüşe yakın
  (dolum sonrası getiri −0,4 … +8 bps); maliyetle sermaye eridi. Kenar derinlikle
  artıyor (5m k=6, H=24: dolum sonrası +18,7 bps, net +%132, Sharpe 0,95), ama
  BTC bacağı zararda, kâr SOL'dan. Açığa satış fitili ve iki yönlü sürüm zararda.
- **fitil 1h:** k=3, H=1: +%116, Sharpe 0,91, alfa %13,9 (t 1,65); k=3, H=6:
  +%326, Sharpe 1,10, alfa t 1,28, beta 0,15, düşüş −%52. 2022 zararda.
- **Ters seçilim çok belirgin:** dolan fitil emirlerinin "açılışta piyasa
  emriyle girilseydi" getirisi −50 … −215 bps, dolmayanlarınki +1 … +14 bps.
  Limitin fiyat avantajı bunu ancak derin seviyelerde aşıyor.
- **donus 1h (tur 1'in yükselen trendde dip alımı):** piyasa emri +%182,
  Sharpe 1,81, alfa %18,7 (t 3,57); limit 1σ altı, 3 bar: +%231, Sharpe 1,87,
  alfa %22,0 (t 3,74). Yıllar 2020–2024 hepsi pozitif, üç coin pozitif.
  Limit kenarı biraz artırıyor; ters seçilim görülmüyor (dolan emirler
  dolmayanlardan kötü değil).
- **donus 15m/5m:** 15m zayıf (Sharpe 0,50–0,66); 5m 1,21–1,28 ama BTC/ETH
  bacakları negatif, kâr SOL'dan.
- **İki yönlü saf dönüş (15m, 5m):** piyasa ve limitte zarar.
- **ORB 15m (piyasa, seviye limiti, kapanış altı limit, ters):** hepsi büyük
  zarar; brüt kenar bile negatif. Limit (seviyeye geri çekilme) daha kötü:
  dolanlar başarısız kırılımlar.
- **Saat pencereleri:** limitle de zarar; dolan emirler fiyat aleyhe gittiğinde
  doluyor (dolan −0,3 bps, dolmayan +30 bps).

Karar (aşama 2): ORB, saat, açığa satış fitili ve iki yönlü saf dönüş
bırakılıyor. Aşama 2: (a) donus 1h yükselen trend dip alımının limit
komşuluğu (mesafe, deneme sayısı, eşik, n, H, trend, çıkış) ve aynı kuralın
15m/5m karşılığı (4 saatlik hareket, 12 saat tutma); (b) fitil 1h komşuluğu
(k, H, σ penceresi, trend filtresi, limit çıkış) ve 5m/15m derin seviyeler.

### Aşama 2 (tarama2.py; 52 yapılandırma; dev_train, 1×)

- **donus 1h limit komşuluğu geniş bir plato:** mesafe 0,75–1,5σ, deneme 1–6
  bar, eşik 2,5–3, trend 30–100 gün: Sharpe 1,63–1,98, alfa %18,7–22,2 (t
  3,3–4,1). Eşik 3,5 ve n=6 daha zayıf (Sharpe 0,88–1,28). Trend filtresi
  olmadan Sharpe 0,97, beta 0,12, 2022 −%30 (filtre şart). Limit ile piyasa
  arasındaki fark 1h'de küçük (piyasa 1,81 → limit 1,87).
- **donus 15m (n=16, H=48):** piyasa 1,62 → limit 1σ 1,71; limit 2σ 1,47.
- **donus 5m (n=48, H=144):** piyasa 1,92 > limit 2σ 1,66 > limit 3,5σ 1,52.
  Dolum oranı emir başına %2–8; dolmayan bölümler (piyasa emriyle girilseydi
  +145…+179 bps) dolanlardan (+55…+65 bps) iyi: 5m'de ters seçilim belirgin,
  limit zarar veriyor.
- **fitil 1h:** derinlik arttıkça Sharpe artıyor (k=3,5–4: 1,12–1,66, alfa t
  2,0–3,0). **Trend filtresi (50 gün SMA üstü) büyük fark yapıyor:** k=3, H=6:
  Sharpe 1,10 → 1,93, alfa t 1,28 → 3,70, düşüş −%52 → −%26; k=3, H=1: 0,91 →
  1,65. Limit çıkış (kapanış +5 bps, 3 bar) ve hedef kâr limiti yardımcı olmadı.
- **fitil 5m/15m derin:** k=6, H=24 + trend: Sharpe 1,98, alfa t 3,93, düşüş
  −%18 (trendsiz 0,95). 15m k=5 H=16: 1,02.
- Bütün iyi sonuçlarda kârın büyük kısmı SOL bacağından ve 2021'den geliyor;
  2022 çoğunda hafif negatif. BTC bacağı yine de pozitif.

Karar (aşama 3): fitil + 50 gün trend filtresinin 1h (k 2,5–4 × H 1–12),
15m ve 5m (k 4–8 × H 12–48) yüzeyi, trend uzunluğu duyarlılığı; ana
adayların 2× maliyet sonucu (yalnız 2× satırı eklenerek).

### Aşama 3–4 (tarama3.py, tarama4.py; 38 yeni yapılandırma, 1× ve 2×; 7 yapılandırmanın yalnız 2× satırı)

- **fitil 1h + 50 gün trend, Sharpe (1×):**

  | k \ H | 1 | 3 | 6 | 12 |
  |---|---|---|---|---|
  | 2,5 | 1,05 | 1,03 | 1,54 | 0,98 |
  | 3 | 1,65 | 1,30 | 1,93 | 1,06 |
  | 3,5 | 1,49 | 1,74 | 1,96 | 1,17 |
  | 4 | 1,48 | 1,76 | 1,85 | 1,17 |
  | 4,5 | 1,59 | 1,70 | 1,70 | 1,17 |

  Trend 30/100 gün (k=3, H=3): 1,20 / 1,14 (50 gün 1,30). σ penceresi 336: 1,30.
- **fitil 5m + 50 gün trend, Sharpe (1×):**

  | k \ H | 12 | 24 | 48 |
  |---|---|---|---|
  | 4 | 0,50 | 1,44 | 1,44 |
  | 6 | 1,52 | 1,98 | 1,94 |
  | 8 | 1,54 | 1,92 | 1,79 |
  | 10 | 1,58 | 1,69 | 1,68 |

  Trend 30/100 gün (k=6, H=24): 1,77 / 1,82.
- **fitil 15m + trend:** 1,29–1,46 (2× 0,60–0,90); 1h ve 5m'den zayıf.
- **2× maliyet (dev_train):** donus 1h piyasa 1,66 / limit 1,80; donus 15m
  piyasa 1,46 / limit 1,61; fitil 1h k3 H6 1,51; fitil 1h k3 H1 0,96; fitil
  5m k6 H24 1,33.
- **Bölüm düzeyinde ters seçilim (`tani_secilim.py`, dev_train):**
  - donus 1h, 1σ, 3 bar: dolum %76; dolan bölümlerin piyasa getirisi +155 bps,
    dolmayanların +102 bps → ters seçilim yok; limit toplam brüt katkıyı
    artırıyor (3,94 vs 3,54).
  - donus 1h, 2σ: dolum %31; dolan +86, dolmayan +133 → ters seçilim; limit
    toplam brütü düşürüyor (2,26 vs 3,70).
  - donus 15m, 1σ, 12 bar: dolum %72; dolan +134, dolmayan +173.
  - donus 5m, 2σ, 36 bar: dolum %38; dolan +110, dolmayan +201 (güçlü ters
    seçilim).
  - İki yönlü 15m dönüş: dolan −18, dolmayan +66; ORB seviye limiti: dolan −23,
    dolmayan +88; saat 21–23: dolan 0, dolmayan +30.

## 4. Dondurma kararı (dev_valid değerlendirmesinden ÖNCE yazıldı)

Arama bitti: defterde 152 benzersiz yapılandırma (152 dev_train 1× satırı,
45 dev_train 2× satırı). dev_valid'e hiç bakılmadı.

Seçim kuralı (yalnız dev_train):

- fitil yüzeylerinde (k × H, 50 gün trend) iç noktalar arasından 3×3
  komşuluğunun 1× Sharpe ortalaması en yüksek olan seçilir.
  - 1h: k=4, H=3 (komşuluk ortalaması 1,697; k=3,5 H=3 1,684; k=4 H=6 1,580;
    k=3,5 H=6 1,549). Tek nokta olarak en yüksek k=3,5 H=6 (1,96) seçilmedi.
  - 5m: k=8, H=24 (komşuluk ortalaması 1,738; k=6 H=24 1,563).
- donus 1h: aşama 2 platosunun merkezi (n=4, eşik 3, trend 50, H=12, limit
  1σ altı, 3 bar). Komşuları Sharpe 1,63–1,98.
- donus 15m: aynı kuralın 15m karşılığı, limit 1σ, 12 bar (dev_train 1,71,
  2× 1,61). Daha ince zaman diliminde limit yerleştirmenin etkisini sınar.
- Kontrol: donus 1h'in piyasa emirli sürümü. Limit ile piyasa yürütmesi
  arasındaki farkı dev_valid'de önceden kayıtlı biçimde ölçmek için. Bu
  yapılandırma tur 1'in `od_dip_ret4h_fut_port3_1h` kuralıyla aynıdır;
  seçim gerekçesi yalnız kontrol olmasıdır.

Dondurulan 5 yapılandırma:

| # | Ad | Aralık | Parametreler |
|---|---|---|---|
| 1 | `t2_limit_gun_ici_fitil_1h_k4_H3_t50` | 1h | fitil, k=4, H=3, sig_n=168, trend 50 gün ile |
| 2 | `t2_limit_gun_ici_fitil_5m_k8_H24_t50` | 5m | fitil, k=8, H=24, sig_n=288, trend 50 gün ile |
| 3 | `t2_limit_gun_ici_donus_1h_n4_e3_t50_H12_lim1.0s_m3` | 1h | donus n=4, eşik 3, vol_n 500, yalnız alım, trend 50, H=12, limit 1σ (sig_n 168), m=3 |
| 4 | `t2_limit_gun_ici_donus_15m_n16_e3_t50_H48_lim1.0s_m12` | 15m | donus n=16, eşik 3, vol_n 2000, yalnız alım, trend 50, H=48, limit 1σ (sig_n 96), m=12 |
| 5 | `t2_limit_gun_ici_donus_1h_n4_e3_t50_H12_piyasa` | 1h | 3 ile aynı, giriş piyasa emri (kontrol) |

Beklenti ve çekinceler (dev_train'den): beşi de "yükselen trendde düşüş
alımı" temasının varyantı; günlük getirileri muhtemelen korelasyonlu. Kârın
çoğu 2021 ve SOL bacağından geliyor; 2022'de hepsi hafif negatif. Beta
0,00–0,03, alfa t 3,4–4,0 (çoklu deneme düzeltmesiz). dev_valid tek seferlik
`evaluate(spec)` ile ölçülecek; sonuca göre değişiklik yapılmayacak.

Dondurma kontrolü (`dondurma_kontrol.py`, `dondurma_kontrol.log`, dev_valid'den
önce): beş spec'in parametreleri defterdeki arama satırlarıyla aynı;
`assert_causal` varsayılan ve ek kesimlerde (0,3/0,5/0,7/0,9/0,99) geçti.
dev_train günlük getiri korelasyonları: fitil 1h–5m 0,61; donus 1h limit–piyasa
0,93; donus 1h–15m 0,66; fitil ile donus arası −0,05…0,32.

Sıradaki adım: `dogrulama.py` her spec için bir kez `evaluate(spec)`.

## 5. dev_valid sonrası (değişiklik yapılmadı)

`dogrulama.py` bir kez çalıştı (`dogrulama.log`, `dogrulama_sonuc.json`).
dev_train sonuçları arama satırlarıyla birebir aynı çıktı. candidate_check:
yalnız `donus_1h_n4_e3_t50_H12_lim1.0s_m3` geçti (dev_valid 1× %+7,18, 2×
%+5,74, Sharpe 0,81, 45 işlem, alfa %+4,06, t 1,06). Diğer dördü geçmedi;
piyasa emirli kontrol %−1,74. dev_valid'den sonra yalnız betimleyici tanı
yapıldı (`tani_dogrulama.py`); hiçbir parametre ya da kural değişmedi, yeni
yapılandırma denenmedi. spec açıklamalarına candidate_check sonucu yazıldı
(açıklama metni sonuçları etkilemez).
