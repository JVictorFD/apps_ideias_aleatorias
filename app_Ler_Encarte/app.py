import streamlit as st
import ollama
import pandas as pd
import json

st.set_page_config(page_title="Radar de Encartes", layout="wide")
st.title("🛒 Radar de Encartes (IA Local - 100% Grátis)")

imagem_recebida = st.file_uploader("Selecione o encarte", type=["jpg", "png", "jpeg", "webp"])

if imagem_recebida is not None:
    # Ler os bytes da imagem para enviar ao Ollama
    image_bytes = imagem_recebida.getvalue()
    
    st.image(image_bytes, caption="Encarte Carregado", width=500)
    
    if st.button("Analisar com IA Local", type="primary"):
        with st.spinner("A IA local está analisando a imagem (isso pode levar alguns segundos dependendo do seu PC)..."):
            try:
# Prompt blindado contra alucinações
                prompt = """
                Você é um extrator de dados estrito. Leia o texto exato desta imagem.
                REGRA 1: NÃO INVENTE PRODUTOS. Extraia apenas o que você conseguir ler claramente.
                REGRA 2: Se você não conseguir identificar um preço ao lado do produto, ignore o produto.
                REGRA 3: Retorne APENAS e EXATAMENTE um array JSON válido, sem comentários.
                
                Exemplo de saída esperada:
                [
                    {"Produto": "Margarina Puro Sabor", "Quantidade": "500g", "Preço": "R$ 4,79"},
                    {"Produto": "Arroz Tio Manoel", "Quantidade": "1kg", "Preço": "R$ 3,79"}
                ]
                """
                
                # Comunicação com o modelo rodando no seu computador
                resposta = ollama.chat(
                    model='llava', 
                    messages=[{
                        'role': 'user',
                        'content': prompt,
                        'images': [image_bytes]
                    }],
                    # options={'temperature': 0} tira a criatividade da IA e a força a ser literal
                    options={
                        'temperature': 0.0,
                        'top_p': 0.1
                    }
                )
                
                texto_resposta = resposta['message']['content'].strip()
                
                # Limpeza básica caso a IA coloque blocos de markdown
                if texto_resposta.startswith("```json"):
                    texto_resposta = texto_resposta[7:-3]
                elif texto_resposta.startswith("```"):
                    texto_resposta = texto_resposta[3:-3]
                    
                # Converter para dataframe
                dados_estruturados = json.loads(texto_resposta)
                df = pd.DataFrame(dados_estruturados)
                
                st.success("Encarte lido com sucesso!")
                st.dataframe(df, use_container_width=True)
                
            except json.JSONDecodeError:
                st.error("A IA não conseguiu formatar os dados como JSON. Veja a resposta bruta:")
                st.write(texto_resposta)
            except Exception as e:
                st.error(f"Erro ao conectar com o Ollama: {e}")
                st.info("Verifique se o Ollama está instalado e rodando em segundo plano no seu computador.")