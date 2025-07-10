import streamlit as st
import pandas as pd
import time
from services import (
    ler_registros_txt, 
    bater_ponto, 
    verificar_login, 
    ler_json_funcionarios,
    atualizar_observacao,
    atualizar_horario,
    obter_proximo_evento
)
from config import RELATORIO_TXT

st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="wide"
)

if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

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
                registro_id = row['ID']
                
                with st.container(border=True):
                    diff = row['Diferença (min)']
                    if diff > 0:
                        cor_diff = "red"
                        texto_diff = f"+{diff} min (atraso)"
                    elif diff < 0:
                        cor_diff = "blue"
                        texto_diff = f"{diff} min (adiantado)"
                    else:
                        cor_diff = "green"
                        texto_diff = "Em ponto"

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
                            if novo_horario != row['Hora']:
                                msg_hora, tipo_hora = atualizar_horario(registro_id, novo_horario)
                                if tipo_hora == "success": st.success(msg_hora)
                                else: st.error(msg_hora)
                            
                            if nova_obs != row.get('Observação', ''):
                                msg_obs, tipo_obs = atualizar_observacao(registro_id, nova_obs)
                                if tipo_obs == "success": st.success(msg_obs)
                                else: st.error(msg_obs)
                            
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
