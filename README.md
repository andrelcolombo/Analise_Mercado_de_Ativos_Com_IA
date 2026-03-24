# 📈 Terminal de Inteligência Financeira v1.0

![Status do Projeto](https://img.shields.io/badge/Status-Em_Desenvolvimento-green)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-ff4b4b)

O **Terminal de Inteligência Financeira** é uma plataforma de análise de dados do mercado de capitais que combina técnicas de **Engenharia de Dados**, **Análise Técnica** e **Inteligência Artificial Generativa**. O objetivo é transformar dados brutos do Yahoo Finance em insights estratégicos e visualizações interativas.

---

## 🏗️ Arquitetura do Sistema

O projeto foi construído seguindo princípios de modularização e eficiência de memória no Streamlit:

1.  **Ingestão de Dados:** Consumo de APIs financeiras (`yfinance`) com tratamento de exceções e normalização de Tickers.
2.  **Camada de Processamento:** Cálculo de indicadores técnicos (Médias Móveis de 50/200 dias, RSI, Performance Acumulada) utilizando `Pandas`.
3.  **Motor de IA:** Agente inteligente integrado via **Groq/LangChain** que realiza o parsing de notícias e sentimentos do mercado.
4.  **Interface (UI/UX):** Dashboard responsivo com suporte a modo escuro nativo e componentes otimizados via `st.fragment`.

---

## 🛠️ Funcionalidades de Engenharia

### 1. Consultoria Estratégica (LLM)
Interface que utiliza modelos de linguagem para interpretar o cenário atual de um ativo, limpando logs técnicos e entregando apenas a recomendação final ao usuário.

### 2. Terminal de Análise Técnica
* **Gráficos de Candlestick:** Interativos com suporte a Zoom e Range Selection.
* **Indicadores de Momento:** RSI (Relative Strength Index) com zonas de sobrecompra e sobrevenda.
* **Métricas em Tempo Real:** Monitoramento de preço e variação percentual com atualização automática a cada 60 segundos.

### 3. Comparativo de Performance (Benchmarking)
Algoritmo que normaliza os preços de diferentes ativos para uma base 100, permitindo comparar o crescimento percentual real entre ações, índices (IBOV/S&P500) e cripto.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
* Python 3.10 ou superior.
* Chave de API da Groq (ou provedor de LLM compatível).
