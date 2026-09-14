import os
import io
import datetime
import requests
import streamlit as st
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Pesquisador Acadêmico & Gemini", page_icon="🎓", layout="wide")

st.title("🎓 Pesquisador Acadêmico (Busca Nativa Gemini & Drive)")
st.markdown("Busca artigos científicos em português no Google Acadêmico/Web nativamente pelo Gemini, baixa os PDFs e organiza no seu Google Drive.")

# ==============================================================================
# CONFIGURAÇÃO DE CHAVES E TOKENS
# ==============================================================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
GOOGLE_DRIVE_TOKEN = st.secrets.get("GOOGLE_DRIVE_TOKEN", None)

# --- FUNÇÃO 1: DOWNLOAD DO PDF ---
def baixar_pdf(url):
    """Tenta realizar o download do PDF a partir de um link."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if res.status_code == 200 and ('pdf' in res.headers.get('Content-Type', '').lower() or url.lower().endswith('.pdf')):
            return res.content
    except Exception:
        pass
    return None

# --- FUNÇÃO 2: CRIAR PASTA E SALVAR NO GOOGLE DRIVE ---
def salvar_no_google_drive(nome_pesquisa, arquivos_pdf):
    """Cria pasta 'nome-da-pesquisa_DD/MM/AAAA' e envia os PDFs."""
    if not GOOGLE_DRIVE_TOKEN:
        st.info("ℹ️ Token do Google Drive não configurado nos Secrets. Etapa do Drive ignorada.")
        return None

    try:
        creds = Credentials.from_authorized_user_info(GOOGLE_DRIVE_TOKEN)
        service = build('drive', 'v3', credentials=creds)

        data_atual = datetime.datetime.now().strftime("%d-%m-%Y")
        nome_pasta = f"{nome_pesquisa}_{data_atual}"

        folder_metadata = {
            'name': nome_pasta,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')

        for pdf in arquivos_pdf:
            file_metadata = {
                'name': pdf['filename'],
                'parents': [folder_id]
            }
            media = MediaIoBaseUpload(io.BytesIO(pdf['bytes']), mimetype='application/pdf')
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return folder_id
    except Exception as e:
        st.error(f"Erro ao salvar no Google Drive: {e}")
        return None

# --- INTERFACE PRINCIPAL ---
termo_busca = st.text_input("Digite o tema da pesquisa acadêmica:", placeholder="Ex: inteligência artificial na saúde pública")

if st.button("Executar Pesquisa e Fluxo de Trabalho", type="primary"):
    if not termo_busca:
        st.warning("Por favor, digite um tema.")
    elif not GEMINI_API_KEY:
        st.error("Configure sua GEMINI_API_KEY nos Secrets do Streamlit Cloud.")
    else:
        st.markdown("---")
        client = genai.Client(api_key=GEMINI_API_KEY)

        # PASSO 1: Busca Nativa do Google Acadêmico via Gemini com Google Search Grounding
        with st.spinner("1/3 - Buscando os 5 principais artigos acadêmicos em português..."):
            prompt_busca = f"""
            Pesquise no Google Acadêmico exatamente 5 artigos científicos e produções acadêmicas em PORTUGUÊS (Brasil) sobre o tema: "{termo_busca}".
            
            Para cada um dos 5 artigos encontrados, forneça:
            1. Título do artigo
            2. Nome da publicação/revista/repositório
            3. Resumo com as descobertas principais
            4. Link direto/URL acessível para visualização ou download do PDF (priorize links diretos de .pdf de fontes como Scielo, Google Scholar, ResearchGate ou repositórios universitários .edu.br / .br)
            """

            try:
                # Habilita a ferramenta de busca do Google
                response_busca = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_busca,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )

                st.subheader("📚 Fontes e Artigos Encontrados:")
                st.markdown(response_busca.text)

                # Extrai links informados nas fontes da resposta Grounding
                urls_encontradas = []
                if response_busca.candidates and response_busca.candidates[0].grounding_metadata:
                    metadata = response_busca.candidates[0].grounding_metadata
                    if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, 'web') and chunk.web and chunk.web.uri:
                                urls_encontradas.append(chunk.web.uri)

                # Remove URLs duplicadas
                urls_encontradas = list(dict.fromkeys(urls_encontradas))[:5]

                if urls_encontradas:
                    st.subheader("🔗 Links/URLs Diretas das Fontes:")
                    for idx, url in enumerate(urls_encontradas, 1):
                        st.write(f"{idx}. [{url}]({url})")

            except Exception as e:
                st.error(f"Erro ao consultar a API do Gemini: {e}")
                st.stop()

        # PASSO 2: Tentativa de Download e Envio para o Drive
        with st.spinner("2/3 - Tentando baixar os arquivos PDF e salvar no Google Drive..."):
            pdfs_baixados = []
            for idx, url in enumerate(urls_encontradas, 1):
                pdf_bytes = baixar_pdf(url)
                if pdf_bytes:
                    nome_arq = f"Artigo_{idx}_{termo_busca.replace(' ', '_')}.pdf"
                    pdfs_baixados.append({"filename": nome_arq, "bytes": pdf_bytes})

            if pdfs_baixados:
                st.success(f"{len(pdfs_baixados)} PDF(s) baixados com sucesso!")
                folder_id = salvar_no_google_drive(termo_busca, pdfs_baixados)
                if folder_id:
                    st.success("📁 Pasta criada e arquivos enviados para o Google Drive com sucesso!")
            else:
                st.warning("Nenhum PDF direto editável pôde ser baixado automaticamente dos links encontrados. Prosseguindo para a geração do roteiro com base nas fontes sumarizadas.")

        # PASSO 3: Geração do Roteiro de Podcast (Audio Overview)
        with st.spinner("3/3 - Gerando o Roteiro do Podcast baseado nas 5 fontes..."):
            try:
                prompt_podcast = f"""
                Você é um roteirista de podcasts científicos.
                Com base nos 5 artigos acadêmicos analisados acima sobre o tema "{termo_busca}":

                Conteúdo dos artigos pesquisados:
                {response_busca.text}

                Crie um ROTEIRO COMPLETO E DETALHADO DE PODCAST (Audio Overview) entre 2 apresentadores:
                - **Apresentador 1 (Anfitrião):** Conduz o programa, faz perguntas inteligentes e conecta os assuntos.
                - **Apresentador 2 (Especialista):** Explica os métodos, conceitos e conclusões das pesquisas de forma didática.

                Escreva em português do Brasil, em tom engajador, profissional e fluido.
                """

                response_podcast = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_podcast
                )

                st.markdown("---")
                st.subheader("🎙️ Roteiro de Podcast Gerado")
                st.markdown(response_podcast.text)

                st.download_button(
                    label="📥 Baixar Roteiro (.txt)",
                    data=response_podcast.text,
                    file_name=f"roteiro_podcast_{termo_busca.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"Erro ao gerar o roteiro do podcast: {e}")
