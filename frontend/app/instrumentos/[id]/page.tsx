"use client";
import { use } from "react";
import { InstrumentoWizard } from "@/components/InstrumentoWizard";

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <InstrumentoWizard respostaId={id} />;
}
