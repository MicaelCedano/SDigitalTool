
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os
import platform
import shutil
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import re

# --- Configuración y Constantes ---
OUTPUT_FILE = 'recibo_garantia.pdf'
CONFIG_FILE = 'garantia_config.txt'
HISTORY_DIR = 'historial_recibos'

# Default Terms from image
DEFAULT_TERMS = """
La garantía quedará anulada en los siguientes casos:

Si el equipo presenta daños físicos, como pantallas rotas, golpes, humedad o cualquier señal de mal uso.

Si el cliente ha provocado daños intencionales o negligentes al dispositivo.

Si no se entrega el equipo con todos sus accesorios originales y en las condiciones en que fue entregado.

Agradecemos su comprensión y cumplimiento con estas condiciones para ofrecerle un mejor servicio.
"""

# Default Header Info from image
DEFAULT_ADDRESS = "Calle Duarte, Esq Dr Ferry #54\nSucursal La Romana\nRNC: 132872975"
DEFAULT_STORE = "ANGELO"

class GarantiaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Ventana ---
        self.title("Generador de Recibo de Garantía")
        self.geometry("900x850")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.logo_path = ""
        self.items_data = [] # Lista de diccionarios: [{'Cantidad': 1, 'Modelo': 'X', 'Imeis': '...'}]

        # --- FRAME 1: CONFIGURACIÓN (Logo, Tienda, Address) ---
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)

        # Logo
        self.select_logo_button = ctk.CTkButton(config_frame, text="Seleccionar Logo", command=self.select_logo_file)
        self.select_logo_button.grid(row=0, column=0, padx=20, pady=10)
        self.logo_path_label = ctk.CTkLabel(config_frame, text="Sin logo", text_color="gray")
        self.logo_path_label.grid(row=0, column=1, padx=20, pady=10, sticky="w")

        # Tienda
        ctk.CTkLabel(config_frame, text="Tienda:").grid(row=1, column=0, padx=20, pady=5, sticky="e")
        self.store_entry = ctk.CTkEntry(config_frame, width=300)
        self.store_entry.insert(0, DEFAULT_STORE)
        self.store_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # --- FRAME 2: DATOS DEL CLIENTE ---
        client_frame = ctk.CTkFrame(self)
        client_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        client_frame.grid_columnconfigure(1, weight=1)

        # ctk.CTkLabel(client_frame, text="Nombre Cliente:").grid(row=0, column=0, padx=20, pady=10, sticky="e")
        # self.client_entry = ctk.CTkEntry(client_frame, placeholder_text="Nombre del cliente...")
        # self.client_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(client_frame, text="Fecha:").grid(row=0, column=0, padx=20, pady=10, sticky="e")
        self.date_entry = ctk.CTkEntry(client_frame, width=120)
        self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.date_entry.grid(row=0, column=1, padx=20, pady=10, sticky="w")

        # --- FRAME 3: LISTA DE PRODUCTOS (Treeview) ---
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", foreground="white", fieldbackground="#2a2d2e", borderwidth=0, font=('Arial', 14), rowheight=35)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", font=('Arial', 16, 'bold'))

        self.tree = ttk.Treeview(list_frame, columns=("Cantidad", "Modelo", "HasIMEIs"), show="headings", selectmode="browse")
        self.tree.heading("Cantidad", text="Cantidad")
        self.tree.heading("Modelo", text="Modelo")
        self.tree.heading("HasIMEIs", text="¿Tiene IMEIs?")
        self.tree.column("Cantidad", width=100, anchor="center")
        self.tree.column("Modelo", width=400)
        self.tree.column("HasIMEIs", width=100, anchor="center")
        
        self.tree.grid(row=0, column=0, sticky="nsew")

        # --- BOTONES ACCIONES ---
        btns_frame = ctk.CTkFrame(list_frame)
        btns_frame.grid(row=1, column=0, sticky="ew", pady=(5,0))
        btns_frame.grid_columnconfigure(5, weight=1) # Spacer

        self.add_btn = ctk.CTkButton(btns_frame, text="Añadir Modelo", command=self.add_row, fg_color="#186A3B", hover_color="#145A32")
        self.add_btn.grid(row=0, column=0, padx=5, pady=5)

        self.edit_btn = ctk.CTkButton(btns_frame, text="Editar", command=self.edit_row)
        self.edit_btn.grid(row=0, column=1, padx=5, pady=5)

        self.del_btn = ctk.CTkButton(btns_frame, text="Eliminar", command=self.delete_row, fg_color="#c42b1c", hover_color="#8a1f16")
        self.del_btn.grid(row=0, column=2, padx=5, pady=5)

        # --- FRAME 4: GENERAR ---
        gen_frame = ctk.CTkFrame(self)
        gen_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.gen_btn = ctk.CTkButton(gen_frame, text="GENERAR RECIBO DE GARANTÍA", command=self.generate_pdf, height=50, font=("Arial", 16, "bold"))
        self.gen_btn.pack(fill="x", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(self, text="Listo", text_color="cyan")
        self.status_label.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    path = f.read().strip()
                if os.path.exists(path):
                    self.logo_path = path
                    self.logo_path_label.configure(text=f"Logo: {os.path.basename(path)}", text_color="white")
            except: pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            f.write(self.logo_path)

    def select_logo_file(self):
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
        if path:
            self.logo_path = path
            self.logo_path_label.configure(text=f"Logo: {os.path.basename(path)}", text_color="white")
            self.save_config()

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.items_data:
            has_imeis = "SÍ" if item.get('Imeis', '').strip() else "NO"
            self.tree.insert("", "end", values=(item['Cantidad'], item['Modelo'], has_imeis))

    def add_row(self):
        if hasattr(self, 'add_win') and self.add_win is not None and self.add_win.winfo_exists():
            self.add_win.lift()
            self.add_win.focus_force()
            return

        self.add_win = ctk.CTkToplevel(self)
        self.add_win.title("Añadir Modelo")
        self.add_win.geometry("500x550")
        self.add_win.attributes('-topmost', True) 
        
        ctk.CTkLabel(self.add_win, text="Modelo:").pack(pady=5)
        entry_model = ctk.CTkEntry(self.add_win, width=300)
        entry_model.pack(pady=5)
        entry_model.focus()

        ctk.CTkLabel(self.add_win, text="IMEIs / Seriales (Uno por línea):").pack(pady=5)
        text_imeis = ctk.CTkTextbox(self.add_win, width=400, height=200)
        text_imeis.pack(pady=5)
        
        lbl_qty = ctk.CTkLabel(self.add_win, text="Cantidad: 1 (Por defecto)", text_color="cyan")
        lbl_qty.pack(pady=5)

        def update_qty(event=None):
            content = text_imeis.get("0.0", "end").strip()
            # Split by newlines, commas, or spaces (handling multiple separators)
            parts = [x for x in re.split(r'[,\n\s]+', content) if x]
            count = len(parts)
            if count == 0:
                lbl_qty.configure(text="Cantidad: 1 (Por defecto)")
            else:
                lbl_qty.configure(text=f"Cantidad: {count}")

        text_imeis.bind('<KeyRelease>', update_qty)
        
        status_lbl = ctk.CTkLabel(self.add_win, text="", text_color="green")
        status_lbl.pack(pady=5)

        def save(close_after=False):
            m = entry_model.get().strip()
            imeis_content = text_imeis.get("0.0", "end").strip()
            
            if not m:
                status_lbl.configure(text="Error: Modelo vacío", text_color="red")
                return
            
            # Robust splitting
            parts = [x.strip() for x in re.split(r'[,\n\s]+', imeis_content) if x.strip()]
            q = len(parts)
            if q == 0: q = 1 
            
            final_imeis = "\n".join(parts)
            
            self.items_data.append({'Modelo': m, 'Cantidad': q, 'Imeis': final_imeis})
            self.refresh_tree()
            
            # Limpiar campos
            entry_model.delete(0, 'end')
            text_imeis.delete("0.0", "end")
            update_qty()
            entry_model.focus()
            
            if close_after:
                self.add_win.destroy()
                self.add_win = None
            else:
                status_lbl.configure(text=f"Agregado: {m}", text_color="green")

        # Botones
        btn_frame = ctk.CTkFrame(self.add_win, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Guardar y Seguir", command=lambda: save(close_after=False)).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="Guardar y Cerrar", command=lambda: save(close_after=True), fg_color="#186A3B").grid(row=0, column=1, padx=5)


    def edit_row(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        item = self.items_data[idx]

        win = ctk.CTkToplevel(self)
        win.title("Editar Modelo")
        win.geometry("500x550")
        
        ctk.CTkLabel(win, text="Modelo:").pack(pady=5)
        entry_model = ctk.CTkEntry(win, width=300)
        entry_model.insert(0, item['Modelo'])
        entry_model.pack(pady=5)

        ctk.CTkLabel(win, text="IMEIs / Seriales:").pack(pady=5)
        text_imeis = ctk.CTkTextbox(win, width=400, height=200)
        text_imeis.pack(pady=5)
        if item.get('Imeis'):
            text_imeis.insert("0.0", item['Imeis'])

        lbl_qty = ctk.CTkLabel(win, text=f"Cantidad: {item['Cantidad']}", text_color="cyan")
        lbl_qty.pack(pady=5)

        def update_qty(event=None):
            content = text_imeis.get("0.0", "end").strip()
            parts = [x for x in re.split(r'[,\n\s]+', content) if x]
            count = len(parts)
            if count == 0:
                lbl_qty.configure(text="Cantidad: 1 (Por defecto)")
            else:
                lbl_qty.configure(text=f"Cantidad: {count}")

        text_imeis.bind('<KeyRelease>', update_qty)

        def save():
            item['Modelo'] = entry_model.get().strip()
            
            content = text_imeis.get("0.0", "end").strip()
            parts = [x.strip() for x in re.split(r'[,\n\s]+', content) if x.strip()]
            q = len(parts)
            if q == 0: q = 1
            
            item['Cantidad'] = q
            item['Imeis'] = "\n".join(parts)
            
            self.refresh_tree()
            win.destroy()

        ctk.CTkButton(win, text="Guardar Cambios", command=save, fg_color="#186A3B").pack(pady=20)

    def delete_row(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        self.items_data.pop(idx)
        self.refresh_tree()



    def generate_pdf(self):
        if not self.items_data:
            messagebox.showwarning("Error", "No hay items para generar.")
            return
        
        store = self.store_entry.get().strip()
        date_str = self.date_entry.get().strip()

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="Recibo_Garantia.pdf")
        if not file_path: return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter, leftMargin=0.4*inch, rightMargin=0.4*inch, topMargin=0.4*inch, bottomMargin=0.2*inch)
            styles = getSampleStyleSheet()
            story = []

            # --- HEADER (GRID LAYOUT) ---
            # Col 1: Logo, Col 2: Info Dirección
            
            # Prepare Logo
            logo_obj = Paragraph("", styles["Normal"])
            if self.logo_path and os.path.exists(self.logo_path):
                img = ImageReader(self.logo_path)
                w, h = img.getSize()
                aspect = h / float(w)
                logo_obj = Image(self.logo_path, width=1.5*inch, height=1.5*inch*aspect, hAlign='LEFT')

            # Prepare Address Text
            style_right = ParagraphStyle('Right', parent=styles['Normal'], alignment=0, leading=14, fontSize=10, textColor=colors.black)
            address_text = DEFAULT_ADDRESS.replace("\n", "<br/>")
            address_para = Paragraph(address_text, style_right)

            header_data = [[logo_obj, address_para]]
            t_header = Table(header_data, colWidths=[4*inch, 3.5*inch])
            t_header.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (1,0), (1,0), 'RIGHT'), # Alineamos el texto a la derecha? No, el bloque a la derecha, pero el texto interno está align=0 left. 
                # El screenshot pone el texto a la derecha de la pagina.
            ]))
            story.append(t_header)
            story.append(Spacer(1, 0.2*inch))

            # --- TITULO PRINCIPAL ---
            title_style = ParagraphStyle('TitleGarantia', parent=styles['h1'], fontSize=24, textColor=colors.navy, spaceAfter=2)
            story.append(Paragraph("RECIBO DE GARANTIA", title_style))
            
            # --- FECHA ---
            date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=12, textColor=colors.deeppink, spaceAfter=5, fontName='Helvetica-Bold')
            story.append(Paragraph(f"Fecha:  {date_str}", date_style))

            # --- TIENDA ---
            store_style = ParagraphStyle('StoreStyle', parent=styles['Normal'], fontSize=12, textColor=colors.black, spaceAfter=10, fontName='Helvetica-Bold')
            story.append(Paragraph(f"Tienda: {store}", store_style))

            # if client:
            #     story.append(Paragraph(f"<b>Cliente:</b> {client}", styles['Normal']))
            #     story.append(Spacer(1, 0.2*inch))

            # --- TABLA ITEMS ---
            # Si tiene IMEIs, los mostramos debajo del modelo
            
            data_rows = []
            # Header
            data_rows.append(['CANT', 'DESCRIPCIÓN'])
            
            # Items
            style_item = ParagraphStyle('Item', parent=styles['Normal'], fontSize=14, leading=16)
            style_imei_list = ParagraphStyle('ImeiList', parent=styles['Normal'], fontSize=12, leading=14, textColor=colors.black)

            total_cant = 0
            for item in self.items_data:
                desc = f"<b>{item['Modelo']}</b>"
                if item.get('Imeis'):
                    # Limpiar y formatear IMEIs
                    raw_imeis = item['Imeis'].replace('\n', ', ')
                    # Usamos tamano 12 para que se vea bien, acorde a lo pedido
                    desc += f"<br/><font size=12>{raw_imeis}</font>"
                
                qty = item['Cantidad']
                total_cant += int(qty)
                data_rows.append([str(qty), Paragraph(desc, style_item)])

            # Fila de Total
            style_center = ParagraphStyle('ItemCenter', parent=style_item, alignment=1)
            data_rows.append([Paragraph(f"<b>{total_cant}</b>", style_center), Paragraph("<b>TOTAL EQUIPOS</b>", style_item)])

            t_items = Table(data_rows, colWidths=[1*inch, 6.5*inch])
            t_items.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (0,-1), 'CENTER'), # Cantidad centrada
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(t_items)
            story.append(Spacer(1, 0.2*inch))

            # --- TERMS ---
            terms_style = ParagraphStyle('Terms', parent=styles['Normal'], fontSize=8, leading=10)
            # Reemplazar saltos de linea simples por <br/>
            formatted_terms = DEFAULT_TERMS.replace("\n", "<br/>")
            story.append(Paragraph(formatted_terms, terms_style))
            
            story.append(Spacer(1, 0.4*inch))

            # --- FIRMA ---
            sig_style = ParagraphStyle('Sig', parent=styles['Normal'], alignment=1, textColor=colors.deeppink, fontSize=12)
            story.append(Paragraph("___________________________________", ParagraphStyle('Line', alignment=1)))
            story.append(Paragraph("Firma", sig_style))

            doc.build(story)

            # --- SAVE TO HISTORY ---
            try:
                if not os.path.exists(HISTORY_DIR):
                    os.makedirs(HISTORY_DIR)
                
                # Create a filename safe for filesystem
                safe_store = "".join([c for c in store if c.isalnum() or c in (' ', '_', '-')]).strip()
                if not safe_store: safe_store = "SinTienda"
                
                # Timestamp for uniqueness
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                history_filename = f"Recibo_{safe_store}_{timestamp}.pdf"
                history_path = os.path.join(HISTORY_DIR, history_filename)
                
                shutil.copy(file_path, history_path)
            except Exception as e:
                print(f"No se pudo guardar en historial: {e}")
            
            if messagebox.askyesno("Generado", f"PDF Guardado: {os.path.basename(file_path)}\n¿Abrir ahora?"):
                if platform.system() == "Windows": os.startfile(file_path)
                else: os.system(f'xdg-open "{file_path}"')
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar PDF: {e}")

if __name__ == "__main__":
    app = GarantiaApp()
    app.mainloop()
