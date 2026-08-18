import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
import requests

st.set_page_config(page_title="Finans & Yatırım Analiz Paneli", layout="wide")

st.title("📊 Finansal Takip, İş Portföy Katılım ve Yatırım Analiz Paneli")

# 1. Yıllık Enflasyon Referansı
TUIK_YILLIK_ENFLASYON = 31.75  # TÜİK güncel yıllık TÜFE (%)

# 2. Varlık Listesi
WATCHLIST = {
    "KPI - İş Portföy Para Piyasası Katılım (TL) Fonu": {
        "ticker": "KPI", "type": "katilim_ppf", "yillik_getiri": 44.50,
        "fon_adi": "İş Portföy Para Piyasası Katılım (TL) Fonu"
    },
    "IAT - İş Portföy Kira Sertifikaları Katılım (TL) Fonu": {
        "ticker": "IAT", "type": "sukuk", "yillik_getiri": 39.80,
        "fon_adi": "İş Portföy Kira Sertifikaları Katılım (TL) Fonu"
    },
    "Gram Altın (TL)": {"ticker": "GRAM_ALTIN", "type": "gram_altin"},
    "Altın Ons (USD)": {"ticker": "GC=F", "type": "commodity"},
    "BIST 100 Endeksi": {"ticker": "XU100.IS", "type": "index"},
    "ASELS (Aselsan)": {"ticker": "ASELS.IS", "type": "stock"},
    "BIMAS (BİM Mağazalar)": {"ticker": "BIMAS.IS", "type": "stock"},
    "EREGL (Erdemir)": {"ticker": "EREGL.IS", "type": "stock"},
    "FROTO (Ford Otosan)": {"ticker": "FROTO.IS", "type": "stock"},
    "THYAO (Türk Hava Yolları)": {"ticker": "THYAO.IS", "type": "stock"},
    "TUPRS (Tüpraş)": {"ticker": "TUPRS.IS", "type": "stock"},
    "VESTL (Vestel Elektronik)": {"ticker": "VESTL.IS", "type": "stock"},
    "USD/TRY (Dolar Kuru)": {"ticker": "USDTRY=X", "type": "fx"},
    "EUR/TRY (Euro Kuru)": {"ticker": "EURTRY=X", "type": "fx"},
    "Özel Sembol Gir...": {"ticker": "CUSTOM", "type": "custom"}
}

STOCKS_ONLY = {
    "ASELS (Aselsan)": "ASELS.IS",
    "BIMAS (BİM Mağazalar)": "BIMAS.IS",
    "EREGL (Erdemir)": "EREGL.IS",
    "FROTO (Ford Otosan)": "FROTO.IS",
    "THYAO (Türk Hava Yolları)": "THYAO.IS",
    "TUPRS (Tüpraş)": "TUPRS.IS",
    "VESTL (Vestel Elektronik)": "VESTL.IS"
}

def get_period_inflation(annual_inflation, p):
    period_months = {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12, "2y": 24, "5y": 60}
    months = period_months.get(p, 12)
    monthly_rate = (1 + (annual_inflation / 100)) ** (1 / 12) - 1
    period_enf = ((1 + monthly_rate) ** months - 1) * 100
    return period_enf, months

@st.cache_data(ttl=300)
def load_clean_data(ticker, p):
    df = pd.DataFrame()
    try:
        df = yf.download(ticker, period=p, interval="1d", auto_adjust=True, progress=False)
    except Exception:
        pass

    if df.empty or len(df) < 2:
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=p, interval="1d", auto_adjust=True)
        except Exception:
            pass

    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        df = df.dropna(subset=['Close'])
        for col in ['Open', 'High', 'Low']:
            if col not in df.columns:
                df[col] = df['Close']
    return df

@st.cache_data(ttl=900)
def get_fundamental_data(ticker_symbol):
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        t = yf.Ticker(ticker_symbol, session=session)
        info = t.info
        if info and isinstance(info, dict) and len(info) > 5:
            return info
    except Exception:
        pass
    return {}

def format_val(val, prefix="", suffix="", multiplier=1.0, precision=2):
    if val is None or not isinstance(val, (int, float)) or pd.isna(val):
        return "-"
    return f"{prefix}{val * multiplier:.{precision}f}{suffix}"

# --- MENÜ ---
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

# 1. KILAVUZ
if page_mode == "📖 Genel Bilgi & Finansal Kılavuz":
    st.subheader("📖 Finansal Okuryazarlık ve Analiz Parametreleri Kılavuzu")
    st.caption("Panelde yer alan tüm metriklerin finansal anlamı ve ideal referans değerleri:")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 1. Değerleme ve Çarpanlar")
        st.markdown("""
        * **F/K (Fiyat / Kazanç):** Şirketin hisse fiyatının yıllık hisse başı kâra oranıdır. 5–12 aralığı makul kabul edilir.
        * **İleri Dönem F/K:** Gelecek 12 ayın kâr beklentisine göre F/K.
        * **PD/DD (Piyasa/Defter):** Şirketin net varlıklarına göre çarpanı (1–3 arası dengeli).
        * **Temettü Verimi (%):** Yıllık nakit kâr payı dağıtım oranı.
        """)
        st.markdown("### 2. Getiri ve Enflasyon")
        st.markdown("""
        * **Nominal Getiri:** Paranın rakamsal artış oranı.
        * **Reel Getiri:** Enflasyondan arındırılmış satın alma gücü artışı.
        """)
    with c2:
        st.markdown("### 3. Bilanço Gücü ve Kârlılık")
        st.markdown("""
        * **Özsermaye Kârı (ROE):** Sermayenin kâr üretme hızı. Enflasyonun (%31.75) üzerinde olmalıdır.
        * **Net Kâr Marjı (%):** Cironun kâra dönüşme oranı.
        * **Borç / Özkaynak (%):** Borç yükü. %50–%150 bandı güvenlidir.
        * **Likit Oran (Quick Ratio):** Kısa vadeli borç ödeme gücü (1.0 ve üzeri idealdir).
        """)
        st.markdown("### 4. Teknik Göstergeler")
        st.markdown("""
        * **RSI (14):** 30 altı aşırı satım (ucuzluk), 70 üstü aşırı alım (şişkinlik).
        * **SMA 20 & 50:** Fiyat ortalamaların üzerindeyse trend pozitiftir.
        """)

# 2. KARŞILAŞTIRMA TABLOSU
elif page_mode == "📑 Tüm Hisselerin Özeti (Karşılaştırma)":
    st.subheader("📑 Takip Listesindeki Şirketlerin Temel Analiz Özeti")
    st.caption("Tüm hisselerin F/K, PD/DD, Kârlılık, Temettü ve Zirve İskonto oranları:")

    summary_rows = []
    with st.spinner("Şirket verileri toplanıyor..."):
        for name, ticker in STOCKS_ONLY.items():
            info = get_fundamental_data(ticker)
            
            p_cur = info.get("currentPrice", info.get("regularMarketPrice", None))
            if not p_cur:
                df_temp = load_clean_data(ticker, "5d")
                if not df_temp.empty:
                    p_cur = float(df_temp['Close'].iloc[-1])

            pe = info.get("trailingPE", None)
            pb = info.get("priceToBook", None)
            roe = info.get("returnOnEquity", None)
            margin = info.get("profitMargins", None)
            div_yield = info.get("dividendYield", None)
            h52 = info.get("fiftyTwoWeekHigh", None)

            zirve_fark = ((p_cur - h52) / h52 * 100) if (p_cur and h52) else None

            summary_rows.append({
                "Hisse": name.split(" ")[0],
                "Şirket": name.split("(")[1].replace(")", ""),
                "Son Fiyat": format_val(p_cur, suffix=" TL"),
                "F/K": format_val(pe),
                "PD/DD": format_val(pb),
                "ROE": format_val(roe, prefix="%", multiplier=100, precision=1),
                "Net Kâr Marjı": format_val(margin, prefix="%", multiplier=100, precision=1),
                "Temettü Verimi": format_val(div_yield, prefix="%", multiplier=100, precision=2),
                "Zirveye Uzaklık": format_val(zirve_fark, prefix="%", precision=1)
            })

    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

# 3. TEKİL DETAY
else:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Piyasa ve Fon Seçimi")
    selected_label = st.sidebar.selectbox("Takip Listesi:", list(WATCHLIST.keys()), index=0)
    selected_item = WATCHLIST[selected_label]

    if selected_item["type"] not in ["katilim_ppf", "sukuk"]:
        period = st.sidebar.selectbox("Zaman Aralığı", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    else:
        period = "1y"

    st.sidebar.markdown("---")
    st.sidebar.subheader("📌 Enflasyon Referansları")
    yillik_enf = st.sidebar.number_input("Yıllık Enflasyon (TÜFE %)", value=TUIK_YILLIK_ENFLASYON, step=0.5)

    donem_enf, ay_sayisi = get_period_inflation(yillik_enf, period)
    st.sidebar.metric(label=f"Seçilen Dönem Enflasyonu ({period} - {ay_sayisi} Aylık)", value=f"%{donem_enf:.2f}")

    if selected_item["type"] in ["katilim_ppf", "sukuk"]:
        st.subheader(f"🏷️ {selected_label}")
        fon_yillik = selected_item["yillik_getiri"]
        fon_reel = ((1 + (fon_yillik / 100)) / (1 + (yillik_enf / 100)) - 1) * 100

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fon Kodu", selected_item["ticker"])
        c2.metric("Yıllık Getiri", f"%{fon_yillik:.2f}")
        c3.metric("Yıllık Enflasyon", f"%{yillik_enf:.2f}")
        c4.metric(label="Yıllık Reel Getiri", value=f"%{fon_reel:+.2f}", delta=f"{fon_reel:+.2f}% Reel Fark")
    else:
        if selected_item["type"] == "gram_altin":
            symbol = "GRAM_ALTIN"
        elif selected_item["ticker"] == "CUSTOM":
            symbol = st.sidebar.text_input("Sembol Kodu:", value="TUPRS.IS").strip().upper()
        else:
            symbol = selected_item["ticker"]

        tab1, tab2 = st.tabs(["📊 Fiyat & Grafik Analizi", "📑 Temel Analiz & Şirket Karnesi"])

        with tab1:
            with st.spinner("Piyasa verileri yükleniyor..."):
                if selected_item["type"] == "gram_altin":
                    df_ons = load_clean_data("GC=F", period)
                    df_usd = load_clean_data("USDTRY=X", period)
                    if not df_ons.empty and not df_usd.empty:
                        data = pd.DataFrame(index=df_ons.index.intersection(df_usd.index))
                        for col in ['Open', 'High', 'Low', 'Close']:
                            data[col] = (df_ons[col] * df_usd[col]) / 31.1035
                        data = data.dropna()
                    else:
                        data = pd.DataFrame()
                else:
                    data = load_clean_data(symbol, period)

            if data.empty or len(data) < 2:
                st.error("Veri yüklenemedi.")
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
                birim = "Puan" if selected_item["type"] == "index" else ("TL" if "TL" in selected_label or ".IS" in symbol or selected_item["type"] == "gram_altin" else "$")
                c1.metric("Son Değer", f"{last_p:.2f} {birim}", f"{daily_c:+.2f}% Günlük")
                c2.metric(f"Nominal Getiri ({period})", f"%{period_r:+.2f}")
                c3.metric(f"{ay_sayisi} Aylık Enflasyon", f"%{donem_enf:.2f}")
                c4.metric(label=f"Reel Getiri ({period})", value=f"%{reel_r:+.2f}", delta=f"{reel_r:+.2f}% Reel Kazanç/Kayıp")
                rsi_durum = "Aşırı Alım" if last_rsi > 70 else ("Aşırı Satım" if last_rsi < 30 else "Nötr")
                c5.metric("RSI (14)", f"{last_rsi:.2f}", rsi_durum)

                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Fiyat"))
                fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='orange', width=1.5), name="SMA 20"))
                fig.add_trace(go.Scatter(x=data.index, y=data['SMA50'], line=dict(color='blue', width=1.5), name="SMA 50"))
                fig.update_layout(title=f"{selected_label} Fiyat Hareketi", xaxis_rangeslider_visible=False, height=450)
                st.plotly_chart(fig, use_container_width=True)

                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='purple', width=1.5), name="RSI"))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
                fig_rsi.update_layout(title="RSI Momentum", yaxis=dict(range=[0, 100]), height=200)
                st.plotly_chart(fig_rsi, use_container_width=True)

        with tab2:
            if selected_item["type"] == "stock" or (selected_item["type"] == "custom" and ".IS" in symbol):
                st.subheader(f"📑 {selected_label} - Finansal Sağlık Karnesi")
                info = get_fundamental_data(symbol)

                st.markdown("##### 1. Değerleme ve Çarpanlar")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("F/K", format_val(info.get("trailingPE")))
                k2.metric("İleri Dönem F/K", format_val(info.get("forwardPE")))
                k3.metric("PD/DD", format_val(info.get("priceToBook")))
                k4.metric("Temettü Verimi", format_val(info.get("dividendYield"), prefix="%", multiplier=100))

                st.markdown("---")
                st.markdown("##### 2. Kârlılık ve Borçluluk")
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Özsermaye Kârı (ROE)", format_val(info.get("returnOnEquity"), prefix="%", multiplier=100, precision=1))
                b2.metric("Net Kâr Marjı", format_val(info.get("profitMargins"), prefix="%", multiplier=100, precision=1))
                b3.metric("Borç / Özkaynak", format_val(info.get("debtToEquity"), prefix="%", precision=1))
                b4.metric("Likit Oran (Quick)", format_val(info.get("quickRatio")))
            else:
                st.info("Temel analiz karnesi sadece BIST hisse senetleri için geçerlidir.")
