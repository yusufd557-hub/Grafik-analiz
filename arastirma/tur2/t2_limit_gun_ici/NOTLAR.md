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
