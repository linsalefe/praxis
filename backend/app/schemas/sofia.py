from __future__ import annotations

from pydantic import BaseModel, Field


class PerguntarIn(BaseModel):
    pergunta: str = Field(min_length=3, max_length=2000)
    paciente_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class CitacaoOut(BaseModel):
    n: int                              # numeração T{n} usada na resposta
    documento_id: str
    slug: str
    titulo: str
    autor: str
    editora: str | None
    is_terceiro: bool
    capitulo: str | None
    pagina_inicio: int | None
    pagina_fim: int | None
    snippet: str                        # preview curto; sempre truncado
    similaridade: float


class PerguntarOut(BaseModel):
    resposta: str
    citacoes: list[CitacaoOut]
    sem_respaldo: bool
    usou_paciente: bool
    modelo: str
    disclaimer: str


class DocumentoOut(BaseModel):
    id: str
    slug: str
    titulo: str
    autor: str
    editora: str | None
    ano: int | None
    is_terceiro: bool
    total_chunks: int
