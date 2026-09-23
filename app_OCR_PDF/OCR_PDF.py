import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import pytesseract
from docx import Document
import os
import numpy as np
from datetime import datetime

# Aponte para o executável do Tesseract no seu sistema
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class AppScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner OCR - V1 (Auto-Crop Robusto)")
        self.root.geometry("700x850") 
        
        self.cap = cv2.VideoCapture(0)
        self.frame_escaneado = None 
        self.pasta_destino = tk.StringVar()
        
        self.documento_atual = None
        self.efeito_piscando = False
        
        # 1. Área do vídeo 
        self.video_label = tk.Label(root)
        self.video_label.pack(pady=5)
        
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
        
        # 3. Painel de botões principais
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="1. Escanear e Ler", command=self.escanear, bg="lightblue", height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="2. Exportar TXT", command=lambda: self.exportar("txt"), height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="3. Exportar DOCX", command=lambda: self.exportar("docx"), height=2).pack(side=tk.LEFT, padx=5)
        
        # 4. Caixa de texto e Logs
        tk.Label(root, text="Texto Extraído:").pack()
        self.texto_extraido = tk.Text(root, height=8, width=65)
        self.texto_extraido.pack(pady=5)

        tk.Label(root, text="Terminal de Logs:").pack()
        self.log_text = scrolledtext.ScrolledText(root, height=7, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.log_text.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        self.log("Aplicativo iniciado. Aguardando câmera...")
        self.atualizar_frame()

    def log(self, mensagem):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{hora}] {mensagem}\n")
        self.log_text.see(tk.END) 
        self.root.update()        
        
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

    def desenhar_vs(self, frame, pts):
        pts = pts.reshape(4, 2)
        for i in range(4):
            p_atual = pts[i]
            p_ant = pts[(i - 1) % 4]
            p_prox = pts[(i + 1) % 4]
            v1 = p_atual + 0.15 * (p_ant - p_atual)
            v2 = p_atual + 0.15 * (p_prox - p_atual)
            cv2.line(frame, tuple(p_atual.astype(int)), tuple(v1.astype(int)), (0, 255, 0), 4)
            cv2.line(frame, tuple(p_atual.astype(int)), tuple(v2.astype(int)), (0, 255, 0), 4)

    def atualizar_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Pré-processamento com filtro de ruído e fechamento morfológico
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
                area = cv2.contourArea(contorno)
                
                # Filtro de área para evitar reconhecimento de objetos pequenos
                if area > 15000: 
                    perimetro = cv2.arcLength(contorno, True)
                    # Tolerância de 4% para imperfeições no papel
                    aproximacao = cv2.approxPolyDP(contorno, 0.04 * perimetro, True)
                    
                    if len(aproximacao) == 4:
                        self.documento_atual = aproximacao
                        
                        mascara = np.zeros(frame.shape[:2], dtype=np.uint8)
                        cv2.fillPoly(mascara, [aproximacao], 255)
                        
                        fundo_escuro = cv2.addWeighted(frame, 0.3, np.zeros_like(frame), 0.7, 0)
                        frame = np.where(mascara[:, :, None] == 255, frame, fundo_escuro)
                        
                        if self.efeito_piscando:
                            branco = np.ones_like(frame) * 255
                            frame = np.where(mascara[:, :, None] == 255, branco, frame)
                        else:
                            cv2.drawContours(frame, [aproximacao], -1, (0, 255, 0), 1)
                            self.desenhar_vs(frame, aproximacao)
                        break

            # Redimensionamento para o display nativo da GUI
            frame_visual = cv2.resize(frame, (480, 360))
            cv_img = cv2.cvtColor(frame_visual, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv_img)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        self.root.after(15, self.atualizar_frame)
        
    def parar_flash(self):
        self.efeito_piscando = False

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para exportação")
        if pasta:
            self.pasta_destino.set(pasta)
            self.log(f"Auto-Save ativado: {pasta}")

    def escanear(self):
        if self.documento_atual is None:
            self.log("ERRO: Nenhum documento detectado. Enquadre a folha.")
            return messagebox.showwarning("Aviso", "Enquadre o documento antes de escanear.")
            
        self.log("Iniciando escaneamento inteligente...")
        ret, frame_original = self.cap.read()
        
        # Pisca a tela (feedback visual)
        self.efeito_piscando = True
        self.root.after(150, self.parar_flash)
        
        # Correção de perspectiva (Auto-Crop e planificação do papel)
        pontos_doc = self.ordenar_pontos(self.documento_atual)
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
        documento_recortado = cv2.warpPerspective(frame_original, matriz, (max_largura, max_altura))
        self.frame_escaneado = documento_recortado.copy()
        
        # OCR
        cinza = cv2.cvtColor(documento_recortado, cv2.COLOR_BGR2GRAY)
        _, binarizada = cv2.threshold(cinza, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        self.log("Filtro aplicado. Extraindo texto...")
        
        try:
            texto = pytesseract.image_to_string(binarizada, lang='por')
            self.log("📝 Escaneado!") 
            self.texto_extraido.delete(1.0, tk.END)
            self.texto_extraido.insert(tk.END, texto)
        except Exception as e:
            self.log(f"ERRO OCR: {e}")

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

        # Exportação condicional
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