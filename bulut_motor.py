import os, json, time
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd, yfinance as yf
from sklearn.linear_model import LinearRegression

TR_SAAT = timezone(timedelta(hours=3))
SIMDI = datetime.now(TR_SAAT)
CSV_DOSYA = "altin_tarihsel_veri.csv"
LOG_DOSYA = "saatlik_tahmin_log.csv"
OZET_DOSYA = "ozet.json"

def piyasa_acik_mi():
    gun = SIMDI.weekday()
    if gun in (5, 6): return False, "Hafta Sonu • Piyasa Kapalı"
    if gun == 0 and SIMDI.hour < 1: return False, "Piyasa Kapalı (01:00'de Açılır)"
    return True, "Küresel Piyasa Açık • Canlı"

def veri_cek(semboller, baslangic=None, period=None, interval="1d"):
    for s in semboller:
        try:
            v = yf.Ticker(s).history(start=baslangic, interval=interval) if baslangic else yf.Ticker(s).history(period=period, interval=interval)
            if not v.empty: return v, s
            time.sleep(1)
        except Exception: time.sleep(1)
    return pd.DataFrame(), None

def calistir():
    if os.path.exists(CSV_DOSYA):
        df = pd.read_csv(CSV_DOSYA, sep=";", decimal=",")
        df["Tarih"] = pd.to_datetime(df["Tarih"])
        df = df.set_index("Tarih")[["Ons_USD", "Dolar_TL"]]
    else:
        baslangic = (SIMDI - timedelta(days=3650)).strftime("%Y-%m-%d")
        o_v, sem = veri_cek(["GC=F", "PAXG-USD", "GLD"], baslangic=baslangic)
        d_v, _ = veri_cek(["TRY=X"], baslangic=baslangic)
        if o_v.empty or d_v.empty: return
        if sem == "GLD": o_v["Close"] *= 10.75
        o_v.index = pd.to_datetime(o_v.index).tz_localize(None).normalize()
        d_v.index = pd.to_datetime(d_v.index).tz_localize(None).normalize()
        df = pd.DataFrame({"Ons_USD": o_v["Close"], "Dolar_TL": d_v["Close"]}).ffill().dropna()

    acik, durum_metin = piyasa_acik_mi()
    os_v, ds_v = pd.DataFrame(), pd.DataFrame()
    if acik:
        os_v, s_sem = veri_cek(["GC=F", "PAXG-USD", "GLD"], period="5d", interval="1h")
        ds_v, _ = veri_cek(["TRY=X"], period="5d", interval="1h")
        if not os_v.empty and not ds_v.empty:
            if s_sem == "GLD": os_v["Close"] *= 10.75
            t = pd.to_datetime(os_v.index[-1]).tz_localize(None).normalize()
            df.loc[t] = [os_v["Close"].iloc[-1].item(), ds_v["Close"].iloc[-1].item()]

    df = df.sort_index()
    df["Gram_Altin_TL"] = (df["Ons_USD"] / 31.1035) * df["Dolar_TL"]
    df_k = df.reset_index()
    df_k.columns = ["Tarih", "Ons_USD", "Dolar_TL", "Gram_Altin_TL"]
    df_k.to_csv(CSV_DOSYA, index=False, sep=";", decimal=",")

    guncel = df_k["Gram_Altin_TL"].iloc[-1].item()
    ons = df_k["Ons_USD"].iloc[-1].item()
    dolar = df_k["Dolar_TL"].iloc[-1].item()

    p60 = df_k.tail(60).copy()
    p60["No"] = np.arange(len(p60))
    m60 = LinearRegression().fit(p60[["No"]].values, p60["Gram_Altin_TL"].values)
    tahmin_60 = m60.predict(np.array([[len(p60)]])).item()

    tahmin_1s = guncel
    if not os_v.empty and not ds_v.empty:
        sdf = pd.DataFrame({"O": os_v["Close"], "D": ds_v["Close"]}).ffill().dropna()
        if len(sdf) >= 5:
            sdf["G"] = (sdf["O"] / 31.1035) * sdf["D"]
            s24 = sdf.tail(24)
            m1 = LinearRegression().fit(np.arange(len(s24)).reshape(-1, 1), s24["G"].values)
            tahmin_1s = m1.predict(np.array([[len(s24)]])).item()

    saat_etiket = SIMDI.strftime("%Y-%m-%d %H:00")
    kolonlar = ["Saat", "Baslangic_TL", "Saatlik_Tahmin_TL", "Sonraki_Gercek_TL", "Hata_TL", "Basari_Yuzde", "Yon_Isabet"]
    log_df = pd.read_csv(LOG_DOSYA, sep=";", decimal=",") if os.path.exists(LOG_DOSYA) else pd.DataFrame(columns=kolonlar)

    if acik:
        if not log_df.empty and pd.isna(log_df.iloc[-1]["Sonraki_Gercek_TL"]) and log_df.iloc[-1]["Saat"] != saat_etiket:
            bas = float(log_df.iloc[-1]["Baslangic_TL"])
            tah = float(log_df.iloc[-1]["Saatlik_Tahmin_TL"])
            hata = abs(guncel - tah)
            idx = log_df.index[-1]
            log_df.at[idx, "Sonraki_Gercek_TL"] = round(guncel, 2)
            log_df.at[idx, "Hata_TL"] = round(hata, 2)
            log_df.at[idx, "Basari_Yuzde"] = round(max(0.0, 100.0 - ((hata / guncel) * 100)), 2)
            log_df.at[idx, "Yon_Isabet"] = 1 if (tah >= bas) == (guncel >= bas) else 0

        if log_df.empty or log_df.iloc[-1]["Saat"] != saat_etiket:
            yeni = pd.DataFrame([{"Saat": saat_etiket, "Baslangic_TL": round(guncel, 2), "Saatlik_Tahmin_TL": round(tahmin_1s, 2), "Sonraki_Gercek_TL": np.nan, "Hata_TL": np.nan, "Basari_Yuzde": np.nan, "Yon_Isabet": np.nan}])
            log_df = pd.concat([log_df, yeni], ignore_index=True)
            log_df.to_csv(LOG_DOSYA, index=False, sep=";", decimal=",")

    tamam = log_df.dropna(subset=["Basari_Yuzde"])
    son_60_liste = [{"t": r["Tarih"].strftime("%d.%m"), "f": round(float(r["Gram_Altin_TL"]), 2)} for _, r in df_k.tail(60).iterrows()]
    gecmis_test = tamam.tail(30).iloc[::-1].to_dict(orient="records")

    ozet = {
        "guncelleme": SIMDI.strftime("%d.%m.%Y %H:%M"),
        "piyasa_acik": acik,
        "piyasa_durum": durum_metin,
        "guncel_tl": round(guncel, 2),
        "ons_usd": round(ons, 2),
        "dolar_tl": round(dolar, 2),
        "tahmin_1s_tl": round(tahmin_1s, 2),
        "degisim_1s_yuzde": round(((tahmin_1s - guncel) / guncel) * 100, 2),
        "tahmin_60g_tl": round(tahmin_60, 2),
        "degisim_60g_yuzde": round(((tahmin_60 - guncel) / guncel) * 100, 2),
        "test_sayisi": int(len(tamam)),
        "ort_basari": round(float(tamam["Basari_Yuzde"].mean()), 2) if not tamam.empty else 0.0,
        "yon_isabet": int(tamam["Yon_Isabet"].sum()) if not tamam.empty else 0,
        "grafik_60g": son_60_liste,
        "son_testler": gecmis_test
    }
    with open(OZET_DOSYA, "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    calistir()
