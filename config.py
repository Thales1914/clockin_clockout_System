from zoneinfo import ZoneInfo
from datetime import time

# --- Configurações de Fuso Horário ---
FUSO_HORARIO = ZoneInfo("America/Fortaleza")

# --- Nomes dos Ficheiros de Dados ---
FUNCIONARIOS_JSON = "funcionarios.json"
# MUDANÇA: Os nomes dos ficheiros foram atualizados para .csv
PONTOS_CSV = "registros_ponto.csv"
RELATORIO_CSV = "relatorio_ponto.csv"

# --- Horários Padrão da Jornada ---
HORARIOS_PADRAO = {
    "Início do Expediente": time(8, 0, 0),
    "Início do Almoço": time(11, 0, 0),
    "Fim do Almoço": time(12, 0, 0),
    "Fim do Expediente": time(18, 0, 0)
}
