import streamlit as st
import pandas as pd
import time
from services import (
    ler_registros_csv, # MUDANÇA
    bater_ponto, 
    verificar_login, 
    ler_json_funcionarios,
    atualizar_registro,
    obter_proximo_evento
)
from config import RELATORIO_CSV # MUDANÇA

st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="wide"
)

@st.cache_data
def carregar_dados_pontos():
    return ler_registros_csv() # MUDANÇA

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
                carregar_dados_pontos.clear()
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
    
    df_filtrado = carregar_dados_pontos()
    if codigo_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Código'] == codigo_selecionado]
    
    if df_filtrado.empty:
        st.info("Nenhum registo para a seleção atual.")
    else:
        df_filtrado_sorted = df_filtrado.sort_values(by=["Data", "Hora"], ascending=False)
        
        for index, row in df_filtrado_sorted.iterrows():
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
                            
                            if tipo == "success": 
                                st.success(msg)
                                carregar_dados_pontos.clear()
                                time.sleep(0.5)
                            else: 
                                st.error(msg)
                        
                        st.session_state.edit_id = None
                        st.rerun()
                    
                    if col_cancel.button("Cancelar", key=f"cancel_{registro_id}"):
                        st.session_state.edit_id = None
                        st.rerun()
                
                elif row.get('Observação'):
                    st.markdown(f"**Obs:** *{row['Observação']}*")
        
        st.divider()
        
        # MUDANÇA: Lógica de download atualizada para CSV.
        csv = df_filtrado_sorted.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descarregar Relatório como CSV",
            data=csv,
            file_name=f"relatorio_{codigo_selecionado}.csv",
            mime="text/csv",
        )

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
