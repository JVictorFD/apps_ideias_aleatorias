import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pytesseract
from docx import Document

# Aponte para o executável do Tesseract no seu sistema
# Se você instalou em outro local, atualize o caminho abaixo
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class AppScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner OCR - V1")
        
        # Inicializa a webcam (0 é a câmera padrão)
        self.cap = cv2.VideoCapture(0)
        
        # Área de exibição do vídeo
        self.video_label = tk.Label(root)
        self.video_label.pack(pady=10)
        
        # Painel de botões
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="1. Escanear e Ler", command=self.escanear, bg="lightblue").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="2. Exportar TXT", command=self.exportar_txt).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="3. Exportar DOCX", command=self.exportar_docx).pack(side=tk.LEFT, padx=5)
        
        # Caixa de texto para o resultado do OCR
        self.texto_extraido = tk.Text(root, height=15, width=60)
        self.texto_extraido.pack(pady=10)
        
        # Inicia o loop de atualização da imagem da câmera
        self.atualizar_frame()

    def atualizar_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Converte as cores do OpenCV (BGR) para o Tkinter (RGB)
            cv_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv_img)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        # Atualiza o frame a cada 15ms
        self.root.after(15, self.atualizar_frame)

    def escanear(self):
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Erro", "Falha ao capturar imagem da webcam.")
            return
            
        # Pré-processamento básico: converte para escala de cinza e aplica binarização
        # Isso aumenta o contraste do papel e melhora drasticamente a precisão do OCR
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binarizada = cv2.threshold(cinza, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        try:
            # Executa a leitura (lang='por' garante o reconhecimento de acentos e cedilha)
            texto = pytesseract.image_to_string(binarizada, lang='por')
            
            # Atualiza a interface com o texto encontrado
            self.texto_extraido.delete(1.0, tk.END)
            self.texto_extraido.insert(tk.END, texto)
        except Exception as e:
            messagebox.showerror("Erro OCR", f"Verifique se o Tesseract está instalado no caminho correto.\nErro: {e}")

    def exportar_txt(self):
        texto = self.texto_extraido.get(1.0, tk.END).strip()
        if not texto:
            return messagebox.showwarning("Aviso", "A caixa de texto está vazia.")
            
        caminho = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Arquivo de Texto", "*.txt")])
        if caminho:
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(texto)
            messagebox.showinfo("Sucesso", "Arquivo salvo com sucesso.")

    def exportar_docx(self):
        texto = self.texto_extraido.get(1.0, tk.END).strip()
        if not texto:
            return messagebox.showwarning("Aviso", "A caixa de texto está vazia.")
            
        caminho = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Documento Word", "*.docx")])
        if caminho:
            doc = Document()
            doc.add_paragraph(texto)
            doc.save(caminho)
            messagebox.showinfo("Sucesso", "Arquivo salvo com sucesso.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppScanner(root)
    root.mainloop()