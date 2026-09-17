import os

from config import PASTA_TMP as TMP_DIR, TAMANHO_PEDACO as CHUNK_SIZE

_buffers_recebendo = {}


def caminho(nome_arquivo):
    return os.path.join(TMP_DIR, nome_arquivo)


def ler_e_fatiar(nome_arquivo):
    """Lê um arquivo da TMP_DIR e retorna lista de (indice, conteudo_bytes)."""
    with open(caminho(nome_arquivo), "rb") as f:
        conteudo = f.read()

    pedacos = []
    for indice, inicio in enumerate(range(0, len(conteudo), CHUNK_SIZE)):
        pedacos.append((indice, conteudo[inicio:inicio + CHUNK_SIZE]))
    return pedacos


def tamanho_arquivo(nome_arquivo):
    return os.path.getsize(caminho(nome_arquivo))


def receber_pedaco(nome_arquivo, indice, conteudo_bytes):
    _buffers_recebendo.setdefault(nome_arquivo, {})
    _buffers_recebendo[nome_arquivo][indice] = conteudo_bytes


def arquivo_completo(nome_arquivo, total_partes_esperadas):
    partes = _buffers_recebendo.get(nome_arquivo, {})
    return len(partes) >= total_partes_esperadas and all(
        i in partes for i in range(total_partes_esperadas)
    )


def salvar_arquivo(nome_arquivo):
    partes = _buffers_recebendo.pop(nome_arquivo, {})
    conteudo = b"".join(partes[i] for i in sorted(partes.keys()))

    os.makedirs(TMP_DIR, exist_ok=True)
    with open(caminho(nome_arquivo), "wb") as f:
        f.write(conteudo)


def apagar_arquivo(nome_arquivo):
    try:
        os.remove(caminho(nome_arquivo))
    except FileNotFoundError:
        pass


def lista_arquivos():
    """Retorna a lista de nomes de arquivos atualmente na pasta TMP_DIR."""
    os.makedirs(TMP_DIR, exist_ok=True)
    return [nome for nome in os.listdir(TMP_DIR) if os.path.isfile(caminho(nome))]