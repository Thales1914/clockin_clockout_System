import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import pytz
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic
from streamlit_gsheets import GSheetsConnection

# --- Configurações da Página ---
st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="centered"
)

# --- CONFIGURAÇÕES GLOBAIS ---
EMPRESA_NOME = "Omega Distribuidora"
EMPRESA_LOCALIZACAO = (-3.8210554, -38.5049637)
RAIO_PERMITIDO_METROS = 150
FUSO_HORARIO = pytz.timezone("America/Fortaleza")

# --- CONEXÃO COM A BASE DE DADOS (GOOGLE SHEETS) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Não foi possível ligar à planilha do Google Sheets. Verifique os 'Secrets' no Streamlit Cloud.")
    st.stop() # Interrompe a execução da app se a conexão falhar

# --- LÓGICA DE NEGÓCIO ---
@st.cache_data(ttl=60) # Adiciona cache para não ler a planilha a cada interação
def carregar_registros():
    """Carrega todos os registos da planilha do Google Sheets."""
    try:
        df = conn.read(worksheet="Registros", usecols=list(range(6)), ttl="0")
        return df.dropna(how="all")
    except Exception as e:
        st.error(f"Não foi possível ler a planilha: {e}")
        return pd.DataFrame()

def bater_ponto(funcionario_id, localizacao_gps, status_local):
    """Adiciona uma nova linha com o registo de ponto na planilha."""
    if not funcionario_id.strip():
        return "⚠️ Por favor, insira um ID de funcionário.", "warning"

    agora = datetime.now(FUSO_HORARIO)
    
    local_str = "N/A"
    if localizacao_gps and 'latitude' in localizacao_gps and 'longitude' in localizacao_gps:
        local_str = f"Lat: {localizacao_gps['latitude']:.4f}, Lon: {localizacao_gps['longitude']:.4f}"

    df_registros = carregar_registros()
    df_funcionario_hoje = df_registros[
        (df_registros["Funcionário"] == funcionario_id) & 
        (df_registros["Data"] == agora.strftime("%Y-%m-%d"))
    ]
    
    tipo_registro = 'Entrada'
    if not df_funcionario_hoje.empty and df_funcionario_hoje.iloc[-1]["Tipo"] == 'Entrada':
        tipo_registro = 'Saída'

    novo_registro = pd.DataFrame([{
        "Funcionário": funcionario_id,
        "Data": agora.strftime("%Y-%m-%d"),
        "Hora": agora.strftime("%H:%M:%S"),
        "Tipo": tipo_registro,
        "Status Local": status_local,
        "Coordenadas": local_str
    }])
    
    try:
        # Cria uma cópia para evitar o aviso 'SettingWithCopyWarning' do pandas
        df_atualizado = df_registros.copy().append(novo_registro, ignore_index=True)
        conn.update(worksheet="Registros", data=df_atualizado)
        # Limpa o cache para que o relatório seja atualizado na próxima recarga
        st.cache_data.clear()
        mensagem = f"Ponto de '{tipo_registro.upper()}' registado às {agora.strftime('%H:%M:%S')}."
        return mensagem, "success"
    except Exception as e:
        return f"❌ Erro ao guardar na planilha: {e}", "error"

# --- INTERFACE GRÁFICA ---
st.title(f"🔵 Ponto {EMPRESA_NOME}")
st.markdown("Insira o seu ID e clique no botão para registar o seu ponto.")

id_funcionario = st.text_input("ID do Funcionário", placeholder="O seu ID aqui...", label_visibility="collapsed")
localizacao_gps = streamlit_geolocation()

if st.button("Bater o Ponto", type="primary", use_container_width=True):
    if not id_funcionario:
        st.warning("É necessário inserir um ID de funcionário.", icon="⚠️")
    elif not localizacao_gps or 'latitude' not in localizacao_gps:
        st.error("Não foi possível obter a sua localização. Por favor, autorize o acesso no seu navegador e recarregue a página.", icon="🛰️")
    else:
        with st.spinner("A verificar localização e a registar..."):
            user_coords = (localizacao_gps['latitude'], localizacao_gps['longitude'])
            distancia = geodesic(EMPRESA_LOCALIZACAO, user_coords).meters
            
            st.info(f"Você está a {distancia:.0f} metros da {EMPRESA_NOME}.", icon="📍")
            
            status_local = "Remoto"
            if distancia <= RAIO_PERMITIDO_METROS:
                status_local = "Presencial"
            
            mensagem, tipo_alerta = bater_ponto(id_funcionario.lower(), localizacao_gps, status_local)

            if status_local == "Presencial":
                st.success(f"Localização validada: {status_local}", icon="✅")
            else:
                st.warning(f"Fora da área da empresa: {status_local}", icon="🗺️")
            
            if tipo_alerta == "success":
                st.success(mensagem)
            else:
                st.error(mensagem)

# --- RELATÓRIO DE PONTOS ---
st.divider()
st.header("Relatório de Pontos")

if st.button("Recarregar Relatório"):
    st.cache_data.clear()

df_relatorio = carregar_registros()

if df_relatorio.empty:
    st.info("Ainda não existem registos de ponto.")
else:
    df_relatorio_sorted = df_relatorio.sort_values(by=["Data", "Hora"], ascending=False)
    st.dataframe(df_relatorio_sorted, use_container_width=True, hide_index=True)

    csv = df_relatorio_sorted.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descarregar Relatório como CSV",
        data=csv,
        file_name="relatorio_ponto.csv",
        mime="text/csv",
    )
