import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from PIL import Image, ImageTk
import pytesseract
import os
import numpy as np
import re
import sqlite3
from datetime import datetime

# Aponte para o executável do Tesseract no seu sistema
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class AppScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner OCR - v1.8.0 (Pro Features & Multi-PDF)")
        self.root.geometry("850x980") 
        
        self.cap = cv2.VideoCapture(0)
        self.pasta_destino = tk.StringVar()
        
        # Inicializa o Banco de Dados Local
        self.inicializar_banco()
        
        # Estados da aplicação
        self.documento_atual = None
        self.frame_escaneado = None 
        self.exibindo_recorte = False
        self.paginas_pdf_acumuladas = [] # Lista para acumular páginas do PDF multipágina
        
        # Estados da Animação
        self.animando = False
        self.fase_animacao = 0
        self.linha_scan_y = 0
        self.frame_congelado_anim = None
        
        # 1. Área do vídeo 
        self.video_label = tk.Label(root)
        self.video_label.pack(pady=5)
        
        # 2. Pasta de Destino e Botões de Acesso
        opcoes_frame = tk.Frame(root)
        opcoes_frame.pack(pady=5, fill=tk.X, padx=20)
        
        tk.Label(opcoes_frame, text="Pasta:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(opcoes_frame, textvariable=self.pasta_destino, state='readonly', width=28).pack(side=tk.LEFT, padx=5)
        tk.Button(opcoes_frame, text="Procurar", command=self.escolher_pasta).pack(side=tk.LEFT, padx=2)
        tk.Button(opcoes_frame, text="📊 Histórico", command=self.abrir_janela_historico, bg="lightyellow", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(opcoes_frame, text="📚 Finalizar PDF Único", command=self.finalizar_pdf_multipagina, bg="lightgreen", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=4)
        
        # 3. Painel de Ação Principal
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        self.btn_escanear = tk.Button(
            btn_frame, text="🔍 Escanear & Salvar [Espaço/Enter]", command=self.acao_escanear, 
            bg="lightblue", font=("Arial", 12, "bold"), width=42, height=2
        )
        self.btn_escanear.pack(pady=2)
        
        # Vincula atalhos de teclado globais (Espaço e Enter)
        self.root.bind("<space>", lambda event: self.acao_escanear())
        self.root.bind("<Return>", lambda event: self.acao_escanear())
        
        # 4. Caixa de texto e Logs
        tk.Label(root, text="Dados Extraídos (Regex + Texto Bruto):").pack()
        self.texto_extraido = scrolledtext.ScrolledText(root, height=6, width=78, font=("Arial", 9))
        self.texto_extraido.pack(pady=2)

        tk.Label(root, text="Terminal de Logs:").pack()
        self.log_text = scrolledtext.ScrolledText(root, height=5, bg="black", fg="lightgreen", font=("Consolas", 9))
        self.log_text.pack(pady=2, padx=20, fill=tk.BOTH, expand=True)
        
        self.log("Sistema v1.8.0 iniciado. Use [Espaço] ou [Enter] para escanear rapidamente.")
        self.atualizar_frame()

    def inicializar_banco(self):
        self.conexao = sqlite3.connect("scanner_historico.db")
        self.cursor = self.conexao.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                caminho_arquivo TEXT,
                resumo_dados TEXT,
                texto_completo TEXT
            )
        """)
        self.conexao.commit()

    def log(self, mensagem):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{hora}] {mensagem}\n")
        self.log_text.see(tk.END) 
        self.root.update()        

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para exportação")
        if pasta:
            self.pasta_destino.set(pasta)
            self.log(f"Pasta configurada: {pasta}")

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

    def extrair_dados_inteligentes(self, texto):
        dados = []
        datas = re.findall(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', texto)
        if datas: dados.append(f"📅 Datas: {', '.join(datas)}")
            
        valores = re.findall(r'(?:R\$?\s?)?\b\d{1,3}(?:\.\d{3})*,\d{2}\b', texto)
        if valores: dados.append(f"💰 Valores: {', '.join(valores)}")
            
        cpfs = re.findall(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', texto)
        if cpfs: dados.append(f"👤 CPFs: {', '.join(cpfs)}")

        resumo_str = " | ".join(dados) if dados else "Nenhum dado estruturado"
        
        if dados:
            formatado = "--- DADOS IDENTIFICADOS (REGEX) ---\n" + "\n".join(dados) + "\n\n--- TEXTO ORIGINAL ---\n" + texto
        else:
            formatado = "--- NENHUM DADO ESTRUTURADO IDENTIFICADO ---\n\n--- TEXTO ORIGINAL ---\n" + texto
            
        return formatado, resumo_str

    def aplicar_filtro_profissional(self, frame_bgr):
        """Aplica limiarização adaptativa para remover sombras e deixar o fundo branco profissional"""
        cinza = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        # Limiarização Otsu para realçar o texto e limpar o fundo
        _, limiarizada = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(limiarizada, cv2.COLOR_GRAY2BGR)

    def atualizar_frame(self):
        if self.animando or self.exibindo_recorte:
            self.root.after(50, self.atualizar_frame)
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
            
        self.root.after(15, self.atualizar_frame)

    def acao_escanear(self):
        if not self.pasta_destino.get():
            self.escolher_pasta()
            if not self.pasta_destino.get():
                return messagebox.showwarning("Aviso", "Selecione uma pasta de destino.")

        if self.documento_atual is None:
            self.log("ERRO: Nenhum papel detectado na câmera.")
            return messagebox.showwarning("Aviso", "Aguarde o contorno verde aparecer.")
        
        self.btn_escanear.config(state=tk.DISABLED, bg="lightgray", text="⏳ Processando & Salvando...")
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
        
        # Aplica o Filtro Profissional (Limiarização Otsu)
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
            self.root.after(20, self.executar_animacao)

    def realizar_ocr_e_salvar_bd(self):
        self.log("Lendo OCR otimizado, salvando arquivos e acumulando página...")
        self.root.update()
        
        try:
            # Como a imagem já está limpa pelo filtro profissional, mandamos direto para o OCR
            texto_bruto = pytesseract.image_to_string(self.frame_escaneado, lang='por').strip()
            texto_formatado, resumo_regex = self.extrair_dados_inteligentes(texto_bruto)
            
            self.texto_extraido.delete(1.0, tk.END)
            self.texto_extraido.insert(tk.END, texto_formatado)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_base = f"scan_{timestamp}"
            pasta = self.pasta_destino.get()
            
            caminho_txt = os.path.join(pasta, f"{nome_base}.txt")
            caminho_img = os.path.join(pasta, f"{nome_base}.png")
            
            with open(caminho_txt, 'w', encoding='utf-8') as f:
                f.write(texto_formatado)
            cv2.imwrite(caminho_img, self.frame_escaneado)
            
            # Adiciona a página atual na lista para o PDF Multipágina
            img_rgb = cv2.cvtColor(self.frame_escaneado, cv2.COLOR_BGR2RGB)
            self.paginas_pdf_acumuladas.append(Image.fromarray(img_rgb).convert("RGB"))
            
            # Registra no SQLite
            data_hora_atual = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            self.cursor.execute(
                "INSERT INTO historico (data_hora, caminho_arquivo, resumo_dados, texto_completo) VALUES (?, ?, ?, ?)",
                (data_hora_atual, caminho_txt, resumo_regex, texto_formatado)
            )
            self.conexao.commit()
            
            self.log(f"💾 Página processada e acumulada na pilha de PDF!")
            self.log("Retornando à câmera em 2 segundos...")
            self.root.after(2000, self.voltar_camera)
            
        except Exception as e:
            self.log(f"ERRO: {e}")
            self.voltar_camera()

    def finalizar_pdf_multipagina(self):
        """Consolida todas as páginas escaneadas em um único PDF multipágina"""
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
            self.log(f"📚 PDF Multipágina gerado com sucesso: {caminho_pdf}")
            messagebox.showinfo("Sucesso", f"PDF unificado gerado com {len(self.paginas_pdf_acumuladas)} página(s)!\n{caminho_pdf}")
            
            # Limpa a pilha após salvar
            self.paginas_pdf_acumuladas = []
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar PDF multipágina: {e}")

    def abrir_janela_historico(self):
        """Abre a janela de histórico com suporte a filtro de busca em tempo real"""
        janela_hist = tk.Toplevel(self.root)
        janela_hist.title("Histórico de Scans (SQLite com Filtro)")
        janela_hist.geometry("800x500")
        
        tk.Label(janela_hist, text="Consultar Banco de Dados Local", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Barra de Pesquisa em Tempo Real
        busca_frame = tk.Frame(janela_hist)
        busca_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(busca_frame, text="🔍 Filtrar (Data, CPF ou Valor):").pack(side=tk.LEFT)
        
        entrada_busca = tk.Entry(busca_frame, width=40)
        entrada_busca.pack(side=tk.LEFT, padx=5)
        
        # Tabela Treeview
        colunas = ("ID", "Data/Hora", "Resumo Regex", "Arquivo TXT")
        tabela = ttk.Treeview(janela_hist, columns=colunas, show="headings", height=15)
        
        tabela.heading("ID", text="ID")
        tabela.heading("Data/Hora", text="Data/Hora")
        tabela.heading("Resumo Regex", text="Resumo Regex")
        tabela.heading("Arquivo TXT", text="Caminho do Arquivo")
        
        tabela.column("ID", width=40, anchor=tk.CENTER)
        tabela.column("Data/Hora", width=130, anchor=tk.CENTER)
        tabela.column("Resumo Regex", width=270, anchor=tk.W)
        tabela.column("Arquivo TXT", width=280, anchor=tk.W)
        tabela.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def carregar_dados(filtro=""):
            for row in tabela.get_children():
                tabela.delete(row)
            
            if filtro:
                query = "SELECT id, data_hora, resumo_dados, caminho_arquivo FROM historico WHERE resumo_dados LIKE ? OR texto_completo LIKE ? ORDER BY id DESC"
                self.cursor.execute(query, (f"%{filtro}%", f"%{filtro}%"))
            else:
                self.cursor.execute("SELECT id, data_hora, resumo_dados, caminho_arquivo FROM historico ORDER BY id DESC")
                
            for reg in self.cursor.fetchall():
                tabela.insert("", tk.END, values=reg)

        # Vincula a digitação na barra de busca para atualizar a tabela instantaneamente
        entrada_busca.bind("<KeyRelease>", lambda event: carregar_dados(entrada_busca.get()))
        
        # Carrega todos inicialmente
        carregar_dados()
        
        tk.Button(janela_hist, text="Fechar", command=janela_hist.destroy, width=15, bg="lightgray").pack(pady=10)

    def voltar_camera(self):
        self.exibindo_recorte = False
        self.documento_atual = None
        self.btn_escanear.config(state=tk.NORMAL, bg="lightblue", text="🔍 Escanear & Salvar [Espaço/Enter]")
        self.log("📸 Câmera pronta para o próximo scan!")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppScanner(root)
    root.mainloop()