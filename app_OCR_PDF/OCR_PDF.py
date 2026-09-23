import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import pytesseract
from docx import Document
import os
import numpy as np
import math
from datetime import datetime

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class AppScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner OCR - V1 (Crop Interativo & Zoom)")
        self.root.geometry("750x950") 
        
        self.cap = cv2.VideoCapture(0)
        self.pasta_destino = tk.StringVar()
        
        # Estados da aplicação
        self.documento_atual = None
        self.frame_escaneado = None 
        self.frame_alta_resolucao = None
        
        # Controle de Interface
        self.modo_ajuste = False
        self.exibindo_recorte = False
        
        # Variáveis do Ajuste Manual
        self.frame_congelado = None
        self.pontos_visuais = None
        self.indice_arrastado = None
        self.fator_escala_x = 1.0
        self.fator_escala_y = 1.0
        
        # 1. Área do vídeo com eventos de Mouse vinculados
        self.video_label = tk.Label(root, cursor="crosshair")
        self.video_label.pack(pady=5)
        
        self.video_label.bind("<Button-1>", self.iniciar_arraste)
        self.video_label.bind("<B1-Motion>", self.arrastar)
        self.video_label.bind("<ButtonRelease-1>", self.parar_arraste)
        
        # 2. Frame de Opções 
        opcoes_frame = tk.Frame(root)
        opcoes_frame.pack(pady=5, fill=tk.X, padx=20)
        
        self.salvar_foto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opcoes_frame, text="Salvar foto recortada junto com o documento", 
            variable=self.salvar_foto_var, font=("Arial", 10, "bold"), fg="darkblue"
        ).pack(anchor=tk.W)
        
        dir_frame = tk.Frame(opcoes_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        tk.Label(dir_frame, text="Salvar automático em:").pack(side=tk.LEFT)
        tk.Entry(dir_frame, textvariable=self.pasta_destino, state='readonly', width=45).pack(side=tk.LEFT, padx=5)
        tk.Button(dir_frame, text="Procurar Pasta", command=self.escolher_pasta).pack(side=tk.LEFT)
        
        # 3. Painel de botões principais (Dividido em duas linhas para não poluir a tela)
        btn_frame_1 = tk.Frame(root)
        btn_frame_1.pack(pady=5)
        
        tk.Button(btn_frame_1, text="1. Congelar & Ajustar", command=self.ativar_ajuste, bg="lightyellow", height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame_1, text="2. Recortar & Ampliar", command=self.escanear, bg="lightblue", height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame_1, text="3. Voltar p/ Câmera", command=self.voltar_camera, bg="lightgray", height=2).pack(side=tk.LEFT, padx=5)
        
        btn_frame_2 = tk.Frame(root)
        btn_frame_2.pack(pady=5)
        tk.Button(btn_frame_2, text="Exportar TXT", command=lambda: self.exportar("txt"), width=20).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame_2, text="Exportar DOCX", command=lambda: self.exportar("docx"), width=20).pack(side=tk.LEFT, padx=10)
        
        # 4. Caixa de texto e Logs
        tk.Label(root, text="Texto Extraído:").pack()
        self.texto_extraido = tk.Text(root, height=8, width=70)
        self.texto_extraido.pack(pady=5)

        tk.Label(root, text="Terminal de Logs:").pack()
        self.log_text = scrolledtext.ScrolledText(root, height=6, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.log_text.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        self.log("Sistema iniciado. Enquadre o documento e clique em 'Congelar & Ajustar'.")
        self.atualizar_frame()

    def log(self, mensagem):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{hora}] {mensagem}\n")
        self.log_text.see(tk.END) 
        self.root.update()        
        
    def voltar_camera(self):
        """Limpa o estado de visualização estática e volta a ler o hardware da câmera"""
        self.exibindo_recorte = False
        self.modo_ajuste = False
        self.documento_atual = None
        self.texto_extraido.delete(1.0, tk.END)
        self.log("Retornando para a câmera ao vivo...")

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

    # --- LÓGICA DE ARRASTE DO MOUSE ---
    def iniciar_arraste(self, event):
        if not self.modo_ajuste or self.pontos_visuais is None:
            return
            
        raio_clique = 30 
        for i, ponto in enumerate(self.pontos_visuais):
            distancia = math.hypot(event.x - ponto[0], event.y - ponto[1])
            if distancia < raio_clique:
                self.indice_arrastado = i
                break

    def arrastar(self, event):
        if self.modo_ajuste and self.indice_arrastado is not None:
            x = max(0, min(event.x, 480))
            y = max(0, min(event.y, 360))
            self.pontos_visuais[self.indice_arrastado] = [x, y]
            self.renderizar_frame_ajuste()

    def parar_arraste(self, event):
        self.indice_arrastado = None

    def ativar_ajuste(self):
        if self.documento_atual is None:
            self.log("Nenhum papel detectado. Aguarde o quadrado verde aparecer.")
            return messagebox.showwarning("Aviso", "Aguarde a detecção verde aparecer antes de ajustar.")
            
        self.modo_ajuste = True
        self.exibindo_recorte = False
        ret, frame = self.cap.read()
        if ret:
            self.frame_alta_resolucao = frame.copy()
            self.frame_congelado = cv2.resize(frame, (480, 360))
            
            h_orig, w_orig = frame.shape[:2]
            self.fator_escala_x = w_orig / 480
            self.fator_escala_y = h_orig / 360
            
            pontos = self.ordenar_pontos(self.documento_atual)
            self.pontos_visuais = []
            for p in pontos:
                self.pontos_visuais.append([int(p[0] / self.fator_escala_x), int(p[1] / self.fator_escala_y)])
                
            self.log("⏱️ Imagem congelada! Arraste os círculos azuis para ajustar.")
            self.renderizar_frame_ajuste()

    def renderizar_frame_ajuste(self):
        frame_desenho = self.frame_congelado.copy()
        
        pts = np.array(self.pontos_visuais, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame_desenho, [pts], True, (255, 0, 0), 2)
        
        for p in self.pontos_visuais:
            cv2.circle(frame_desenho, tuple(p), 8, (255, 0, 0), -1)
            cv2.circle(frame_desenho, tuple(p), 12, (0, 255, 255), 2)
            
        cv_img = cv2.cvtColor(frame_desenho, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv_img)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def atualizar_frame(self):
        # A câmera ao vivo SÓ desenha se não estivermos ajustando vértices ou exibindo o recorte final
        if not self.modo_ajuste and not self.exibindo_recorte:
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
                cv_img = cv2.cvtColor(frame_visual, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv_img)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                
        self.root.after(15, self.atualizar_frame)

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para exportação")
        if pasta:
            self.pasta_destino.set(pasta)
            self.log(f"Auto-Save ativado: {pasta}")

    def escanear(self):
        if not self.modo_ajuste or self.pontos_visuais is None:
            self.log("ERRO: É necessário congelar a imagem primeiro.")
            return messagebox.showwarning("Aviso", "Clique em 'Congelar & Ajustar' antes de recortar.")
            
        self.log("Recortando e extraindo imagem corrigida...")
        
        pontos_reais = []
        for p in self.pontos_visuais:
            pontos_reais.append([p[0] * self.fator_escala_x, p[1] * self.fator_escala_y])
            
        pontos_doc = np.array(pontos_reais, dtype="float32")
        (tl, tr, br, bl) = pontos_doc
        
        larguraA = np.linalg.norm(br - bl)
        larguraB = np.linalg.norm(tr - tl)
        max_largura = max(int(larguraA), int(larguraB))
        
        alturaA = np.linalg.norm(tr - br)
        alturaB = np.linalg.norm(tl - bl)
        max_altura = max(int(alturaA), int(alturaB))
        
        pontos_destino = np.array([
            [0, 0],
            [max_largura - 1, 0],
            [max_largura - 1, max_altura - 1],
            [0, max_altura - 1]
        ], dtype="float32")
        
        matriz = cv2.getPerspectiveTransform(pontos_doc, pontos_destino)
        documento_recortado = cv2.warpPerspective(self.frame_alta_resolucao, matriz, (max_largura, max_altura))
        self.frame_escaneado = documento_recortado.copy()
        
        # --- NOVO: Exibe o documento recortado na tela (Efeito de Zoom Automático) ---
        # Calcula a proporção para caber perfeitamente no quadro de 480x360 da interface
        h_rec, w_rec = documento_recortado.shape[:2]
        proporcao = min(480 / w_rec, 360 / h_rec)
        novo_w, novo_h = int(w_rec * proporcao), int(h_rec * proporcao)
        frame_zoom = cv2.resize(documento_recortado, (novo_w, novo_h))
        
        # Fundo preto para preencher as bordas que sobrarem
        fundo = np.zeros((360, 480, 3), dtype=np.uint8)
        y_offset = (360 - novo_h) // 2
        x_offset = (480 - novo_w) // 2
        fundo[y_offset:y_offset+novo_h, x_offset:x_offset+novo_w] = frame_zoom
        
        cv_img_recorte = cv2.cvtColor(fundo, cv2.COLOR_BGR2RGB)
        img_recorte = Image.fromarray(cv_img_recorte)
        imgtk_recorte = ImageTk.PhotoImage(image=img_recorte)
        self.video_label.imgtk = imgtk_recorte
        self.video_label.configure(image=imgtk_recorte)
        
        # Altera os estados para manter a imagem do recorte na tela e parar o ajuste
        self.exibindo_recorte = True
        self.modo_ajuste = False
        
        # --- FIM NOVO ---

        cinza = cv2.cvtColor(documento_recortado, cv2.COLOR_BGR2GRAY)
        _, binarizada = cv2.threshold(cinza, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        self.log("Filtro aplicado. Extraindo texto (aguarde)...")
        self.root.update()
        
        try:
            texto = pytesseract.image_to_string(binarizada, lang='por')
            self.log("📝 Escaneamento Concluído! Visualize a imagem e valide o texto.") 
            self.texto_extraido.delete(1.0, tk.END)
            self.texto_extraido.insert(tk.END, texto)
        except Exception as e:
            self.log(f"ERRO OCR: {e}")
            self.voltar_camera()

    def exportar(self, formato):
        texto = self.texto_extraido.get(1.0, tk.END).strip()
        if not texto:
            return messagebox.showwarning("Aviso", "Caixa vazia.")
            
        pasta_padrao = self.pasta_destino.get()
        nome = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if pasta_padrao:
            caminho = os.path.join(pasta_padrao, f"{nome}.{formato}")
        else:
            tipos = [("Arquivo TXT", "*.txt")] if formato == "txt" else [("Documento DOCX", "*.docx")]
            caminho = filedialog.asksaveasfilename(initialfile=nome, defaultextension=f".{formato}", filetypes=tipos)
            if not caminho:
                return

        if formato == 'txt':
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(texto)
        elif formato == 'docx':
            doc = Document()
            doc.add_paragraph(texto)
            doc.save(caminho)
            
        salvou_foto = False
        if self.salvar_foto_var.get() and self.frame_escaneado is not None:
            caminho_img = os.path.splitext(caminho)[0] + '.png'
            cv2.imwrite(caminho_img, self.frame_escaneado)
            self.log("📸 Print RECORTADO salvo com sucesso!")
            salvou_foto = True
            
        self.log(f"📄 {formato.upper()} exportado.")
        msg = "Documento e foto salvos!" if salvou_foto else "Documento salvo com sucesso!"
        messagebox.showinfo("Sucesso", f"{msg}\nLocal: {caminho}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppScanner(root)
    root.mainloop()