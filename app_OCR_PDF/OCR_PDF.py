import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import pytesseract
import os
import numpy as np
from datetime import datetime

# Aponte para o executável do Tesseract no seu sistema
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class AppScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner OCR - v1.4.1 (Continuous Scan Fix)")
        self.root.geometry("700x850") 
        
        self.cap = cv2.VideoCapture(0)
        self.pasta_destino = tk.StringVar()
        
        # Estados da aplicação
        self.documento_atual = None
        self.frame_escaneado = None 
        self.exibindo_recorte = False
        
        # Estados da Animação
        self.animando = False
        self.fase_animacao = 0
        self.linha_scan_y = 0
        self.frame_congelado_anim = None
        
        # 1. Área do vídeo 
        self.video_label = tk.Label(root)
        self.video_label.pack(pady=5)
        
        # 2. Pasta de Destino Fixa (Obrigatória para o fluxo contínuo)
        opcoes_frame = tk.Frame(root)
        opcoes_frame.pack(pady=10, fill=tk.X, padx=20)
        
        tk.Label(opcoes_frame, text="Salvar documentos em:", font=("Arial", 10, "bold"), fg="darkblue").pack(side=tk.LEFT)
        tk.Entry(opcoes_frame, textvariable=self.pasta_destino, state='readonly', width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(opcoes_frame, text="Procurar Pasta", command=self.escolher_pasta).pack(side=tk.LEFT)
        
        # 3. Painel de Ação
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        self.btn_escanear = tk.Button(
            btn_frame, text="🔍 Escanear e Salvar", command=self.acao_escanear, 
            bg="lightblue", font=("Arial", 14, "bold"), width=30, height=2
        )
        self.btn_escanear.pack(pady=5)
        
        # 4. Caixa de texto e Logs
        tk.Label(root, text="Último Texto Extraído:").pack()
        self.texto_extraido = tk.Text(root, height=7, width=65)
        self.texto_extraido.pack(pady=5)

        tk.Label(root, text="Terminal de Logs:").pack()
        self.log_text = scrolledtext.ScrolledText(root, height=6, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.log_text.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        self.log("Sistema iniciado. Selecione a pasta de destino para começar.")
        self.atualizar_frame()

    def log(self, mensagem):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{hora}] {mensagem}\n")
        self.log_text.see(tk.END) 
        self.root.update()        

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para exportação automática")
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

    def atualizar_frame(self):
        # BUG FIX 1.4.1: Mantém o loop sempre vivo! 
        # Apenas pula a leitura da câmera se estiver ocupado com a animação ou exibindo o resultado.
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
            
        # O loop do OpenCV se reinicia a cada 15ms ininterruptamente
        self.root.after(15, self.atualizar_frame)

    def acao_escanear(self):
        if not self.pasta_destino.get():
            self.escolher_pasta()
            if not self.pasta_destino.get():
                return messagebox.showwarning("Aviso", "Selecione uma pasta para salvar os arquivos automaticamente.")

        if self.documento_atual is None:
            self.log("ERRO: Nenhum papel detectado na câmera.")
            return messagebox.showwarning("Aviso", "Aguarde o contorno verde aparecer no documento.")
        
        self.btn_escanear.config(state=tk.DISABLED, bg="lightgray", text="⏳ Processando...")
        self.iniciar_animacao_scan()

    def iniciar_animacao_scan(self):
        self.log("Capturando e alinhando perspectiva...")
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
        
        self.frame_escaneado = cv2.warpPerspective(frame_original, matriz, (max_largura, max_altura))
        
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
            self.realizar_ocr_e_salvar()
        else:
            self.root.after(20, self.executar_animacao)

    def realizar_ocr_e_salvar(self):
        self.log("Lendo texto (OCR)...")
        self.root.update()
        
        cinza = cv2.cvtColor(self.frame_escaneado, cv2.COLOR_BGR2GRAY)
        _, binarizada = cv2.threshold(cinza, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        try:
            texto = pytesseract.image_to_string(binarizada, lang='por')
            self.texto_extraido.delete(1.0, tk.END)
            self.texto_extraido.insert(tk.END, texto)
            
            nome_base = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            caminho_txt = os.path.join(self.pasta_destino.get(), f"{nome_base}.txt")
            caminho_img = os.path.join(self.pasta_destino.get(), f"{nome_base}.png")
            
            with open(caminho_txt, 'w', encoding='utf-8') as f:
                f.write(texto.strip())
            cv2.imwrite(caminho_img, self.frame_escaneado)
            
            self.log(f"💾 Sucesso! {nome_base} (.txt e .png) salvos.")
            self.log("Retornando à câmera em 2 segundos...")
            
            self.root.after(2000, self.voltar_camera)
            
        except Exception as e:
            self.log(f"ERRO OCR: {e}")
            self.voltar_camera()

    def voltar_camera(self):
        # Como o atualizar_frame continuou rodando no fundo (em modo de espera),
        # basta alterar as flags para False e a câmera "acordará" instantaneamente.
        self.exibindo_recorte = False
        self.documento_atual = None
        self.btn_escanear.config(state=tk.NORMAL, bg="lightblue", text="🔍 Escanear e Salvar")
        self.log("📸 Câmera pronta para o próximo scan!")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppScanner(root)
    root.mainloop()