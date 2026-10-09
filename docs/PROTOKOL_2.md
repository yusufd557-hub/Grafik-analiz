# Kârlı Strateji Araştırması — Ön Kayıt Protokolü, Sürüm 2

9 Ekim 2026 · araştırma turu 2'nin strateji sonuçlarından **önce** yazıldı.

Sürüm 1 ([`PROTOKOL.md`](PROTOKOL.md)) ve sonuçları değişmeden korunur
([`arastirma/SONUC_1.md`](../arastirma/SONUC_1.md)). Sürüm 1'in görülmemiş
dönemi (01.07.2025–30.09.2026) kullanıldı. Bu yüzden sürüm 2'de görülmemiş
geçmiş dönem yoktur; **tek kanıt ileriye dönük takiptir.** Sayısal değerler
kodda, `GRAFIK_ANALIZ_PROTOKOL=2` ile seçilen
`grafik_analiz/research/protocol.py` dosyasındadır. Kayıtlar
`arastirma/tur2/` altına yazılır.

## Sürüm 1'den farklar

1. **Dönemler:**
   - Eğitim: verinin başı – 31.12.2024.
   - İç doğrulama: 01.01.2025 – 30.09.2026.
   - 30.09.2026 sonrasının verisi geliştirmede kilitlidir.
2. **Alfa şartı:** Sürüm 1'de adayların kârı büyük ölçüde piyasanın
   yönünden geliyordu (denetim, `DENETIM_1.md`). Sürüm 2'de aday, eğitim ve
   iç doğrulama dönemlerinin her ikisinde de piyasa kıyasına göre **pozitif
   alfa** üretmelidir.
   - Piyasa kıyası: BTC/ETH/SOL eşit ağırlıklı al-tut, stratejinin
     piyasasında.
   - Alfa: günlük net getirinin kıyasa göre doğrusal regresyonundaki sabit
     terim, yıllık.
3. **Limit emir modeli:** Stratejiler pozisyon değişimini bir sonraki barda
   limit emirle deneyebilir.
   - Emir verildiği anda piyasa fiyatının öbür tarafındaysa piyasa emri
     sayılır.
   - Değilse yalnız fiyat limitin 2 bps ötesine geçerse limit fiyattan dolar.
     Dolmazsa iptal olur.
   - Maker komisyonu: spot %0,10, vadeli %0,02. Kayma yok.
4. **Yeni veriler:**
   - Vadeli konumlanma ölçüleri (5 dakikalık açık pozisyon, uzun/kısa
     oranları, taker oranı; 2020-09'dan).
   - Vadeli prim endeksi.
   - Geniş vadeli evren. Her ay, önceki 30 günün hacmine göre ilk 30
     sözleşme seçilir. Listeden çıkarılanlar dahildir, sabit değerli
     sözleşmeler hariçtir.

## Değişmeyenler

- **İşlem simülasyonu:** kapanışta karar, sonraki açılışta işlem.
- **Piyasa emri maliyetleri:**
  - Spot: %0,10 + %0,02 kayma, taraf başına.
  - Vadeli: %0,05 + %0,02 kayma, taraf başına, fonlama dahil.
  - İki kat maliyet testi.
- **Kaldıraç yok.**
- **İleri bakış denetimi.**
- **Deney defteri:** değerlendirilen her yapılandırma `arastirma/tur2/deneyler/`
  altına yazılır.
- **Geliştirme dönemi kuralları:**
  - Parametreler yalnız eğitim döneminde seçilir.
  - Aile başına en fazla 5 dondurulmuş yapılandırma iç doğrulamada bir kez
    ölçülür.

## Aday şartları

Bir yapılandırma şu şartların hepsini geçerse aday olur:

1. Eğitimde net getiri > 0.
2. İç doğrulamada net getiri > 0.
3. İç doğrulamada iki kat maliyetle net getiri > 0.
4. İç doğrulamada yıllık Sharpe ≥ 0,5.
5. İç doğrulamada en az 20 işlem.
6. Eğitimde alfa > 0.
7. İç doğrulamada alfa > 0.

## İleriye dönük takibe seçim

Görülmemiş dönem açılmadan önce yazılır: `arastirma/tur2/FINALISTLER.md`.
Seçim mekaniktir:

- İç doğrulamada en az 30 işlem yapmış adaylar, iki kat maliyetle Sharpe'a
  göre sıralanır.
- Bir aday, daha önce seçilenlerle günlük getiri korelasyonu 0,70'ten
  küçükse seçilir.
- En fazla **5** yapılandırma seçilir.

Seçilenler, kodları değiştirilmeden ileriye dönük takibe alınır
(`grafik_analiz/forward`). Sinyaller her bar kapanışında önce kaydedilir.

## İleriye dönük değerlendirme

En erken **90 gün ve 30 işlem** sonra, takipteki her yapılandırma için:

**Seviye 1 — kârlı:**

1. Net getiri > 0.
2. İki kat maliyetle net getiri > 0.
3. En az 30 işlem.
4. En iyi tek işlem çıkarıldığında getiri hâlâ > 0.

**Seviye 2 — istatistiksel olarak anlamlı:** Seviye 1'e ek olarak blok
bootstrap ile "ortalama ≤ 0" olasılığı 0,05 / takipteki yapılandırma
sayısından küçük olmalıdır.

**Kıyas:** al-tut ve alfa raporlanır.

Takip sırasında kural veya parametre değişirse yapılandırma yeni bir sürüm
olur; ileriye dönük takibi sıfırdan başlar.
