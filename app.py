import os
import requests
import datetime
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Pesquisador Acadêmico & Gemini", page_icon="🎓", layout="wide")

st.title("🎓 Pesquisador Acadêmico & Gerador de Podcast")
st.markdown("Busca 5 artigos em português no Google Acadêmico via Gemini, disponibiliza o download dos PDFs e gera o roteiro de podcast automaticamente.")

# ==============================================================================
# CHAVE DE API DO GEMINI
# ==============================================================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()

# --- FUNÇÃO DE DOWNLOAD DO PDF ---
@st.cache_data(show_spinner=False)
def baixar_pdf(url):
    """Tenta baixar o PDF para disponibilizar o botão no Streamlit."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

# --- ENTRADA DO USUÁRIO ---
termo_busca = st.text_input("Qual o tema da pesquisa acadêmica?", placeholder="Ex: inteligência artificial na educação")

if st.button("Executar Pesquisa e Gerar Podcast", type="primary"):
    if not termo_busca:
        st.warning("Por favor, digite um tema para pesquisar.")
    elif not GEMINI_API_KEY:
        st.error("Configure a GEMINI_API_KEY nos Secrets do Streamlit Cloud.")
    else:
        st.markdown("---")
        client = genai.Client(api_key=GEMINI_API_KEY)

        # PASSO 1: Busca Nativa no Google Acadêmico via Gemini (Sem Serper)
        with st.spinner("1/2 - Buscando os 5 principais artigos científicos em português..."):
            prompt_busca = f"""
            Pesquise no Google Acadêmico exatamente 5 artigos científicos e produções acadêmicas em PORTUGUÊS (Brasil) sobre o tema: "{termo_busca}".
            
            Para cada artigo encontrado, apresente:
            1. Título do Artigo
            2. Publicação / Revista / Instituição
            3. Breve Resumo das descobertas principais
            4. Link/URL direto para o arquivo .pdf ou acesso ao artigo em repositórios (como SciELO, Google Scholar, universidades .br).
            """

            try:
                # Usa a busca nativa do Google integrada ao Gemini
                response_busca = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_busca,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )

                st.subheader("📚 5 Artigos Acadêmicos Encontrados:")
                st.markdown(response_busca.text)

                # Extrai links de fontes da busca
                urls_encontradas = []
                if response_busca.candidates and response_busca.candidates[0].grounding_metadata:
                    metadata = response_busca.candidates[0].grounding_metadata
                    if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, 'web') and chunk.web and chunk.web.uri:
                                urls_encontradas.append(chunk.web.uri)

                urls_encontradas = list(dict.fromkeys(urls_encontradas))[:5]

                # Exibe botões para download dos PDFs encontrados
                if urls_encontradas:
                    st.write("---")
                    st.subheader("📄 Downloads dos PDFs Acessíveis:")
                    for idx, url in enumerate(urls_encontradas, 1):
                        pdf_bytes = baixar_pdf(url)
                        col_link, col_down = st.columns([0.7, 0.3])
                        with col_link:
                            st.write(f"**{idx}.** [{url}]({url})")
                        with col_down:
                            if pdf_bytes:
                                st.download_button(
                                    label="📄 Baixar PDF",
                                    data=pdf_bytes,
                                    file_name=f"artigo_{idx}_{termo_busca.replace(' ', '_')}.pdf",
                                    mime="application/pdf",
                                    key=f"down_{idx}"
                                )
                            else:
                                st.caption("Download direto bloqueado pelo site")

            except Exception as e:
                st.error(f"Erro ao realizar a busca com o Gemini: {e}")
                st.stop()

        # PASSO 2: Geração do Roteiro de Podcast (Audio Overview)
        with st.spinner("2/2 - Gerando o Roteiro do Podcast..."):
            try:
                prompt_podcast = f"""
                Você é um roteirista de podcasts acadêmicos e educacionais.
                Com base no conteúdo dos 5 artigos científicos pesquisados sobre "{termo_busca}":

                RESUMO DOS ARTIGOS:
                {response_busca.text}

                Crie um ROTEIRO COMPLETO DE PODCAST (estilo Audio Overview / NotebookLM) entre 2 apresentadores:
                - **Apresentador A (Anfitrião):** Conduz a conversa de forma entusiasmada, faz perguntas reflexivas e liga os temas.
                - **Apresentador B (Especialista):** Explica os resultados, métodos e conclusões dos artigos científicos de forma simples e didática.

                Escreva em português do Brasil, mantendo uma conversa natural, fluida e envolvente.
                """

                response_podcast = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_podcast
                )

                st.markdown("---")
                st.subheader("🎙️ Roteiro de Podcast Gerado")
                st.markdown(response_podcast.text)

                # Download do Roteiro em TXT
                st.download_button(
                    label="📥 Baixar Roteiro do Podcast (.txt)",
                    data=response_podcast.text,
                    file_name=f"roteiro_podcast_{termo_busca.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"Erro ao gerar o roteiro do podcast: {e}")
