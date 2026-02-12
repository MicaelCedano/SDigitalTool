import streamlit as st
import pandas as pd
import pdfplumber
import re
import os
import base64
from datetime import datetime
from io import BytesIO

# Importar librerías de ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
st.set_page_config(page_title="Sistema de Documentos", layout="wide", page_icon="📂", initial_sidebar_state="collapsed")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .big-button {
        width: 100%;
        padding: 20px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 10px;
        background-color: #f0f2f6;
        border: 1px solid #d0d7de;
        text-align: center;
        margin-bottom: 10px;
        cursor: pointer;
        transition: 0.3s;
    }
    .big-button:hover {
        background-color: #e0e5ea;
        border-color: #0969da;
        color: #0969da;
    }
    h1 { color: #2C3E50; }
    .stButton>button { width: 100%; height: 100px; font-size: 20px; }
</style>
""", unsafe_allow_html=True)

# --- UTILS COMUNES ---
DEFAULT_THEME_COLOR = '#BDE5F8'
PDF_THEMES = {
    "Azul Clásico": "#BDE5F8",
    "Verde Menta": "#C1E1C1",
    "Gris Elegante": "#E0E0E0",
    "Rojo Suave": "#FADBD8",
    "Dorado": "#F9E79F"
}

LOGO_CACHE_FILE = "logo_cache_web.png"

def save_logo_to_cache(uploaded_file):
    try:
        with open(LOGO_CACHE_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except Exception as e:
        print(f"Error saving logo: {e}")
        return False

def get_cached_logo():
    if os.path.exists(LOGO_CACHE_FILE):
        return LOGO_CACHE_FILE
    return None

def _is_light_color(hex_color):
    h = hex_color.lstrip('#')
    try:
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
        return brightness > 125
    except: return True

def get_logo_image_reader(logo_source):
    """Helper to convert logo source (path or bytes) to ImageReader/Image safely"""
    logo_paragraph = Paragraph("", getSampleStyleSheet()["Normal"])
    if not logo_source:
        return logo_paragraph

    try:
        if isinstance(logo_source, str): # Ruta archivo
            with open(logo_source, "rb") as f:
                content = f.read()
                logo_bytes_io = BytesIO(content)
        else: # UploadedFile
            content = logo_source.read()
            logo_source.seek(0) # Reset
            logo_bytes_io = BytesIO(content)

        if logo_bytes_io:
            img_stream_1 = BytesIO(logo_bytes_io.getvalue())
            img_stream_2 = BytesIO(logo_bytes_io.getvalue())
            
            logo_img = Image(img_stream_1)
            ir = ImageReader(img_stream_2)
            
            iw, ih = ir.getSize()
            aspect = ih / float(iw)
            
            target_w = 1.5 * inch
            target_h = target_w * aspect
            if target_h > 0.8 * inch:
                target_h = 0.8 * inch
                target_w = target_h / aspect
                
            logo_img.drawWidth = target_w
            logo_img.drawHeight = target_h
            return logo_img
    except Exception as e:
        st.warning(f"Error cargando logo: {e}")
    return logo_paragraph

# ==========================================
# MODULO 1: CONDUCE SIMPLE (Original)
# ==========================================
def clean_model_name(model_name):
    # Lista de colores simplificada para mantener codigo limpio
    colors_to_remove = [
        'negro', 'rojo', 'verde', 'azul', 'blanco', 'gris', 'plateado', 'dorado',
        'black', 'red', 'green', 'blue', 'white', 'gray', 'silver', 'gold'
    ]
    model = model_name
    model = re.sub(r'\s*5g\b', '', model, flags=re.IGNORECASE)
    model = re.sub(r'\s*\d+\.?\d*\"+\s*$', '', model, flags=re.IGNORECASE)
    color_pattern = r'\b(' + '|'.join(map(re.escape, colors_to_remove)) + r')\b'
    model = re.sub(color_pattern, '', model, flags=re.IGNORECASE)
    model = re.sub(r'\(\s*\)', '', model)
    model = re.sub(r'\s{2,}', ' ', model).strip()
    return model

def extract_conduce_info(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join(page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages)
    
    cliente = ""
    factura = ""
    cliente_match = re.search(r"Cliente:\s*(.*?)(?=\s*(?:Dirección:|Vendedor:|$))", text, re.DOTALL | re.IGNORECASE)
    factura_match = re.search(r"No Factura\s*(\w+)", text, re.IGNORECASE)
    
    if cliente_match: cliente = cliente_match.group(1).strip()
    if factura_match: factura = factura_match.group(1).strip()

    found_items_1 = re.findall(r"^(\d+\.\d{2})\s+(.*?)(?=\s+\d{1,3}(?:,?\d{3})*\.\d{2})", text, re.MULTILINE)
    found_items_2 = re.findall(r"^(.+?)\s+\d{1,3}(?:,?\d{3})*\.\d{2}\s+0\.00\s+\d{1,3}(?:,?\d{3})*\.\d{2}\n\s*(\d+\.\d{2})\s*$", text, re.MULTILINE)
    found_items_2 = [(qty, desc) for desc, qty in found_items_2]
    
    found_items = found_items_1 + found_items_2
    
    df = pd.DataFrame(found_items, columns=['Cantidad', 'Modelo'])
    if not df.empty:
        df['Cantidad'] = pd.to_numeric(df['Cantidad']).astype(int)
        df['Modelo'] = df['Modelo'].apply(clean_model_name)
        df = df[df['Modelo'] != ""]
        df = df.groupby('Modelo', as_index=False)['Cantidad'].sum()
    
    return cliente, factura, df

def generate_conduce_pdf(destinatario, factura, logo_source, data_df, accent_hex, show_total):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                            leftMargin=0.4*inch, rightMargin=0.4*inch, 
                            topMargin=0.3*inch, bottomMargin=0.3*inch)
    story = []
    styles = getSampleStyleSheet()

    logo_paragraph = get_logo_image_reader(logo_source)

    title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'], alignment=2, fontSize=18, spaceAfter=5, textColor=colors.HexColor("#2C3E50"))
    title = Paragraph("CONDUCE DE ENTREGA", title_style)
    
    header_table = Table([[logo_paragraph, title]], colWidths=[2.5*inch, 5.0*inch])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))

    info_data = [
        [f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", f"FACTURA N°: {factura}"],
        [f"CLIENTE: {destinatario}", ""]
    ]
    info_table = Table(info_data, colWidths=[5.2*inch, 2.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#34495E")),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor(accent_hex)),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.1*inch))

    data = data_df.sort_values(by="Modelo")
    table_data = [[Paragraph("CANT", styles["Normal"]), Paragraph("DESCRIPCIÓN DEL MODELO / EQUIPO", styles["Normal"]), Paragraph("VERIF.", styles["Normal"])]]
    
    row_style = ParagraphStyle('Row', parent=styles['Normal'], fontSize=10, leading=11)
    
    for _, row in data.iterrows():
        table_data.append([str(row['Cantidad']), Paragraph(str(row['Modelo']), row_style), "[      ]"])
    
    t = Table(table_data, colWidths=[0.8*inch, 6.1*inch, 0.8*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(accent_hex)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black if _is_light_color(accent_hex) else colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (0,1), (0,-1), 'CENTER'),
        ('ALIGN', (2,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t)

    if show_total:
        story.append(Spacer(1, 0.05*inch))
        total = data['Cantidad'].sum()
        tot_style = ParagraphStyle('Tot', parent=styles['Normal'], alignment=2, fontSize=11, fontName='Helvetica-Bold')
        story.append(Paragraph(f"TOTAL UNIDADES: {total}", tot_style))

    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>Nota Importante:</b><br/>Recibido Conforme...", ParagraphStyle('Legal', fontSize=7, leading=8)))
    story.append(Spacer(1, 0.3*inch))
    
    sig_data = [["_______________________", "_______________________"], ["Despachado por", "RECIBIDO CONFORME"]]
    sig_table = Table(sig_data, colWidths=[3.75*inch, 3.75*inch])
    sig_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(sig_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

def page_conduce():
    st.header("🚚 Generador de Conduces")
    
    uploaded_pdf = st.file_uploader("📂 Sube tu factura (PDF)", type="pdf", key="conduce_pdf")
    
    if uploaded_pdf:
        if 'c_file' not in st.session_state or st.session_state.c_file != uploaded_pdf.name:
            st.session_state.c_file = uploaded_pdf.name
            cli, fac, df = extract_conduce_info(uploaded_pdf)
            st.session_state.c_cli = cli
            st.session_state.c_fac = fac
            st.session_state.c_df = df
    
    col1, col2 = st.columns(2)
    destinatario = col1.text_input("Destinatario", value=st.session_state.get('c_cli', ''))
    factura = col2.text_input("No. Factura", value=st.session_state.get('c_fac', ''))
    
    if 'c_df' in st.session_state:
        edited_df = st.data_editor(st.session_state.c_df, num_rows="dynamic", use_container_width=True)
    else:
        edited_df = pd.DataFrame(columns=['Cantidad', 'Modelo'])

    if st.button("Generar PDF", type="primary", use_container_width=True):
        if 'logo_active' in st.session_state:
            pdf_bytes = generate_conduce_pdf(destinatario, factura, st.session_state.logo_active, edited_df, st.session_state.accent_color, True).getvalue()
            b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600"></iframe>', unsafe_allow_html=True)

# ==========================================
# MODULO 2: RECIBO DE GARANTÍA
# ==========================================
def generate_garantia_pdf(store_name, date_str, items_df, logo_source):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.4*inch, rightMargin=0.4*inch, topMargin=0.4*inch, bottomMargin=0.2*inch)
    story = []
    styles = getSampleStyleSheet()

    # Logo
    logo_obj = get_logo_image_reader(logo_source)
    
    # Address
    address_text = "Calle Duarte, Esq Dr Ferry #54<br/>Sucursal La Romana<br/>RNC: 132872975"
    address_para = Paragraph(address_text, ParagraphStyle('Right', parent=styles['Normal'], alignment=0, leading=14, fontSize=10))

    t_header = Table([[logo_obj, address_para]], colWidths=[4*inch, 3.5*inch])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
    story.append(t_header)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("RECIBO DE GARANTIA", ParagraphStyle('TitleG', parent=styles['Heading1'], fontSize=24, textColor=colors.navy, spaceAfter=2)))
    story.append(Paragraph(f"Fecha:  {date_str}", ParagraphStyle('Date', parent=styles['Normal'], fontSize=12, textColor=colors.deeppink, fontName='Helvetica-Bold')))
    story.append(Paragraph(f"Tienda: {store_name}", ParagraphStyle('Store', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', spaceAfter=10)))

    # Items Table
    data_rows = [['CANT', 'DESCRIPCIÓN']]
    total_cant = 0
    
    for _, row in items_df.iterrows():
        qty = int(row['Cantidad']) if str(row['Cantidad']).isdigit() else 1
        total_cant += qty
        desc = f"<b>{row['Modelo']}</b>"
        if row['IMEIs/Coment']:
            desc += f"<br/><font size=10 color=grey>{row['IMEIs/Coment'].replace(',', '<br/>')}</font>"
        
        data_rows.append([str(qty), Paragraph(desc, ParagraphStyle('I', parent=styles['Normal'], fontSize=12))])

    data_rows.append([str(total_cant), Paragraph("<b>TOTAL EQUIPOS</b>", styles['Normal'])])

    t_items = Table(data_rows, colWidths=[1*inch, 6.5*inch])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 0.2*inch))

    # Terms
    terms = "La garantía quedará anulada si el equipo presenta daños físicos, humedad o mal uso."
    story.append(Paragraph(terms, ParagraphStyle('Terms', fontSize=8)))
    story.append(Spacer(1, 0.4*inch))
    
    story.append(Paragraph("___________________________________", ParagraphStyle('L', alignment=1)))
    story.append(Paragraph("Firma", ParagraphStyle('S', alignment=1, textColor=colors.deeppink)))

    doc.build(story)
    buffer.seek(0)
    return buffer

def page_garantia():
    st.header("🛡️ Recibo de Garantía")
    
    col1, col2 = st.columns(2)
    store = col1.text_input("Nombre Tienda", "ANGELO")
    date_val = col2.date_input("Fecha", datetime.now())
    
    st.subheader("Items")
    
    if 'g_df' not in st.session_state:
        st.session_state.g_df = pd.DataFrame(columns=['Cantidad', 'Modelo', 'IMEIs/Coment'])

    edited_df = st.data_editor(
        st.session_state.g_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Cantidad": st.column_config.NumberColumn(default=1, min_value=1),
            "IMEIs/Coment": st.column_config.TextColumn("Seriales / IMEIs (Opcional)")
        }
    )

    if st.button("🖨️ Generar Recibo", type="primary"):
        if edited_df.empty:
            st.error("Agrega items primero.")
        else:
            if 'logo_active' in st.session_state:
                pdf_bytes = generate_garantia_pdf(store, date_val.strftime("%d/%m/%Y"), edited_df, st.session_state.logo_active).getvalue()
                b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600"></iframe>', unsafe_allow_html=True)

# ==========================================
# APP MAIN
# ==========================================

# Initialize session state for navigation
if 'navigation_target' not in st.session_state:
    st.session_state.navigation_target = "Inicio"

# --- SIDEBAR (Global) ---
with st.sidebar:
    st.title("Menu Principal")
    
    # Selection bound to session state
    selection = st.radio("Ir a:", ["Inicio", "Conduce de Entrega", "Recibo de Garantía"], key="navigation_target")

    # 1. Config Logo (Global)
    st.sidebar.markdown("---")
    cached_logo = get_cached_logo()
    uploaded_logo = st.file_uploader("Logo (Global)", type=["png","jpg"])
    
    if uploaded_logo:
        save_logo_to_cache(uploaded_logo)
        st.session_state.logo_active = uploaded_logo
    elif cached_logo:
        st.session_state.logo_active = cached_logo
        st.sidebar.image(cached_logo, width=100)
    
    # 2. Config Color (Global)
    theme_name = st.selectbox("Tema PDF", list(PDF_THEMES.keys()))
    st.session_state.accent_color = PDF_THEMES[theme_name]
    
    st.markdown("---")


# --- ROUTER ---
if st.session_state.navigation_target == "Inicio":
    st.title("Bienvenido al Sistema")
    st.markdown("### Selecciona una herramienta para comenzar:")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚚 Conduce de Entrega\n\nGenerar documentos desde PDF", use_container_width=True, type="primary"):
            st.session_state.navigation_target = "Conduce de Entrega"
            st.rerun()

    with col2:
        if st.button("🛡️ Recibo de Garantía\n\nCrear recibo manual", use_container_width=True, type="primary"):
            st.session_state.navigation_target = "Recibo de Garantía"
            st.rerun()

elif st.session_state.navigation_target == "Conduce de Entrega":
    page_conduce()

elif st.session_state.navigation_target == "Recibo de Garantía":
    page_garantia()
