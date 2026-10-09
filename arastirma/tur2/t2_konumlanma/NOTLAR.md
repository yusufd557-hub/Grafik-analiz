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
