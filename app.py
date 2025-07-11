import streamlit as st
import pandas as pd
import time
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
    gerar_arquivo_excel
)

init_db()

st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="wide"
)

if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
if 'status_message' not in st.session_state:
    st.session_state.status_message = None

def tela_de_login():
    st.header("Login do Sistema de Ponto")
    with st.container(border=False):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            codigo = st.text_input("Seu Código")
            senha = st.text_input("Sua Senha", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if codigo and senha:
                    user_info, erro = verificar_login(codigo, senha)
                    if erro: st.error(erro)
                    else:
                        st.session_state.user_info = user_info
                        st.session_state.user_info['codigo'] = codigo
                        st.rerun()
                else:
                    st.warning("Por favor, preencha todos os campos.")

def tela_funcionario():
    st.title(f"🔵 Bem-vindo, {st.session_state.user_info['nome']}!")
    st.header("Registo de Ponto")
    proximo_evento = obter_proximo_evento(st.session_state.user_info['codigo'])
    if proximo_evento == "Jornada Finalizada":
        st.info("Sua jornada de hoje já foi completamente registada. Bom descanso!")
    else:
        if st.button(f"Confirmar {proximo_evento}", type="primary", use_container_width=True):
            mensagem, tipo = bater_ponto(
                st.session_state.user_info['codigo'],
                st.session_state.user_info['nome'],
                st.session_state.user_info['cargo']
            )
            if tipo == "success":
                st.success(mensagem)
                time.sleep(1)
                st.rerun()
            else:
                st.error(mensagem)

def tela_admin():
    st.title("🔵 Painel do Administrador")

    if st.session_state.status_message:
        msg, tipo = st.session_state.status_message
        if tipo == "success":
            st.success(msg)
        elif tipo == "warning":
            st.warning(msg)
        else:
            st.error(msg)
        st.session_state.status_message = None

    tab1, tab2 = st.tabs(["Relatório de Pontos", "Gerenciamento de Funcionários"])

    with tab1:
        st.header("Relatório de Pontos")
        
        funcionarios_df = ler_funcionarios_df()
        opcoes_filtro = {"Todos": "Todos"}
        for _, row in funcionarios_df[funcionarios_df['role'] == 'employee'].iterrows():
            opcoes_filtro[row['codigo']] = f"{row['nome']} (Cód: {row['codigo']})"
        codigo_selecionado = st.selectbox(
            "Filtrar por funcionário:",
            options=list(opcoes_filtro.keys()),
            format_func=lambda x: opcoes_filtro[x]
        )
        
        df_registros = ler_registros_df()
        
        if df_registros.empty:
            st.info("Ainda não há registos de ponto.")
        else:
            df_filtrado = df_registros.copy()
            if codigo_selecionado != "Todos":
                df_filtrado = df_registros[df_registros['Código'] == codigo_selecionado]

            if df_filtrado.empty:
                st.info("Nenhum registo para a seleção atual.")
            else:
                st.subheader("Visualização dos Últimos Eventos")
                df_visualizacao = df_filtrado.sort_values(by=["Data", "Hora"], ascending=False)
                
                for index, row in df_visualizacao.iterrows():
                    registro_id = row['ID']
                    with st.container(border=True):
                        diff = row['Diferença (min)']
                        cor_diff = "green" if diff == 0 else "red" if diff > 0 else "blue"
                        texto_diff = "Em ponto" if diff == 0 else f"{'+' if diff > 0 else ''}{diff} min ({'atraso' if diff > 0 else 'adiantado'})"
                        col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 1])
                        col1.text(f"Nome: {row['Nome']}")
                        col2.text(f"Evento: {row['Descrição']}")
                        col3.text(f"Data: {row['Data']}")
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
                                    msg, tipo = atualizar_registro(
                                        registro_id,
                                        novo_horario=horario_para_atualizar,
                                        nova_observacao=obs_para_atualizar
                                    )
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
                
                df_organizado = gerar_relatorio_organizado_df(df_filtrado)
                df_bruto = df_filtrado.sort_values(by=["Data", "Hora"])

                excel_buffer = gerar_arquivo_excel(df_organizado, df_bruto)

                st.download_button(
                    label="📥 Baixar Relatório em Excel",
                    data=excel_buffer,
                    file_name=f"relatorio_ponto_{codigo_selecionado if codigo_selecionado != 'Todos' else 'geral'}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    with tab2:
        st.header("Cadastrar Novo Funcionário")
        with st.form("add_employee_form", clear_on_submit=True):
            novo_codigo = st.text_input("Código do Funcionário (único)")
            novo_nome = st.text_input("Nome Completo")
            novo_cargo = st.text_input("Cargo")
            nova_senha = st.text_input("Senha Provisória", type="password")

            submitted = st.form_submit_button("Adicionar Funcionário")
            if submitted:
                msg, tipo = adicionar_funcionario(
                    novo_codigo.strip(), 
                    novo_nome.strip(), 
                    novo_cargo.strip(), 
                    nova_senha
                )
                st.session_state.status_message = (msg, tipo)
                st.rerun()

if st.session_state.user_info:
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