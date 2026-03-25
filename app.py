# Imports
import altair as alt
import re
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.yfinance import YFinanceTools
from phi.tools.duckduckgo import DuckDuckGo
from dotenv import load_dotenv

# Configuração de Página (Deve ser o primeiro comando Streamlit)
st.set_page_config(page_title="Análise de Ações com IA", page_icon=":chart_with_upwards_trend:", layout="wide", initial_sidebar_state="expanded")

# CSS para esconder elementos do Streamlit e o botão do GitHub
hide_github_icon = """
    <style>
    .stAppDeployButton {
        display: none !important;
    }
    #MainMenu {
        visibility: hidden;
    }
    footer {
        visibility: hidden;
    }
    header {
        visibility: hidden;
    }
    </style>
"""
st.markdown(hide_github_icon, unsafe_allow_html=True)

# Tenta importar o Vizro para a segunda aba
try:
    import vizro.plotly_express as vpx
except ImportError:
    vpx = px 

# Carrega o arquivo de variáveis de ambiente
load_dotenv()

########## Integração com API Dados de Mercado ##########

@st.cache_data(ttl=86400) # Cache de 24 horas para lista de tickers (estático)
def buscar_todos_tickers_br():
    """Busca a lista oficial de tickers da B3 via API Dados de Mercado."""
    url = "https://api.dadosdemercado.com.br/v1/tickers"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            dados = response.json()
            lista_tickers = [item['ticker'] for item in dados]
            return sorted(lista_tickers)
        return []
    except Exception as e:
        print(f"Erro ao buscar tickers da API: {e}")
        return []

########## Funções de Analytics (Lógica Original & B3) ##########

def normalizar_ticker(ticker):
    ticker = ticker.upper().strip()
    if re.match(r'^[A-Z]{4}[0-9]{1,2}$', ticker):
        return f"{ticker}.SA"
    return ticker

@st.cache_data(ttl=43200) # Cache de 12 horas para dados históricos
def extrai_dados(ticker, period="1y"):
    ticker_final = normalizar_ticker(ticker)
    stock = yf.Ticker(ticker_final)
    hist = stock.history(period=period)
    if hist.empty:
        return None
    hist.reset_index(inplace=True)
    return hist

def plot_stock_price(hist, ticker):
    fig = px.line(hist, x="Date", y="Close", title=f"{ticker} Preços das Ações", markers=True)
    st.plotly_chart(fig, use_container_width=True)

def plot_candlestick(hist, ticker):
    fig = go.Figure(data=[go.Candlestick(x=hist['Date'],
                                         open=hist['Open'],
                                         high=hist['High'],
                                         low=hist['Low'],
                                         close=hist['Close'])])
    fig.update_layout(title=f"{ticker} Candlestick Chart", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

def plot_media_movel(hist, ticker):
    hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
    hist['EMA_20'] = hist['Close'].ewm(span=20, adjust=False).mean()
    fig = px.line(hist, x='Date', y=['Close', 'SMA_20', 'EMA_20'],
                  title=f"{ticker} Médias Móveis (20 Períodos)")
    st.plotly_chart(fig, use_container_width=True)

def plot_volume(hist, ticker):
    fig = px.bar(hist, x='Date', y='Volume', title=f"{ticker} Volume de Negociação")
    st.plotly_chart(fig, use_container_width=True)

########## Função da Terceira Aba (Entrada de Texto Livre) ##########

def renderizar_aba_comparativa():
    st.title("⚖️ Comparativo de Performance (Peer Analysis)")
    
    if "texto_tickers" not in st.session_state:
        st.session_state["texto_tickers"] = "PETR4, VALE3"

    st.info("""
        **Como digitar os ativos:**
        - 🇧🇷 **B3 (Ações/FIIs):** `PETR4`, `VALE3`, `HGLG11`
        - 🇺🇸 **EUA:** `AAPL`, `TSLA`, `MSFT`
        - ₿ **Cripto:** `BTC-USD`, `ETH-USD`
        - 📈 **Índices:** `^BVSP`, `^GSPC`

        *Separe os tickers por vírgula e aperte **ENTER**.*
        """)

    col_filtros_1, col_filtros_2 = st.columns([2, 1])
    
    with col_filtros_1:
        st.text_input(
            "Digite os Tickers:",
            placeholder="Ex: PETR4, ITUB4, GOOGL",
            key="texto_tickers" 
        )
        texto_input = st.session_state["texto_tickers"]

    with col_filtros_2:
        h_map = {
            "1 Mês": "1mo", 
            "3 Meses": "3mo", 
            "6 Meses": "6mo", 
            "1 Ano": "1y", 
            "5 Anos": "5y"
        }
        horiz = st.selectbox("Período", list(h_map.keys()), index=3, key="periodo_comp")

    if texto_input:
        tickers_brutos = [t.strip() for t in texto_input.split(",") if t.strip()]
        tickers_sel = [normalizar_ticker(t) for t in tickers_brutos]

        if tickers_sel:
            try:
                with st.spinner(f"Baixando dados para: {', '.join(tickers_sel)}..."):
                    df_raw = yf.download(tickers_sel, period=h_map[horiz], progress=False)['Close']
                    
                    if not df_raw.empty:
                        if isinstance(df_raw, pd.Series):
                            df_plot = df_raw.to_frame()
                            df_plot.columns = [tickers_sel[0]]
                        else:
                            df_plot = df_raw
                        
                        df_plot = df_plot.dropna(axis=1, how='all')
                        
                        if not df_plot.empty:
                            base_price = df_plot.fillna(method='bfill').iloc[0]
                            norm_df = (df_plot / base_price) * 100
                            
                            st.subheader(f"📈 Evolução Relativa (Base 100) - {horiz}")
                            
                            c_data = norm_df.reset_index().melt(id_vars=["Date"], var_name="Ativo", value_name="Val")
                            chart = alt.Chart(c_data).mark_line().encode(
                                x=alt.X("Date:T", title="Data"),
                                y=alt.Y("Val:Q", title="Índice (Base 100)", scale=alt.Scale(zero=False)),
                                color="Ativo:N",
                                tooltip=["Date:T", "Ativo:N", alt.Tooltip("Val:Q", format=".2f")]
                            ).properties(height=400).interactive()
                            
                            st.altair_chart(chart, use_container_width=True)
                            st.divider()
                            
                            rent = ((df_plot.iloc[-1] / df_plot.iloc[0]) - 1) * 100
                            cols = st.columns(min(len(df_plot.columns), 5))
                            for idx, t in enumerate(df_plot.columns):
                                with cols[idx % 5]:
                                    st.metric(t, f"R$ {df_plot[t].iloc[-1]:.2f}", f"{rent[t]:.2f}%")
            except Exception as e:
                st.error(f"Erro ao processar dados: {e}")

########## Configuração do Agente de IA ##########

MODEL_ID = "llama-3.1-8b-instant"

# Cache da resposta da IA por 24 horas para economizar API
@st.cache_data(ttl=86400)
def executar_agente_ia(ticker):
    agente_consultor = Agent(
        name="Consultor Financeiro",
        model=Groq(id=MODEL_ID),
        tools=[
            DuckDuckGo(), 
            YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True, company_news=True)
        ],
        instructions=[
            "Você é um consultor financeiro sênior do mercado de ações.",
            "Responda em Português do Brasil.",
            "Use tabelas para dados numéricos.",
            "Nunca use tags HTML como <h2> ou <p>, use apenas Markdown.",
            "Seja direto e não narre as ferramentas que está usando.",
            "Sempre inclua as fontes no final."
        ],
        markdown=True
    )
    prompt = f"Forneça um resumo das notícias de hoje e recomendações de analistas para {ticker}."
    return agente_consultor.run(prompt)

########## Interface Streamlit e Navegação ##########

# Sidebar
st.sidebar.title("📈 Análise de Ações com IA")
st.sidebar.title("⚙️ Menu de Navegação")
aba_selecionada = st.sidebar.radio("Escolha a Aba:", ["Consultoria IA", "Gráficos Avançados", "Comparativo de Pares"])

st.sidebar.divider()
ticker_usuario = st.sidebar.text_input("Ticker do Ativo (Ex: PETR4, AAPL):", value="PETR4").upper()

if st.sidebar.button("Suporte"):
    st.sidebar.write("andre-luiz-colombo@outlook.com")

########## ABA 1: CONSULTORIA IA ##########

if aba_selecionada == "Consultoria IA":
    st.title("🤖 Análise de Mercado de Ações com IA")
    st.header("Análise Estratégica com IA")

    if st.button("Executar Consultoria"):
        if ticker_usuario:
            ticker_ia = normalizar_ticker(ticker_usuario)
            with st.spinner(f"Processando análise para {ticker_ia}..."):
                try:
                    st.subheader("🤖 Recomendação do Especialista")
                    response = executar_agente_ia(ticker_ia)

                    if response and hasattr(response, 'content'):
                        clean_response = re.sub(r"(Running:[\s\S]*?\n\n)", "", response.content)
                        clean_response = re.sub(r"<.*?>", "", clean_response)
                        frases_remover = ["Eu vou iniciar buscando", "Para isso vou usar", "Vou usar o endpoint"]
                        for frase in frases_remover:
                            clean_response = re.sub(f"{frase}.*?\n", "", clean_response)
                        st.markdown(clean_response)
                    
                    st.divider()
                    st.subheader(f"🎯 Consenso de Mercado: {ticker_ia}")
                    
                    ticker_obj = yf.Ticker(ticker_ia)
                    info = ticker_obj.info
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        rec = info.get('recommendationKey', 'N/A').replace('_', ' ').title()
                        st.metric("Sentimento", rec)
                    with c2:
                        target = info.get('targetMeanPrice', 'N/A')
                        st.metric("Preço Alvo", f"R$ {target}" if target != 'N/A' else "N/A")
                    with c3:
                        atual = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
                        st.metric("Preço Atual", f"R$ {atual}" if atual != 'N/A' else "N/A")
                    
                    st.divider()
                    st.subheader("📊 Visualização de Mercado")
                    
                    hist = extrai_dados(ticker_usuario, period="6mo")
                    if hist is not None:
                        col1, col2 = st.columns(2)
                        with col1:
                            plot_stock_price(hist, ticker_ia)
                            plot_media_movel(hist, ticker_ia)
                        with col2:
                            plot_candlestick(hist, ticker_ia)
                            plot_volume(hist, ticker_ia)
                            
                except Exception as e:
                    st.error(f"Erro na execução: {e}")

########## ABA 2: GRÁFICOS AVANÇADOS ##########

elif aba_selecionada == "Gráficos Avançados":
    st.title("📊 Terminal de Análise Técnica")
    ticker_ia = normalizar_ticker(ticker_usuario)

    @st.fragment(run_every="86400s") #Aumentado para 24hrs para evitar Rate Limit
    def mostrar_metricas_vivas(ticker):
        try:
            t_obj = yf.Ticker(ticker)
            d_rec = t_obj.history(period="1d", interval="1m")
            if not d_rec.empty:
                p_atual = d_rec['Close'].iloc[-1]
                f_ant = t_obj.info.get('previousClose', p_atual)
                var = ((p_atual - f_ant) / f_ant) * 100
                m1, m2, m3 = st.columns(3)
                m1.metric("Preço (Tempo Real)", f"R$ {p_atual:.2f}", f"{var:.2f}%")
                m2.metric("Máxima Dia", f"R$ {d_rec['High'].max():.2f}")
                m3.metric("Mínima Dia", f"R$ {d_rec['Low'].min():.2f}")
                st.caption(f"⏱️ Última atualização: {d_rec.index[-1].strftime('%H:%M:%S')}")
        except:
            st.error("⚠️ Yahoo Finance em Rate Limit. Aguarde 1 minuto.")

    mostrar_metricas_vivas(ticker_ia)
    st.divider()
    hist = extrai_dados(ticker_usuario, period="1y")
    if hist is not None:
        st.subheader(f"1. Candlestick & Médias Móveis - {ticker_ia}")
        hist['MA50'] = hist['Close'].rolling(50).mean()
        hist['MA200'] = hist['Close'].rolling(200).mean()
        fig_candle = go.Figure(data=[
            go.Candlestick(x=hist['Date'], open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Preço"),
            go.Scatter(x=hist['Date'], y=hist['MA50'], line=dict(color='orange', width=2), name="Média 50d"),
            go.Scatter(x=hist['Date'], y=hist['MA200'], line=dict(color='blue', width=2), name="Média 200d")
        ])
        fig_candle.update_layout(xaxis_rangeslider_visible=True, height=600, template="plotly_white")
        st.plotly_chart(fig_candle, use_container_width=True)

        st.info("""
            **💡 Dica de Navegação:**
            * **Filtrar Tempo:** Deslize as extremidades da barra inferior para ajustar o período.
            * **Zoom:** Clique e arraste o mouse sobre uma área do gráfico para aproximar.
            * **Reset:** Clique duas vezes no gráfico para voltar à visão original.
        """)

        st.divider()
        st.subheader("2. Evolução de Fechamento")
        fig_area = vpx.area(hist, x="Date", y="Close", title="Tendência 1 Ano")
        st.plotly_chart(fig_area, use_container_width=True)
        st.divider()
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (delta.where(delta < 0, 0).abs()).rolling(window=14).mean()
        hist['RSI'] = 100 - (100 / (1 + (gain / loss)))
        st.subheader("3. Índice de Força Relativa (RSI)")
        fig_rsi = px.line(hist, x="Date", y="RSI", title="RSI (Momento)")
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        st.plotly_chart(fig_rsi, use_container_width=True)

########## ABA 3: COMPARATIVO ##########

elif aba_selecionada == "Comparativo de Pares":
    renderizar_aba_comparativa()

# Footer
st.sidebar.divider()
st.sidebar.markdown("**Desenvolvido Por:** André L. Colombo")
st.sidebar.caption("Engenharia de Dados & Analytics")
