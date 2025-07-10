from zoneinfo import ZoneInfo
from datetime import time

FUSO_HORARIO = ZoneInfo("America/Fortaleza")

FUNCIONARIOS_JSON = "funcionarios.json"
PONTOS_TXT = "registros_ponto.txt"
RELATORIO_TXT = "relatorio_ponto.txt"

HORARIOS_PADRAO = {
    "Início do Expediente": time(8, 0, 0),
    "Início do Almoço": time(11, 0, 0),
    "Fim do Almoço": time(12, 0, 0),
    "Fim do Expediente": time(18, 0, 0)
}
