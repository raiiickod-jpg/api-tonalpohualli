from datetime import datetime, timedelta
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="API Calendario Mexica / Tonalpohualli")

# ---------------------------------------------------------
# CONSTANTES Y TABLAS OFICIALES
# ---------------------------------------------------------
ANCHOR_DATE = datetime(1818, 3, 15)  # 1 Cipactli, Año 1 Tochtli

SIGNOS = [
    ("Cipactli", 1), ("Ehecatl", 1), ("Calli", 1), ("Cuetzpalin", 1), ("Coatl", 1),
    ("Miquiztli", -1), ("Mazatl", 1), ("Tochtli", 1), ("Atl", -1), ("Itzcuintli", 0),
    ("Ozomatli", 1), ("Malinalli", -1), ("Acatl", 1), ("Ocelotl", 1), ("Cuauhtli", 1),
    ("Cozcacuauhtli", 1), ("Ollin", 1), ("Tecpatl", 0), ("Quiahuitl", -1), ("Xochitl", 1)
]

NUMERALES_NAHUATL = [
    "Ce", "Ome", "Yei", "Nahui", "Macuilli", "Chicuace", "Chicome",
    "Chicuei", "Chicnahui", "Matlactli", "Matlactli omome", "Matlactli omeyi", "Matlactli onnahui"
]

TONALTEUCTIN = [
    ("Xiuhtecuhtli", 1), ("Tlaltecuhtli", -1), ("Chalchiuhtlicue", 1), ("Tonatiuh", 1),
    ("Tlazoltéotl", 0), ("Mictlantecuhtli", -1), ("Cintéotl", 1), ("Tláloc", 1),
    ("Quetzalcóatl", 1), ("Tezcatlipoca", 0), ("Mictlantecuhtli", -1),
    ("Tlahuizcalpantecuhtli", -1), ("Citlalicue", 1)
]

YOHUALTEUCTIN = [
    ("Xiuhtecuhtli", 1), ("Itztli", -1), ("Piltzintecuhtli", 1), ("Cintéotl", 1),
    ("Mictlantecuhtli", -1), ("Chalchiuhtlicue", 1), ("Tlazoltéotl", 0),
    ("Tepeyollotli", 1), ("Tláloc", 1)
]

CARGADORES = ["Tochtli", "Acatl", "Tecpatl", "Calli"]

# ---------------------------------------------------------
# FUNCIONES MATEMÁTICAS CORE
# ---------------------------------------------------------
def get_year_info(date_obj: datetime):
    """Determina el Año Base Mexica, si cae en Nemontemi y el Cargador del Año."""
    year_start = datetime(date_obj.year, 3, 15)
    
    if date_obj < year_start:
        base_year = date_obj.year - 1
        curr_year_start = datetime(base_year, 3, 15)
    else:
        base_year = date_obj.year
        curr_year_start = year_start

    years_elapsed = base_year - 1818
    numeral_year = (years_elapsed % 13) + 1
    cargador_signo = CARGADORES[years_elapsed % 4]
    
    is_acatl = (cargador_signo == "Acatl")
    nemontemi_days = 6 if is_acatl else 5
    
    # Revisar si la fecha cae en Nemontemi del año solar (previo a 15 de marzo)
    next_year_start = datetime(base_year + 1, 3, 15)
    nemontemi_start = next_year_start - timedelta(days=nemontemi_days)
    
    is_nemontemi = nemontemi_start <= date_obj < next_year_start
    
    return base_year, years_elapsed, numeral_year, cargador_signo, is_nemontemi, curr_year_start

def calc_active_days(date_obj: datetime) -> int:
    """Calcula los días activos acumulados del Tonalpohualli (360 días por año)."""
    base_year, years_elapsed, _, _, is_nemontemi, curr_year_start = get_year_info(date_obj)
    past_active_days = years_elapsed * 360
    
    if is_nemontemi:
        days_in_curr_year = 360
    else:
        days_in_curr_year = (date_obj - curr_year_start).days
        if days_in_curr_year > 360:
            days_in_curr_year = 360
            
    return past_active_days + days_in_curr_year

def compute_tonal_data(date_obj: datetime):
    """Genera la ficha completa del Tonalpohualli para una fecha dada."""
    base_year, _, num_year, cargador, is_nemontemi, _ = get_year_info(date_obj)
    
    if is_nemontemi:
        return f"{date_obj.strftime('%d de %B de %Y')}, Pausa Ritual en Nemontemi, año {num_year} {cargador}."
    
    total_active = calc_active_days(date_obj)
    
    # Numeral y Signo del Día
    num_day = (total_active % 13) + 1
    idx_sign = total_active % 20
    sign_name, sign_val = SIGNOS[idx_sign]
    
    # Trecena Regente (Signo inicial con numeral 1)
    idx_trecena = (idx_sign - (num_day - 1)) % 20
    trecena_name, _ = SIGNOS[idx_trecena]
    
    # Dioses y Carga Energetica
    day_lord_name, day_lord_val = TONALTEUCTIN[num_day - 1]
    night_lord_name, night_lord_val = YOHUALTEUCTIN[total_active % 9]
    
    # Evaluación de Carga (+1, 0, -1)
    score = sign_val + day_lord_val + night_lord_val
    auspicio = "Favorable" if score > 0 else ("Neutral" if score == 0 else "Desfavorable")
    
    num_nahuatl = NUMERALES_NAHUATL[num_day - 1]
    
    return f"{date_obj.day} de {date_obj.strftime('%B')} de {date_obj.year}, {num_nahuatl} {sign_name}, Ce {trecena_name}, año {num_year} {cargador}, carga {score:+d} {auspicio}."

# ---------------------------------------------------------
# ENDPOINTS DE LA API
# ---------------------------------------------------------
class SearchQuery(BaseModel):
    numeral: int
    signo_index: int
    base_date: str = None  # Formato YYYY-MM-DD (por defecto hoy)

@app.get("/calcular")
def calcular_fecha(fecha: str):
    """Ejemplo: GET /calcular?fecha=2026-11-07"""
    dt = datetime.strptime(fecha, "%Y-%m-%d")
    return {"resultado": compute_tonal_data(dt)}

@app.post("/buscar_proximo")
def buscar_proximo(query: SearchQuery):
    """Busca la fecha del próximo (numeral, signo) objetivo."""
    curr_dt = datetime.strptime(query.base_date, "%Y-%m-%d") if query.base_date else datetime.now()
    
    # Índice absoluto objetivo T2 (0 a 259)
    t2 = (40 * (query.numeral - 1) + 221 * query.signo_index) % 260
    
    # Iteración día a día agregando saltos de Nemontemi en marzo
    target_dt = curr_dt + timedelta(days=1)
    while True:
        total_active = calc_active_days(target_dt)
        if (total_active % 13) + 1 == query.numeral and (total_active % 20) == query.signo_index:
            break
        target_dt += timedelta(days=1)
        
    return {"resultado": compute_tonal_data(target_dt)}
