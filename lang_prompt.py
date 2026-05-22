import re
from collections import Counter


# Trigramas característicos de cada idioma
PERFIS_IDIOMA = {
    "pt": ["de ", " de", " a ", "que", " o ", " e ", "ão", "os ", "por", "não", "para", "uma", "com"],
    "en": ["the", " th", "he ", "in ", " of", "and", " an", "to ", "is ", "it ", "for"],
    "es": ["de ", " de", " la", "la ", "que", " en", " y ", " el", "con", "una", "ión"],
    "fr": ["de ", " de", " la", "le ", "les", " et", "des", "une", " à ", "nt "],
}

NOMES_IDIOMA = {
    "pt": "Português", "en": "English",
    "es": "Español",   "fr": "Français",
    "desconhecido": "Desconhecido",
}


def detetar_idioma(texto: str) -> tuple:
    """
    Deteta o idioma por análise de trigramas (sequências de 3 chars).
    Compara a frequência dos trigramas do texto com perfis de cada língua.
    A confiança é calculada pela margem entre o 1º e 2º classificado.
    Devolve (código_idioma, confiança 0-1).
    """
    if not texto or len(texto) < 50:
        return "desconhecido", 0.0

    amostra = re.sub(r"\s+", " ", texto.lower()[:3000])
    trigramas = Counter(amostra[i:i+3] for i in range(len(amostra) - 2))
    total = sum(trigramas.values()) or 1

    pontuacoes = {
        idioma: sum(trigramas.get(ng, 0) for ng in perfil) / total
        for idioma, perfil in PERFIS_IDIOMA.items()
    }

    melhor = max(pontuacoes, key=pontuacoes.get)
    valores = sorted(pontuacoes.values(), reverse=True)
    margem = valores[0] - valores[1] if len(valores) > 1 else valores[0]
    confianca = min(1.0, margem * 20)

    if confianca < 0.1:
        return "desconhecido", round(confianca, 3)
    return melhor, round(confianca, 3)


# Templates de prompts por idioma e tipo de normalização
TEMPLATES_PROMPT = {
    "pt": {
        "Normalização geral":  "Normaliza o seguinte texto em português, corrigindo erros ortográficos, melhorando a pontuação e a coesão textual. Mantém o significado original e devolve apenas o texto normalizado:\n\n{texto}",
        "Registo formal":      "Reformula o seguinte texto em português num registo formal e profissional, corrigindo erros. Devolve apenas o texto reformulado:\n\n{texto}",
        "Registo académico":   "Adapta o seguinte texto para um registo académico em português, corrigindo erros e melhorando a precisão terminológica. Devolve apenas o texto:\n\n{texto}",
        "Resumo":              "Resume o seguinte texto em português mantendo as ideias principais. Devolve apenas o resumo:\n\n{texto}",
        "Correção gramatical": "Corrige os erros gramaticais e ortográficos do seguinte texto em português sem alterar o estilo. Devolve apenas o texto corrigido:\n\n{texto}",
    },
    "en": {
        "Normalização geral":  "Normalize the following English text by fixing spelling, punctuation and coherence. Return only the normalized text:\n\n{texto}",
        "Registo formal":      "Rewrite the following text in a formal professional English register. Return only the rewritten text:\n\n{texto}",
        "Registo académico":   "Adapt the following text to an academic English register. Return only the text:\n\n{texto}",
        "Resumo":              "Summarize the following English text keeping the main ideas. Return only the summary:\n\n{texto}",
        "Correção gramatical": "Fix all grammar and spelling errors in the following English text without changing its style. Return only the corrected text:\n\n{texto}",
    },
    "es": {
        "Normalização geral":  "Normaliza el siguiente texto en español corrigiendo errores. Devuelve solo el texto normalizado:\n\n{texto}",
        "Registo formal":      "Reescribe el siguiente texto en español en un registro formal. Devuelve solo el texto:\n\n{texto}",
        "Registo académico":   "Adapta el siguiente texto a un registro académico en español. Devuelve solo el texto:\n\n{texto}",
        "Resumo":              "Resume el siguiente texto en español. Devuelve solo el resumen:\n\n{texto}",
        "Correção gramatical": "Corrige los errores del siguiente texto en español. Devuelve solo el texto:\n\n{texto}",
    },
}


def gerar_prompt(texto: str, idioma: str, tipo: str) -> str:
    """
    Gera o prompt completo para enviar à API.
    Seleciona o template pelo idioma detetado e pelo tipo de normalização.
    Se o idioma não tiver templates, usa inglês como fallback.
    """
    templates = TEMPLATES_PROMPT.get(idioma, TEMPLATES_PROMPT["en"])
    template = templates.get(tipo, list(templates.values())[0])
    return template.format(texto=texto)


# Lista dos tipos disponíveis para preencher o dropdown da interface
TIPOS_NORMALIZACAO = list(TEMPLATES_PROMPT["pt"].keys())