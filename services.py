# Importa as bibliotecas necessárias para o funcionamento da lógica.
import json
import os
from datetime import datetime
# Importa as constantes de configuração do ficheiro 'config.py'.
from config import FUNCIONARIOS_JSON, PONTOS_TXT, FUSO_HORARIO


#Faz a leitura do registro de funcionários 
def ler_json_funcionarios():
    """Lê o ficheiro JSON de funcionários de forma segura."""
    # Verifica se o ficheiro de funcionários existe antes de tentar abri-lo.
    if not os.path.exists(FUNCIONARIOS_JSON):
        # Se não existir, retorna um erro claro.
        return None, f"Erro crítico: O ficheiro '{FUNCIONARIOS_JSON}' não foi encontrado."
    try:
        # Abre o ficheiro, lê o seu conteúdo e converte o JSON para um dicionário Python.
        with open(FUNCIONARIOS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f), None # Retorna os dados e None para o erro.
    except (json.JSONDecodeError, IOError) as e:
        # Se houver um erro ao ler ou decodificar o JSON, retorna um erro.
        return None, f"Erro ao ler o ficheiro '{FUNCIONARIOS_JSON}': {e}"

#Faz a leitura do arquivo em txt
def ler_registros_txt():
    """Lê os registros de ponto do ficheiro .txt e os transforma numa lista de dicionários."""
    # Se o ficheiro de pontos não existir, retorna uma lista vazia.
    if not os.path.exists(PONTOS_TXT):
        return []
    
    registros = []
    # Abre o ficheiro para leitura.
    with open(PONTOS_TXT, 'r', encoding='utf-8') as f:
        # Itera sobre cada linha do ficheiro.
        for linha in f:
            # Remove espaços em branco e divide a linha pelo caractere '|'.
            partes = linha.strip().split('|')
            # Verifica se a linha tem o número mínimo de campos esperado.
            if len(partes) >= 6:
                # Cria um dicionário para o registo e adiciona-o à lista.
                registros.append({
                    "Código": partes[0], "Nome": partes[1], "Cargo": partes[2],
                    "Data": partes[3], "Hora": partes[4], "Tipo": partes[5],
                    # Adiciona a observação se ela existir, senão deixa em branco.
                    "Observação": partes[6] if len(partes) > 6 else ""
                })
    return registros


#Função criada para salvar os arquivos no txt, e futuramente iremos exportar esse arquivo
def salvar_todos_registros_txt(registros):
    """Salva a lista completa de registros no ficheiro .txt, sobrescrevendo o conteúdo."""
    # Abre o ficheiro em modo de escrita ('w'), o que apaga o conteúdo antigo.
    with open(PONTOS_TXT, 'w', encoding='utf-8') as f:
        for registro in registros:
            # Formata cada registo numa linha de texto com os campos separados por '|'.
            linha = (
                f"{registro['Código']}|{registro['Nome']}|{registro['Cargo']}|"
                f"{registro['Data']}|{registro['Hora']}|{registro['Tipo']}|"
                f"{registro.get('Observação', '')}\n"
            )
            f.write(linha)

#Função criada para a lógica de login de users
def verificar_login(codigo, senha):
    """Verifica se o código e a senha correspondem a um utilizador e retorna os seus dados."""
    funcionarios, erro = ler_json_funcionarios()
    if erro:
        return None, erro

    # Obtém os dados do utilizador pelo código.
    user_data = funcionarios.get(codigo)
    # Verifica se o utilizador existe e se a senha está correta.
    if user_data and user_data['senha'] == senha:
        return user_data, None
    else:
        return None, "Código ou senha inválidos."

#Função criada para a lógica de bater ponto
def bater_ponto(codigo, nome, cargo):
    """Regista a entrada ou saída de um funcionário."""
    # Obtém a data e hora atuais no fuso horário correto.
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")

    todos_registros = ler_registros_txt()
    # Filtra para obter apenas os registos do funcionário no dia de hoje.
    registros_do_dia = [r for r in todos_registros if r['Código'] == codigo and r['Data'] == hoje_str]

    # Determina se o ponto é uma 'Entrada' ou uma 'Saída'.
    tipo_registro = 'Entrada'
    if registros_do_dia and registros_do_dia[-1]['Tipo'] == 'Entrada':
        tipo_registro = 'Saída'

    # Cria o dicionário para o novo registo.
    novo_registro = {
        "Código": codigo, "Nome": nome, "Cargo": cargo,
        "Data": hoje_str, "Hora": agora.strftime("%H:%M:%S"), "Tipo": tipo_registro,
        "Observação": "" # A observação começa sempre vazia.
    }
    
    # Adiciona o novo registo à lista e salva tudo de volta no ficheiro.
    todos_registros.append(novo_registro)
    salvar_todos_registros_txt(todos_registros)
    
    # Retorna uma mensagem de sucesso para ser exibida na interface.
    mensagem_sucesso = f"Ponto de '{tipo_registro}' registado para {nome} às {novo_registro['Hora']}."
    return mensagem_sucesso, "success"

#Função para editar as observações que o Admin pode fazer a respeito dos pontos do fúncionarios
def atualizar_observacao(identificador_registro, nova_observacao):
    """Encontra um registro específico e atualiza a sua observação."""
    todos_registros = ler_registros_txt()
    
    registro_encontrado = False
    # Itera por todos os registos para encontrar o que corresponde ao ID.
    for registro in todos_registros:
        # Cria um ID temporário para o registo atual para comparação.
        id_atual = f"{registro['Código']}-{registro['Data']}-{registro['Hora']}"
        if id_atual == identificador_registro:
            # Atualiza o campo de observação e marca como encontrado.
            registro['Observação'] = nova_observacao
            registro_encontrado = True
            break
            
    if registro_encontrado:
        # Se encontrou, salva a lista completa de registos atualizada.
        salvar_todos_registros_txt(todos_registros)
        return "Observação atualizada com sucesso.", "success"
    else:
        return "Erro: Registro não encontrado para atualização.", "error"

#Função para salvar o arquivo de funcionários em JSON
def salvar_json(caminho_arquivo, dados):
    """Função auxiliar para salvar o ficheiro de funcionários."""
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

#Função para o admin adicionar um novo funcionário
def adicionar_funcionario(codigo, nome, cargo, senha):
    """Adiciona um novo funcionário (usado pelo admin)."""
    funcionarios, erro = ler_json_funcionarios()
    if erro:
        return erro, "error"
    
    # Verifica se o código já está em uso.
    if codigo in funcionarios:
        return f"O código '{codigo}' já está em uso.", "warning"
    
    # Adiciona o novo funcionário ao dicionário e salva no ficheiro.
    funcionarios[codigo] = {"nome": nome, "cargo": cargo, "senha": senha, "role": "employee"}
    salvar_json(FUNCIONARIOS_JSON, funcionarios)
    return f"Funcionário '{nome}' adicionado com sucesso.", "success"

#Função para o admin remover um funcionário
def remover_funcionario(codigo):
    """Remove um funcionário (usado pelo admin)."""
    funcionarios, erro = ler_json_funcionarios()
    if erro:
        return erro, "error"

    # Verifica se o funcionário existe e não é o admin.
    if codigo in funcionarios and codigo != "admin":
        del funcionarios[codigo]
        salvar_json(FUNCIONARIOS_JSON, funcionarios)
        return f"Funcionário com código '{codigo}' removido.", "success"
    else:
        return "Funcionário não encontrado ou não pode ser removido.", "error"

#Função para determinar qual a próxima ação do funcionário (Entrada ou Saída)
def obter_proximo_tipo_ponto(codigo):
    """Verifica o último registro do dia para determinar a próxima ação."""
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")

    todos_registros = ler_registros_txt()
    registros_do_dia = [r for r in todos_registros if r['Código'] == codigo and r['Data'] == hoje_str]

    if registros_do_dia and registros_do_dia[-1]['Tipo'] == 'Entrada':
        return 'Saída'
    else:
        return 'Entrada'
