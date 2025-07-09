# services.py
import json
import os
from datetime import datetime
from config import FUNCIONARIOS_JSON, PONTOS_TXT, FUSO_HORARIO

# --- Funções de Gestão de Ficheiros ---

def ler_json_funcionarios():
    """Lê o ficheiro JSON de funcionários de forma segura."""
    if not os.path.exists(FUNCIONARIOS_JSON):
        return None, f"Erro crítico: O ficheiro '{FUNCIONARIOS_JSON}' não foi encontrado."
    try:
        with open(FUNCIONARIOS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except (json.JSONDecodeError, IOError) as e:
        return None, f"Erro ao ler o ficheiro '{FUNCIONARIOS_JSON}': {e}"

def ler_registros_txt():
    """Lê os registros de ponto do ficheiro .txt e os transforma numa lista de dicionários."""
    if not os.path.exists(PONTOS_TXT):
        return []
    
    registros = []
    with open(PONTOS_TXT, 'r', encoding='utf-8') as f:
        for linha in f:
            partes = linha.strip().split('|')
            if len(partes) == 6:
                registros.append({
                    "Código": partes[0], "Nome": partes[1], "Cargo": partes[2],
                    "Data": partes[3], "Hora": partes[4], "Tipo": partes[5]
                })
    return registros

def salvar_registro_txt(novo_registro):
    """Adiciona (append) um novo registro ao ficheiro .txt."""
    linha = (
        f"{novo_registro['Código']}|{novo_registro['Nome']}|"
        f"{novo_registro['Cargo']}|{novo_registro['Data']}|"
        f"{novo_registro['Hora']}|{novo_registro['Tipo']}\n"
    )
    with open(PONTOS_TXT, 'a', encoding='utf-8') as f:
        f.write(linha)

# --- Funções de Lógica de Negócio ---

def bater_ponto(codigo):
    """
    Regista a entrada ou saída de um funcionário.
    Retorna uma tupla: (mensagem, tipo_da_mensagem)
    Ex: ("Ponto registado!", "success") ou ("Código não encontrado", "error")
    """
    funcionarios, erro = ler_json_funcionarios()
    if erro:
        return erro, "error"

    if codigo not in funcionarios:
        return f"Código de funcionário '{codigo}' não encontrado.", "error"

    nome_funcionario = funcionarios[codigo]["nome"]
    cargo_funcionario = funcionarios[codigo]["cargo"]
    
    todos_registros = ler_registros_txt()
    
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")

    registros_do_dia = [r for r in todos_registros if r['Código'] == codigo and r['Data'] == hoje_str]

    tipo_registro = 'Entrada'
    if registros_do_dia and registros_do_dia[-1]['Tipo'] == 'Entrada':
        tipo_registro = 'Saída'

    novo_registro = {
        "Código": codigo, "Nome": nome_funcionario, "Cargo": cargo_funcionario,
        "Data": hoje_str, "Hora": agora.strftime("%H:%M:%S"), "Tipo": tipo_registro
    }
    
    salvar_registro_txt(novo_registro)
    
    mensagem_sucesso = f"Ponto de '{tipo_registro}' registado para {nome_funcionario} às {novo_registro['Hora']}."
    return mensagem_sucesso, "success"
