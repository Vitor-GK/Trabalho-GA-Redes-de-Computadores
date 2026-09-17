import os

import config
import protocol
import network
import file_manager
import file_watcher
import status_view
from state import state as estado_rede


def enviar_arquivo(sock, nome, endereco_destino):
    pedacos = file_manager.ler_e_fatiar(nome)
    if not pedacos:
        pedacos = [(0, b"")] 
    total = len(pedacos)
    for indice, conteudo in pedacos:
        mensagem = protocol.codifica_dados(nome, indice, total, conteudo)
        network.envia(sock, mensagem, endereco_destino)


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
            if not os.path.exists(file_manager.caminho(nome)):
                network.envia(sock, protocol.codifica_pedir(nome), endereco)

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
            file_watcher.marcar_para_ignorar(nome)
            file_manager.apagar_arquivo(nome)
            if peer_id is not None:
                estado_rede.remover_arquivo(peer_id, nome)
            estado_rede.remover_arquivo(meu_id, nome)

        elif tipo == protocol.LISTA:
            for nome in file_manager.lista_arquivos():
                tamanho = file_manager.tamanho_arquivo(nome)
                network.envia(sock, protocol.codifica_anuncio(nome, tamanho), endereco)

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
        network.transmite(sock, protocol.codifica_anuncio(nome, tamanho), outros_peers)

    def on_arquivo_removido(nome):
        estado_rede.remover_arquivo(meu_id, nome)
        network.transmite(sock, protocol.codifica_removido(nome), outros_peers)

    def _monitor_inatividade():
        import time
        while True:
            time.sleep(3)
            estado_rede.marcar_visto(meu_id)
            estado_rede.marcar_inativos(timeout_segundos=8)

    import threading
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