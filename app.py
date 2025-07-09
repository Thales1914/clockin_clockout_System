import streamlit as st
import pandas as pd
from services import (
    ler_registros_txt, 
    bater_ponto, 
    verificar_login, 
    ler_json_funcionarios,
    atualizar_observacao
)
from config import RELATORIO_TXT

st.set_page_config(
    page_title="Ponto Omega",
    layout="wide"
)

if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

#Criação do formulario de login
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

#Nesse trecho temos as duas telas que usaremos na aplicação, pois teremos a divisão de entre tela fun e tela admin


#Aqui se encontra a tela de funcionário, onde na tela só tera o botão para bater o ponto, pois a logica de identificação já vai ser feita na tela de login
def tela_funcionario():
    st.title(f"🔵 Bem-vindo, {st.session_state.user_info['nome']}!")
    st.header("Registo de Ponto")
    
    if st.button("Confirmar Meu Ponto", type="primary", use_container_width=True):
        mensagem, tipo = bater_ponto(
            st.session_state.user_info['codigo'], 
            st.session_state.user_info['nome'], 
            st.session_state.user_info['cargo']
        )
        if tipo == "success": st.success(mensagem)
        else: st.error(mensagem)

#Aqui se encontra a tela de admin, onde o admin poderar exportar relátorios e fazer edições em pontos de funcionários
def tela_admin():
    st.title("🔵 Painel do Administrador")
    
    st.header("Relatório de Pontos")
    
    funcionarios, _ = ler_json_funcionarios()
    opcoes_filtro = {"Todos": "Todos"}
    if funcionarios:
        for codigo, info in funcionarios.items():
            if info.get("role") == "employee":
                opcoes_filtro[codigo] = f"{info['nome']} (Cód: {codigo})"
    
    codigo_selecionado = st.selectbox(
        "Filtrar por funcionário:",
        options=list(opcoes_filtro.keys()),
        format_func=lambda x: opcoes_filtro[x]
    )
    
    dados_tabela = ler_registros_txt()
    if not dados_tabela:
        st.info("Ainda não há registos de ponto.")
    else:
        df = pd.DataFrame(dados_tabela)
        df_filtrado = df[df['Código'] == codigo_selecionado] if codigo_selecionado != "Todos" else df
        
        if df_filtrado.empty:
            st.info("Nenhum registo para a seleção atual.")
        else:
            df_filtrado_sorted = df_filtrado.sort_values(by=["Data", "Hora"], ascending=False)
            
            for index, row in df_filtrado_sorted.iterrows():
                registro_id = f"{row['Código']}-{row['Data']}-{row['Hora']}"
                
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 3, 1])
                    col1.text(f"Cód: {row['Código']}")
                    col2.text(f"Nome: {row['Nome']}")
                    col3.text(f"Data: {row['Data']}")
                    col4.text(f"Hora: {row['Hora']} ({row['Tipo']})")
                    
                    if col5.button("Editar", key=f"edit_{registro_id}"):
                        st.session_state.edit_id = registro_id
                        st.rerun()

                    if st.session_state.edit_id == registro_id:
                        nova_obs = st.text_area(
                            "Observação:", 
                            value=row.get('Observação', ''), 
                            key=f"obs_{registro_id}"
                        )
                        col_save, col_cancel, _ = st.columns([1, 1, 5])
                        if col_save.button("Salvar", key=f"save_{registro_id}", type="primary"):
                            msg, tipo = atualizar_observacao(registro_id, nova_obs)
                            if tipo == "success": st.success(msg)
                            else: st.error(msg)
                            st.session_state.edit_id = None
                            st.rerun()
                        
                        if col_cancel.button("Cancelar", key=f"cancel_{registro_id}"):
                            st.session_state.edit_id = None
                            st.rerun()
                    elif row.get('Observação'):
                        st.markdown(f"**Obs:** *{row['Observação']}*")

if st.session_state.user_info:
    if st.sidebar.button("Sair"):
        st.session_state.user_info = None
        st.session_state.edit_id = None
        st.rerun()

    if st.session_state.user_info.get("role") == "admin":
        tela_admin()
    else:
        tela_funcionario()
else:
    tela_de_login()
