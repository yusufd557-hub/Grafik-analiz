# t2_genis_evren — çalışma notları

Aile: geniş, zamana bağlı (hayatta kalan yanlılığı olmadan) vadeli evrende
kesitsel stratejiler (protokol sürüm 2). Bu dosya iç doğrulama (dev_valid)
değerlendirmesinden **önce** yazılır; dondurma kararı da burada, dev_valid'e
bakmadan kaydedilir.

## Başlangıç durumu (9 Ekim 2026)

- Bu aile için önceki bir çalışma yok: `arastirma/tur2/t2_genis_evren/` yoktu,
  `arastirma/tur2/deneyler/t2_genis_evren.jsonl` yoktu.
- İndirme günlüğü `BITTI` yazmış; eksik fonlama sonradan tamamlanmış
  (317/317 üyede 4h ve fonlama).
- Evren (yükleyiciyle, `scope="dev"`, yalnız yapı bilgisi, getiri yok):
  84 ay (2019-10 … 2026-09), dev döneminde 315 farklı sembol, eğitimde
  (2024 sonuna kadar) 200. Ay başına üye sayısı 2020-08'den itibaren 30;
  2020-03'ten önce 17'nin altında. Her ay ortalama 7,6 yeni üye giriyor.
- 315 sembolün hepsinin 4h ve 1d vadeli mumu var. Dev döneminin sonundan
  önce verisi biten 14 sembol var; bunlardan yalnız 3'ü evrendeyken bitiyor
  (LUNAUSDT 2022-05, MATICUSDT 2024-09 — POL'e geçiş, EOSUSDT 2025-05).

## Harness kısıtı (önemli)

Bacak ağırlıkları sabit ve toplamı en fazla 1; bacak başına pozisyon
[-1, 1]. Bacaklar = dev döneminde evrene hiç girmiş 315 sembol, ağırlık
1/315. Bir anda en fazla ~30 üye tutulabildiğinden brüt maruziyet en fazla
~30/315 ≈ %9,5 olur. Getiri, düşüş ve alfa tam yatırımlı bir uygulamaya göre
yaklaşık 1/10 ölçekte görünür; Sharpe, alfa t ve işaretler (aday şartlarının
hepsi) ölçekten bağımsızdır. Bu bir harness kısıtıdır, raporda belirtilecek.

## Plan

1. **Sinyal altyapısı** (`grafik_analiz/strategies/t2_genis_evren.py`):
   - Bütün bacakların kapanışlarından ortak zaman dizinli panel.
   - Evren `load_universe("dev")` ile yüklenir ve açıkça son barın
     kapanışına kesilir (`ay <= son_bar + aralık`). Bar t'de alınan karar
     t+1 barında tutulur; uygunluk t+1 barının ayının evrenine göre.
   - Listeden çıkış: verisi küresel son bardan önce biten sembolde son bardan
     bir önceki barda hedef 0 (talimat: "son bardan önce çık"). Bu bir barlık
     ileri bilgidir (Binance kaldırmayı günler önce duyurur); açıkça
     belirtilecek, etkisi eğitimde ölçülecek.
   - Fonlama: yalnız `funding_time <= bar açılışı` olan kayıtlar
     (assert_causal fonlamayı kesim barının açılışında kestiği için ve
     ihtiyat için).
   - Yeniden dengeleme `reb` günde bir (sabit takvim: 1970-01-01'den gün
     sayısı mod reb == 0; hafta günü ayarlanmaz). Arada pozisyon sabit;
     evrenden çıkan ya da listeden kalkan sembol hemen kapanır, yeni üye
     ancak sonraki dengelemede girer.
   - Seçim: uygun ve skoru geçerli üyeler sıralanır; en iyi `k_oran` kısmı
     uzun, en kötü `k_oran` kısmı kısa. İsteğe bağlı tampon (mevcut pozisyon
     sıralamada `tampon` kadar geriye düşene dek tutulur).
   - Boyut: eşit (±1) ya da ters oynaklık; taraflar dolar nötr ya da
     (seçenek) beta nötr (geçmiş kayan beta, BTC/ETH/SOL eşit ağırlıklı
     getiriye göre). Uygun üye sayısı `min_uye`'den azsa pozisyon yok.
2. **Faktörler** (skor yüksek = uzun):
   - `mom_L[_s]`: son L günün log getirisi (son s gün atlanarak).
   - `rev_L`: son L günün getirisinin tersi (kısa vadeli dönüş).
   - `fon_F`: son F günün ortalama fonlamasının tersi (düşük fonlamada uzun).
   - `oyn_V`: son V günün günlük getiri oynaklığının tersi (düşük oynaklık).
   - Bileşik: `a+b` biçiminde, kesitsel sıra z-skorlarının eşit ağırlıklı
     toplamı.
3. **Arama** yalnız `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0,))`
   (gerektiğinde 2.0). 1d ana zaman dilimi; 4h yalnız gerekçeli olursa.
   Önce tek faktörler (temel ayarlarla), sonra en iyi tek faktörlerin
   dengeleme sıklığı / k_oran / tampon / beta nötr komşulukları, sonra
   bileşikler. Toplam birkaç yüz yapılandırmayı geçmeyecek.
4. **Eğitim içi döküm** (yıllık getiri, uzun/kısa bacak katkısı) yalnız
   veriyi 31.12.2024'te kesen bir yardımcıyla ve yalnız deftere yazılmış
   yapılandırmalar için yapılır.
5. **Seçim ölçütü (eğitim):** 1× Sharpe ve alfa > 0, 2× maliyette pozitif
   getiri, beta mutlak değeri küçük (piyasa nötr), yıllar arasında tutarlılık
   (tek yıla dayanmama), komşu parametrelerde sağlamlık.
6. En fazla 5 yapılandırma dondurulur, `assert_causal` (ek kesimlerle)
   uygulanır, dev_valid'de bir kez ölçülür.

## Arama günlüğü

(her taramadan sonra eklenir)
