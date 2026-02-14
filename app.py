import streamlit as st
import pandas as pd
import pdfplumber
import re
import os
import base64
import json
import glob
import time
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
# --- ESTILOS CSS ---
def get_theme_css(theme_mode):
    # ==========================
    # CSS COMÚN (Fuentes, Layout)
    # ==========================
    common_css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stCard {
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .stCard:hover { transform: translateY(-2px); }
    
    .feature-card {
        padding: 1.5rem;
        border-radius: 1rem;
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
    }
    .feature-card:hover { transform: translateY(-5px); }

    .stButton>button {
        background: linear-gradient(90deg, #0969da 0%, #0550ae 100%);
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(9, 105, 218, 0.2);
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #0b7bed 0%, #0660cf 100%);
        box-shadow: 0 6px 12px rgba(9, 105, 218, 0.3);
        transform: translateY(-2px);
        color: white !important;
    }
    """
    
    # ==========================
    # MODO CLARO (LIGHT)
    # ==========================
    if theme_mode == "Claro":
        mode_css = """
        .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        h1, h2, h3 { color: #2C3E50 !important; }
        h1 {
            background: -webkit-linear-gradient(45deg, #0969da, #2C3E50);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stCard { background-color: white; }
        .feature-card {
            background: white; border: 1px solid #eee; color: #333333;
        }
        .feature-card h3 { color: #0969da !important; }
        .feature-card p { color: #555555 !important; }
        
        /* Sidebar Claro */
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa; border-right: 1px solid #dee2e6;
        }
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label {
            color: #495057 !important;
        }
        
        /* Inputs Claro */
        .stTextInput>div>div>input, .stNumberInput>div>div>input, div[data-baseweb="select"] > div {
            background-color: #ffffff !important; border: 1px solid #ced4da !important; color: #000000 !important;
        }
        .stTextInput label, .stSelectbox label, .stFileUploader label { color: #212529 !important; }
        """
    
    # ==========================
    # MODO OSCURO (DARK)
    # ==========================
    else:
        mode_css = """
        .stApp { background: linear-gradient(135deg, #1a1c24 0%, #0e1117 100%); }
        h1, h2, h3 { color: #e0e0e0 !important; }
        h1 {
            background: -webkit-linear-gradient(45deg, #4da4ff, #e0e0e0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stCard { background-color: #262730; }
        .feature-card {
            background: #262730; border: 1px solid #41444e; color: #e0e0e0;
        }
        .feature-card h3 { color: #4da4ff !important; }
        .feature-card p { color: #b0b0b0 !important; }
        
        /* Sidebar Oscuro */
        section[data-testid="stSidebar"] {
            background-color: #1e1e1e; border-right: 1px solid #41444e;
        }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
             color: #e0e0e0 !important; border-bottom: 2px solid #41444e;
        }
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label {
            color: #cfcfcf !important;
        }
        
        /* Inputs Oscuro */
        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div, div[data-baseweb="select"] > div {
            background-color: #262730 !important; border: 1px solid #41444e !important; color: #e0e0e0 !important;
        }
        input { color: #e0e0e0 !important; caret-color: #e0e0e0 !important; }
        .stTextInput label, .stSelectbox label, .stFileUploader label, .stRadio label { color: #e0e0e0 !important; }
        
        /* File Uploader Oscuro */
        [data-testid="stFileUploader"] section {
            background-color: #262730 !important; border: 1px dashed #41444e !important;
        }
        [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] small, [data-testid="stFileUploader"] div {
            color: #cfcfcf !important;
        }
        """

    return f"<style>{common_css}{mode_css}</style>"

# --- THEME SELECTOR ---
with st.sidebar.expander("⚙️ Configuración", expanded=True):
    app_theme = st.radio("Tema de la App", ["Claro", "Oscuro"], index=1, horizontal=True)

st.markdown(get_theme_css(app_theme), unsafe_allow_html=True)

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
# GESTIÓN DE SESIONES COLABORATIVAS
# ==========================================
SESSIONS_DIR = "sessions"
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

def get_available_sessions():
    files = glob.glob(os.path.join(SESSIONS_DIR, "*.json"))
    return [os.path.basename(f).replace(".json", "") for f in files]

def load_session_data(session_name):
    try:
        with open(os.path.join(SESSIONS_DIR, f"{session_name}.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error cargando sesión: {e}")
        return None

def save_session_data(session_name, data):
    try:
        data['last_updated'] = datetime.now().isoformat()
        with open(os.path.join(SESSIONS_DIR, f"{session_name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Error guardando sesión: {e}")
        return False

# ==========================================
# MODULO 1: CONDUCE SIMPLE (Original)
# ==========================================
def clean_model_name(model_name):
    # Lista de colores simplificada para mantener codigo limpio
    colors_to_remove = [
        'negro', 'rojo', 'verde', 'azul', 'blanco', 'gris', 'plateado',
        'dorado', 'púrpura', 'morado', 'lavanda', 'rosa', 'rosado', 'amarillo', 'naranja', 'marrón',
        'cyan', 'magenta', 'grafito', 'sierra', 'black', 'red', 'green',
        'blue', 'white', 'gray', 'silver', 'gold', 'purple', 'pink',
        'yellow', 'orange', 'brown', 'graphite', 'midnight blue',
        'desert gold', 'titanium', 'oro', 'arena', 'pantone', 'tapestry',
        'arabesque', 'navy', 'violet', 'mint', 'cream', 'beige', 'charcoal',
        'blaze', 'pure', 'tendril', 'polar', 'deep', 'space', 'rose'
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
        # Check active session for auto-sync
        active_session = st.session_state.get('active_session')
        
        # Load from session if requested (via button or init)
        if active_session and st.session_state.get('trigger_load_session'):
            session_data = load_session_data(active_session)
            if session_data and session_data.get('type') == 'conduce_simple':
                st.session_state.c_cli = session_data.get('destinatario', '')
                st.session_state.c_fac = session_data.get('factura', '')
                st.session_state.c_df = pd.DataFrame(session_data.get('items', []))
    if 'c_df' in st.session_state:
        # Check active session for auto-sync
        active_session = st.session_state.get('active_session')
        
        # Load from session if requested (via button or init)
        if active_session and st.session_state.get('trigger_load_session'):
            session_data = load_session_data(active_session)
            if session_data and session_data.get('type') == 'conduce_simple':
                st.session_state.c_cli = session_data.get('destinatario', '')
                st.session_state.c_fac = session_data.get('factura', '')
                st.session_state.c_df = pd.DataFrame(session_data.get('items', []))
                st.session_state.trigger_load_session = False
                st.session_state.data_version = st.session_state.get('data_version', 0) + 1 # Force editor update
                st.rerun()

        # Dynamic key to force refresh when data updates from session
        editor_key = f"editor_simple_{st.session_state.get('data_version', 0)}"
        edited_df = st.data_editor(st.session_state.c_df, num_rows="dynamic", use_container_width=True, key=editor_key)
        
        # Auto-save changes to session
        if active_session:
            current_data = {
                "type": "conduce_simple",
                "destinatario": destinatario, # Use current input values
                "factura": factura,
                "items": edited_df.to_dict('records')
            }
            # Save on every interaction potentially heavy, but ensures real-time feel
            save_session_data(active_session, current_data)
            st.caption(f"☁️ Guardado en sesión: {active_session}")
            
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
# MODULO 3: CONDUCE CON IMEIS
# ==========================================
def generate_conduce_imeis_pdf(destinatario, factura, logo_source, data_df, accent_hex):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                            leftMargin=0.4*inch, rightMargin=0.4*inch, 
                            topMargin=0.3*inch, bottomMargin=0.3*inch)
    story = []
    styles = getSampleStyleSheet()

    # --- HEADER ---
    logo_paragraph = get_logo_image_reader(logo_source)
    
    title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'], alignment=2, fontSize=18, spaceAfter=5, textColor=colors.HexColor("#2C3E50"))
    title = Paragraph("CONDUCE DE ENTREGA (IMEIs)", title_style)
    
    header_table = Table([[logo_paragraph, title]], colWidths=[2.5*inch, 5.0*inch])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))

    # --- INFO ---
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

    # --- TITLE GOODS ---
    Story_Goods = [
        [Paragraph("<b>DETALLE DE MERCANCÍA</b>", ParagraphStyle('H2Center', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.black))]
    ]
    t_title_goods = Table(Story_Goods, colWidths=[7.7*inch])
    t_title_goods.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(accent_hex)),
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(t_title_goods)
    
    # --- GOODS TABLE ---
    prod_data = [[Paragraph('<b>CANT</b>', styles['Normal']), Paragraph('<b>DESCRIPCIÓN DEL MODELO / EQUIPO</b>', styles['Normal'])]]
    
    data = data_df.sort_values(by="Modelo")
    row_style = ParagraphStyle('Row', parent=styles['Normal'], fontSize=10, leading=11)
    
    for _, row in data.iterrows():
        prod_data.append([str(row['Cantidad']), Paragraph(str(row['Modelo']), row_style)])
        
    t_products = Table(prod_data, colWidths=[0.8*inch, 6.9*inch])
    t_products.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
    ]))
    story.append(t_products)
    story.append(Spacer(1, 0.2*inch))

    # --- IMEIS SECTION ---
    # Check if any IMEIs exist
    has_imeis = data['IMEIs'].str.strip().ne('').any()
    
    if has_imeis:
        # Title IMEIs
        Story_Imeis_Title = [
            [Paragraph("<b>DETALLE DE IMEIS / SERIALES</b>", ParagraphStyle('H2Center', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.black))]
        ]
        t_title_imeis = Table(Story_Imeis_Title, colWidths=[7.7*inch])
        t_title_imeis.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(accent_hex)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(t_title_imeis)

        # IMEIs Content
        imei_rows = []
        style_imeis = ParagraphStyle('Imeis', parent=styles['Normal'], fontSize=8, leading=10)
        
        for _, row in data.iterrows():
            imeis_text = str(row['IMEIs']).strip()
            if imeis_text:
                full_text = f"<b>{row['Modelo']}:</b> {imeis_text}"
                imei_rows.append([Paragraph(full_text, style_imeis)])
        
        if imei_rows:
            t_imeis_content = Table(imei_rows, colWidths=[7.7*inch])
            t_imeis_content.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('topPadding', (0,0), (-1,-1), 3),
                ('bottomPadding', (0,0), (-1,-1), 3),
            ]))
            story.append(t_imeis_content)
        
        story.append(Spacer(1, 0.2*inch))

    # --- FOOTER ---
    note_text = """<b>Nota Importante:</b> Al firmar como "Recibido Conforme", el cliente acepta las políticas de la empresa y certifica que ha recibido la mercancía detallada en este conduce, con los seriales/IMEIs aquí descritos. La mercancía viaja por cuenta y riesgo del comprador."""
    story.append(Paragraph(note_text, ParagraphStyle('Note', parent=styles['Normal'], fontSize=7)))
    story.append(Spacer(1, 0.4*inch))

    sig_data = [["_______________________", "_______________________"], ["Despachado por", "RECIBIDO CONFORME"]]
    sig_table = Table(sig_data, colWidths=[3.75*inch, 3.75*inch])
    sig_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(sig_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

def page_conduce_imeis():
    st.header("📱 Generador de Conduces con IMEIs")
    
    # Session Status Banner
    active_session = st.session_state.get('active_session')
    if active_session:
        st.info(f"🔗 MODO COLABORATIVO ACTIVO: **{active_session}**")
        col_sync1, col_sync2 = st.columns([1, 4])
        if col_sync1.button("📥 Recargar Datos"):
             st.session_state.trigger_load_session = True
             st.rerun()
             
    uploaded_pdf = st.file_uploader("📂 Sube tu factura (PDF)", type="pdf", key="conduce_imeis_pdf")
    
    if uploaded_pdf:
        if 'ci_file' not in st.session_state or st.session_state.ci_file != uploaded_pdf.name:
            st.session_state.ci_file = uploaded_pdf.name
            cli, fac, df = extract_conduce_info(uploaded_pdf)
            st.session_state.ci_cli = cli
            st.session_state.ci_fac = fac
            # Add separate empty column for IMEIs if not present
            if 'IMEIs' not in df.columns:
                df['IMEIs'] = ""
            st.session_state.ci_df = df
    
    col1, col2 = st.columns(2)
    destinatario = col1.text_input("Destinatario", value=st.session_state.get('ci_cli', ''))
    factura = col2.text_input("No. Factura", value=st.session_state.get('ci_fac', ''))
    
    st.info("💡 Puedes pegar los IMEIs directamente en la columna 'IMEIs' al lado de cada modelo.")
    
    if 'ci_df' in st.session_state:
        # Load logic for IMEIs page
        if active_session and st.session_state.get('trigger_load_session'):
            session_data = load_session_data(active_session)
            if session_data and session_data.get('type') == 'conduce_imeis':
                st.session_state.ci_cli = session_data.get('destinatario', '')
                st.session_state.ci_fac = session_data.get('factura', '')
                st.session_state.ci_df = pd.DataFrame(session_data.get('items', []))
                st.session_state.trigger_load_session = False # Reset flag
                st.session_state.data_version = st.session_state.get('data_version', 0) + 1 # Force editor update
                st.rerun()

        # Dynamic key to force refresh
        editor_key = f"editor_imeis_{st.session_state.get('data_version', 0)}"
        edited_df = st.data_editor(
            st.session_state.ci_df, 
            num_rows="dynamic", 
            use_container_width=True,
            key=editor_key,
            column_config={
                "Cantidad": st.column_config.NumberColumn(default=1, min_value=1),
                "IMEIs": st.column_config.TextColumn("IMEIs / Seriales", width="large", help="Pega aquí los seriales separados por espacio o coma, o cada uno en una linea nueva")
            }
        )
        
        # Auto-save logic
        if active_session:
            current_data = {
                "type": "conduce_imeis",
                "destinatario": destinatario,
                "factura": factura,
                "items": edited_df.to_dict('records')
            }
            save_session_data(active_session, current_data)
            st.caption(f"☁️ Sincronizado con sesión: {active_session}")

    else:
        edited_df = pd.DataFrame(columns=['Cantidad', 'Modelo', 'IMEIs'])

    if st.button("Generar PDF con IMEIs", type="primary", use_container_width=True):
        if 'logo_active' in st.session_state:
            pdf_bytes = generate_conduce_imeis_pdf(destinatario, factura, st.session_state.logo_active, edited_df, st.session_state.accent_color).getvalue()
            b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600"></iframe>', unsafe_allow_html=True)

# ==========================================
# APP MAIN
# ==========================================

# Initialize session state for navigation
if 'navigation_target' not in st.session_state:
    st.session_state.navigation_target = "Inicio"

def navigate_to(page):
    st.session_state.navigation_target = page

# --- SIDEBAR (Global) ---
with st.sidebar:
    st.title("Menu Principal")
    
    # Selection bound to session state
    selection = st.radio("Ir a:", ["Inicio", "Conduce de Entrega", "Conduce con IMEIs", "Recibo de Garantía"], key="navigation_target")

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
    
    # 3. Collaborative Mode
    st.sidebar.subheader("🤝 Colaboración (Experimental)")
    with st.expander("Panel de Sesiones"):
        session_opts = get_available_sessions()
        new_session = st.text_input("Nueva Sesión (Nombre)")
        if st.button("Crear Nueva"):
            if new_session:
                save_session_data(new_session, {"created": datetime.now().isoformat(), "items": []})
                st.success(f"Creada: {new_session}")
                st.rerun()
        
        st.markdown("---")
        selected_session = st.selectbox("Unirse a Sesión", ["-- Seleccionar --"] + session_opts)
        
        if st.button("Conectar / Cargar"):
            if selected_session and selected_session != "-- Seleccionar --":
                st.session_state.active_session = selected_session
                st.session_state.trigger_load_session = True # Trigger load on next run
                st.success(f"Conectado a: {selected_session}")
            else:
                st.session_state.active_session = None
                st.warning("Desconectado")
        
        if st.session_state.get('active_session'):
            st.sidebar.success(f"🟢 Activa: {st.session_state.active_session}")
            if st.button("Salir de Sesión"):
                st.session_state.active_session = None
                st.rerun()

            st.markdown("---")
            st.checkbox("📡 Modo Tiempo Real (Auto-Recarga)", value=False, key="live_mode", help="Activa para ver cambios automáticamente. Desactiva para editar.")
            
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>Sistema de Documentos v2.0</p>
            <p>© 2026</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- ROUTER ---
if st.session_state.navigation_target == "Inicio":
    st.markdown("<h1 style='text-align: center; margin-bottom: 50px;'>Bienvenido al Sistema de Documentos</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 40px; margin-bottom: 15px;">🚚</div>
            <h3 style="margin-bottom: 10px;">Conduce de Entrega</h3>
            <p style="color: #666; font-size: 14px; margin-bottom: 20px;">Genera documentos de entrega automáticamente procesando tus facturas PDF.</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("Acceder a Conduces", 
                  key="btn_conduce",
                  use_container_width=True, 
                  type="primary", 
                  on_click=navigate_to, 
                  args=("Conduce de Entrega",))

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 40px; margin-bottom: 15px;">📱</div>
            <h3 style="margin-bottom: 10px;">Conduce con IMEIs</h3>
            <p style="color: #666; font-size: 14px; margin-bottom: 20px;">Herramienta especializada para equipos que requieren registro de seriales o IMEIs.</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("Acceder a IMEIs", 
                  key="btn_imeis",
                  use_container_width=True, 
                  type="primary", 
                  on_click=navigate_to, 
                  args=("Conduce con IMEIs",))

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 40px; margin-bottom: 15px;">🛡️</div>
            <h3 style="margin-bottom: 10px;">Recibo de Garantía</h3>
            <p style="color: #666; font-size: 14px; margin-bottom: 20px;">Crea recibos de garantía profesionales de forma manual y rápida.</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("Acceder a Garantía", 
                  key="btn_garantia",
                  use_container_width=True, 
                  type="primary", 
                  on_click=navigate_to, 
                  args=("Recibo de Garantía",))

elif st.session_state.navigation_target == "Conduce de Entrega":
    page_conduce()

elif st.session_state.navigation_target == "Conduce con IMEIs":
    page_conduce_imeis()

elif st.session_state.navigation_target == "Recibo de Garantía":
    page_garantia()

# --- AUTO-REFRESH LOGIC ---
if st.session_state.get('active_session') and st.session_state.get('live_mode'):
    time.sleep(2)
    st.rerun()
