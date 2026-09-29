import streamlit as st
import pytesseract
from PIL import Image
import re
import pandas as pd
import os

# ==========================================
# CONFIGURAÇÃO DO TESSERACT (APENAS PARA WINDOWS)
# Se você estiver no Linux ou Mac, pode comentar a linha abaixo.
# Se estiver no Windows, verifique se o caminho está correto.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# ==========================================

st.set_page_config(page_title="Radar de Encartes", layout="centered")
st.title("🛒 Radar de Encartes Reais (OCR Local)")
st.write("Faça o upload do encarte para extrair os produtos e preços usando Tesseract OCR.")

def extrair_produtos_e_precos(texto_bruto):
    """
    Usa Expressões Regulares (Regex) para encontrar padrões de "Produto + Preço"
    no texto extraído pela imagem.
    """
    linhas = texto_bruto.split('\n')
    produtos_encontrados = []
    
    # Padrao regex para encontrar valores em reais (ex: 12,99 | 5.99 | R$ 10,00)
    padrao_preco = r'(?:R\$\s*)?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})'
    
    produto_atual = ""
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
            
        # Tenta encontrar um preço na linha
        match_preco = re.search(padrao_preco, linha)
        
        if match_preco:
            preco_encontrado = match_preco.group(1)
            # Remove o preço da linha para tentar isolar o nome do produto
            nome_produto = linha.replace(match_preco.group(0), '').strip()
            
            # Se o nome do produto ficou na mesma linha do preço
            if len(nome_produto) > 3:
                produtos_encontrados.append({
                    "Produto": nome_produto,
                    "Preço Extraído": f"R$ {preco_encontrado}"
                })
            # Se a linha só tinha o preço, assume que o produto estava na linha anterior
            elif produto_atual and len(produto_atual) > 3:
                 produtos_encontrados.append({
                    "Produto": produto_atual,
                    "Preço Extraído": f"R$ {preco_encontrado}"
                })
            produto_atual = "" # Reseta
        else:
            # Se não tem preço, guarda a linha como possível nome de produto
            # Filtra linhas muito curtas que podem ser lixo do OCR
            if len(linha) > 3 and not re.search(r'^\d+$', linha):
                produto_atual = linha
                
    return produtos_encontrados

# Interface de Upload
imagem_recebida = st.file_uploader("Selecione a imagem do encarte", type=["jpg", "png", "jpeg", "webp"])

if imagem_recebida is not None:
    # Exibir a imagem
    imagem = Image.open(imagem_recebida)
    st.image(imagem, caption="Encarte Carregado", use_container_width=True)
    
    if st.button("Analisar Encarte"):
        with st.spinner("Extraindo texto da imagem com Tesseract..."):
            try:
                # 1. Executar o OCR (forçando o idioma português se estiver instalado)
                # Dica: se falhar o 'por', use apenas lang='eng' ou retire o parâmetro lang.
                texto_extraido = pytesseract.image_to_string(imagem, lang='por')
                
                # 2. Processar o texto com Regex
                dados_estruturados = extrair_produtos_e_precos(texto_extraido)
                
                st.success("Análise Concluída!")
                
                if dados_estruturados:
                    st.subheader("Produtos Identificados")
                    df = pd.DataFrame(dados_estruturados)
                    st.dataframe(df, use_container_width=True)
                    
                    # Simulação de cruzamento com banco de dados
                    st.info("💡 Próximo passo no seu algoritmo: Salvar esses dados em um banco local (SQLite) e cruzar com o histórico para encontrar as reais promoções.")
                else:
                    st.warning("O OCR extraiu texto, mas o algoritmo não conseguiu associar produtos e preços com clareza.")
                
                # Mostrar o texto bruto para depuração (opcional, bom para você ajustar o regex depois)
                with st.expander("Ver texto bruto extraído pelo OCR"):
                    st.text(texto_extraido)
                    
            except Exception as e:
                st.error(f"Erro ao processar imagem: {e}")
                st.write("Verifique se o Tesseract está instalado corretamente na sua máquina.")