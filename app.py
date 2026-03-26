import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Termal Kısma ve Denge Analizi", layout="wide")
st.title("📈 Gelişmiş Termal Kısma (Throttling) ve Steady-State Analizi")

st.markdown("""
Bu araç, ortam sıcaklığındaki değişimlere karşı cihazınızın akım/güç kısıp kısmadığını **ΔT (Cihaz - Ortam)** prensibiyle analiz eder.
Zaman ekseni **Dakika** bazlıdır ve testteki farklı ortam sıcaklıklarındaki denge (steady-state) durumları otomatik raporlanır.
""")

# Dosya Yükleme
uploaded_file = st.file_uploader("Ölçüm CSV Dosyanızı Yükleyin", type=["csv", "CSV"])

if uploaded_file is not None:
    with st.spinner('Veriler işleniyor...'):
        df = pd.read_csv(uploaded_file, skiprows=24)
        df = df.drop(0).reset_index(drop=True)
        df = df.replace('BURN OUT', np.nan)
        
        temp_columns = [col for col in df.columns if col.startswith('CH')]
        for col in temp_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        valid_cols = [col for col in temp_columns if df[col].notna().any()]
        
        st.divider()

        # --- 1. AYARLAR VE İSİMLENDİRME ---
        st.header("⚙️ 1. Veri Ayarları ve İsimlendirme")
        
        col_ayar1, col_ayar2 = st.columns(2)
        with col_ayar1:
            sampling_rate = st.number_input("Örnekleme Aralığı (Saniye)", min_value=0.1, value=1.0, step=0.1)
        
        # Zaman eksenini DAKİKA olarak oluştur
        df['Zaman (dk)'] = (df.index * sampling_rate) / 60.0

        st.subheader("Kanalları İsimlendirin")
        renames = {}
        cols = st.columns(4)
        for i, col in enumerate(valid_cols):
            with cols[i % 4]:
                new_name = st.text_input(f"'{col}' için yeni isim:", value=col, key=col)
                renames[col] = new_name
                
        df = df.rename(columns=renames)
        valid_cols_renamed = list(renames.values())

        st.divider()

        # --- 2. GENEL GRAFİK BÖLÜMÜ ---
        st.header("📊 2. Genel Sıcaklık Grafiği (Dakika Bazlı)")
        selected_cols = st.multiselect("Grafikte Gösterilecek Kanalları Seçin:", options=valid_cols_renamed, default=valid_cols_renamed)
        
        if selected_cols:
            fig = px.line(df, x='Zaman (dk)', y=selected_cols, title="Zaman İçerisinde Sıcaklık Değişimi")
            fig.update_layout(xaxis_title="Zaman (Dakika)", yaxis_title="Sıcaklık (°C)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()

            # --- 3. AKIM KISMA VE STEADY-STATE ANALİZİ ---
            st.header("⚡ 3. Akım Kısma (Thermal Throttling) Analizi")
            st.markdown("""
            **Nasıl Çalışır?** Sistem, referans kabul edilen maksimum ΔT değerini 100% güç (nominal akım) olarak kabul eder. 
            Ortam sıcaklığı arttığında cihaz sıcaklığı aynı oranda artmıyorsa (ΔT daralıyorsa), bu daralma oranı kadar akım kısıldığı hesaplanır.
            """)
            
            col_analiz1, col_analiz2, col_analiz3 = st.columns(3)
            with col_analiz1:
                ambient_col = st.selectbox("Ortam Sıcaklığı Kanalı:", options=selected_cols)
            with col_analiz2:
                target_col = st.selectbox("Cihaz/Test Kanalı:", options=[c for c in selected_cols if c != ambient_col])
            with col_analiz3:
                nominal_current = st.number_input("Giriş Akımı / Nominal Akım (mA)", value=1000.0, step=100.0)

            if target_col and ambient_col:
                # Delta T Hesaplama
                df['Delta T'] = df[target_col] - df[ambient_col]
                
                # Cihazın nominal akımda çalıştığı kabul edilen en yüksek Delta T değeri
                max_delta_t = df['Delta T'].max()
                ref_delta_t = st.number_input("Referans ΔT (°C) (Akımın %100 kabul edildiği sıcaklık farkı)", value=float(max_delta_t))
                
                # Akım ve Kısma (%) Hesaplamaları
                df['Tahmini Akım (mA)'] = nominal_current * (df['Delta T'] / ref_delta_t)
                df['Tahmini Akım (mA)'] = df['Tahmini Akım (mA)'].clip(upper=nominal_current, lower=0) # Akım nominali geçemez
                df['Akım Kısma Oranı (%)'] = 100 * (1 - (df['Tahmini Akım (mA)'] / nominal_current))
                df['Akım Kısma Oranı (%)'] = df['Akım Kısma Oranı (%)'].clip(lower=0)

                # Kapsamlı Grafik (Çift Eksen)
                fig_throttle = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Sıcaklıklar
                fig_throttle.add_trace(go.Scatter(x=df['Zaman (dk)'], y=df[target_col], name=f"{target_col} (°C)", line=dict(color='red')), secondary_y=False)
                fig_throttle.add_trace(go.Scatter(x=df['Zaman (dk)'], y=df[ambient_col], name=f"{ambient_col} (°C)", line=dict(color='blue', dash='dot')), secondary_y=False)
                
                # Akım (mA)
                fig_throttle.add_trace(go.Scatter(x=df['Zaman (dk)'], y=df['Tahmini Akım (mA)'], name="Anlık Akım (mA)", line=dict(color='green', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.1)'), secondary_y=True)

                fig_throttle.update_layout(title_text="Sıcaklık ve Çekilen Akım Korelasyonu", hovermode="x unified")
                fig_throttle.update_yaxes(title_text="Sıcaklık (°C)", secondary_y=False)
                fig_throttle.update_yaxes(title_text="Çekilen Akım (mA)", secondary_y=True, range=[0, nominal_current*1.1])
                fig_throttle.update_xaxes(title_text="Zaman (Dakika)")
                
                st.plotly_chart(fig_throttle, use_container_width=True)

                st.divider()

                # --- 4. FARKLI ORTAM SICAKLIKLARI İÇİN STEADY STATE ÖZETİ ---
                st.header("🌡️ Farklı Ortam Sıcaklıklarında Performans (Steady-State Özeti)")
                st.write("Aşağıdaki tablo, sıcaklık artış hızının durduğu (sistemin dengeye ulaştığı) kısımları farklı ortam sıcaklıklarına göre gruplayıp filtreler.")

                # Değişim Hızı (Türev) - Denge durumunu bulmak için
                # 1 dakikalık pencerede sıcaklık değişim hızını hesapla
                window_size = int(60 / sampling_rate) if sampling_rate < 60 else 2
                df['dT/dt'] = df[target_col].diff(periods=window_size).abs()
                
                # Steady-state kabul şartı: 1 dakikadaki değişim 0.5 dereceden az ise
                steady_state_df = df[df['dT/dt'] < 0.5].copy()
                
                # Ortam sıcaklığını en yakın tam sayıya yuvarlayarak bölgeleri (zonları) grupla
                steady_state_df['Ortam Zonu (°C)'] = steady_state_df[ambient_col].round()
                
                if not steady_state_df.empty:
                    summary = steady_state_df.groupby('Ortam Zonu (°C)').agg(
                        Denge_Sicakligi=(target_col, 'mean'),
                        Ortalama_Delta_T=('Delta T', 'mean'),
                        Tahmini_Akim=('Tahmini Akım (mA)', 'mean'),
                        Kisma_Yuzdesi=('Akım Kısma Oranı (%)', 'mean'),
                        Veri_Noktasi_Sayisi=('Zaman (dk)', 'count')
                    ).reset_index()
                    
                    # Veri sayısı çok az olan anlık takılmaları (gürültüleri) filtrele
                    summary = summary[summary['Veri_Noktasi_Sayisi'] > (window_size * 2)]
                    
                    # Tabloyu formatla
                    summary = summary.rename(columns={
                        'Denge_Sicakligi': f"{target_col} Denge Sıcaklığı (°C)",
                        'Ortalama_Delta_T': "ΔT (Cihaz - Ortam)",
                        'Tahmini_Akim': "Çekilen Akım (mA)",
                        'Kisma_Yuzdesi': "Güç Kısma (%)"
                    })
                    
                    st.dataframe(summary.style.format({
                        f"{target_col} Denge Sıcaklığı (°C)": "{:.1f}",
                        "ΔT (Cihaz - Ortam)": "{:.1f}",
                        "Çekilen Akım (mA)": "{:.0f}",
                        "Güç Kısma (%)": "{:.1f}%",
                        "Veri_Noktasi_Sayisi": "{:.0f}"
                    }), use_container_width=True)
                else:
                    st.warning("Verilerde belirgin bir 'Steady-State' (Denge) noktası tespit edilemedi. Sıcaklık sürekli değişim halinde olabilir.")