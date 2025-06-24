import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic

st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="centered"
)

EMPRESA_NOME = "Omega Distribuidora"
EMPRESA_LOCALIZACAO = (-3.8055, -38.5866)
RAIO_PERMITIDO_METROS = 150

ARQUIVO_JSON = "registros_ponto.json"
ARQUIVO_EXCEL = "relatorio_ponto.xlsx"

def carregar_registros():
    if not os.path.exists(ARQUIVO_JSON):
        return {}
    try:
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def salvar_registros(registros):
    with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(registros, f, indent=4, ensure_ascii=False)

def bater_ponto(funcionario_id, localizacao_gps, status_local):
    if not funcionario_id.strip():
        return "⚠️ Por favor, insira um ID de funcionário.", "warning"

    registros = carregar_registros()
    agora = datetime.now()
    hoje_str = agora.strftime("%Y-%m-%d")

    if funcionario_id not in registros:
        registros[funcionario_id] = {}
    if hoje_str not in registros[funcionario_id]:
        registros[funcionario_id][hoje_str] = []

    registros_do_dia = registros[funcionario_id][hoje_str]
    
    tipo_registro = 'entrada'
    if registros_do_dia and registros_do_dia[-1]['tipo'] == 'entrada':
        tipo_registro = 'saida'

    local_str = "N/A"
    if localizacao_gps and 'latitude' in localizacao_gps and 'longitude' in localizacao_gps:
        local_str = f"Lat: {localizacao_gps['latitude']:.4f}, Lon: {localizacao_gps['longitude']:.4f}"

    novo_registro = {
        "hora": agora.isoformat(),
        "tipo": tipo_registro,
        "localizacao_gps": local_str,
        "status_local": status_local
    }
    registros[funcionario_id][hoje_str].append(novo_registro)
    salvar_registros(registros)
    
    mensagem = f"Ponto de '{tipo_registro.upper()}' registado às {agora.strftime('%H:%M:%S')}."
    return mensagem, "success"

st.title(f"🔵 Ponto {EMPRESA_NOME}")
st.markdown("Insira o seu ID e clique no botão para registar o seu ponto.")

localizacao_gps = streamlit_geolocation()

id_funcionario = st.text_input("ID do Funcionário", placeholder="O seu ID aqui...")

if st.button("Bater o Ponto", type="primary", use_container_width=True):
    if not id_funcionario:
        st.warning("É necessário inserir um ID de funcionário.", icon="⚠️")
    elif not localizacao_gps or 'latitude' not in localizacao_gps:
        st.error("Não foi possível obter a sua localização. Por favor, autorize o acesso no seu navegador.", icon="🛰️")
    else:
        user_coords = (localizacao_gps['latitude'], localizacao_gps['longitude'])
        
        distancia = geodesic(EMPRESA_LOCALIZACAO, user_coords).meters
        
        st.info(f"Você está a {distancia:.0f} metros da {EMPRESA_NOME}.", icon="📍")
        
        status_local = ""
        if distancia <= RAIO_PERMITIDO_METROS:
            st.success("Localização validada: Dentro da área permitida (Presencial).")
            status_local = "Presencial"
        else:
            st.warning("Aviso: Fora da área permitida (Remoto).")
            status_local = "Remoto"
        
        mensagem, tipo_alerta = bater_ponto(id_funcionario.lower(), localizacao_gps, status_local)
        if tipo_alerta == "success":
            st.success(mensagem, icon="✅")
        else:
            st.warning(mensagem, icon="⚠️")

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
                dados_tabela.append({
                    'Funcionário': func_id,
                    'Data': data,
                    'Hora': datetime.fromisoformat(evento['hora']).strftime('%H:%M:%S'),
                    'Tipo': evento['tipo'].capitalize(),
                    'Status Local': evento.get('status_local', 'N/D'),
                    'Coordenadas': evento.get('localizacao_gps', 'N/D')
                })
    
    df = pd.DataFrame(dados_tabela)
    st.dataframe(df.style.hide(axis="index"), use_container_width=True)

    if st.button("Exportar para Excel", use_container_width=True):
        df.to_excel(ARQUIVO_EXCEL, index=False)
        with open(ARQUIVO_EXCEL, "rb") as file:
            st.download_button(
                label="Clique aqui para descarregar a planilha",
                data=file,
                file_name=ARQUIVO_EXCEL,
                mime="application/vnd.ms-excel"
            )
