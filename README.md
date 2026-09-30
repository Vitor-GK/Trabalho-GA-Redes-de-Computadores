# Trabalho GA — Sincronização de Arquivos Distribuídos em P2P (UDP)


## Integrantes

- Vitor Kockhann
- Gabriel Marcon

## Descrição

Sistema de atualização de arquivos distribuídos entre peers, implementado em Python
puro sobre sockets UDP. Cada peer monitora uma pasta local (`tmp`) e, ao detectar um
arquivo novo ou removido, avisa os demais peers da rede. O objetivo é manter a pasta
`tmp` de todos os peers sempre com o mesmo conjunto de arquivos.

A rede é estática: no sentido que cada peer conhece os outros por uma lista fixa de endereços
(`peers.json`), sem descoberta automática nem autenticação ou remoção/adição de peers de forma 
dinâmica, ou seja, durante a execução do programa.

## Protocolo

Mensagens de texto trocadas via UDP, no formato `TIPO|campo1|campo2|...`:

| Mensagem | Significado |
|---|---|
| `ANUNCIO nome tamanho` | um peer avisa que passou a ter um arquivo |
| `PEDIR nome` | solicita o conteúdo de um arquivo que ainda não se tem |
| `DADOS nome parte total conteudo` | envio do conteúdo (em base64, fatiado por causa do limite do datagrama) |
| `REMOVIDO nome` | avisa que um arquivo foi apagado |
| `LISTA` | pede o conjunto atual de arquivos (usado por um peer novo ao entrar na rede) |
| `CONFIRMA tipo nome` | confirma recebimento de um ANUNCIO/REMOVIDO |

Como o UDP não garante entrega, ANUNCIO, REMOVIDO e PEDIR são retransmitidos até
receber confirmação ou até chegar no número máximo de tentativas.

## Estrutura do código

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | loop principal, tratador de mensagens, retransmissão/confirmação |
| `config.py` | leitura do `peers.json`, ID do peer, constantes |
| `network.py` | socket UDP, envio e escuta de mensagens |
| `protocol.py` | codificação/decodificação das mensagens |
| `state.py` | estado da rede (quais arquivos cada peer tem, quem está ativo) |
| `file_manager.py` | leitura, fatiamento, gravação e remoção de arquivos |
| `file_watcher.py` | monitoramento da pasta `tmp` |
| `status_view.py` | exibição do comando `status` |

## Como executar

Requisitos: Python 3, sem dependências externas.

1. Edite `peers.json` com o ID, host e porta de cada peer da rede:
```json
   [
     {"id": "A", "host": "192.168.0.10", "porta": 5000},
     {"id": "B", "host": "192.168.0.11", "porta": 5000},
     {"id": "C", "host": "192.168.0.12", "porta": 5000}
   ]
```
2. Copie o projeto (com o mesmo `peers.json`) para cada máquina/VM que vai rodar um peer.

3. Em cada máquina, rode:

   python3 main.py <ID_DO_PEER>

   Exemplo: `python3 main.py A`

   Sendo a Letra do comando (A, B, C...) correspondente
   ao ip da máquina em questão e ao que está no peers.json

4. Digite `status` a qualquer momento para ver o estado da rede, ou `sair` para encerrar.


5. Coloque ou apague arquivos na pasta `tmp` do peer — a mudança se propaga
   automaticamente para os demais peers ativos.

Para testar na mesma máquina, use `127.0.0.1` com portas diferentes para cada peer.

## Ambientes testados

Testado com peers rodando em máquinas virtuais distintas (VirtualBox), simulando
peers em redes/hosts diferentes.