# TextNorm Pipeline
    Laboratório de Programação – TP2 | UTAD 2025/26
    Normalização de Texto com Pipeline de Pré-Processamento e SLMs

## Descrição

Aplicação em Python com interface gráfica (tkinter) que processa documentos em **PDF, DOCX e TXT**, aplica uma pipeline configurável de limpeza e pré-processamento de texto, prepara o conteúdo para envio a um modelo de linguagem (SLM) e gera relatórios automáticos em **HTML ou PDF**.

##  Ficheiros

tp2-lab.py         →  aplicação completa com interface gráfica (tkinter)
requirements.txt   →  dependências necessárias
README.md          →  este ficheiro
exemplo_input.txt  →  ficheiro de texto para testar a aplicação
notas_entrega.txt  →  estado de implementação de cada tarefa

##  Interface — Separadores

### 1 · Extração
- Botão **"Abrir Ficheiro"** para carregar PDF, DOCX ou TXT
- Apresenta o texto bruto extraído sem qualquer transformação
- Mostra estatísticas: caracteres, palavras, linhas, tamanho
- Deteta automaticamente o idioma do texto

### 2 · Limpeza
- Checkboxes para ativar/desativar cada etapa da pipeline
- Botão **"Executar Pipeline"**
- Mostra o texto **antes** e **depois** lado a lado
- Cards com estatísticas: etapas executadas, chars removidos, % de redução

### 3 · Chunking & Prompt
- Escolha da estratégia de segmentação (dropdown)
- Escolha do tipo de normalização (dropdown)
- Selector de chunk — vê o texto e o prompt gerado lado a lado
- Cards com estatísticas: nº de chunks, palavras/chunk, maior, menor

### 4 · API SLM
-Configura quantos chunks enviar (spinbox)
-Barra de progresso durante o envio (corre em segundo plano)
-Retry automático — tenta até 3 vezes por chunk, com feedback em tempo real 
-Mostra o texto final normalizado pela API
-Cards: chunks enviados, sucesso, erros, tentativas totais, tokens gerados, tempo médio

### 5 · Relatório
- Estado visual de cada etapa (Feito / Pendente)
- Exporta relatório em **HTML** (sem dependências extra)
- Exporta relatório em **PDF** (requer weasyprint)
- Pré-visualização do HTML gerado na própria janela


## Etapas da Pipeline de Limpeza

| Etapa | O que faz |

| Remoção de artefactos | Remove caracteres de controlo, bytes inválidos e caracteres zero-width |
| Normalização Unicode | Normaliza para forma NFC (consistência entre sistemas) |
| Correção de quebras de linha | Converte `\r\n`, `\r` e form-feeds para `\n` uniforme |
| Remoção de números de página | Elimina linhas que sejam apenas números de página |
| Deteção cabeçalhos/rodapés | Remove linhas repetidas em múltiplas páginas |
| Reconstrução de parágrafos | Re-une linhas partidas a meio de frase (comum em PDFs) |
| Normalização de pontuação | Converte aspas curvas, travessões e reticências para ASCII |
| Normalização de espaços | Colapsa múltiplos espaços e linhas em branco excessivas |

Cada etapa é independente e pode ser ligada/desligada na interface.


## Estratégias de Chunking

| Estratégia | Descrição |

| Tamanho fixo (512 chars) | Blocos de 512 caracteres com overlap de 50 |
| Tamanho fixo (1024 chars) | Blocos de 1024 caracteres com overlap de 100 |
| Por parágrafo | Agrupa parágrafos até 1024 chars |
| Por frase | Agrupa frases até 512 chars |



## Deteção de Idioma

Automática, sem dependências externas, por análise de trigramas.  
Suporta: 🇵🇹 Português · 🇬🇧 English · 🇪🇸 Español · 🇫🇷 Français

O idioma detetado é usado automaticamente para gerar os prompts no idioma correto.



## API SLM

**Endpoint:** `https://reality.utad.net/slm`  
**Método:** `POST`  
**Modelo:** `llama-3.2-1b-instruct`


{
  "model": "llama-3.2-1b-instruct",
  "messages": [
    { "role": "user", "content": "<PROMPT>" }
  ]
}

Retry automático: se a API falhar, o sistema tenta automaticamente até 3 vezes antes de desistir. A interface mostra em tempo real se a resposta veio à 1ª, 2ª ou 3ª tentativa, ou se houve erro.

## Relatório Gerado

O relatório inclui:
- Visão geral (chars originais, chars limpos, % redução, idioma)
- Parâmetros usados (estratégia de chunking, tipo de normalização)
- Tabela por etapa da pipeline (linhas antes/depois, Δ chars)
- Texto original vs texto limpo (primeiros 1500 chars de cada)
- Resultados da API: chunks enviados, tokens gerados, tempo médio
- Amostra do texto normalizado

## Grupo
Nome                                  Número
David Pinto                           al2025163203
Diogo Baptista                        al2025162057 
Tomás Cardona                         al2025162399


##  Licença

Projeto académico — UTAD 2025/26 · Laboratório de Programação