import json
import os
from datetime import datetime
from config import FUNCIONARIOS_JSON, PONTOS_TXT, FUSO_HORARIO


#Faz a leitura do registro de funcionários 
def ler_json_funcionarios():
    if not os.path.exists(FUNCIONARIOS_JSON):
        return None, f"Erro crítico: O ficheiro '{FUNCIONARIOS_JSON}' não foi encontrado."
    try:
        with open(FUNCIONARIOS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except (json.JSONDecodeError, IOError) as e:
        return None, f"Erro ao ler o ficheiro '{FUNCIONARIOS_JSON}': {e}"

#Faz a leitura do arquivo em txt
def ler_registros_txt():
    if not os.path.exists(PONTOS_TXT):
        return []
    
    registros = []
    with open(PONTOS_TXT, 'r', encoding='utf-8') as f:
        for linha in f:
            partes = linha.strip().split('|')
            if len(partes) >= 6:
                registros.append({
                    "Código": partes[0], "Nome": partes[1], "Cargo": partes[2],
                    "Data": partes[3], "Hora": partes[4], "Tipo": partes[5],
                    "Observação": partes[6] if len(partes) > 6 else ""
                })
    return registros


#Função criada para salvar os arquivos no txt, e futuramente iremos exportar esse arquivo
def salvar_todos_registros_txt(registros):
    with open(PONTOS_TXT, 'w', encoding='utf-8') as f:
        for registro in registros:
            linha = (
                f"{registro['Código']}|{registro['Nome']}|{registro['Cargo']}|"
                f"{registro['Data']}|{registro['Hora']}|{registro['Tipo']}|"
                f"{registro.get('Observação', '')}\n"
            )
            f.write(linha)

#Função criada para a lógica de login de users
def verificar_login(codigo, senha):
    funcionarios, erro = ler_json_funcionarios()
    if erro:
        return None, erro

    user_data = funcionarios.get(codigo)
    if user_data and user_data['senha'] == senha:
        return user_data, None
    else:
        return None, "Código ou senha inválidos."

#Função criada para a lógica de bater ponto
def bater_ponto(codigo, nome, cargo):
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")

    todos_registros = ler_registros_txt()
    registros_do_dia = [r for r in todos_registros if r['Código'] == codigo and r['Data'] == hoje_str]

    tipo_registro = 'Entrada'
    if registros_do_dia and registros_do_dia[-1]['Tipo'] == 'Entrada':
        tipo_registro = 'Saída'

    novo_registro = {
        "Código": codigo, "Nome": nome, "Cargo": cargo,
        "Data": hoje_str, "Hora": agora.strftime("%H:%M:%S"), "Tipo": tipo_registro,
        "Observação": ""
    }
    
    todos_registros.append(novo_registro)
    salvar_todos_registros_txt(todos_registros)
    
    mensagem_sucesso = f"Ponto de '{tipo_registro}' registado para {nome} às {novo_registro['Hora']}."
    return mensagem_sucesso, "success"

#Função para editar as observações que o Admin pode fazer a respeito dos pontos do fúncionarios
def atualizar_observacao(identificador_registro, nova_observacao):
    todos_registros = ler_registros_txt()
    
    registro_encontrado = False
    for registro in todos_registros:
        id_atual = f"{registro['Código']}-{registro['Data']}-{registro['Hora']}"
        if id_atual == identificador_registro:
            registro['Observação'] = nova_observacao
            registro_encontrado = True
            break
            
    if registro_encontrado:
        salvar_todos_registros_txt(todos_registros)
        return "Observação atualizada com sucesso.", "success"
    else:
        return "Erro: Registro não encontrado para atualização.", "error"
