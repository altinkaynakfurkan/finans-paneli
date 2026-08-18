import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator

st.set_page_config(page_title="Finans & İş Portföy Katılım Takip Paneli", layout="wide")

st.title("📊 Finansal Takip, İş Portföy Katılım ve Dönemsel Enflasyon Analizi")

# 1. Yıllık Enflasyon Referansı
TUIK_YILLIK_ENFLASYON = 31.75  # TÜİK güncel yıllık TÜFE (%)

# 2. İstenen Sıralamaya Göre Düzenlenmiş Varlık Listesi
WATCHLIST = {
    # 1. Para Piyasası Fonu
    "KPI - İş Portföy Para Piyasası Katılım (TL) Fonu": {
        "ticker": "KPI", 
        "type": "katilim_ppf", 
        "yillik_getiri": 44.50,
        "fon_adi": "İş Portföy Para Piyasası Katılım (TL) Fonu"
    },
    
    # 2. Kira Sertifikaları Fonu
    "IAT - İş Portföy Kira Sertifikaları Katılım (TL) Fonu": {
        "ticker": "IAT", 
        "type": "sukuk", 
        "yillik_getiri": 39.80,
        "fon_adi": "İş Portföy Kira Sertifikaları Katılım (TL) Fonu"
    },

    # 3. Altın Gram
    "Gram Altın (TL)": {"ticker": "GRAM_ALTIN", "type": "gram_altin"},

    # 4. Altın Ons
    "Altın Ons (USD)": {"ticker": "GC=F", "type": "commodity"},

    # 5. Hisseler (A'dan Z'ye Alfabetik)
    "ASELS (Aselsan)": {"ticker": "ASELS.IS", "type": "stock"},
    "BIMAS (BİM Mağazalar)": {"ticker": "BIMAS.IS", "type": "stock"},
    "EREGL (Erdemir)": {"ticker": "EREGL.IS", "type": "stock"},
    "FROTO (Ford Otosan)": {"ticker": "FROTO.IS", "type": "stock"},
    "THYAO (Türk Hava Yolları)": {"ticker": "THYAO.IS", "type": "stock"},
    "VESTL (Vestel Elektronik)": {"ticker": "VESTL.IS", "type": "stock"},

    # 6. Döviz Kurları & Özel Arama
    "USD/TRY (Dolar Kuru)": {"ticker": "USDTRY=X", "type": "fx"},
    "EUR/TRY (Euro Kuru)": {"ticker": "EURTRY=X", "type": "fx"},
    "Özel Sembol Gir...": {"ticker": "CUSTOM", "type": "custom"}
}

# Zaman Aralığına Göre Dinamik Kümülatif Enflasyon Hesabı
def get_period_inflation(annual_inflation, p):
    period_months = {
        "1mo": 1,
        "3mo": 3,
        "6mo": 6,
        "1y": 12,
        "2y": 24,
        "5y": 60
    }
    months = period_months.get(p, 12)
    monthly_rate = (1 + (annual_inflation / 100)) ** (1 / 12) - 1
    period_enf = ((1 + monthly_rate) ** months - 1) * 100
    return period_enf, months

# --- Sol Menü ---
st.sidebar.header("Piyasa ve Fon Seçimi")
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
st.sidebar.metric(
    label=f"Seçilen Dönem Enflasyonu ({period} - {ay_sayisi} Aylık)",
    value=f"%{donem_enf:.2f}"
)
st.sidebar.caption(f"Yıllık %{yillik_enf:.2f} referansına göre {ay_sayisi} aylık bileşik TÜFE karşılığı.")

# Temiz Veri Çekme Motoru
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

# --- A. İŞ PORTFÖY KATILIM FONLARI ---
if selected_item["type"] in ["katilim_ppf", "sukuk"]:
    st.subheader(f"🏷️ {selected_label}")
    fon_yillik = selected_item["yillik_getiri"]
    fon_reel_getiri = ((1 + (fon_yillik / 100)) / (1 + (yillik_enf / 100)) - 1) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fon Kodu", selected_item["ticker"])
    c2.metric("Yıllık Getiri", f"%{fon_yillik:.2f}")
    c3.metric("Yıllık Enflasyon", f"%{yillik_enf:.2f}")
    c4.metric(
        label="Yıllık Reel Getiri",
        value=f"%{fon_reel_getiri:+.2f}",
        delta=f"{fon_reel_getiri:+.2f}% Enflasyon Farkı"
    )

    st.info(f"""
    **{selected_item['fon_adi']} Özeti:**
    * **Portföy Yöneticisi:** İş Portföy Yönetimi A.Ş.
    * **Fon Türü:** {'Katılım Para Piyasası (Faizsiz Likit TL)' if selected_item['type'] == 'katilim_ppf' else 'Kira Sertifikaları Katılım (Sukuk TL)'}
    * **İşlem Platformu:** TEFAS (Tüm bankalardan alınıp satılabilir).
    """)

# --- B. GRAM ALTIN, HİSSE, DÖVİZ VE EMTİA GÖRÜNÜMÜ ---
else:
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
            if selected_item["ticker"] == "CUSTOM":
                symbol = st.sidebar.text_input("Sembol Kodu:", value="ASELS.IS").strip().upper()
            else:
                symbol = selected_item["ticker"]
            data = load_clean_data(symbol, period)

    if data.empty or len(data) < 2:
        st.error(f"Seçilen varlık için canlı veri çekilemedi. Lütfen bağlantınızı kontrol ediniz.")
    else:
        # İndikatörler
        data['SMA20'] = SMAIndicator(close=data['Close'], window=min(20, len(data))).sma_indicator()
        data['SMA50'] = SMAIndicator(close=data['Close'], window=min(50, len(data))).sma_indicator()
        data['RSI'] = RSIIndicator(close=data['Close'], window=min(14, len(data))).rsi()

        start_price = float(data['Close'].iloc[0])
        last_close = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2])
        daily_change = ((last_close - prev_close) / prev_close) * 100
        period_return = ((last_close - start_price) / start_price) * 100
        last_rsi = float(data['RSI'].iloc[-1]) if pd.notnull(data['RSI'].iloc[-1]) else 50.0

        # Reel Getiri Hesabı
        reel_getiri = ((1 + (period_return / 100)) / (1 + (donem_enf / 100)) - 1) * 100

        st.subheader(f"📈 {selected_label}")

        # 1. Özet Metrik Kartları
        c1, c2, c3, c4, c5 = st.columns(5)
        birim = "TL" if "TL" in selected_label or ".IS" in selected_item.get("ticker", "") or selected_item["type"] == "gram_altin" else "$"
        c1.metric("Son Fiyat", f"{last_close:.2f} {birim}", f"{daily_change:+.2f}% Günlük")
        c2.metric(f"Nominal Getiri ({period})", f"%{period_return:+.2f}")
        c3.metric(f"{ay_sayisi} Aylık Enflasyon", f"%{donem_enf:.2f}")
        
        c4.metric(
            label=f"Reel Getiri ({period})",
            value=f"%{reel_getiri:+.2f}",
            delta=f"{reel_getiri:+.2f}% Reel Kazanç/Kayıp"
        )
        rsi_durum = "Aşırı Alım" if last_rsi > 70 else ("Aşırı Satım" if last_rsi < 30 else "Nötr")
        c5.metric("RSI (14)", f"{last_rsi:.2f}", rsi_durum)

        # 2. Mum & SMA Grafiği
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Fiyat"))
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='orange', width=1.5), name="SMA 20"))
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA50'], line=dict(color='blue', width=1.5), name="SMA 50"))
        fig.update_layout(title=f"{selected_label} Fiyat Hareketi ve Ortalamalar", xaxis_rangeslider_visible=False, height=450)
        st.plotly_chart(fig, use_container_width=True)

        # 3. RSI Grafiği
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='purple', width=1.5), name="RSI"))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        fig_rsi.update_layout(title="RSI Momentum", yaxis=dict(range=[0, 100]), height=200)
        st.plotly_chart(fig_rsi, use_container_width=True)
