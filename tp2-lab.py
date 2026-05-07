import io
import os
import re
import json
import time
import html as html_module
import datetime
import unicodedata
import urllib.request
import threading
from collections import Counter
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# TAREFA 1 – EXTRAÇÃO DE TEXTO MULTI-FORMATO

def extrair_txt(conteudo: bytes) -> str:
    try:
        import chardet
        enc = chardet.detect(conteudo).get("encoding") or "utf-8"
    except ImportError:
        enc = "utf-8"
    try:
        return conteudo.decode(enc)
    except Exception:
        return conteudo.decode("utf-8", errors="replace")


def extrair_pdf(conteudo: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("Instala pdfplumber:  pip install pdfplumber")
    paginas = []
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text(x_tolerance=2, y_tolerance=2)
            if texto:
                paginas.append(texto)
            paginas.append("\f")
    return "\n".join(paginas)


def extrair_docx(conteudo: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("Instala python-docx:  pip install python-docx")
    doc = Document(io.BytesIO(conteudo))
    linhas = [p.text for p in doc.paragraphs]
    for tabela in doc.tables:
        for linha in tabela.rows:
            linhas.append("\t".join(c.text for c in linha.cells))
    return "\n".join(linhas)


def extrair_texto(caminho: str) -> str:
    if not os.path.isfile(caminho):
        raise FileNotFoundError(f"Ficheiro não encontrado: {caminho}")
    with open(caminho, "rb") as f:
        conteudo = f.read()
    nome = caminho.lower()
    if nome.endswith(".pdf"):
        return extrair_pdf(conteudo)
    elif nome.endswith(".docx"):
        return extrair_docx(conteudo)
    elif nome.endswith(".txt"):
        return extrair_txt(conteudo)
    else:
        raise ValueError(f"Formato não suportado. Use PDF, DOCX ou TXT.")

# TAREFA 2 – PIPELINE DE LIMPEZA

def remover_artefactos(texto: str) -> str:
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)
    texto = texto.replace("\ufffd", "")
    texto = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", texto)
    return texto

def normalizar_unicode(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)

def corrigir_quebras_de_linha(texto: str) -> str:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = texto.replace("\f", "\n\n")
    return texto

def remover_numeros_pagina(texto: str) -> str:
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
    linhas = texto.split("\n")
    n_paginas = texto.count("\f") + 1
    threshold = max(2, n_paginas * 0.4)
    freq = Counter(l.strip() for l in linhas if l.strip())
    return "\n".join(
        l for l in linhas
        if not (freq.get(l.strip(), 0) >= threshold and len(l.strip()) < 120)
    )

def reconstruir_paragrafos(texto: str) -> str:
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
    for orig, repl in {"\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',
                       "\u2013":"-","\u2014":"-","\u2026":"...","\u2022":"-"}.items():
        texto = texto.replace(orig, repl)
    return texto

def normalizar_espacos(texto: str) -> str:
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = "\n".join(l.rstrip() for l in texto.split("\n"))
    return texto.strip()


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
    estatisticas = []
    texto_atual = texto
    for (nome, funcao), ativo in zip(ETAPAS_PIPELINE, etapas_ativas):
        if not ativo:
            continue
        antes = texto_atual
        texto_atual = funcao(texto_atual)
        estatisticas.append({
            "etapa": nome,
            "chars_antes": len(antes),
            "chars_depois": len(texto_atual),
            "chars_removidos": len(antes) - len(texto_atual),
            "linhas_antes": antes.count("\n") + 1,
            "linhas_depois": texto_atual.count("\n") + 1,
        })
    return texto_atual, estatisticas

# TAREFA 3 – PREPARAÇÃO DO INPUT

PERFIS_IDIOMA = {
    "pt": ["de ", " de", " a ", "que", " o ", " e ", "ão", "os ", "por", "não", "para", "uma", "com"],
    "en": ["the", " th", "he ", "in ", " of", "and", " an", "to ", "is ", "it ", "for"],
    "es": ["de ", " de", " la", "la ", "que", " en", " y ", " el", "con", "una", "ión"],
    "fr": ["de ", " de", " la", "le ", "les", " et", "des", "une", " à ", "nt "],
}
NOMES_IDIOMA = {"pt": "Português", "en": "English", "es": "Español",
                "fr": "Français", "desconhecido": "Desconhecido"}

def detetar_idioma(texto: str) -> tuple:
    if not texto or len(texto) < 50:
        return "desconhecido", 0.0
    amostra = re.sub(r"\s+", " ", texto.lower()[:3000])
    trigramas = Counter(amostra[i:i+3] for i in range(len(amostra) - 2))
    total = sum(trigramas.values()) or 1
    pontuacoes = {lang: sum(trigramas.get(ng, 0) for ng in perfil) / total
                  for lang, perfil in PERFIS_IDIOMA.items()}
    melhor = max(pontuacoes, key=pontuacoes.get)
    valores = sorted(pontuacoes.values(), reverse=True)
    margem = valores[0] - valores[1] if len(valores) > 1 else valores[0]
    confianca = min(1.0, margem * 20)
    return (melhor, round(confianca, 3)) if confianca >= 0.1 else ("desconhecido", round(confianca, 3))


def chunk_tamanho_fixo(texto: str, tamanho: int = 512, overlap: int = 50) -> list:
    chunks, inicio = [], 0
    while inicio < len(texto):
        fim = min(inicio + tamanho, len(texto))
        if fim < len(texto):
            corte = texto.rfind(" ", inicio, fim)
            if corte > inicio:
                fim = corte
        bloco = texto[inicio:fim].strip()
        if bloco:
            chunks.append(bloco)
        inicio = fim - overlap if fim < len(texto) else fim
    return chunks

def chunk_por_paragrafo(texto: str, max_chars: int = 1024) -> list:
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
    chunks, buffer = [], ""
    for frase in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÀÂÊÔÃÕ\"])", texto):
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


ESTRATEGIAS_CHUNKING = {
    "Tamanho fixo (512 chars)":  lambda t: chunk_tamanho_fixo(t, 512, 50),
    "Tamanho fixo (1024 chars)": lambda t: chunk_tamanho_fixo(t, 1024, 100),
    "Por parágrafo":             lambda t: chunk_por_paragrafo(t, 1024),
    "Por frase":                 lambda t: chunk_por_frase(t, 512),
}

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
    templates = TEMPLATES_PROMPT.get(idioma, TEMPLATES_PROMPT["en"])
    template = templates.get(tipo, list(templates.values())[0])
    return template.format(texto=texto)

# TAREFA 4 – API SLM

API_URL   = "https://reality.utad.net/slm"
API_MODEL = "llama-3.2-1b-instruct"

def chamar_api(prompt: str, timeout: int = 60) -> dict:
    payload = {"model": API_MODEL, "messages": [{"role": "user", "content": prompt}]}
    corpo = json.dumps(payload).encode("utf-8")
    pedido = urllib.request.Request(API_URL, data=corpo, method="POST",
                                    headers={"Content-Type": "application/json"})
    inicio = time.time()
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resp:
            tempo = round(time.time() - inicio, 2)
            dados = json.loads(resp.read().decode("utf-8"))
        conteudo = ""
        if "choices" in dados and dados["choices"]:
            conteudo = dados["choices"][0].get("message", {}).get("content", "")
        elif "message" in dados:
            conteudo = dados["message"].get("content", "")
        uso = dados.get("usage", {})
        return {"sucesso": True, "conteudo": conteudo,
                "tokens_prompt": uso.get("prompt_tokens", 0),
                "tokens_resposta": uso.get("completion_tokens", 0),
                "tempo": tempo, "erro": None}
    except Exception as e:
        return {"sucesso": False, "conteudo": "", "tokens_prompt": 0,
                "tokens_resposta": 0, "tempo": round(time.time()-inicio, 2), "erro": str(e)}

# TAREFA 5 – RELATÓRIO HTML

def gerar_relatorio_html(nome_ficheiro, texto_bruto, texto_limpo,
                          estatisticas, idioma, confianca, estrategia,
                          tipo_norm, resultados_api=None, texto_final="") -> str:
    def _e(t): return html_module.escape(str(t))
    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_rem = sum(e["chars_removidos"] for e in estatisticas)
    pct = round(100 * total_rem / max(len(texto_bruto), 1), 1)

    linhas_etapas = ""
    for e in estatisticas:
        cor = "#4ade80" if e["chars_removidos"] >= 0 else "#f87171"
        linhas_etapas += (f"<tr><td>{_e(e['etapa'])}</td><td>{e['linhas_antes']:,}</td>"
                          f"<td>{e['linhas_depois']:,}</td>"
                          f"<td style='color:{cor};font-weight:600'>{e['chars_removidos']:+,}</td></tr>")

    secao_api = ""
    if resultados_api:
        ok = [r for r in resultados_api if r.get("sucesso")]
        avg = round(sum(r["tempo"] for r in resultados_api) / len(resultados_api), 2)
        toks = sum(r.get("tokens_resposta", 0) for r in resultados_api)
        amostra = _e(texto_final[:2000]) + ("..." if len(texto_final) > 2000 else "")
        secao_api = f"""<section class="s"><h2>4. Resultados da API SLM</h2>
        <div class="grid">
          <div class="card"><span class="val">{len(resultados_api)}</span><span class="lbl">Chunks enviados</span></div>
          <div class="card"><span class="val">{len(ok)}</span><span class="lbl">Com sucesso</span></div>
          <div class="card"><span class="val">{avg}s</span><span class="lbl">Tempo médio</span></div>
          <div class="card"><span class="val">{toks:,}</span><span class="lbl">Tokens gerados</span></div>
        </div>
        <h3>Texto normalizado (amostra)</h3><pre class="box">{amostra}</pre></section>"""

    return f"""<!DOCTYPE html><html lang="pt"><head><meta charset="UTF-8">
<title>TextNorm – Relatório</title><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Georgia,serif;background:#f8f7f4;color:#1a1a1a;line-height:1.7}}
.header{{background:#0d0d0d;color:#f0ede8;padding:2rem 3rem;border-bottom:3px solid #e85d26}}
.header h1{{font-family:'Courier New',monospace;font-size:1.6rem}}
.sub{{color:#888;font-style:italic;margin-top:.3rem}}
.meta{{margin-top:.8rem;font-size:.8rem;color:#666;font-family:monospace}}
.wrap{{max-width:900px;margin:0 auto;padding:2rem 1.5rem}}
.s{{background:#fff;border-radius:8px;padding:1.8rem;margin-bottom:1.2rem;border:1px solid #e8e4de}}
h2{{font-family:'Courier New',monospace;font-size:.95rem;color:#e85d26;text-transform:uppercase;
    letter-spacing:1px;border-bottom:1px solid #e8e4de;padding-bottom:.5rem;margin-bottom:1rem}}
h3{{font-size:.88rem;color:#555;margin:1rem 0 .3rem;font-family:'Courier New',monospace}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:.7rem;margin-bottom:1rem}}
.card{{background:#f8f7f4;border:1px solid #e8e4de;border-radius:6px;padding:.7rem;text-align:center}}
.val{{display:block;font-size:1.3rem;font-weight:700;font-family:'Courier New',monospace;color:#e85d26}}
.lbl{{display:block;font-size:.68rem;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-top:.2rem}}
table{{width:100%;border-collapse:collapse;font-size:.83rem}}
th{{background:#f0ede8;padding:.5rem .8rem;text-align:left;font-family:'Courier New',monospace;
    font-size:.7rem;text-transform:uppercase;color:#666;border-bottom:2px solid #e8e4de}}
td{{padding:.5rem .8rem;border-bottom:1px solid #f0ede8}}
.box{{background:#f8f7f4;border:1px solid #e8e4de;border-radius:6px;padding:.9rem;
      font-family:'Courier New',monospace;font-size:.77rem;white-space:pre-wrap;
      word-break:break-word;max-height:250px;overflow-y:auto}}
.footer{{text-align:center;color:#aaa;font-size:.72rem;margin-top:2rem;font-family:monospace}}
</style></head><body>
<div class="header">
  <h1>⚙ TextNorm Pipeline — Relatório</h1>
  <div class="sub">Normalização de Texto com SLMs · UTAD 2025/26</div>
  <div class="meta">Ficheiro: {_e(nome_ficheiro)} &nbsp;|&nbsp; Gerado: {agora} &nbsp;|&nbsp; Modelo: {API_MODEL}</div>
</div>
<div class="wrap">
<section class="s"><h2>1. Visão Geral</h2>
  <div class="grid">
    <div class="card"><span class="val">{len(texto_bruto):,}</span><span class="lbl">Chars originais</span></div>
    <div class="card"><span class="val">{len(texto_limpo):,}</span><span class="lbl">Chars limpos</span></div>
    <div class="card"><span class="val">-{pct}%</span><span class="lbl">Redução</span></div>
    <div class="card"><span class="val">{_e(idioma).upper()}</span><span class="lbl">Idioma ({int(confianca*100)}%)</span></div>
    <div class="card"><span class="val">{len(estatisticas)}</span><span class="lbl">Etapas</span></div>
  </div>
  <table>
    <tr><th>Parâmetro</th><th>Valor</th></tr>
    <tr><td>Estratégia de chunking</td><td>{_e(estrategia)}</td></tr>
    <tr><td>Tipo de normalização</td><td>{_e(tipo_norm)}</td></tr>
    <tr><td>Idioma detetado</td><td>{_e(NOMES_IDIOMA.get(idioma, idioma))} ({int(confianca*100)}% confiança)</td></tr>
    <tr><td>Total caracteres removidos</td><td>{total_rem:,}</td></tr>
  </table>
</section>
<section class="s"><h2>2. Etapas da Pipeline</h2>
  <table><thead><tr><th>Etapa</th><th>Linhas antes</th><th>Linhas depois</th><th>Δ Chars</th></tr></thead>
  <tbody>{linhas_etapas}</tbody></table>
</section>
<section class="s"><h2>3. Texto Antes / Depois</h2>
  <h3>Texto original (primeiros 1500 chars)</h3>
  <pre class="box">{_e(texto_bruto[:1500])}{'...' if len(texto_bruto)>1500 else ''}</pre>
  <h3>Texto após limpeza (primeiros 1500 chars)</h3>
  <pre class="box">{_e(texto_limpo[:1500])}{'...' if len(texto_limpo)>1500 else ''}</pre>
</section>
{secao_api}
<div class="footer">TextNorm Pipeline · UTAD – Laboratório de Programação · {datetime.datetime.now().year}</div>
</div></body></html>"""

# INTERFACE GRÁFICA

# Cores e fontes
COR_BG       = "#1a1a1a"
COR_PANEL    = "#242424"
COR_BORDA    = "#333333"
COR_LARANJA  = "#E85D26"
COR_TEXTO    = "#F0EDE8"
COR_TEXTO2   = "#999999"
COR_VERDE    = "#4ade80"
COR_VERMELHO = "#f87171"
FONTE_MONO   = ("Courier New", 10)
FONTE_TITULO = ("Courier New", 11, "bold")
FONTE_LABEL  = ("Segoe UI", 10)
FONTE_BTN    = ("Courier New", 10, "bold")


class TextNormApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚙ TextNorm Pipeline — UTAD TP2")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(bg=COR_BG)

        # Estado
        self.texto_bruto   = ""
        self.texto_limpo   = ""
        self.nome_ficheiro = ""
        self.idioma        = "desconhecido"
        self.confianca_id  = 0.0
        self.estatisticas  = []
        self.chunks        = []
        self.prompts       = []
        self.resultados_api= []
        self.texto_final   = ""
        self.etapas_vars   = []
        self.estrategia_var= tk.StringVar(value="Por parágrafo")
        self.tipo_norm_var = tk.StringVar(value="Normalização geral")
        self.max_chunks_var= tk.IntVar(value=3)

        self._build_ui()

    # Construção da UI

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#0d0d0d", height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="⚙  TextNorm Pipeline",
                 font=("Courier New", 14, "bold"), bg="#0d0d0d", fg=COR_TEXTO).pack(side="left", padx=20, pady=10)
        tk.Label(header, text="UTAD · Laboratório de Programação · TP2 · 2025/26",
                 font=("Courier New", 9), bg="#0d0d0d", fg=COR_TEXTO2).pack(side="left", padx=5, pady=10)
        # barra laranja
        tk.Frame(self, bg=COR_LARANJA, height=3).pack(fill="x")

        # Notebook de separadores
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background=COR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COR_PANEL, foreground=COR_TEXTO2,
                        font=FONTE_TITULO, padding=[16, 8], borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", COR_LARANJA)],
                  foreground=[("selected", "white")])
        style.configure("TFrame", background=COR_BG)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab1 = ttk.Frame(self.nb)
        self.tab2 = ttk.Frame(self.nb)
        self.tab3 = ttk.Frame(self.nb)
        self.tab4 = ttk.Frame(self.nb)
        self.tab5 = ttk.Frame(self.nb)

        self.nb.add(self.tab1, text="  1 · Extração  ")
        self.nb.add(self.tab2, text="  2 · Limpeza  ")
        self.nb.add(self.tab3, text="  3 · Chunking & Prompt  ")
        self.nb.add(self.tab4, text="  4 · API SLM  ")
        self.nb.add(self.tab5, text="  5 · Relatório  ")

        self._build_tab1()
        self._build_tab2()
        self._build_tab3()
        self._build_tab4()
        self._build_tab5()

        # Barra de estado
        self.status_var = tk.StringVar(value="Pronto. Carrega um ficheiro para começar.")
        barra = tk.Frame(self, bg="#0d0d0d", height=28)
        barra.pack(fill="x", side="bottom")
        tk.Label(barra, textvariable=self.status_var,
                 font=("Courier New", 9), bg="#0d0d0d", fg=COR_TEXTO2,
                 anchor="w").pack(fill="x", padx=12, pady=4)

    # Helpers de widgets 

    def _frame(self, parent, **kw):
        return tk.Frame(parent, bg=COR_BG, **kw)

    def _panel(self, parent, titulo="", **kw):
        outer = tk.Frame(parent, bg=COR_PANEL, bd=0, highlightthickness=1,
                         highlightbackground=COR_BORDA, **kw)
        if titulo:
            tk.Label(outer, text=titulo.upper(), font=("Courier New", 8, "bold"),
                     bg=COR_PANEL, fg=COR_LARANJA).pack(anchor="w", padx=10, pady=(8,2))
        return outer

    def _label(self, parent, texto, **kw):
        return tk.Label(parent, text=texto, bg=kw.pop("bg", COR_BG),
                        fg=kw.pop("fg", COR_TEXTO), font=FONTE_LABEL, **kw)

    def _btn(self, parent, texto, comando, cor=COR_LARANJA, **kw):
        return tk.Button(parent, text=texto, command=comando,
                         bg=cor, fg="white", font=FONTE_BTN,
                         relief="flat", cursor="hand2",
                         activebackground="#c94d1e", activeforeground="white",
                         padx=14, pady=6, **kw)

    def _textarea(self, parent, height=10, **kw):
        area = scrolledtext.ScrolledText(
            parent, height=height, font=FONTE_MONO,
            bg="#0f0f0f", fg=COR_TEXTO, insertbackground=COR_TEXTO,
            relief="flat", wrap="word", bd=0,
            selectbackground=COR_LARANJA, **kw)
        return area

    def _status(self, msg):
        self.status_var.set(msg)
        self.update_idletasks()

    def _stat_card(self, parent, titulo, valor):
        f = tk.Frame(parent, bg=COR_PANEL, bd=0, highlightthickness=1,
                     highlightbackground=COR_BORDA)
        f.pack(side="left", padx=4, pady=4, fill="x", expand=True)
        tk.Label(f, text=str(valor), font=("Courier New", 14, "bold"),
                 bg=COR_PANEL, fg=COR_LARANJA).pack(pady=(8,0))
        tk.Label(f, text=titulo.upper(), font=("Courier New", 7),
                 bg=COR_PANEL, fg=COR_TEXTO2).pack(pady=(0,8))
        return f

    # Extração 

    def _build_tab1(self):
        p = self._frame(self.tab1)
        p.pack(fill="both", expand=True, padx=16, pady=14)

        self._label(p, "Carrega um ficheiro PDF, DOCX ou TXT. O texto é apresentado em bruto, sem qualquer transformação.",
                    fg=COR_TEXTO2).pack(anchor="w", pady=(0,10))

        # Botão de upload
        top = self._frame(p)
        top.pack(fill="x")
        self._btn(top, "📂  Abrir Ficheiro", self._abrir_ficheiro).pack(side="left")
        self.label_ficheiro = tk.Label(top, text="Nenhum ficheiro selecionado",
                                       font=("Courier New", 9), bg=COR_BG, fg=COR_TEXTO2)
        self.label_ficheiro.pack(side="left", padx=14)

        # Cards de estatísticas
        self.stats_frame1 = self._frame(p)
        self.stats_frame1.pack(fill="x", pady=(10,6))

        # Idioma
        self.label_idioma = tk.Label(p, text="", font=("Courier New", 9),
                                     bg=COR_BG, fg=COR_VERDE)
        self.label_idioma.pack(anchor="w", pady=(0,6))

        # Área de texto
        self._label(p, "Texto extraído (bruto):").pack(anchor="w")
        self.area_bruto = self._textarea(p, height=22)
        self.area_bruto.pack(fill="both", expand=True, pady=(4,0))

    def _abrir_ficheiro(self):
        caminho = filedialog.askopenfilename(
            title="Seleciona um ficheiro",
            filetypes=[("Documentos", "*.pdf *.docx *.txt"), ("Todos", "*.*")]
        )
        if not caminho:
            return
        self._status(f"A extrair {os.path.basename(caminho)}...")
        try:
            texto = extrair_texto(caminho)
            self.texto_bruto   = texto
            self.nome_ficheiro = os.path.basename(caminho)
            self.texto_limpo   = ""
            self.estatisticas  = []
            self.chunks = []; self.prompts = []
            self.resultados_api = []; self.texto_final = ""

            idioma, conf = detetar_idioma(texto)
            self.idioma = idioma; self.confianca_id = conf

            # Atualizar UI
            self.label_ficheiro.config(text=self.nome_ficheiro)
            self._atualizar_stats1(texto)
            self.label_idioma.config(
                text=f"🌐  Idioma detetado: {NOMES_IDIOMA.get(idioma, idioma)}  (confiança {int(conf*100)}%)")
            self.area_bruto.config(state="normal")
            self.area_bruto.delete("1.0", "end")
            self.area_bruto.insert("1.0", texto)
            self.area_bruto.config(state="disabled")
            self._status(f"✓ Ficheiro carregado — {len(texto):,} caracteres")
        except Exception as e:
            messagebox.showerror("Erro na extração", str(e))
            self._status("Erro na extração.")

    def _atualizar_stats1(self, texto):
        for w in self.stats_frame1.winfo_children():
            w.destroy()
        self._stat_card(self.stats_frame1, "Caracteres",  f"{len(texto):,}")
        self._stat_card(self.stats_frame1, "Palavras",    f"{len(texto.split()):,}")
        self._stat_card(self.stats_frame1, "Linhas",      f"{texto.count(chr(10))+1:,}")
        self._stat_card(self.stats_frame1, "Tamanho",     f"{len(texto.encode())/1024:.1f} KB")

    # Limpeza 

    def _build_tab2(self):
        p = self._frame(self.tab2)
        p.pack(fill="both", expand=True, padx=16, pady=14)

        # Checkboxes das etapas
        painel = self._panel(p, "Etapas da pipeline")
        painel.pack(fill="x", pady=(0,10))
        grid = tk.Frame(painel, bg=COR_PANEL)
        grid.pack(fill="x", padx=10, pady=(0,10))
        self.etapas_vars = []
        for i, (nome, _) in enumerate(ETAPAS_PIPELINE):
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(grid, text=nome, variable=var,
                                bg=COR_PANEL, fg=COR_TEXTO, selectcolor=COR_BG,
                                activebackground=COR_PANEL, activeforeground=COR_TEXTO,
                                font=FONTE_LABEL, cursor="hand2")
            cb.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=2)
            self.etapas_vars.append(var)

        self._btn(p, "▶  Executar Pipeline", self._correr_pipeline).pack(anchor="w", pady=(0,10))

        # Estatísticas por etapa
        self.stats_frame2 = self._frame(p)
        self.stats_frame2.pack(fill="x", pady=(0,6))

        # Antes / Depois
        colunas = self._frame(p)
        colunas.pack(fill="both", expand=True)

        col_e = self._frame(colunas)
        col_e.pack(side="left", fill="both", expand=True, padx=(0,6))
        self._label(col_e, "Antes da limpeza:").pack(anchor="w")
        self.area_antes = self._textarea(col_e, height=16)
        self.area_antes.pack(fill="both", expand=True, pady=(4,0))

        col_d = self._frame(colunas)
        col_d.pack(side="left", fill="both", expand=True)
        self._label(col_d, "Depois da limpeza:").pack(anchor="w")
        self.area_depois = self._textarea(col_d, height=16)
        self.area_depois.pack(fill="both", expand=True, pady=(4,0))

    def _correr_pipeline(self):
        if not self.texto_bruto:
            messagebox.showwarning("Aviso", "Extrai primeiro um ficheiro no separador 1.")
            return
        ativas = [v.get() for v in self.etapas_vars]
        self._status("A processar pipeline...")
        try:
            limpo, stats = correr_pipeline(self.texto_bruto, ativas)
            self.texto_limpo  = limpo
            self.estatisticas = stats
            self.chunks = []; self.prompts = []
            self.resultados_api = []; self.texto_final = ""

            # Stats cards
            for w in self.stats_frame2.winfo_children():
                w.destroy()
            total_rem = sum(e["chars_removidos"] for e in stats)
            pct = round(100 * total_rem / max(len(self.texto_bruto), 1), 1)
            self._stat_card(self.stats_frame2, "Etapas",      len(stats))
            self._stat_card(self.stats_frame2, "Chars removidos", f"{total_rem:,}")
            self._stat_card(self.stats_frame2, "Redução",     f"{pct}%")
            self._stat_card(self.stats_frame2, "Chars finais", f"{len(limpo):,}")

            # Áreas de texto
            for area, conteudo in [(self.area_antes, self.texto_bruto),
                                   (self.area_depois, limpo)]:
                area.config(state="normal")
                area.delete("1.0", "end")
                area.insert("1.0", conteudo)
                area.config(state="disabled")

            self._status(f"✓ Pipeline concluída — {len(stats)} etapas | -{pct}% de redução")
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            self._status("Erro na pipeline.")

    # Chunking & Prompt 

    def _build_tab3(self):
        p = self._frame(self.tab3)
        p.pack(fill="both", expand=True, padx=16, pady=14)

        # Opções
        opcoes = self._panel(p, "Configuração")
        opcoes.pack(fill="x", pady=(0,10))
        grid = tk.Frame(opcoes, bg=COR_PANEL)
        grid.pack(fill="x", padx=10, pady=(0,10))

        self._label(grid, "Estratégia de chunking:", bg=COR_PANEL).grid(row=0, column=0, sticky="w", pady=4, padx=4)
        ttk.Combobox(grid, textvariable=self.estrategia_var,
                     values=list(ESTRATEGIAS_CHUNKING.keys()),
                     state="readonly", width=28).grid(row=0, column=1, sticky="w", pady=4, padx=4)

        self._label(grid, "Tipo de normalização:", bg=COR_PANEL).grid(row=1, column=0, sticky="w", pady=4, padx=4)
        tipos = list(TEMPLATES_PROMPT["pt"].keys())
        ttk.Combobox(grid, textvariable=self.tipo_norm_var,
                     values=tipos, state="readonly", width=28).grid(row=1, column=1, sticky="w", pady=4, padx=4)

        self._btn(p, "✂️  Segmentar & Gerar Prompts", self._correr_chunking).pack(anchor="w", pady=(0,10))

        # Stats
        self.stats_frame3 = self._frame(p)
        self.stats_frame3.pack(fill="x", pady=(0,6))

        # Chunk selector
        sel_frame = self._frame(p)
        sel_frame.pack(fill="x", pady=(0,6))
        self._label(sel_frame, "Ver chunk:").pack(side="left")
        self.chunk_var = tk.StringVar()
        self.combo_chunks = ttk.Combobox(sel_frame, textvariable=self.chunk_var,
                                          state="readonly", width=30)
        self.combo_chunks.pack(side="left", padx=8)
        self.combo_chunks.bind("<<ComboboxSelected>>", self._mostrar_chunk)

        # Chunk / Prompt lado a lado
        colunas = self._frame(p)
        colunas.pack(fill="both", expand=True)
        col_c = self._frame(colunas)
        col_c.pack(side="left", fill="both", expand=True, padx=(0,6))
        self._label(col_c, "Texto do chunk:").pack(anchor="w")
        self.area_chunk = self._textarea(col_c, height=16)
        self.area_chunk.pack(fill="both", expand=True, pady=(4,0))

        col_pr = self._frame(colunas)
        col_pr.pack(side="left", fill="both", expand=True)
        self._label(col_pr, "Prompt gerado:").pack(anchor="w")
        self.area_prompt = self._textarea(col_pr, height=16)
        self.area_prompt.pack(fill="both", expand=True, pady=(4,0))

    def _correr_chunking(self):
        fonte = self.texto_limpo or self.texto_bruto
        if not fonte:
            messagebox.showwarning("Aviso", "Extrai primeiro um ficheiro no separador 1.")
            return
        estrategia = self.estrategia_var.get()
        tipo = self.tipo_norm_var.get()
        fn = ESTRATEGIAS_CHUNKING.get(estrategia, list(ESTRATEGIAS_CHUNKING.values())[0])
        self.chunks  = fn(fonte)
        self.prompts = [gerar_prompt(c, self.idioma, tipo) for c in self.chunks]
        self.resultados_api = []; self.texto_final = ""

        # Stats
        for w in self.stats_frame3.winfo_children():
            w.destroy()
        avg = sum(len(c.split()) for c in self.chunks) / max(len(self.chunks), 1)
        self._stat_card(self.stats_frame3, "Chunks",       len(self.chunks))
        self._stat_card(self.stats_frame3, "Palavras/chunk", f"{avg:.0f}")
        self._stat_card(self.stats_frame3, "Maior",        f"{max(len(c) for c in self.chunks):,} chars")
        self._stat_card(self.stats_frame3, "Menor",        f"{min(len(c) for c in self.chunks):,} chars")

        # Combo
        self.combo_chunks["values"] = [f"Chunk {i+1}  ({len(c.split())} palavras)"
                                        for i, c in enumerate(self.chunks)]
        if self.chunks:
            self.combo_chunks.current(0)
            self._mostrar_chunk()

        self._status(f"✓ {len(self.chunks)} chunks gerados com estratégia '{estrategia}'")

    def _mostrar_chunk(self, event=None):
        idx = self.combo_chunks.current()
        if idx < 0 or idx >= len(self.chunks):
            return
        for area, conteudo in [(self.area_chunk, self.chunks[idx]),
                               (self.area_prompt, self.prompts[idx])]:
            area.config(state="normal")
            area.delete("1.0", "end")
            area.insert("1.0", conteudo)
            area.config(state="disabled")

    # API SLM 

    def _build_tab4(self):
        p = self._frame(self.tab4)
        p.pack(fill="both", expand=True, padx=16, pady=14)

        info = self._panel(p, "Endpoint")
        info.pack(fill="x", pady=(0,10))
        tk.Label(info, text=f"URL: {API_URL}    Modelo: {API_MODEL}",
                 font=FONTE_MONO, bg=COR_PANEL, fg=COR_TEXTO2).pack(anchor="w", padx=10, pady=6)

        cfg = self._frame(p)
        cfg.pack(fill="x", pady=(0,10))
        self._label(cfg, "Máx. chunks a enviar:").pack(side="left")
        tk.Spinbox(cfg, from_=1, to=20, textvariable=self.max_chunks_var,
                   width=4, bg=COR_PANEL, fg=COR_TEXTO, font=FONTE_MONO,
                   buttonbackground=COR_PANEL).pack(side="left", padx=8)

        btns = self._frame(p)
        btns.pack(fill="x", pady=(0,10))
        self._btn(btns, "🚀  Enviar para API", self._enviar_api).pack(side="left", padx=(0,8))

        # Progresso
        self.progresso_var = tk.DoubleVar(value=0)
        self.barra_prog = ttk.Progressbar(p, variable=self.progresso_var, maximum=100)
        self.barra_prog.pack(fill="x", pady=(0,8))

        # Stats
        self.stats_frame4 = self._frame(p)
        self.stats_frame4.pack(fill="x", pady=(0,6))

        # Texto final normalizado
        self._label(p, "Texto normalizado pela API:").pack(anchor="w")
        self.area_normalizado = self._textarea(p, height=18)
        self.area_normalizado.pack(fill="both", expand=True, pady=(4,0))

    def _enviar_api(self):
        if not self.prompts:
            messagebox.showwarning("Aviso", "Gera os prompts no separador 3 primeiro.")
            return
        n = min(self.max_chunks_var.get(), len(self.prompts))
        self._status(f"A enviar {n} chunks para a API...")
        self.progresso_var.set(0)

        def tarefa():
            resultados = []
            for i, prompt in enumerate(self.prompts[:n]):
                r = chamar_api(prompt)
                resultados.append(r)
                self.progresso_var.set((i + 1) / n * 100)
                self._status(f"Chunk {i+1}/{n} — {'OK' if r['sucesso'] else 'ERRO'}")
            self.resultados_api = resultados
            self.texto_final = "\n\n".join(
                r["conteudo"] for r in resultados if r.get("sucesso") and r.get("conteudo"))
            self.after(0, self._atualizar_tab4)

        threading.Thread(target=tarefa, daemon=True).start()

    def _atualizar_tab4(self):
        resultados = self.resultados_api
        ok    = sum(1 for r in resultados if r.get("sucesso"))
        fail  = len(resultados) - ok
        toks  = sum(r.get("tokens_resposta", 0) for r in resultados)
        avg   = round(sum(r["tempo"] for r in resultados) / max(len(resultados), 1), 2)

        for w in self.stats_frame4.winfo_children():
            w.destroy()
        self._stat_card(self.stats_frame4, "Enviados",    len(resultados))
        self._stat_card(self.stats_frame4, "Sucesso",     ok)
        self._stat_card(self.stats_frame4, "Erro",        fail)
        self._stat_card(self.stats_frame4, "Tokens",      f"{toks:,}")
        self._stat_card(self.stats_frame4, "Tempo médio", f"{avg}s")

        self.area_normalizado.config(state="normal")
        self.area_normalizado.delete("1.0", "end")
        self.area_normalizado.insert("1.0", self.texto_final or "(Sem resposta da API)")
        self.area_normalizado.config(state="disabled")

        self._status(f"✓ {ok}/{len(resultados)} chunks processados | {toks} tokens gerados")

    # Relatório 

    def _build_tab5(self):
        p = self._frame(self.tab5)
        p.pack(fill="both", expand=True, padx=16, pady=14)

        self._label(p, "Gera um relatório completo com os parâmetros, o texto antes/depois e a avaliação da normalização.",
                    fg=COR_TEXTO2).pack(anchor="w", pady=(0,14))

        # Estado do pipeline
        estado = self._panel(p, "Estado do pipeline")
        estado.pack(fill="x", pady=(0,14))
        self.estado_frame = tk.Frame(estado, bg=COR_PANEL)
        self.estado_frame.pack(fill="x", padx=10, pady=(0,10))
        self._atualizar_estado()

        # Botões
        btns = self._frame(p)
        btns.pack(fill="x", pady=(0,14))
        self._btn(btns, "📄  Exportar HTML", lambda: self._gerar_relatorio("html")).pack(side="left", padx=(0,10))
        self._btn(btns, "📑  Exportar PDF",  lambda: self._gerar_relatorio("pdf"),
                  cor="#2563eb").pack(side="left")
        tk.Label(btns, text="(PDF requer weasyprint)", font=("Courier New", 8),
                 bg=COR_BG, fg=COR_TEXTO2).pack(side="left", padx=10)

        # Pré-visualização
        self._label(p, "Pré-visualização do relatório:").pack(anchor="w")
        self.area_relatorio = self._textarea(p, height=22)
        self.area_relatorio.pack(fill="both", expand=True, pady=(4,0))

        # Atualizar estado ao mudar de tab
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        if self.nb.index("current") == 4:
            self._atualizar_estado()

    def _atualizar_estado(self):
        for w in self.estado_frame.winfo_children():
            w.destroy()
        itens = [
            ("📄 Extração",  bool(self.texto_bruto)),
            ("🧹 Limpeza",   bool(self.texto_limpo)),
            ("✂️ Chunking",  bool(self.chunks)),
            ("🤖 API SLM",   bool(self.resultados_api)),
        ]
        for nome, feito in itens:
            cor  = COR_VERDE if feito else COR_VERMELHO
            tick = "✓ Feito" if feito else "⏳ Pendente"
            f = tk.Frame(self.estado_frame, bg=COR_PANEL)
            f.pack(side="left", expand=True, fill="x", padx=6, pady=6)
            tk.Label(f, text=nome, font=("Courier New", 9), bg=COR_PANEL, fg=COR_TEXTO).pack()
            tk.Label(f, text=tick, font=("Courier New", 9, "bold"), bg=COR_PANEL, fg=cor).pack()

    def _gerar_relatorio(self, fmt):
        if not self.texto_bruto:
            messagebox.showwarning("Aviso", "Extrai primeiro um ficheiro no separador 1.")
            return
        try:
            html = gerar_relatorio_html(
                nome_ficheiro=self.nome_ficheiro or "texto",
                texto_bruto=self.texto_bruto,
                texto_limpo=self.texto_limpo or self.texto_bruto,
                estatisticas=self.estatisticas,
                idioma=self.idioma,
                confianca=self.confianca_id,
                estrategia=self.estrategia_var.get(),
                tipo_norm=self.tipo_norm_var.get(),
                resultados_api=self.resultados_api or None,
                texto_final=self.texto_final,
            )

            if fmt == "html":
                caminho = filedialog.asksaveasfilename(
                    defaultextension=".html",
                    filetypes=[("HTML", "*.html")],
                    initialfile="relatorio_textnorm.html",
                )
                if caminho:
                    with open(caminho, "w", encoding="utf-8") as f:
                        f.write(html)
                    self._status(f"✓ Relatório HTML guardado em {caminho}")
                    messagebox.showinfo("Sucesso", f"Relatório guardado em:\n{caminho}")

            elif fmt == "pdf":
                try:
                    from weasyprint import HTML as WP
                    caminho = filedialog.asksaveasfilename(
                        defaultextension=".pdf",
                        filetypes=[("PDF", "*.pdf")],
                        initialfile="relatorio_textnorm.pdf",
                    )
                    if caminho:
                        WP(string=html).write_pdf(caminho)
                        self._status(f"✓ Relatório PDF guardado em {caminho}")
                        messagebox.showinfo("Sucesso", f"Relatório PDF guardado em:\n{caminho}")
                except ImportError:
                    messagebox.showerror("weasyprint não encontrado",
                                         "Instala com:\n\npip install weasyprint\n\nA guardar como HTML em alternativa.")
                    self._gerar_relatorio("html")
                    return

            # Pré-visualização
            self.area_relatorio.config(state="normal")
            self.area_relatorio.delete("1.0", "end")
            self.area_relatorio.insert("1.0", html)
            self.area_relatorio.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Erro", str(e))
            self._status("Erro ao gerar relatório.")

# MAIN

if __name__ == "__main__":
    app = TextNormApp()
    app.mainloop()