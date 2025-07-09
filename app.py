# Importa as bibliotecas necessárias. `streamlit` para a interface, `pandas` para a tabela.
import streamlit as st
import pandas as pd
import time # Importa a biblioteca de tempo para criar pausas

# Importa as funções de lógica de negócio do nosso ficheiro 'services.py'.
# Isto mantém a interface gráfica separada da manipulação de dados (código limpo).
from services import (
    ler_registros_txt, 
    bater_ponto, 
    verificar_login, 
    ler_json_funcionarios,
    adicionar_funcionario,
    remover_funcionario,
    atualizar_observacao,
    obter_proximo_tipo_ponto
)
# Importa as constantes de configuração do nosso ficheiro 'config.py'.
from config import RELATORIO_TXT

# --- Configurações da Página ---
# Este comando deve ser o primeiro comando Streamlit a ser executado.
# Ele define as propriedades da aba do navegador e o layout da página.
st.set_page_config(
    page_title="Ponto Omega",
    page_icon="🔵",
    layout="centered" # 'centered' mantém a interface num layout de largura fixa e centralizado.
)

# --- Gestão de Estado da Sessão ---
# O Streamlit re-executa o script inteiro a cada interação do utilizador.
# `st.session_state` é um dicionário que "sobrevive" a estas re-execuções.
# Usamo-lo para "lembrar" quem está logado.

# Se a chave 'user_info' ainda não existe na sessão, inicializamo-la como None.
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- Telas da Aplicação ---
# Dividimos a aplicação em funções para cada "tela" (login, funcionário, admin).
# Isto torna o código mais legível e organizado.

#Criação do formulario de login
def tela_de_login():
    """Desenha a tela de login no ecrã."""
    st.header("Login do Sistema de Ponto")
    
    # Cria os campos de texto para o código e a senha.
    # `type="password"` esconde os caracteres digitados no campo da senha.
    codigo = st.text_input("Seu Código")
    senha = st.text_input("Sua Senha", type="password")

    # Cria o botão de "Entrar".
    if st.button("Entrar", type="primary"):
        # Se o botão for clicado, verifica se os campos foram preenchidos.
        if codigo and senha:
            # Chama a função de lógica para verificar as credenciais.
            user_info, erro = verificar_login(codigo, senha)
            
            # Se a função de verificação retornar um erro, exibe-o.
            if erro:
                st.error(erro)
            # Se o login for bem-sucedido...
            else:
                # Guarda as informações do utilizador na sessão.
                st.session_state.user_info = user_info
                # Adiciona o código do utilizador à informação da sessão para uso futuro.
                st.session_state.user_info['codigo'] = codigo
                # `st.rerun()` força a página a recarregar imediatamente.
                # Na recarga, a lógica principal irá detetar que `st.session_state.user_info`
                # já não é None e irá mostrar a tela correta.
                st.rerun()
        else:
            st.warning("Por favor, preencha todos os campos.")

#Aqui se encontra a tela de funcionário, onde na tela só tera o botão para bater o ponto, pois a logica de identificação já vai ser feita na tela de login
def tela_funcionario():
    """Desenha a tela para um funcionário normal que fez login."""
    st.title(f"🔵 Bem-vindo, {st.session_state.user_info['nome']}!")
    st.header("Registo de Ponto")
    
    # Chama a função de lógica para saber se o próximo ponto é uma entrada ou uma saída.
    proximo_tipo = obter_proximo_tipo_ponto(st.session_state.user_info['codigo'])
    
    # Cria o botão de bater ponto com o texto dinâmico ("Confirmar Entrada" ou "Confirmar Saída").
    if st.button(f"Confirmar {proximo_tipo}", type="primary", use_container_width=True):
        # Chama a função de lógica para registar o ponto.
        mensagem, tipo = bater_ponto(
            st.session_state.user_info['codigo'], 
            st.session_state.user_info['nome'], 
            st.session_state.user_info['cargo']
        )
        # Exibe a mensagem de sucesso ou erro retornada pela função de lógica.
        if tipo == "success":
            st.success(mensagem)
            # Aguarda 1 segundo para que o utilizador possa ler a mensagem.
            time.sleep(1)
            # Recarrega a página para atualizar o texto do botão para a próxima ação.
            st.rerun()
        else:
            st.error(mensagem)

#Aqui se encontra a tela de admin, onde o admin poderar exportar relátorios e fazer edições em pontos de funcionários
def tela_admin():
    """Desenha o painel completo para o administrador."""
    st.title("🔵 Painel do Administrador")
    
    # Cria as abas para organizar o conteúdo do painel de admin.
    tab1, tab2 = st.tabs(["📋 Relatório de Pontos", "👥 Gerir Funcionários"])

    # Conteúdo da primeira aba: Relatório
    with tab1:
        st.header("Relatório de Pontos")
        funcionarios, _ = ler_json_funcionarios()
        # Cria um dicionário para as opções do filtro, começando com "Todos".
        opcoes_filtro = {"Todos": "Todos"}
        if funcionarios:
            for codigo, info in funcionarios.items():
                # Adiciona apenas os funcionários normais (não o admin) ao filtro.
                if info.get("role") == "employee":
                    opcoes_filtro[codigo] = f"{info['nome']} (Cód: {codigo})"
        
        # Cria o menu suspenso (selectbox) para o filtro.
        codigo_selecionado = st.selectbox(
            "Filtrar por funcionário:",
            options=list(opcoes_filtro.keys()),
            format_func=lambda x: opcoes_filtro[x] # Define como o texto das opções é exibido.
        )
        
        dados_tabela = ler_registros_txt()
        if not dados_tabela:
            st.info("Ainda não há registos de ponto.")
        else:
            df = pd.DataFrame(dados_tabela)
            # Filtra o DataFrame com base na seleção do menu suspenso.
            df_filtrado = df[df['Código'] == codigo_selecionado] if codigo_selecionado != "Todos" else df
            
            if df_filtrado.empty:
                st.info("Nenhum registo para a seleção atual.")
            else:
                # Ordena os registos por data e hora, do mais recente para o mais antigo.
                df_filtrado_sorted = df_filtrado.sort_values(by=["Data", "Hora"], ascending=False)
                
                # Inicializa a variável de edição na sessão se ela não existir.
                if 'edit_id' not in st.session_state:
                    st.session_state.edit_id = None

                # Faz um loop por cada linha do DataFrame para exibir os registos individualmente.
                for index, row in df_filtrado_sorted.iterrows():
                    # Cria um ID único para cada registo, usado para as chaves dos botões.
                    registro_id = f"{row['Código']}-{row['Data']}-{row['Hora']}"
                    
                    # Usa um container para agrupar visualmente cada registo.
                    with st.container(border=True):
                        col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 3, 1])
                        col1.text(f"Cód: {row['Código']}")
                        col2.text(f"Nome: {row['Nome']}")
                        col3.text(f"Data: {row['Data']}")
                        col4.text(f"Hora: {row['Hora']} ({row['Tipo']})")
                        
                        # Cria o botão "Editar". A chave (key) é única para cada botão.
                        if col5.button("Editar", key=f"edit_{registro_id}"):
                            # Ao clicar, guarda o ID do registo na sessão e recarrega a página.
                            st.session_state.edit_id = registro_id
                            st.rerun()

                        # Se o ID deste registo for o que está guardado na sessão, mostra a área de edição.
                        if st.session_state.edit_id == registro_id:
                            nova_obs = st.text_area(
                                "Observação:", 
                                value=row.get('Observação', ''), 
                                key=f"obs_{registro_id}"
                            )
                            col_save, col_cancel, _ = st.columns([1, 1, 5])
                            if col_save.button("Salvar", key=f"save_{registro_id}", type="primary"):
                                msg, tipo = atualizar_observacao(registro_id, nova_obs)
                                if tipo == "success": st.success(msg)
                                else: st.error(msg)
                                # Limpa o ID da sessão para sair do modo de edição e recarrega.
                                st.session_state.edit_id = None
                                st.rerun()
                            
                            if col_cancel.button("Cancelar", key=f"cancel_{registro_id}"):
                                st.session_state.edit_id = None
                                st.rerun()
                        # Se não estiver em modo de edição, mas houver uma observação, exibe-a.
                        elif row.get('Observação'):
                            st.markdown(f"**Obs:** *{row['Observação']}*")
                
                # Gera o conteúdo do ficheiro de texto para download.
                relatorio_texto = f"Relatório de Pontos - {opcoes_filtro[codigo_selecionado]}\n" + "="*40 + "\n\n"
                for _, row in df_filtrado_sorted.iterrows():
                    relatorio_texto += f"Nome: {row['Nome']} (Cód: {row['Código']})\n"
                    relatorio_texto += f"Data: {row['Data']} | Hora: {row['Hora']} | Tipo: {row['Tipo']}\n" + "-"*20 + "\n"
                
                # Cria o botão para descarregar o relatório em .txt.
                st.download_button(
                    "Descarregar Relatório em .txt",
                    relatorio_texto.encode('utf-8'),
                    f"relatorio_{codigo_selecionado}.txt",
                    "text/plain"
                )

    # Conteúdo da segunda aba: Gestão de Funcionários
    with tab2:
        st.header("Gestão de Funcionários")
        # Usa um formulário para que os campos só sejam processados quando o botão for clicado.
        with st.form("novo_funcionario", clear_on_submit=True):
            st.subheader("Adicionar Novo Funcionário")
            novo_codigo = st.text_input("Código do Funcionário")
            novo_nome = st.text_input("Nome Completo")
            novo_cargo = st.text_input("Cargo")
            nova_senha = st.text_input("Senha Temporária", type="password")
            if st.form_submit_button("Adicionar"):
                msg, tipo = adicionar_funcionario(novo_codigo, novo_nome, novo_cargo, nova_senha)
                if tipo == "success": st.success(msg)
                else: st.error(msg)
        
        st.divider()
        st.subheader("Funcionários Atuais")
        if funcionarios:
            for codigo, info in funcionarios.items():
                if info.get("role") == "employee":
                    col1, col2, col3 = st.columns([1, 2, 1])
                    col1.write(f"**Cód:** {codigo}")
                    col2.write(f"**Nome:** {info['nome']}")
                    if col3.button("Remover", key=f"rem_{codigo}"):
                        msg, tipo = remover_funcionario(codigo)
                        if tipo == "success": 
                            st.success(msg)
                            st.rerun()
                        else: 
                            st.error(msg)

# --- Lógica de Roteamento ---
# Este é o bloco principal que decide qual tela mostrar.

# Se a sessão contém informações do utilizador, significa que ele está logado.
if st.session_state.user_info:
    # Cria o botão de "Sair" na barra lateral.
    if st.sidebar.button("Sair"):
        # Limpa as informações da sessão e recarrega a página, voltando para a tela de login.
        st.session_state.user_info = None
        st.rerun()

    # Verifica o "papel" (role) do utilizador para decidir qual tela mostrar.
    if st.session_state.user_info.get("role") == "admin":
        tela_admin()
    else:
        tela_funcionario()
# Se não houver informações do utilizador na sessão, mostra a tela de login.
else:
    tela_de_login()
