"""
api_client.py
Tarefa 4 – Ligação à API do SLM
Endpoint: https://reality.utad.net/slm
Modelo: llama-3.2-1b-instruct
Retry automático até 3 tentativas por chunk.
"""

import json
import time
import urllib.request
import urllib.error


API_URL   = "https://reality.utad.net/slm"
API_MODEL = "llama-3.2-1b-instruct"


def chamar_api(prompt: str, timeout: int = 60, max_tentativas: int = 3) -> dict:
    """
    Envia um prompt à API da UTAD e devolve a resposta.

    Formato do pedido (OpenAI-compatible):
    {
        "model": "llama-3.2-1b-instruct",
        "messages": [{"role": "user", "content": "<PROMPT>"}]
    }

    Retry automático:
    - Se falhar, tenta novamente até max_tentativas vezes
    - Aguarda 2 segundos entre tentativas
    - Devolve sucesso=False apenas se todas as tentativas falharem

    Devolve dicionário com:
    - sucesso, conteudo, tokens_prompt, tokens_resposta, tempo, tentativas, erro
    """
    payload = {
        "model": API_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    corpo = json.dumps(payload).encode("utf-8")

    ultimo_erro = ""
    inicio_total = time.time()

    for tentativa in range(1, max_tentativas + 1):
        pedido = urllib.request.Request(
            API_URL,
            data=corpo,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=timeout) as resp:
                dados = json.loads(resp.read().decode("utf-8"))

            # extrai o texto da resposta (formato OpenAI)
            conteudo = ""
            if "choices" in dados and dados["choices"]:
                conteudo = dados["choices"][0].get("message", {}).get("content", "")
            elif "message" in dados:
                conteudo = dados["message"].get("content", "")

            uso = dados.get("usage", {})
            return {
                "sucesso":         True,
                "conteudo":        conteudo,
                "tokens_prompt":   uso.get("prompt_tokens", 0),
                "tokens_resposta": uso.get("completion_tokens", 0),
                "tempo":           round(time.time() - inicio_total, 2),
                "tentativas":      tentativa,
                "erro":            None,
            }

        except urllib.error.HTTPError as e:
            ultimo_erro = f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            ultimo_erro = str(e)

        # espera antes de tentar de novo (exceto na última tentativa)
        if tentativa < max_tentativas:
            time.sleep(2)

    return {
        "sucesso":         False,
        "conteudo":        "",
        "tokens_prompt":   0,
        "tokens_resposta": 0,
        "tempo":           round(time.time() - inicio_total, 2),
        "tentativas":      max_tentativas,
        "erro":            f"Falhou após {max_tentativas} tentativas. Último erro: {ultimo_erro}",
    }