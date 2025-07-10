import json
import os
from datetime import datetime, time
from config import FUNCIONARIOS_JSON, PONTOS_TXT, FUSO_HORARIO, HORARIOS_PADRAO

def ler_json_funcionarios():
    if not os.path.exists(FUNCIONARIOS_JSON):
        return None, f"Erro crítico: O ficheiro '{FUNCIONARIOS_JSON}' não foi encontrado."
    try:
        with open(FUNCIONARIOS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except (json.JSONDecodeError, IOError) as e:
        return None, f"Erro ao ler o ficheiro '{FUNCIONARIOS_JSON}': {e}"

def ler_registros_txt():
    if not os.path.exists(PONTOS_TXT):
        return []
    
    registros = []
    with open(PONTOS_TXT, 'r', encoding='utf-8') as f:
        for linha in f:
            partes = linha.strip().split('|')
            if len(partes) >= 8:
                registros.append({
                    "ID": partes[0], "Código": partes[1], "Nome": partes[2], "Cargo": partes[3],
                    "Data": partes[4], "Hora": partes[5], "Descrição": partes[6],
                    "Diferença (min)": int(partes[7]),
                    "Observação": partes[8] if len(partes) > 8 else ""
                })
    return registros

def salvar_todos_registros_txt(registros):
    with open(PONTOS_TXT, 'w', encoding='utf-8') as f:
        for registro in registros:
            linha = (
                f"{registro['ID']}|{registro['Código']}|{registro['Nome']}|{registro['Cargo']}|"
                f"{registro['Data']}|{registro['Hora']}|{registro['Descrição']}|"
                f"{registro['Diferença (min)']}|{registro.get('Observação', '')}\n"
            )
            f.write(linha)

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
    todos_registros = ler_registros_txt()
    registros_do_dia = [r for r in todos_registros if r['Código'] == codigo and r['Data'] == hoje_str]
    
    num_pontos = len(registros_do_dia)
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

    todos_registros = ler_registros_txt()
    
    novo_registro = {
        "ID": f"{codigo}-{agora.isoformat()}",
        "Código": codigo, "Nome": nome, "Cargo": cargo,
        "Data": hoje_str, "Hora": agora.strftime("%H:%M:%S"),
        "Descrição": proximo_evento,
        "Diferença (min)": diferenca_minutos,
        "Observação": ""
    }
    
    todos_registros.append(novo_registro)
    salvar_todos_registros_txt(todos_registros)
    
    if diferenca_minutos > 0:
        msg_extra = f" ({diferenca_minutos} min de atraso)"
    elif diferenca_minutos < 0:
        msg_extra = f" ({-diferenca_minutos} min de adiantamento)"
    else:
        msg_extra = " (em ponto)"
        
    mensagem_sucesso = f"'{proximo_evento}' registado para {nome} às {novo_registro['Hora']}{msg_extra}."
    return mensagem_sucesso, "success"

def atualizar_observacao(identificador_registro, nova_observacao):
    todos_registros = ler_registros_txt()
    registro_encontrado = False
    for registro in todos_registros:
        if registro['ID'] == identificador_registro:
            registro['Observação'] = nova_observacao
            registro_encontrado = True
            break
    if registro_encontrado:
        salvar_todos_registros_txt(todos_registros)
        return "Observação atualizada.", "success"
    return "Erro: Registro não encontrado.", "error"

def atualizar_horario(identificador_registro, novo_horario_str):
    try:
        novo_horario_obj = datetime.strptime(novo_horario_str, "%H:%M:%S").time()
    except ValueError:
        return "Formato de hora inválido. Use HH:MM:SS.", "error"

    todos_registros = ler_registros_txt()
    registro_encontrado = False
    for registro in todos_registros:
        if registro['ID'] == identificador_registro:
            descricao_evento = registro['Descrição']
            hora_prevista = HORARIOS_PADRAO.get(descricao_evento)
            
            if hora_prevista:
                data_registro = datetime.strptime(registro['Data'], "%Y-%m-%d")
                datetime_previsto = data_registro.replace(hour=hora_prevista.hour, minute=hora_prevista.minute)
                datetime_novo = data_registro.replace(hour=novo_horario_obj.hour, minute=novo_horario_obj.minute, second=novo_horario_obj.second)
                
                diferenca_minutos = round((datetime_novo - datetime_previsto).total_seconds() / 60)
                registro['Diferença (min)'] = diferenca_minutos

            registro['Hora'] = novo_horario_str
            registro_encontrado = True
            break
            
    if registro_encontrado:
        salvar_todos_registros_txt(todos_registros)
        return "Horário e diferença recalculados com sucesso.", "success"
    return "Erro: Registro não encontrado.", "error"
