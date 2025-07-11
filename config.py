from zoneinfo import ZoneInfo
from datetime import time


FUSO_HORARIO = ZoneInfo("America/Fortaleza")


DATABASE_FILE = "ponto.db"
RELATORIO_CSV = "relatorio_ponto.csv"


HORARIOS_PADRAO = {
    "Início do Expediente": time(8, 0, 0),
    "Início do Almoço": time(11, 0, 0),
    "Fim do Almoço": time(12, 0, 0),
    "Fim do Expediente": time(18, 0, 0)
}
