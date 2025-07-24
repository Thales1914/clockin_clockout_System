import sqlite3
import pandas as pd
from datetime import datetime, time
from config import DATABASE_FILE, FUSO_HORARIO, HORARIOS_PADRAO, TOLERANCIA_MINUTOS
import hashlib
from contextlib import contextmanager
import numpy as np
import io

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_empresa TEXT NOT NULL UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funcionarios (
                codigo TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                senha TEXT NOT NULL,
                role TEXT NOT NULL,
                empresa_id INTEGER,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros (
                id TEXT PRIMARY KEY,
                codigo_funcionario TEXT NOT NULL,
                nome TEXT NOT NULL,
                data TEXT NOT NULL,
                hora TEXT NOT NULL,
                descricao TEXT NOT NULL,
                diferenca_min INTEGER NOT NULL,
                observacao TEXT,
                FOREIGN KEY (codigo_funcionario) REFERENCES funcionarios (codigo)
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM empresas")
        if cursor.fetchone()[0] == 0:
            initial_empresas = [
                ('Ômega Barroso',), ('Ômega Matriz',),
                ('Ômega Cariri',), ('Ômega Sobral',)
            ]
            cursor.executemany("INSERT INTO empresas (nome_empresa) VALUES (?)", initial_empresas)

        cursor.execute("SELECT COUNT(*) FROM funcionarios")
        if cursor.fetchone()[0] == 0:
            initial_users = [
                ('admin', 'Administrador', _hash_senha('admin123'), 'admin', None)
            ]
            cursor.executemany("INSERT INTO funcionarios (codigo, nome, senha, role, empresa_id) VALUES (?, ?, ?, ?, ?)", initial_users)

        conn.commit()

def ler_empresas():
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT id, nome_empresa FROM empresas ORDER BY nome_empresa", conn)
    return df

def ler_funcionarios_df():
    with get_db_connection() as conn:
        query = """
            SELECT f.codigo, f.nome, f.role, f.empresa_id, e.nome_empresa
            FROM funcionarios f
            LEFT JOIN empresas e ON f.empresa_id = e.id
        """
        df = pd.read_sql_query(query, conn)
    return df

def verificar_login(codigo, senha):
    senha_hash = _hash_senha(senha)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM funcionarios WHERE codigo = ? AND senha = ?", (codigo, senha_hash))
        user = cursor.fetchone()
        
        if user:
            return dict(user), None
    return None, "Código ou senha inválidos."

def obter_proximo_evento(codigo):
    hoje_str = datetime.now(FUSO_HORARIO).strftime("%Y-%m-%d")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM registros WHERE codigo_funcionario = ? AND data = ?", (codigo, hoje_str))
        num_pontos = cursor.fetchone()[0]
    
    eventos_programados = list(HORARIOS_PADRAO.keys())
    if num_pontos < len(eventos_programados):
        return eventos_programados[num_pontos]
    return "Jornada Finalizada"

def bater_ponto(codigo, nome):
    agora = datetime.now(FUSO_HORARIO)
    hoje_str = agora.strftime("%Y-%m-%d")
    proximo_evento = obter_proximo_evento(codigo)

    if proximo_evento == "Jornada Finalizada":
        return "Sua jornada de hoje já foi completamente registada.", "warning"

    hora_prevista = HORARIOS_PADRAO[proximo_evento]
    datetime_previsto = agora.replace(hour=hora_prevista.hour, minute=hora_prevista.minute, second=0, microsecond=0)
    
    diferenca_bruta_min = round((agora - datetime_previsto).total_seconds() / 60)
    
    if abs(diferenca_bruta_min) <= TOLERANCIA_MINUTOS:
        diferenca_final_min = 0
    else:
        if diferenca_bruta_min > 0:
            diferenca_final_min = diferenca_bruta_min - TOLERANCIA_MINUTOS
        else:
            diferenca_final_min = diferenca_bruta_min + TOLERANCIA_MINUTOS
            
    novo_registro = {
        "id": f"{codigo}-{agora.isoformat()}", "codigo_funcionario": codigo, "nome": nome,
        "data": hoje_str, "hora": agora.strftime("%H:%M:%S"),
        "descricao": proximo_evento, "diferenca_min": diferenca_final_min, "observacao": ""
    }

    with get_db_connection() as conn:
        with conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO registros (id, codigo_funcionario, nome, data, hora, descricao, diferenca_min, observacao) VALUES (:id, :codigo_funcionario, :nome, :data, :hora, :descricao, :diferenca_min, :observacao)", novo_registro)
    
    msg_extra = ""
    if diferenca_final_min != 0:
        if diferenca_final_min > 0:
            msg_extra = f" ({diferenca_final_min} min de atraso)"
        else:
            msg_extra = f" ({-diferenca_final_min} min de adiantamento)"

    status_final = " (em ponto)"
    if diferenca_final_min != 0:
        status_final = ""
    elif diferenca_bruta_min != 0:
        status_final = " (dentro da tolerância, registrado como 'em ponto')"
        
    return f"'{proximo_evento}' registado para {nome} às {novo_registro['hora']}{msg_extra}{status_final}.", "success"

def ler_registros_df():
    with get_db_connection() as conn:
        query = """
            SELECT
                r.id, r.codigo_funcionario, r.nome, r.data, r.hora,
                r.descricao, r.diferenca_min, r.observacao, e.nome_empresa
            FROM registros r
            JOIN funcionarios f ON r.codigo_funcionario = f.codigo
            LEFT JOIN empresas e ON f.empresa_id = e.id
        """
        df = pd.read_sql_query(query, conn)
    
    df = df.rename(columns={
        'id': 'ID', 'codigo_funcionario': 'Código', 'nome': 'Nome',
        'data': 'Data', 'hora': 'Hora', 'descricao': 'Descrição', 
        'diferenca_min': 'Diferença (min)', 'observacao': 'Observação',
        'nome_empresa': 'Empresa'
    })
    return df

def atualizar_registro(id_registro, novo_horario=None, nova_observacao=None):
    try:
        with get_db_connection() as conn:
            with conn:
                cursor = conn.cursor()
                if nova_observacao is not None:
                    cursor.execute("UPDATE registros SET observacao = ? WHERE id = ?", (nova_observacao, id_registro))

                if novo_horario is not None:
                    novo_horario_obj = datetime.strptime(novo_horario, "%H:%M:%S").time()
                    cursor.execute("SELECT descricao, data FROM registros WHERE id = ?", (id_registro,))
                    row = cursor.fetchone()
                    if row:
                        descricao_evento = row['descricao']
                        hora_prevista = HORARIOS_PADRAO.get(descricao_evento)
                        if hora_prevista:
                            data_registro = datetime.strptime(row['data'], "%Y-%m-%d")
                            datetime_previsto = data_registro.replace(hour=hora_prevista.hour, minute=hora_prevista.minute)
                            datetime_novo = data_registro.replace(hour=novo_horario_obj.hour, minute=novo_horario_obj.minute, second=novo_horario_obj.second)
                            
                            diferenca_bruta_min = round((datetime_novo - datetime_previsto).total_seconds() / 60)

                            if abs(diferenca_bruta_min) <= TOLERANCIA_MINUTOS:
                                diferenca_final_min = 0
                            else:
                                if diferenca_bruta_min > 0:
                                    diferenca_final_min = diferenca_bruta_min - TOLERANCIA_MINUTOS
                                else:
                                    diferenca_final_min = diferenca_bruta_min + TOLERANCIA_MINUTOS
                            
                            cursor.execute("UPDATE registros SET hora = ?, diferenca_min = ? WHERE id = ?", (novo_horario, diferenca_final_min, id_registro))

    except ValueError:
        return "Formato de hora inválido. Use HH:MM:SS.", "error"
    except sqlite3.Error as e:
        return f"Erro no banco de dados: {e}", "error"

    return "Registro atualizado com sucesso.", "success"

def adicionar_funcionario(codigo, nome, senha, empresa_id):
    if not all([codigo, nome, senha, empresa_id]):
        return "Todos os campos, incluindo a empresa, são obrigatórios.", "error"

    try:
        with get_db_connection() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT codigo FROM funcionarios WHERE codigo = ?", (codigo,))
                if cursor.fetchone():
                    return f"O código '{codigo}' já está em uso por outro funcionário.", "warning"

                senha_hash = _hash_senha(senha)
                cursor.execute(
                    "INSERT INTO funcionarios (codigo, nome, senha, role, empresa_id) VALUES (?, ?, ?, ?, ?)",
                    (codigo, nome, senha_hash, 'employee', empresa_id)
                )
    except sqlite3.Error as e:
        return f"Erro no banco de dados ao adicionar funcionário: {e}", "error"

    return f"Funcionário '{nome}' adicionado com sucesso!", "success"

def importar_funcionarios_em_massa(df_funcionarios, empresa_id):
    novos_funcionarios = []
    erros = []
    sucesso_count = 0
    ignorados_count = 0
    df_existentes = ler_funcionarios_df()
    codigos_existentes = df_existentes['codigo'].tolist()
    colunas_necessarias = ['MATRICULA', 'COLABORADOR', 'SENHA']
    for col in colunas_necessarias:
        if col not in df_funcionarios.columns:
            erros.append(f"Erro Crítico: A coluna obrigatória '{col}' não foi encontrada no arquivo.")
            return 0, 0, erros
    for index, row in df_funcionarios.iterrows():
        try:
            codigo = str(row['MATRICULA']).strip()
            nome_completo = str(row['COLABORADOR']).strip()
            senha_texto = str(row['SENHA']).strip()
            if codigo in codigos_existentes:
                ignorados_count += 1
                continue
            if not all([codigo, nome_completo, senha_texto]):
                erros.append(f"Linha {index+2}: Contém dados incompletos.")
                continue
            senha_hash = _hash_senha(senha_texto)
            novos_funcionarios.append((codigo, nome_completo, senha_hash, 'employee', empresa_id))
            codigos_existentes.append(codigo)
        except Exception as e:
            erros.append(f"Linha {index+2}: Erro ao processar - {e}")
    if novos_funcionarios:
        try:
            with get_db_connection() as conn:
                with conn:
                    cursor = conn.cursor()
                    cursor.executemany(
                        "INSERT INTO funcionarios (codigo, nome, senha, role, empresa_id) VALUES (?, ?, ?, ?, ?)",
                        novos_funcionarios
                    )
                    sucesso_count = len(novos_funcionarios)
        except sqlite3.Error as e:
            erros.append(f"Erro geral no banco de dados: {e}")
            sucesso_count = 0
    return sucesso_count, ignorados_count, erros

def _formatar_timedelta(td):
    if pd.isnull(td):
        return "00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"

def gerar_relatorio_organizado_df(df_registros: pd.DataFrame) -> pd.DataFrame:
    if df_registros.empty:
        return pd.DataFrame()

    df = df_registros.copy()

    mapeamento_eventos = {
        "Início do Expediente": "Entrada",
        "Fim do Expediente": "Saída"
    }
    df['Descrição'] = df['Descrição'].replace(mapeamento_eventos)

    df_pivot = df.pivot_table(
        index=['Data', 'Código', 'Nome', 'Empresa'],
        columns='Descrição',
        values='Hora',
        aggfunc='first'
    ).reset_index()

    df_obs = df.dropna(subset=['Observação']).groupby(['Data', 'Código'])['Observação'].apply(lambda x: ' | '.join(x.unique())).reset_index()
    
    df_final = pd.merge(df_pivot, df_obs, on=['Data', 'Código'], how='left')
    df_final['Observação'] = df_final['Observação'].fillna('')

    eventos = ['Entrada', 'Saída']
    for evento in eventos:
        if evento not in df_final.columns:
            df_final[evento] = np.nan
        df_final[evento] = pd.to_datetime(df_final[evento], format='%H:%M:%S', errors='coerce').dt.time

    dt_entrada = pd.to_datetime(df_final['Data'].astype(str) + ' ' + df_final['Entrada'].astype(str), errors='coerce')
    dt_saida = pd.to_datetime(df_final['Data'].astype(str) + ' ' + df_final['Saída'].astype(str), errors='coerce')

    horas_trabalhadas = dt_saida - dt_entrada
    
    df_final['Total Horas Trabalhadas'] = horas_trabalhadas.apply(_formatar_timedelta)
    
    colunas_finais = [
        'Data', 'Código', 'Nome', 'Empresa',
        'Entrada', 'Saída',
        'Total Horas Trabalhadas', 'Observação'
    ]
    for col in colunas_finais:
        if col not in df_final.columns:
            df_final[col] = 'N/A'
            
    df_final = df_final[colunas_finais]
    
    df_final.rename(columns={'Código': 'Código do Funcionário', 'Nome': 'Nome do Funcionário'}, inplace=True)
    df_final['Data'] = pd.to_datetime(df_final['Data']).dt.strftime('%d/%m/%Y')
    return df_final

def gerar_arquivo_excel(df_organizado, df_bruto):
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        df_organizado.to_excel(writer, sheet_name='Relatório Diário', index=False)
        df_bruto.to_excel(writer, sheet_name='Log de Eventos (Bruto)', index=False)
        workbook = writer.book
        worksheet_organizado = writer.sheets['Relatório Diário']
        for column in worksheet_organizado.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet_organizado.column_dimensions[column_letter].width = adjusted_width
        worksheet_bruto = writer.sheets['Log de Eventos (Bruto)']
        for column in worksheet_bruto.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet_bruto.column_dimensions[column_letter].width = adjusted_width
    output_buffer.seek(0)
    return output_buffer