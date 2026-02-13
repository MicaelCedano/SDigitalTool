import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import pdfplumber
import re
import os
import platform
import json
import logging
import subprocess
import webbrowser
from datetime import datetime

# Importar librerías de ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    filename='pdfconduce.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- CONSTANTES ---
CONFIG_FILE = 'pdfconduce_config.json'
DEFAULT_THEME_COLOR = '#BDE5F8' # Azul claro por defecto

# Colores predefinidos para el PDF
PDF_THEMES = {
    "Azul Clásico": "#BDE5F8",
    "Verde Menta": "#C1E1C1",
    "Gris Elegante": "#E0E0E0",
    "Rojo Suave": "#FADBD8",
    "Dorado": "#F9E79F"
}

# Lista base de colores a eliminar (se puede extender en config)
DEFAULT_COLORS_TO_REMOVE = [
    'negro', 'rojo', 'verde', 'azul', 'blanco', 'gris', 'plateado',
    'dorado', 'púrpura', 'morado', 'lavanda', 'rosa', 'rosado', 'amarillo', 'naranja', 'marrón',
    'cyan', 'magenta', 'grafito', 'sierra', 'black', 'red', 'green',
    'blue', 'white', 'gray', 'silver', 'gold', 'purple', 'pink',
    'yellow', 'orange', 'brown', 'graphite', 'midnight blue',
    'desert gold', 'titanium', 'oro', 'arena', 'pantone', 'tapestry',
    'arabesque', 'navy', 'violet', 'mint', 'cream', 'beige', 'charcoal',
    'blaze', 'pure', 'tendril', 'polar', 'deep', 'space', 'rose'
]

class ConfigManager:
    """Maneja la carga y guardado de la configuración en JSON."""
    def __init__(self):
        self.config = {
            "logo_path": "",
            "recent_pdfs": [],
            "learned_corrections": {}, # { "Modelo Original": "Modelo Corregido" }
            "pdf_theme": "Azul Clásico",
            "colors_to_remove": DEFAULT_COLORS_TO_REMOVE,
            "last_destinatario": "",
            "last_output_dir": ""
        }
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
            except Exception as e:
                logging.error(f"Error cargando config: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando config: {e}")
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def add_recent_pdf(self, path):
        if path in self.config["recent_pdfs"]:
            self.config["recent_pdfs"].remove(path)
        self.config["recent_pdfs"].insert(0, path)
        self.config["recent_pdfs"] = self.config["recent_pdfs"][:5] # Mantener solo los últimos 5
        self.save_config()

    def add_correction(self, original, corrected):
        self.config["learned_corrections"][original] = corrected
        self.save_config()

class PDFProcessorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = ConfigManager()

        # --- Configuración de la ventana ---
        self.title("Generador de Conduces Pro")
        self.geometry("950x750")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.pdf_path = ""
        self.processed_data = None

        self.setup_ui()

    def setup_ui(self):
        # --- HEADER / MENU SUPERIOR ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="ew")
        
        # Historial de Archivos
        ctk.CTkLabel(header_frame, text="Recientes:").pack(side="left", padx=5)
        self.recent_files_combo = ctk.CTkComboBox(
            header_frame, 
            values=self.cfg.config["recent_pdfs"] if self.cfg.config["recent_pdfs"] else ["Sin historial"],
            width=300,
            command=self.on_recent_file_select
        )
        self.recent_files_combo.pack(side="left", padx=5)

        # Configuración de Tema PDF
        ctk.CTkLabel(header_frame, text="Color PDF:").pack(side="left", padx=(20, 5))
        self.theme_combo = ctk.CTkComboBox(
            header_frame,
            values=list(PDF_THEMES.keys()),
            command=self.on_theme_change
        )
        self.theme_combo.set(self.cfg.config.get("pdf_theme", "Azul Clásico"))
        self.theme_combo.pack(side="left", padx=5)

        # --- FRAME 1: SELECCIÓN ---
        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        files_frame.grid_columnconfigure(1, weight=1)

        # Botón PDF
        self.select_pdf_button = ctk.CTkButton(files_frame, text="Seleccionar PDF (Origen)", command=self.select_pdf_file)
        self.select_pdf_button.grid(row=0, column=0, padx=20, pady=10)
        self.file_path_label = ctk.CTkLabel(files_frame, text="Ningún archivo seleccionado", text_color="gray")
        self.file_path_label.grid(row=0, column=1, padx=20, pady=10, sticky="w")

        # Botón Logo
        self.select_logo_button = ctk.CTkButton(files_frame, text="Seleccionar Logo", command=self.select_logo_file, fg_color="transparent", border_width=1)
        self.select_logo_button.grid(row=1, column=0, padx=20, pady=10)
        logo_text = f"Logo: {os.path.basename(self.cfg.config['logo_path'])}" if self.cfg.config['logo_path'] else "Sin logo seleccionado"
        self.logo_path_label = ctk.CTkLabel(files_frame, text=logo_text, text_color="gray")
        self.logo_path_label.grid(row=1, column=1, padx=20, pady=10, sticky="w")


        # --- FRAME 2: DATOS ---
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(info_frame, text="Destinatario:").grid(row=0, column=0, padx=10, pady=10)
        self.destinatario_entry = ctk.CTkEntry(info_frame, placeholder_text="Cliente...")
        self.destinatario_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        # Autocompletar último usado (simple)
        if self.cfg.config["last_destinatario"]:
             self.destinatario_entry.insert(0, self.cfg.config["last_destinatario"])

        ctk.CTkLabel(info_frame, text="No. Factura:").grid(row=0, column=2, padx=10, pady=10)
        self.factura_entry = ctk.CTkEntry(info_frame, placeholder_text="12345...")
        self.factura_entry.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        self.show_total_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(info_frame, text="Mostrar Total Equipos", variable=self.show_total_var).grid(row=0, column=4, padx=10)

        # --- FRAME 3: PREVIEW ---
        preview_frame = ctk.CTkFrame(self)
        preview_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        preview_frame.grid_rowconfigure(1, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        # Toolbar de Acciones
        toolbar = ctk.CTkFrame(preview_frame, height=40, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.load_button = ctk.CTkButton(toolbar, text="🔄 Cargar Datos PDF", command=self.process_pdf_for_preview, state="disabled", fg_color="#2ecc71", text_color="white")
        self.load_button.pack(side="left", padx=5)
        
        ctk.CTkButton(toolbar, text="+ Agregar Item Manual", command=self.add_manual_item, fg_color="#3498db").pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="✎ Editar", command=self.edit_selected_row, width=80).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🗑 Eliminar", command=self.delete_selected_row, width=80, fg_color="#e74c3c").pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="📊 Exportar Excel", command=self.export_to_excel, width=100, fg_color="transparent", border_width=1).pack(side="right", padx=5)

        # Treeview
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", foreground="white", fieldbackground="#2a2d2e", borderwidth=0, rowheight=30, font=('Arial', 12))
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", font=('Calibri', 10, 'bold'))
        
        self.tree = ttk.Treeview(preview_frame, columns=("Cantidad", "Modelo"), show="headings", selectmode="browse")
        self.tree.heading("Cantidad", text="Cantidad")
        self.tree.heading("Modelo", text="Modelo / Descripción")
        self.tree.column("Cantidad", width=100, anchor="center")
        self.tree.column("Modelo", width=600)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Scrollbar
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        # --- FRAME 4: FOOTER / GENERAR ---
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        self.status_label = ctk.CTkLabel(footer_frame, text="Listo.", text_color="gray")
        self.status_label.pack(side="left")

        self.generate_button = ctk.CTkButton(footer_frame, text="🚀 Generar y Abrir PDF", command=self.generate_and_open_pdf, state="disabled", font=("Arial", 14, "bold"), height=40)
        self.generate_button.pack(side="right", padx=5)

        self.email_button = ctk.CTkButton(footer_frame, text="✉ Enviar por Correo", command=self.send_email_action, state="disabled", fg_color="transparent", border_width=1)
        self.email_button.pack(side="right", padx=5)

    # --- LÓGICA DE INTERFAZ ---
    
    def on_recent_file_select(self, choice):
        if choice and choice != "Sin historial":
            if os.path.exists(choice):
                self.pdf_path = choice
                self.file_path_label.configure(text=f"PDF: {os.path.basename(choice)}", text_color="white")
                self.load_button.configure(state="normal")
                self.status_label.configure(text=f"Cargado desde historial: {os.path.basename(choice)}")
                # Opcional: Auto-cargar
                # self.process_pdf_for_preview()
            else:
                self.status_label.configure(text=f"El archivo ya no existe: {choice}", text_color="red")

    def on_theme_change(self, choice):
        self.cfg.config["pdf_theme"] = choice
        self.cfg.save_config()

    def select_pdf_file(self):
        file_path = filedialog.askopenfilename(title="Selecciona un PDF", filetypes=(("Archivos PDF", "*.pdf"),))
        if file_path:
            self.pdf_path = file_path
            self.file_path_label.configure(text=f"PDF: {os.path.basename(file_path)}", text_color="white")
            self.load_button.configure(state="normal")
            self.generate_button.configure(state="disabled") # Requiere volver a procesar/validar
            
            self.cfg.add_recent_pdf(file_path)
            # Actualizar combo
            self.recent_files_combo.configure(values=self.cfg.config["recent_pdfs"])
            self.recent_files_combo.set(file_path)

    def select_logo_file(self):
        logo_path = filedialog.askopenfilename(title="Selecciona Logo", filetypes=(("Imágenes", "*.png *.jpg *.jpeg"),))
        if logo_path:
            self.cfg.config["logo_path"] = logo_path
            self.cfg.save_config()
            self.logo_path_label.configure(text=f"Logo: {os.path.basename(logo_path)}", text_color="white")

    def check_buttons_state(self):
        has_data =  len(self.tree.get_children()) > 0
        state = "normal" if has_data else "disabled"
        self.generate_button.configure(state=state)
        # Email se habilita solo tras generar el PDF exitosamente, pero aquí lo habilitamos si hay algo que procesar 
        # (aunque la lógica real es después de generar). Lo dejaremos disabled hasta generar.

    # --- LÓGICA DE PROCESAMIENTO ---

    def process_pdf_for_preview(self):
        if not self.pdf_path: return
        self.status_label.configure(text="Procesando PDF...", text_color="cyan")
        self.update_idletasks()
        
        try:
            raw_text = self.extract_text_from_pdf()
            
            # 1. Extracción de Metadatos (Cliente, Factura)
            cliente_match = re.search(r"Cliente:\s*(.*?)(?=\s*(?:Dirección:|Vendedor:|$))", raw_text, re.DOTALL | re.IGNORECASE)
            factura_match = re.search(r"No Factura\s*(\w+)", raw_text, re.IGNORECASE)
            
            if cliente_match:
                self.destinatario_entry.delete(0, 'end')
                self.destinatario_entry.insert(0, cliente_match.group(1).strip())
            if factura_match:
                self.factura_entry.delete(0, 'end')
                self.factura_entry.insert(0, factura_match.group(1).strip())

            # 2. Extracción de Productos
            # Pattern 1: Standard
            found_items_1 = re.findall(r"^(\d+\.\d{2})\s+(.*?)(?=\s+\d{1,3}(?:,?\d{3})*\.\d{2})", raw_text, re.MULTILINE)
            # Pattern 2: Inverted
            found_items_2 = re.findall(r"^(.+?)\s+\d{1,3}(?:,?\d{3})*\.\d{2}\s+0\.00\s+\d{1,3}(?:,?\d{3})*\.\d{2}\n\s*(\d+\.\d{2})\s*$", raw_text, re.MULTILINE)
            found_items_2 = [(qty, desc) for desc, qty in found_items_2] # Swap
            
            found_items = found_items_1 + found_items_2
            
            if not found_items:
                messagebox.showinfo("Aviso", "No se encontraron productos automáticamente. Puede agregarlos manualmente.")
            
            df = pd.DataFrame(found_items, columns=['Cantidad', 'Modelo'])
            if not df.empty:
                df['Cantidad'] = pd.to_numeric(df['Cantidad']).astype(int)
                df['Modelo'] = df['Modelo'].apply(self.clean_model_name)
                
                # Agrupar
                df = df[df['Modelo'] != ""]
                df = df.groupby('Modelo', as_index=False)['Cantidad'].sum()
                self.processed_data = df
            else:
                self.processed_data = pd.DataFrame(columns=['Cantidad', 'Modelo'])

            self.populate_treeview()
            self.check_buttons_state()
            self.status_label.configure(text="Datos cargados correctamente.", text_color="lightgreen")

        except Exception as e:
            logging.error(f"Error procesando PDF: {e}")
            messagebox.showerror("Error", f"Error procesando PDF: {e}")
            self.status_label.configure(text="Error al procesar.", text_color="red")

    def extract_text_from_pdf(self):
        with pdfplumber.open(self.pdf_path) as pdf:
            return "\n".join(page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages)

    def clean_model_name(self, model_name):
        model = model_name
        
        # 1. Comprobar diccionario de correcciones aprendidas
        # Buscamos coincidencias aproximadas o exactas? Por ahora exactas pre-limpieza o post-limpieza
        # Haremos una limpieza básica, y luego checamos si hay rename.
        
        # Limpieza básica regex
        model = re.sub(r'\s*5g\b', '', model, flags=re.IGNORECASE)
        model = re.sub(r'\s*\d+\.?\d*\"+\s*$', '', model, flags=re.IGNORECASE)
        
        colors = self.cfg.config.get("colors_to_remove", [])
        color_pattern = r'\b(' + '|'.join(map(re.escape, colors)) + r')\b'
        model = re.sub(color_pattern, '', model, flags=re.IGNORECASE)
        
        model = re.sub(r'\(\s*\)', '', model)
        model = re.sub(r'\s+XT\w+-\w+', '', model, flags=re.IGNORECASE)
        model = re.sub(r'\s+A\w+L\b', '', model, flags=re.IGNORECASE)
        # Otros cleanups del usuario anterior
        model = re.sub(r'\s+SM-\w+\b', '', model, flags=re.IGNORECASE)
        model = re.sub(r'\bBLADE\b', '', model, flags=re.IGNORECASE)
        model = re.sub(r'\s+Z\d+\b', '', model, flags=re.IGNORECASE)
        model = re.sub(r'(\d+[GT]B)\b.*', r'\1', model, flags=re.IGNORECASE)
        
        model = re.sub(r'\s{2,}', ' ', model).strip()

        # 2. Aplicar corrección aprendida (si existe)
        if model in self.cfg.config["learned_corrections"]:
            return self.cfg.config["learned_corrections"][model]

        return model

    # --- EDICIÓN MANUAL Y GESTIÓN ---

    def populate_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if self.processed_data is not None:
            sorted_data = self.processed_data.sort_values(by="Modelo")
            for _, row in sorted_data.iterrows():
                self.tree.insert("", "end", values=(row["Cantidad"], row["Modelo"]))
        self.check_buttons_state()

    def add_manual_item(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Agregar Item")
        dialog.geometry("400x200")
        
        ctk.CTkLabel(dialog, text="Cantidad:").pack(pady=5)
        qty_entry = ctk.CTkEntry(dialog)
        qty_entry.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Modelo / Descripción:").pack(pady=5)
        model_entry = ctk.CTkEntry(dialog, width=300)
        model_entry.pack(pady=5)
        
        def save():
            q = qty_entry.get()
            m = model_entry.get()
            if q.isdigit() and m:
                self.tree.insert("", "end", values=(q, m))
                self.update_df_from_tree()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Cantidad inválida o modelo vacío.")
        
        ctk.CTkButton(dialog, text="Agregar", command=save).pack(pady=10)

    def edit_selected_row(self):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        old_qty, old_model = item['values']
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar Item")
        dialog.geometry("400x250")
        
        ctk.CTkLabel(dialog, text="Cantidad:").pack(pady=5)
        qty_entry = ctk.CTkEntry(dialog)
        qty_entry.insert(0, old_qty)
        qty_entry.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Modelo:").pack(pady=5)
        model_entry = ctk.CTkEntry(dialog, width=300)
        model_entry.insert(0, old_model)
        model_entry.pack(pady=5)
        
        remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(dialog, text="Recordar este cambio de nombre para el futuro", variable=remember_var).pack(pady=10)
        
        def save():
            new_q = qty_entry.get()
            new_m = model_entry.get()
            if new_q.isdigit() and new_m:
                self.tree.item(selected[0], values=(new_q, new_m))
                
                # Guardar aprendizaje si se solicitó y cambió el nombre
                if remember_var.get() and new_m != old_model:
                    self.cfg.add_correction(old_model, new_m)
                    print(f"Aprendido: {old_model} -> {new_m}")

                self.update_df_from_tree()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Datos inválidos.")

        ctk.CTkButton(dialog, text="Guardar Cambios", command=save).pack(pady=10)

    def delete_selected_row(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Confirmar", "¿Eliminar item seleccionado?"):
            self.tree.delete(selected[0])
            self.update_df_from_tree()

    def update_df_from_tree(self):
        rows = []
        for item_id in self.tree.get_children():
            row = self.tree.item(item_id)['values']
            rows.append(row)
        
        if rows:
            self.processed_data = pd.DataFrame(rows, columns=["Cantidad", "Modelo"])
            self.processed_data["Cantidad"] = pd.to_numeric(self.processed_data["Cantidad"])
        else:
            self.processed_data = pd.DataFrame(columns=["Cantidad", "Modelo"])
        
        self.check_buttons_state()

    def export_to_excel(self):
        if self.processed_data is None or self.processed_data.empty: return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            try:
                self.processed_data.to_excel(path, index=False)
                messagebox.showinfo("Éxito", "Exportado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al exportar: {e}")

    # --- GENERACIÓN DE PDF ---

    def generate_and_open_pdf(self):
        dest = self.destinatario_entry.get().strip()
        fact = self.factura_entry.get().strip()
        if not dest or not fact:
            messagebox.showwarning("Faltan Datos", "Ingrese Destinatario y No. Factura")
            return

        # Guardar destinatario en historial
        self.cfg.config["last_destinatario"] = dest
        self.cfg.save_config()

        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf", 
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"Conduce_{fact}.pdf",
            title="Guardar Conduce"
        )
        if not output_path: return

        try:
            accent_color = PDF_THEMES.get(self.cfg.config.get("pdf_theme", "Azul Clásico"), DEFAULT_THEME_COLOR)
            self.create_pdf_pro(dest, fact, self.cfg.config["logo_path"], output_path, accent_color)
            
            self.status_label.configure(text=f"Generado: {os.path.basename(output_path)}", text_color="lightgreen")
            self.generated_pdf_path = output_path # Guardar referencia para email
            self.email_button.configure(state="normal")
            
            if messagebox.askyesno("Abrir", "PDF Generado con éxito. ¿Deseas abrirlo?"):
                self.open_file(output_path)
                
        except Exception as e:
            logging.error(f"Error generando PDF: {e}")
            messagebox.showerror("Error Critico", f"No se pudo generar el PDF: {e}")

    def create_pdf_pro(self, destinatario, factura, logo_path, filename, accent_hex):
        # MÁRGENES REDUCIDOS para aprovechar la hoja al máximo
        doc = SimpleDocTemplate(filename, pagesize=letter, 
                                leftMargin=0.4*inch, rightMargin=0.4*inch, 
                                topMargin=0.3*inch, bottomMargin=0.3*inch)
        story = []
        styles = getSampleStyleSheet()

        # 1. Cabecera Compacta
        logo = Paragraph("", styles["Normal"])
        if logo_path and os.path.exists(logo_path):
            try:
                img = Image(logo_path)
                # Ajuste dinámico de tamaño (Más pequeño para ahorrar espacio)
                ir = ImageReader(logo_path)
                iw, ih = ir.getSize()
                aspect = ih / float(iw)
                target_w = 1.5 * inch # Reducido de 2.0
                target_h = target_w * aspect
                if target_h > 0.8 * inch: # Reducido de 1.2
                    target_h = 0.8 * inch
                    target_w = target_h / aspect
                img.drawWidth = target_w
                img.drawHeight = target_h
                logo = img
            except: pass

        # Título más pequeño y con menos espacio
        title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'], alignment=2, fontSize=18, spaceAfter=5, textColor=colors.HexColor("#2C3E50"))
        title = Paragraph("CONDUCE DE ENTREGA", title_style)
        
        # Tabla de cabecera ajustada
        header_table = Table([[logo, title]], colWidths=[2.5*inch, 5.0*inch])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        story.append(header_table)
        story.append(Spacer(1, 0.1*inch)) # Spacer reducido

        # 2. Info Cliente Compacta
        info_data = [
            [f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", f"FACTURA N°: {factura}"],
            [f"CLIENTE: {destinatario}", ""]
        ]
        info_table = Table(info_data, colWidths=[5.2*inch, 2.5*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9), # Fuente 9
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#34495E")),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor(accent_hex)),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2), # Padding reducido
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.1*inch)) # Spacer reducido

        # 3. Lista de Productos Compacta
        data = self.processed_data.sort_values(by="Modelo")
        table_data = [[Paragraph("CANT", styles["Normal"]), Paragraph("DESCRIPCIÓN DEL MODELO / EQUIPO", styles["Normal"]), Paragraph("VERIF.", styles["Normal"])]]
        
        # Estilos filas más compactos
        row_style = ParagraphStyle('Row', parent=styles['Normal'], fontSize=10, leading=11) # Fuente 10, Leading 11
        
        checkbox_symbol = "[      ]" 
        
        for _, row in data.iterrows():
            table_data.append([str(row['Cantidad']), Paragraph(row['Modelo'], row_style), checkbox_symbol])
        
        t = Table(table_data, colWidths=[0.8*inch, 6.1*inch, 0.8*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(accent_hex)),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black if self._is_light_color(accent_hex) else colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ALIGN', (0,1), (0,-1), 'CENTER'),
            ('ALIGN', (2,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9), # Header tabla fuente 9
            ('BOTTOMPADDING', (0,0), (-1,-1), 3), # Padding muy reducido
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(t)

        # 4. Total compactado
        if self.show_total_var.get():
            story.append(Spacer(1, 0.05*inch))
            total = data['Cantidad'].sum()
            tot_style = ParagraphStyle('Tot', parent=styles['Normal'], alignment=2, fontSize=11, fontName='Helvetica-Bold')
            story.append(Paragraph(f"TOTAL UNIDADES: {total}", tot_style))

        # 5. Footer Legal y Firmas (Pegado al contenido)
        story.append(Spacer(1, 0.2*inch)) # Spacer reducido
        
        note_text = """
        <b>Nota Importante:</b><br/>
        Al firmar como "Recibido Conforme", el cliente acepta las políticas de la empresa y certifica que ha recibido la mercancía detallada.<br/>
        Cualquier reclamo debe realizarse antes de retirar la mercancía. No nos hacemos responsables tras la salida.
        """
        # Fuente legal reducida a 7
        story.append(Paragraph(note_text, ParagraphStyle('Legal', fontSize=7, leading=8, textColor=colors.black)))
        
        story.append(Spacer(1, 0.3*inch))
        
        sig_data = [["_______________________", "_______________________"], ["Despachado por", "RECIBIDO CONFORME"]]
        sig_table = Table(sig_data, colWidths=[3.75*inch, 3.75*inch])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 9)
        ]))
        story.append(sig_table)

        doc.build(story)

    def _is_light_color(self, hex_color):
        # Estimación simple de brillo para decidir si el texto header es blanco o negro
        h = hex_color.lstrip('#')
        try:
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
            return brightness > 125
        except: return True

    def open_file(self, path):
        if platform.system() == 'Windows': os.startfile(path)
        elif platform.system() == 'Darwin': subprocess.call(['open', path])
        else: subprocess.call(['xdg-open', path])

    def send_email_action(self):
        # Abre el cliente de correo predeterminado.
        # No podemos adjuntar fiablemente en todas las plataformas sin librerías externas pesadas.
        # Ofrecemos abrir la carpeta y el mailto.
        subject = f"Envío de Conduce - {self.destinatario_entry.get()}"
        body = "Se adjunta el conduce de entrega correspondiente."
        
        # Intentar copiar al portapapeles la ruta? No, mejor abrir carpeta.
        if self.generated_pdf_path:
            folder = os.path.dirname(self.generated_pdf_path)
            self.open_file(folder) # Abrir carpeta para que el usuario arrastre
            
            # Abrir mail
            webbrowser.open(f"mailto:?subject={subject}&body={body}")
            messagebox.showinfo("Correo", "Se ha abierto tu cliente de correo y la carpeta del archivo.\nPor favor, arrastra el PDF al correo manualmente.")

if __name__ == "__main__":
    app = PDFProcessorApp()
    app.mainloop()
    