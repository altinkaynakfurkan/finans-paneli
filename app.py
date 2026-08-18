import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Finans & Yatırım Analiz Paneli (İş Yatırım & TEFAS)", layout="wide")

st.title("📊 BIST & İş Portföy Finansal Takip Paneli")

# 1. Enflasyon Referansı
TUIK_YILLIK_ENFLASYON = 31.75

# 2. Varlık Listesi
WATCHLIST = {
    "KPI - İş Portföy Para Piyasası Katılım Fonu": {"ticker": "KPI", "type": "tefas_fund"},
    "IAT - İş Portföy Kira Sertifikaları Katılım Fonu": {"ticker": "IAT", "type": "tefas_fund"},
    "Gram Altın (TL)": {"ticker": "ALTIN", "type": "is_fx"},
    "Altın Ons (USD)": {"ticker": "XAU/USD", "type": "is_fx"},
    "BIST 100 Endeksi": {"ticker": "XU100", "type": "is_stock"},
    "ASELS (Aselsan)": {"ticker": "ASELS", "type": "is_stock"},
    "BIMAS (BİM Mağazalar)": {"ticker": "BIMAS", "type": "is_stock"},
    "EREGL (Erdemir)": {"ticker": "EREGL", "type": "is_stock"},
    "FROTO (Ford Otosan)": {"ticker": "FROTO", "type": "is_stock"},
    "THYAO (Türk Hava Yolları)": {"ticker": "THYAO", "type": "is_stock"},
    "TUPRS (Tüpraş)": {"ticker": "TUPRS", "type": "is_stock"},
    "VESTL (Vestel Elektronik)": {"ticker": "VESTL", "type": "is_stock"},
    "USD/TRY (Dolar Kuru)": {"ticker": "USD/TRL", "type": "is_fx"},
    "EUR/TRY (Euro Kuru)": {"ticker": "EUR/TRL", "type": "is_fx"},
    "Özel BIST Hissesi Gir...": {"ticker": "CUSTOM", "type": "custom"}
}

STOCKS_ONLY = {
    "ASELS (Aselsan)": "ASELS",
    "BIMAS (BİM Mağazalar)": "BIMAS",
    "EREGL (Erdemir)": "EREGL",
    "FROTO (Ford Otosan)": "FROTO",
    "THYAO (Türk Hava Yolları)": "THYAO",
    "TUPRS (Tüpraş)": "TUPRS",
    "VESTL (Vestel Elektronik)": "VESTL"
}

def get_period_inflation(annual_inflation, p):
    period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = period_days.get(p, 365)
    months = days // 30
    monthly_rate = (1 + (annual_inflation / 100)) ** (1 / 12) - 1
    period_enf = ((1 + monthly_rate) ** months - 1) * 100
    return period_enf, months, days

# --- 1. İŞ YATIRIM VERİ MOTORU ---
@st.cache_data(ttl=300)
def get_is_yatirim_history(symbol, days=365):
    try:
        end_date = datetime.now().strftime("%d-%m-%Y")
        start_date = (datetime.now() - timedelta(days=days+30)).strftime("%d-%m-%Y")
        url = f"https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/HisseTekil?hisse={symbol}&startdate={start_date}&enddate={end_date}.json"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        
        if "value" in data and len(data["value"]) > 0:
            df = pd.DataFrame(data["value"])
            df['Date'] = pd.to_datetime(df['HGD_TARIH'], format="%d-%m-%Y")
            df = df.sort_values('Date').set_index('Date')
            df['Close'] = pd.to_numeric(df['HGD_KAPANIS'], errors='coerce')
            df['Open'] = pd.to_numeric(df['HGD_ACILIS'], errors='coerce').fillna(df['Close'])
            df['High'] = pd.to_numeric(df['HGD_YUKSEK'], errors='coerce').fillna(df['Close'])
            df['Low'] = pd.to_numeric(df['HGD_DUSUK'], errors='coerce').fillna(df['Close'])
            df['Volume'] = pd.to_numeric(df['HGD_HACIM'], errors='coerce').fillna(0)
            return df.dropna(subset=['Close'])
    except Exception:
        pass
    return pd.DataFrame()

# --- 2. İŞ YATIRIM BİLANÇO VE ÇARPAN MOTORU ---
@st.cache_data(ttl=900)
def get_is_yatirim_fundamentals(symbol):
    try:
        url = f"https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/TeknikGostergeler?hisse={symbol}.json"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if "value" in data and len(data["value"]) > 0:
            return data["value"][0]
    except Exception:
        pass
    return {}

# --- 3. TEFAS CANLI FON MOTORU ---
@st.cache_data(ttl=600)
def get_tefas_fund_data(fund_code):
    try:
        url = "https://fonturkey.com.tr/api/fund-detail" # Takasbank TEFAS API Servisi
        headers = {"User-Agent": "Mozilla/5.0"}
        # TEFAS Doğrudan Post İsteği
        tefas_url = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
        payload = {
            "fontip": "YAT",
            "fonkod": fund_code,
            "bastarih": (datetime.now() - timedelta(days=365)).strftime("%d.%m.%Y"),
            "bittarih": datetime.now().strftime("%d.%m.%Y")
        }
        res = requests.post(tefas_url, data=payload, headers=headers, timeout=10)
        data = res.json()
        if "data" in data and len(data["data"]) > 0:
            df = pd.DataFrame(data["data"])
            df['Date'] = pd.to_datetime(df['TARIH'], unit='ms')
            df['Close'] = pd.to_numeric(df['FIYAT'])
            df = df.sort_values('Date').set_index('Date')
            return df
    except Exception:
        pass
    return pd.DataFrame()

def format_val(val, prefix="", suffix="", multiplier=1.0, precision=2):
    if val is None or not isinstance(val, (int, float)) or pd.isna(val):
        return "-"
    return f"{prefix}{val * multiplier:.{precision}f}{suffix}"

# --- SOL MENÜ ---
st.sidebar.header("🧭 Menü Seçimi")
page_mode = st.sidebar.radio(
    "Sayfa:",
    [
        "📈 Tekil Varlık & Grafik Detayı",
        "📑 Tüm Hisselerin Özeti (Karşılaştırma)",
        "📖 Genel Bilgi & Finansal Kılavuz"
    ],
    index=0
)

# 1. KILAVUZ SAYFASI
if page_mode == "📖 Genel Bilgi & Finansal Kılavuz":
    st.subheader("📖 Finansal Okuryazarlık ve Analiz Parametreleri Kılavuzu")
    st.caption("Doğrudan İş Yatırım & TEFAS altyapısından alınan finansal göstergelerin anlamları:")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 1. Değerleme ve Çarpanlar")
        st.markdown("""
        * **F/K (Fiyat / Kazanç):** Şirketin piyasa değerinin yıllık kârına oranıdır. Şirketin kendini kaç yılda amorti edeceğini gösterir (5-12 arası ideal).
        * **PD/DD (Piyasa/Defter Değeri):** Şirketin borsadaki değerinin özkaynaklarına oranıdır (1-3 arası makul).
        * **Temettü Verimi (%):** Yıllık nakit kâr payı dağıtım oranı.
        """)
        st.markdown("### 2. Getiri ve Enflasyon")
        st.markdown("""
        * **Nominal Getiri:** Paranın sayısal artışıdır.
        * **Reel Getiri (Fisher Formülü):** Enflasyondan arındırılmış satın alma gücü artışıdır.
        """)
    with c2:
        st.markdown("### 3. Fonlar (TEFAS) & Teknik")
        st.markdown("""
        * **KPI (Para Piyasası Katılım):** Faizsiz likit getiri sağlar, değeri asla düşmez.
        * **IAT (Kira Sertifikaları Katılım):** Sukuk getirisi sunar, düzenli gelir akışı sağlar.
        * **RSI (14):** 30 altı aşırı satım (fırsat), 70 üstü aşırı alım (düzeltme riski).
        * **SMA 20 & 50:** Fiyat ortalamaların üzerindeyse trend pozitiftir.
        """)

# 2. TOPLU KARŞILAŞTIRMA SAYFASI
elif page_mode == "📑 Tüm Hisselerin Özeti (Karşılaştırma)":
    st.subheader("📑 Takip Listesindeki Şirketlerin Karşılaştırmalı Performans Tablosu")
    
    comp_period = st.sidebar.selectbox("Dönem:", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    yillik_enf = st.sidebar.number_input("Yıllık Enflasyon (TÜFE %)", value=TUIK_YILLIK_ENFLASYON, step=0.5)
    donem_enf, ay_sayisi, days_count = get_period_inflation(yillik_enf, comp_period)
    
    st.caption(f"Veri Kaynağı: **İş Yatırım** | Seçilen Dönem: **{comp_period} ({ay_sayisi} Aylık)** | Enflasyon: **%{donem_enf:.2f}**")

    summary_rows = []
    with st.spinner("İş Yatırım sunucularından veriler toplanıyor..."):
        for name, ticker in STOCKS_ONLY.items():
            df_hist = get_is_yatirim_history(ticker, days=days_count)
            fund = get_is_yatirim_fundamentals(ticker)

            if not df_hist.empty and len(df_hist) >= 2:
                last_p = float(df_hist['Close'].iloc[-1])
                start_p = float(df_hist['Close'].iloc[0])
                prev_p = float(df_hist['Close'].iloc[-2])

                daily_c = ((last_p - prev_p) / prev_p) * 100
                nom_ret = ((last_p - start_p) / start_p) * 100
                reel_ret = ((1 + (nom_ret / 100)) / (1 + (donem_enf / 100)) - 1) * 100

                h52 = float(df_hist['High'].max())
                zirve_iskonto = ((last_p - h52) / h52) * 100

                rsi_s = RSIIndicator(close=df_hist['Close'], window=min(14, len(df_hist))).rsi()
                last_rsi = float(rsi_s.iloc[-1]) if pd.notnull(rsi_s.iloc[-1]) else 50.0

                summary_rows.append({
                    "Hisse": name.split(" ")[0],
                    "Şirket": name.split("(")[1].replace(")", ""),
                    "Son Fiyat": f"{last_p:.2f} TL",
                    "Günlük Fark": f"%{daily_c:+.2f}",
                    f"Nominal ({comp_period})": f"%{nom_ret:+.2f}",
                    f"Reel ({comp_period})": f"%{reel_ret:+.2f}",
                    "Zirve İskonto": f"%{zirve_iskonto:.1f}",
                    "RSI (14)": f"{last_rsi:.1f}",
                    "F/K": format_val(fund.get("FK")),
                    "PD/DD": format_val(fund.get("PDDD"))
                })

    if summary_rows:
        df_summary = pd.DataFrame(summary_rows)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
    else:
        st.error("İş Yatırım verilerine şu anda ulaşılamadı.")

# 3. TEKİL DETAY SAYFASI
else:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Piyasa ve Fon Seçimi")
    selected_label = st.sidebar.selectbox("Takip Listesi:", list(WATCHLIST.keys()), index=0)
    selected_item = WATCHLIST[selected_label]

    if selected_item["type"] != "tefas_fund":
        period = st.sidebar.selectbox("Zaman Aralığı", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    else:
        period = "1y"

    st.sidebar.markdown("---")
    st.sidebar.subheader("📌 Enflasyon Referansları")
    yillik_enf = st.sidebar.number_input("Yıllık Enflasyon (TÜFE %)", value=TUIK_YILLIK_ENFLASYON, step=0.5)

    donem_enf, ay_sayisi, days_count = get_period_inflation(yillik_enf, period)
    st.sidebar.metric(label=f"Seçilen Dönem Enflasyonu ({period} - {ay_sayisi} Aylık)", value=f"%{donem_enf:.2f}")

    # TEFAS FONLARI (KPI & IAT)
    if selected_item["type"] == "tefas_fund":
        st.subheader(f"🏷️ {selected_label}")
        with st.spinner("TEFAS / Takasbank verileri yükleniyor..."):
            df_tefas = get_tefas_fund_data(selected_item["ticker"])

        if not df_tefas.empty and len(df_tefas) >= 2:
            last_p = float(df_tefas['Close'].iloc[-1])
            start_p = float(df_tefas['Close'].iloc[0])
            fund_ret = ((last_p - start_p) / start_p) * 100
            fon_reel = ((1 + (fund_ret / 100)) / (1 + (donem_enf / 100)) - 1) * 100

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pay Fiyatı", f"{last_p:.4f} TL")
            c2.metric(f"Yıllık Getiri (TEFAS)", f"%{fund_ret:.2f}")
            c3.metric("Yıllık Enflasyon", f"%{yillik_enf:.2f}")
            c4.metric(label="Reel Getiri", value=f"%{fon_reel:+.2f}", delta=f"{fon_reel:+.2f}% Reel Kazanç")

            fig_fund = go.Figure()
            fig_fund.add_trace(go.Scatter(x=df_tefas.index, y=df_tefas['Close'], line=dict(color='green', width=2), name="Pay Fiyatı"))
            fig_fund.update_layout(title=f"{selected_label} TEFAS Fiyat Grafiği", height=400)
            st.plotly_chart(fig_fund, use_container_width=True)
        else:
            # Yedek sabit metrik
            st.info("Canlı TEFAS verisi yükleniyor...")

    # HİSSE, BIST 100, ALTIN VE DÖVİZ
    else:
        symbol = selected_item["ticker"]
        if symbol == "CUSTOM":
            symbol = st.sidebar.text_input("BIST Kodu (örn. TUPRS):", value="TUPRS").strip().upper()

        tab1, tab2 = st.tabs(["📊 Fiyat & Grafik Analizi", "📑 Temel Analiz & Şirket Karnesi"])

        with tab1:
            with st.spinner("İş Yatırım fiyat verileri alınıyor..."):
                data = get_is_yatirim_history(symbol, days=days_count)

            if data.empty or len(data) < 2:
                st.error("Seçilen varlık için veri çekilemedi.")
            else:
                data['SMA20'] = SMAIndicator(close=data['Close'], window=min(20, len(data))).sma_indicator()
                data['SMA50'] = SMAIndicator(close=data['Close'], window=min(50, len(data))).sma_indicator()
                data['RSI'] = RSIIndicator(close=data['Close'], window=min(14, len(data))).rsi()

                start_p = float(data['Close'].iloc[0])
                last_p = float(data['Close'].iloc[-1])
                prev_p = float(data['Close'].iloc[-2])
                daily_c = ((last_p - prev_p) / prev_p) * 100
                period_r = ((last_p - start_p) / start_p) * 100
                last_rsi = float(data['RSI'].iloc[-1]) if pd.notnull(data['RSI'].iloc[-1]) else 50.0
                reel_r = ((1 + (period_r / 100)) / (1 + (donem_enf / 100)) - 1) * 100

                st.subheader(f"📈 {selected_label}")
                c1, c2, c3, c4, c5 = st.columns(5)
                birim = "Puan" if symbol == "XU100" else ("$" if "USD" in symbol else "TL")
                c1.metric("Son Değer", f"{last_p:.2f} {birim}", f"{daily_c:+.2f}% Günlük")
                c2.metric(f"Nominal ({period})", f"%{period_r:+.2f}")
                c3.metric(f"{ay_sayisi} Aylık Enflasyon", f"%{donem_enf:.2f}")
                c4.metric(label=f"Reel ({period})", value=f"%{reel_r:+.2f}", delta=f"{reel_r:+.2f}% Reel Kazanç/Kayıp")
                rsi_durum = "Aşırı Alım" if last_rsi > 70 else ("Aşırı Satım" if last_rsi < 30 else "Nötr")
                c5.metric("RSI (14)", f"{last_rsi:.2f}", rsi_durum)

                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Fiyat"))
                fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='orange', width=1.5), name="SMA 20"))
                fig.add_trace(go.Scatter(x=data.index, y=data['SMA50'], line=dict(color='blue', width=1.5), name="SMA 50"))
                fig.update_layout(title=f"{selected_label} Fiyat ve Ortalamalar (İş Yatırım)", xaxis_rangeslider_visible=False, height=450)
                st.plotly_chart(fig, use_container_width=True)

                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='purple', width=1.5), name="RSI"))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
                fig_rsi.update_layout(title="RSI Momentum", yaxis=dict(range=[0, 100]), height=200)
                st.plotly_chart(fig_rsi, use_container_width=True)

        with tab2:
            if selected_item["type"] in ["is_stock", "custom"]:
                st.subheader(f"📑 {selected_label} - İş Yatırım Bilanço & Çarpan Karnesi")
                fund = get_is_yatirim_fundamentals(symbol)

                st.markdown("##### 1. Değerleme ve Çarpanlar")
                k1, k2, k3 = st.columns(3)
                k1.metric("F/K (Fiyat/Kazanç)", format_val(fund.get("FK")), help="İdeal aralık: 5-12")
                k2.metric("PD/DD (Piyasa/Defter)", format_val(fund.get("PDDD")), help="1-3 arası dengeli")
                k3.metric("FD / FAVÖK", format_val(fund.get("FDFAVOK")), help="Operasyonel kârlılık çarpanı")

                st.markdown("---")
                st.markdown("##### 2. Fiyat İskontosu ve Trend")
                p1, p2 = st.columns(2)
                if not data.empty:
                    h52 = float(data['High'].max())
                    iskonto = ((last_p - h52) / h52) * 100
                    p1.metric("52 Hafta Zirvesi", f"{h52:.2f} TL")
                    p2.metric("Zirveye İskonto", f"%{iskonto:.2f}", help="Zirveden geri çekilme oranı")
            else:
                st.info("Temel analiz karnesi sadece BIST hisse senetleri için geçerlidir.")
