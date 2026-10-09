# Tur 2 Denetimi — B: Protokol ve deney defteri disiplini

Tarih: 9 Ekim 2026. Kapsam: `t2_cift`, `t2_konumlanma`, `t2_emir_akisi`,
`t2_lead_lag`, `t2_limit_gun_ici`, `t2_bindirme`, `t2_meta`. `t2_genis_evren`
kapsam dışıdır.

## Yöntem ve sınırlar

- Okunanlar:
  - `docs/PROTOKOL_2.md`, `docs/PROTOKOL.md`, `arastirma/DENETIM_1.md`,
    `arastirma/SONUC_1.md`.
  - `grafik_analiz/research/{protocol,data,evaluate,metrics,ledger}.py`.
  - Her ailenin `NOTLAR.md`, `RAPOR.md`, strateji modülü ve defteri.
  - `arastirma/tur2/FINALISTLER.md` ve `finalist_secimi.py`.
- Bütün sayılar defter satırlarından (`arastirma/tur2/deneyler/<aile>.jsonl`),
  ailelerin `dogrulama_sonuc.json` / `dondurulmus_sonuclar.json` dosyalarından
  ya da git geçmişinden okundu.
  - Hesaplar bu denetimin geçici betikleriyle yapıldı. Betikler depoya
    eklenmedi.
  - DSR, depodaki `metrics.deflated_sharpe` ile yeniden hesaplandı.
  - `specs()`, `GRAFIK_ANALIZ_PROTOKOL=2` ile içe aktarıldı.
- **Veri indirilmedi.** Stratejiler yeniden çalıştırılmadı.
  - Defterdeki ölçülerin kodla yeniden üretilip üretilmediği bu bölümde
    sınanmadı.
  - Günlük getiri korelasyonları da yeniden hesaplanamadı.
- Defterdeki `zaman` damgaları araştırmacının makinesinde yazıldı. Bağımsız
  bir zaman kanıtı değildir.
  - Orijinal makinedeki dosya zamanları yok.
  - Bağımsız zaman kanıtı yalnız git commit zamanlarıdır. Bunlar da ara kayıt
    anlarını gösterir, yazılma anını göstermez.

## Bulguların özeti (önem sırasıyla)

Kritik bulgu yok. Defter disiplininin mekanik kuralları yedi ailede de
tutuyor:

- aile başına en fazla 5 dondurulmuş yapılandırma,
- her biri dev_valid'de tam bir kez (bir 1× ve bir 2× satırı),
- bütün satırlarda protokol "2",
- ad öneki ve `StrategySpec.family` doğru,
- ilk dev_valid satırından sonra arama satırı yok,
- raporlanan sayılar defterle tutarlı.

| # | Önem | Aile | Bulgu (kısa) |
|---|---|---|---|
| Ö1 | önemli | t2_lead_lag, t2_cift, tur geneli | İşlem sayısı bacak başına sayılıyor. Bazı adaylar ≥ 20 (aday şartı) ve ≥ 30 (takip seçimi) eşiklerini yalnız bu sayımla geçiyor. Bacak başına sayım FINALISTLER.md'de t2_cift sonuçları bilinirken açıkça yazıldı. |
| Ö2 | önemli | hepsi | Dondurma kararının dev_valid'den önce yazıldığını gösteren bir git anlık görüntüsü hiçbir ailede yok. Kanıt, araştırmacının kendi beyanı ve defter zamanlarıdır. Bunlarla çelişen bir iz bulunmadı. |
| Ö3 | önemli | tur geneli (özellikle t2_limit_gun_ici, t2_meta, t2_bindirme) | Tur 2'nin dev_valid dönemi, tur 1'in sonuçları bilinen dönemleriyle örtüşüyor. Araştırmacılar bu sonuçları okudu. Bazı adaylar, tur 1'de dev_valid / görülmemiş dönem sonucu bilinen kurallarla aynı ya da onlardan türetilmiş. |
| Ö4 | önemli | tur geneli | Tur düzeyinde 2.345 deneme var. Bu sayıyla bütün adayların DSR'si ≈ 1e−10. t2_bindirme tur 1 yapılandırmalarını yeniden kullanıyor ama tur 1'in denemeleri sayılmıyor. |
| Ö5 | önemli | t2_lead_lag, takip seçimi | lead_lag #1 ile #4'ün dev_valid korelasyonu 0,695, eşik 0,70. İkisinin birlikte seçilmesi, korelasyon hesabının ayrıntısına bağlı. Bu ayrıntılar protokolde tanımlı değil. |
| K1 | küçük | t2_konumlanma, t2_meta, diğerleri | Defter dışında dev_valid yeniden hesaplandı. Yeniden üretim ve betimleyici tanı amaçlıydı ve açıklandı. konumlanma'nın yeniden üretim iddiasının betiği depoda yok. |
| K2 | küçük | t2_lead_lag | RAPOR tablosunda yuvarlama hataları var: Sharpe'ta ≤ 0,001, getiride ≤ 0,01 puan. Hiçbir şart sonucunu değiştirmiyor. |
| K3 | küçük | t2_emir_akisi, t2_meta | Ad/parametre tutarsızlıkları var. emir_akisi dondururken yapılandırmaları yeniden adlandırdı. meta'da 14 ad iki farklı parametreyle kullanıldı. Ölçüler ve deneme sayıları etkilenmiyor. |
| K4 | küçük | t2_bindirme, t2_cift | NOTLAR'da küçük zaman ve metin tutarsızlıkları var. Sinyali etkilemiyor. |
| K5 | küçük | takip seçimi | FINALISTLER.md protokolde olmayan bir "denetim nedeniyle çıkarma" (`--haric`) adımı ekliyor. |
| K6 | küçük | defter | Defter `spec.weights` alanını kaydetmiyor. Kapsamdaki ailelerde etkisi yok. |

---

## 1. Defter sayımları

`pencere × maliyet_kat` satır sayıları ve benzersiz yapılandırmalar. Benzersizlik
ölçütü: ad + `parametreler` (json, anahtarlar sıralı).

| Aile | Satır | dev_train 1× | dev_train 2× | dev_valid 1× | dev_valid 2× | Benzersiz (ad+parametre) | Benzersiz parametre (dev_train 1×) | dev_valid'deki yapılandırma | protokol | aile alanı |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| t2_cift | 1284 | 639 | 639 | 3 | 3 | 636 | 636 | 3 | hepsi "2" | hepsi doğru |
| t2_konumlanma | 510 | 250 | 250 | 5 | 5 | 245 | 245 | 5 | hepsi "2" | hepsi doğru |
| t2_emir_akisi | 799 | 606 | 183 | 5 | 5 | 606 | 594 | 5 | hepsi "2" | hepsi doğru |
| t2_lead_lag | 398 | 366 | 22 | 5 | 5 | 361 | 361 | 5 | hepsi "2" | hepsi doğru |
| t2_limit_gun_ici | 217 | 157 | 50 | 5 | 5 | 152 | 152 | 5 | hepsi "2" | hepsi doğru |
| t2_bindirme | 280 | 136 | 136 | 4 | 4 | 131 | 131 | 4 | hepsi "2" | hepsi doğru |
| t2_meta | 227 | 191 | 26 | 5 | 5 | 188 | 188 (anahtar eşitlemesiyle 186) | 5 | hepsi "2" | hepsi doğru |

- Başka pencere yok. `holdout` ya da `all` satırı yok.
- Her dondurulmuş yapılandırmanın tam bir dev_valid 1× ve bir dev_valid 2×
  satırı var. Yinelenen dev_valid satırı yok.
  - Satır numaraları aşağıdaki bölüm 3 tablosunda.
- Bütün strateji adları `<aile>_` ile başlıyor.
- `specs()` çıktısı denetlendi. Kapsamdaki modüllerin döndürdüğü 32
  `StrategySpec`'in hepsinde:
  - `family` alanı aile anahtarına eşit.
  - Adlar defterdeki dev_valid adlarıyla birebir aynı.
  - `interval + legs + params`, defterdeki dev_valid satırının
    `parametreler` alanıyla json olarak birebir aynı.
- Her dev_valid yapılandırması için, ilk dev_valid satırından önce aynı
  parametrelerle yazılmış bir dev_train arama satırı var. Bu satırın 1×
  ölçüleri, doğrulama çalıştırmasının dev_train 1× satırıyla birebir aynı.
  - İstisna: t2_emir_akisi'de bu eşleşme adla değil, yalnız parametre ve
    ölçüyle sağlanıyor (bkz. K3).
- Tekrarlanan dev_train satırları yalnız `evaluate(spec)` doğrulama
  çalıştırmasının kendi dev_train satırlarıdır.
  - Her aile için tekrar sayısı, dondurulan yapılandırma sayısına eşit.
  - t2_emir_akisi'de "594 benzersiz" sayısı 7 arama tekrarını da düşer
    (RAPOR "Deneme sayısı"). Bu doğrulandı: 606 satır, 594 benzersiz parametre.

## 2. Olay sırası (dondurma → dev_valid)

### 2.1 Defter zamanları

| Aile | İlk arama satırı | Son arama satırı (dev_valid'den önce) | İlk dev_valid satırı | NOTLAR'daki dondurma zamanı | İlk dev_valid'den sonra arama satırı |
|---|---|---|---|---|---|
| t2_cift | 07:00:45 | 08:56:05 | 08:59:26 | tarih var, saat yok; değerlendirme başlangıcı "08:59:24Z" (NOTLAR:206) | yok |
| t2_konumlanma | 07:00:42 | 08:49:37 | 08:52:31 | 08:51 UTC (NOTLAR:197) | yok |
| t2_emir_akisi | 09:03:43 | 16:32:40 | 16:35:41 | 16:34 UTC (RAPOR "Dondurma gerekçesi") | yok |
| t2_lead_lag | 11:48:41 | 16:40:32 | 16:43:43 | saat yok (NOTLAR "Dondurma kararı") | yok |
| t2_limit_gun_ici | 16:48:24 | 17:17:55 | 17:20:28 | saat yok (NOTLAR bölüm 4) | yok |
| t2_bindirme | 17:02:17 | 17:17:33 | 17:36:20 | 17:18 UTC (NOTLAR:238) | yok |
| t2_meta | 17:36:59 | 17:57:18 | 18:01:09 | saat yok (NOTLAR bölüm 5) | yok |

- Bütün zamanlar 9 Ekim 2026, UTC.
- Her ailede, ilk dev_valid satırından sonraki dev_train satırları yalnız
  dondurulan yapılandırmaların `evaluate(spec)` çağrısının kendi satırlarıdır.
  - t2_cift 6, t2_konumlanma 10, t2_emir_akisi 10, t2_lead_lag 9,
    t2_limit_gun_ici 10, t2_bindirme 8, t2_meta 10 satır (aynı saniyedekiler
    dahil).
  - dev_valid görüldükten sonra yeniden ayar ya da yeni arama satırı yok.
- Her defter zaman sırasına göre artan biçimde yazılmış (monoton).

### 2.2 Git anlık görüntüleri

Kontrol yöntemi: `git log -- <dosya>` ve her ara kayıtta
`git show <commit>:<dosya>`.

- **t2_konumlanma:**
  - `20c1f31` (07:02:58) içindeki NOTLAR'da bölüm 4 "Seçim kuralı" zaten
    var. O anda defter 216 satırdı ve dev_valid satırı yoktu.
  - O commit'ten HEAD'e kadar NOTLAR'dan silinen satır yok; dosyaya yalnız
    ekleme yapıldı.
  - Dondurma tablosunun kendisi (bölüm 10) ilk kez `f0a75be`'de (09:09:01)
    görünüyor. O commit'te defterde dev_valid satırları zaten var.
- **t2_cift:**
  - `c9302ed` (07:06:30) yalnız planı ve tarama 1–2 notlarını içeriyor.
  - Dondurma bölümü ilk kez `f0a75be`'de (09:09:01), dev_valid'den sonra
    görünüyor.
  - Tarama 6 "karar kuralı"nın sonuçtan önce yazıldığı yalnız beyandır.
  - NOTLAR:176'da "ilk yazımdaki 629 hesap hatasıydı" notu var. Dondurma
    bölümünün ilk yazımdan sonra düzeltildiğini gösteriyor; düzeltmenin zamanı
    bilinmiyor. Düzeltilen yalnız deneme sayısı.
- **t2_emir_akisi:**
  - `9a6c9c9` (12:04:40): plan ve aşama 2b planı var, dondurma yok.
  - `a33b447` (16:36:04): "Dondurma kararı" bölümü var. "dev_valid sonucu"
    bölümü ise yok.
    - Aynı commit'teki defterde dev_valid satırları var (16:35:41–16:35:48).
    - Yani anlık görüntü dev_valid'den 23 saniye sonra alınmış ve sonuç
      bölümü henüz eklenmemiş.
  - Sonuç bölümü `d111647`'de (16:37:23) eklenmiş. Diff yalnız ekleme
    içeriyor.
  - Bu, dondurma metninin sonuçlardan önce yazıldığı beyanıyla tutarlı ama
    kesin kanıt değildir.
- **t2_lead_lag:**
  - `d111647` (16:37:23) içindeki NOTLAR'da dondurma yok. O sırada defter
    335 satırdı; arama 16:40:32'ye kadar sürdü.
  - Dondurma bölümü 16:40:32 ile 16:43:43 arasında, yaklaşık 3 dakikada
    yazılmış olmalı. Bu da beyandır.
  - `229a043`'te (16:44:41) dondurma ve doğrulama birlikte görünüyor.
- **t2_limit_gun_ici:**
  - `229a043` (16:44:41) içindeki NOTLAR, ilk arama satırından (16:48:24)
    önceki plan bölümlerini (0–3) içeriyor.
  - Dondurma bölümü yalnız `0e92dc0`'da (22:37:06), dev_valid'den sonra var.
- **t2_bindirme, t2_meta:** Bütün dosyalar ilk kez `0e92dc0`'da (22:37:06),
  dev_valid'den sonra commit'lendi. Sıra kanıtı yalnız beyan ve defter
  zamanlarıdır.
- **Strateji modülleri:**
  - dev_valid'den önce alınmış anlık görüntüsü olan modüllerde sonraki
    değişiklikler yalnız sonuç açıklama metinleridir:
    - t2_emir_akisi `a33b447` → HEAD: yalnız `CHECK` sözlüğüne açıklama
      metni.
    - t2_lead_lag `229a043` → HEAD: yalnız `SONUC` sözlüğü. Bu sözlük
      yalnız `description` alanına giriyor.
  - Diğer modüllerin dev_valid öncesi anlık görüntüsü yok:
    - t2_cift ve t2_konumlanma ilk kez `f0a75be`'de görünüyor.
    - t2_limit_gun_ici, t2_bindirme ve t2_meta ilk kez `0e92dc0`'da
      görünüyor.
  - Bu yüzden dondurma anındaki kodla HEAD'deki kodun aynı olduğu git'le
    gösterilemiyor.
  - Dolaylı kanıt: HEAD'deki `specs()` parametreleri dev_valid satırlarıyla
    birebir aynı. Aileler, doğrulamanın dev_train ölçülerinin arama
    satırlarıyla birebir aynı çıktığını yazıyor; bu, defterde doğrulandı.
  - Ama arama ile doğrulama arasında sinyal kodunun değişmediği, ancak veriyle
    yeniden çalıştırmayla sınanabilir. Bu bölümde yapılmadı.
- **Ö2'nin özeti:**
  - Hiçbir ailede dondurma kararını dev_valid'den önce gösteren bir git
    anlık görüntüsü yok.
  - Çelişen bir iz de yok:
    - NOTLAR dosyaları ara kayıtlar arasında yalnız eklemeyle büyümüş
      (silinen satır yok).
    - Dondurma bölümleri dev_valid sonuç bölümlerinden önce duruyor.
    - Defterde dev_valid sonrası arama yok.
  - Adaylar için anlamı: "dondurma dev_valid'den önce" iddiası beyan
    düzeyindedir. İleriye dönük takip bu yüzden asıl kanıt olarak kalmalı.

### 2.3 dev_valid sonrası açıklanan değişiklikler

Açıklanan değişikliklerin hepsi yalnız açıklama metni ya da defter dışı
betimleyici dökümdür. Sinyali etkileyen bir değişiklik bulunmadı:

- spec açıklamaları: t2_cift, t2_konumlanma, t2_bindirme, t2_limit_gun_ici,
  t2_meta `FROZEN_CHECK`, t2_lead_lag `SONUC`, t2_emir_akisi `CHECK`.
- betimleyici dökümler: `dogrulama_korelasyon`, `dogrulama_tani`,
  `tani_dogrulama`, `dogrulama_dokum`, `dogrulama_kenar`.

**K1 (küçük):** Defter dışında dev_valid yeniden hesaplandı.

- t2_konumlanma NOTLAR:245, "`evaluate(..., record=False)` ile 5 spec'in
  bütün sayıları farksız yeniden üretildi" diyor. Bunu yapan betik depoda yok:
  `record=False` aramasında t2_konumlanma klasöründe eşleşme yok.
- t2_meta `yeniden_uretim.py`, dev_valid dahil `evaluate(spec, record=False)`
  çağırıyor.
- Bunlar yeniden üretim kontrolüdür ve açıklanmıştır. Yine de "dev_valid'de bir
  kez" kuralının harfi dışında, deftere girmeyen ek dev_valid hesaplarıdır.
- Adayları değiştirmez.

## 3. Raporlanan sayılar ve defter

Dondurulan 32 yapılandırma aşağıda.

- dev_valid ölçüleri defterden alındı:
  - getiri: `total_return`
  - Sharpe: `sharpe`
  - işlem: `trades`
  - alfa: `alfa`, 1×, yıllık
  - beta: `beta`, 1×
- Son sütun, `candidate_check`'in protokol 2'deki yedi şartının defter
  ölçülerine uygulanmasıdır.
  - Eğitim ölçüsü olarak doğrulama çalıştırmasının dev_train 1× satırı
    kullanıldı.
  - Şart numaraları: 1 eğitim net > 0, 2 dv net > 0, 3 dv 2× net > 0,
    4 dv Sharpe ≥ 0,5, 5 dv işlem ≥ 20, 6 eğitim alfa > 0, 7 dv alfa > 0.

| Aile | Yapılandırma (önek atıldı) | Defter satırı dv 1×/2× | dv 1× % | dv 2× % | Sharpe 1× | Sharpe 2× | İşlem | Alfa % | Beta | candidate_check (defterden) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| t2_cift | `1h_SOLBTC_..._k6_..._max_bar6_limit_bps20.0...` (B) | 1274/1276 | +7,50 | +6,77 | 0,909 | 0,831 | 28 | +4,24 | 0,001 | GEÇTİ |
| t2_cift | `1h_SOLBTC-SOLETH_..._k6_..._max_bar6_limit_bps20.0...` (C) | 1278/1280 | +4,33 | +3,80 | 0,725 | 0,645 | 55 | +2,49 | −0,001 | GEÇTİ |
| t2_cift | `1h_SOLBTC-SOLETH_..._k12_..._max_bar3_limit_bps10.0...` (D) | 1282/1284 | +0,56 | +0,25 | 0,189 | 0,087 | 41 | +0,36 | −0,004 | geçmedi (4) |
| t2_konumlanma | `kalabalik_1h_SEPET3_genel_w7_c0.5_cx0.5_s-1_limit_lb1` (D1) | 492/494 | −23,27 | −58,21 | −0,105 | −0,853 | 1579 | −5,50 | 0,115 | geçmedi (2,3,4,7) |
| t2_konumlanma | `kalabalik_1h_SEPET3_genel_w30_c1.0_cx0.0_s-1` (D2) | 496/498 | +24,23 | +5,92 | 0,503 | 0,284 | 340 | +21,04 | −0,018 | GEÇTİ |
| t2_konumlanma | `oi_1h_SEPET3_birikim_k8_w30_a1.0_b1.5_t12` (D3) | 500/502 | +6,37 | −11,00 | 0,277 | −0,246 | 382 | +5,09 | 0,052 | geçmedi (3,4) |
| t2_konumlanma | `fark_1h_SEPET3_w14_c0.5_cx0.0_s1` (D4) | 504/506 | −30,44 | −54,39 | −0,211 | −0,720 | 904 | −9,62 | −0,042 | geçmedi (2,3,4,7) |
| t2_konumlanma | `taker_4h_SEPET3_k12_w30_c2.0_cx0.0_s1` (D5) | 508/510 | −3,88 | −10,36 | 0,012 | −0,165 | 149 | −0,20 | 0,078 | geçmedi (2,3,4,7) |
| t2_emir_akisi | `uyum_5m_n72_k3.5_h12` | 781/783 | +2,09 | −4,68 | 0,177 | −0,264 | 147 | +1,58 | 0,000 | geçmedi (3,4) |
| t2_emir_akisi | `uyum_15m_n24_k3.5_h2` | 785/787 | +2,57 | −4,10 | 0,185 | −0,157 | 144 | +2,12 | −0,004 | geçmedi (3,4) |
| t2_emir_akisi | `artik_15m_n12_k3.5_h8` | 789/791 | −3,24 | −12,56 | −0,354 | −1,486 | 217 | −1,69 | −0,011 | geçmedi (2,3,4,7) |
| t2_emir_akisi | `uyum_spot_5m_n72_k3.5_h12_uzun` | 793/795 | −5,34 | −15,30 | −0,427 | −1,316 | 139 | −3,06 | 0,027 | geçmedi (2,3,4,7) |
| t2_emir_akisi | `kontrol_getiri_donus_5m_n72_k5_h12` | 797/799 | +3,98 | +0,21 | 0,355 | 0,053 | 79 | +2,47 | 0,001 | geçmedi (4) |
| t2_lead_lag | `baz_5m_kendi_w288_e6_t12_limt2b2` (#1) | 380/382 | +16,58 | +14,55 | 1,125 | 1,002 | 113 | +8,94 | 0,026 | GEÇTİ |
| t2_lead_lag | `baz_15m_kendi_w192_e5_t8_limt2b2` (#2) | 384/386 | −8,72 | −9,76 | −0,721 | −0,812 | 80 | −5,06 | 0,014 | geçmedi (2,3,4,7) |
| t2_lead_lag | `sv_5m_hepsi_k6_e4_t36_limt2b2` (#3) | 388/390 | −0,76 | −1,42 | −0,004 | −0,047 | 36 | −0,16 | 0,021 | geçmedi (2,3,4,7) |
| t2_lead_lag | `baz_5m_hepsi_w288_e5_t12_uzun_limt2b2` (#4) | 392/394 | +19,81 | +18,91 | 1,247 | 1,203 | 48 | +10,63 | 0,010 | GEÇTİ |
| t2_lead_lag | `sv_5m_hepsi_k4_e4_t12_uzun_limt2b2` (#5) | 396/398 | +17,19 | +16,73 | 1,195 | 1,173 | 27 | +9,32 | 0,009 | GEÇTİ |
| t2_limit_gun_ici | `fitil_1h_k4_H3_t50` | 199/201 | +2,76 | −1,97 | 0,299 | −0,172 | 157 | +1,68 | 0,007 | geçmedi (3,4) |
| t2_limit_gun_ici | `fitil_5m_k8_H24_t50` | 203/205 | −5,89 | −10,19 | −0,459 | −0,840 | 156 | −3,31 | 0,015 | geçmedi (2,3,4,7) |
| t2_limit_gun_ici | `donus_1h_n4_e3_t50_H12_lim1.0s_m3` (#3) | 207/209 | +7,18 | +5,74 | 0,809 | 0,658 | 45 | +4,06 | 0,006 | GEÇTİ |
| t2_limit_gun_ici | `donus_15m_n16_e3_t50_H48_lim1.0s_m12` | 211/213 | −5,05 | −7,00 | −0,544 | −0,766 | 69 | −2,91 | 0,013 | geçmedi (2,3,4,7) |
| t2_limit_gun_ici | `donus_1h_n4_e3_t50_H12_piyasa` | 215/217 | −1,74 | −4,15 | −0,178 | −0,462 | 53 | −0,93 | 0,009 | geçmedi (2,3,4,7) |
| t2_bindirme | `vol_nakit_1d_h0.4_n40_b0.1` | 266/268 | −13,31 | −13,60 | −0,013 | −0,018 | 0 | −4,26 | 0,640 | geçmedi (2,3,4,5,7) |
| t2_bindirme | `trend_yarim_4h_L15_b0.15_f7` | 270/272 | +13,77 | +11,57 | 0,584 | 0,506 | 55 | +7,45 | 0,163 | GEÇTİ |
| t2_bindirme | `trendvol_tam_4h_L10_h0.3_n30_b0.1_f7` | 274/276 | +18,84 | +16,00 | 0,686 | 0,601 | 98 | +10,14 | 0,177 | GEÇTİ |
| t2_bindirme | `portfoy_esit_risk_sermaye` | 278/280 | −1,50 | −4,73 | −0,106 | −0,408 | 297 | −0,65 | −0,003 | geçmedi (2,3,4,7) |
| t2_meta | `4h_kanal_n20_b3.0-1.5-H60_logit_tam_taban0.0` (1) | 209/211 | −1,38 | −11,30 | 0,104 | −0,118 | 227 | +2,45 | 0,063 | geçmedi (2,3,4) |
| t2_meta | `4h_kanal_top[n14-20-30-48]_n48_b3.0-1.5-H60_logit_tam_taban0.0` (2) | 213/215 | +3,14 | −6,34 | 0,192 | −0,040 | 283 | +4,29 | 0,042 | geçmedi (3,4) |
| t2_meta | `1h_kanal_n96_iz4.0-H240_logit_tam_taban0.0` (3) | 217/219 | −7,14 | −17,01 | 0,027 | −0,170 | 241 | +0,73 | 0,023 | geçmedi (2,3,4) |
| t2_meta | `1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0` (4) | 221/223 | +25,72 | +8,53 | 0,592 | 0,303 | 315 | +17,15 | 0,011 | GEÇTİ |
| t2_meta | `4h_ema_e20-100_b3.0-1.5-H60_logit_tam_taban0.0_min_olay150` (5) | 225/227 | +6,64 | +2,50 | 0,346 | 0,173 | 85 | +4,65 | −0,020 | geçmedi (4) |

Sonuçlar:

- **Geçti/geçmedi:** Yedi RAPOR'un `candidate_check` tablolarındaki sonuç, 32
  yapılandırmanın hepsinde defterden yeniden hesaplanan sonuçla aynı.
  Başarısız şartlar da aynı.
  - Aday sayısı 10: t2_cift B ve C; t2_konumlanma D2; t2_lead_lag #1, #4 ve
    #5; t2_limit_gun_ici donus_1h limit; t2_bindirme trend_yarim ve
    trendvol_tam; t2_meta 1h_kanal_n96_iz3.0.
  - Sınırda olanlar:
    - konumlanma D2'nin Sharpe'ı 0,5026; eşik 0,5.
    - bindirme trend_yarim'in 2× Sharpe'ı 0,506. Bu şart değil, yalnız
      sıralamaya girer.
- **Sayısal karşılaştırma:**
  - Karşılaştırılan alanlar: RAPOR'lardaki dev_valid 1×/2× getiri, Sharpe,
    işlem, alfa ve beta tabloları; NOTLAR'daki dondurma tablolarındaki eğitim
    sayıları; Deflated Sharpe girdileri.
  - Hiçbir yerde 0,5 yüzde puanını aşan fark yok.
  - Ayrıca kontrol edilenler (hepsi defterle aynı):
    - t2_cift dondurma tablosu (NOTLAR:181–185) ve RAPOR bölüm 4.
    - t2_konumlanma bölüm 10–11 ve RAPOR bölüm 6.
    - t2_emir_akisi RAPOR "dev_valid sonuçları".
    - t2_limit_gun_ici RAPOR tablosu (satır 247–258).
    - t2_bindirme RAPOR satır 233–247.
    - t2_meta RAPOR satır 230–247.
- **K2 (küçük, t2_lead_lag):** RAPOR.md satır 177–181 ve modüldeki `SONUC`
  sözlüğünde (`grafik_analiz/strategies/t2_lead_lag.py:378–389`) yanlış
  yuvarlamalar var:

  | Değer | Raporda | Defterde |
  |---|---:|---:|
  | #2 Sharpe | −0,722 | −0,721149 |
  | #3 Sharpe | −0,005 | −0,004294 |
  | #4 Sharpe | 1,246 | 1,246853 |
  | #4 2× Sharpe | 1,202 | 1,202783 |
  | #4 2× getiri | %+18,90 | 0,189054 |
  | #5 Sharpe | 1,194 | 1,194798 |
  | #1 getiri | %+16,57 | 0,165785 |
  | #1 en büyük düşüş | %−10,11 | −0,101046 |
  | #2 en büyük düşüş | %−16,35 | −0,163443 |
  | #3 en büyük düşüş | %−15,96 | −0,159511 |
  | #5 en büyük düşüş | %−14,65 | −0,146417 |
  | #1 eğitim alfası | +0,154 | 0,154951 (NOTLAR'da doğru: +0,155) |
  | #2 eğitim alfası | +0,249 | 0,249582 |
  | #3 eğitim alfası | +0,259 | 0,259906 |

  - Farkların hepsi Sharpe'ta ≤ 0,001, getiride ≤ 0,01 puan.
  - Hiçbir şart ya da sıralama sonucunu değiştirmiyor.

## 4. Deneme sayıları ve Deflated Sharpe

Deneme sayısı N = defterde `pencere == "dev_train"` ve `maliyet_kat == 1.0`
olan satırlar. Varyans, bu satırların yıllık Sharpe'larının örneklem
varyansıdır (ddof = 1; Sharpe'ı boş satırlar varyansa girmez).

| Aile | N (defter) | N (RAPOR) | Sharpe'ı boş satır | Varyans (defter) | Varyans (RAPOR) | Ortalama / en büyük | Şansla beklenen en büyük yıllık Sharpe |
|---|---:|---:|---:|---:|---:|---|---:|
| t2_cift | 639 | 639 | 0 | 0,6319 | 0,6319 | −0,589 / 1,098 | 2,49 |
| t2_konumlanma | 250 | 250 | 0 | 0,7648 | 0,7648 | 0,712 / 2,112 | 2,48 |
| t2_emir_akisi | 606 | 606 | 6 | 4,6022 | 4,60 | −0,369 / 2,288 | 6,67 |
| t2_lead_lag | 366 | 366 | 0 | 1,3682 | 1,368 | 0,284 / 1,720 | 3,46 |
| t2_limit_gun_ici | 157 | 157 | 0 | 4,8824 | 4,882 | 0,361 / 1,984 | 5,93 |
| t2_bindirme | 136 | 136 | 0 | 0,3913 | 0,391 | 1,494 / 6,594 | 1,65 |
| t2_meta | 191 | 191 | 6 | 0,3376 | 0,338 | 0,341 / 1,315 | 1,60 |
| **Tur (7 aile)** | **2.345** | — | 12 | **2,3720** (birleşik) | — | — | **5,38** |

- Sayılar ve varyanslar yedi raporda da defterle aynı.
- RAPOR'lardaki DSR değerleri yeniden hesaplandı. Girdiler: aile N'si, aile
  varyansı, dev_valid 1× Sharpe, gün, çarpıklık ve basıklık (ailelerin sonuç
  json'larından). Hepsi raporlananla aynı:

  | Aile | DSR |
  |---|---|
  | t2_cift | 0,0013 / 0,0022 / 0,0015 |
  | t2_konumlanma (D2) | 0,0040 |
  | t2_emir_akisi | ≈ 0 |
  | t2_lead_lag | 4e−6, 0, 2e−6, 1e−6, < 1e−6 |
  | t2_limit_gun_ici | ≈ 0 |
  | t2_bindirme | 0,014 / 0,076 / 0,0945 / 0,010 |
  | t2_meta | 0,024 / 0,031 / 0,019 / 0,084 / 0,048 |

**Ö4 (önemli, tur geneli):**

- Yedi ailenin toplam deneme sayısı 2.345 dev_train 1× satırıdır; 2.333'ünün
  Sharpe'ı dolu.
  - Bütün denemelerin birleşik Sharpe varyansıyla (2,372) tur düzeyinde
    şansla beklenen en büyük yıllık Sharpe 5,38'dir.
  - Bu N ve varyansla 10 adayın DSR'si 2e−24 ile 1,3e−10 arasındadır.
  - Aile içi en yüksek DSR'ler (bindirme 0,0945, meta 0,084) tur düzeyinde
    sıfıra iner.
- Aile DSR'lerinin farkı büyük ölçüde deneme Sharpe varyansından geliyor.
  bindirme (0,39) ve meta (0,34) varyansı küçük aileler olduğu için en hafif
  düzeltmeyi alıyor.
- Ayrıca t2_bindirme deneme sayısını eksik sayıyor:
  - Tur 1'in dondurulmuş 19 yapılandırmasını bileşen olarak yeniden ölçüyor.
  - Trend sinyali tur 1'in trend topluluğudur (`trend.leg_target`).
  - Bunların seçildiği tur 1 denemeleri (SONUC_1: yaklaşık 1.930) bindirme'nin
    N'sine girmiyor. Aynı durum t2_limit_gun_ici'nin tur 1 `od_dip` kuralına
    dayanan yapılandırmaları için de geçerli.
- Adaylar için anlamı: DSR aday şartı değil, adaylık değişmiyor. Ama hiçbir
  adayın dev_valid sonucu çoklu deneme düzeltmesinden sonra anlamlı değildir.

## 5. İzin verilen yolların dışında değişen dosyalar

`git log --name-only b72977a..HEAD` sonucu. İzin verilen yollar:

- `arastirma/tur2/<aile>/`
- `grafik_analiz/strategies/t2_*.py`
- `arastirma/tur2/deneyler/`

Bu yolların dışında değişen dosyalar:

| Dosya | Commit | Yazan |
|---|---|---|
| `grafik_analiz/research/universe.py` | `ddea1d2` (09:08:48) "Evren indirmesi: mumlar varken eksik fonlamayı yeniden dene" | Koordinatör. Diff yalnız `_download_symbol`'un indirme/fonlama tamamlama akışını değiştiriyor; sinyal, backtest ya da ölçü koduna dokunmuyor. Kapsamdaki stratejilerin hiçbiri `load_universe` kullanmıyor (modüllerde geçen "universe" yalnız yerel parametre adı). |
| `arastirma/tur2/FINALISTLER.md` | `8764e54` (12:04:18) | Koordinatör |
| `arastirma/tur2/finalist_secimi.py` | `8764e54` (12:04:18) | Koordinatör |
| `arastirma/veri_indir.py` | `b4d4add` (22:46:58) | Koordinatör |

- `b72977a`'dan bu yana `grafik_analiz/research/` altında başka değişiklik
  yok. `protocol.py`, `evaluate.py`, `metrics.py`, `ledger.py` ve `data.py`
  protokol sürüm 2 commit'indeki haliyle duruyor.
- "Tur 2: ara kayıt" commit'lerindeki öteki bütün dosyalar araştırmacıların
  dosyalarıdır ve izinli yollardadır. Bu commit'ler koordinatörün araştırmacı
  dosyalarından aldığı anlık görüntülerdir.

## 6. FINALISTLER.md ve finalist_secimi.py

### 6.1 Kurala uygunluk

`docs/PROTOKOL_2.md` "İleriye dönük takibe seçim" bölümü ile karşılaştırıldı:

- **Aday:** `candidate_check` (protokol 2) geçenler. ✓
  - Betik ölçüleri `evaluate()` ile aynı adımlarla, deftere yazmadan yeniden
    hesaplıyor (`olc`, `finalist_secimi.py:44–61`).
  - Aday listesi bütün `t2_*` ailelerinin `specs()` çıktısıdır.
- **≥ 30 işlem:** ✓ (`MIN_ISLEM = 30`, satır 115).
- **Sıralama:** dev_valid 2× maliyetle Sharpe, azalan. ✓ (satır 107)
- **Açgözlü korelasyon:** daha önce seçilenlerin hepsiyle korelasyon
  < 0,70. ✓ (satır 121, `>= KORELASYON_SINIRI` olan elenir)
- **En fazla 5:** ✓ (`MAX_FORWARD_FINALISTS`).
- Sıra (önce denetim çıkarması, sonra işlem filtresi, sonra kontenjan, sonra
  korelasyon) protokol kuralıyla aynı sonucu verir.
- Protokolün tanımlamadığı ama betiğin seçtiği ayrıntılar:
  - Korelasyon dev_valid 1× günlük getirisiyle hesaplanıyor.
  - Hesap `pd.DataFrame(gunluk).fillna(0.0).corr()` ile yapılıyor; günleri
    olmayan strateji o günler 0 sayılıyor.
  - FINALISTLER.md "iç doğrulama günlük getiri korelasyonu" diyor; bu kısım
    tutarlı.
- **K5 (küçük):** FINALISTLER.md kural 2 ve `--haric`, protokolde olmayan bir
  "denetim nedeniyle çıkarma" adımı ekliyor.
  - Gerekçenin yazılması şartı var.
  - Bu, mekanik seçime sonradan takdir girmesine izin veren tek kapıdır.
  - Yalnız açık kritik ihlal ve ileri bakış için kullanılmalı.

### 6.2 Bacak başına işlem sayımı (Ö1, önemli)

`metrics.summarize`, birleşik `trades` tablosunun satırlarını sayıyor
(`evaluate.backtest`: her bacağın işlemleri ayrı satır). Bu yüzden:

- Aynı anda birden çok bacağa giren bir sinyal, bacak sayısı kadar işlem
  sayılır.
- Aday şartı 5 (≥ 20) ve takip şartı (≥ 30) bu sayıya uygulanıyor.

Adaylara etkisi (bağımsız olay sayısı ailelerin kendi raporlarından):

| Aday | Harness işlemi | Bağımsız olay | Kaynak | ≥ 20 (aday) | ≥ 30 (takip) |
|---|---:|---|---|---|---|
| t2_lead_lag #5 `sv_5m_hepsi_k4_e4_t12_uzun` | 27 | 9 olay günü, her olayda 3 coin | t2_lead_lag/RAPOR.md:226–227 | yalnız bacak sayımıyla geçiyor | 27 ile zaten geçmiyor |
| t2_lead_lag #4 `baz_5m_hepsi_w288_e5_t12_uzun` | 48 | 16 işlem günü; sinyal üç coinin ortalaması, giriş üçüne birden | t2_lead_lag/RAPOR.md:223 | yalnız bacak sayımıyla geçiyor (yaklaşık 16) | yalnız bacak sayımıyla geçiyor |
| t2_cift C `SOLBTC-SOLETH k6` | 55 | yaklaşık 28 çift işlemi | t2_cift/RAPOR.md:252 | geçiyor | yalnız bacak sayımıyla geçiyor |
| t2_cift B `SOLBTC k6` | 28 | 14 çift işlemi | t2_cift/RAPOR.md:132 | yalnız bacak sayımıyla geçiyor | 28 ile zaten geçmiyor |
| t2_bindirme trend_yarim / trendvol_tam | 55 / 98 | Bilinmiyor. Altı bacak (her coinde spot + vadeli); bir maruziyet değişikliği iki bacakta işlem doğurabiliyor. | — | belirsiz | belirsiz |
| t2_konumlanma D2, t2_lead_lag #1, t2_limit_gun_ici #3, t2_meta #4 | 340 / 113 / 45 / 315 | Coin başına sinyal. Bacak sayımı olay sayımına yakın olmalı, ama kod satır satır sınanmadı. | — | geçiyor | geçiyor |

- PROTOKOL_2 "işlem"i tanımlamıyor. Harness sürüm 1'den beri bacak başına
  sayıyor. Bu yüzden `candidate_check` sonuçları mekanik olarak doğrudur.
- Ama FINALISTLER.md kural 3, bacak başına sayımı açıkça benimsiyor ("iki
  bacaklı bir çift işlemi en az 2 işlem sayılır"). Bu metin şu sırada yazıldı:
  - `8764e54` 12:04:18'de commit'lendi.
  - O sırada t2_cift sonuçları biliniyordu: dev_valid 08:59; C 55 bacak
    işlemi, yaklaşık 28 çift işlemi.
  - FINALISTLER.md bunu kendisi de belirtiyor: "O sırada sonuçları bilinen
    aileler yalnızca `t2_cift` ve `t2_konumlanma` idi."
- Bu tanım C'yi 30 eşiğinin üstünde tutuyor. Tanımın sonuca bakılarak
  seçildiğine dair bir kanıt yok; harness'in var olan sayımını yazıya
  geçiriyor. Yine de bilinen bir sonuçtan sonra yazılmış bir yorumdur.
- Adaylar için anlamı:
  - lead_lag #4'ün bağımsız gözlem sayısı yaklaşık 16, #5'inki 9. Bu adayların
    "en az 20 işlem" şartının amacını karşıladığı söylenemez.
  - lead_lag #4 ve cift C takip eşiğini yalnız bacak sayımıyla geçiyor.

### 6.3 Defterden çıkan geçici sıralama (korelasyon hariç)

10 adaydan ≥ 30 işlem şartıyla cift B (28) ve lead_lag #5 (27) düşüyor.
Kalanlar dev_valid 2× Sharpe'a göre şöyle sıralanıyor:

1. lead_lag #4 — 1,203
2. lead_lag #1 — 1,002
3. limit_gun_ici donus_1h limit — 0,658
4. cift C — 0,645
5. bindirme trendvol_tam — 0,601
6. bindirme trend_yarim — 0,506
7. meta 1h_iz3 — 0,303
8. konumlanma D2 — 0,284

Korelasyon adımı veri gerektirdiği için burada çalıştırılmadı. Ailelerin
kendi raporladığı dev_valid korelasyonları:

- bindirme trend_yarim – trendvol_tam: 0,958 (t2_bindirme/RAPOR.md:289).
- lead_lag #1 – #4: **0,695** (`t2_lead_lag/dogrulama_sonuc.json`,
  `korelasyon_dev_valid`).

**Ö5 (önemli):**

- lead_lag #1 ile #4'ün korelasyonu eşiğin (0,70) yalnız 0,005 altında.
- Betiğin hesabı (`fillna(0.0)`, bütün adayların gün birleşimi) ile ailenin
  hesabı arasındaki küçük farklar bu çiftin ikisinin birlikte seçilip
  seçilmeyeceğini belirleyebilir.
- Protokol korelasyonun dönemini, maliyetini ve eksik gün işlemini
  tanımlamıyor.
- Seçim çalıştırıldığında bu çift için hesaplanan değer FINALISTLER.md'ye
  yazılmalı.
- Ayrıca lead_lag #1 ve #4 aynı likidasyon olaylarından besleniyor
  (RAPOR.md:29, korelasyon 0,69–0,91). Takipte bağımsız iki kanıt
  sayılmamalı.

## 7. Bilgi bulaşması (Ö3, önemli, tur geneli)

- **Dönemlerin örtüşmesi:** Tur 2 dev_valid'i 01.01.2025 – 30.09.2026.
  - Tur 1'in iç doğrulamasının son altı ayını (01.01–30.06.2025) içeriyor.
  - Tur 1'in görülmemiş dönemini (01.07.2025 – 30.09.2026) tamamen içeriyor.
  - Bu iki dönemin sonuçları `DENETIM_1.md`, `SONUC_1.md`, tur 1
    `FINALISTLER.md` ve tur 1 aile raporlarında yazılı.
- **Araştırmacıların okudukları:** Kendi notlarına göre SONUC_1 ve DENETIM_1'i
  okuyan aileler:
  - t2_konumlanma (NOTLAR:9–17)
  - t2_limit_gun_ici (NOTLAR:10–18). Tur 1 `ortalamaya_donus`, `kirilim` ve
    `mevsimsellik` raporlarını da okudu.
  - t2_bindirme (NOTLAR:10–25)
  - t2_meta (NOTLAR:9–21)
- **Somut örtüşmeler:**
  - **t2_limit_gun_ici aday #3** (`donus_1h_n4_e3_t50_H12_lim1.0s_m3`):
    - Kural, tur 1'in `od_dip_ret4h_fut_port3_1h` kuralına trend filtresi ve
      limit emir eklenmiş halidir.
    - Piyasa emirli kontrolü (#5) tur 1 kuralıyla aynıdır (NOTLAR:186–191).
    - `od_dip`, tur 1'de 2024-01 – 2025-06 iç doğrulamasında aday şartlarını
      geçmişti (DENETIM_1.md:174; tur 1 FINALISTLER.md:53).
  - **t2_meta aday** (`1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0`):
    - Birincil sinyal Donchian kanal kırılımı.
    - Tur 1 finalisti `kirilim_kanal4h_vadeli_uzun`'un görülmemiş dönem sonucu
      (+%9,8) SONUC_1'de yazılı.
  - **t2_bindirme adayları:**
    - Tur 1 trend topluluğunu kullanıyor.
    - Portföy havuzu tur 1 yapılandırmalarıdır.
    - Bileşen seçimi 2024 alfasını da şart koşuyor. 2024, tur 1'in iç
      doğrulamasıydı.
- Araştırmacılar bu bilgiyi seçimde kullanmadıklarını yazıyor, ve seçimler
  önceden yazılmış mekanik kurallarla yapılmış görünüyor. Bunu doğrulamak
  mümkün değil.
- Adaylar için anlamı: Bu adayların dev_valid sonucu, tur 1'de kısmen görülmüş
  bir dönemde, kısmen görülmüş kurallarla elde edildi. Tek geçerli kanıt
  ileriye dönük takiptir.

## 8. Diğer küçük bulgular

- **K3 (t2_emir_akisi, t2_meta): adlandırma.**
  - emir_akisi'nin dondurulan beş yapılandırması aramadaki adlarından farklı
    adla değerlendirildi:
    - `t2_emir_akisi_a3_uyum_5m_n72_k3.5_h12` (satır 636) →
      `t2_emir_akisi_uyum_5m_n72_k3.5_h12` (780).
    - Benzer biçimde satır 442 → 788, 580 → 784, 660 → 796
      (`a4_getiri_donus_..._k5.0` → `kontrol_getiri_donus_..._k5`) ve
      754 → 792 (`a4_uyum_spot_...` → `..._uzun`).
    - Parametreler ve dev_train ölçüleri birebir aynı. NOTLAR'daki "her
      birinin defterde aynı parametreli dev_train satırı var" beyanı doğru.
      Ama ada dayalı denetimlerde bu eşleşme görünmüyor.
  - meta'da 14 strateji adı iki farklı `min_olay` değeriyle iki ayrı deneme
    olarak kullanıldı. Örnek: `t2_meta_4h_kanal_n120_b3.0-1.5-H30_hepsi`,
    eğitim getirisi 0,242 ve 0,513.
    - Dondurulan iki yapılandırmanın tekrar satırlarında `topluluk: ""`
      anahtarı eklenmiş: satır 205/206 ve 208/220, arama satırları 149/166
      ile karşılaştırma. Ölçüler aynı.
    - Satır sayımına dayanan deneme sayısı (191) etkilenmiyor.
- **K4 (t2_bindirme, t2_cift): NOTLAR metni.**
  - bindirme NOTLAR:188 "Tarama 2 … 17:02–17:20 UTC" diyor; dondurma ise
    17:18 (NOTLAR:238). Defterdeki son arama satırı 17:17:33, yani defterle
    çelişki yok. Yalnız metindeki saat tutarsız.
  - cift NOTLAR:176'daki sonradan düzeltme için bkz. 2.2.
- **K6 (defter):** `ledger.record` yalnız `interval`, `legs` ve `params`
  alanlarını yazıyor; `spec.weights` yazılmıyor.
  - Kapsamda yalnız t2_lead_lag ağırlık veriyor. Dondurulan beş
    yapılandırmada ağırlıklar eşit 1/3 (kontrol edildi). Etkisi yok.
- **Bilgi notu (bulgu değil):**
  - t2_bindirme `vol_nakit` (kıyas) dev_valid'de 0 işlem, eğitimde 3 işlem
    gösteriyor. Harness sürekli pozisyonu tek işlem sayıyor.
  - Bu yapılandırma aday değil. NOTLAR'da önceden "kıyas" olarak işaretli.

## 9. Adaylar için toplu sonuç

| Aday | Defter ile RAPOR | Sıra kanıtı | Bu bölümdeki çekinceler |
|---|---|---|---|
| t2_cift B | uyumlu | beyan + defter | 28 işlem = 14 çift işlemi (Ö1). Takip eşiğinin altında. |
| t2_cift C | uyumlu | beyan + defter | Takip eşiğini yalnız bacak sayımıyla geçiyor (Ö1). B ile korelasyon 0,91. |
| t2_konumlanma D2 | uyumlu | seçim kuralı git'te 07:02'de var; dondurma tablosu beyan | Sharpe 0,5026 (sınırda) |
| t2_lead_lag #1 | uyumlu; yuvarlama K2 | git'te 3 dakikalık pencere, beyan | #4 ile korelasyon 0,695 (Ö5) |
| t2_lead_lag #4 | uyumlu; yuvarlama K2 | aynı | yaklaşık 16 bağımsız olay (Ö1); Ö5 |
| t2_lead_lag #5 | uyumlu; yuvarlama K2 | aynı | 9 bağımsız olay (Ö1); takip eşiğinin altında |
| t2_limit_gun_ici donus_1h limit | uyumlu | plan git'te; dondurma beyan | Tur 1 `od_dip` kuralının türevi (Ö3) |
| t2_bindirme trend_yarim | uyumlu | beyan + defter | trendvol_tam ile korelasyon 0,958; tur 1 trend topluluğu (Ö3, Ö4) |
| t2_bindirme trendvol_tam | uyumlu | beyan + defter | Ö3, Ö4 |
| t2_meta 1h_iz3 | uyumlu | beyan + defter | Kanal kırılımı tur 1'de görülmüş sinyal (Ö3) |

Bu bölümde hiçbir adayın elenmesini gerektiren kritik bir protokol ihlali
bulunmadı. Ö1, Ö3 ve Ö5'in seçim sırasında FINALISTLER.md'ye not edilmesi
önerilir.
