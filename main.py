import config
import protocol
import network
import file_manager
import state
import file_watcher
import status_view


def enviar_arquivo(sock, nome, endereco_destino):
    conteudo = file_manager.obtem_conteudo(nome) 
    tamanho_pedaco = config.TAMANHO_PEDACO 
    pedacos = [conteudo[i:i + tamanho_pedaco] for i in range(0, len(conteudo), tamanho_pedaco)]
    if not pedacos:
        pedacos = [b""]  
    total = len(pedacos)
    for i, pedaco in enumerate(pedacos, start=1):
        mensagem = protocol.codifica_dados(nome, i, total, pedaco)
        network.envia(sock, mensagem, endereco_destino)


def cria_tratador(sock, peers):

    def trata_mensagem(dados, endereco):
        tipo, campos = protocol.decodifica(dados)
        peer_id = network.identifica_peer(endereco, peers)
        if peer_id is not None:
            state.marca_ativo(peer_id)

        if tipo == protocol.ANUNCIO:
            nome = campos["nome"]
            if peer_id is not None:
                state.adiciona_arquivo(peer_id, nome)
            if nome not in file_manager.lista_arquivos():
                network.envia(sock, protocol.codifica_pedir(nome), endereco)

        elif tipo == protocol.PEDIR:
            nome = campos["nome"]
            if nome in file_manager.lista_arquivos():
                enviar_arquivo(sock, nome, endereco)

        elif tipo == protocol.DADOS:
            nome, parte, total = campos["nome"], campos["parte"], campos["total"]
            completo = file_manager.salva_pedaco(nome, parte, total, campos["conteudo"])
            if completo:
                print(f"[+] arquivo '{nome}' recebido de {peer_id or endereco}")

        elif tipo == protocol.REMOVIDO:
            nome = campos["nome"]
            if peer_id is not None:
                state.remove_arquivo(peer_id, nome)
            file_manager.remove_arquivo(nome)

        elif tipo == protocol.LISTA:
            for nome in file_manager.lista_arquivos():
                tamanho = file_manager.tamanho_arquivo(nome)
                network.envia(sock, protocol.codifica_anuncio(nome, tamanho), endereco)

    return trata_mensagem


def main():
    meu_id = config.obtem_meu_id()
    peers = config.carrega_peers()
    meu_host, minha_porta = config.obtem_meu_endereco(meu_id, peers)
    outros_peers = config.obtem_outros_peers(meu_id, peers)

    sock = network.cria_socket(minha_porta)
    print(f"[peer {meu_id}] escutando na porta {minha_porta}")

    tratador = cria_tratador(sock, peers)
    network.inicia_escuta(sock, tratador)

    def on_arquivo_adicionado(nome):
        tamanho = file_manager.tamanho_arquivo(nome)
        network.transmite(sock, protocol.codifica_anuncio(nome, tamanho), outros_peers)
        print(f"[+] anunciando '{nome}' para os outros peers")

    def on_arquivo_removido(nome):
        network.transmite(sock, protocol.codifica_removido(nome), outros_peers)
        print(f"[-] avisando remocao de '{nome}'")

    file_watcher.inicia_watcher(config.PASTA_TMP, on_arquivo_adicionado, on_arquivo_removido)

    network.transmite(sock, protocol.codifica_lista(), outros_peers)
    print(f"[peer {meu_id}] pedindo sincronizacao inicial aos outros peers...")

    print("Digite 'status' para ver o estado da rede, ou 'sair' para encerrar.")
    while True:
        comando = input("> ").strip().lower()
        if comando == "status":
            status_view.mostra()
        elif comando == "sair":
            break

    sock.close()


if __name__ == "__main__":
    main()