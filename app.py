# app.py
import streamlit as st
import pandas as pd
# Importa as funções e constantes dos outros ficheiros
from services import ler_registros_txt, bater_ponto
from config import RELATORIO_TXT

# --- Configurações da Página ---
st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="centered"
)

# --- Interface Gráfica com Streamlit ---

st.title("🔵 Sistema de Ponto - Omega Distribuidora")

tab1, tab2 = st.tabs(["🕒 Bater Ponto", "📋 Relatório"])

# --- Aba de Bater Ponto ---
with tab1:
    st.header("Registo de Ponto")
    codigo_input = st.text_input("Digite o seu código de funcionário:", key="codigo_ponto", placeholder="Ex: 101")
    
    if st.button("Confirmar Ponto", type="primary"):
        if codigo_input:
            # Chama a função de lógica e recebe a resposta
            mensagem, tipo = bater_ponto(codigo_input)
            # Exibe a resposta na interface
            if tipo == "success":
                st.success(mensagem)
            else:
                st.error(mensagem)
        else:
            st.warning("Por favor, insira o seu código.")

# --- Aba de Relatório ---
with tab2:
    st.header("Relatório de Pontos")
    
    dados_tabela = ler_registros_txt()
    
    if not dados_tabela:
        st.info("Ainda não há registos de ponto para exibir.")
    else:
        dados_tabela_sorted = sorted(dados_tabela, key=lambda x: (x['Data'], x['Hora']))

        df = pd.DataFrame(dados_tabela_sorted)
        # Reordena as colunas para melhor visualização
        df = df[['Código', 'Nome', 'Cargo', 'Data', 'Hora', 'Tipo']]
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        relatorio_texto = "Relatório de Pontos - Omega Distribuidora\n"
        relatorio_texto += "=" * 40 + "\n\n"
        for evento in dados_tabela_sorted:
            relatorio_texto += f"Nome: {evento['Nome']} (Cód: {evento['Código']})\n"
            relatorio_texto += f"Cargo: {evento['Cargo']}\n"
            relatorio_texto += f"Data: {evento['Data']} | Hora: {evento['Hora']} | Tipo: {evento['Tipo']}\n"
            relatorio_texto += "-" * 20 + "\n"

        st.download_button(
            label="Descarregar Relatório em .txt",
            data=relatorio_texto.encode('utf-8'),
            file_name=RELATORIO_TXT,
            mime="text/plain"
        )
