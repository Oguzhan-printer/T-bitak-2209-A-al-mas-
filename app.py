import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import ttest_ind, chi2_contingency
import statsmodels.api as sm
from statsmodels.formula.api import ols
from fpdf import FPDF
import plotly.express as px 
import plotly.io as pio 
import warnings
import io 

warnings.filterwarnings('ignore')

# --- 2. SİSTEMİN GEREKLİ SÜTUNLARI (ŞABLON İÇİN) ---
NUMERIC_COLUMNS = [
    'yas', 'gebelik_haftasi', 
    'korku_vas_baseline', 'korku_olcek_baseline',
    'korku_vas_4cm', 'korku_olcek_4cm',
    'korku_vas_8cm', 'korku_olcek_8cm',
    'endise_oxford_baseline', 'endise_oxford_son_test'
]
CATEGORIC_COLUMNS = [
    'grup', 'egitim_durumu', 'dogum_baslangici', 'medeni_durum', 
    'gelir_duzeyi', 'calisma_durumu', 'planli_gebelik_mi'
]
ALL_REQUIRED_COLUMNS = NUMERIC_COLUMNS + CATEGORIC_COLUMNS

# --- 3. YENİ ŞABLON OLUŞTURMA FONKSİYONU ---
@st.cache_data 
def create_template_excel():
    df_template = pd.DataFrame(columns=ALL_REQUIRED_COLUMNS)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_template.to_excel(writer, sheet_name='Veri_Giris_Sayfasi', index=False)
    return output.getvalue()

# --- 4. YARDIMCI PDF FONKSİYONLARI ---
def normalize_for_pdf(text):
    text = str(text) 
    replacements = {
        'İ': 'I', 'ı': 'i', 'Ş': 'S', 'ş': 's', 'Ğ': 'G', 'ğ': 'g',
        'Ü': 'U', 'ü': 'u', 'Ö': 'O', 'ö': 'o', 'Ç': 'C', 'ç': 'c'
    }
    for tr_char, en_char in replacements.items():
        text = text.replace(tr_char, en_char)
    return text

def create_pdf_report(results, charts):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Ebelik Arastirmasi Istatistiksel Analiz Raporu", ln=True, align="C")
    pdf.ln(5) 
    
    # --- FAZ 1 Raporu ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "FAZ 1: Baslangic Denkligi Raporu", ln=True)
    pdf.set_font("Arial", "", 10)
    
    if results['faz1_is_denk']:
        pdf.set_text_color(0, 100, 0); pdf.multi_cell(190, 5, normalize_for_pdf("SONUC: Randomizasyon BASARILI (Tum p > 0.05)"))
        pdf.set_text_color(0, 0, 0); pdf.multi_cell(190, 5, normalize_for_pdf(
            "Yorum: Gruplar arasi anlamli bir baslangic farki bulunamamistir. "
            "Bu, gruplarin homojen (denk) oldugunu ve arastirmanin ic gecerliliginin "
            "yuksek oldugunu gosterir."
        ))
    else:
        pdf.set_text_color(255, 165, 0); pdf.multi_cell(190, 5, normalize_for_pdf("SONUC: Randomizasyon BASARISIZ (p < 0.05)"))
        pdf.set_text_color(0, 0, 0); failed_vars_str = ", ".join(results['faz1_failed_vars_display_names'])
        pdf.multi_cell(190, 5, normalize_for_pdf(
            f"Neden Kaynakli?: Analiz, '{failed_vars_str}' degisken(ler)i acisindan anlamli bir fark tespit etmistir."
        ))
    pdf.ln(5)
    
    # --- FAZ 2 Raporu ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "FAZ 2: Hipotez Testleri Raporu (ANCOVA)", ln=True)
    
    if results['correction_applied']:
        pdf.set_font("Arial", "B", 10); pdf.set_text_color(200, 0, 0)
        pdf.multi_cell(190, 5, normalize_for_pdf(
            f"DIKKAT: ISTATISTIKSEL DUZELTME UYGULANDI.\nFAZ 1'deki denklik hatasi nedeniyle su degisken(ler) analize 'kovaryant' "
            f"olarak eklenmistir: {results['correction_applied']}"
        ))
        pdf.set_text_color(0, 0, 0); pdf.ln(2)

    # FAZ 2 Sonuçları
    pdf.set_font("Arial", "B", 12); pdf.cell(190, 8, "[H1: Latent Faz Korku]", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, normalize_for_pdf(f"- VAS Sonucu: {'DESTEKLENDI' if results['h1_vas_p'] < 0.05 else 'Reddedildi'} (p-degeri: {results['h1_vas_p']:.6f})"), ln=True)
    pdf.cell(190, 5, normalize_for_pdf(f"- Dogum Korku Olcegi Sonucu: {'DESTEKLENDI' if results['h1_olcek_p'] < 0.05 else 'Reddedildi'} (p-degeri: {results['h1_olcek_p']:.6f})"), ln=True)
    
    pdf.set_font("Arial", "B", 12); pdf.cell(190, 8, "[H2: Aktif Faz Korku]", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, normalize_for_pdf(f"- VAS Sonucu: {'DESTEKLENDI' if results['h2_vas_p'] < 0.05 else 'Reddedildi'} (p-degeri: {results['h2_vas_p']:.6f})"), ln=True)
    pdf.cell(190, 5, normalize_for_pdf(f"- Dogum Korku Olcegi Sonucu: {'DESTEKLENDI' if results['h2_olcek_p'] < 0.05 else 'Reddedildi'} (p-degeri: {results['h2_olcek_p']:.6f})"), ln=True)
    
    pdf.set_font("Arial", "B", 12); pdf.cell(190, 8, "[H3: Endise Duzeyi]", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, normalize_for_pdf(f"- Oxford Endise Olcegi Sonucu: {'DESTEKLENDI' if results['h3_oxford_p'] < 0.05 else 'Reddedildi'} (p-degeri: {results['h3_oxford_p']:.6f})"), ln=True)
    pdf.ln(5)
    
    # --- Nihai Yorum ---
    pdf.set_font("Arial", "B", 14); pdf.cell(190, 10, "Nihai Rapor Yorumu (Analist Ozeti)", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(190, 5, normalize_for_pdf(results['final_report_text']))
    
    # --- Sayfa 3: Sosyodemografik Grafikler (EK A) ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "EK A: Sosyodemografik Dagilimlar (Dashboard Grafikleri)", ln=True)
    try:
        img_medeni = pio.to_image(charts['fig_pie_medeni'], format="png"); img_gelir = pio.to_image(charts['fig_pie_gelir'], format="png")
        img_calisma = pio.to_image(charts['fig_pie_calisma'], format="png"); img_plan = pio.to_image(charts['fig_pie_plan'], format="png")
        pdf.image(io.BytesIO(img_medeni), w=90, h=65, x=10); pdf.image(io.BytesIO(img_gelir), w=90, h=65, x=110)
        pdf.ln(70); pdf.image(io.BytesIO(img_calisma), w=90, h=65, x=10); pdf.image(io.BytesIO(img_plan), w=90, h=65, x=110)
    except Exception as e:
        pdf.set_text_color(255, 0, 0); pdf.cell(190, 10, normalize_for_pdf(f"Pasta grafikleri olusturulamadi: {e}"), ln=True); pdf.set_text_color(0, 0, 0)
        
    # --- Sayfa 4: Denklik Grafikleri (EK B) ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "EK B: Gorsel Denklik Kontrolu Grafikleri", ln=True)
    try:
        img_yas_box = pio.to_image(charts['fig_yas_box'], format="png"); img_hafta_box = pio.to_image(charts['fig_hafta_box'], format="png")
        img_egitim_bar = pio.to_image(charts['fig_egitim_bar'], format="png"); img_dogum_bar = pio.to_image(charts['fig_dogum_bar'], format="png")
        pdf.image(io.BytesIO(img_yas_box), w=90, h=70, x=10); pdf.image(io.BytesIO(img_hafta_box), w=90, h=70, x=110)
        pdf.ln(75); pdf.image(io.BytesIO(img_egitim_bar), w=90, h=70, x=10); pdf.image(io.BytesIO(img_dogum_bar), w=90, h=70, x=110)
    except Exception as e:
        pdf.set_text_color(255, 0, 0); pdf.cell(190, 10, normalize_for_pdf(f"Denklik grafikleri olusturulamadi: {e}"), ln=True); pdf.set_text_color(0, 0, 0)

    # --- Sayfa 5: Puan Evrimi ve Korelasyon Grafikleri (EK C) ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "EK C: Puan Evrimi ve Korelasyon Grafikleri", ln=True)
    try:
        img_vas_line = pio.to_image(charts['fig_vas_line'], format="png")
        img_stacked = pio.to_image(charts['fig_stacked'], format="png")
        img_heatmap = pio.to_image(charts['fig_heatmap'], format="png")
        pdf.image(io.BytesIO(img_vas_line), w=190, h=80); pdf.ln(85)
        pdf.image(io.BytesIO(img_stacked), w=190, h=90); pdf.ln(95)
        pdf.image(io.BytesIO(img_heatmap), w=190, h=100)
    except Exception as e:
        pdf.set_text_color(255, 0, 0); pdf.cell(190, 10, normalize_for_pdf(f"Puan evrimi/korelasyon grafikleri olusturulamadi: {e}"), ln=True); pdf.set_text_color(0, 0, 0)
        
    return bytes(pdf.output(dest='S'))

# --- 5. BACKEND: NİHAİ İSTATİSTİK MOTORU (HESAPLAMA) ---
def run_full_analysis(df_data):
    results = {} 
    
    missing_cols = [col for col in ALL_REQUIRED_COLUMNS if col not in df_data.columns]
    if missing_cols:
        return {'error': f"HATA: Yüklediğiniz Excel dosyası bir Şablon dosyası değil. Şu sütunlar eksik: {', '.join(missing_cols)}. Lütfen 'Boş Excel Şablonunu İndir' butonunu kullanarak doğru şablonu indirin ve verilerinizi oraya girin."}
    
    df_cleaned = df_data.copy()
    for col in NUMERIC_COLUMNS:
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        
    if df_cleaned[NUMERIC_COLUMNS].isnull().all().all():
        return {'error': "HATA: Analiz edilecek sayısal veri bulunamadı. Yüklediğiniz Excel şablonundaki sayısal sütunlar ('yas', 'korku_vas_baseline' vb.) tamamen boş veya geçersiz metin ('yok', 'N/A' vb.) içeriyor. Lütfen verilerinizi kontrol edin."}

    try:
        grup_mudahale = df_cleaned[df_cleaned['grup'] == 'Müdahale']
        grup_kontrol = df_cleaned[df_cleaned['grup'] == 'Kontrol']
    except KeyError:
        return {'error': "HATA: 'grup' sütunu bulunamadı veya 'Müdahale'/'Kontrol' değerleri yanlış yazılmış. Lütfen şablonu kontrol edin."}
    
    display_to_col_map_denklik = {
        'Yaş': 'yas', 'Gebelik Haftası': 'gebelik_haftasi',
        'Eğitim Durumu': 'egitim_durumu', 'Doğum Başlangıcı (Doğum Şekli)': 'dogum_baslangici',
        'Medeni Durum': 'medeni_durum', 'Gelir Düzeyi': 'gelir_duzeyi',
        'Çalışma Durumu': 'calisma_durumu', 'Planlı Gebelik': 'planli_gebelik_mi'
    }

    # --- FAZ 1 HESAPLAMALARI (Denklik) ---
    p_values_numeric = {
        'Yaş': ttest_ind(grup_mudahale['yas'], grup_kontrol['yas'], equal_var=False, nan_policy='omit')[1],
        'Gebelik Haftası': ttest_ind(grup_mudahale['gebelik_haftasi'], grup_kontrol['gebelik_haftasi'], equal_var=False, nan_policy='omit')[1],
        'Başlangıç Korku (VAS)': ttest_ind(grup_mudahale['korku_vas_baseline'], grup_kontrol['korku_vas_baseline'], equal_var=False, nan_policy='omit')[1],
        'Başlangıç Korku (Ölçek)': ttest_ind(grup_mudahale['korku_olcek_baseline'], grup_kontrol['korku_olcek_baseline'], equal_var=False, nan_policy='omit')[1],
        'Başlangıç Endişe (Oxford)': ttest_ind(grup_mudahale['endise_oxford_baseline'], grup_kontrol['endise_oxford_baseline'], equal_var=False, nan_policy='omit')[1]
    }
    p_values_categoric = {
        'Eğitim Durumu': chi2_contingency(pd.crosstab(df_cleaned['grup'], df_cleaned['egitim_durumu']))[1],
        'Doğum Başlangıcı (Doğum Şekli)': chi2_contingency(pd.crosstab(df_cleaned['grup'], df_cleaned['dogum_baslangici']))[1],
        'Medeni Durum': chi2_contingency(pd.crosstab(df_cleaned['grup'], df_cleaned['medeni_durum']))[1],
        'Gelir Düzeyi': chi2_contingency(pd.crosstab(df_cleaned['grup'], df_cleaned['gelir_duzeyi']))[1],
        'Çalışma Durumu': chi2_contingency(pd.crosstab(df_cleaned['grup'], df_cleaned['calisma_durumu']))[1],
        'Planlı Gebelik': chi2_contingency(pd.crosstab(df_cleaned['grup'], df_cleaned['planli_gebelik_mi']))[1]
    }
    results['faz1_numeric_p_values'] = p_values_numeric
    results['faz1_categoric_p_values'] = p_values_categoric
    
    all_p_values_dict = {**p_values_numeric, **p_values_categoric}
    failed_vars_display_names = [var_name for var_name, p in all_p_values_dict.items() if p < 0.05]
    results['faz1_is_denk'] = len(failed_vars_display_names) == 0
    results['faz1_failed_vars_display_names'] = failed_vars_display_names 
    
    # --- DİNAMİK DÜZELTME MOTORU ---
    correction_formula_part = ""
    if not results['faz1_is_denk']:
        for var_name in failed_vars_display_names:
            col_name = display_to_col_map_denklik.get(var_name)
            if col_name: 
                if col_name in CATEGORIC_COLUMNS:
                    correction_formula_part += f" + C({col_name})"
                else:
                    correction_formula_part += f" + {col_name}"
    results['correction_applied'] = correction_formula_part 
    
    # --- FAZ 2 HESAPLAMALARI (Dinamik Formüllerle) ---
    f_h1_vas_base = 'korku_vas_4cm ~ grup + korku_vas_baseline'
    f_h1_olcek_base = 'korku_olcek_4cm ~ grup + korku_olcek_baseline'
    f_h2_vas_base = 'korku_vas_8cm ~ grup + korku_vas_4cm'
    f_h2_olcek_base = 'korku_olcek_8cm ~ grup + korku_olcek_4cm'
    f_h3_oxford_base = 'endise_oxford_son_test ~ grup + endise_oxford_baseline'
    
    results['h1_vas_p'] = sm.stats.anova_lm(ols(f_h1_vas_base + correction_formula_part, data=df_cleaned.dropna(subset=['korku_vas_4cm', 'grup', 'korku_vas_baseline'])).fit(), typ=3).loc['grup', 'PR(>F)']
    results['h1_olcek_p'] = sm.stats.anova_lm(ols(f_h1_olcek_base + correction_formula_part, data=df_cleaned.dropna(subset=['korku_olcek_4cm', 'grup', 'korku_olcek_baseline'])).fit(), typ=3).loc['grup', 'PR(>F)']
    results['h2_vas_p'] = sm.stats.anova_lm(ols(f_h2_vas_base + correction_formula_part, data=df_cleaned.dropna(subset=['korku_vas_8cm', 'grup', 'korku_vas_4cm'])).fit(), typ=3).loc['grup', 'PR(>F)']
    results['h2_olcek_p'] = sm.stats.anova_lm(ols(f_h2_olcek_base + correction_formula_part, data=df_cleaned.dropna(subset=['korku_olcek_8cm', 'grup', 'korku_olcek_4cm'])).fit(), typ=3).loc['grup', 'PR(>F)']
    results['h3_oxford_p'] = sm.stats.anova_lm(ols(f_h3_oxford_base + correction_formula_part, data=df_cleaned.dropna(subset=['endise_oxford_son_test', 'grup', 'endise_oxford_baseline'])).fit(), typ=3).loc['grup', 'PR(>F)']
    
    # --- Akıllı Yorum v2.0 (Nihai Yorum Metnini Oluştur) ---
    h_p_values = [results['h1_vas_p'], results['h1_olcek_p'], results['h2_vas_p'], results['h2_olcek_p'], results['h3_oxford_p']]
    faz2_basarili = any(p < 0.05 for p in h_p_values)
    
    final_report_text = ""
    if results['faz1_is_denk'] and faz2_basarili:
        results['final_report_title'] = "NİHAİ SONUÇ: Güçlü Bulgular (Pozitif)"
        final_report_text = "Yorum: Araştırma, gruplar arasında tam denklik (FAZ 1) sağlamıştır. İstatistiksel analizler (FAZ 2), müdahale grubunda korku ve/veya endişe düzeylerinde anlamlı bir azalma olduğunu doğrulamıştır. Bu bulgular, nefes egzersizi müdahalesinin, protokolde hedeflenen bağımlı değişkenler üzerinde anlamlı ve pozitif bir etkiye sahip olduğunu güçlü bir şekilde desteklemektedir."
    elif not results['faz1_is_denk'] and faz2_basarili:
        results['final_report_title'] = "NİHAİ SONUÇ: Düzeltilmiş Bulgular (Pozitif)"
        failed_vars_str = ", ".join(results['faz1_failed_vars_display_names'])
        final_report_text = f"Yorum: Hipotezler (FAZ 2) müdahale lehine çıksa da, FAZ 1 denklik testlerinde ({failed_vars_str}) başarısızlık tespit edilmiştir. Bu 'karıştırıcı değişkenler', FAZ 2 ANCOVA analizine otomatik olarak eklenerek etkileri 'kontrol altına alınmıştır'. Düzeltilmiş sonuçlar, müdahalenin (denklik hatalarına rağmen) pozitif bir etkiye sahip olduğunu desteklemektedir."
    elif results['faz1_is_denk'] and not faz2_basarili:
        results['final_report_title'] = "NİHAİ SONUÇ: Etkisiz Müdahale (Nötr Bulgular)"
        final_report_text = "Yorum: Araştırma, gruplar arasında tam denklik (FAZ 1) sağlamış olmasına rağmen, hipotez testleri (FAZ 2) müdahalenin istatistiksel olarak anlamlı bir fark yaratmadığını (p > 0.05) göstermiştir. Bu bulgular, nefes egzersizi müdahalesinin, bu çalışmanın koşulları ve örneklemi üzerinde ölçülebilir bir etkiye sahip olmadığını göstermektedir."
    else: # not faz1_is_denk and not faz2_basarili
        results['final_report_title'] = "NİHAİ SONUÇ: Sonuçsuz Bulgular (Geçersiz)"
        final_report_text = "Yorum: Araştırma hem FAZ 1 denklik testlerinde başarısız olmuş hem de FAZ 2 hipotez testlerinde anlamlı bir sonuç üretememiştir. Gruplar arasındaki başlangıç farkları ve müdahalenin etkisizliği nedeniyle, araştırma sonuçları 'geçersiz' (inconclusive) kabul edilmelidir."
    
    results['final_report_text'] = final_report_text.strip()
    results['error'] = None
    return results

# --- 6. BACKEND: TÜM GÖRSELLERİ OLUŞTURMA MOTORU ---
def generate_all_charts(df_charts):
    charts = {}
    
    df_charts_norm = df_charts.copy()
    for col in CATEGORIC_COLUMNS:
        df_charts_norm[col] = df_charts_norm[col].astype(str).apply(normalize_for_pdf)

    # --- BÖLÜM 1: Frekans Tabloları & Pasta Grafikler ---
    df_pie = df_charts_norm['medeni_durum'].value_counts().reset_index()
    charts['fig_pie_medeni'] = px.pie(df_pie, names='medeni_durum', values='count', hole=0.3, title=normalize_for_pdf("Medeni Durum"))
    charts['fig_pie_medeni'].update_traces(textposition='inside', textinfo='percent+label')
    charts['fig_pie_medeni'].update_layout(showlegend=False, margin=dict(t=30, b=20, l=20, r=20))

    df_pie = df_charts_norm['gelir_duzeyi'].value_counts().reset_index()
    charts['fig_pie_gelir'] = px.pie(df_pie, names='gelir_duzeyi', values='count', hole=0.3, title=normalize_for_pdf("Gelir Düzeyi"),
                                    category_orders={'gelir_duzeyi': ['Dusuk', 'Orta', 'Yuksek']})
    charts['fig_pie_gelir'].update_traces(textposition='inside', textinfo='percent+label')
    charts['fig_pie_gelir'].update_layout(showlegend=False, margin=dict(t=30, b=20, l=20, r=20))

    df_pie = df_charts_norm['calisma_durumu'].value_counts().reset_index()
    charts['fig_pie_calisma'] = px.pie(df_pie, names='calisma_durumu', values='count', hole=0.3, title=normalize_for_pdf("Çalışma Durumu"))
    charts['fig_pie_calisma'].update_traces(textposition='inside', textinfo='percent+label')
    charts['fig_pie_calisma'].update_layout(showlegend=False, margin=dict(t=30, b=20, l=20, r=20))

    df_pie = df_charts_norm['planli_gebelik_mi'].value_counts().reset_index()
    charts['fig_pie_plan'] = px.pie(df_pie, names='planli_gebelik_mi', values='count', hole=0.3, title=normalize_for_pdf("Planlı Gebelik"))
    charts['fig_pie_plan'].update_traces(textposition='inside', textinfo='percent+label')
    charts['fig_pie_plan'].update_layout(showlegend=False, margin=dict(t=30, b=20, l=20, r=20))
    
    # --- BÖLÜM 2: Sayısal Denklik (Kutu Grafikleri) ---
    charts['fig_yas_box'] = px.box(df_charts_norm, x='grup', y='yas', color='grup', title=normalize_for_pdf('Yaş Dağılımı (Gruplara Göre)'), points="all")
    charts['fig_yas_box'].update_layout(showlegend=False)
    
    charts['fig_hafta_box'] = px.box(df_charts_norm, x='grup', y='gebelik_haftasi', color='grup', title=normalize_for_pdf('Gebelik Haftası Dağılımı (Gruplara Göre)'), points="all")
    charts['fig_hafta_box'].update_layout(showlegend=False)

    # --- BÖLÜM 3: Kategorik Denklik (Sütun Grafikleri) ---
    charts['fig_egitim_bar'] = px.histogram(df_charts_norm, x='egitim_durumu', color='grup', barmode='group', title=normalize_for_pdf('Eğitim Durumu (Gruplara Göre)'),
                                            category_orders={'egitim_durumu': ['Ilkokul', 'Lise', 'Universite']})
    
    charts['fig_dogum_bar'] = px.histogram(df_charts_norm, x='dogum_baslangici', color='grup', barmode='group', title=normalize_for_pdf('Doğum Başlangıcı (Gruplara Göre)'))
    
    # --- BÖLÜM 4: Ortalama Puan Evrimi (Çizgi Grafikler) ---
    df_mean = df_charts_norm.groupby('grup')[['korku_vas_baseline', 'korku_vas_4cm', 'korku_vas_8cm']].mean().reset_index()
    zaman_etiketleri_vas = {'korku_vas_baseline': 'Baseline', 'korku_vas_4cm': '4cm', 'korku_vas_8cm': '8cm'}
    df_vas_long = df_mean.melt(id_vars='grup', value_vars=zaman_etiketleri_vas.keys(), var_name='Zaman', value_name='Ortalama Puan (VAS)')
    df_vas_long['Zaman'] = df_vas_long['Zaman'].map(zaman_etiketleri_vas)
    charts['fig_vas_line'] = px.line(df_vas_long, x='Zaman', y='Ortalama Puan (VAS)', color='grup', title=normalize_for_pdf('Ortalama VAS (Korku) Puanı Evrimi'), markers=True,
                                     category_orders={'Zaman': ['Baseline', '4cm', '8cm']})

    # --- BÖLÜM 5: Likert-tipi Görselleştirme ---
    vas_bins = [0, 4, 7, 10.1]; vas_labels = [normalize_for_pdf('Düşük Korku (0-3)'), normalize_for_pdf('Orta Korku (4-6)'), normalize_for_pdf('Yüksek Korku (7-10)')]
    df_likert = df_charts_norm[['grup', 'korku_vas_baseline', 'korku_vas_4cm', 'korku_vas_8cm']].copy()
    df_likert['Baseline'] = pd.cut(df_likert['korku_vas_baseline'], bins=vas_bins, labels=vas_labels, right=False)
    df_likert['4cm (Latent Son)'] = pd.cut(df_likert['korku_vas_4cm'], bins=vas_bins, labels=vas_labels, right=False)
    df_likert['8cm (Aktif Son)'] = pd.cut(df_likert['korku_vas_8cm'], bins=vas_bins, labels=vas_labels, right=False)
    df_long = df_likert.melt(id_vars=['grup'], value_vars=['Baseline', '4cm (Latent Son)', '8cm (Aktif Son)'], var_name='Olum Zamani', value_name='Korku Seviyesi')
    color_map = {vas_labels[0]: 'green', vas_labels[1]: 'orange', vas_labels[2]: 'red'}
    charts['fig_stacked'] = px.histogram(df_long, x='Olum Zamani', color='Korku Seviyesi', facet_col='grup', barmode='stack', barnorm='percent', title=normalize_for_pdf('Korku Seviyelerinin (VAS) Zamana Göre Değişimi'),
                                         color_discrete_map=color_map, category_orders={"Olum Zamani": ['Baseline', '4cm (Latent Son)', '8cm (Aktif Son)'], "Korku Seviyesi": vas_labels}) 

    # --- BÖLÜM 6: Korelasyon Isı Haritası ---
    corr_cols_in_df = [col for col in NUMERIC_COLUMNS if col in df_charts_norm.columns]
    corr_matrix = df_charts_norm[corr_cols_in_df].corr()
    charts['fig_heatmap'] = px.imshow(corr_matrix, text_auto='.2f', aspect="auto", color_continuous_scale='RdBu_r', zmin=-1, zmax=1, title=normalize_for_pdf("Sayısal Değişkenler Korelasyon Isı Haritası"))
    
    return charts

# --- 7. FRONTEND: TÜM ARAYÜZ FONKSİYONLARI ---

def display_kılavuz_tab():
    """ (v12.2) Kılavuz sekmesini (içi dolu metinlerle) çizer."""
    st.header("Protokol Kılavuzu ve Metodoloji")
    st.markdown("Bu bölümde, analiz motorunun dayandığı istatistiksel yöntemler ve veri setindeki değişkenlerin rolleri profesyonel bir dille açıklanmaktadır.")
    
    st.subheader("1. Temel Metodolojik Terimler")
    st.markdown("""
    - **Visual Analog Skala (VAS):** Katılımcının; ağrı, korku veya anksiyete gibi sübjektif bir deneyimi, 0 (hiç yok) ile 10 (en şiddetli) arasında derecelendirdiği, valide edilmiş (geçerliliği kanıtlanmış) bir ölçüm aracıdır.
    - **Latent Faz:** Doğum eyleminin başladığı, servikal silinme ve dilatasyonun (açılma) başladığı ancak ilerlemenin yavaş olduğu (protokolde ~0-4 cm arası olarak tanımlanan) evredir.
    - **Aktif Faz:** Servikal dilatasyonun hızlandığı (protokolde ~4-8/10 cm arası olarak tanımlanan), doğum eyleminin güçlü ve düzenli kasılmalarla ilerlediği evredir.
    """)
    
    st.subheader("2. FAZ 1: Grupların Başlangıç Denkliği (Baseline Equivalence)")
    st.info("Amaç: Araştırmanın iç geçerliliğini (internal validity) sağlamak.")
    st.markdown("""
    Randomize Kontrollü Deneylerde (RCT), 'Müdahale' (Deney) ve 'Kontrol' grupları oluşturulur. Bu iki grubun, araştırma başlamadan önceki **karıştırıcı değişkenler (confounders)** bakımından birbirine denk olması hayati önem taşır.
    
    **Denklik Testi (FAZ 1)**, tam olarak bu kontrolü yapar. Raporumuzda, denklik değişkenleri için `p > 0.05` (p-değerinin 0.05'ten büyük) olması, "gruplar arasında istatistiksel olarak anlamlı bir fark yoktur" anlamına gelir. Bu, randomizasyonun başarılı olduğunu ve grupların karşılaştırmaya uygun (homojen) olduğunu teyit eder.
    """)
    
    st.subheader("3. FAZ 2: Hipotez Testleri için ANCOVA'nın Rolü")
    st.info("Amaç: Müdahalenin 'saf' etkisini (net effect) izole etmek.")
    st.markdown("""
    Hipotezleri test ederken (örn. 8cm'deki korku puanlarını karşılaştırırken) basit bir t-testi kullanmak, katılımcıların 4cm'deki bireysel farklılıklarını göz ardı edecektir.
    
    **ANCOVA (Kovaryans Analizi)**, Son-Test (Post-Test) puanlarını (örn. `korku_vas_8cm`) gruplar arasında karşılaştırırken, katılımcıların Ön-Test (Pre-Test) puanlarını (örn. `korku_vas_4cm`) bir **'kovaryant' (kontrol değişkeni)** olarak analize dahil eder.
    
    **Bu motor (v12.2) daha da akıllıdır:** Eğer FAZ 1'de 'Yaş' veya 'Eğitim Durumu' gibi bir değişkende denklik bozulursa (p < 0.05), bu 'sorunlu' değişkenleri de ANCOVA formülüne otomatik olarak bir kovaryant olarak ekler ve sonucu buna göre **DÜZELTİR**.
    """)
    
    st.divider()
    st.subheader("4. Veri Seti Değişkenlerinin (Sütunların) Analizdeki Rolü")
    
    st.markdown("Veri setindeki her sütun, analizde belirli bir rol üstlenir. Bu roller 3 ana kategoriye ayrılır (İndireceğiniz Excel Şablonundaki sütun adlarıdır):")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("Grup A: Denklik Değişkenleri (Karıştırıcılar)")
        st.markdown("""
        "FAZ 1: Denklik Testi" için kullanılırlar. Grupların homojenliğini (benzerliğini) test ederler.
        - **`yas`** - **`gebelik_haftasi`** - **`egitim_durumu`**
        - **`dogum_baslangici`** - **`medeni_durum`** - **`gelir_duzeyi`**
        - **`calisma_durumu`** - **`planli_gebelik_mi`**
        """)
    with col2:
        st.info("Grup B: Kovaryantlar (Ön-Testler)")
        st.markdown("""
        "FAZ 2: ANCOVA" analizinde 'kontrol değişkeni' olarak kullanılırlar.
        - **`korku_vas_baseline`** - **`korku_olcek_baseline`**
        - **`endise_oxford_baseline`**
        - **`korku_vas_4cm`** - **`korku_olcek_4cm`**
        """)
    with col3:
        st.info("Grup C: Bağımlı Değişkenler (Son-Testler)")
        st.markdown("""
        Bunlar, müdahalenin etkisinin ölçüldüğü nihai 'sonuç' değişkenleridir.
        - **`korku_vas_4cm`** - **`korku_olcek_4cm`**
        - **`korku_vas_8cm`** - **`korku_olcek_8cm`**
        - **`endise_oxford_son_test`**
        """)

def display_dashboard_tab(df_charts, charts):
    """(v12.0) Dashboard sekmesini, önceden oluşturulmuş grafiklerle çizer."""
    st.header("Veri Seti Özeti (Keşifsel Veri Analizi Dashboard)")
    try:
        st.subheader("Sosyodemografik Dağılımlar (Frekans ve Yüzdeler)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Medeni Durum**")
            st.plotly_chart(charts['fig_pie_medeni'], use_container_width=True)
            df_pie_data = df_charts['medeni_durum'].value_counts().reset_index().rename(columns={'medeni_durum': 'Kategori', 'count': 'Sayı (n)'})
            st.dataframe(df_pie_data, use_container_width=True)
        with col2:
            st.markdown("**Gelir Düzeyi**")
            st.plotly_chart(charts['fig_pie_gelir'], use_container_width=True)
            df_pie_data = df_charts['gelir_duzeyi'].value_counts().reset_index().rename(columns={'gelir_duzeyi': 'Kategori', 'count': 'Sayı (n)'})
            st.dataframe(df_pie_data, use_container_width=True)
        
        st.divider()
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Çalışma Durumu**")
            st.plotly_chart(charts['fig_pie_calisma'], use_container_width=True)
            df_pie_data = df_charts['calisma_durumu'].value_counts().reset_index().rename(columns={'calisma_durumu': 'Kategori', 'count': 'Sayı (n)'})
            st.dataframe(df_pie_data, use_container_width=True)
        with col4:
            st.markdown("**Planlı Gebelik**")
            st.plotly_chart(charts['fig_pie_plan'], use_container_width=True)
            df_pie_data = df_charts['planli_gebelik_mi'].value_counts().reset_index().rename(columns={'planli_gebelik_mi': 'Kategori', 'count': 'Sayı (n)'})
            st.dataframe(df_pie_data, use_container_width=True)
        
        st.divider()
        st.subheader("Sayısal Değişkenlerin Gruplara Göre Dağılımı (Denklik Kontrolü)")
        col1_box, col2_box = st.columns(2)
        with col1_box:
            st.plotly_chart(charts['fig_yas_box'], use_container_width=True)
        with col2_box:
            st.plotly_chart(charts['fig_hafta_box'], use_container_width=True)
        
        st.divider()
        st.subheader("Kategorik Değişkenlerin Gruplara Göre Dağılımı (Denklik Kontrolü)")
        col1_bar, col2_bar = st.columns(2)
        with col1_bar:
            st.plotly_chart(charts['fig_egitim_bar'], use_container_width=True)
        with col2_bar:
            st.plotly_chart(charts['fig_dogum_bar'], use_container_width=True)
            
        st.divider()
        st.subheader("Ortalama Puanların Zamana Göre Evrimi")
        st.plotly_chart(charts['fig_vas_line'], use_container_width=True)
        
        st.divider()
        st.subheader("Korku Seviyesi Dağılımının Evrimi (Likert-tipi)")
        st.plotly_chart(charts['fig_stacked'], use_container_width=True)
        
        st.divider()
        st.subheader("Değişken İlişki Haritası (Korelasyon)")
        st.plotly_chart(charts['fig_heatmap'], use_container_width=True)
        
    except Exception as e:
        st.error(f"Görselleştirme hatası: {e}. Lütfen Excel dosyanızdaki sütun adlarını ('Kılavuz' sekmesinde belirtilen) kontrol edin.")

def display_analysis_tab(analysis_results, charts_for_pdf):
    """(v12.0) Analiz sekmesini çizer ve PDF indirme butonunu yönetir."""
    try:
        if analysis_results.get('error'):
            st.error(analysis_results['error'])
        else:
            st.divider()
            st.header("FAZ 1: Başlangıç Denkliği (Tanımlayıcı İstatistikler)")
            df_numeric = pd.DataFrame(analysis_results['faz1_numeric_p_values'].items(), columns=["Değişken", "p-değeri"])
            df_categoric = pd.DataFrame(analysis_results['faz1_categoric_p_values'].items(), columns=["Değişken", "p-değeri"])
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Sayısal Değişkenler")
                st.dataframe(df_numeric, use_container_width=True)
            with col2:
                st.subheader("Kategorik Değişkenler")
                st.dataframe(df_categoric, use_container_width=True) 
            
            if analysis_results['faz1_is_denk']:
                st.success("SONUÇ: Randomizasyon BAŞARILI (Tüm p > 0.05)")
                st.markdown("Gruplar arasında istatistiksel olarak anlamlı bir başlangıç farkı bulunamamıştır. Bu, grupların homojen (denk) olduğunu ve araştırmanın iç geçerliliğinin yüksek olduğunu gösterir.")
            else:
                st.warning("SONUÇ: Randomizasyon BAŞARISIZ (p < 0.05)")
                failed_vars_str = ", ".join(analysis_results['faz1_failed_vars_display_names'])
                st.markdown(f"**Neden Kaynaklı?:** Analiz, gruplar arasında **{failed_vars_str}** değişken(ler)i açısından istatistiksel olarak anlamlı bir fark (p < 0.05) tespit etmiştir.")
            
            st.divider()
            st.header("FAZ 2: Hipotez Testleri (ANCOVA)")
            correction_text = analysis_results.get('correction_applied')
            if correction_text:
                st.info(f"""
                    **DİKKAT: İSTATİSTİKSEL DÜZELTME UYGULANDI**\n
                    FAZ 1'deki denklik hatası(ları) nedeniyle, FAZ 2 ANCOVA formüllerine 
                    şu değişken(ler) 'kontrol değişkeni' (kovaryant) olarak 
                    otomatik eklenmiştir: **{correction_text}**\n
                    Gördüğünüz p-değerleri, bu 'düzeltilmiş' sonuçlardır.
                """)
            
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                st.subheader("[H1: Latent Faz Korku]")
                p1_vas = analysis_results['h1_vas_p']; p1_olcek = analysis_results['h1_olcek_p']
                st.metric(label="VAS Sonucu", value="DESTEKLENDİ" if p1_vas < 0.05 else "Reddedildi", delta=f"p-değeri: {p1_vas:.6f}")
                st.metric(label="Doğum Korku Ölçeği Sonucu", value="DESTEKLENDİ" if p1_olcek < 0.05 else "Reddedildi", delta=f"p-değeri: {p1_olcek:.6f}")
            with col_h2:
                st.subheader("[H2: Aktif Faz Korku]")
                p2_vas = analysis_results['h2_vas_p']; p2_olcek = analysis_results['h2_olcek_p']
                st.metric(label="VAS Sonucu", value="DESTEKLENDİ" if p2_vas < 0.05 else "Reddedildi", delta=f"p-değeri: {p2_vas:.6f}")
                st.metric(label="Doğum Korku Ölçeği Sonucu", value="DESTEKLENDİ" if p2_olcek < 0.05 else "Reddedildi", delta=f"p-değeri: {p2_olcek:.6f}")
            with col_h3:
                st.subheader("[H3: Endişe Düzeyi]")
                p3_oxford = analysis_results['h3_oxford_p']
                st.metric(label="Oxford Endişe Ölçeği Sonucu", value="DESTEKLENDİ" if p3_oxford < 0.05 else "Reddedildi", delta=f"p-değeri: {p3_oxford:.6f}")
            
            st.divider()
            st.header("Nihai Rapor Yorumu (Analist Özeti)")
            report_title = analysis_results['final_report_title']
            report_text = analysis_results['final_report_text']
            if "Güçlü" in report_title: st.success(report_title)
            elif "Düzeltilmiş" in report_title: st.success(report_title) 
            elif "Etkisiz" in report_title: st.info(report_title)
            else: st.error(report_title)
            st.markdown(report_text)
            
            st.balloons()
            st.divider()
            
            st.header("Raporu Dışa Aktar")
            try:
                # (v12.0) PDF BUTONU ARTIK GRAFİKLERİ DE GÖNDERİYOR
                pdf_bytes = create_pdf_report(analysis_results, charts_for_pdf)
                st.download_button(
                    label="Kapsamlı Raporu PDF Olarak İndir (Metin + Grafikler)",
                    data=pdf_bytes,
                    file_name="Ebelik_Arastirma_Raporu_v12.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as pdf_e:
                st.error(f"PDF oluşturulurken bir hata oluştu: {pdf_e}")
                st.error("Rapor PDF'e dönüştürülemedi. 'kaleido' kütüphanesinin kurulu olduğundan emin olun.")
            
    except Exception as e:
        st.error(f"Genel bir hata oluştu: {e}")
        st.warning("Analiz başarısız olduğu için PDF raporu oluşturulamaz.")

def clear_session_state():
    """Yeni bir dosya yüklendiğinde eski sonuçları ve grafikleri hafızadan siler."""
    keys_to_delete = ['analysis_results', 'df_for_tabs', 'charts_dict']
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]

# --- 8. ANA UYGULAMA MANTIĞI (v12.2) ---

st.set_page_config(page_title="Ebelik Araştırması Analiz Motoru", layout="wide")

# --- Kenar Çubuğu (Sidebar) ---
st.sidebar.title("🤰 Ebelik Araştırması")
st.sidebar.header("Adım 1: Şablonu İndirin")
excel_buffer = create_template_excel()
st.sidebar.download_button(
    label="Boş Excel Şablonunu İndir",
    data=excel_buffer,
    file_name="Ebelik_Veri_Giris_Sabloni.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
    help="Analiz motorunun çalışması için verilerinizi bu şablona girmeniz gerekmektedir."
)

st.sidebar.header("Adım 2: Şablonu Yükleyin")
uploaded_file = st.sidebar.file_uploader(
    "Lütfen doldurduğunuz şablonu buraya yükleyin",
    type=["xlsx"],
    on_change=clear_session_state, 
    help="Verilerinizle doldurduğunuz 'Ebelik_Veri_Giris_Sabloni.xlsx' dosyasını yükleyin."
)

st.sidebar.header("Adım 3: Analiz Edin")
start_analysis = st.sidebar.button("Analizi Başlat", type="primary", use_container_width=True, help="Yüklenen veriyi analiz eder ve raporlar.")
st.sidebar.divider()
st.sidebar.info("v12.2 - Uzman Sistem (Temiz & Kapsamlı Rapor)")

# --- Ana Arayüz ---
st.title("Ebelik Araştırması İstatistiksel Analiz Raporu")

# --- v12.3 Eklentisi: Footer ---
footer_html = """
<style>
.footer {
    position: fixed;
    right: 15px; /* Kenardan biraz boşluk */
    bottom: 10px;
    width: auto;
    text-align: right;
    font-size: 12px;
    color: #888; /* Düşük görünürlüklü gri */
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.footer a {
    color: #0077B5; /* LinkedIn mavisine yakın bir renk */
    text-decoration: none; /* Alt çizgiyi kaldır */
}
.footer a:hover {
    text-decoration: underline; /* Üzerine gelince altını çiz */
}
</style>

<div class="footer">
    Geliştirici: Oğuzhan Yazıcı<br>
    © 2025 Tüm hakları saklıdır. | 
    <a href="https://www.linkedin.com/in/o%C4%9Fuzhan-yaz%C4%B1c%C4%B1-2b09aa327/" target="_blank">LinkedIn Profilim</a>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
# --- Footer Eklentisi Bitişi ---


# 3 Sekmeyi her zaman göster
tab_kılavuz, tab_dashboard, tab_analiz = st.tabs([
    "ℹ️ Protokol Kılavuzu", 
    "📊 Veri Seti Özeti (Dashboard)",
    "📈 İstatistiksel Analiz (Rapor)"
])

with tab_kılavuz:
    display_kılavuz_tab()

# --- Analiz ve Yükleme Mantığı ---
if start_analysis:
    if uploaded_file is not None:
        if 'analysis_results' not in st.session_state: 
            try:
                df_from_excel = None
                with st.spinner("Veri okunuyor ve 'yok', '7,0' gibi hatalı girişler temizleniyor..."):
                    df_from_excel = pd.read_excel(uploaded_file, engine='openpyxl')
                    
                    df_cleaned = df_from_excel.copy()
                    for col in NUMERIC_COLUMNS:
                        if col in df_cleaned.columns:
                            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
                        else:
                            pass 
                    
                    st.session_state.df_for_tabs = df_cleaned 

                with st.spinner("İstatistiksel analiz motoru çalıştırılıyor... (Dinamik Düzeltme yapılıyor...)"):
                    st.session_state.analysis_results = run_full_analysis(df_cleaned)
                
                if st.session_state.analysis_results.get('error') is None:
                    with st.spinner("Tüm dashboard grafikleri oluşturuluyor... (Bu işlem 10-15 saniye sürebilir...)"):
                        st.session_state.charts_dict = generate_all_charts(df_cleaned)
                else:
                    st.session_state.charts_dict = {} 
                
                st.rerun() 
                
            except Exception as e:
                st.error(f"Genel bir hata oluştu: {e}")
                clear_session_state()
    else:
        st.warning("Lütfen 'Analizi Başlat' butonuna basmadan önce Adım 2'de bir dosya yükleyin.")

# --- Sekmeleri Doldurma ---
if 'analysis_results' in st.session_state and 'df_for_tabs' in st.session_state:
    results = st.session_state.analysis_results
    df_display = st.session_state.df_for_tabs
    charts = st.session_state.get('charts_dict', {}) 
    
    if results.get('error'):
        with tab_analiz: 
            st.error(results['error'])
        with tab_dashboard:
            st.error(f"Analiz başarısız olduğu için dashboard oluşturulamadı: {results['error']}")
    else:
        with tab_dashboard:
            display_dashboard_tab(df_display, charts)
        with tab_analiz:
            display_analysis_tab(results, charts)
else:
    with tab_dashboard:
        st.info("Veri setinin görsel özetini görmek için lütfen sol menüdeki adımları izleyin.")
    with tab_analiz:
        st.info("İstatistiksel analiz raporunu görmek için lütfen sol menüdeki adımları izleyin.")
