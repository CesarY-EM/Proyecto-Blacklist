from pydantic import BaseModel
from typing import List

class ResultadoBloque(BaseModel):
    bloque: str
    resultado: str
    hallazgos: List[dict] = []
    muestras: List[dict] = []

    class Config:
        from_attributes=True
