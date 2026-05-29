import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os

# importa os módulos do projeto
from extractor import extrair_texto
from cleaner import ETAPAS_PIPELINE, correr_pipeline
from chunker import ESTRATEGIAS_CHUNKING, segmentar_texto
from lang_prompt import detetar_idioma, gerar_prompt, NOMES_IDIOMA, TIPOS_NORMALIZACAO
from api import chamar_api, API_URL, API_MODEL
from gerador_relatorio import gerar_relatorio_html, guardar_html, guardar_pdf


# ── Cores e fontes ────────────────────────────────────────────────────────────
COR_BG      = "#1a1a1a"
COR_PANEL   = "#242424"
COR_BORDA   = "#333333"
COR_LARANJA = "#E85D26"
COR_TEXTO   = "#F0EDE8"
COR_TEXTO2  = "#999999"
COR_VERDE   = "#4ade80"
COR_VERMELHO= "#f87171"
FONTE_MONO  = ("Courier New", 11)
FONTE_LABEL = ("Segoe UI", 11)
FONTE_BTN   = ("Courier New", 11, "bold")
FONTE_TITULO= ("Courier New", 12, "bold")


class TextNormApp(tk.Tk):
    """
    Classe principal da aplicação — herda de tk.Tk (a janela raiz do tkinter).
    Organizada em 5 separadores, um por tarefa do enunciado.
    O estado (texto extraído, limpo, chunks, etc.) é guardado em atributos
    da classe para ser partilhado entre separadores.
    """

    def __init__(self):
        super().__init__()
        self.title("TextNorm Pipeline – UTAD TP2")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(bg=COR_BG)

        # ── Estado partilhado entre separadores ───────────────────────────────
        self.texto_bruto    = ""
        self.texto_limpo    = ""
        self.nome_ficheiro  = ""
        self.idioma         = "desconhecido"
        self.confianca_id   = 0.0
        self.estatisticas   = []
        self.chunks         = []
        self.prompts        = []
        self.resultados_api = []
        self.texto_final    = ""

        # variáveis tkinter ligadas a widgets da interface
        self.etapas_vars    = []
        self.estrategia_var = tk.StringVar(value="Por parágrafo")
        self.tipo_norm_var  = tk.StringVar(value="Normalização geral")
        self.max_chunks_var = tk.IntVar(value=3)

        self._build_ui()

    # ── Helpers de criação de widgets ─────────────────────────────────────────

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
                         relief="flat", cursor="hand2", padx=18, pady=8, **kw)

    def _textarea(self, parent, height=10, **kw):
        return scrolledtext.ScrolledText(
            parent, height=height, font=FONTE_MONO,
            bg="#0f0f0f", fg=COR_TEXTO, relief="flat", wrap="word", **kw)

    def _status(self, msg):
        self.status_var.set(msg)
        self.update_idletasks()

    def _stat_card(self, parent, titulo, valor):
        f = tk.Frame(parent, bg=COR_PANEL, highlightthickness=1,
                     highlightbackground=COR_BORDA)
        f.pack(side="left", padx=6, pady=6, fill="x", expand=True)
        tk.Label(f, text=str(valor), font=("Courier New", 16, "bold"),
                 bg=COR_PANEL, fg=COR_LARANJA).pack(pady=(12,2))
        tk.Label(f, text=titulo.upper(), font=("Courier New", 8),
                 bg=COR_PANEL, fg=COR_TEXTO2).pack(pady=(2,12))

    # ── Construção da UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        """Constrói o cabeçalho, os 5 separadores e a barra de estado."""
        header = tk.Frame(self, bg="#0d0d0d", height=65)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="⚙  TextNorm Pipeline",
                 font=("Courier New", 16, "bold"), bg="#0d0d0d", fg=COR_TEXTO).pack(side="left", padx=24, pady=12)
        tk.Label(header, text="UTAD · Laboratório de Programação · TP2 · 2025/26",
                 font=("Courier New", 10), bg="#0d0d0d", fg=COR_TEXTO2).pack(side="left", padx=8)
        tk.Frame(self, bg=COR_LARANJA, height=3).pack(fill="x")

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background=COR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COR_PANEL, foreground=COR_TEXTO2,
                        font=FONTE_TITULO, padding=[20, 10])
        style.map("TNotebook.Tab",
                  background=[("selected", COR_LARANJA)],
                  foreground=[("selected", "white")])
        style.configure("TFrame", background=COR_BG)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

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

        self.status_var = tk.StringVar(value="Pronto. Carrega um ficheiro para começar.")
        barra = tk.Frame(self, bg="#0d0d0d", height=32)
        barra.pack(fill="x", side="bottom")
        tk.Label(barra, textvariable=self.status_var,
                 font=("Courier New", 10), bg="#0d0d0d", fg=COR_TEXTO2,
                 anchor="w").pack(fill="x", padx=14, pady=6)

    # ── Tab 1 – Extração ──────────────────────────────────────────────────────

    def _build_tab1(self):
        p = self._frame(self.tab1)
        p.pack(fill="both", expand=True, padx=20, pady=18)
        top = self._frame(p)
        top.pack(fill="x")
        self._btn(top, "📂  Abrir Ficheiro", self._abrir_ficheiro).pack(side="left")
        self.label_ficheiro = tk.Label(top, text="Nenhum ficheiro selecionado",
                                       font=("Courier New", 9), bg=COR_BG, fg=COR_TEXTO2)
        self.label_ficheiro.pack(side="left", padx=14)
        self.stats_frame1 = self._frame(p)
        self.stats_frame1.pack(fill="x", pady=(10,6))
        self.label_idioma = tk.Label(p, text="", font=("Courier New", 9),
                                     bg=COR_BG, fg=COR_VERDE)
        self.label_idioma.pack(anchor="w", pady=(0,6))
        self._label(p, "Texto extraído (bruto):").pack(anchor="w")
        self.area_bruto = self._textarea(p, height=22)
        self.area_bruto.pack(fill="both", expand=True, pady=(8,0))

    def _abrir_ficheiro(self):
        """Abre o seletor de ficheiros e chama extrair_texto() do módulo extractor."""
        caminho = filedialog.askopenfilename(
            filetypes=[("Documentos", "*.pdf *.docx *.txt"), ("Todos", "*.*")])
        if not caminho:
            return
        try:
            texto = extrair_texto(caminho)   # função do extractor.py
            self.texto_bruto   = texto
            self.nome_ficheiro = os.path.basename(caminho)
            self.texto_limpo = ""; self.estatisticas = []
            self.chunks = []; self.prompts = []
            self.resultados_api = []; self.texto_final = ""

            idioma, conf = detetar_idioma(texto)   # função do lang_prompt.py
            self.idioma = idioma; self.confianca_id = conf

            self.label_ficheiro.config(text=self.nome_ficheiro)
            for w in self.stats_frame1.winfo_children(): w.destroy()
            self._stat_card(self.stats_frame1, "Caracteres", f"{len(texto):,}")
            self._stat_card(self.stats_frame1, "Palavras",   f"{len(texto.split()):,}")
            self._stat_card(self.stats_frame1, "Linhas",     f"{texto.count(chr(10))+1:,}")
            self.label_idioma.config(
                text=f"🌐  Idioma detetado: {NOMES_IDIOMA.get(idioma, idioma)}  ({int(conf*100)}% confiança — valor normal, nunca 100%)")
            self.area_bruto.config(state="normal")
            self.area_bruto.delete("1.0", "end")
            self.area_bruto.insert("1.0", texto)
            self.area_bruto.see("1.0")
            self.area_bruto.update()
            self.area_bruto.config(state="disabled")
            self._status(f"✓ {self.nome_ficheiro} carregado — {len(texto):,} chars")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ── Tab 2 – Limpeza ───────────────────────────────────────────────────────

    def _build_tab2(self):
        p = self._frame(self.tab2)
        p.pack(fill="both", expand=True, padx=20, pady=18)
        painel = self._panel(p, "Etapas da pipeline")
        painel.pack(fill="x", pady=(0,14))
        grid = tk.Frame(painel, bg=COR_PANEL)
        grid.pack(fill="x", padx=10, pady=(0,14))
        self.etapas_vars = []
        for i, (nome, _) in enumerate(ETAPAS_PIPELINE):
            var = tk.BooleanVar(value=True)
            tk.Checkbutton(grid, text=nome, variable=var,
                           bg=COR_PANEL, fg=COR_TEXTO, selectcolor=COR_BG,
                           activebackground=COR_PANEL, font=FONTE_LABEL,
                           cursor="hand2").grid(row=i//2, column=i%2, sticky="w", padx=10, pady=2)
            self.etapas_vars.append(var)
        self._btn(p, "▶  Executar Pipeline", self._correr_pipeline).pack(anchor="w", pady=(0,14))
        self.stats_frame2 = self._frame(p)
        self.stats_frame2.pack(fill="x", pady=(0,6))
        colunas = self._frame(p)
        colunas.pack(fill="both", expand=True)
        col_e = self._frame(colunas)
        col_e.pack(side="left", fill="both", expand=True, padx=(0,6))
        self._label(col_e, "Antes da limpeza:").pack(anchor="w")
        self.area_antes = self._textarea(col_e, height=16)
        self.area_antes.pack(fill="both", expand=True, pady=(8,0))
        col_d = self._frame(colunas)
        col_d.pack(side="left", fill="both", expand=True)
        self._label(col_d, "Depois da limpeza:").pack(anchor="w")
        self.area_depois = self._textarea(col_d, height=16)
        self.area_depois.pack(fill="both", expand=True, pady=(8,0))

    def _correr_pipeline(self):
        """Lê os checkboxes e chama correr_pipeline() do módulo cleaner."""
        if not self.texto_bruto:
            messagebox.showwarning("Aviso", "Extrai primeiro um ficheiro no separador 1.")
            return
        ativas = [v.get() for v in self.etapas_vars]
        try:
            limpo, stats = correr_pipeline(self.texto_bruto, ativas)   # cleaner.py
            self.texto_limpo = limpo; self.estatisticas = stats
            self.chunks = []; self.prompts = []
            self.resultados_api = []; self.texto_final = ""
            for w in self.stats_frame2.winfo_children(): w.destroy()
            total_rem = sum(e["chars_removidos"] for e in stats)
            pct = round(100 * total_rem / max(len(self.texto_bruto), 1), 1)
            self._stat_card(self.stats_frame2, "Etapas",          len(stats))
            self._stat_card(self.stats_frame2, "Chars removidos", f"{total_rem:,}")
            self._stat_card(self.stats_frame2, "Redução",         f"{pct}%")
            for area, conteudo in [(self.area_antes, self.texto_bruto),
                                   (self.area_depois, limpo)]:
                area.config(state="normal")
                area.delete("1.0", "end")
                area.insert("1.0", conteudo)
                area.config(state="disabled")
            if total_rem == 0:
                self._status("✓ Pipeline concluída — texto já estava limpo, nenhuma alteração necessária")
            else:
                self._status(f"✓ Pipeline concluída — {len(stats)} etapas | -{pct}% ({total_rem:,} chars removidos)")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ── Tab 3 – Chunking & Prompt ─────────────────────────────────────────────

    def _build_tab3(self):
        p = self._frame(self.tab3)
        p.pack(fill="both", expand=True, padx=20, pady=18)
        opcoes = self._panel(p, "Configuração")
        opcoes.pack(fill="x", pady=(0,14))
        grid = tk.Frame(opcoes, bg=COR_PANEL)
        grid.pack(fill="x", padx=10, pady=(0,14))
        self._label(grid, "Estratégia:", bg=COR_PANEL).grid(row=0, column=0, sticky="w", pady=4, padx=4)
        ttk.Combobox(grid, textvariable=self.estrategia_var,
                     values=list(ESTRATEGIAS_CHUNKING.keys()),
                     state="readonly", width=28).grid(row=0, column=1, sticky="w", pady=4, padx=4)
        self._label(grid, "Tipo de normalização:", bg=COR_PANEL).grid(row=1, column=0, sticky="w", pady=4, padx=4)
        ttk.Combobox(grid, textvariable=self.tipo_norm_var,
                     values=TIPOS_NORMALIZACAO,
                     state="readonly", width=28).grid(row=1, column=1, sticky="w", pady=4, padx=4)
        self._btn(p, "✂️  Segmentar & Gerar Prompts", self._correr_chunking).pack(anchor="w", pady=(0,14))
        self.stats_frame3 = self._frame(p)
        self.stats_frame3.pack(fill="x", pady=(0,6))
        sel_frame = self._frame(p)
        sel_frame.pack(fill="x", pady=(0,6))
        self._label(sel_frame, "Ver chunk:").pack(side="left")
        self.chunk_var = tk.StringVar()
        self.combo_chunks = ttk.Combobox(sel_frame, textvariable=self.chunk_var,
                                          state="readonly", width=30)
        self.combo_chunks.pack(side="left", padx=8)
        self.combo_chunks.bind("<<ComboboxSelected>>", self._mostrar_chunk)
        colunas = self._frame(p)
        colunas.pack(fill="both", expand=True)
        col_c = self._frame(colunas)
        col_c.pack(side="left", fill="both", expand=True, padx=(0,6))
        self._label(col_c, "Texto do chunk:").pack(anchor="w")
        self.area_chunk = self._textarea(col_c, height=16)
        self.area_chunk.pack(fill="both", expand=True, pady=(8,0))
        col_pr = self._frame(colunas)
        col_pr.pack(side="left", fill="both", expand=True)
        self._label(col_pr, "Prompt gerado (instruções + texto do chunk):").pack(anchor="w")
        self.area_prompt = self._textarea(col_pr, height=16)
        self.area_prompt.pack(fill="both", expand=True, pady=(8,0))

    def _correr_chunking(self):
        """Chama segmentar_texto() do chunker.py e gerar_prompt() do lang_prompt.py."""
        fonte = self.texto_limpo or self.texto_bruto
        if not fonte:
            messagebox.showwarning("Aviso", "Extrai primeiro um ficheiro no separador 1.")
            return
        estrategia = self.estrategia_var.get()
        tipo = self.tipo_norm_var.get()
        self.chunks  = segmentar_texto(fonte, estrategia)   # chunker.py
        self.prompts = [gerar_prompt(c, self.idioma, tipo) for c in self.chunks]  # lang_prompt.py
        self.resultados_api = []; self.texto_final = ""
        for w in self.stats_frame3.winfo_children(): w.destroy()
        avg = sum(len(c.split()) for c in self.chunks) / max(len(self.chunks), 1)
        self._stat_card(self.stats_frame3, "Chunks",        len(self.chunks))
        self._stat_card(self.stats_frame3, "Palavras/chunk", f"{avg:.0f}")
        self._stat_card(self.stats_frame3, "Maior",         f"{max(len(c) for c in self.chunks):,} ch")
        self.combo_chunks["values"] = [f"Chunk {i+1}  ({len(c.split())} palavras)"
                                        for i, c in enumerate(self.chunks)]
        if self.chunks:
            self.combo_chunks.current(0)
            self._mostrar_chunk()
        self._status(f"✓ {len(self.chunks)} chunks gerados")

    def _mostrar_chunk(self, event=None):
        """Atualiza as áreas de texto com o chunk e prompt selecionados."""
        idx = self.combo_chunks.current()
        if idx < 0 or idx >= len(self.chunks): return
        for area, conteudo in [(self.area_chunk, self.chunks[idx]),
                               (self.area_prompt, self.prompts[idx])]:
            area.config(state="normal")
            area.delete("1.0", "end")
            area.insert("1.0", conteudo)
            area.config(state="disabled")

    # ── Tab 4 – API SLM ───────────────────────────────────────────────────────

    def _build_tab4(self):
        p = self._frame(self.tab4)
        p.pack(fill="both", expand=True, padx=20, pady=18)

        # aviso sobre rede da UTAD
        aviso = tk.Frame(p, bg="#2a1f00", highlightthickness=1, highlightbackground="#E85D26")
        aviso.pack(fill="x", pady=(0,14))
        tk.Label(aviso,
                 text="⚠  Esta funcionalidade requer ligação à rede da UTAD (presencial ou VPN).\n"
                      "   Fora da rede os pedidos irão falhar — usa o botão Demo para ver um exemplo.",
                 font=("Courier New", 9), bg="#2a1f00", fg="#fbbf24",
                 justify="left").pack(anchor="w", padx=12, pady=8)

        info = self._panel(p, "Endpoint")
        info.pack(fill="x", pady=(0,14))
        tk.Label(info, text=f"URL: {API_URL}    Modelo: {API_MODEL}",
                 font=FONTE_MONO, bg=COR_PANEL, fg=COR_TEXTO2).pack(anchor="w", padx=10, pady=6)
        cfg = self._frame(p)
        cfg.pack(fill="x", pady=(0,14))
        self._label(cfg, "Max. chunks a enviar:").pack(side="left")
        tk.Spinbox(cfg, from_=1, to=20, textvariable=self.max_chunks_var,
                   width=4, bg=COR_PANEL, fg=COR_TEXTO, font=FONTE_MONO,
                   buttonbackground=COR_PANEL).pack(side="left", padx=8)

        btns = self._frame(p)
        btns.pack(anchor="w", pady=(0,14))
        self._btn(btns, "Enviar para API", self._enviar_api).pack(side="left", padx=(0,8))
        self._btn(btns, "Demo (sem rede)", self._demo_api, cor="#555555").pack(side="left")
        self.progresso_var = tk.DoubleVar(value=0)
        ttk.Progressbar(p, variable=self.progresso_var, maximum=100).pack(fill="x", pady=(0,8))
        self.stats_frame4 = self._frame(p)
        self.stats_frame4.pack(fill="x", pady=(0,6))
        self._label(p, "Texto normalizado pela API:").pack(anchor="w")
        self.area_normalizado = self._textarea(p, height=18)
        self.area_normalizado.pack(fill="both", expand=True, pady=(8,0))

    def _enviar_api(self):
        """
        Envia os chunks à API em background com threading.
        Threading é necessário para não bloquear a interface durante os pedidos.
        Chama chamar_api() do módulo api_client.py.
        """
        if not self.prompts:
            messagebox.showwarning("Aviso", "Gera os prompts no separador 3 primeiro.")
            return
        n = min(self.max_chunks_var.get(), len(self.prompts))
        self.progresso_var.set(0)

        def tarefa():
            resultados = []
            for i, prompt in enumerate(self.prompts[:n]):
                self._status(f"Chunk {i+1}/{n} — Tentativa 1...")
                r = chamar_api(prompt)   # api_client.py — com retry automático
                resultados.append(r)
                self.progresso_var.set((i + 1) / n * 100)
                t = r.get("tentativas", 1)
                if r["sucesso"]:
                    self._status(f"Chunk {i+1}/{n} — OK à {t}ª tentativa ({r['tempo']}s)")
                else:
                    self._status(f"Chunk {i+1}/{n} — Erro após {t} tentativas")
            self.resultados_api = resultados
            self.texto_final = "\n\n".join(
                r["conteudo"] for r in resultados if r.get("sucesso") and r.get("conteudo"))
            self.after(0, self._atualizar_tab4)

        threading.Thread(target=tarefa, daemon=True).start()

    def _demo_api(self):
        """
        Simula uma resposta da API sem necessitar de rede.
        Util para demonstrar a aplicacao fora da rede da UTAD.
        Usa o primeiro chunk disponivel e mostra um texto normalizado de exemplo.
        """
        if not self.chunks:
            messagebox.showwarning("Aviso", "Gera os prompts no separador 3 primeiro.")
            return

        EXEMPLO_RESPOSTA = (
            "Este é um exemplo de texto normalizado pelo modelo llama-3.2-1b-instruct.\n\n"
            "Na versão real, o modelo recebe o prompt com o texto original e devolve "
            "o texto corrigido ortograficamente, com a pontuação melhorada e a estrutura "
            "de frases mais coerente, mantendo sempre o significado original.\n\n"
            "Para usar a API real, liga-te à rede da UTAD (presencial ou VPN) "
            "e clica em 'Enviar para API'."
        )

        # simula um resultado bem-sucedido para cada chunk
        n = min(self.max_chunks_var.get(), len(self.chunks))
        self.resultados_api = [
            {"sucesso": True, "conteudo": EXEMPLO_RESPOSTA,
             "tokens_prompt": 120, "tokens_resposta": 85,
             "tempo": 1.2, "tentativas": 1, "erro": None}
            for _ in range(n)
        ]
        self.texto_final = EXEMPLO_RESPOSTA
        self.after(0, self._atualizar_tab4)
        self._status("Demo: a mostrar exemplo de resposta da API (sem ligacao real)")

    def _atualizar_tab4(self):
        """Atualiza os cards e o texto normalizado após receber as respostas da API."""
        rs = self.resultados_api
        ok   = sum(1 for r in rs if r.get("sucesso"))
        toks = sum(r.get("tokens_resposta", 0) for r in rs)
        avg  = round(sum(r["tempo"] for r in rs) / max(len(rs), 1), 2)
        total_tent = sum(r.get("tentativas", 1) for r in rs)
        for w in self.stats_frame4.winfo_children(): w.destroy()
        self._stat_card(self.stats_frame4, "Enviados",    len(rs))
        self._stat_card(self.stats_frame4, "Sucesso",     ok)
        self._stat_card(self.stats_frame4, "Tentativas",  total_tent)
        self._stat_card(self.stats_frame4, "Tokens",      f"{toks:,}")
        self._stat_card(self.stats_frame4, "Tempo médio", f"{avg}s")
        self.area_normalizado.config(state="normal")
        self.area_normalizado.delete("1.0", "end")
        msg = self.texto_final or (
            "(Sem resposta da API)\n\n"
            "Possivel causa: nao estas ligado a rede da UTAD.\n"
            "Liga-te a rede UTAD (presencial ou VPN) e tenta novamente,\n"
            "ou clica em Demo para ver um exemplo sem ligacao.")
        self.area_normalizado.insert("1.0", msg)
        self.area_normalizado.config(state="disabled")
        self._status(f"✓ {ok}/{len(rs)} chunks processados | {toks} tokens")

    # ── Tab 5 – Relatório ─────────────────────────────────────────────────────

    def _build_tab5(self):
        p = self._frame(self.tab5)
        p.pack(fill="both", expand=True, padx=20, pady=18)
        estado = self._panel(p, "Estado do pipeline")
        estado.pack(fill="x", pady=(0,14))
        self.estado_frame = tk.Frame(estado, bg=COR_PANEL)
        self.estado_frame.pack(fill="x", padx=10, pady=(0,14))
        self._atualizar_estado()
        btns = self._frame(p)
        btns.pack(fill="x", pady=(0,14))
        self._btn(btns, "📄  Exportar HTML", lambda: self._gerar_relatorio("html")).pack(side="left", padx=(0,10))
        self._btn(btns, "📑  Exportar PDF",  lambda: self._gerar_relatorio("pdf"),
                  cor="#2563eb").pack(side="left")
        tk.Label(btns, text="(PDF requer weasyprint)", font=("Courier New", 8),
                 bg=COR_BG, fg=COR_TEXTO2).pack(side="left", padx=10)
        self._label(p, "Pré-visualização:").pack(anchor="w")
        self.area_relatorio = self._textarea(p, height=22)
        self.area_relatorio.pack(fill="both", expand=True, pady=(8,0))
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        if self.nb.index("current") == 4:
            self._atualizar_estado()

    def _atualizar_estado(self):
        """Mostra quais etapas já foram concluídas com indicadores visuais."""
        for w in self.estado_frame.winfo_children(): w.destroy()
        for nome, feito in [
            ("📄 Extração",  bool(self.texto_bruto)),
            ("🧹 Limpeza",   bool(self.texto_limpo)),
            ("✂️ Chunking",  bool(self.chunks)),
            ("🤖 API SLM",   bool(self.resultados_api)),
        ]:
            cor  = COR_VERDE if feito else COR_VERMELHO
            tick = "✓ Feito" if feito else "⏳ Pendente"
            f = tk.Frame(self.estado_frame, bg=COR_PANEL)
            f.pack(side="left", expand=True, fill="x", padx=10, pady=10)
            tk.Label(f, text=nome, font=("Courier New", 9), bg=COR_PANEL, fg=COR_TEXTO).pack()
            tk.Label(f, text=tick, font=("Courier New", 9, "bold"), bg=COR_PANEL, fg=cor).pack()

    def _gerar_relatorio(self, fmt):
        """
        Chama gerar_relatorio_html() do report_generator.py e guarda em ficheiro.
        Usa guardar_html() ou guardar_pdf() do mesmo módulo.
        """
        if not self.texto_bruto:
            messagebox.showwarning("Aviso", "Extrai primeiro um ficheiro no separador 1.")
            return
        try:
            html = gerar_relatorio_html(   # report_generator.py
                nome_ficheiro  = self.nome_ficheiro or "texto",
                texto_bruto    = self.texto_bruto,
                texto_limpo    = self.texto_limpo or self.texto_bruto,
                estatisticas   = self.estatisticas,
                idioma         = self.idioma,
                confianca      = self.confianca_id,
                estrategia     = self.estrategia_var.get(),
                tipo_norm      = self.tipo_norm_var.get(),
                resultados_api = self.resultados_api or None,
                texto_final    = self.texto_final,
            )
            if fmt == "html":
                caminho = filedialog.asksaveasfilename(
                    defaultextension=".html",
                    filetypes=[("HTML", "*.html")],
                    initialfile="relatorio_textnorm.html")
                if caminho:
                    import webbrowser
                    guardar_html(html, caminho)   # report_generator.py
                    webbrowser.open(f"file:///{caminho.replace(chr(92), '/')}")
                    messagebox.showinfo("Sucesso", f"Relatório guardado e aberto no browser:\n{caminho}")
                    self._status(f"✓ Relatório HTML guardado e aberto no browser")
            elif fmt == "pdf":
                try:
                    caminho = filedialog.asksaveasfilename(
                        defaultextension=".pdf",
                        filetypes=[("PDF", "*.pdf")],
                        initialfile="relatorio_textnorm.pdf")
                    if caminho:
                        guardar_pdf(html, caminho)   # report_generator.py
                        messagebox.showinfo("Sucesso", f"Guardado em:\n{caminho}")
                except RuntimeError:
                    messagebox.showerror("Erro", "weasyprint não instalado.\npip install weasyprint")
                    self._gerar_relatorio("html")
                    return
            self.area_relatorio.config(state="normal")
            self.area_relatorio.delete("1.0", "end")
            self.area_relatorio.insert("1.0", html)
            self.area_relatorio.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Erro", str(e))


# ── Ponto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = TextNormApp()
    app.mainloop()