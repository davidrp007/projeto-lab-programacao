"""
chunker.py
Tarefa 3 – Segmentação do Texto em Chunks
4 estratégias disponíveis para dividir o texto em blocos adequados ao SLM.
"""

import re


def chunk_tamanho_fixo(texto: str, tamanho: int = 512, overlap: int = 50) -> list:
    """
    Divide o texto em blocos de tamanho fixo (em caracteres).
    O overlap é a sobreposição entre chunks — os últimos N chars
    de um chunk são os primeiros do próximo, para não perder contexto.
    Tenta cortar em espaços para não partir palavras a meio.
    """
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fim = min(inicio + tamanho, len(texto))
        if fim < len(texto):
            # tenta cortar no último espaço antes do limite
            corte = texto.rfind(" ", inicio, fim)
            if corte > inicio:
                fim = corte
        bloco = texto[inicio:fim].strip()
        if bloco:
            chunks.append(bloco)
        inicio = fim - overlap if fim < len(texto) else fim
    return chunks


def chunk_por_paragrafo(texto: str, max_chars: int = 1024) -> list:
    """
    Divide por parágrafos (separados por linha em branco).
    Agrupa parágrafos consecutivos até atingir max_chars.
    Mantém coerência semântica — cada chunk é um conjunto de parágrafos completos.
    """
    chunks, buffer = [], ""
    for para in re.split(r"\n{2,}", texto):
        para = para.strip()
        if not para:
            continue
        if len(buffer) + len(para) + 2 <= max_chars:
            buffer = (buffer + "\n\n" + para).strip() if buffer else para
        else:
            if buffer:
                chunks.append(buffer)
            buffer = para
    if buffer:
        chunks.append(buffer)
    return chunks


def chunk_por_frase(texto: str, max_chars: int = 512) -> list:
    """
    Divide por frases (terminadas em . ! ?).
    O lookbehind (?<=[.!?]) e lookahead (?=[A-Z...]) garantem
    que só divide em fronteiras de frase reais.
    """
    chunks, buffer = [], ""
    frases = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÀÂÊÔÃÕ\"])", texto)
    for frase in frases:
        frase = frase.strip()
        if not frase:
            continue
        if len(buffer) + len(frase) + 1 <= max_chars:
            buffer = (buffer + " " + frase).strip() if buffer else frase
        else:
            if buffer:
                chunks.append(buffer)
            buffer = frase
    if buffer:
        chunks.append(buffer)
    return chunks


# Dicionário com todas as estratégias disponíveis
ESTRATEGIAS_CHUNKING = {
    "Tamanho fixo (512 chars)":  lambda t: chunk_tamanho_fixo(t, 512, 50),
    "Tamanho fixo (1024 chars)": lambda t: chunk_tamanho_fixo(t, 1024, 100),
    "Por parágrafo":             lambda t: chunk_por_paragrafo(t, 1024),
    "Por frase":                 lambda t: chunk_por_frase(t, 512),
}


def segmentar_texto(texto: str, estrategia: str) -> list:
    """Ponto de entrada do chunking — aplica a estratégia escolhida."""
    fn = ESTRATEGIAS_CHUNKING.get(estrategia)
    if not fn:
        raise ValueError(f"Estratégia desconhecida: {estrategia}")
    return fn(texto)