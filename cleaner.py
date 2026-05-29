"""
cleaner.py
Tarefa 2 – Pipeline de Limpeza e Pré-Processamento
8 etapas independentes, cada uma pode ser ativada ou desativada.
"""

import re
import unicodedata
from collections import Counter


def remover_artefactos(texto: str) -> str:
    """
    Remove caracteres de controlo, bytes inválidos e caracteres invisíveis.
    [\x00-\x08\x0b\x0c\x0e-\x1f\x7f] são códigos ASCII sem representação visual.
    \ufffd é o caractere de substituição que aparece em erros de encoding.
    Os restantes são caracteres de largura zero comuns em copy-paste da web.
    """
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)
    texto = texto.replace("\ufffd", "")
    texto = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", texto)
    return texto


def normalizar_unicode(texto: str) -> str:
    """
    Normaliza para forma NFC — garante consistência entre sistemas
    operativos (Mac vs Windows usam representações Unicode diferentes).
    """
    return unicodedata.normalize("NFC", texto)


def corrigir_quebras_de_linha(texto: str) -> str:
    """
    Converte todas as variantes de quebra de linha para \n uniforme.
    Windows usa \r\n, Mac antigo usava \r.
    O \f (nova página) é convertido em duas linhas em branco.
    """
    texto = texto.replace("\r\n", "\n")
    texto = texto.replace("\r", "\n")
    texto = texto.replace("\f", "\n\n")
    return texto


def remover_numeros_pagina(texto: str) -> str:
    """
    Remove linhas que sejam apenas números de página.
    Deteta padrões como: "3", "- 3 -", "Page 3", "Página 3".
    re.fullmatch exige que o padrão ocupe a linha toda.
    """
    linhas = texto.split("\n")
    resultado = []
    for linha in linhas:
        s = linha.strip()
        if re.fullmatch(r"[-–\s]*\d+[-–\s]*", s):
            continue
        if re.match(r"^(page|página|pág\.?)\s*\d+", s, re.IGNORECASE):
            continue
        resultado.append(linha)
    return "\n".join(resultado)


def remover_cabecalhos_rodapes(texto: str) -> str:
    """
    Deteta e remove cabeçalhos e rodapés repetidos.
    Se uma linha curta (< 120 chars) aparecer em 40%+ das páginas,
    é provavelmente um cabeçalho ou rodapé — é removida.
    Usa Counter para contar a frequência de cada linha.
    """
    linhas = texto.split("\n")
    n_paginas = texto.count("\f") + 1
    threshold = max(2, n_paginas * 0.4)
    freq = Counter(l.strip() for l in linhas if l.strip())
    return "\n".join(
        l for l in linhas
        if not (freq.get(l.strip(), 0) >= threshold and len(l.strip()) < 120)
    )


def reconstruir_paragrafos(texto: str) -> str:
    """
    Re-une linhas partidas a meio de frase — problema comum em PDFs.
    Junta a linha atual com a seguinte se:
    - a linha tem mais de 40 chars (não é um título curto)
    - não termina em pontuação final (. ! ? : ; - —)
    - a linha seguinte não tem indentação (não é novo parágrafo)
    """
    linhas = texto.split("\n")
    resultado = []
    i = 0
    while i < len(linhas):
        atual = linhas[i].rstrip()
        proxima = linhas[i + 1].strip() if i + 1 < len(linhas) else ""
        if (atual and proxima and len(atual) > 40
                and not atual.endswith((".", "!", "?", ":", ";", "-", "—"))
                and not re.match(r"^\s{2,}", linhas[i + 1])):
            resultado.append(atual + " " + proxima)
            i += 2
        else:
            resultado.append(atual)
            i += 1
    return "\n".join(resultado)


def normalizar_pontuacao(texto: str) -> str:
    """
    Converte caracteres tipográficos para ASCII simples.
    Processadores de texto usam aspas "curvas", travessões longos, etc.
    Os modelos de linguagem funcionam melhor com texto ASCII limpo.
    """
    substituicoes = {
        "\u2018": "'", "\u2019": "'",   # aspas simples curvas
        "\u201c": '"', "\u201d": '"',   # aspas duplas curvas
        "\u2013": "-", "\u2014": "-",   # en-dash e em-dash
        "\u2026": "...",                 # reticências
        "\u2022": "-",                   # bullet point
    }
    for orig, repl in substituicoes.items():
        texto = texto.replace(orig, repl)
    return texto


def normalizar_espacos(texto: str) -> str:
    """
    Colapsa múltiplos espaços e linhas em branco em excesso.
    [ \t]+ → um espaço; \n{3,} → duas linhas em branco.
    Remove também espaços desnecessários no final de cada linha.
    """
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = "\n".join(l.rstrip() for l in texto.split("\n"))
    return texto.strip()


# Lista ordenada das etapas — a ordem importa
ETAPAS_PIPELINE = [
    ("Remoção de artefactos",        remover_artefactos),
    ("Normalização Unicode",          normalizar_unicode),
    ("Correção de quebras de linha",  corrigir_quebras_de_linha),
    ("Remoção de números de página",  remover_numeros_pagina),
    ("Deteção cabeçalhos/rodapés",    remover_cabecalhos_rodapes),
    ("Reconstrução de parágrafos",    reconstruir_paragrafos),
    ("Normalização de pontuação",     normalizar_pontuacao),
    ("Normalização de espaços",       normalizar_espacos),
]


def correr_pipeline(texto: str, etapas_ativas: list) -> tuple:
    """
    Executa a pipeline aplicando as etapas ativas pela ordem da lista.
    Guarda estatísticas de cada etapa executada.
    Devolve (texto_limpo, lista_de_estatísticas).
    """
    estatisticas = []
    texto_atual = texto

    for (nome, funcao), ativo in zip(ETAPAS_PIPELINE, etapas_ativas):
        if not ativo:
            continue
        antes = texto_atual
        texto_atual = funcao(texto_atual)
        estatisticas.append({
            "etapa":           nome,
            "chars_antes":     len(antes),
            "chars_depois":    len(texto_atual),
            "chars_removidos": len(antes) - len(texto_atual),
            "linhas_antes":    antes.count("\n") + 1,
            "linhas_depois":   texto_atual.count("\n") + 1,
        })

    return texto_atual, estatisticas