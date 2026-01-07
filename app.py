import streamlit as st
import pandas as pd
from supabase import create_client
import json
import google.generativeai as genai
import plotly.express as px
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Fantini OS | Enterprise", page_icon="🦁", layout="wide")

# --- ÁREA DE SEGURANÇA (COLE SUAS CHAVES AQUI) ---
# Deixe assim antes de subir:
URL_DO_SUPABASE = "COLE_A_URL_DO_SUPABASE_AQUI" 
CHAVE_DO_SUPABASE = "COLE_A_KEY_ANON_PUBLIC_AQUI"
CHAVE_DO_GOOGLE = "COLE_A_CHAVE_AIZA_AQUI"
# -----------------------------------------------

# --- CONEXÃO BANCO DE DADOS ---
@st.cache_resource
def init_supabase():
    try:
        if "COLE_A" not in URL_DO_SUPABASE:
            return create_client(URL_DO_SUPABASE, CHAVE_DO_SUPABASE)
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_supabase()

# --- CONEXÃO IA ---
def config_gemini():
    try:
        key = CHAVE_DO_GOOGLE if "COLE_A" not in CHAVE_DO_GOOGLE else st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=key)
        return True
    except:
        return False

tem_gemini = config_gemini()

# --- MOTOR DE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'FANTINI REPRESENTACOES', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'Solucoes em Audio e Hardware', 0, 1, 'C')
        self.line(10, 30, 200, 30)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def gerar_pdf_pedido(dados_pedido, catalogo_df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Cabeçalho do Pedido
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"PEDIDO DE VENDA - {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Cliente: {dados_pedido.get('cliente', 'Nao Informado')}", 0, 1)
    pdf.ln(5)
    
    # Cabeçalho da Tabela
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 10, "SKU", 1, 0, 'C', 1)
    pdf.cell(90, 10, "Produto", 1, 0, 'C', 1)
    pdf.cell(20, 10, "Qtd", 1, 0, 'C', 1)
    pdf.cell(25, 10, "Unit (R$)", 1, 0, 'C', 1)
    pdf.cell(25, 10, "Total (R$)", 1, 1, 'C', 1)
    
    pdf.set_font("Arial", size=10)
    total_geral = 0
    
    # Loop de Itens Seguro
    for item in dados_pedido.get('itens', []):
        sku = item.get('sku', '')
        qtd = int(item.get('qtd', 1))
        
        # Busca Preço
        preco_unit = 0.0
        if not catalogo_df.empty:
            filtro = catalogo_df['sku'] == sku
            encontrados = catalogo_df[filtro]
            if not encontrados.empty:
                preco_unit = float(encontrados.iloc[0]['preco_tabela'])
            
        subtotal = preco_unit * qtd
        total_geral += subtotal
        
        # Desenha Linha
        pdf.cell(30, 10, str(sku)[:15], 1)
        pdf.cell(90, 10, str(item.get('produto', ''))[:40], 1)
        pdf.cell(20, 10, str(qtd), 1, 0, 'C')
        pdf.cell(25, 10, f"{preco_unit:.2f}", 1, 0, 'R')
        pdf.cell(25, 10, f"{subtotal:.2f}", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(165, 10, "TOTAL:", 0, 0, 'R')
    pdf.cell(25, 10, f"R$ {total_geral:.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- CÉREBRO DA IA (MODO SEGURO / FALLBACK) ---
def processar_pedido_gemini(texto_cliente, catalogo_str):
    prompt = f"""
    Responda APENAS com JSON.
    CATÁLOGO: {catalogo_str}
    PEDIDO: "{texto_cliente}"
    JSON:
    {{
      "cliente": "Nome Identificado",
      "itens": [ {{ "sku": "...", "produto": "...", "qtd": 1 }} ],
      "analise": "Resumo"
    }}
    """
    
    try:
        # TENTATIVA 1: Modelo Flash (Mais Rápido)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
    except Exception:
        try:
            # TENTATIVA 2: Modelo Pro (Mais Estável - Fallback)
            print("⚠️ Flash falhou, trocando para Gemini Pro...")
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
        except Exception as e:
            return {"erro": f"Todos os modelos falharam: {str(e)}"}

    try:
        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except:
        return {"erro": "Erro ao ler JSON da IA", "bruto": response.text}

# --- MENU ---
with st.sidebar:
    st.title("🦁 Fantini OS")
    st.markdown("---")
    menu = st.radio("Menu", ["Dashboard", "Produtos", "Clientes", "Agente de Vendas"])
    st.markdown("---")
    st.success(f"Sistema Online")

# --- PÁGINAS ---

if menu == "Dashboard":
    st.header("📊 Visão Executiva")
    if supabase:
        df = pd.DataFrame(supabase.table('produtos').select("*").execute().data)
        if not df.empty:
            c1, c2 = st.columns(2)
            c1.metric("Valor Estoque", f"R$ {df['preco_tabela'].sum():.2f}")
            c2.metric("Total SKUs", len(df))
            st.plotly_chart(px.bar(df, x='nome', y='estoque_atual', title="Estoque"))
        else:
            st.warning("Cadastre produtos na aba 'Produtos'.")

elif menu == "Produtos":
    st.header("📦 Gestão de Catálogo")
    tab1, tab2 = st.tabs(["Lista", "Novo"])
    with tab1:
        if supabase:
            df = pd.DataFrame(supabase.table('produtos').select("*").execute().data)
            if not df.empty: st.dataframe(df, use_container_width=True)
    with tab2:
        with st.form("novo_prod"):
            sku = st.text_input("SKU")
            nome = st.text_input("Nome")
            preco = st.number_input("Preço", min_value=0.0)
            estoque = st.number_input("Estoque", min_value=0)
            if st.form_submit_button("Salvar"):
                supabase.table('produtos').insert({
                    "sku": sku, "nome": nome, 
                    "preco_tabela": preco, "estoque_atual": estoque
                }).execute()
                st.rerun()

elif menu == "Clientes":
    st.header("👥 Clientes")
    tab1, tab2 = st.tabs(["Lista", "Novo"])
    with tab1:
        if supabase:
            df = pd.DataFrame(supabase.table('clientes').select("*").execute().data)
            if not df.empty: st.dataframe(df, use_container_width=True)
    with tab2:
        with st.form("novo_cli"):
            razao = st.text_input("Nome")
            zap = st.text_input("WhatsApp")
            if st.form_submit_button("Salvar"):
                supabase.table('clientes').insert({
                    "razao_social": razao, 
                    "whatsapp_comprador": zap, 
                    "cnpj": "ISENTO"
                }).execute()
                st.rerun()

elif menu == "Agente de Vendas":
    st.header("🧠 Gerador de Pedidos IA")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        texto = st.text_area("Pedido:", height=200, placeholder="Ex: 5 Pioneer pro Kyra")
        btn = st.button("⚡ Processar", type="primary", use_container_width=True)
        
    with c2:
        if btn and supabase and tem_gemini:
            with st.spinner("Gerando PDF..."):
                prods_db = supabase.table('produtos').select("*").execute().data
                res = processar_pedido_gemini(texto, str(prods_db))
                
                if "erro" in res:
                    st.error(res['erro'])
                else:
                    st.success("Sucesso!")
                    if res.get('itens'):
                        st.dataframe(pd.DataFrame(res['itens']), use_container_width=True, hide_index=True)
                        try:
                            pdf_bytes = gerar_pdf_pedido(res, pd.DataFrame(prods_db))
                            st.download_button("📄 BAIXAR PDF", pdf_bytes, "Pedido.pdf", "application/pdf", type="primary")
                        except Exception as e:
                            st.error(f"Erro PDF: {e}")