import threading
import time


class NetworkState:
    def __init__(self):
        self._lock = threading.Lock()
        self._peers = {}

    def registrar_peer(self, peer_id):
        with self._lock:
            self._peers.setdefault(peer_id, {
                "ativo": False,
                "ultima_vez_visto": 0.0,
                "arquivos": {},
            })

    def atualizar_arquivo(self, peer_id, nome, tamanho):
         with self._lock:
            self._peers.setdefault(peer_id, {"ativo": True, "ultima_vez_visto": time.time(), "arquivos": {}})
            self._peers[peer_id]["arquivos"][nome] = tamanho
            self._peers[peer_id]["ativo"] = True
            self._peers[peer_id]["ultima_vez_visto"] = time.time()

    def remover_arquivo(self, peer_id, nome):
        with self._lock:
            peer = self._peers.get(peer_id)
            if peer and nome in peer["arquivos"]:
                del peer["arquivos"][nome]

    def marcar_visto(self, peer_id):
        with self._lock:
            self._peers.setdefault(peer_id, {"ativo": True, "ultima_vez_visto": 0.0, "arquivos": {}})
            self._peers[peer_id]["ativo"] = True
            self._peers[peer_id]["ultima_vez_visto"] = time.time()

    def marcar_inativos(self, timeout_segundos):
        agora = time.time()
        with self._lock:
            for peer in self._peers.values():
                if agora - peer["ultima_vez_visto"] > timeout_segundos:
                    peer["ativo"] = False

    def obter_estado(self):
        with self._lock:
            return {
                peer_id: {
                    "ativo": info["ativo"],
                    "arquivos": dict(info["arquivos"]),
                }
                for peer_id, info in self._peers.items()
            }

    def meus_arquivos_locais(self):
        raise NotImplementedError("Defina como identificar o peer local (ver config.py do grupo)")
state = NetworkState()