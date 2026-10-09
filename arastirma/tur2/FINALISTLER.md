# Tur 2 — İleriye Dönük Takibe Seçim Kuralı

9 Ekim 2026 · tur 2'nin sekiz ailesinden altısı ve denetim **bitmeden önce**
yazıldı. O sırada sonuçları bilinen aileler yalnızca `t2_cift` ve
`t2_konumlanma` idi. Kural [`docs/PROTOKOL_2.md`](../../docs/PROTOKOL_2.md)
"İleriye dönük takibe seçim" bölümünün uygulamasıdır ve
[`finalist_secimi.py`](finalist_secimi.py) ile mekanik olarak uygulanır.

## Kural

1. **Adaylar:** `grafik_analiz/strategies/t2_*.py` dosyalarındaki dondurulmuş
   yapılandırmalardan `candidate_check`'i (protokol 2, yedi şart) geçenler.
2. **Denetim:** Denetimde (`DENETIM_2.md`) kritik ihlal ya da ileri bakış
   hatası bulunan yapılandırma, gerekçesi bu dosyaya yazılarak sıralamadan önce
   çıkarılır (`--haric`).
3. **İşlem sayısı:** İç doğrulamada en az 30 işlem yapmamış adaylar elenir.
   İşlem sayısı, değerlendirme altyapısının saydığı sayıdır. Bu sayı her
   bacağın her pozisyon dilimini ayrı sayar. Örneğin iki bacaklı bir çift
   işlemi en az 2 işlem sayılır.
4. **Sıralama:** Kalanlar iç doğrulamada iki kat maliyetle Sharpe'a göre
   sıralanır.
5. **Seçim:** Sırayla, daha önce seçilenlerin hepsiyle iç doğrulama günlük
   getiri korelasyonu 0,70'ten küçük olan seçilir. En fazla 5 yapılandırma
   seçilir.

Seçilenler kodları değiştirilmeden `grafik_analiz/forward` takibine eklenir.
Hiçbir aday kalmazsa takibe yeni yapılandırma eklenmez.

## Denetim nedeniyle çıkarılanlar

(Denetimden sonra doldurulacak.)

## Sonuç

(Seçim çalıştırıldıktan sonra doldurulacak.)
