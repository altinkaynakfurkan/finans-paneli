import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator

st.set_page_config(page_title="Finans & Yatırım Analiz Paneli", layout="wide")

st.title("📊 Finansal Takip, İş Portföy Katılım ve Yatırım Analiz Paneli")

# 1. Yıllık Enflasyon Referansı
TUIK_YILLIK_ENFLASYON = 31.75  # TÜİK güncel yıllık TÜFE (%)

# 2. Varlık Listesi
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

    # 5. BIST 100 Endeksi
    "BIST 100 Endeksi": {"ticker": "XU100.IS", "type": "index"},

    # 6. Hisseler (A'dan Z'ye Alfabetik)
    "ASELS (Aselsan)": {"ticker": "ASELS.IS", "type": "stock"},
    "BIMAS (BİM Mağazalar)": {"ticker": "BIMAS.IS", "type": "stock"},
    "EREGL (Erdemir)": {"ticker": "EREGL.IS", "type": "stock"},
    "FROTO (Ford Otosan)": {"ticker": "FROTO.IS", "type": "stock"},
    "THYAO (Türk Hava Yolları)": {"ticker": "THYAO.IS", "type": "stock"},
    "TUPRS (Tüpraş)": {"ticker": "TUPRS.IS", "type": "stock"},
    "VESTL (Vestel Elektronik)": {"ticker": "VESTL.IS", "type": "stock"},

    # 7. Döviz Kurları & Özel Arama
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

# Zaman Aralığına Göre Dinamik Kümülatif Enflasyon Hesabı
def get_period_inflation(annual_inflation, p):
    period_months = {
        "1mo": 1, "3mo": 3, "6mo": 6, "1y": 12, "2y": 24, "5y": 60
    }
    months = period_months.get(p, 12)
    monthly_rate = (1 + (annual_inflation / 100)) ** (1 / 12) - 1
    period_enf = ((1 + monthly_rate) ** months - 1) * 100
    return period_enf, months

# Temiz Fiyat Verisi Çekme Motoru
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

# Temel Analiz Bilgilerini Çekme Fonksiyonu
@st.cache_data(ttl=600)
def get_fundamental_data(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        return t.info
    except Exception:
        return {}

# --- SOL MENÜ NAVİGASYONU ---
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
# 1. MOD: GENEL BİLGİ & FİNANSAL KILAVUZ
# ==========================================
if page_mode == "📖 Genel Bilgi & Finansal Kılavuz":
    st.subheader("📖 Finansal Okuryazarlık ve Analiz Parametreleri Kılavuzu")
    st.caption("Panelde yer alan tüm metriklerin finansal anlamı ve ideal referans değerleri:")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 1. Değerleme ve Çarpanlar")
        st.markdown("""
        * **F/K (Fiyat / Kazanç):** 
          * *Anlamı:* Şirketin hisse fiyatının, hisse başına düşen yıllık net kârına oranıdır. Şirketin mevcut kârıyla piyasa değerini kaç yılda amorti edeceğini gösterir.
          * *İdeal Değer:* Genellikle **5 – 12** aralığı makul kabul edilir. Sektör ortalamasından düşük olması iskontolu (ucuz) olduğuna işaret edebilir.
        
        * **İleri Dönem F/K (Forward P/E):**
          * *Anlamı:* Analistlerin gelecek 12 ay için beklediği tahmini kâra göre hesaplanan F/K'dır. Mevcut F/K'dan düşükse kârın büyüyeceği bekleniyor demektir.
        
        * **PD/DD (Piyasa Değeri / Defter Değeri):**
          * *Anlamı:* Şirketin borsadaki toplam piyasa değerinin, şirketin özkaynaklarına (net mal varlığına) bölünmesidir.
          * *İdeal Değer:* Sanayi şirketlerinde **1 – 3** bandı dengeli sayılır. 1'in altı şirketin varlıklarının altında fiyatlandığını gösterir.
        
        * **Temettü Verimi (%):**
          * *Anlamı:* Şirketin elde ettiği kârdan hisse başına nakit dağıttığı kâr payının hisse fiyatına oranıdır.
          * *İdeal Değer:* %5 ve üzeri düzenli temettü ödeyen şirketler güçlü pasif gelir kaynağıdır.
        """)

        st.markdown("### 2. Getiri ve Enflasyon")
        st.markdown("""
        * **Nominal Getiri:** Paranın rakamsal artış oranıdır.
        * **Reel Getiri (Fisher Formülü):** Enflasyondan arındırılmış gerçek satın alma gücü kazancıdır.
          $$\\text{Reel Getiri} = \\frac{1 + \\text{Nominal Getiri}}{1 + \\text{Enflasyon}} - 1$$
        """)

    with c2:
        st.markdown("### 3. Bilanço Gücü ve Kârlılık")
        st.markdown("""
        * **Özsermaye Kârlılığı (ROE - Return on Equity):**
          * *Anlamı:* Şirketin ortaklarının koyduğu her 100 TL sermaye ile yıl sonunda ne kadar net kâr ürettiğini gösterir.
          * *İdeal Değer:* Enflasyonun üzerinde olmalıdır (En az **>%35-%40**). Enflasyonun altında ROE üreten şirketler reel olarak erir.
        
        * **Net Kâr Marjı (%):**
          * *Anlamı:* Şirketin kasasına giren her 100 TL cironun kaç TL'sinin net kâr olarak kaldığıdır.
          * *İdeal Değer:* Yüksek ve istikrarlı olması fiyatlama gücünü gösterir.
        
        * **Borç / Özkaynak Oranı (%):**
          * *Anlamı:* Şirketin toplam borç yükünün özkaynaklarına oranıdır.
          * *İdeal Değer:* **%50 - %150** bandı güvenlidir. %200'ün üzeri yüksek faiz dönemlerinde faiz gideri baskısı yaratır.
        
        * **Likit Oran (Quick Ratio / Asit-Test):**
          * *Anlamı:* Şirketin stoklarını satmaya gerek kalmadan, sadece nakit ve alacaklarıyla kısa vadeli borçlarını ödeyebilme gücüdür.
          * *İdeal Değer:* **$\ge 1.0$** olması şirketin nakit sıkıntısı çekmediğini gösterir.
        """)

        st.markdown("### 4. Teknik Momentum Göstergeleri")
        st.markdown("""
        * **RSI (14 - Göreceli Güç Endeksi):**
          * *30'un Altı (Aşırı Satım):* Aşırı satış baskısı yemiş, tepki alımı gelebilir.
          * *50 - 65 Arası:* Sağlıklı yükseliş trendi.
          * *70'in Üstü (Aşırı Alım):* Aşırı şişmiş, düzeltme/kâr satışı riski yüksek.
        
        * **SMA 20 ve SMA 50:** Fiyat ortalamaların üzerindeyse trend yukarı yönlüdür.
        """)

# ==========================================
# 2. MOD: TOPLU ÖZET VE KARŞILAŞTIRMA SAYFASI
# ==========================================
elif page_mode == "📑 Tüm Hisselerin Özeti (Karşılaştırma)":
    st.subheader("📑 Takip Listesindeki Şirketlerin Temel Analiz Özeti")
    st.caption("Tüm hisselerin F/K, PD/DD, Kârlılık, Temettü ve Zirve İskonto oranları tek tabloda:")

    summary_rows = []
    with st.spinner("Şirket verileri toplanıyor..."):
        for name, ticker in STOCKS_ONLY.items():
            info = get_fundamental_data(ticker)
            if info:
                p_cur = info.get("currentPrice", info.get("regularMarketPrice", None))
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
                    "Son Fiyat (TL)": f"{p_cur:.2f}" if p_cur else "-",
                    "F/K": f"{pe:.2f}" if pe else "-",
                    "PD/DD": f"{pb:.2f}" if pb else "-",
                    "Özsermaye Kârı (ROE)": f"%{roe*100:.1f}" if roe else "-",
                    "Net Kâr Marjı": f"%{margin*100:.1f}" if margin else "-",
                    "Temettü Verimi": f"%{div_yield*100:.2f}" if div_yield else "%0.00",
                    "Zirveye Uzaklık": f"%{zirve_fark:.1f}" if zirve_fark else "-"
                })

    if summary_rows:
        df_summary = pd.DataFrame(summary_rows)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
    else:
        st.error("Şirket bilgileri şu anda yüklenemedi.")

# ==========================================
# 3. MOD: TEKİL VARLIK DETAY SAYFASI
# ==========================================
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
    st.sidebar.metric(
        label=f"Seçilen Dönem Enflasyonu ({period} - {ay_sayisi} Aylık)",
        value=f"%{donem_enf:.2f}"
    )

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

    # --- B. DİĞER TÜM VARLIKLAR (HİSSE, ALTIN, BIST 100, DÖVİZ) ---
    else:
        if selected_item["type"] == "gram_altin":
            symbol = "GRAM_ALTIN"
        elif selected_item["ticker"] == "CUSTOM":
            symbol = st.sidebar.text_input("Sembol Kodu:", value="TUPRS.IS").strip().upper()
        else:
            symbol = selected_item["ticker"]

        tab1, tab2 = st.tabs(["📊 Fiyat & Grafik Analizi", "📑 Temel Analiz & Şirket Karnesi"])

        # SEKME 1: GRAFİK VE TEKNİK
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
                st.error(f"Seçilen varlık için canlı veri çekilemedi.")
            else:
                data['SMA20'] = SMAIndicator(close=data['Close'], window=min(20, len(data))).sma_indicator()
                data['SMA50'] = SMAIndicator(close=data['Close'], window=min(50, len(data))).sma_indicator()
                data['RSI'] = RSIIndicator(close=data['Close'], window=min(14, len(data))).rsi()

                start_price = float(data['Close'].iloc[0])
                last_close = float(data['Close'].iloc[-1])
                prev_close = float(data['Close'].iloc[-2])
                daily_change = ((last_close - prev_close) / prev_close) * 100
                period_return = ((last_close - start_price) / start_price) * 100
                last_rsi = float(data['RSI'].iloc[-1]) if pd.notnull(data['RSI'].iloc[-1]) else 50.0
                reel_getiri = ((1 + (period_return / 100)) / (1 + (donem_enf / 100)) - 1) * 100

                st.subheader(f"📈 {selected_label}")

                c1, c2, c3, c4, c5 = st.columns(5)
                birim = "Puan" if selected_item["type"] == "index" else ("TL" if "TL" in selected_label or ".IS" in symbol or selected_item["type"] == "gram_altin" else "$")
                c1.metric("Son Değer", f"{last_close:.2f} {birim}", f"{daily_change:+.2f}% Günlük")
                c2.metric(f"Nominal Getiri ({period})", f"%{period_return:+.2f}")
                c3.metric(f"{ay_sayisi} Aylık Enflasyon", f"%{donem_enf:.2f}")
                c4.metric(
                    label=f"Reel Getiri ({period})",
                    value=f"%{reel_getiri:+.2f}",
                    delta=f"{reel_getiri:+.2f}% Reel Kazanç/Kayıp"
                )
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

        # SEKME 2: SEÇİLİ HİSSEYE ÖZEL DETAYLI BİLANÇO KARNESİ
        with tab2:
            if selected_item["type"] == "stock" or (selected_item["type"] == "custom" and ".IS" in symbol):
                st.subheader(f"📑 {selected_label} - Finansal Sağlık & Değerleme Karnesi")
                with st.spinner("Bilanço ve değerleme verileri alınıyor..."):
                    info = get_fundamental_data(symbol)

                if info:
                    # 1. Satır: Değerleme Çarpanları
                    st.markdown("##### 1. Değerleme ve Çarpanlar")
                    k1, k2, k3, k4 = st.columns(4)
                    pe = info.get("trailingPE", None)
                    fwd_pe = info.get("forwardPE", None)
                    pb = info.get("priceToBook", None)
                    div_yield = info.get("dividendYield", None)

                    k1.metric("F/K (Fiyat/Kazanç)", f"{pe:.2f}" if pe else "N/A", help="İdeal aralık: 5-12. Düşük olması kâra göre ucuzluğu gösterir.")
                    k2.metric("İleri Dönem F/K", f"{fwd_pe:.2f}" if fwd_pe else "N/A", help="Gelecek 1 yıl tahmini kârına göre F/K.")
                    k3.metric("PD/DD (Piyasa/Defter)", f"{pb:.2f}" if pb else "N/A", help="Şirketin net varlıklarına göre çarpanı. 1-3 arası makul.")
                    k4.metric("Temettü Verimi", f"%{div_yield * 100:.2f}" if div_yield else "%0.00", help="Yıllık nakit kâr payı dağıtım oranı.")

                    st.markdown("---")

                    # 2. Satır: Kârlılık ve Borçluluk
                    st.markdown("##### 2. Kârlılık ve Borçluluk Durumu")
                    b1, b2, b3, b4 = st.columns(4)
                    roe = info.get("returnOnEquity", None)
                    profit_margin = info.get("profitMargins", None)
                    debt_to_equity = info.get("debtToEquity", None)
                    quick_ratio = info.get("quickRatio", None)

                    b1.metric("Özsermaye Kârı (ROE)", f"%{roe * 100:.2f}" if roe else "N/A", help="Sermayenin yıllık büyüme gücü. Enflasyonun (%31.75) üstünde olmalı.")
                    b2.metric("Net Kâr Marjı", f"%{profit_margin * 100:.2f}" if profit_margin else "N/A", help="Cironun kâra dönüşme oranı.")
                    b3.metric("Borç / Özkaynak", f"%{debt_to_equity:.1f}" if debt_to_equity else "N/A", help="%50-%150 bandı güvenlidir.")
                    b4.metric("Likit Oran (Quick Ratio)", f"{quick_ratio:.2f}" if quick_ratio else "N/A", help="1.0 ve üzeri nakit gücünün iyi olduğunu gösterir.")

                    st.markdown("---")

                    # 3. Satır: Piyasa Büyüklüğü ve Zirve İskonto
                    st.markdown("##### 3. Piyasa Büyüklüğü ve Fiyat İskontosu")
                    p1, p2, p3, p4 = st.columns(4)
                    market_cap = info.get("marketCap", 0)
                    market_cap_bil = market_cap / 1_000_000_000 if market_cap else 0
                    high_52 = info.get("fiftyTwoWeekHigh", 0)
                    low_52 = info.get("fiftyTwoWeekLow", 0)
                    current_p = info.get("currentPrice", last_close if 'last_close' in locals() else 0)
                    zirve_uzaklik = ((current_p - high_52) / high_52) * 100 if high_52 else 0

                    p1.metric("Piyasa Değeri", f"{market_cap_bil:.2f} Milyar TL")
                    p2.metric("52 Hafta Zirve", f"{high_52:.2f} TL")
                    p3.metric("52 Hafta Dip", f"{low_52:.2f} TL")
                    p4.metric("Zirveye Uzaklık (İskonto)", f"%{zirve_uzaklik:.2f}", help="Tarihi zirve seviyesinden şu anki geri çekilme oranı.")
                else:
                    st.warning("Temel veriler yüklenemedi.")
            else:
                st.info("Temel analiz karnesi sadece BIST hisse senetleri için geçerlidir.")
