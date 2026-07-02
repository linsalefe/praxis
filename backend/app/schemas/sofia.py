from __future__ import annotations

from pydantic import BaseModel, Field


class PerguntarIn(BaseModel):
    pergunta: str = Field(min_length=3, max_length=2000)
    paciente_id: str | None = None
    conversa_id: str | None = None      # continua uma conversa existente; None cria nova
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
    conversa_id: str                    # conversa onde o turno foi gravado


class ConversaResumoOut(BaseModel):
    id: str
    titulo: str
    paciente_id: str | None
    total_turnos: int
    criado_em: str
    atualizado_em: str


class TurnoOut(BaseModel):
    pergunta: str
    resposta: str
    citacoes: list[CitacaoOut]
    sem_respaldo: bool
    usou_paciente: bool
    modelo: str | None
    disclaimer: str
    criado_em: str


class ConversaDetalheOut(BaseModel):
    id: str
    titulo: str
    paciente_id: str | None
    criado_em: str
    turnos: list[TurnoOut]


class DocumentoOut(BaseModel):
    id: str
    slug: str
    titulo: str
    autor: str
    editora: str | None
    ano: int | None
    is_terceiro: bool
    total_chunks: int
