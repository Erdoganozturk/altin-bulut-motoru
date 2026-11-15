import json, urllib.request
import flet as ft

VERI_URL = "https://githubusercontent.com"

def main(page: ft.Page):
    page.title = "Gram Altın Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f172a"
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    gram_girdi = ft.TextField(label="Elimdeki Gram Altın", value="0", width=180, keyboard_type=ft.KeyboardType.NUMBER, border_color="#fbbf24")
    durum_txt = ft.Text("Buluttan veriler çekiliyor...", color="#94a3b8", size=12)
    icerik = ft.Column(spacing=12)

    def kart(baslik, deger, alt_bilgi, renk):
        return ft.Container(
            bgcolor="#1e293b", border_radius=14, padding=14, border=ft.border.all(1, "#334155"),
            content=ft.Column([
                ft.Text(baslik, size=11, color="#94a3b8", weight=ft.FontWeight.BOLD),
                ft.Text(deger, size=20, color=renk, weight=ft.FontWeight.BOLD),
                ft.Text(alt_bilgi, size=12, color="#cbd5e1")
            ], spacing=4)
        )

    def verileri_yukle(e=None):
        icerik.controls.clear()
        durum_txt.value = "Bulut sunucusuna bağlanılıyor..."
        page.update()
        try:
            req = urllib.request.urlopen(VERI_URL, timeout=10)
            veri = json.loads(req.read().decode("utf-8"))
            guncel = float(veri["guncel_tl"])
            try: eldeki = float(gram_girdi.value.replace(",", "."))
            except ValueError: eldeki = 0.0

            icerik.controls.extend([
                kart("GÜNCEL GRAM ALTIN", f"{guncel:,.2f} TL", f"Ons: ${veri['ons_usd']}  •  Dolar: {veri['dolar_tl']} TL", "#fbbf24"),
                kart("1 SAAT SONRAKİ TAHMİN", f"{veri['tahmin_1s_tl']:,.2f} TL", f"Beklenti: %{veri['degisim_1s_yuzde']:+.2f}", "#38bdf8" if veri["degisim_1s_yuzde"] >= 0 else "#f87171"),
                kart("60 GÜNLÜK TREND TAHMİNİ", f"{veri['tahmin_60g_tl']:,.2f} TL", f"Beklenti: %{veri['degisim_60g_yuzde']:+.2f}", "#34d399" if veri["degisim_60g_yuzde"] >= 0 else "#f87171"),
                kart("SAATLİK ÖZ-TEST DOĞRULUĞU", f"%{veri['ort_basari']:.1f}", f"Test: {veri['test_sayisi']} Saat  •  Yön İsabeti: {veri['yon_isabet']}/{veri['test_sayisi']}", "#fb923c"),
                kart("TOPLAM VARLIĞIM", f"{(guncel * eldeki):,.2f} TL", f"{eldeki} Gram Altın Karşılığı", "#a78bfa"),
            ])
            durum_txt.value = f"Son Bulut Güncellemesi: {veri['guncelleme']} ({veri['piyasa_durum']})"
        except Exception as err:
            durum_txt.value = f"Bağlantı Hatası: {err}"
        page.update()

    baslik_bar = ft.Row([
        ft.Text("Gram Altın Pro", size=22, weight=ft.FontWeight.BOLD, color="#fbbf24"),
        ft.IconButton(icon=ft.Icons.REFRESH, icon_color="#38bdf8", on_click=verileri_yukle)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    gram_girdi.on_change = verileri_yukle
    page.add(baslik_bar, durum_txt, gram_girdi, icerik)
    verileri_yukle()

ft.run(main)
