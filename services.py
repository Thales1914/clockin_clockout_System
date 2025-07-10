import json
import os
import pandas as pd
from datetime import datetime, time
from config import FUNCIONARIOS_JSON, PONTOS_CSV, FUSO_HORARIO, HORARIOS_PADRAO

# --- Funções de Gestão de Ficheiros ---

def ler_json_funcionarios():
    if not os.path.exists(FUNCIONARIOS_JSON):
        return None, f"Erro crítico: O ficheiro '{FUNCIONARIOS_JSON}' não foi encontrado."
    try:
        with open(FUNCIONARIOS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except (json.JSONDecodeError, IOError) as e:
        return None, f"Erro ao ler o ficheiro '{FUNCIONARIOS_JSON}': {e}"

# MUDANÇA: A lógica agora usa pandas para ler o CSV.
def ler_registros_csv():
    """Lê os registros de ponto do ficheiro .csv e retorna um DataFrame."""
    if not os.path.exists(PONTOS_CSV):
        # Se o ficheiro não existir, retorna um DataFrame vazio com as colunas corretas.
        return pd.DataFrame(columns=["ID", "Código", "Nome", "Cargo", "Data", "Hora", "Descrição", "Diferença (min)", "Observação"])
    try:
        # Lê o CSV e garante que a coluna 'Código' é lida como string.
        return pd.read_csv(PONTOS_CSV, dtype={'Código': str})
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["ID", "Código", "Nome", "Cargo", "Data", "Hora", "Descrição", "Diferença (min)", "Observação"])

# MUDANÇA: A lógica agora usa pandas para salvar o CSV.
def salvar_dataframe_csv(df):
    """Salva o DataFrame completo no ficheiro .csv, sobrescrevendo o conteúdo."""
    df.to_csv(PONTOS_CSV, index=False)

# --- Funções de Lógica de Negócio (adaptadas para pandas) ---

def verificar_login(codigo, senha):
    funcionarios, erro = ler_json_funcionarios()
    if erro:
        return None, erro
    user_data = funcionarios.get(codigo)
    if user_data and user_data['senha'] == senha:
        return user_data, None
    else:
        return None, "Código ou senha inválidos."

def obter_proximo_evento(codigo):
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")
    df_registros = ler_registros_csv()
    
    # Filtra o DataFrame usando a sintaxe do pandas.
    df_registros_do_dia = df_registros[(df_registros['Código'] == codigo) & (df_registros['Data'] == hoje_str)]
    
    num_pontos = len(df_registros_do_dia)
    eventos_programados = list(HORARIOS_PADRAO.keys())
    
    if num_pontos < len(eventos_programados):
        return eventos_programados[num_pontos]
    else:
        return "Jornada Finalizada"

def bater_ponto(codigo, nome, cargo):
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")

    proximo_evento = obter_proximo_evento(codigo)
    if proximo_evento == "Jornada Finalizada":
        return "Sua jornada de hoje já foi completamente registada.", "warning"

    hora_prevista = HORARIOS_PADRAO[proximo_evento]
    datetime_previsto = agora.replace(hour=hora_prevista.hour, minute=hora_prevista.minute, second=hora_prevista.second, microsecond=0)
    diferenca_segundos = (agora - datetime_previsto).total_seconds()
    diferenca_minutos = round(diferenca_segundos / 60)

    df_registros = ler_registros_csv()
    
    novo_registro = pd.DataFrame([{
        "ID": f"{codigo}-{agora.isoformat()}",
        "Código": codigo, "Nome": nome, "Cargo": cargo,
        "Data": hoje_str, "Hora": agora.strftime("%H:%M:%S"),
        "Descrição": proximo_evento,
        "Diferença (min)": diferenca_minutos,
        "Observação": ""
    }])
    
    # Concatena o novo registro ao DataFrame existente.
    df_atualizado = pd.concat([df_registros, novo_registro], ignore_index=True)
    salvar_dataframe_csv(df_atualizado)
    
    if diferenca_minutos > 0:
        msg_extra = f" ({diferenca_minutos} min de atraso)"
    elif diferenca_minutos < 0:
        msg_extra = f" ({-diferenca_minutos} min de adiantamento)"
    else:
        msg_extra = " (em ponto)"
        
    mensagem_sucesso = f"'{proximo_evento}' registado para {nome} às {novo_registro.iloc[0]['Hora']}{msg_extra}."
    return mensagem_sucesso, "success"

def atualizar_registro(id_registro, novo_horario=None, nova_observacao=None):
    df = ler_registros_csv()
    # Encontra o índice da linha que corresponde ao ID do registro.
    idx = df.index[df['ID'] == id_registro].tolist()

    if not idx:
        return "Erro: Registro não encontrado para atualização.", "error"
    
    idx = idx[0] # Pega o primeiro (e único) índice encontrado.

    if nova_observacao is not None:
        df.loc[idx, 'Observação'] = nova_observacao

    if novo_horario is not None:
        try:
            novo_horario_obj = datetime.strptime(novo_horario, "%H:%M:%S").time()
            df.loc[idx, 'Hora'] = novo_horario
            
            descricao_evento = df.loc[idx, 'Descrição']
            hora_prevista = HORARIOS_PADRAO.get(descricao_evento)
            if hora_prevista:
                data_registro = datetime.strptime(df.loc[idx, 'Data'], "%Y-%m-%d")
                datetime_previsto = data_registro.replace(hour=hora_prevista.hour, minute=hora_prevista.minute)
                datetime_novo = data_registro.replace(hour=novo_horario_obj.hour, minute=novo_horario_obj.minute, second=novo_horario_obj.second)
                diferenca_minutos = round((datetime_novo - datetime_previsto).total_seconds() / 60)
                df.loc[idx, 'Diferença (min)'] = diferenca_minutos
        except ValueError:
            return "Formato de hora inválido. Use HH:MM:SS.", "error"

    salvar_dataframe_csv(df)
    return "Registro atualizado com sucesso.", "success"
