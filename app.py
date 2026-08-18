import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator

st.set_page_config(page_title="Finans & Yatırım Analiz Paneli", layout="wide")

st.title("📊 Finansal Takip & Yatırım Analiz Paneli")

# 1. Enflasyon Referansı
TUIK_YILLIK_ENFLASYON = 31.75

# 2. Varlık Listesi
WATCHLIST = {
    "KPI - İş Portföy Para Piyasası Katılım Fonu": {
        "ticker": "KPI", "type": "fund", "yillik_getiri": 44.50,
        "fon_adi": "İş Portföy Para Piyasası Katılım (TL) Fonu"
    },
    "IAT - İş Portföy Kira Sertifikaları Katılım Fonu": {
        "ticker": "IAT", "type": "fund", "yillik_getiri": 39.80,
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

@st.cache_data(ttl=600)
def load_clean_data(ticker, p):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=p, interval="1d", auto_adjust=True)
        if df.empty or len(df) < 2:
            df = yf.download(ticker, period=p, interval="1d", auto_adjust=True, progress=False)

        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=['Close'])
            for col in ['Open', 'High', 'Low']:
                if col not in df.columns:
                    df[col] = df['Close']
            return df
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=900)
def get_fundamental_data(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
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

# --- MENÜ SEÇİMİ ---
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

# ==========================================
# 1. MOD: GENEL BİLGİ & FİNANSAL KILAVUZ (TAM KAPSAMLI)
# ==========================================
if page_mode == "📖 Genel Bilgi & Finansal Kılavuz":
    st.subheader("📖 Finansal Okuryazarlık, Temel Göstergeler & Yatırımcı Kılavuzu")
    st.caption("Paneldeki tüm analitik göstergelerin finansal mantığı, ideal referans aralıkları ve pratik kullanım kuralları:")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 1. 💵 Getiri ve Enflasyon Dinamikleri")
        st.markdown("""
        * **Nominal Getiri:** Paranın sadece etiket/sayısal büyümesidir. Örneğin 100.000 TL paranız 1 yıl sonunda 130.000 TL olduğunda nominal getiri **%30**'dur.
        * **Reel Getiri (Satın Alma Gücü Kazanımı):** Paranın mal ve hizmet sepeti karşısındaki net güç artışıdır. Finans literatüründe **Fisher Formülü** ile hesaplanır:
          $$\\text{Reel Getiri} = \\frac{1 + \\text{Nominal Getiri}}{1 + \\text{Enflasyon}} - 1$$
        * **Yatırımcı Kuralı:** Nominal kazanç psikolojik bir yanılsama olabilir; portföyü büyüten tek faktör enflasyonun üzerindeki **pozitif reel getiri**dir.
        """)

        st.markdown("### 2. 📊 Şirket Değerleme Çarpanları")
        st.markdown("""
        * **F/K (Fiyat / Kazanç Oranı):** 
          * *Anlamı:* Şirketin hisse fiyatının, hisse başına yıllık net kârına oranıdır. *"Şirket bugünkü kâr performansıyla piyasa değerini kaç yılda amorti eder?"* sorusunun yanıtıdır.
          * *İdeal Aralık:* BIST sanayi şirketlerinde **5 – 12** aralığı makul kabul edilir. Sektör ortalamasından belirgin düşük olması iskontoya işaret eder.
        * **İleri Dönem F/K (Forward P/E):** Gelecek 12 ayın kâr tahminleriyle hesaplanan F/K'dır. Mevcut F/K'dan düşükse şirketin kârını büyüteceği bekleniyor demektir.
        * **PD/DD (Piyasa Değeri / Defter Değeri):**
          * *Anlamı:* Şirketin borsadaki toplam değerinin, bilançosundaki net özkaynaklarına (tüm varlıklar - borçlar) oranıdır.
          * *İdeal Aralık:* **1.0 – 3.0** bandı dengeli sayılır. 1'in altı şirketin fabrikaları ve varlıklarının piyasada iskonto gördüğünü ifade eder.
        * **Temettü Verimi (%):** Şirketin elde ettiği kârdan hisse başına dağıttığı nakit kâr payının hisse fiyatına oranıdır. %5 ve üzeri verim düzenli pasif gelir sağlar.
        """)

        st.markdown("### 3. 🥇 Emtia, Döviz ve BIST Endeksleri")
        st.markdown("""
        * **Gram Altın (TL) Formülü:**
          $$\\text{Gram Altın (TL)} = \\frac{\\text{Ons Altın (USD)} \\times \\text{USD/TRY}}{31{,}1035}$$
          Hem ons fiyatından hem de Dolar kurundan beslendiği için çifte koruma (hedge) sağlar.
        * **BIST 100 Endeksi (XU100):** Borsa İstanbul'da işlem gören en yüksek piyasa değerine ve işlem hacmine sahip 100 şirketin ağırlıklı performans göstergesidir.
        """)

    with col2:
        st.markdown("### 4. 🏢 Bilanço Sağlığı ve Kârlılık Gücü")
        st.markdown("""
        * **Özsermaye Kârlılığı (ROE - Return on Equity):**
          * *Anlamı:* Şirket ortaklarının koyduğu her 100 TL özkaynak ile yıl sonunda ne kadar net kâr üretildiğidir.
          * *Kritik Kural:* ROE mutlaka yıllık enflasyon oranından (%31,75) yüksek olmalıdır. Aksi halde şirket reel olarak erir.
        * **Net Kâr Marjı (%):** Şirketin kasasına giren her 100 TL cironun kaç TL'sinin kâr olarak kaldığıdır. Fiyatlama gücünü gösterir.
        * **Borç / Özkaynak Oranı (%):** Şirketin toplam finansal borçlarının özkaynaklara oranıdır. Yüksek faiz dönemlerinde **%150'nin altı** güvenli limandır.
        * **Likit Oran (Quick Ratio / Asit-Test):** Şirketin stoklarını satmasına gerek kalmadan, kasadaki nakit ve alacaklarıyla kısa vadeli borçlarını ödeyebilme gücüdür (**$\ge 1.0$ idealdir**).
        """)

        st.markdown("### 5. 📈 Teknik Analiz ve Momentum")
        st.markdown("""
        * **RSI (14 - Göreceli Güç Endeksi):** 0-100 arasında momentumu ölçer.
          * **30'un Altı (Aşırı Satım):** Satışlar panik boyutuna ulaşmış, fiyat aşırı ucuzlamış olabilir (Tepki yükselişi potansiyeli).
          * **50 – 65 Arası:** Sağlıklı ve dengeli boğa yükseliş trendi.
          * **70'in Üstü (Aşırı Alım):** Coşku aşırı artmış, kâr satışı ve düzeltme riski yükselmiştir.
        * **SMA 20 ve SMA 50 (Hareketli Ortalamalar):**
          * Fiyat ortalamaların üzerindeyse trend yukarıdır.
          * **Golden Cross (Altın Kesişme):** Kısa vadeli ortalamanın uzun vadeli ortalamayı yukarı kesmesi güçlü boğa rallisini işaret eder.
        """)

        st.markdown("### 6. 🛡️ Portföy Mimarisi (Savunma vs. Hücum)")
        st.markdown("""
        * **Savunma & Likidite (KPI - Katılım Para Piyasası Fonu):** Değeri düşmeyen, her gün istikrarlı getiri yazan acil durum ve fırsat nakdidir.
        * **Dengeleyici & Sukuk (IAT - Kira Sertifikaları Fonu):** Düzenli faizsiz kira geliri akışı sağlar, dalgalanmayı düşürür.
        * **Hücum & Büyüme (BIST Hisseleri - FROTO, TUPRS, ASELS vb.):** İhracat, kapasite artışı ve temettüyle enflasyonu uzun vadede katlayan ana büyüme motorudur.
        """)

# ==========================================
# 2. MOD: TOPLU KARŞILAŞTIRMA TABLOSU
# ==========================================
elif page_mode == "📑 Tüm Hisselerin Özeti (Karşılaştırma)":
    st.subheader("📑 Takip Listesindeki Şirketlerin Karşılaştırmalı Performans Tablosu")
    
    comp_period = st.sidebar.selectbox("Karşılaştırma Dönemi:", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    yillik_enf = st.sidebar.number_input("Yıllık Enflasyon (TÜFE %)", value=TUIK_YILLIK_ENFLASYON, step=0.5)
    donem_enf, ay_sayisi = get_period_inflation(yillik_enf, comp_period)
    
    st.caption(f"Seçilen Dönem: **{comp_period} ({ay_sayisi} Aylık)** | Dönem Enflasyonu: **%{donem_enf:.2f}**")

    summary_rows = []
    with st.spinner("Şirket verileri hesaplanıyor..."):
        for name, ticker in STOCKS_ONLY.items():
            df_hist = load_clean_data(ticker, "1y")
            info = get_fundamental_data(ticker)

            if not df_hist.empty and len(df_hist) >= 2:
                last_p = float(df_hist['Close'].iloc[-1])
                prev_p = float(df_hist['Close'].iloc[-2])
                daily_c = ((last_p - prev_p) / prev_p) * 100

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
                    "Günlük Fark": f"%{daily_c:+.2f}",
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

# ==========================================
# 3. MOD: TEKİL DETAY SAYFASI
# ==========================================
else:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Piyasa ve Fon Seçimi")
    selected_label = st.sidebar.selectbox("Takip Listesi:", list(WATCHLIST.keys()), index=0)
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

    # FONLAR (KPI & IAT)
    if selected_item["type"] == "fund":
        st.subheader(f"🏷️ {selected_label}")
        fon_yillik = selected_item["yillik_getiri"]
        fon_reel = ((1 + (fon_yillik / 100)) / (1 + (yillik_enf / 100)) - 1) * 100

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fon Kodu", selected_item["ticker"])
        c2.metric("Yıllık Getiri (Brüt)", f"%{fon_yillik:.2f}")
        c3.metric("Yıllık Enflasyon", f"%{yillik_enf:.2f}")
        c4.metric(label="Yıllık Reel Getiri", value=f"%{fon_reel:+.2f}", delta=f"{fon_reel:+.2f}% Reel Kazanç")

        st.info(f"""
        **{selected_item['fon_adi']} Özeti:**
        * **Yönetici:** İş Portföy Yönetimi A.Ş.
        * **Getiri Tipi:** {'Faizsiz Katılım Para Piyasası (Likit TL)' if selected_item['ticker'] == 'KPI' else 'Kira Sertifikaları Katılım (Sukuk TL)'}
        * **İşlem:** TEFAS üzerinden tüm bankalardan alınıp satılabilir.
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
                    df_ons = load_clean_data("GC=F", period)
                    df_usd = load_clean_data("USDTRY=X", period)
                    if not df_ons.empty and not df_usd.empty:
                        common_index = df_ons.index.intersection(df_usd.index)
                        data = pd.DataFrame(index=common_index)
                        for col in ['Open', 'High', 'Low', 'Close']:
                            data[col] = (df_ons.loc[common_index, col] * df_usd.loc[common_index, col]) / 31.1035
                        data = data.dropna()
                    else:
                        data = pd.DataFrame()
                else:
                    data = load_clean_data(symbol, period)

            if data.empty or len(data) < 2:
                st.error("Veri alınamadı. Lütfen sembolün doğruluğunu kontrol ediniz.")
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
                birim = "Puan" if symbol == "XU100.IS" else ("TL" if "TL" in selected_label or ".IS" in symbol or selected_item["type"] == "gram_altin" else "$")
                c1.metric("Son Değer", f"{last_p:.2f} {birim}", f"{daily_c:+.2f}% Günlük")
                c2.metric(f"Nominal ({period})", f"%{period_r:+.2f}")
                c3.metric(f"{ay_sayisi} Aylık Enflasyon", f"%{donem_enf:.2f}")
                c4.metric(label=f"Reel ({period})", value=f"%{reel_r:+.2f}", delta=f"{reel_r:+.2f}% Reel Fark")
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
