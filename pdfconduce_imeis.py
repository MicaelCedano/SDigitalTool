
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import pdfplumber
import re
import os
import platform
from datetime import datetime

# Importar las librerías necesarias de ReportLab para crear el PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# --- Nombres de archivos de configuración y salida ---
OUTPUT_FILE = 'conduce_imeis.pdf'
CONFIG_FILE = 'app_config.txt'

# --- Lista de colores a eliminar (Misma que original) ---
COLORS_TO_REMOVE = [
    'negro', 'rojo', 'verde', 'azul', 'blanco', 'gris', 'plateado',
    'dorado', 'púrpura', 'morado', 'lavanda', 'rosa', 'rosado', 'amarillo', 'naranja', 'marrón',
    'cyan', 'magenta', 'grafito', 'sierra', 'black', 'red', 'green',
    'blue', 'white', 'gray', 'silver', 'gold', 'purple', 'pink',
    'yellow', 'orange', 'brown', 'graphite', 'midnight blue',
    'desert gold', 'titanium', 'oro', 'arena', 'pantone', 'tapestry',
    'arabesque', 'navy', 'violet', 'mint', 'cream', 'beige', 'charcoal',
    'blaze', 'pure', 'tendril', 'polar', 'deep', 'space', 'rose'
]

class PDFProcessorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuración de la ventana ---
        self.title("Generador de Conduces con IMEIs")
        self.geometry("900x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.pdf_path = ""
        self.logo_path = ""
        self.processed_data = None
        self.imeis_data = {} # Diccionario para almacenar IMEIs: { "NombreModelo": "lista de imeis..." }

        # --- FRAME 1: SELECCIÓN DE ARCHIVOS ---
        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        files_frame.grid_columnconfigure(1, weight=1)

        self.select_pdf_button = ctk.CTkButton(files_frame, text="Seleccionar PDF de Origen", command=self.select_pdf_file)
        self.select_pdf_button.grid(row=0, column=0, padx=20, pady=(10, 5))
        self.file_path_label = ctk.CTkLabel(files_frame, text="Ningún archivo PDF seleccionado", text_color="gray")
        self.file_path_label.grid(row=0, column=1, padx=20, pady=(10, 5), sticky="w")

        self.select_logo_button = ctk.CTkButton(files_frame, text="Seleccionar Logo (Opcional)", command=self.select_logo_file)
        self.select_logo_button.grid(row=1, column=0, padx=20, pady=(5, 10))
        self.logo_path_label = ctk.CTkLabel(files_frame, text="Ningún logo seleccionado", text_color="gray")
        self.logo_path_label.grid(row=1, column=1, padx=20, pady=(5, 10), sticky="w")

        # --- FRAME 2: INFO DESTINATARIO Y FACTURA ---
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(info_frame, text="Destinatario:").grid(row=0, column=0, padx=(20, 5), pady=5, sticky="e")
        self.destinatario_entry = ctk.CTkEntry(info_frame, placeholder_text="Se completará desde el PDF...")
        self.destinatario_entry.grid(row=0, column=1, padx=(0, 20), pady=5, sticky="ew")

        ctk.CTkLabel(info_frame, text="No. Factura:").grid(row=1, column=0, padx=(20, 5), pady=5, sticky="e")
        self.factura_entry = ctk.CTkEntry(info_frame, placeholder_text="Se completará desde el PDF...")
        self.factura_entry.grid(row=1, column=1, padx=(0, 20), pady=5, sticky="ew")

        # --- FRAME 3: BOTÓN DE CARGA ---
        self.load_button = ctk.CTkButton(self, text="Cargar Datos del PDF a la Vista Previa", command=self.process_pdf_for_preview, state="disabled")
        self.load_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # --- FRAME 4: VISTA PREVIA (TREEVIEW) ---
        preview_frame = ctk.CTkFrame(self)
        preview_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", foreground="white", fieldbackground="#2a2d2e", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", font=('Calibri', 10, 'bold'))
        
        self.tree = ttk.Treeview(preview_frame, columns=("Cantidad", "Modelo", "HasIMEIs"), show="headings", selectmode="browse")
        self.tree.heading("Cantidad", text="Cantidad")
        self.tree.heading("Modelo", text="Modelo")
        self.tree.heading("HasIMEIs", text="¿Tiene IMEIs?")
        self.tree.column("Cantidad", width=100, anchor="center")
        self.tree.column("Modelo", width=400)
        self.tree.column("HasIMEIs", width=100, anchor="center")
        
        self.tree.grid(row=0, column=0, sticky="nsew")

        # --- BOTONES DE EDICIÓN Y EXPORTACIÓN ---
        edit_export_frame = ctk.CTkFrame(preview_frame)
        edit_export_frame.grid(row=1, column=0, sticky="ew", pady=(5,0))
        edit_export_frame.grid_columnconfigure(4, weight=1) # Push buttons left
        
        self.edit_button = ctk.CTkButton(edit_export_frame, text="Editar Fila", command=self.edit_selected_row)
        self.edit_button.grid(row=0, column=0, padx=5)

        # --- NUEVO BOTÓN PARA AÑADIR PRODUCTOS ---
        self.add_button = ctk.CTkButton(edit_export_frame, text="Añadir Producto", command=self.add_new_row, fg_color="#186A3B", hover_color="#145A32")
        self.add_button.grid(row=0, column=1, padx=5)
        
        self.delete_button = ctk.CTkButton(edit_export_frame, text="Eliminar Fila", command=self.delete_selected_row, fg_color="#c42b1c", hover_color="#8a1f16")
        self.delete_button.grid(row=0, column=2, padx=5)
        
        # --- NUEVO BOTÓN PARA IMEIS ---
        self.imei_button = ctk.CTkButton(edit_export_frame, text="Gestionar IMEIs", command=self.manage_imeis, fg_color="#2b8a3e", hover_color="#1e602b")
        self.imei_button.grid(row=0, column=3, padx=5)

        self.export_button = ctk.CTkButton(edit_export_frame, text="Exportar Excel", command=self.export_to_excel)
        self.export_button.grid(row=0, column=4, padx=5)

        # --- FRAME 5: BOTÓN DE GENERACIÓN Y ESTADO ---
        self.generate_button = ctk.CTkButton(self, text="Generar Conduce PDF con IMEIs", command=self.generate_and_open_pdf, state="disabled", height=40, font=('Arial', 14, 'bold'))
        self.generate_button.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="", text_color="cyan")
        self.status_label.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="w")
        
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    path = f.read().strip()
                    if path and os.path.exists(path):
                        self.logo_path = path
                        display_path = os.path.basename(self.logo_path)
                        self.logo_path_label.configure(text=f"Logo: {display_path}", text_color="white")
        except Exception:
            pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(self.logo_path)
        except Exception:
            pass

    def select_pdf_file(self):
        self.status_label.configure(text="")
        file_path = filedialog.askopenfilename(title="Selecciona un archivo PDF", filetypes=(("Archivos PDF", "*.pdf"),))
        if file_path:
            self.pdf_path = file_path
            self.file_path_label.configure(text=f"PDF: {os.path.basename(file_path)}", text_color="white")
            self.load_button.configure(state="normal")
            self.generate_button.configure(state="disabled")
            self.processed_data = None
            self.imeis_data = {}
            self.clear_treeview()

    def select_logo_file(self):
        self.status_label.configure(text="")
        logo_path = filedialog.askopenfilename(title="Selecciona un archivo de imagen", filetypes=(("Imágenes", "*.png *.jpg *.jpeg"),))
        if logo_path:
            self.logo_path = logo_path
            self.logo_path_label.configure(text=f"Logo: {os.path.basename(logo_path)}", text_color="white")
            self.save_config()

    def check_generate_button_state(self):
        if self.processed_data is not None and not self.processed_data.empty:
            self.generate_button.configure(state="normal")
        else:
            self.generate_button.configure(state="disabled")

    def process_pdf_for_preview(self):
        if not self.pdf_path: return
        self.status_label.configure(text="Procesando PDF...", text_color="cyan")
        self.update_idletasks()

        try:
            raw_text = self.extract_text_from_pdf()
            
            # --- Extracción básica de Cliente/Factura (igual que v1) ---
            cliente_match = re.search(r"Cliente:\s*(.*?)(?=\s*(?:Dirección:|Vendedor:|$))", raw_text, re.DOTALL | re.IGNORECASE)
            factura_match = re.search(r"No Factura\s*(\w+)", raw_text, re.IGNORECASE)

            if cliente_match:
                self.destinatario_entry.delete(0, 'end')
                self.destinatario_entry.insert(0, cliente_match.group(1).strip())
            if factura_match:
                self.factura_entry.delete(0, 'end')
                self.factura_entry.insert(0, factura_match.group(1).strip())

            # --- Extracción de Productos (Lógica de limpieza v1) ---
            product_pattern = re.compile(r"^(\d+\.\d{2})\s+(.*?)(?=\s+\d{1,3}(?:,?\d{3})*\.\d{2})", re.MULTILINE)
            found_items_1 = product_pattern.findall(raw_text)
            
            type2_pattern = re.compile(r"^(.+?)\s+\d{1,3}(?:,?\d{3})*\.\d{2}\s+0\.00\s+\d{1,3}(?:,?\d{3})*\.\d{2}\n\s*(\d+\.\d{2})\s*$", re.MULTILINE)
            found_items_2 = [(qty, desc) for desc, qty in type2_pattern.findall(raw_text)]
            
            found_items = found_items_1 + found_items_2
            
            if not found_items:
                messagebox.showinfo("Sin Resultados", "No se encontraron productos.")
                self.status_label.configure(text="No se encontraron datos.")
                return

            df = pd.DataFrame(found_items, columns=['Cantidad', 'Modelo'])
            df['Cantidad'] = pd.to_numeric(df['Cantidad']).astype(int)

            # --- Limpieza de Nombres de Modelos ---
            df['Modelo'] = df['Modelo'].str.replace(r'\s*5g\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s*\d+\.?\d*\"+\s*$', '', regex=True, flags=re.IGNORECASE).str.strip()
            color_pattern = r'\b(' + '|'.join(COLORS_TO_REMOVE) + r')\b'
            df['Modelo'] = df['Modelo'].str.replace(color_pattern, '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\(\s*\)', '', regex=True).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s+XT\w+-\w+', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s+A\w+L\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s+S\w+B\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s+PB\w+\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s+T\d+[A-Z]\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s+SM-\w+\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\bBLADE\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s+Z\d+\b', '', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'(\d+[GT]B)\b.*', r'\1', regex=True, flags=re.IGNORECASE).str.strip()
            df['Modelo'] = df['Modelo'].str.replace(r'\s{2,}', ' ', regex=True).str.strip()

            self.processed_data = df.groupby('Modelo', as_index=False)['Cantidad'].sum()
            self.imeis_data = {} # Resetear IMEIs al cargar nuevo PDF
            
            self.populate_treeview()
            self.check_generate_button_state()
            self.status_label.configure(text="Datos cargados correctamente.", text_color="lightgreen")

        except Exception as e:
            messagebox.showerror("Error", f"Error al procesar PDF: {e}")
            self.status_label.configure(text="Error de procesamiento", text_color="red")

    def extract_text_from_pdf(self):
        with pdfplumber.open(self.pdf_path) as pdf:
            return "\n".join(page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages)

    def populate_treeview(self):
        self.clear_treeview()
        sorted_data = self.processed_data.sort_values(by="Modelo")
        for index, row in sorted_data.iterrows():
            modelo = row["Modelo"]
            has_imeis = "SÍ" if modelo in self.imeis_data and self.imeis_data[modelo].strip() else "NO"
            self.tree.insert("", "end", values=(row["Cantidad"], modelo, has_imeis))

    def clear_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def add_new_row(self):
        add_win = ctk.CTkToplevel(self)
        add_win.title("Añadir Producto")
        
        ctk.CTkLabel(add_win, text="Cantidad:").grid(row=0, column=0, padx=10, pady=10)
        cantidad_entry = ctk.CTkEntry(add_win)
        cantidad_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(add_win, text="Modelo:").grid(row=1, column=0, padx=10, pady=10)
        modelo_entry = ctk.CTkEntry(add_win, width=300)
        modelo_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def save_new():
            try:
                cantidad = int(cantidad_entry.get())
                modelo = modelo_entry.get().strip()
                if not modelo:
                    raise ValueError("El modelo no puede estar vacío.")
                
                # Insertar en treeview
                self.tree.insert("", "end", values=(cantidad, modelo, "NO"))
                
                # Actualizar DataFrame
                new_row = {'Cantidad': cantidad, 'Modelo': modelo}
                if self.processed_data is not None:
                     # Using concat instead of append
                    new_df = pd.DataFrame([new_row])
                    self.processed_data = pd.concat([self.processed_data, new_df], ignore_index=True)
                else:
                    self.processed_data = pd.DataFrame([new_row])
                
                self.check_generate_button_state()
                add_win.destroy()
                self.status_label.configure(text=f"Producto '{modelo}' añadido.", text_color="cyan")
                
            except ValueError:
                messagebox.showerror("Error", "Cantidad inválida. Debe ser un número entero.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo añadir: {e}")

        ctk.CTkButton(add_win, text="Añadir", command=save_new).grid(row=2, column=0, columnspan=2, pady=10)

    def manage_imeis(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Gestión de IMEIs", "Selecciona un modelo para gestionar sus IMEIs.")
            return
        
        item = self.tree.item(selected[0])
        cantidad, modelo, _ = item['values']
        
        # Ventana para pegar/editar IMEIs
        imei_win = ctk.CTkToplevel(self)
        imei_win.title(f"Gestión de IMEIs - {modelo}")
        imei_win.geometry("600x500")
        
        ctk.CTkLabel(imei_win, text=f"Modelo: {modelo} (Cant: {cantidad})", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkLabel(imei_win, text="Pega aquí los IMEIs (separados por coma, espacio o enter):").pack(pady=5)
        
        textbox = ctk.CTkTextbox(imei_win, width=550, height=350)
        textbox.pack(pady=10)
        
        # Cargar IMEIs existentes si los hay
        if modelo in self.imeis_data:
            textbox.insert("0.0", self.imeis_data[modelo])
            
        def save_imeis():
            content = textbox.get("0.0", "end").strip()
            # Limpieza básica de la entrada
            content = content.replace("\n", ", ").replace("  ", " ")
            self.imeis_data[modelo] = content
            
            # Actualizar indicador en Treeview
            self.tree.set(selected[0], "HasIMEIs", "SÍ" if content else "NO")
            imei_win.destroy()
            self.status_label.configure(text=f"IMEIs guardados para {modelo}", text_color="cyan")

        ctk.CTkButton(imei_win, text="Guardar IMEIs", command=save_imeis).pack(pady=10)

    def edit_selected_row(self):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        cantidad, modelo, _ = item['values']
        
        edit_win = ctk.CTkToplevel(self)
        edit_win.title("Editar Fila")
        
        ctk.CTkLabel(edit_win, text="Cantidad:").grid(row=0, column=0, padx=10, pady=10)
        cantidad_entry = ctk.CTkEntry(edit_win)
        cantidad_entry.insert(0, str(cantidad))
        cantidad_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(edit_win, text="Modelo:").grid(row=1, column=0, padx=10, pady=10)
        modelo_entry = ctk.CTkEntry(edit_win, width=300)
        modelo_entry.insert(0, modelo)
        modelo_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def save_edit():
            old_model = modelo
            new_cantidad = int(cantidad_entry.get())
            new_modelo = modelo_entry.get().strip()
            
            # Si cambia el nombre del modelo, hay que migrar los IMEIs si existían
            if old_model != new_modelo and old_model in self.imeis_data:
                self.imeis_data[new_modelo] = self.imeis_data.pop(old_model)
            
            self.tree.item(selected[0], values=(new_cantidad, new_modelo, "SÍ" if new_modelo in self.imeis_data else "NO"))
            self.update_processed_data_from_tree()
            edit_win.destroy()

        ctk.CTkButton(edit_win, text="Guardar", command=save_edit).grid(row=2, column=0, columnspan=2, pady=10)

    def delete_selected_row(self):
        selected = self.tree.selection()
        if not selected: return
        
        modelo = self.tree.item(selected[0])['values'][1]
        
        if messagebox.askyesno("Eliminar", "¿Seguro que deseas eliminar la fila seleccionada?"):
            self.tree.delete(selected[0])
            if modelo in self.imeis_data: # Limpiar datos huérfanos
                del self.imeis_data[modelo]
            self.update_processed_data_from_tree()

    def update_processed_data_from_tree(self):
        items = self.tree.get_children()
        data = []
        for item in items:
            vals = self.tree.item(item)['values']
            data.append({'Cantidad': int(vals[0]), 'Modelo': vals[1]})
        self.processed_data = pd.DataFrame(data) if data else pd.DataFrame(columns=['Cantidad', 'Modelo'])
        self.check_generate_button_state()

    def export_to_excel(self):
        if self.processed_data is None or self.processed_data.empty: return
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if file_path:
            self.processed_data.to_excel(file_path, index=False)
            messagebox.showinfo("Exportar", f"Guardado en {os.path.basename(file_path)}")

    def generate_and_open_pdf(self):
        destinatario = self.destinatario_entry.get().strip()
        factura_num = self.factura_entry.get().strip()
        
        if not destinatario or not factura_num:
            messagebox.showwarning("Error", "Falta Destinatario o No. Factura.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf", 
            filetypes=[("PDF", "*.pdf")],
            initialfile=OUTPUT_FILE,
            title="Guardar Conduce"
        )
        if not file_path: return

        try:
            self.create_pdf_conduce(destinatario, factura_num, self.logo_path, file_path)
            
            if messagebox.askyesno("Éxito", f"PDF generado: {os.path.basename(file_path)}\n¿Abrir ahora?"):
                if platform.system() == "Windows": os.startfile(file_path)
                elif platform.system() == "Darwin": os.system(f'open "{file_path}"')
                else: os.system(f'xdg-open "{file_path}"')
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF: {e}")

    def create_pdf_conduce(self, destinatario, factura_num, logo_path, output_file):
        doc = SimpleDocTemplate(output_file, pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []

        # --- HEADER ---
        if logo_path and os.path.exists(logo_path):
            try:
                img_reader = ImageReader(logo_path)
                w, h = img_reader.getSize()
                aspect = h / float(w)
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch*aspect, hAlign='LEFT')
            except:
                logo = Paragraph("LOGO ERROR", styles['Normal'])
        else:
            logo = Paragraph("", styles['Normal'])

        title = Paragraph("CONDUCE", ParagraphStyle('Title', parent=styles['h1'], alignment=1, fontSize=16, spaceAfter=20))
        
        # Tabla Header (Logo + Titulo/Datos)
        # Usamos una tabla simple alineada
        header_data = [[logo, title]]
        t_header = Table(header_data, colWidths=[2.5*inch, 4*inch])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 0.2*inch))

        # --- DATOS DEL CLIENTE ---
        style_bold = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')
        style_normal = styles['Normal']
        
        client_data = [
            [Paragraph("<b>FECHA:</b>", style_normal), Paragraph(datetime.now().strftime("%d/%m/%Y"), style_normal)],
            [Paragraph("<b>DESTINATARIO:</b>", style_normal), Paragraph(destinatario, style_normal)],
            [Paragraph("<b>No. FACTURA:</b>", style_normal), Paragraph(factura_num, style_normal)]
        ]
        
        t_client = Table(client_data, colWidths=[1.5*inch, 5*inch])
        t_client.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_client)
        story.append(Spacer(1, 0.3*inch))

        # --- TABLA DE MERCANCIA ---
        # Header azul
        Story_Goods = [
            [Paragraph("<b>DETALLE DE MERCANCÍA</b>", ParagraphStyle('H2Center', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.black))]
        ]
        t_title_goods = Table(Story_Goods, colWidths=[6.5*inch])
        t_title_goods.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#BDE5F8')),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(t_title_goods)
        
        # Columnas
        prod_data = [[Paragraph('<b>CANTIDAD</b>', style_bold), Paragraph('<b>DESCRIPCIÓN</b>', style_bold)]]
        
        sorted_df = self.processed_data.sort_values(by="Modelo")
        for _, row in sorted_df.iterrows():
            prod_data.append([str(row['Cantidad']), Paragraph(row['Modelo'], style_normal)])
            
        t_products = Table(prod_data, colWidths=[1.5*inch, 5*inch])
        t_products.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), # Subheader gris
            ('ALIGN', (0,0), (-1,0), 'CENTER'), # Centrar titulos
            ('ALIGN', (0,1), (0,-1), 'CENTER'), # Centrar cantidades
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        story.append(t_products)
        story.append(Spacer(1, 0.3*inch))

        # --- TABLA DE IMEIS ---
        # Solo si hay algún IMEI registrado
        if any(self.imeis_data.values()):
            # Header Title
            Story_Imeis_Title = [
                [Paragraph("<b>DETALLE DE IMEIS</b>", ParagraphStyle('H2Center', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.black))]
            ]
            t_title_imeis = Table(Story_Imeis_Title, colWidths=[6.5*inch])
            t_title_imeis.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#BDE5F8')),
                ('BOX', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ]))
            story.append(t_title_imeis)

            # Contenido de IMEIs
            # Lo haremos como una tabla de 1 columna con multiples filas, una por modelo
            imei_rows = []
            
            # Estilo pequeño para los IMEIs
            style_imeis = ParagraphStyle('Imeis', parent=styles['Normal'], fontSize=8, leading=10)
            
            for _, row in sorted_df.iterrows():
                modelo = row['Modelo']
                if modelo in self.imeis_data and self.imeis_data[modelo].strip():
                    imei_text = self.imeis_data[modelo]
                    # Formato: "Modelo: imeis..."
                    # Usamos negrita para el modelo
                    full_text = f"<b>{modelo}:</b> {imei_text}"
                    p = Paragraph(full_text, style_imeis)
                    imei_rows.append([p])
            
            if imei_rows:
                t_imeis_content = Table(imei_rows, colWidths=[6.5*inch])
                t_imeis_content.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('topPadding', (0,0), (-1,-1), 3),
                    ('bottomPadding', (0,0), (-1,-1), 3),
                ]))
                story.append(t_imeis_content)
            
            story.append(Spacer(1, 0.3*inch))

        # --- NOTA Y FIRMAS ---
        note_text = """
        <b>Nota Importante:</b> El este nuestro valores es ... (texto legal) ...
        """ 
        # (Usando el texto legal corto por ahora, se puede expandir si el OCR lo permite o usar el genérico)
        note_text = """<b>Nota Importante:</b> Al firmar como "Recibido Conforme", el cliente acepta las políticas de la empresa y certifica que ha recibido la mercancía detallada en este conduce, con los seriales/IMEIs aquí descritos. La mercancía viaja por cuenta y riesgo del comprador."""
        
        story.append(Paragraph(note_text, ParagraphStyle('Note', parent=styles['Normal'], fontSize=7)))
        story.append(Spacer(1, 0.6*inch))

        # Firmas
        sig_data = [
            ["___________________________", "___________________________"],
            ["Despachado por", "RECIBIDO CONFORME Y CONTADO"]
        ]
        t_sigs = Table(sig_data, colWidths=[3*inch, 3*inch])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('LEFTPADDING', (0,0), (-1,-1), 20),
            ('RIGHTPADDING', (0,0), (-1,-1), 20),
        ]))
        story.append(t_sigs)

        doc.build(story)

if __name__ == "__main__":
    app = PDFProcessorApp()
    app.mainloop()
