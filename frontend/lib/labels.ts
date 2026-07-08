/**
 * Dicionário único de rótulos de exibição — nenhum enum cru deve chegar à UI.
 * Regra: sempre passar por statusLabel/eventoLabel/modalidadeLabel/formaPagamentoLabel.
 * O <StatusBadge> (components/ui/StatusBadge) consome statusLabel + statusTone.
 */

export type Tom = "pos" | "info" | "warn" | "risk" | "neutral";

/** Fallback humano: "em_andamento" → "Em andamento" (nunca o enum cru). */
export function humanizar(v: string): string {
  const s = v.replace(/[_-]+/g, " ").trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : v;
}

// --- Status (sessões, evoluções, documentos, instrumentos, financeiro) ---
const STATUS_LABEL: Record<string, string> = {
  // sessões
  agendada: "Agendada",
  realizada: "Realizada",
  falta: "Falta",
  cancelada: "Cancelada",
  // evoluções / documentos
  rascunho: "Rascunho",
  assinado: "Assinado",
  assinada: "Assinada",
  // instrumentos
  em_andamento: "Em andamento",
  finalizado: "Finalizado",
  // financeiro
  pendente: "Pendente",
  pago: "Pago",
  // casos
  ativo: "Ativo",
  encerrado: "Encerrado",
  // risco (nível derivado — prefixado para não colidir com outros enums)
  risco_minimo: "Risco mínimo",
  risco_baixo: "Risco baixo",
  risco_moderado: "Risco moderado",
  risco_alto: "Risco alto",
};

/** Tom semântico → classe de badge existente no design system. */
const STATUS_TOM: Record<string, Tom> = {
  // concluídos / positivos → verde (--ok)
  realizada: "pos",
  assinado: "pos",
  assinada: "pos",
  finalizado: "pos",
  pago: "pos",
  // agendamentos → neutro-teal
  agendada: "info",
  // em progresso / a resolver → âmbar
  em_andamento: "warn",
  pendente: "warn",
  // não realizados → tijolo suave
  falta: "risk",
  cancelada: "risk",
  // rascunho → neutro
  rascunho: "neutral",
  // casos
  ativo: "pos",
  encerrado: "neutral",
  // risco
  risco_minimo: "pos",
  risco_baixo: "info",
  risco_moderado: "warn",
  risco_alto: "risk",
};

export const TOM_CLASSE: Record<Tom, string> = {
  pos: "badge-pos",
  info: "badge-info",
  warn: "badge-warn",
  risk: "badge-risk",
  neutral: "badge-neutral",
};

export function statusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return STATUS_LABEL[status] ?? humanizar(status);
}

export function statusTom(status: string | null | undefined): Tom {
  if (!status) return "neutral";
  return STATUS_TOM[status] ?? "neutral";
}

// --- Eventos da timeline (tipo_evento) ---
const EVENTO_LABEL: Record<string, string> = {
  sessao: "Sessão",
  evolucao: "Evolução",
  instrumento: "Instrumento",
  documento: "Documento",
  // formas verbais (enums longos, se vierem do backend)
  documento_criado: "Documento criado",
  instrumento_aplicado: "Instrumento aplicado",
  evolucao_criada: "Evolução criada",
  sessao_criada: "Sessão criada",
};

export function eventoLabel(tipo: string | null | undefined): string {
  if (!tipo) return "—";
  return EVENTO_LABEL[tipo] ?? humanizar(tipo);
}

// --- Modalidade de sessão ---
const MODALIDADE_LABEL: Record<string, string> = {
  presencial: "Presencial",
  online: "Online",
};

export function modalidadeLabel(m: string | null | undefined): string {
  if (!m) return "—";
  return MODALIDADE_LABEL[m] ?? humanizar(m);
}

// --- Tipo de instrumento (rótulo curto do catálogo; preserva siglas) ---
const INSTRUMENTO_LABEL: Record<string, string> = {
  gad7: "GAD-7",
  phq9: "PHQ-9",
  dass21: "DASS-21",
  gam: "GAM",
  maastricht: "Entrevista de Maastricht",
  ptmf: "PTMF",
  srq20: "SRQ-20",
  who5: "WHO-5",
  wrap: "WRAP",
};

export function instrumentoTipoLabel(tipo: string | null | undefined): string {
  if (!tipo) return "—";
  return INSTRUMENTO_LABEL[tipo] ?? tipo.toUpperCase();
}

// --- Forma de pagamento (financeiro) ---
const FORMA_LABEL: Record<string, string> = {
  pix: "Pix",
  dinheiro: "Dinheiro",
  cartao: "Cartão",
  transferencia: "Transferência",
  boleto: "Boleto",
};

export function formaPagamentoLabel(f: string | null | undefined): string {
  if (!f) return "—";
  return FORMA_LABEL[f] ?? humanizar(f);
}

// --- Tipo de documento (CFP) ---
const DOC_TIPO_LABEL: Record<string, string> = {
  declaracao: "Declaração",
  atestado: "Atestado",
  relatorio: "Relatório",
  laudo: "Laudo",
  encaminhamento: "Encaminhamento",
};

export function docTipoLabel(tipo: string | null | undefined): string {
  if (!tipo) return "—";
  return DOC_TIPO_LABEL[tipo] ?? humanizar(tipo);
}

// --- Tipo de encontro de grupo ---
const GRUPO_TIPO_LABEL: Record<string, string> = {
  grupo: "Grupo",
  oficina: "Oficina",
  assembleia: "Assembleia",
};

export function grupoTipoLabel(tipo: string | null | undefined): string {
  if (!tipo) return "—";
  return GRUPO_TIPO_LABEL[tipo] ?? humanizar(tipo);
}

// --- Nível de risco (C-SSRS) ---
const NIVEL_RISCO_LABEL: Record<string, string> = {
  minimo: "Mínimo",
  baixo: "Baixo",
  moderado: "Moderado",
  alto: "Alto",
};

/** Rótulo curto do nível ("Moderado"). Para badge, use status={`risco_${nivel}`}. */
export function nivelRiscoLabel(nivel: string | null | undefined): string {
  if (!nivel) return "—";
  return NIVEL_RISCO_LABEL[nivel] ?? humanizar(nivel);
}
