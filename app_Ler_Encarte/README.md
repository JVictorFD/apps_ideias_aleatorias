# 🛒 Radar de Encartes Reais (app_Ler_Encarte)

Um aplicativo em Python criado com Streamlit e Tesseract OCR para ler encartes de supermercado, extrair produtos e preços, e estruturar os dados para análise de falsas promoções.

## 🚀 Como rodar localmente

1. Instale o [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) na sua máquina.
2. Clone este repositório.
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt


# 🌍 Bíblia Maps

Um aplicativo web interativo, leve e responsivo criado em Python para explorar geograficamente os eventos históricos da Bíblia. O projeto utiliza mapas dinâmicos para plotar localizações exatas de passagens bíblicas, permitindo filtrar eventos por época e visualizar informações detalhadas de cada acontecimento histórico diretamente no globo terrestre.

---

## ⚙️ Funcionalidades Atuais (v1.1.0)

* **Mapa Interativo Global:** Navegação livre, aproximação (zoom) e movimentação fluida.
* **Banco de Dados Modular (JSON):** Separação inteligente entre a interface e os dados, facilitando a adição de novos eventos sem alterar o código.
* **Agrupamento Dinâmico (Clusters):** Sistema que agrupa eventos próximos (como os vários que ocorreram em Jerusalém) em bolhas numeradas para não poluir a tela, expandindo-os automaticamente ao dar zoom.
* **Filtros Históricos:** Filtre a visualização instantaneamente entre eventos do Antigo e Novo Testamento.
* **Base do "Modo Andarilho":** Preparação da interface para o futuro modo de visão imersiva em primeira pessoa.

---

## 🚀 Como rodar localmente

Este passo a passo foi desenhado para ser simples e direto, permitindo que tanto desenvolvedores quanto usuários curiosos consigam rodar o mapa em poucos minutos.

### Pré-requisitos

Você precisa ter o **Python** instalado no seu computador. Se não tiver, baixe a versão mais recente em [python.org](https://www.python.org/).

### Passo a Passo

1. **Abra o terminal na pasta do projeto**
Navegue até a pasta `Biblia_Maps` onde os arquivos estão salvos. Se estiver usando o VS Code, basta abrir a pasta nele e abrir o terminal integrado (`Ctrl` + `'`).
2. **Crie um ambiente virtual (Recomendado)**
Isso cria uma "bolha" segura para instalar as bibliotecas sem afetar o resto do seu computador.
* **Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate

```


* **Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate

```




3. **Instale as dependências**


Com o ambiente ativado, instale as bibliotecas que desenham o mapa (Streamlit e Folium):
```bash
pip install -r requirements.txt

```


4. **Inicie o aplicativo**
Execute o comando abaixo para "ligar" o servidor local:
```bash
streamlit run app.py

```


*O seu navegador padrão (Chrome, Edge, Safari) abrirá automaticamente com o aplicativo rodando em tela cheia.*

---

## 📂 Como a estrutura funciona (Para Desenvolvedores)

Se você quiser expandir o projeto ou adicionar novas passagens bíblicas, não é necessário saber programar. A arquitetura foi dividida para facilitar a escalabilidade.

```text
Biblia_Maps/
├── .streamlit/
│   └── config.toml           # (Força o tema claro para evitar bugs visuais)
├── dados/
│   └── eventos_biblicos.json # (Adicione novos eventos copiando a estrutura deste arquivo)
├── app.py                    # (Motor principal da aplicação)
├── requirements.txt          # (Lista de bibliotecas)
└── .gitignore                # (Evita que o ambiente virtual suba para o GitHub)

```

### Como adicionar um novo ponto no mapa?

Abra o arquivo `dados/eventos_biblicos.json` e adicione um novo bloco seguindo este padrão:

```json
{
    "id": "nome_do_evento_sem_espacos",
    "regiao": "Nome da Região Maior",
    "subregiao": "Cidade ou Local",
    "evento": "Título do Acontecimento",
    "personagens": "Nome das Pessoas Envolvidas",
    "referencia": "Livro Capítulo:Versículo",
    "local_atual": "Nome do país ou região atual",
    "coordenadas": [Latitude, Longitude],
    "testamento": "Antigo Testamento ou Novo Testamento",
    "icone": "star"
}

```

*Salve o arquivo e simplesmente recarregue a página no navegador. O novo ponto já aparecerá no globo!*