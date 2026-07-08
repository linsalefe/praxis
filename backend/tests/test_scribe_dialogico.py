"""Template de evolução dialógica (Diálogo Aberto, Onda 1.4).

Testa a montagem pura da diretriz de abordagem — sem chamar o LLM.
"""
from app.scribe.structurer import montar_diretriz


def test_dialogo_aberto_usa_template_dialogico():
    d = montar_diretriz("dialogo_aberto")
    assert "Diálogo Aberto" in d
    # princípios dialógicos presentes no template
    for termo in ("polifonia", "rede", "incerteza", "compartilhada"):
        assert termo in d.lower()


def test_outras_abordagens_recebem_frase_de_tom():
    d = montar_diretriz("gam")
    assert "GAM" in d
    assert "polifonia" not in d.lower()


def test_sem_abordagem_sem_diretriz():
    assert montar_diretriz(None) == ""
    assert montar_diretriz("") == ""
