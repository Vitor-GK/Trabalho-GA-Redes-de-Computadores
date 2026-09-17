# TODO: importar a instância compartilhada de state.py do grupo
from state import state


def imprimir_status():
    dados = state.obter_estado()

    print("Estado da rede:")
    if not dados:
        print("(nenhum peer registrado ainda)")
        return

    for peer_id in sorted(dados.keys()):
        info = dados[peer_id]
        situacao = "ATIVO" if info["ativo"] else "INATIVO"
        arquivos = info["arquivos"]
        nomes = ", ".join(sorted(arquivos.keys())) if arquivos else "(nenhum)"
        print(f"{peer_id} [{situacao}] — {len(arquivos)} arquivo(s): {nomes}")


def monitorar_em_loop(intervalo_segundos=5):
    import threading
    import time

    def _loop():
        while True:
            imprimir_status()
            time.sleep(intervalo_segundos)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    # Permite rodar `python status_view.py` isoladamente para testar a
    # formatação com dados fake, sem depender do resto do sistema.
    from state import NetworkState

    fake = NetworkState()
    fake.atualizar_arquivo("peer_A", "relatorio.pdf", 20480)
    fake.atualizar_arquivo("peer_A", "foto.jpg", 10240)
    fake.atualizar_arquivo("peer_B", "relatorio.pdf", 20480)
    fake.registrar_peer("peer_C")

    state = fake  # sobrescreve só para este teste manual
    imprimir_status()