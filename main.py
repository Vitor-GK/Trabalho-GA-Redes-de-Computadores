import os
import time
import threading

import config
import protocol
import network
import file_manager
import file_watcher
import status_view
from state import state as estado_rede

_eventos_confirmacao = {}
_eventos_lock = threading.Lock()

_pedidos_em_andamento = set()
_pedidos_lock = threading.Lock()


def enviar_arquivo(sock, nome, endereco_destino):
    pedacos = file_manager.ler_e_fatiar(nome)
    if not pedacos:
        pedacos = [(0, b"")]
    total = len(pedacos)
    for indice, conteudo in pedacos:
        mensagem = protocol.codifica_dados(nome, indice, total, conteudo)
        network.envia(sock, mensagem, endereco_destino)


def _pede_com_retentativas(sock, nome, endereco):
    try:
        for tentativa in range(1, config.MAX_TENTATIVAS + 1):
            network.envia(sock, protocol.codifica_pedir(nome), endereco)
            time.sleep(config.TIMEOUT_RETRANSMISSAO)
            if os.path.exists(file_manager.caminho(nome)):
                return
        print(f"[!] nao foi possivel obter '{nome}' de {endereco} apos {config.MAX_TENTATIVAS} tentativas")
    finally:
        with _pedidos_lock:
            _pedidos_em_andamento.discard(nome)


def _anuncia_ou_remove_com_confirmacao(sock, tipo, nome, peer, monta_mensagem, tamanho=None):
    endereco = (peer["host"], peer["porta"])
    chave = (peer["id"], tipo, nome)
    evento = threading.Event()
    with _eventos_lock:
        _eventos_confirmacao[chave] = evento
    try:
        for tentativa in range(1, config.MAX_TENTATIVAS + 1):
            network.envia(sock, monta_mensagem(), endereco)
            if evento.wait(timeout=config.TIMEOUT_RETRANSMISSAO):
                if tipo == protocol.ANUNCIO and tamanho is not None:
                    estado_rede.atualizar_arquivo(peer["id"], nome, tamanho)
                elif tipo == protocol.REMOVIDO:
                    estado_rede.remover_arquivo(peer["id"], nome)
                return
        print(f"[!] peer {peer['id']} nao confirmou '{tipo} {nome}' apos {config.MAX_TENTATIVAS} tentativas")
    finally:
        with _eventos_lock:
            _eventos_confirmacao.pop(chave, None)


def _transmite_com_confirmacao(sock, tipo, nome, peers_destino, monta_mensagem, tamanho=None):
    for peer in peers_destino:
        threading.Thread(
            target=_anuncia_ou_remove_com_confirmacao,
            args=(sock, tipo, nome, peer, monta_mensagem, tamanho),
            daemon=True,
        ).start()


def cria_tratador(sock, peers, meu_id):
    def trata_mensagem(dados, endereco):
        tipo, campos = protocol.decodifica(dados)
        peer_id = network.identifica_peer(endereco, peers)
        if peer_id is not None:
            estado_rede.marcar_visto(peer_id)

        if tipo == protocol.ANUNCIO:
            nome, tamanho = campos["nome"], campos["tamanho"]
            if peer_id is not None:
                estado_rede.atualizar_arquivo(peer_id, nome, tamanho)
            network.envia(sock, protocol.codifica_confirma(protocol.ANUNCIO, nome), endereco)
            if not os.path.exists(file_manager.caminho(nome)):
                with _pedidos_lock:
                    ja_buscando = nome in _pedidos_em_andamento
                    if not ja_buscando:
                        _pedidos_em_andamento.add(nome)
                if not ja_buscando:
                    threading.Thread(
                        target=_pede_com_retentativas, args=(sock, nome, endereco), daemon=True
                    ).start()

        elif tipo == protocol.PEDIR:
            nome = campos["nome"]
            if os.path.exists(file_manager.caminho(nome)):
                enviar_arquivo(sock, nome, endereco)

        elif tipo == protocol.DADOS:
            nome, parte, total = campos["nome"], campos["parte"], campos["total"]
            file_manager.receber_pedaco(nome, parte, campos["conteudo"])
            if file_manager.arquivo_completo(nome, total):
                file_watcher.marcar_para_ignorar(nome)
                file_manager.salvar_arquivo(nome)
                estado_rede.atualizar_arquivo(meu_id, nome, file_manager.tamanho_arquivo(nome))
                print(f"[+] arquivo '{nome}' recebido de {peer_id or endereco}")

        elif tipo == protocol.REMOVIDO:
            nome = campos["nome"]
            network.envia(sock, protocol.codifica_confirma(protocol.REMOVIDO, nome), endereco)
            file_watcher.marcar_para_ignorar(nome)
            file_manager.apagar_arquivo(nome)
            if peer_id is not None:
                estado_rede.remover_arquivo(peer_id, nome)
            estado_rede.remover_arquivo(meu_id, nome)

        elif tipo == protocol.LISTA:
            for nome in file_manager.lista_arquivos():
                tamanho = file_manager.tamanho_arquivo(nome)
                network.envia(sock, protocol.codifica_anuncio(nome, tamanho), endereco)

        elif tipo == protocol.CONFIRMA:
            if peer_id is not None:
                chave = (peer_id, campos["tipo_confirmado"], campos["nome"])
                with _eventos_lock:
                    evento = _eventos_confirmacao.get(chave)
                if evento is not None:
                    evento.set()

    return trata_mensagem


def main():
    meu_id = config.obtem_meu_id()
    peers = config.carrega_peers()
    _, minha_porta = config.obtem_meu_endereco(meu_id, peers)
    outros_peers = config.obtem_outros_peers(meu_id, peers)

    sock = network.cria_socket(minha_porta)
    print(f"[peer {meu_id}] escutando na porta {minha_porta}")

    network.inicia_escuta(sock, cria_tratador(sock, peers, meu_id))

    estado_rede.registrar_peer(meu_id)
    estado_rede.marcar_visto(meu_id)
    for nome in file_manager.lista_arquivos():
        estado_rede.atualizar_arquivo(meu_id, nome, file_manager.tamanho_arquivo(nome))

    def on_arquivo_adicionado(nome):
        tamanho = file_manager.tamanho_arquivo(nome)
        estado_rede.atualizar_arquivo(meu_id, nome, tamanho)
        _transmite_com_confirmacao(
            sock, protocol.ANUNCIO, nome, outros_peers,
            lambda: protocol.codifica_anuncio(nome, tamanho),
            tamanho=tamanho,
        )

    def on_arquivo_removido(nome):
        estado_rede.remover_arquivo(meu_id, nome)
        _transmite_com_confirmacao(
            sock, protocol.REMOVIDO, nome, outros_peers,
            lambda: protocol.codifica_removido(nome),
        )

    def _monitor_inatividade():
        while True:
            time.sleep(3)
            estado_rede.marcar_visto(meu_id)
            estado_rede.marcar_inativos(timeout_segundos=8)

    threading.Thread(target=_monitor_inatividade, daemon=True).start()

    file_watcher.inicia_watcher(config.PASTA_TMP, on_arquivo_adicionado, on_arquivo_removido)

    network.transmite(sock, protocol.codifica_lista(), outros_peers)
    print(f"[peer {meu_id}] pedindo sincronizacao inicial...")

    print("Digite 'status' para ver o estado da rede, ou 'sair' para encerrar.")
    while True:
        comando = input("> ").strip().lower()
        if comando == "status":
            status_view.imprimir_status()
        elif comando == "sair":
            break

    sock.close()


if __name__ == "__main__":
    main()