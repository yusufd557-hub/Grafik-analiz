# Finalistler

Protokol: [`docs/PROTOKOL.md`](../docs/PROTOKOL.md) (sürüm 1). Bu belge görülmemiş
dönem açılmadan **önce** yazıldı ve commit edildi.

## Seçim kuralı (sonuçlara bakmadan önce sabitlendi)

Bağımsız denetim ([`DENETIM_1.md`](DENETIM_1.md)), görülmemiş dönemin dil modeli
araştırmacıların eğitim bilgisiyle örtüşebileceğini belirtti ve finalistlerin
mekanik bir kuralla seçilmesini önerdi. Kural:

1. **Uygunluk:**
   - Aday şartlarını geçmiş olmak (`candidate_check`).
   - İleri bakış denetimini geçmiş olmak (`assert_causal`).
   - Denetimde yeniden üretilmiş olmak.
   - İç doğrulamada (01.01.2024–30.06.2025) **en az 30 işlem** yapmış olmak.
     Gerekçe: görülmemiş dönem 15 aydır ve en az 20 işlem şartı vardır. 18
     aylık iç doğrulamada 30'dan az işlem yapan bir yapılandırma bu şartı
     muhtemelen karşılayamaz. Denetim, 27 işlemli ve %0,9 maruziyetli bir
     yapılandırmayı bu nedenle kırılgan buldu.
2. **Puan:** iç doğrulamada **iki kat maliyetle** yıllık Sharpe oranı
   (günlük net getirilerden).
3. **Çeşitlilik:** Adaylar puana göre büyükten küçüğe sıralanır. Bir aday
   yalnızca iç doğrulamadaki günlük net getirisinin, daha önce seçilmiş
   bütün finalistlerle korelasyonu 0,70'ten küçükse seçilir. Böylece
   birbirinin kopyası olan yapılandırmalar ayrı finalist sayılmaz.
4. En fazla **3** finalist seçilir.
5. Görülmemiş dönemde her finalist protokoldeki Seviye 1 ve Seviye 2
   şartlarıyla, parametreleri değiştirilmeden, **bir kez** ölçülür. Seviye 2
   için anlamlılık eşiği 0,05 / finalist sayısıdır.
6. Eşit ağırlıklı BTC/ETH/SOL al-tut (aynı piyasa) karşılaştırma için
   raporlanır; şart değildir.

## Uygulama

Kural `arastirma/finalist_secimi.py` ile yalnız geliştirme dönemi verisiyle
uygulanır. Sonuç bu belgenin altına eklenir.
