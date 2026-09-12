import os
import datetime
import streamlit as st
import requests
import google.generativeai as genai

st.set_page_config(page_title="Pesquisador Gemini Notebook", page_icon="🔍", layout="wide")

st.title("🔍 Pesquisador de Assuntos Recentes & Gemini")
st.markdown("Busque informações das últimas 36 horas, selecione as fontes e envie para análise do Gemini.")

# ==============================================================================
# CONFIGURAÇÃO AUTOMÁTICA DAS CHAVES (COLE SUAS CHAVES AQUI SE PREFERIR)
# ==============================================================================
GEMINI_KEY_PADRAO = "AQ.Ab8RN6IjIonUWlBXKv-rifYP8TYxHzqLX4JvJPHsmwsu3LTowQ"
SERPER_KEY_PADRAO = ""
# ==============================================================================

# Busca chave dos Secrets do Streamlit ou usa a chave informada direto no código
gemini_api_key = st.secrets.get("GEMINI_API_KEY", GEMINI_KEY_PADRAO)
serper_api_key = st.secrets.get("SERPER_API_KEY", SERPER_KEY_PADRAO)

# --- BARRA LATERAL INFORMATIVA ---
with st.sidebar:
    st.header("⚙️ Status da Conexão")
    if gemini_api_key and gemini_api_key != "SUA_CHAVE_DO_GEMINI_AQUI":
        st.success("✅ Gemini API Conectada")
    else:
        st.error("❌ Gemini API não configurada")
        
    if serper_api_key and serper_api_key != "SUA_CHAVE_DO_SERPER_AQUI":
        st.success("✅ Busca Google News (Serper) Ativa")
    else:
        st.info("ℹ️ Modo de busca demonstrativo ativo")

# --- 1. ENTRADA DO USUÁRIO ---
termo_busca = st.text_input("O que você deseja pesquisar?", placeholder="Ex: eleições 2026, tecnologia...")

def buscar_noticias_36h(query, api_key):
    """Busca notícias/documentos publicados nas últimas 36h."""
    if not api_key or api_key == "SUA_CHAVE_DO_SERPER_AQUI":
        return [
            {"title": f"Últimas atualizações sobre {query} - Portal A", "link": "https://noticias.exemplo.com/materia-1", "snippet": "Análise detalhada das movimentações das últimas 24h.", "source": "Portal A"},
            {"title": f"Documento Oficial e Notas sobre {query}", "link": "https://gov.exemplo.br/documento-oficial", "snippet": "Publicação oficial do relatório atualizado.", "source": "Diário Oficial"},
            {"title": f"Análise Especial: Impactos de {query}", "link": "https://analise.exemplo.com/artigo-2", "snippet": "Especialistas discutem os desdobramentos mais recentes.", "source": "Blog de Análise"}
        ]
    
    url = "https://google.serper.dev/news"
    payload = {"q": f"{query} when:36h", "gl": "br", "hl": "pt-br"}
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        results = response.json().get('news', [])
        return [{"title": r.get('title'), "link": r.get('link'), "snippet": r.get('snippet'), "source": r.get('source')} for r in results]
    else:
        st.error("Erro na busca de notícias. Verifique a chave da API de busca.")
        return []

# --- 2. BUSCA E EXIBIÇÃO ---
if st.button("Buscar conteúdos (Últimas 36h)", type="primary"):
    if not termo_busca:
        st.warning("Por favor, digite um assunto para pesquisar.")
    else:
        with st.spinner("Buscando fontes e produções documentais recentes..."):
            st.session_state['resultados'] = buscar_noticias_36h(termo_busca, serper_api_key)
            st.session_state['termo_pesquisado'] = termo_busca

# --- 3. SELEÇÃO COM CHECKBOXES (FLAGS) ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    st.subheader(f"Resultados encontrados para: '{st.session_state['termo_pesquisado']}'")
    st.write("Marque as fontes e produções documentais que deseja analisar:")

    fontes_selecionadas = []
    
    for idx, item in enumerate(st.session_state['resultados']):
        col1, col2 = st.columns([0.05, 0.95])
        with col1:
            marcado = st.checkbox("", key=f"flag_{idx}", value=True)
        with col2:
            st.markdown(f"**[{item['title']}]({item['link']})** - *Fonte: {item['source']}*")
            st.caption(item['snippet'])
            st.write("---")
        
        if marcado:
            fontes_selecionadas.append(item)

    # --- 4. CONEXÃO COM O GEMINI & PROCESSAMENTO ---
    st.subheader("🚀 Processamento e Análise no Gemini")
    
    if fontes_selecionadas:
        st.success(f"{len(fontes_selecionadas)} fonte(s) selecionada(s).")
        
        col_acao1, col_acao2 = st.columns(2)
        with col_acao1:
            modelo_consumo = st.selectbox(
                "Escolha o modelo de consumo da pesquisa:",
                [
                    "Resumo Executivo Geral",
                    "Linha do Tempo dos Fatos",
                    "Análise Crítica e Pontos de Vista",
                    "Perguntas e Respostas (FAQ)",
                    "Roteiro de Apresentação / Briefing"
                ]
            )
            
        with col_acao2:
            st.write(" ")
            st.write(" ")
            enviar_notebook = st.button("Analisar com o Gemini", type="primary")

        if enviar_notebook:
            if not gemini_api_key or gemini_api_key == "SUA_CHAVE_DO_GEMINI_AQUI":
                st.error("Configure a Gemini API Key para continuar.")
            else:
                with st.spinner("Sintetizando fontes e gerando o relatório..."):
                    try:
                        genai.configure(api_key=gemini_api_key)
                        
                        contexto_fontes = "\n\n".join([
                            f"Título: {f['title']}\nFonte: {f['source']}\nLink: {f['link']}\nTrecho: {f['snippet']}"
                            for f in fontes_selecionadas
                        ])
                        
                        prompt_sistema = f"""
                        Você é um assistente de pesquisa especializado.
                        Analise as seguintes fontes sobre '{st.session_state['termo_pesquisado']}' coletadas nas últimas 36 horas:

                        --- FONTES COLETADAS ---
                        {contexto_fontes}
                        --- FIM DAS FONTES ---

                        Elabore uma resposta estruturada seguindo o formato: {modelo_consumo}.
                        Sempre cite as fontes/links fornecidos quando mencionar informações específicas.
                        """
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt_sistema)
                        
                        # Salva o resultado na sessão para não perder no refresh
                        st.session_state['relatorio_gerado'] = response.text
                        st.session_state['modelo_escolhido'] = modelo_consumo
                        
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao processar com a API do Gemini: {e}")

        # --- EXIBIÇÃO DO RELATÓRIO E BOTÃO DE DOWNLOAD ---
        if 'relatorio_gerado' in st.session_state:
            st.balloons()
            st.subheader(f"📑 Resultado: {st.session_state['modelo_escolhido']}")
            st.markdown(st.session_state['relatorio_gerado'])

            # Prepara o conteúdo em formato legível de texto
            data_atual = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
            conteudo_download = f"""================================================================================
RELATÓRIO DE PESQUISA: {st.session_state['termo_pesquisado'].upper()}
Modelo de Consumo: {st.session_state['modelo_escolhido']}
Data da Pesquisa: {data_atual}
================================================================================

{st.session_state['relatorio_gerado']}

================================================================================
Fontes Utilizadas na Análise:
"""
            for f in fontes_selecionadas:
                conteudo_download += f"- {f['title']} ({f['source']}): {f['link']}\n"

            # Nome do arquivo de download
            nome_arquivo = f"pesquisa_{st.session_state['termo_pesquisado'].lower().replace(' ', '_')}.txt"

            st.write("---")
            st.download_button(
                label="📥 Baixar Relatório em Arquivo de Texto (.txt)",
                data=conteudo_download,
                file_name=nome_arquivo,
                mime="text/plain",
                type="secondary"
            )

    else:
        st.warning("Selecione pelo menos uma fonte para continuar.")
