from app.instrumentos.definitions.dass21_v1 import DASS21_V1
from app.instrumentos.definitions.gad7_v1 import GAD7_V1
from app.instrumentos.definitions.gam_v1 import GAM_V1
from app.instrumentos.definitions.maastricht_v1 import MAASTRICHT_V1
from app.instrumentos.definitions.phq9_v1 import PHQ9_V1
from app.instrumentos.definitions.ptmf_v1 import PTMF_V1
from app.instrumentos.definitions.srq20_v1 import SRQ20_V1
from app.instrumentos.definitions.who5_v1 import WHO5_V1
from app.instrumentos.definitions.wrap_v1 import WRAP_V1

# Escalas Likert quantitativas (kind: likert_sum) — escore/faixa factuais.
ESCALAS_LIKERT = [PHQ9_V1, GAD7_V1, WHO5_V1, DASS21_V1, SRQ20_V1]

# Qualitativos (secoes) — formulação/síntese narrativa, sem escore.
QUALITATIVOS = [MAASTRICHT_V1, WRAP_V1, GAM_V1, PTMF_V1]

CATALOGO = [*QUALITATIVOS, *ESCALAS_LIKERT]

__all__ = [
    "CATALOGO",
    "ESCALAS_LIKERT",
    "QUALITATIVOS",
    "MAASTRICHT_V1",
    "WRAP_V1",
    "GAM_V1",
    "PTMF_V1",
    "PHQ9_V1",
    "GAD7_V1",
    "WHO5_V1",
    "DASS21_V1",
    "SRQ20_V1",
]
