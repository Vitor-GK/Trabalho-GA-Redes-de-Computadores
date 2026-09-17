import os
import threading
import time

from config import PASTA_TMP as TMP_DIR

INTERVALO_VERIFICACAO = 2.0

_ignorar_proxima_varredura = set()
_ignorar_lock = threading.Lock()


def marcar_para_ignorar(nome_arquivo):
    with _ignorar_lock:
        _ignorar_proxima_varredura.add(nome_arquivo)


def _consumir_ignorados():
    with _ignorar_lock:
        ignorados = set(_ignorar_proxima_varredura)
        _ignorar_proxima_varredura.clear()
    return ignorados


class FileWatcher:
    def __init__(self, on_arquivo_adicionado, on_arquivo_removido):
        self._on_adicionado = on_arquivo_adicionado
        self._on_removido = on_arquivo_removido
        self._rodando = False
        self._thread = None
        self._estado_anterior = set()

    def _listar_arquivos(self):
        os.makedirs(TMP_DIR, exist_ok=True)
        return set(os.listdir(TMP_DIR))

    def iniciar(self):
        self._estado_anterior = self._listar_arquivos()
        self._rodando = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self._rodando = False
        if self._thread:
            self._thread.join(timeout=INTERVALO_VERIFICACAO + 1)

    def _loop(self):
        while self._rodando:
            time.sleep(INTERVALO_VERIFICACAO)
            atual = self._listar_arquivos()
            ignorados = _consumir_ignorados()

            adicionados = (atual - self._estado_anterior) - ignorados
            removidos = (self._estado_anterior - atual) - ignorados

            for nome in adicionados:
                self._on_adicionado(nome)

            for nome in removidos:
                self._on_removido(nome)

            self._estado_anterior = atual


def inicia_watcher(pasta, on_arquivo_adicionado, on_arquivo_removido):
    """Cria e inicia um FileWatcher, devolvendo o objeto (para poder chamar .parar() depois)."""
    watcher = FileWatcher(on_arquivo_adicionado, on_arquivo_removido)
    watcher.iniciar()
    return watcher