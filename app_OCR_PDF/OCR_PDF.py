import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import pytesseract
from docx import Document
import os
from datetime import datetime

# Aponte para o executável do Tesseract no seu sistema
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class AppScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner OCR - V1")
        
        # Aumentamos a janela para acomodar os novos elementos
        self.root.geometry("680x850") 
        
        self.cap = cv2.VideoCapture(0)
        self.frame_escaneado = None 
        
        # Variável para armazenar a pasta de salvamento automático
        self.pasta_destino = tk.StringVar()
        
        # 1. Área de exibição do vídeo
        self.video_label = tk.Label(root)
        self.video_label.pack(pady=5)
        
        # 2. Frame de Opções (Checkbox + Pasta de Destino)
        opcoes_frame = tk.Frame(root)
        opcoes_frame.pack(pady=5, fill=tk.X, padx=20)
        
        self.salvar_foto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opcoes_frame, 
            text="Salvar foto da câmera junto com o documento", 
            variable=self.salvar_foto_var,
            font=("Arial", 10, "bold"), fg="darkblue"
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
        # Unificamos a chamada de exportação usando lambda para simplificar o código
        tk.Button(btn_frame, text="2. Exportar TXT", command=lambda: self.exportar("txt"), height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="3. Exportar DOCX", command=lambda: self.exportar("docx"), height=2).pack(side=tk.LEFT, padx=5)
        
        # 4. Caixa de texto para o resultado do OCR
        tk.Label(root, text="Texto Extraído:").pack()
        self.texto_extraido = tk.Text(root, height=10, width=65)
        self.texto_extraido.pack(pady=5)

        # 5. Caixa de texto para o Log Visível
        tk.Label(root, text="Terminal de Logs:").pack()
        self.log_text = scrolledtext.ScrolledText(root, height=7, width=80, bg="black", fg="lightgreen", font=("Consolas", 9))
        self.log_text.pack(pady=5)
        
        self.log("Aplicativo iniciado. Aguardando câmera...")
        self.atualizar_frame()

    def log(self, mensagem):
        """Escreve na caixa de log preta e atualiza a interface em tempo real"""
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{hora}] {mensagem}\n")
        self.log_text.see(tk.END) # Rola automaticamente para a última linha
        self.root.update()        # Impede que a tela congele durante o processamento
        
    def atualizar_frame(self):
        ret, frame = self.cap.read()
        if ret:
            cv_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv_img)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        self.root.after(15, self.atualizar_frame)
        
    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para exportação")
        if pasta:
            self.pasta_destino.set(pasta)
            self.log(f"Pasta configurada: {pasta}")

    def escanear(self):
        self.log("Iniciando captura...")
        ret, frame = self.cap.read()
        if not ret:
            self.log("ERRO: Falha ao ler o hardware da câmera.")
            messagebox.showerror("Erro", "Falha ao capturar imagem da webcam.")
            return
            
        self.frame_escaneado = frame.copy()
        self.log("Imagem capturada com sucesso e salva na memória.")
        
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binarizada = cv2.threshold(cinza, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        self.log("Filtro de contraste aplicado.")
        
        try:
            self.log("Enviando imagem para o Tesseract OCR... aguarde.")
            texto = pytesseract.image_to_string(binarizada, lang='por')
            
            self.log(f"Leitura concluída! {len(texto)} caracteres extraídos.")
            self.texto_extraido.delete(1.0, tk.END)
            self.texto_extraido.insert(tk.END, texto)
        except Exception as e:
            self.log(f"ERRO CRÍTICO NO OCR: {e}")
            messagebox.showerror("Erro OCR", f"Detalhes no terminal.\nErro: {e}")

    def exportar(self, formato):
        """Função unificada para exportar texto e imagem automaticamente ou manualmente"""
        texto = self.texto_extraido.get(1.0, tk.END).strip()
        if not texto:
            self.log("Exportação abortada: caixa de texto vazia.")
            return messagebox.showwarning("Aviso", "A caixa de texto está vazia.")
            
        pasta_padrao = self.pasta_destino.get()
        nome_arquivo = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if pasta_padrao:
            # Modo Automático: Salva direto sem perguntar
            caminho = os.path.join(pasta_padrao, f"{nome_arquivo}.{formato}")
            self.log(f"Modo Automático: Exportando para {caminho}")
        else:
            # Modo Manual: Pergunta onde salvar
            tipos = [("Arquivo de Texto", "*.txt")] if formato == "txt" else [("Documento Word", "*.docx")]
            caminho = filedialog.asksaveasfilename(
                initialfile=nome_arquivo, 
                defaultextension=f".{formato}", 
                filetypes=tipos
            )
            if not caminho:
                self.log("Exportação cancelada pelo usuário.")
                return
            self.log(f"Exportando para {caminho}")

        # Exporta o texto de acordo com o formato
        if formato == 'txt':
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(texto)
        elif formato == 'docx':
            doc = Document()
            doc.add_paragraph(texto)
            doc.save(caminho)
            
        # Verifica se precisa salvar a imagem vinculada
        salvou_foto = False
        if self.salvar_foto_var.get() and self.frame_escaneado is not None:
            caminho_img = os.path.splitext(caminho)[0] + '.png'
            cv2.imwrite(caminho_img, self.frame_escaneado)
            self.log(f"Imagem da câmera salva em: {caminho_img}")
            salvou_foto = True
            
        self.log(f"Exportação finalizada com sucesso.")
        msg = "Documento e foto salvos!" if salvou_foto else "Documento salvo com sucesso!"
        messagebox.showinfo("Sucesso", f"{msg}\nLocal: {caminho}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppScanner(root)
    root.mainloop()