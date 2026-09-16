import json
import os
import sys

PASTA_TMP = "tmp"
TAMANHO_PEDACO = 1000        
TIMEOUT_RETRANSMISSAO = 2.0  
MAX_TENTATIVAS = 5


def carrega_peers(caminho="peers.json"):
    if not os.path.exists(caminho):
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), caminho)
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def obtem_meu_id():
    if len(sys.argv) < 2:
        print("uso: python main.py <ID_DO_PEER>   (ex.: python main.py A)")
        sys.exit(1)
    return sys.argv[1]


def obtem_meu_endereco(meu_id, peers):
    for p in peers:
        if p["id"] == meu_id:
            return p["host"], p["porta"]
    raise ValueError(f"id de peer desconhecido: {meu_id}")


def obtem_outros_peers(meu_id, peers):
    return [p for p in peers if p["id"] != meu_id]