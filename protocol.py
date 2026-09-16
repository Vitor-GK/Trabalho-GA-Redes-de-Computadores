import base64

ANUNCIO = "ANUNCIO"
PEDIR = "PEDIR"
DADOS = "DADOS"
REMOVIDO = "REMOVIDO"
LISTA = "LISTA"

SEPARADOR = "|"


def codifica_anuncio(nome, tamanho):
    return f"{ANUNCIO}{SEPARADOR}{nome}{SEPARADOR}{tamanho}".encode("utf-8")


def codifica_pedir(nome):
    return f"{PEDIR}{SEPARADOR}{nome}".encode("utf-8")


def codifica_dados(nome, parte, total, conteudo_bytes):
    conteudo_b64 = base64.b64encode(conteudo_bytes).decode("ascii")
    return f"{DADOS}{SEPARADOR}{nome}{SEPARADOR}{parte}{SEPARADOR}{total}{SEPARADOR}{conteudo_b64}".encode("utf-8")


def codifica_removido(nome):
    return f"{REMOVIDO}{SEPARADOR}{nome}".encode("utf-8")


def codifica_lista():
    return LISTA.encode("utf-8")


def decodifica(dados_recebidos):
    texto = dados_recebidos.decode("utf-8")
    campos = texto.split(SEPARADOR)
    tipo = campos[0]

    if tipo == ANUNCIO:
        _, nome, tamanho = campos
        return tipo, {"nome": nome, "tamanho": int(tamanho)}

    if tipo == PEDIR:
        _, nome = campos
        return tipo, {"nome": nome}

    if tipo == DADOS:
        _, nome, parte, total, conteudo_b64 = campos
        conteudo = base64.b64decode(conteudo_b64)
        return tipo, {"nome": nome, "parte": int(parte), "total": int(total), "conteudo": conteudo}

    if tipo == REMOVIDO:
        _, nome = campos
        return tipo, {"nome": nome}

    if tipo == LISTA:
        return tipo, {}

    raise ValueError(f"mensagem desconhecida: {texto}")