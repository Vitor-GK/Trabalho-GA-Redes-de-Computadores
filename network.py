import socket
import threading


def cria_socket(porta):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", porta))
    return sock


def envia(sock, mensagem_bytes, endereco_destino):
    try:
        sock.sendto(mensagem_bytes, endereco_destino)
    except OSError as e:
        print(f"[erro ao enviar para {endereco_destino}]: {e}")


def transmite(sock, mensagem_bytes, peers_destino):
    for peer in peers_destino:
        envia(sock, mensagem_bytes, (peer["host"], peer["porta"]))


def escuta(sock, callback):
    while True:
        try:
            dados, endereco = sock.recvfrom(65536)
        except OSError:
            return 
        callback(dados, endereco)


def inicia_escuta(sock, callback):
    t = threading.Thread(target=escuta, args=(sock, callback), daemon=True)
    t.start()
    return t


def identifica_peer(endereco_remetente, peers):
    ip, porta = endereco_remetente
    for p in peers:
        if p["host"] == ip and p["porta"] == porta:
            return p["id"]
    return None  