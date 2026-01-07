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

# --- ÁREA DE SEGURANÇA ---
URL_DO_SUPABASE = "COLE_A_URL_DO_SUPABASE_AQUI" 
CHAVE_DO_SUPABASE = "COLE_A_KEY_ANON_PUBLIC_AQUI"
CHAVE_DO_GOOGLE = "COLE_A_CHAVE_AIZA_AQUI"

# --- CONEXÃO BANCO DE DADOS ---
@st.cache_resource
def init_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        if "COLE_A" not in URL_DO_SUPABASE:
            return create_client(URL_DO_SUPABASE, CHAVE_DO_SUPABASE)
        return None

supabase = init_supabase()

# --- CONEXÃO IA ---
def config_gemini():
    try:
        key = st.secrets["GOOGLE_API_KEY"]
    except:
        key = CHAVE_DO_GOOGLE
    
    if key and "COLE_A" not in key:
        genai.configure(api_key=key)
        return True
    return False

tem_gemini = config_gemini()

# --- MOTOR DE PDF 2.0 (AGORA COM DADOS COMPLETOS) ---
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

def gerar_pdf_pedido(dados_pedido, catalogo_df, cliente_info=None):
    pdf = PDF()
    pdf.add_page()
    
    # 1. DADOS DO PEDIDO
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"PEDIDO DE VENDA", 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
    pdf.ln(5)
    
    # 2. DADOS DO CLIENTE (COMPLETO)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 35, 'F') # Caixa cinza de fundo
    
    pdf.set_font("Arial", 'B', 10)
    cliente_nome = dados_pedido.get('cliente', 'Consumidor')
    pdf.cell(20, 8, "Cliente:", 0, 0)
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 8, cliente_nome, 0, 1)
    
    if cliente_info:
        # Linha 2
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(15, 6, "CNPJ:", 0, 0)
        pdf.set_font("Arial", size=10)
        pdf.cell(50, 6, str(cliente_info.get('cnpj', '')), 0, 0)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(10, 6, "IE:", 0, 0)
        pdf.set_font("Arial", size=10)
        pdf.cell(50, 6, str(cliente_info.get('inscricao_estadual', '')), 0, 1)
        
        # Linha 3
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(20, 6, "Endereco:", 0, 0)
        pdf.set_font("Arial", size=10)
        pdf.cell(100, 6, f"{cliente_info.get('endereco', '')} - {cliente_info.get('cidade', '')}/{cliente_info.get('estado', '')}", 0, 1)

        # Linha 4
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(15, 6, "Email:", 0, 0)
        pdf.set_font("Arial", size=10)
        pdf.cell(80, 6, str(cliente_info.get('email_xml', '')), 0, 0)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(15, 6, "Tel:", 0, 0)
        pdf.set_font("Arial", size=10)
        pdf.cell(50, 6, str(cliente_info.get('whatsapp_comprador', '')), 0, 1)
    
    pdf.ln(10)
    
    # 3. TABELA DE ITENS
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(25, 8, "SKU", 1, 0, 'C', 1)
    pdf.cell(85, 8, "DESCRICAO", 1, 0, 'L', 1)
    pdf.cell(15, 8, "QTD", 1, 0, 'C', 1)
    pdf.cell(30, 8, "UNIT (R$)", 1, 0, 'R', 1)
    pdf.cell(35, 8, "TOTAL (R$)", 1, 1, 'R', 1)
    
    pdf.set_font("Arial", size=9)
    total_geral = 0
    
    for item in dados_pedido.get('itens', []):
        sku = item.get('sku', '')
        qtd = int(item.get('qtd', 1))
        
        preco_unit = 0.0
        if not catalogo_df.empty:
            filtro = catalogo_df['sku'] == sku
            encontrados = catalogo_df[filtro]
            if not encontrados.empty:
                preco_unit = float(encontrados.iloc[0]['preco_tabela'])
            
        subtotal = preco_unit * qtd
        total_geral += subtotal
        
        pdf.cell(25, 8, str(sku)[:12], 1, 0, 'C')
        pdf.cell(85, 8, str(item.get('produto', ''))[:45], 1, 0, 'L')
        pdf.cell(15, 8, str(qtd), 1, 0, 'C')
        pdf.cell(30, 8, f"{preco_unit:.2f}", 1, 0, 'R')
        pdf.cell(35, 8, f"{subtotal:.2f}", 1, 1, 'R')
        
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(155, 10, "TOTAL DO PEDIDO:", 0, 0, 'R')
    pdf.cell(35, 10, f"R$ {total_geral:.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- CÉREBRO DA IA ---
def encontrar_modelo_disponivel():
    modelos = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos.append(m.name)
                if 'flash' in m.name or '1.5' in m.name: return m.name
        if modelos: return modelos[0]
    except: pass
    return 'gemini-pro'

def processar_pedido_gemini(texto_cliente, catalogo_str):
    try:
        nome_modelo = encontrar_modelo_disponivel()
        model = genai.GenerativeModel(nome_modelo)
        
        prompt = f"""
        Responda APENAS JSON.
        CATÁLOGO: {catalogo_str}
        PEDIDO: "{texto_cliente}"
        JSON:
        {{
          "cliente": "Nome Identificado (Ou razao social)",
          "itens": [ {{ "sku": "...", "produto": "...", "qtd": 1 }} ],
          "analise": "Resumo"
        }}
        """
        response = model.generate_content(prompt)
        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(texto_limpo)
        except:
            return {"erro": "IA falhou no JSON", "bruto": texto_limpo}
    except Exception as e:
        return {"erro": f"Erro Técnico: {str(e)}"}

# --- MENU ---
with st.sidebar:
    st.title("🦁 Fantini OS")
    st.caption("v5.0 Enterprise")
    st.markdown("---")
    menu = st.radio("Navegação", ["Dashboard", "Clientes (Novo)", "Produtos", "Agente de Vendas"])
    st.markdown("---")
    st.success("Sistema Online")

# --- PÁGINAS ---

if menu == "Dashboard":
    st.header("📊 Visão Executiva")
    if supabase:
        df = pd.DataFrame(supabase.table('produtos').select("*").execute().data)
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Estoque Total", f"R$ {df['preco_tabela'].sum():.2f}")
            c2.metric("SKUs Ativos", len(df))
            c3.metric("Meta", "R$ 100k")
            st.plotly_chart(px.bar(df, x='nome', y='estoque_atual', title="Nível de Estoque"))
        else:
            st.warning("Cadastre produtos primeiro.")

# --- CADASTRO DE CLIENTES COMPLETO ---
elif menu == "Clientes (Novo)":
    st.header("👥 Gestão de Carteira")
    
    tab1, tab2 = st.tabs(["📋 Listagem Geral", "➕ Novo Cadastro Completo"])
    
    with tab1:
        if supabase:
            resp = supabase.table('clientes').select("*").execute()
            df = pd.DataFrame(resp.data)
            if not df.empty:
                # Mostra colunas principais
                colunas_visiveis = ['razao_social', 'nome_fantasia', 'cnpj', 'cidade', 'whatsapp_comprador']
                # Filtra apenas colunas que existem no dataframe para não dar erro
                cols_reais = [c for c in colunas_visiveis if c in df.columns]
                st.dataframe(df[cols_reais], use_container_width=True)
            else:
                st.info("Nenhum cliente cadastrado.")

    with tab2:
        st.subheader("Ficha Cadastral")
        with st.form("form_cliente_completo"):
            st.markdown("**Dados Principais**")
            c1, c2 = st.columns(2)
            razao = c1.text_input("Razão Social *")
            fantasia = c2.text_input("Nome Fantasia")
            
            c3, c4, c5 = st.columns(3)
            cnpj = c3.text_input("CNPJ *")
            ie = c4.text_input("Inscrição Estadual")
            contato = c5.text_input("Nome do Contato")
            
            st.markdown("**Endereço & Contato**")
            c6, c7 = st.columns([2, 1])
            end = c6.text_input("Endereço Completo (Rua, Nº, Bairro)")
            cidade = c7.text_input("Cidade")
            
            c8, c9, c10 = st.columns(3)
            estado = c8.selectbox("UF", ["MG", "SP", "RJ", "ES", "BA", "RS", "SC", "PR", "GO", "DF"])
            zap = c9.text_input("WhatsApp *")
            email = c10.text_input("Email NFe (XML)")
            
            obs = st.text_area("Observações / Perfil")
            
            if st.form_submit_button("💾 Salvar Cliente"):
                if not razao or not cnpj:
                    st.error("Razão Social e CNPJ são obrigatórios.")
                else:
                    try:
                        dados = {
                            "razao_social": razao,
                            "nome_fantasia": fantasia,
                            "cnpj": cnpj,
                            "inscricao_estadual": ie,
                            "contato_nome": contato,
                            "endereco": end,
                            "cidade": cidade,
                            "estado": estado,
                            "whatsapp_comprador": zap,
                            "email_xml": email,
                            "perfil_compra": obs
                        }
                        supabase.table('clientes').insert(dados).execute()
                        st.success(f"Cliente {fantasia or razao} cadastrado com sucesso!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

elif menu == "Produtos":
    st.header("📦 Produtos")
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
                supabase.table('produtos').insert({"sku": sku, "nome": nome, "preco_tabela": preco, "estoque_atual": estoque}).execute()
                st.rerun()

elif menu == "Agente de Vendas":
    st.header("🧠 Pedido Inteligente")
    st.info("O sistema agora busca o cadastro completo do cliente para gerar o PDF.")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        texto = st.text_area("Digite o pedido:", height=200)
        btn = st.button("⚡ Processar", type="primary", use_container_width=True)
        
    with c2:
        if btn and supabase and tem_gemini:
            with st.spinner("Analisando..."):
                # 1. Busca Catálogo
                prods_db = supabase.table('produtos').select("*").execute().data
                
                # 2. IA Processa
                res = processar_pedido_gemini(texto, str(prods_db))
                
                if "erro" in res:
                    st.error(res['erro'])
                else:
                    st.success("Sucesso!")
                    
                    # 3. Tenta achar o cliente no banco pelo nome que a IA achou
                    nome_cliente_ia = res.get('cliente', '')
                    cliente_db = {}
                    
                    # Busca inteligente no banco (case insensitive simples)
                    if nome_cliente_ia and nome_cliente_ia != "Não identificado":
                        # Tenta buscar por parte do nome
                        resp_cli = supabase.table('clientes').select("*").ilike('razao_social', f"%{nome_cliente_ia}%").execute()
                        if not resp_cli.data:
                             # Tenta pelo nome fantasia
                             resp_cli = supabase.table('clientes').select("*").ilike('nome_fantasia', f"%{nome_cliente_ia}%").execute()
                        
                        if resp_cli.data:
                            cliente_db = resp_cli.data[0] # Pega o primeiro que achou
                            st.info(f"✅ Cliente vinculado: {cliente_db.get('razao_social')} ({cliente_db.get('cnpj')})")
                        else:
                            st.warning(f"Cliente '{nome_cliente_ia}' não encontrado no cadastro. O PDF sairá incompleto.")

                    if res.get('itens'):
                        st.dataframe(pd.DataFrame(res['itens']), use_container_width=True, hide_index=True)
                        try:
                            # Passa os dados do cliente para o PDF
                            pdf_bytes = gerar_pdf_pedido(res, pd.DataFrame(prods_db), cliente_info=cliente_db)
                            st.download_button("📄 BAIXAR PDF COMPLETO", pdf_bytes, "Pedido.pdf", "application/pdf", type="primary")
                        except Exception as e:
                            st.error(f"Erro PDF: {e}")