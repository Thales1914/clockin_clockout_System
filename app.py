import streamlit as st
import pandas as pd
import time
from datetime import date, datetime
from services import (
    init_db,
    ler_registros_df,
    bater_ponto,
    verificar_login,
    obter_proximo_evento,
    atualizar_registro,
    ler_funcionarios_df,
    adicionar_funcionario,
    gerar_relatorio_organizado_df,
    gerar_arquivo_excel,
    ler_empresas,
    importar_funcionarios_em_massa
)

init_db()

st.set_page_config(
    page_title="Ponto Omega",
    page_icon="assets/logo.png",
    layout="wide"
)

def carregar_css_customizado():
    st.markdown("""
        <style>
            div[data-testid="stTextInput"] { max-width: 450px; margin: auto; }
            div[data-testid="stButton"] { max-width: 450px; margin: auto; }
            div[data-testid="stVerticalBlock"] div[data-testid="stContainer"][style*="border: 1px solid"] {
                padding-top: 1em !important; padding-bottom: 1em !important; margin-bottom: 10px !important;
            }
            div[data-testid="stAlert"][kind="info"] { background-color: #262730; border-radius: 10px; }
            button[data-testid="stTab"][aria-selected="true"] { color: #FFFFFF; }
            div[data-testid="stTabs"] button[aria-selected="true"]::after { background-color: #FFFFFF; }
            div[data-testid="stFormSubmitButton"] button {
                background-color: #F27421; color: #FFFFFF; border: none;
            }
            div[data-testid="stFormSubmitButton"] button:hover {
                background-color: #d8661c; color: #FFFFFF; border: none;
            }
        </style>
    """, unsafe_allow_html=True)

carregar_css_customizado()

if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
if 'status_message' not in st.session_state:
    st.session_state.status_message = None

def tela_de_login():
    with st.container():
        _ , col2, _ = st.columns([1, 2, 1])
        with col2:
            st.image("assets/logo.png", width=350)
            st.text("") 
            codigo = st.text_input("Seu Código", label_visibility="collapsed", placeholder="Seu Código")
            senha = st.text_input("Sua Senha", type="password", label_visibility="collapsed", placeholder="Sua Senha")
            if st.button("Entrar", type="primary", use_container_width=True):
                if codigo and senha:
                    user_info, erro = verificar_login(codigo, senha)
                    if erro: 
                        st.error(erro)
                    else:
                        st.session_state.user_info = user_info
                        st.session_state.user_info['codigo'] = codigo
                        st.rerun()
                else:
                    st.warning("Por favor, preencha todos os campos.")

def tela_funcionario():
    st.title(f"Bem-vindo, {st.session_state.user_info['nome']}!")
    tab1, tab2 = st.tabs(["Registrar Ponto", "Meus Registros"])
    with tab1:
        st.header("Registro de Ponto")
        proximo_evento = obter_proximo_evento(st.session_state.user_info['codigo'])
        if proximo_evento == "Jornada Finalizada":
            st.info("Sua jornada de hoje já foi completamente registrada. Bom descanso!")
        else:
            if st.button(f"Confirmar {proximo_evento}", type="primary", use_container_width=True):
                mensagem, tipo = bater_ponto(
                    st.session_state.user_info['codigo'],
                    st.session_state.user_info['nome']
                )
                if tipo == "success":
                    st.success(mensagem)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(mensagem)
    with tab2:
        st.header("Histórico dos Meus Pontos")
        df_todos_registros = ler_registros_df()
        meus_registros_df = df_todos_registros[df_todos_registros['Código'] == st.session_state.user_info['codigo']]
        if meus_registros_df.empty:
            st.info("Você ainda não possui registros de ponto.")
        else:
            df_visualizacao = meus_registros_df.sort_values(by=["Data", "Hora"], ascending=False)
            for _, row in df_visualizacao.iterrows():
                with st.container(border=True):
                    data_br = datetime.strptime(row['Data'], '%Y-%m-%d').strftime('%d/%m/%Y')
                    diff = row['Diferença (min)']
                    cor_diff = "green" if diff == 0 else "red" if diff > 0 else "Yellow"
                    texto_diff = "Em ponto" if diff == 0 else f"{'+' if diff > 0 else ''}{diff} min ({'atraso' if diff > 0 else 'adiantado'})"
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 4])
                    col1.text(f"Evento: {row['Descrição']}")
                    col2.text(f"Data: {data_br}")
                    col3.text(f"Hora: {row['Hora']}")
                    col4.markdown(f"Status: **<font color='{cor_diff}'>{texto_diff}</font>**", unsafe_allow_html=True)
                    if row.get('Observação'):
                        st.markdown(f"**Obs:** *{row['Observação']}*")

def tela_admin():
    st.title("Painel do Administrador")
    if st.session_state.status_message:
        msg, tipo = st.session_state.status_message
        if tipo == "success": st.success(msg)
        elif tipo == "warning": st.warning(msg)
        else: st.error(msg)
        st.session_state.status_message = None

    tab1, tab2, tab3, tab4 = st.tabs(["Relatório de Pontos", "Cadastrar Funcionário", "Visualizar Funcionários", "Importar Funcionários"])
    with tab1:
        st.header("Filtros do Relatório")
        empresas_df = ler_empresas()
        opcoes_empresas = {0: "Todas as Empresas"}
        opcoes_empresas.update(dict(zip(empresas_df['id'], empresas_df['nome_empresa'])))
        col1_filtros, col2_filtros, col3_filtros = st.columns(3)
        with col1_filtros:
            empresa_selecionada_id = st.selectbox(
                "Filtrar por empresa:",
                options=list(opcoes_empresas.keys()),
                format_func=lambda x: opcoes_empresas[x]
            )
        with col2_filtros:
            data_inicio = st.date_input("Data Início", value=date.today().replace(day=1), format="DD/MM/YYYY")
        with col3_filtros:
            data_fim = st.date_input("Data Fim", value=date.today(), format="DD/MM/YYYY")
        st.divider()
        st.header("Relatório de Pontos")
        funcionarios_df = ler_funcionarios_df()
        df_registros = ler_registros_df()
        if empresa_selecionada_id != 0:
            codigos_funcionarios_empresa = funcionarios_df[funcionarios_df['empresa_id'] == empresa_selecionada_id]['codigo'].tolist()
        else:
            codigos_funcionarios_empresa = funcionarios_df[funcionarios_df['role'] == 'employee']['codigo'].tolist()
        df_filtrado_empresa = df_registros[df_registros['Código'].isin(codigos_funcionarios_empresa)]
        df_filtrado_empresa['Data_dt'] = pd.to_datetime(df_filtrado_empresa['Data'], format='%Y-%m-%d').dt.date
        df_filtrado_data = df_filtrado_empresa[(df_filtrado_empresa['Data_dt'] >= data_inicio) & (df_filtrado_empresa['Data_dt'] <= data_fim)].copy()
        opcoes_funcionarios_filtrados = {"Todos": "Todos"}
        for _, row in funcionarios_df[funcionarios_df['codigo'].isin(codigos_funcionarios_empresa)].iterrows():
            opcoes_funcionarios_filtrados[row['codigo']] = f"{row['nome']} (Cód: {row['codigo']})"
        codigo_selecionado = st.selectbox(
            "Filtrar por funcionário (opcional):",
            options=list(opcoes_funcionarios_filtrados.keys()),
            format_func=lambda x: opcoes_funcionarios_filtrados[x]
        )
        df_final_filtrado = df_filtrado_data.copy()
        if codigo_selecionado != "Todos":
            df_final_filtrado = df_final_filtrado[df_final_filtrado['Código'] == codigo_selecionado]
        if df_final_filtrado.empty:
            st.info("Nenhum registro encontrado para os filtros selecionados.")
        else:
            st.subheader("Visualização dos Eventos")
            df_visualizacao = df_final_filtrado.sort_values(by=["Data_dt", "Hora"], ascending=False)
            for index, row in df_visualizacao.iterrows():
                registro_id = row['ID']
                with st.container(border=True):
                    data_br = row['Data_dt'].strftime('%d/%m/%Y')
                    diff = row['Diferença (min)']
                    cor_diff = "green" if diff == 0 else "red" if diff > 0 else "lightgray"
                    texto_diff = "Em ponto" if diff == 0 else f"{'+' if diff > 0 else ''}{diff} min ({'atraso' if diff > 0 else 'adiantado'})"
                    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 1])
                    col1.text(f"Nome: {row['Nome']}")
                    col2.text(f"Evento: {row['Descrição']}")
                    col3.text(f"Data: {data_br}")
                    col4.markdown(f"Hora: {row['Hora']} | Status: **<font color='{cor_diff}'>{texto_diff}</font>**", unsafe_allow_html=True)
                    if col5.button("Editar", key=f"edit_{registro_id}"):
                        st.session_state.edit_id = registro_id
                        st.rerun()
                    if st.session_state.edit_id == registro_id:
                        edit_col1, edit_col2 = st.columns(2)
                        with edit_col1:
                            novo_horario = st.text_input("Nova Hora (HH:MM:SS):", value=row['Hora'], key=f"hora_{registro_id}")
                        with edit_col2:
                            nova_obs = st.text_area("Observação:", value=row.get('Observação', ''), key=f"obs_{registro_id}")
                        col_save, col_cancel, _ = st.columns([1, 1, 5])
                        if col_save.button("Salvar", key=f"save_{registro_id}", type="primary"):
                            horario_mudou = novo_horario.strip() != row['Hora'].strip()
                            obs_mudou = nova_obs.strip() != str(row.get('Observação', '')).strip()
                            if horario_mudou or obs_mudou:
                                horario_para_atualizar = novo_horario.strip() if horario_mudou else None
                                obs_para_atualizar = nova_obs.strip() if obs_mudou else None
                                msg, tipo = atualizar_registro(registro_id, novo_horario=horario_para_atualizar, nova_observacao=obs_para_atualizar)
                                st.session_state.status_message = (msg, tipo)
                            st.session_state.edit_id = None
                            st.rerun()
                        if col_cancel.button("Cancelar", key=f"cancel_{registro_id}"):
                            st.session_state.edit_id = None
                            st.rerun()
                    elif row.get('Observação'):
                        st.markdown(f"**Obs:** *{row['Observação']}*")
            st.divider()
            st.subheader("Exportar Relatório Completo")
            df_organizado = gerar_relatorio_organizado_df(df_final_filtrado)
            df_bruto = df_final_filtrado.sort_values(by=["Data_dt", "Hora"]).copy()
            df_bruto['Data'] = pd.to_datetime(df_bruto['Data']).dt.strftime('%d/%m/%Y')
            excel_buffer = gerar_arquivo_excel(df_organizado, df_bruto.drop(columns=['Data_dt']))
            st.download_button(
                label="📥 Baixar Relatório Filtrado em Excel",
                data=excel_buffer,
                file_name=f"relatorio_ponto_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet",
                use_container_width=True
            )
    with tab2:
        st.header("Cadastrar Novo Funcionário")
        empresas_df_cadastro = ler_empresas()
        empresas_para_cadastro = dict(zip(empresas_df_cadastro['id'], empresas_df_cadastro['nome_empresa']))
        with st.form("add_employee_form", clear_on_submit=True):
            empresa_id_cadastro = st.selectbox("Empresa do Funcionário", options=list(empresas_para_cadastro.keys()), format_func=lambda x: empresas_para_cadastro[x])
            novo_codigo = st.text_input("Código do Funcionário (único)")
            novo_nome = st.text_input("Nome Completo")
            nova_senha = st.text_input("Senha Provisória", type="password")
            submitted = st.form_submit_button("Adicionar Funcionário")
            if submitted:
                msg, tipo = adicionar_funcionario(novo_codigo.strip(), novo_nome.strip(), nova_senha, empresa_id_cadastro)
                st.session_state.status_message = (msg, tipo)
                st.rerun()
    with tab3:
        st.header("Funcionários Cadastrados no Sistema")
        todos_funcionarios_df = ler_funcionarios_df()
        df_exibicao = todos_funcionarios_df[todos_funcionarios_df['role'] == 'employee']
        if df_exibicao.empty:
            st.info("Nenhum funcionário cadastrado no sistema (além do administrador).")
        else:
            df_final = df_exibicao[['codigo', 'nome', 'nome_empresa']].rename(columns={'codigo': 'Código', 'nome': 'Nome', 'nome_empresa': 'Empresa'})
            st.dataframe(df_final, use_container_width=True, hide_index=True)
            
    with tab4:
        st.header("Importar Funcionários em Lote via CSV")
        st.info("O arquivo CSV precisa conter as colunas: `MATRICULA`, `COLABORADOR` e `SENHA`.")
        empresas_df_import = ler_empresas()
        empresas_para_import = dict(zip(empresas_df_import['id'], empresas_df_import['nome_empresa']))
        empresa_id_importacao = st.selectbox("Selecione a empresa para qual estes funcionários serão importados:", options=list(empresas_para_import.keys()), format_func=lambda x: empresas_para_import[x], key="empresa_import")
        arquivo_csv = st.file_uploader("Selecione o arquivo CSV", type=["csv"])
        if st.button("Iniciar Importação", type="primary", use_container_width=True):
            if arquivo_csv is not None and empresa_id_importacao is not None:
                with st.spinner("Processando arquivo..."):
                    try:
                        # --- CORREÇÃO APLICADA AQUI ---
                        df_para_importar = pd.read_csv(arquivo_csv, sep=';')
                        
                        df_para_importar.columns = [col.strip().upper() for col in df_para_importar.columns]
                        
                        sucesso, ignorados, erros = importar_funcionarios_em_massa(df_para_importar, empresa_id_importacao)
                        
                        st.success(f"{sucesso} funcionários importados com sucesso!")
                        if ignorados > 0:
                            st.warning(f"{ignorados} funcionários foram ignorados (matrícula já existente).")
                        if erros:
                            st.error("Ocorreram os seguintes erros durante a importação:")
                            for erro in erros:
                                st.code(erro)
                    except Exception as e:
                        st.error(f"Não foi possível ler o arquivo. Verifique se o formato está correto. Erro: {e}")
            else:
                st.warning("Por favor, selecione uma empresa e um arquivo CSV para continuar.")

if st.session_state.user_info:
    st.sidebar.image("assets/logo.png", use_container_width=True)
    if st.sidebar.button("Sair"):
        st.session_state.user_info = None
        st.session_state.edit_id = None
        st.session_state.status_message = None
        st.rerun()
    if st.session_state.user_info.get("role") == "admin":
        tela_admin()
    else:
        tela_funcionario()
else:
    tela_de_login()