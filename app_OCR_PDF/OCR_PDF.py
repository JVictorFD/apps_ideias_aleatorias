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
        self.root.title("Scanner OCR - v1.2.0 (Smart Auto-Crop)")
        self.root.geometry("700x850") 
        
        self.cap = cv2.VideoCapture(0)
        self.pasta_destino = tk.StringVar()
        
        # Estados da aplicação
        self.documento_atual = None
        self.frame_escaneado = None 
        self.exibindo_recorte = False
        
        # 1. Área do vídeo 
        self.video_label = tk.Label(root)
        self.video_label.pack(pady=5)
        
        # 2. Configurações de Exportação (Minimalista)
        opcoes_frame = tk.Frame(root)
        opcoes_frame.pack(pady=5, fill=tk.X, padx=20)
        
        self.auto_save_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            opcoes_frame, text="Exportação Automática (Salvar pasta fixa)", 
            variable=self.auto_save_var, font=("Arial", 10, "bold"), fg="darkblue",
            command=self.verificar_auto_save
        ).pack(anchor=tk.W)
        
        self.dir_frame = tk.Frame(opcoes_frame)
        tk.Label(self.dir_frame, text="Salvar em:").pack(side=tk.LEFT)
        tk.Entry(self.dir_frame, textvariable=self.pasta_destino, state='readonly', width=45).pack(side=tk.LEFT, padx=5)
        tk.Button(self.dir_frame, text="Procurar Pasta", command=self.escolher_pasta).pack(side=tk.LEFT)
        
        # 3. Painel de Ações Principal (Apenas 2 botões)
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        
        self.btn_escanear = tk.Button(btn_frame, text="🔍 Escanear Documento", command=self.acao_escanear, bg="lightblue", font=("Arial", 11, "bold"), width=25, height=2)
        self.btn_escanear.pack(side=tk.LEFT, padx=10)
        
        self.btn_exportar = tk.Button(btn_frame, text="💾 Exportar Arquivo", command=self.exportar, bg="lightgray", font=("Arial", 11, "bold"), width=25, height=2)
        self.btn_exportar.pack(side=tk.LEFT, padx=10)
        
        # 4. Caixa de texto e Logs
        tk.Label(root, text="Texto Extraído:").pack()
        self.texto_extraido = tk.Text(root, height=8, width=65)
        self.texto_extraido.pack(pady=5)

        tk.Label(root, text="Terminal de Logs:").pack()
        self.log_text = scrolledtext.ScrolledText(root, height=6, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.log_text.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        self.log("Sistema iniciado. Enquadre o papel no quadrado verde e clique em Escanear.")
        self.atualizar_frame()

    def log(self, mensagem):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{hora}] {mensagem}\n")
        self.log_text.see(tk.END) 
        self.root.update()        

    def verificar_auto_save(self):
        """Mostra a escolha de pasta apenas se o auto-save for marcado"""
        if self.auto_save_var.get():
            self.dir_frame.pack(fill=tk.X, pady=5)
            if not self.pasta_destino.get():
                self.escolher_pasta()
        else:
            self.dir_frame.pack_forget()

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para exportação")
        if pasta:
            self.pasta_destino.set(pasta)
            self.log(f"Auto-Save ativado na pasta: {pasta}")
        else:
            self.auto_save_var.set(False)
            self.dir_frame.pack_forget()

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

    def atualizar_frame(self):
        if not self.exibindo_recorte:
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

    def acao_escanear(self):
        """Alterna inteligentemente entre Escanear (Auto-Crop) e Voltar para a Câmera"""
        if self.exibindo_recorte:
            self.exibindo_recorte = False
            self.documento_atual = None
            self.btn_escanear.config(text="🔍 Escanear Documento", bg="lightblue")
            self.texto_extraido.delete(1.0, tk.END)
            self.log("Retornando para a câmera ao vivo...")
        else:
            if self.documento_atual is None:
                self.log("ERRO: Nenhum papel detectado. Aguarde o contorno verde.")
                return messagebox.showwarning("Aviso", "Aguarde a detecção verde aparecer antes de escanear.")
            self.realizar_recorte_e_ocr()

    def realizar_recorte_e_ocr(self):
        self.log("Iniciando auto-crop, zoom e correção de perspectiva...")
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
        documento_recortado = cv2.warpPerspective(frame_original, matriz, (max_largura, max_altura))
        self.frame_escaneado = documento_recortado.copy()
        
        # Aplica o Zoom Visual na Interface
        h_rec, w_rec = documento_recortado.shape[:2]
        proporcao = min(480 / w_rec, 360 / h_rec)
        novo_w, novo_h = int(w_rec * proporcao), int(h_rec * proporcao)
        frame_zoom = cv2.resize(documento_recortado, (novo_w, novo_h))
        
        fundo = np.zeros((360, 480, 3), dtype=np.uint8)
        y_off, x_off = (360 - novo_h) // 2, (480 - novo_w) // 2
        fundo[y_off:y_off+novo_h, x_off:x_off+novo_w] = frame_zoom
        
        cv_img_recorte = cv2.cvtColor(fundo, cv2.COLOR_BGR2RGB)
        imgtk_recorte = ImageTk.PhotoImage(image=Image.fromarray(cv_img_recorte))
        self.video_label.imgtk = imgtk_recorte
        self.video_label.configure(image=imgtk_recorte)
        
        self.exibindo_recorte = True
        self.btn_escanear.config(text="🔄 Nova Captura", bg="lightyellow")
        
        cinza = cv2.cvtColor(documento_recortado, cv2.COLOR_BGR2GRAY)
        _, binarizada = cv2.threshold(cinza, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        self.log("Lendo texto com OCR...")
        self.root.update()
        
        try:
            texto = pytesseract.image_to_string(binarizada, lang='por')
            self.texto_extraido.delete(1.0, tk.END)
            self.texto_extraido.insert(tk.END, texto)
            self.log("📝 Pronto! Exporte o arquivo ou faça uma nova captura.") 
        except Exception as e:
            self.log(f"ERRO OCR: {e}")

    def exportar(self):
        texto = self.texto_extraido.get(1.0, tk.END).strip()
        if not texto:
            return messagebox.showwarning("Aviso", "A caixa de texto está vazia.")
            
        nome_base = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.auto_save_var.get() and self.pasta_destino.get():
            caminho_txt = os.path.join(self.pasta_destino.get(), f"{nome_base}.txt")
            caminho_img = os.path.join(self.pasta_destino.get(), f"{nome_base}.png")
            
            with open(caminho_txt, 'w', encoding='utf-8') as f:
                f.write(texto)
            if self.frame_escaneado is not None:
                cv2.imwrite(caminho_img, self.frame_escaneado)
                
            self.log(f"📄 Salvo automaticamente em: {caminho_txt}")
            messagebox.showinfo("Sucesso", "TXT e Imagem salvos automaticamente!")
        else:
            tipos = [("Arquivo de Texto", "*.txt"), ("Documento Word", "*.docx")]
            caminho = filedialog.asksaveasfilename(initialfile=nome_base, defaultextension=".txt", filetypes=tipos)
            if not caminho: return
            
            formato = os.path.splitext(caminho)[1]
            if formato == '.txt':
                with open(caminho, 'w', encoding='utf-8') as f: f.write(texto)
            elif formato == '.docx':
                doc = Document()
                doc.add_paragraph(texto)
                doc.save(caminho)
                
            if self.frame_escaneado is not None:
                caminho_img = os.path.splitext(caminho)[0] + '.png'
                cv2.imwrite(caminho_img, self.frame_escaneado)
                
            self.log(f"📄 Arquivo e imagem salvos em: {caminho}")
            messagebox.showinfo("Sucesso", "Documento e Imagem salvos com sucesso!")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppScanner(root)
    root.mainloop()