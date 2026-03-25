import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Sıcaklık Analiz Programı", layout="wide")
st.title("📈 Termokupl Veri Analizi ve Raporlama")

st.markdown("""
Bu program, Graphtec cihazınızdan aldığınız termokupl ölçüm verilerini (CSV) okur, 
'BURN OUT' (boşta/bağlı olmayan) kanalları temizler ve size interaktif bir analiz sunar.
""")

# Dosya Yükleme Alanı
uploaded_file = st.file_uploader("Lütfen Ölçüm CSV Dosyanızı Yükleyin", type=["csv", "CSV"])

if uploaded_file is not None:
    with st.spinner('Veriler işleniyor...'):
        # Veriyi yükle (ilk 24 satırdaki cihaz bilgilerini atla)
        df = pd.read_csv(uploaded_file, skiprows=24)
        
        # 1. satırdaki birim ("degC", "V" vb.) bilgisini sil
        df = df.drop(0).reset_index(drop=True)
        
        # 'BURN OUT' yazan geçersiz verileri NaN (Boş değer) yap
        df = df.replace('BURN OUT', np.nan)
        
        # "CH" ile başlayan sıcaklık/voltaj kanallarını tespit et
        temp_columns = [col for col in df.columns if col.startswith('CH')]
        
        # Sütunları sayısal formata çevir
        for col in temp_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # Tarih ve saat sütununu datetime objesine çevir
        df['Date&Time'] = pd.to_datetime(df['Date&Time'])
        
        st.success("Veri başarıyla yüklendi ve temizlendi!")

        # Genel Bilgiler
        st.subheader("📋 Veri Önizleme")
        st.dataframe(df.head(), use_container_width=True)
        
        # Sadece içerisinde geçerli veri olan (hepsi NaN olmayan) kanalları bul
        valid_cols = [col for col in temp_columns if df[col].notna().any()]
        
        st.divider()

        # İnteraktif Grafik Bölümü
        st.subheader("📊 İnteraktif Sıcaklık Grafiği")
        st.write("Aşağıdan görmek istediğiniz kanalları seçebilirsiniz. Grafiğin üzerine gelerek değerleri detaylı görebilir, alanı seçerek yakınlaştırabilirsiniz.")
        
        selected_cols = st.multiselect(
            "Görüntülenecek Kanalları Seçin:", 
            options=valid_cols, 
            default=valid_cols
        )
        
        if selected_cols:
            # Plotly ile interaktif grafik çizimi
            fig = px.line(
                df, 
                x='Date&Time', 
                y=selected_cols, 
                title="Zaman İçerisinde Sıcaklık Değişimi", 
                labels={"value": "Değer (°C / Volt)", "variable": "Kanal", "Date&Time": "Zaman"}
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()

            # İstatistiksel Özet (Raporlama) Bölümü
            st.subheader("📉 Detaylı İstatistiksel Rapor")
            st.write("Seçilen kanallara ait Maksimum, Minimum ve Ortalama değerler:")
            
            # Seçili kanalların istatistiğini al ve daha temiz göster
            stats_df = df[selected_cols].describe().T
            stats_df = stats_df[['count', 'mean', 'std', 'min', 'max']]
            stats_df.columns = ['Veri Sayısı', 'Ortalama', 'Standart Sapma', 'Minimum', 'Maksimum']
            st.dataframe(stats_df.style.format("{:.2f}"), use_container_width=True)

            # Veriyi filtreleyip indirme butonu
            st.download_button(
                label="Temizlenmiş Veriyi CSV Olarak İndir",
                data=df[['Date&Time'] + selected_cols].to_csv(index=False).encode('utf-8'),
                file_name='temizlenmis_sicaklik_verisi.csv',
                mime='text/csv',
            )
        else:
            st.warning("Lütfen grafik çizimi için en az bir kanal seçin.")