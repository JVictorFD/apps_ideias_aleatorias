import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os

# Configuração da página (garante tela cheia)
st.set_page_config(
    page_title="Bíblia Maps",
    page_icon="🌍",
    layout="wide"
)

# Carregamento seguro dos dados
@st.cache_data
def carregar_dados():
    caminho_arquivo = os.path.join("dados", "eventos_biblicos.json")
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Arquivo não encontrado: {caminho_arquivo}")
        return []

eventos = carregar_dados()

# Construção da Barra Lateral
with st.sidebar:
    st.title("📜 Bíblia Maps")
    st.write("Explore os eventos históricos da Bíblia de forma interativa.")
    
    st.header("Filtros")
    filtro_testamento = st.selectbox(
        "Selecione o Período Histórico:",
        ["Todos", "Antigo Testamento", "Novo Testamento"]
    )
    
    st.markdown("---")
    
    st.subheader("Modo Imersivo")
    if st.button("🚶‍♂️ Modo Andarilho", use_container_width=True, type="primary"):
        st.success("O Modo Andarilho (Visão em 1ª pessoa) será ativado em breve. Fique atento às próximas atualizações!")
    
    st.markdown("---")
    st.caption("v1.0.0 - Bíblia Maps")

# Aplicação dos filtros
eventos_filtrados = eventos
if filtro_testamento != "Todos":
    eventos_filtrados = [e for e in eventos if e["testamento"] == filtro_testamento]

# Mapa Base usando OpenStreetMap para evitar bloqueios de tela preta
mapa_biblico = folium.Map(location=[31.7, 35.2], zoom_start=5, tiles="OpenStreetMap")# Renderização dos Marcadores
for evento in eventos_filtrados:
    coord = evento["coordenadas"]
    cor_marcador = "darkred" if evento["testamento"] == "Antigo Testamento" else "cadetblue"
    
    html_popup = f"""
    <div style="font-family: Arial, sans-serif; width: 260px;">
        <h4 style="margin-bottom: 5px; color: #2C3E50; border-bottom: 1px solid #eee; padding-bottom: 5px;">{evento['evento']}</h4>
        <p style="margin: 4px 0; font-size: 13px;"><b>Local:</b> {evento['subregiao']}</p>
        <p style="margin: 4px 0; font-size: 13px;"><b>Envolvidos:</b> {evento['personagens']}</p>
        <p style="margin: 4px 0; font-size: 13px;"><b>Livro:</b> <i>{evento['referencia']}</i></p>
        <div style="margin-top: 10px; background-color: #f8f9fa; padding: 5px; border-radius: 4px;">
            <p style="margin: 0; font-size: 11px; color: #7f8c8d;"><b>Geografia Atual:</b> {evento['local_atual']}</p>
        </div>
    </div>
    """
    
    folium.Marker(
        location=coord,
        popup=folium.Popup(html_popup, max_width=300),
        tooltip=evento['evento'],
        icon=folium.Icon(color=cor_marcador, icon=evento['icone'])
    ).add_to(mapa_biblico)

# Exibição do mapa na tela
st_folium(
    mapa_biblico, 
    width="100%", 
    height=700,
    returned_objects=[]
)