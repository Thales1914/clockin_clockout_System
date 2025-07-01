import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic

# --- Configurações da Página ---
st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="centered"
)

# --- CONFIGURAÇÕES GLOBAIS ---
EMPRESA_NOME = "Omega Distribuidora"
EMPRESA_LOCALIZACAO = (-3.8210554, -38.5049637)
RAIO_PERMITIDO_METROS = 50
# AJUSTADO: Aumentamos o limite para aceitar sinais mais fracos
PRECISAO_MAXIMA_METROS = 151 

# --- Lógica de Negócio (código inalterado) ---
FUSO_HORARIO = ZoneInfo("America/Fortaleza")
ARQUIVO_JSON = "registros_ponto.json"
ARQUIVO_EXCEL = "relatorio_ponto.xlsx"

def carregar_registros():
    if not os.path.exists(ARQUIVO_JSON):
        return {}
    try:
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {}

def salvar_registros(registros):
    with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(registros, f, indent=4, ensure_ascii=False)

def bater_ponto(funcionario_id, localizacao_gps, status_local, precisao):
    if not funcionario_id.strip():
        return "⚠️ Por favor, insira um ID de funcionário.", "warning"

    registros = carregar_registros()
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")

    registros_funcionario = registros.get(funcionario_id, {})
    registros_do_dia = registros_funcionario.get(hoje_str, [])

    tipo_registro = 'entrada'
    if registros_do_dia and registros_do_dia[-1].get('tipo') == 'entrada':
        tipo_registro = 'saida'

    local_str = "N/A"
    if localizacao_gps and 'latitude' in localizacao_gps:
        local_str = f"Lat: {localizacao_gps['latitude']:.4f}, Lon: {localizacao_gps['longitude']:.4f}"

    novo_registro = {
        "hora": agora.isoformat(),
        "tipo": tipo_registro,
        "localizacao_gps": local_str,
        "status_local": status_local,
        "precisao_gps_metros": precisao
    }
    
    registros_do_dia.append(novo_registro)
    registros_funcionario[hoje_str] = registros_do_dia
    registros[funcionario_id] = registros_funcionario
    
    salvar_registros(registros)
    
    mensagem = f"Ponto de '{tipo_registro.upper()}' registado às {agora.strftime('%H:%M:%S')}."
    return mensagem, "success"

# --- Interface Gráfica com Streamlit ---

st.title(f"🔵 Ponto {EMPRESA_NOME}")
st.markdown("Insira o seu ID e clique no botão para registar o seu ponto.")

localizacao_gps = streamlit_geolocation()
id_funcionario = st.text_input("ID do Funcionário", placeholder="O seu ID aqui...")

if localizacao_gps and 'accuracy' in localizacao_gps:
    precisao_atual = localizacao_gps['accuracy']
    if precisao_atual is not None:
        if precisao_atual <= PRECISAO_MAXIMA_METROS:
            st.caption(f"🛰️ Qualidade do sinal: Boa (precisão de {precisao_atual:.0f}m)")
        else:
            st.caption(f"🛰️ Qualidade do sinal: Fraca (precisão de {precisao_atual:.0f}m). Tente ir para um local mais aberto.")

if st.button("Bater o Ponto", type="primary", use_container_width=True):
    if not id_funcionario:
        st.warning("É necessário inserir um ID de funcionário.", icon="⚠️")
    elif not localizacao_gps or 'latitude' not in localizacao_gps:
        st.error("Não foi possível obter a sua localização. Por favor, autorize o acesso no seu navegador e recarregue a página.", icon="🛰️")
    else:
        precisao_gps = localizacao_gps.get('accuracy')
        if precisao_gps is None or precisao_gps > PRECISAO_MAXIMA_METROS:
            st.error(f"Sinal de GPS muito fraco (precisão de {precisao_gps:.0f}m). O ponto não pode ser registado. Tente novamente num local com melhor sinal.", icon="🚫")
        else:
            with st.spinner("A verificar localização..."):
                user_coords = (localizacao_gps['latitude'], localizacao_gps['longitude'])
                distancia = geodesic(EMPRESA_LOCALIZACAO, user_coords).meters
                st.info(f"Você está a {distancia:.0f} metros da {EMPRESA_NOME}.", icon="📍")
                
                status_local = "Remoto"
                if distancia <= RAIO_PERMITIDO_METROS:
                    st.success("Localização validada: Dentro da área permitida (Presencial).")
                    status_local = "Presencial"
                else:
                    st.warning("Aviso: Fora da área permitida (Remoto).")
                    status_local = "Remoto"
                
                mensagem, tipo_alerta = bater_ponto(id_funcionario.lower(), localizacao_gps, status_local, precisao_gps)
                if tipo_alerta == "success":
                    st.success(mensagem, icon="✅")
                else:
                    st.warning(mensagem, icon="⚠️")

# --- Funcionalidade de Relatório ---
st.divider()
st.header("Relatório de Pontos")

registros_atuais = carregar_registros()
if not registros_atuais:
    st.info("Ainda não existem registos de ponto.")
else:
    dados_tabela = []
    for func_id, dias in registros_atuais.items():
        for data, eventos in dias.items():
            for evento in eventos:
                hora_iso = evento.get('hora', '')
                if hora_iso:
                    hora_obj = datetime.fromisoformat(hora_iso).astimezone(FUSO_HORARIO)
                    hora_formatada = hora_obj.strftime('%H:%M:%S')
                else:
                    hora_formatada = 'N/D'

                dados_tabela.append({
                    'Funcionário': func_id,
                    'Data': data,
                    'Hora': hora_formatada,
                    'Tipo': evento.get('tipo', 'N/D').capitalize(),
                    'Status Local': evento.get('status_local', 'N/D'),
                    'Precisão GPS (m)': evento.get('precisao_gps_metros'),
                    'Coordenadas': evento.get('localizacao_gps', 'N/D')
                })
    
    df = pd.DataFrame(dados_tabela)
    if not df.empty:
        colunas_ordenadas = ['Funcionário', 'Data', 'Hora', 'Tipo', 'Status Local', 'Precisão GPS (m)', 'Coordenadas']
        df = df[colunas_ordenadas]
        st.dataframe(df.style.hide(axis="index"), use_container_width=True)

        df.to_excel(ARQUIVO_EXCEL, index=False, engine='openpyxl')
        with open(ARQUIVO_EXCEL, "rb") as file:
            st.download_button(
                label="Descarregar Relatório como Excel",
                data=file,
                file_name=ARQUIVO_EXCEL,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )