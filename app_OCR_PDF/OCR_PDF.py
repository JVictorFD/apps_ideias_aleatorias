import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import customtkinter as ctk
import pytesseract
import os
import numpy as np
import re
import sqlite3
from datetime import datetime

# Aponte para o executável do Tesseract no seu sistema
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("System")  # Segue o tema do Windows (Dark/Light)
ctk.set_default_color_theme("blue")

class AppScannerModerno(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Scanner OCR Inteligente - v1.9.0 (CustomTkinter & IA Classifier)")
        self.geometry("900x950")
        
        self.cap = cv2.VideoCapture(0)
        self.pasta_destino = ctk.StringVar(value="")
        
        # Inicializa o Banco de Dados Local
        self.inicializar_banco()
        
        # Estados da aplicação
        self.documento_atual = None
        self.frame_escaneado = None 
        self.exibindo_recorte = False
        self.paginas_pdf_acumuladas = []
        
        # Estados da Animação
        self.animando = False
        self.fase_animacao = 0
        self.linha_scan_y = 0
        self.frame_congelado_anim = None
        
        # --- LAYOUT DA INTERFACE (CustomTkinter) ---
        
        # Topo: Configurações e Tema
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.btn_pasta = ctk.CTkButton(top_frame, text="📁 Selecionar Pasta Base", command=self.escolher_pasta, width=180)
        self.btn_pasta.pack(side=tk.LEFT, padx=5)
        
        self.lbl_pasta = ctk.CTkLabel(top_frame, text="Nenhuma pasta selecionada", text_color="gray")
        self.lbl_pasta.pack(side=tk.LEFT, padx=5)
        
        self.menu_tema = ctk.CTkOptionMenu(top_frame, values=["System", "Dark", "Light"], command=self.mudar_tema, width=100)
        self.menu_tema.pack(side=tk.RIGHT, padx=5)
        self.menu_tema.set("System")

        # Área de Vídeo / Câmera
        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.pack(pady=5)
        
        # Botões de Ação Secundários (Histórico e PDF Multipágina)
        Apoio_frame = ctk.CTkFrame(self, fg_color="transparent")
        Apoio_frame.pack(pady=5, fill=tk.X, padx=20)
        
        self.btn_historico = ctk.CTkButton(Apoio_frame, text="📊 Ver Histórico & Buscar", command=self.abrir_janela_historico, fg_color="#2b78e4", hover_color="#1d5db6")
        self.btn_historico.pack(side=tk.LEFT, expand=True, padx=5, fill=tk.X)
        
        self.btn_pdf = ctk.CTkButton(Apoio_frame, text="📚 Finalizar PDF Multipágina", command=self.finalizar_pdf_multipagina, fg_color="#107c10", hover_color="#0e630e")
        self.btn_pdf.pack(side=tk.LEFT, expand=True, padx=5, fill=tk.X)

        # Botão Principal de Escaneamento
        self.btn_escanear = ctk.CTkButton(
            self, text="🔍 Escanear, Classificar & Salvar [Espaço/Enter]", command=self.acao_escanear, 
            font=("Arial", 14, "bold"), height=50, fg_color="#005fb8", hover_color="#00458c"
        )
        self.btn_escanear.pack(pady=10, padx=20, fill=tk.X)
        
        # Atalhos de Teclado Globais
        self.bind("<space>", lambda event: self.acao_escanear())
        self.bind("<Return>", lambda event: self.acao_escanear())
        
        # Caixa de Texto Inteligente (Regex + Classificação)
        lbl_txt = ctk.CTkLabel(self, text="Dados Extraídos & Classificação por IA:", font=("Arial", 11, "bold"))
        lbl_txt.pack(anchor=tk.W, padx=20)
        
        self.texto_extraido = ctk.CTkTextbox(self, height=140, font=("Consolas", 11))
        self.texto_extraido.pack(pady=2, padx=20, fill=tk.X)

        # Terminal de Logs
        lbl_log = ctk.CTkLabel(self, text="Terminal de Logs do Sistema:", font=("Arial", 11, "bold"))
        lbl_log.pack(anchor=tk.W, padx=20)
        
        self.log_text = ctk.CTkTextbox(self, height=100, font=("Consolas", 10), fg_color="black", text_color="#00ff00")
        self.log_text.pack(pady=2, padx=20, fill=tk.BOTH, expand=True)
        
        self.log("Sistema v1.9.0 inicializado com CustomTkinter e Classificador de IA.")
        self.atualizar_frame()

    def inicializar_banco(self):
        self.conexao = sqlite3.connect("scanner_historico.db")
        self.cursor = self.conexao.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                categoria TEXT,
                caminho_arquivo TEXT,
                resumo_dados TEXT,
                texto_completo TEXT
            )
        """)
        self.conexao.commit()

    def log(self, mensagem):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{hora}] {mensagem}\n")
        self.log_text.see("end")
        self.update_idletasks()

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta base para exportação")
        if pasta:
            self.pasta_destino.set(pasta)
            self.lbl_pasta.configure(text=pasta, text_color="green")
            self.log(f"Pasta configurada: {pasta}")

    def mudar_tema(self, novo_tema):
        ctk.set_appearance_mode(novo_tema)

    def ordenar_pontos(self, pontos):
        pontos = pontos.reshape((4, 2))
        nova_ordem = np.zeros((4, 2), dtype=np.float32)
        soma = pontos.sum(axis=1)
        nova_ordem[0] = pontos[np.argmin(soma)]
        nova_ordem[2] = pontos[np.argmax(soma)]
        diff = np.diff(pontos, axis=1)
        nova_ordem[1] = pontos[np.argmin(diff)]
        nova_ordem[3] = pontos[np.argmax(diff)]
        return nova_ordem

    def exibir_imagem_interface(self, frame_bgr):
        cv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv_img)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def classificar_e_extrair_dados(self, texto):
        """Classifica o documento por regras de IA e extrai dados via Regex"""
        texto_lower = texto.lower()
        
        # Regras Simples de Classificação Baseada em Conteúdo
        if any(termo in texto_lower for termo in ["cnpj", "nf-e", "nota fiscal", "total a pagar", "imposto"]):
            categoria = "Notas_Fiscais"
        elif any(termo in texto_lower for termo in ["contrato", "cláusula", "contratante", "contratada", "foro"]):
            categoria = "Contratos"
        elif any(termo in texto_lower for termo in ["recibo", "recebemos de", "importância de", "referente a"]):
            categoria = "Recibos"
        else:
            categoria = "Documentos_Gerais"

        # Regex para extração de dados
        dados = []
        datas = re.findall(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', texto)
        if datas: dados.append(f"📅 Datas: {', '.join(datas)}")
            
        valores = re.findall(r'(?:R\$?\s?)?\b\d{1,3}(?:\.\d{3})*,\d{2}\b', texto)
        if valores: dados.append(f"💰 Valores: {', '.join(valores)}")
            
        cpfs = re.findall(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', texto)
        if cpfs: dados.append(f"👤 CPFs: {', '.join(cpfs)}")

        resumo_str = " | ".join(dados) if dados else "Nenhum dado estruturado"
        
        formatado = f"🤖 CATEGORIA DETECTADA: [{categoria.upper()}]\n"
        if dados:
            formatado += "--- DADOS IDENTIFICADOS (REGEX) ---\n" + "\n".join(dados) + "\n\n"
        formatado += "--- TEXTO ORIGINAL ---\n" + texto
            
        return formatado, resumo_str, categoria

    def aplicar_filtro_profissional(self, frame_bgr):
        cinza = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        _, limiarizada = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(limiarizada, cv2.COLOR_GRAY2BGR)

    def atualizar_frame(self):
        if self.animando or self.exibindo_recorte:
            self.after(50, self.atualizar_frame)
            return

        ret, frame = self.cap.read()
        if ret:
            cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
            bordas = cv2.Canny(desfoque, 30, 150)
            
            kernel = np.ones((5, 5), np.uint8)
            bordas = cv2.dilate(bordas, kernel, iterations=1)
            bordas = cv2.erode(bordas, kernel, iterations=1)
            
            contornos, _ = cv2.findContours(bordas, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contornos = sorted(contornos, key=cv2.contourArea, reverse=True)[:5]
            
            self.documento_atual = None
            
            for contorno in contornos:
                if cv2.contourArea(contorno) > 15000: 
                    perimetro = cv2.arcLength(contorno, True)
                    aproximacao = cv2.approxPolyDP(contorno, 0.04 * perimetro, True)
                    
                    if len(aproximacao) == 4:
                        self.documento_atual = aproximacao
                        cv2.drawContours(frame, [aproximacao], -1, (0, 255, 0), 2)
                        break

            frame_visual = cv2.resize(frame, (480, 360))
            self.exibir_imagem_interface(frame_visual)
            
        self.after(15, self.atualizar_frame)

    def acao_escanear(self):
        if not self.pasta_destino.get():
            self.escolher_pasta()
            if not self.pasta_destino.get():
                return messagebox.showwarning("Aviso", "Selecione uma pasta de destino.")

        if self.documento_atual is None:
            self.log("ERRO: Nenhum papel detectado na câmera.")
            return messagebox.showwarning("Aviso", "Aguarde o contorno verde aparecer.")
        
        self.btn_escanear.configure(state="disabled", fg_color="gray", text="⏳ Processando IA & Classificando...")
        self.iniciar_animacao_scan()

    def iniciar_animacao_scan(self):
        ret, frame_original = self.cap.read()
        if not ret: return
        
        pontos_doc = self.ordenar_pontos(self.documento_atual)
        (tl, tr, br, bl) = pontos_doc
        
        larguraA = np.linalg.norm(br - bl)
        larguraB = np.linalg.norm(tr - tl)
        max_largura = max(int(larguraA), int(larguraB))
        
        alturaA = np.linalg.norm(tr - br)
        alturaB = np.linalg.norm(tl - bl)
        max_altura = max(int(alturaA), int(alturaB))
        
        pontos_destino = np.array([[0, 0], [max_largura - 1, 0], [max_largura - 1, max_altura - 1], [0, max_altura - 1]], dtype="float32")
        matriz = cv2.getPerspectiveTransform(pontos_doc, pontos_destino)
        
        frame_recortado_bruto = cv2.warpPerspective(frame_original, matriz, (max_largura, max_altura))
        self.frame_escaneado = self.aplicar_filtro_profissional(frame_recortado_bruto)
        
        h_rec, w_rec = self.frame_escaneado.shape[:2]
        proporcao = min(480 / w_rec, 360 / h_rec)
        novo_w, novo_h = int(w_rec * proporcao), int(h_rec * proporcao)
        frame_zoom = cv2.resize(self.frame_escaneado, (novo_w, novo_h))
        
        fundo = np.zeros((360, 480, 3), dtype=np.uint8)
        y_off, x_off = (360 - novo_h) // 2, (480 - novo_w) // 2
        fundo[y_off:y_off+novo_h, x_off:x_off+novo_w] = frame_zoom
        
        self.frame_congelado_anim = fundo
        self.animando = True
        self.fase_animacao = y_off
        self.linha_scan_y = novo_h 
        
        self.executar_animacao()

    def executar_animacao(self):
        frame_animado = self.frame_congelado_anim.copy()
        y_atual = self.fase_animacao
        
        cv2.line(frame_animado, (0, y_atual), (480, y_atual), (0, 255, 0), 3)
        overlay = frame_animado.copy()
        cv2.rectangle(overlay, (0, 0), (480, y_atual), (0, 50, 0), -1)
        frame_animado = cv2.addWeighted(overlay, 0.3, frame_animado, 0.7, 0)
        
        self.exibir_imagem_interface(frame_animado)
        self.fase_animacao += 15 
        
        if self.fase_animacao >= (360 - (360 - self.linha_scan_y) // 2):
            self.animando = False
            self.exibindo_recorte = True
            self.exibir_imagem_interface(self.frame_congelado_anim)
            self.realizar_ocr_e_salvar_bd()
        else:
            self.after(20, self.executar_animacao)

    def realizar_ocr_e_salvar_bd(self):
        self.log("Executando OCR e Classificação Inteligente...")
        self.update_idletasks()
        
        try:
            texto_bruto = pytesseract.image_to_string(self.frame_escaneado, lang='por').strip()
            texto_formatado, resumo_regex, categoria = self.classificar_e_extrair_dados(texto_bruto)
            
            self.texto_extraido.delete("0.0", "end")
            self.texto_extraido.insert("0.0", texto_formatado)
            
            # Cria subpasta automática baseada na categoria da IA
            pasta_base = self.pasta_destino.get()
            pasta_categoria = os.path.join(pasta_base, categoria)
            os.makedirs(pasta_categoria, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_base = f"scan_{timestamp}"
            
            caminho_txt = os.path.join(pasta_categoria, f"{nome_base}.txt")
            caminho_img = os.path.join(pasta_categoria, f"{nome_base}.png")
            
            with open(caminho_txt, 'w', encoding='utf-8') as f:
                f.write(texto_formatado)
            cv2.imwrite(caminho_img, self.frame_escaneado)
            
            img_rgb = cv2.cvtColor(self.frame_escaneado, cv2.COLOR_BGR2RGB)
            self.paginas_pdf_acumuladas.append(Image.fromarray(img_rgb).convert("RGB"))
            
            data_hora_atual = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            self.cursor.execute(
                "INSERT INTO historico (data_hora, categoria, caminho_arquivo, resumo_dados, texto_completo) VALUES (?, ?, ?, ?, ?)",
                (data_hora_atual, categoria, caminho_txt, resumo_regex, texto_formatado)
            )
            self.conexao.commit()
            
            self.log(f"💾 Salvo na categoria [{categoria}] com IA!")
            self.log("Retornando à câmera em 2 segundos...")
            self.after(2000, self.voltar_camera)
            
        except Exception as e:
            self.log(f"ERRO: {e}")
            self.voltar_camera()

    def finalizar_pdf_multipagina(self):
        if not self.paginas_pdf_acumuladas:
            return messagebox.showwarning("Aviso", "Nenhuma página foi escaneada nesta sessão ainda.")
            
        pasta = self.pasta_destino.get()
        if not pasta:
            pasta = filedialog.askdirectory(title="Selecione onde salvar o PDF unificado")
            if not pasta: return
            self.pasta_destino.set(pasta)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        caminho_pdf = os.path.join(pasta, f"documento_completo_{timestamp}.pdf")
        
        try:
            primeira_pagina = self.paginas_pdf_acumuladas[0]
            demais_paginas = self.paginas_pdf_acumuladas[1:]
            
            primeira_pagina.save(
                caminho_pdf, "PDF", resolution=150.0, save_all=True, append_images=demais_paginas
            )
            self.log(f"📚 PDF Multipágina gerado: {caminho_pdf}")
            messagebox.showinfo("Sucesso", f"PDF unificado gerado com {len(self.paginas_pdf_acumuladas)} página(s)!\n{caminho_pdf}")
            self.paginas_pdf_acumuladas = []
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar PDF multipágina: {e}")

    def abrir_janela_historico(self):
        janela_hist = ctk.CTkToplevel(self)
        janela_hist.title("Histórico de Scans & Busca Inteligente")
        janela_hist.geometry("850x520")
        
        lbl = ctk.CTkLabel(janela_hist, text="Consultar Banco de Dados Local", font=("Arial", 14, "bold"))
        lbl.pack(pady=10)
        
        busca_frame = ctk.CTkFrame(janela_hist, fg_color="transparent")
        busca_frame.pack(fill=tk.X, padx=15, pady=5)
        
        lbl_busca = ctk.CTkLabel(busca_frame, text="🔍 Filtrar por Categoria, Data ou Valor:")
        lbl_busca.pack(side=tk.LEFT, padx=5)
        
        entrada_busca = ctk.CTkEntry(busca_frame, width=350)
        entrada_busca.pack(side=tk.LEFT, padx=5)
        
        # Tabela Treeview
        colunas = ("ID", "Data/Hora", "Categoria", "Resumo Regex", "Arquivo TXT")
        tabela = ttk.Treeview(janela_hist, columns=colunas, show="headings", height=15)
        
        tabela.heading("ID", text="ID")
        tabela.heading("Data/Hora", text="Data/Hora")
        tabela.heading("Categoria", text="Categoria")
        tabela.heading("Resumo Regex", text="Resumo Regex")
        tabela.heading("Arquivo TXT", text="Caminho do Arquivo")
        
        tabela.column("ID", width=40, anchor=tk.CENTER)
        tabela.column("Data/Hora", width=120, anchor=tk.CENTER)
        tabela.column("Categoria", width=110, anchor=tk.CENTER)
        tabela.column("Resumo Regex", width=220, anchor=tk.W)
        tabela.column("Arquivo TXT", width=240, anchor=tk.W)
        tabela.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        def carregar_dados(filtro=""):
            for row in tabela.get_children():
                tabela.delete(row)
            
            if filtro:
                query = "SELECT id, data_hora, categoria, resumo_dados, caminho_arquivo FROM historico WHERE categoria LIKE ? OR resumo_dados LIKE ? OR texto_completo LIKE ? ORDER BY id DESC"
                self.cursor.execute(query, (f"%{filtro}%", f"%{filtro}%", f"%{filtro}%"))
            else:
                self.cursor.execute("SELECT id, data_hora, categoria, resumo_dados, caminho_arquivo FROM historico ORDER BY id DESC")
                
            for reg in self.cursor.fetchall():
                tabela.insert("", tk.END, values=reg)

        entrada_busca.bind("<KeyRelease>", lambda event: carregar_dados(entrada_busca.get()))
        carregar_dados()
        
        btn_fechar = ctk.CTkButton(janela_hist, text="Fechar", command=janela_hist.destroy, width=120)
        btn_fechar.pack(pady=10)

    def voltar_camera(self):
        self.exibindo_recorte = False
        self.documento_atual = None
        self.btn_escanear.configure(state="normal", fg_color="#005fb8", text="🔍 Escanear, Classificar & Salvar [Espaço/Enter]")
        self.log("📸 Câmera pronta para o próximo scan!")

if __name__ == "__main__":
    app = AppScannerModerno()
    app.mainloop()