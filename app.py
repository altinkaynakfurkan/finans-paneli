import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
import requests

st.set_page_config(page_title="Finans & Yatırım Analiz Paneli", layout="wide")

st.title("📊 Finansal Takip & Yatırım Analiz Paneli")

# 1. Yıllık Enflasyon Referansı
TUIK_YILLIK_ENFLASYON = 31.75

# 2. Varlık Listesi
WATCHLIST = {
    "KPI - İş Portföy Para Piyasası Katılım (TL) Fonu": {
        "ticker": "KPI", "type": "fund", "yillik_getiri": 44.50,
        "fon_adi": "İş Portföy Para Piyasası Katılım (TL) Fonu"
    },
    "IAT - İş Portföy Kira Sertifikaları Katılım (TL) Fonu": {
        "ticker": "IAT", "type": "fund", "yillik_getiri": 39.80,
        "fon_adi": "İş Portföy Kira Sertifikaları Katılım (TL) Fonu"
    },
    "Gram Altın (TL - Canlı Alış/Satış)": {"ticker": "GRAM_ALTIN", "type": "gram_altin"},
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

# BIST DÜNKÜ KAPANIŞ VE ANLIK FİYAT HESAPLAMA MOTORU
@st.cache_data(ttl=60)
def get_bist_live_snapshot(symbol):
    try:
        t = yf.Ticker(symbol)
        fi = getattr(t, 'fast_info', None)
        if fi:
            last_p = fi.get('lastPrice', None) or fi.get('last_price', None)
            prev_p = fi.get('previousClose', None) or fi.get('previous_close', None)
            if last_p and prev_p and prev_p > 0:
                change_amount = float(last_p) - float(prev_p)
                change_pct = (change_amount / float(prev_p)) * 100
                return float(last_p), float(prev_p), float(change_pct), float(change_amount)
    except Exception:
        pass
    return None, None, None, None

# CANLI GRAM ALTIN MOTORU
@st.cache_data(ttl=60)
def get_live_gram_altin(fallback_price=None):
    try:
        url = "https://api.genelpara.com/embed/altin.json"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if res.status_code == 200:
            data = res.json()
            ga = data.get("GA", {})
            alis = float(str(ga.get("alis", "0")).replace(",", "."))
            satis = float(str(ga.get("satis", "0")).replace(",", "."))
            degisim = float(str(ga.get("degisim", "0")).replace(",", "."))
            if alis > 1000 and satis > 1000:
                return {"alis": alis, "satis": satis, "makas": satis - alis, "degisim": degisim}
    except Exception:
        pass

    if fallback_price and fallback_price > 0:
        return {
            "alis": round(fallback_price * 0.995, 2),
            "satis": round(fallback_price * 1.005, 2),
            "makas": round(fallback_price * 0.01, 2),
            "degisim": 0.0
        }
    return None

# GEÇMİŞ ZAMAN SERİSİ MOTORU
@st.cache_data(ttl=600)
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
            df.columns = df.columns.get_level_values(0)
        df = df.loc[:, ~df.columns.duplicated()]

        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = pd.to_datetime(df.index).floor('D')

        df = df.dropna(subset=['Close'])
        for col in ['Open', 'High', 'Low']:
            if col not in df.columns:
                df[col] = df['Close']
        return df
    return pd.DataFrame()

# GRAM ALTIN ZAMAN SERİSİ
@st.cache_data(ttl=600)
def get_gram_altin_data(period):
    df_ons = load_clean_data("GC=F", period)
    df_usd = load_clean_data("USDTRY=X", period)

    if not df_ons.empty and not df_usd.empty:
        all_dates = df_ons.index.union(df_usd.index).sort_values()
        ons_c = df_ons['Close'].reindex(all_dates).ffill().bfill()
        usd_c = df_usd['Close'].reindex(all_dates).ffill().bfill()
        ons_o = df_ons['Open'].reindex(all_dates).ffill().bfill()
        usd_o = df_usd['Open'].reindex(all_dates).ffill().bfill()
        ons_h = df_ons['High'].reindex(all_dates).ffill().bfill()
        usd_h = df_usd['High'].reindex(all_dates).ffill().bfill()
        ons_l = df_ons['Low'].reindex(all_dates).ffill().bfill()
        usd_l = df_usd['Low'].reindex(all_dates).ffill().bfill()

        df_gram = pd.DataFrame(index=all_dates)
        df_gram['Close'] = (ons_c * usd_c) / 31.1035
        df_gram['Open'] = (ons_o * usd_o) / 31.1035
        df_gram['High'] = (ons_h * usd_h) / 31.1035
        df_gram['Low'] = (ons_l * usd_l) / 31.1035
        return df_gram.dropna()
    return pd.DataFrame()

# BULUT & LOKAL UYUMLU GÜVENLİ ÇARPAN MOTORU
@st.cache_data(ttl=3600)
def get_fundamental_data(ticker_symbol):
    data = {}
    try:
        t = yf.Ticker(ticker_symbol)
        
        # 1. Öncelik: fast_info (Bulutta engellenmeyen hızlı API)
        fi = getattr(t, 'fast_info', None)
        if fi:
            data["trailingPE"] = fi.get("trailing_pe", None) or fi.get("trailingPE", None)
            data["priceToBook"] = fi.get("price_to_book", None) or fi.get("priceToBook", None)
        
        # 2. Öncelik: info (Temettü ve kârlılık oranları)
        info = getattr(t, 'info', {})
        if isinstance(info, dict) and len(info) > 0:
            if not data.get("trailingPE"):
                data["trailingPE"] = info.get("trailingPE") or info.get("forwardPE")
            if not data.get("priceToBook"):
                data["priceToBook"] = info.get("priceToBook")
            
            div = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
            if div is not None:
                data["dividendYield"] = div if div < 1.0 else (div / 100.0)
                
            data["forwardPE"] = info.get("forwardPE")
            data["returnOnEquity"] = info.get("returnOnEquity")
            data["profitMargins"] = info.get("profitMargins")
            data["debtToEquity"] = info.get("debtToEquity")
            data["quickRatio"] = info.get("quickRatio")
    except Exception:
        pass
    return data

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

# 1. MOD: GENEL BİLGİ & FİNANSAL KILAVUZ
if page_mode == "📖 Genel Bilgi & Finansal Kılavuz":
    st.subheader("📖 Finansal Okuryazarlık, Temel Göstergeler & Yatırımcı Kılavuzu")
    st.caption("Paneldeki tüm göstergelerin Borsa İstanbul hesaplama mantığı:")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 1. 💵 Günlük Değişim ve Getiri Kuralları")
        st.markdown("""
        * **Resmi BIST Günlük Fark:** Anlık son fiyat ile dünkü resmi kapanış (uzlaşma) arasındaki net TL tutarı ve yüzdesel orandır:
          $$\\Delta \\text{TL} = \\text{Son Fiyat} - \\text{Dünkü Kapanış}$$
          $$\\text{Günlük Değişim (\\%)} = \\frac{\\Delta \\text{TL}}{\\text{Dünkü Kapanış}} \\times 100$$
        * **Reel Getiri (Fisher Formülü):** Enflasyondan arındırılmış satın alma gücü artışıdır:
          $$\\text{Reel Getiri} = \\frac{1 + \\text{Nominal Getiri}}{1 + \\text{Enflasyon}} - 1$$
        """)
        st.markdown("### 2. 📊 Şirket Değerleme Çarpanları")
        st.markdown("""
        * **F/K (Fiyat / Kazanç):** 5–12 ideal amortisman bandı.
        * **PD/DD (Piyasa/Defter):** 1–3 dengeli özkaynak çarpanı.
        * **Temettü Verimi (%):** Yıllık nakit kâr payı oranı.
        """)
    with col2:
        st.markdown("### 3. 🏢 Bilanço Sağlığı ve Kârlılık")
        st.markdown("""
        * **Özsermaye Kârı (ROE):** Sermayenin kâr üretme gücü (Enflasyonun üzerinde olmalı).
        * **Net Kâr Marjı (%):** Cironun kâra dönüşme oranı.
        * **Borç / Özkaynak (%):** %50–%150 güvenli borç seviyesi.
        """)
        st.markdown("### 4. 📈 Teknik Analiz")
        st.markdown("""
        * **RSI (14):** 30 altı aşırı satım (fırsat), 70 üstü aşırı alım (düzeltme riski).
        * **SMA 20 & 50:** Fiyat ortalamaların üzerindeyse trend pozitiftir.
        """)

# 2. MOD: TOPLU KARŞILAŞTIRMA TABLOSU
elif page_mode == "📑 Tüm Hisselerin Özeti (Karşılaştırma)":
    st.subheader("📑 Takip Listesindeki Şirketlerin Karşılaştırmalı Performans Tablosu")
    
    comp_period = st.sidebar.selectbox("Karşılaştırma Dönemi:", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    yillik_enf = st.sidebar.number_input("Yıllık Enflasyon (TÜFE %)", value=TUIK_YILLIK_ENFLASYON, step=0.5)
    donem_enf, ay_sayisi = get_period_inflation(yillik_enf, comp_period)
    
    st.caption(f"Hesaplama: **Dünkü Kapanışa Göre BIST Değişimi** | Seçilen Dönem: **{comp_period} ({ay_sayisi} Aylık)** | Enflasyon: **%{donem_enf:.2f}**")

    summary_rows = []
    with st.spinner("Şirket verileri BIST formülüyle hesaplanıyor..."):
        for name, ticker in STOCKS_ONLY.items():
            df_hist = load_clean_data(ticker, "1y")
            info = get_fundamental_data(ticker)
            live_last, live_prev, live_change, live_diff = get_bist_live_snapshot(ticker)

            if not df_hist.empty and len(df_hist) >= 2:
                last_p = live_last if live_last is not None else float(df_hist['Close'].iloc[-1])
                prev_close = live_prev if live_prev is not None else float(df_hist['Close'].iloc[-2])
                
                diff_amount = live_diff if live_diff is not None else (last_p - prev_close)
                daily_c = live_change if live_change is not None else ((diff_amount / prev_close) * 100)

                df_period = load_clean_data(ticker, comp_period)
                if not df_period.empty and len(df_period) >= 1:
                    start_p = float(df_period['Close'].iloc[0])
                    nom_ret = ((last_p - start_p) / start_p) * 100
                    reel_ret = ((1 + (nom_ret / 100)) / (1 + (donem_enf / 100)) - 1) * 100
                else:
                    nom_ret, reel_ret = 0.0, 0.0

                h52 = float(df_hist['High'].max())
                zirve_iskonto = ((last_p - h52) / h52) * 100

                rsi_series = RSIIndicator(close=df_hist['Close'], window=min(14, len(df_hist))).rsi()
                last_rsi = float(rsi_series.iloc[-1]) if pd.notnull(rsi_series.iloc[-1]) else 50.0

                pe = info.get("trailingPE", None)
                pb = info.get("priceToBook", None)
                div_yield = info.get("dividendYield", None)

                summary_rows.append({
                    "Hisse": name.split(" ")[0],
                    "Şirket": name.split("(")[1].replace(")", ""),
                    "Son Fiyat": f"{last_p:.2f} TL",
                    "Günlük Fark (BIST)": f"{diff_amount:+.2f} TL (%{daily_c:+.2f})",
                    f"Nominal ({comp_period})": f"%{nom_ret:+.2f}",
                    f"Reel ({comp_period})": f"%{reel_ret:+.2f}",
                    "Zirve İskonto": f"%{zirve_iskonto:.1f}",
                    "RSI (14)": f"{last_rsi:.1f}",
                    "F/K": format_val(pe),
                    "PD/DD": format_val(pb),
                    "Temettü": format_val(div_yield, prefix="%", multiplier=100, precision=2)
                })

    if summary_rows:
        df_summary = pd.DataFrame(summary_rows)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
    else:
        st.error("Veriler yüklenemedi. Lütfen sayfayı yenileyiniz.")

# 3. MOD: TEKİL DETAY SAYFASI
else:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Piyasa ve Fon Seçimi")
    selected_label = st.sidebar.selectbox("Takip Listesi:", list(WATCHLIST.keys()), index=5)
    selected_item = WATCHLIST[selected_label]

    if selected_item["type"] != "fund":
        period = st.sidebar.selectbox("Zaman Aralığı", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    else:
        period = "1y"

    st.sidebar.markdown("---")
    st.sidebar.subheader("📌 Enflasyon Referansları")
    yillik_enf = st.sidebar.number_input("Yıllık Enflasyon (TÜFE %)", value=TUIK_YILLIK_ENFLASYON, step=0.5)

    donem_enf, ay_sayisi = get_period_inflation(yillik_enf, period)
    st.sidebar.metric(label=f"Seçilen Dönem Enflasyonu ({period} - {ay_sayisi} Aylık)", value=f"%{donem_enf:.2f}")

    # FONLAR
    if selected_item["type"] == "fund":
        st.subheader(f"🏷️ {selected_label}")
        fon_yillik = selected_item["yillik_getiri"]
        fon_gunluk = ((1 + (fon_yillik / 100)) ** (1 / 365) - 1) * 100
        fon_aylik = ((1 + (fon_yillik / 100)) ** (1 / 12) - 1) * 100
        fon_reel = ((1 + (fon_yillik / 100)) / (1 + (yillik_enf / 100)) - 1) * 100

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Fon Kodu", selected_item["ticker"])
        c2.metric("Günlük Getiri", f"%{fon_gunluk:.4f}")
        c3.metric("Aylık Getiri", f"%{fon_aylik:.2f}")
        c4.metric("Yıllık Brüt", f"%{fon_yillik:.2f}")
        c5.metric(label="Yıllık Reel Getiri", value=f"%{fon_reel:+.2f}", delta=f"{fon_reel:+.2f}% Reel Kazanç")

        st.info(f"""
        **{selected_item['fon_adi']} Özeti:**
        * **Portföy Yöneticisi:** İş Portföy Yönetimi A.Ş.
        * **Fon Türü:** {'Katılım Para Piyasası (Faizsiz Likit TL)' if selected_item['ticker'] == 'KPI' else 'Kira Sertifikaları Katılım (Sukuk TL)'}
        * **İşlem:** TEFAS üzerinden tüm bankalardan valörsüz alınıp satılabilir.
        """)

    # HİSSE, GRAM ALTIN, ONS, BIST 100, DÖVİZ
    else:
        if selected_item["type"] == "gram_altin":
            symbol = "GRAM_ALTIN"
        elif selected_item["ticker"] == "CUSTOM":
            symbol = st.sidebar.text_input("Sembol Kodu (örn. TUPRS.IS):", value="TUPRS.IS").strip().upper()
        else:
            symbol = selected_item["ticker"]

        tab1, tab2 = st.tabs(["📊 Fiyat & Grafik Analizi", "📑 Temel Analiz & Şirket Karnesi"])

        with tab1:
            with st.spinner("Piyasa verileri yükleniyor..."):
                if selected_item["type"] == "gram_altin":
                    data = get_gram_altin_data(period)
                    live_last, live_prev, live_diff = None, None, None
                else:
                    data = load_clean_data(symbol, period)
                    live_last, live_prev, _, live_diff = get_bist_live_snapshot(symbol)

            if data.empty or len(data) < 2:
                st.error("Seçilen varlık için canlı veri çekilemedi.")
            else:
                data['SMA20'] = SMAIndicator(close=data['Close'], window=min(20, len(data))).sma_indicator()
                data['SMA50'] = SMAIndicator(close=data['Close'], window=min(50, len(data))).sma_indicator()
                data['RSI'] = RSIIndicator(close=data['Close'], window=min(14, len(data))).rsi()

                start_p = float(data['Close'].iloc[0])
                last_p = live_last if live_last is not None else float(data['Close'].iloc[-1])
                prev_close = live_prev if live_prev is not None else float(data['Close'].iloc[-2])
                
                diff_amount = live_diff if live_diff is not None else (last_p - prev_close)
                daily_c = ((last_p - prev_close) / prev_close) * 100
                period_r = ((last_p - start_p) / start_p) * 100
                last_rsi = float(data['RSI'].iloc[-1]) if pd.notnull(data['RSI'].iloc[-1]) else 50.0
                reel_r = ((1 + (period_r / 100)) / (1 + (donem_enf / 100)) - 1) * 100

                st.subheader(f"📈 {selected_label}")

                birim = "Puan" if symbol == "XU100.IS" else ("TL" if "TL" in selected_label or ".IS" in symbol or selected_item["type"] == "gram_altin" else "$")

                if selected_item["type"] == "gram_altin":
                    live_gold = get_live_gram_altin(last_p)
                    c1, c2, c3, c4, c5 = st.columns(5)
                    if live_gold:
                        c1.metric("Canlı Alış", f"{live_gold['alis']:.2f} TL")
                        c2.metric("Canlı Satış", f"{live_gold['satis']:.2f} TL", f"{diff_amount:+.2f} TL (%{daily_c:+.2f})")
                        c3.metric("Alış-Satış Makası", f"{live_gold['makas']:.2f} TL")
                    else:
                        c1.metric("Son Değer", f"{last_p:.2f} TL", f"{diff_amount:+.2f} TL (%{daily_c:+.2f})")
                        c2.metric("Nominal Getiri", f"%{period_r:+.2f}")
                        c3.metric("Dönem Enflasyonu", f"%{donem_enf:.2f}")

                    c4.metric(f"Nominal ({period})", f"%{period_r:+.2f}")
                    c5.metric(label=f"Reel ({period})", value=f"%{reel_r:+.2f}", delta=f"{reel_r:+.2f}% Reel Fark")
                else:
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Son Değer", f"{last_p:.2f} {birim}", f"{diff_amount:+.2f} {birim} (%{daily_c:+.2f})")
                    c2.metric(f"Nominal Getiri ({period})", f"%{period_r:+.2f}")
                    c3.metric(f"{ay_sayisi} Aylık Enflasyon", f"%{donem_enf:.2f}")
                    c4.metric(label=f"Reel Getiri ({period})", value=f"%{reel_r:+.2f}", delta=f"{reel_r:+.2f}% Reel Kazanç/Kayıp")
                    rsi_durum = "Aşırı Alım" if last_rsi > 70 else ("Aşırı Satım" if last_rsi < 30 else "Nötr")
                    c5.metric("RSI (14)", f"{last_rsi:.2f}", rsi_durum)

                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Fiyat"))
                fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='orange', width=1.5), name="SMA 20"))
                fig.add_trace(go.Scatter(x=data.index, y=data['SMA50'], line=dict(color='blue', width=1.5), name="SMA 50"))
                fig.update_layout(title=f"{selected_label} Fiyat Hareketi ve Ortalamalar", xaxis_rangeslider_visible=False, height=450)
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
