"""
report_generator.py
Tarefa 5 – Geração de Relatórios Automáticos
Exporta em HTML (sem dependências) ou PDF (requer weasyprint).
"""

import html as html_module
import datetime

from lang_prompt import NOMES_IDIOMA
from api import API_MODEL


def gerar_relatorio_html(
    nome_ficheiro, texto_bruto, texto_limpo,
    estatisticas, idioma, confianca,
    estrategia, tipo_norm,
    resultados_api=None, texto_final=""
) -> str:
    """
    Gera um relatório HTML completo com:
    - Visão geral com estatísticas (chars, redução, idioma)
    - Parâmetros utilizados
    - Tabela por etapa da pipeline
    - Texto antes e depois da limpeza
    - Resultados da API (se executada)
    Devolve a string HTML pronta a guardar em ficheiro.
    """
    def _e(t):
        return html_module.escape(str(t))

    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_rem = sum(e["chars_removidos"] for e in estatisticas)
    pct = round(100 * total_rem / max(len(texto_bruto), 1), 1)

    # linhas da tabela de etapas
    linhas_etapas = ""
    for e in estatisticas:
        cor = "#4ade80" if e["chars_removidos"] >= 0 else "#f87171"
        linhas_etapas += (
            f"<tr><td>{_e(e['etapa'])}</td>"
            f"<td>{e['linhas_antes']:,}</td>"
            f"<td>{e['linhas_depois']:,}</td>"
            f"<td style='color:{cor};font-weight:600'>{e['chars_removidos']:+,}</td></tr>"
        )

    # secção dos resultados da API (só se a API foi chamada)
    secao_api = ""
    if resultados_api:
        ok  = [r for r in resultados_api if r.get("sucesso")]
        avg = round(sum(r["tempo"] for r in resultados_api) / len(resultados_api), 2)
        toks = sum(r.get("tokens_resposta", 0) for r in resultados_api)
        total_tent = sum(r.get("tentativas", 1) for r in resultados_api)
        amostra = _e(texto_final[:2000]) + ("..." if len(texto_final) > 2000 else "")
        secao_api = f"""<section class="s"><h2>4. Resultados da API SLM</h2>
        <div class="grid">
          <div class="card"><span class="val">{len(resultados_api)}</span><span class="lbl">Chunks enviados</span></div>
          <div class="card"><span class="val">{len(ok)}</span><span class="lbl">Com sucesso</span></div>
          <div class="card"><span class="val">{total_tent}</span><span class="lbl">Tentativas totais</span></div>
          <div class="card"><span class="val">{avg}s</span><span class="lbl">Tempo médio</span></div>
          <div class="card"><span class="val">{toks:,}</span><span class="lbl">Tokens gerados</span></div>
        </div>
        <h3>Texto normalizado (amostra)</h3>
        <pre class="box">{amostra}</pre></section>"""

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
  <h1>TextNorm Pipeline — Relatório</h1>
  <div class="sub">Normalização de Texto com SLMs · UTAD 2025/26</div>
  <div class="meta">Ficheiro: {_e(nome_ficheiro)} | Gerado: {agora} | Modelo: {API_MODEL}</div>
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
    <tr><td>Idioma detetado</td><td>{_e(NOMES_IDIOMA.get(idioma, idioma))} ({int(confianca*100)}%)</td></tr>
    <tr><td>Total de caracteres removidos</td><td>{total_rem:,}</td></tr>
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


def guardar_html(html: str, caminho: str) -> str:
    """Guarda o relatório HTML em ficheiro. Devolve o caminho."""
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html)
    return caminho


def guardar_pdf(html: str, caminho: str) -> str:
    """Converte HTML para PDF com weasyprint. Devolve o caminho."""
    try:
        from weasyprint import HTML as WP
        WP(string=html).write_pdf(caminho)
        return caminho
    except ImportError:
        raise RuntimeError("Instala weasyprint:  pip install weasyprint")