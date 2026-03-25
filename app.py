import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gelişmiş Sıcaklık Analiz Programı", layout="wide")
st.title("📈 Gelişmiş Termokupl ve Termal Kısma Analizi")

st.markdown("""
Bu araç ile verilerinizi saniye bazlı inceleyebilir, kanalları isimlendirebilir ve 
**Ortam sıcaklığına bağlı akım/güç kısma (thermal throttling)** durumlarını değişim hızı (türev) ile tespit edebilirsiniz.
""")

# Dosya Yükleme
uploaded_file = st.file_uploader("Ölçüm CSV Dosyanızı Yükleyin", type=["csv", "CSV"])

if uploaded_file is not None:
    with st.spinner('Veriler işleniyor...'):
        # Veriyi yükle ve temizle
        df = pd.read_csv(uploaded_file, skiprows=24)
        df = df.drop(0).reset_index(drop=True)
        df = df.replace('BURN OUT', np.nan)
        
        # Kanalları bul
        temp_columns = [col for col in df.columns if col.startswith('CH')]
        for col in temp_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # Sadece geçerli kanalları al
        valid_cols = [col for col in temp_columns if df[col].notna().any()]
        
        st.success("Veri başarıyla yüklendi!")
        
        st.divider()

        # --- 1. AYARLAR VE İSİMLENDİRME BÖLÜMÜ ---
        st.header("⚙️ 1. Veri Ayarları ve İsimlendirme")
        
        col_ayar1, col_ayar2 = st.columns(2)
        with col_ayar1:
            # Örnekleme Hızı Ayarı
            sampling_rate = st.number_input(
                "Örnekleme Aralığı (Saniye)", 
                min_value=0.1, value=1.0, step=0.1,
                help="Her bir ölçüm satırı arasındaki saniye farkı"
            )
        
        # Zaman eksenini saniye olarak oluştur (0, 1, 2, 3... * sampling_rate)
        df['Zaman (s)'] = df.index * sampling_rate

        # Kanal İsimlendirme
        st.subheader("Kanalları İsimlendirin")
        renames = {}
        cols = st.columns(4)
        for i, col in enumerate(valid_cols):
            with cols[i % 4]:
                new_name = st.text_input(f"'{col}' için yeni isim:", value=col)
                renames[col] = new_name
                
        # Sütun isimlerini güncelle
        df = df.rename(columns=renames)
        valid_cols_renamed = list(renames.values())

        st.divider()

        # --- 2. GENEL GRAFİK BÖLÜMÜ ---
        st.header("📊 2. Genel Sıcaklık Grafiği")
        selected_cols = st.multiselect(
            "Grafikte Gösterilecek Kanalları Seçin:", 
            options=valid_cols_renamed, 
            default=valid_cols_renamed
        )
        
        if selected_cols:
            fig = px.line(
                df, 
                x='Zaman (s)', 
                y=selected_cols, 
                title="Saniye Bazlı Sıcaklık Değişimi", 
            )
            # Eksen isimlendirmeleri
            fig.update_layout(
                xaxis_title="Zaman (Saniye)",
                yaxis_title="Sıcaklık (°C)",
                hovermode="x unified",
                legend_title_text="Kanallar"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()

            # --- 3. AKIM KISMA (THROTTLING) VE ARTIS ANALİZİ ---
            st.header("🔍 3. Akım Kısma ve Sıcaklık Artış Analizi")
            st.markdown("""
            Bu bölüm, ortam sıcaklığının artmasıyla fırının/cihazın gücünü kestiği anları tespit etmek içindir. 
            **Sıcaklık Artış Hızı (°C/s)** eğrisi sıfıra veya eksiye doğru keskin bir düşüş yapıyorsa, sistem akım kısmış demektir.
            """)
            
            col_analiz1, col_analiz2, col_analiz3 = st.columns(3)
            with col_analiz1:
                ambient_col = st.selectbox("Ortam Sıcaklığı Kanalı:", options=selected_cols)
            with col_analiz2:
                target_col = st.selectbox("Hedef (Cihaz/İç) Kanalı:", options=[c for c in selected_cols if c != ambient_col] + [ambient_col])
            with col_analiz3:
                window_size = st.slider("Hassasiyet (Yumuşatma Penceresi)", min_value=1, max_value=60, value=10, help="Değişim hızındaki anlık gürültüleri filtrelemek için veri noktası sayısı.")

            if target_col and ambient_col:
                # Sıcaklık değişim hızını (Türev - dT/dt) hesapla
                # .diff() ile farkı alıp, geçen süreye bölüyoruz. Gürültüyü azaltmak için rolling mean yapıyoruz.
                df['Artış Hızı (°C/s)'] = df[target_col].diff() / sampling_rate
                df['Artış Hızı (°C/s)'] = df['Artış Hızı (°C/s)'].rolling(window=window_size).mean()

                # Çift Y eksenli grafik oluştur (Sol: Sıcaklık, Sağ: Artış Hızı)
                fig_analiz = make_subplots(specs=[[{"secondary_y": True}]])

                # Sıcaklıkları ekle (Sol eksen)
                fig_analiz.add_trace(go.Scatter(x=df['Zaman (s)'], y=df[target_col], name=f"{target_col} Sıcaklığı", line=dict(color='red')), secondary_y=False)
                fig_analiz.add_trace(go.Scatter(x=df['Zaman (s)'], y=df[ambient_col], name=f"{ambient_col} Sıcaklığı", line=dict(color='blue', dash='dash')), secondary_y=False)
                
                # Artış Hızını ekle (Sağ eksen)
                fig_analiz.add_trace(go.Scatter(x=df['Zaman (s)'], y=df['Artış Hızı (°C/s)'], name=f"{target_col} Artış Hızı (Güç Göstergesi)", line=dict(color='green', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.1)'), secondary_y=True)

                fig_analiz.update_layout(
                    title_text=f"{target_col} Isınma Karakteristiği ve Güç Kısma Tespiti",
                    hovermode="x unified"
                )
                fig_analiz.update_yaxes(title_text="Sıcaklık (°C)", secondary_y=False)
                fig_analiz.update_yaxes(title_text="Artış Hızı (°C / Saniye)", secondary_y=True, showgrid=False)
                fig_analiz.update_xaxes(title_text="Zaman (Saniye)")

                st.plotly_chart(fig_analiz, use_container_width=True)

                # Detaylı Değerlendirme Çıktıları
                st.subheader("📋 Artış Değerlendirme Raporu")
                max_temp = df[target_col].max()
                max_rate = df['Artış Hızı (°C/s)'].max()
                total_delta = max_temp - df[target_col].iloc[0]
                
                col_rap1, col_rap2, col_rap3 = st.columns(3)
                col_rap1.metric(label=f"Maksimum {target_col} Sıcaklığı", value=f"{max_temp:.1f} °C")
                col_rap2.metric(label="Toplam Sıcaklık Artışı (ΔT)", value=f"{total_delta:.1f} °C")
                col_rap3.metric(label="En Yüksek Isınma Hızı", value=f"{max_rate:.3f} °C/s")