"""Coordena as validações e atualizações de mapas independentes."""

from __future__ import annotations

from contextlib import ExitStack
from logging import Logger
from pathlib import Path
from time import sleep

from playwright.sync_api import BrowserContext

from .configuracao import Configuracao, Mapa
from .csvs import ResultadoMapa, validar_mapa
from .mymaps import ErroMapa, ErroUploadTemporario, abrir_mapa, localizar_camada, reimportar_camada
from .navegador import NAVEGADOR_PADRAO, ErroAutenticacao, abrir_navegador

_PAUSA_UPLOAD_SEGUNDOS = 2


def _atualizar_mapa(
    contexto: BrowserContext, mapa: Mapa, resultado: ResultadoMapa, coluna: str, log: Logger, *, arrastar_csv: bool,
) -> bool:
    pagina = contexto.new_page()
    operacao = "acesso ao editor"
    concluidas = 0
    total = len(resultado.camadas)

    def registrar_falha(erro: ErroMapa | ErroAutenticacao) -> None:
        log.error(
            "%s — %s — %s (%d/%d camada(s) confirmada(s))",
            mapa.nome, operacao, erro, concluidas, total,
        )

    log.info("%s — iniciando atualização de %d camada(s)", mapa.nome, total)
    try:
        abrir_mapa(pagina, mapa)
        remotas = []
        for camada in resultado.camadas:
            operacao = f"{camada.nome} — verificação da camada existente"
            try:
                remota = localizar_camada(pagina, camada.nome)
            except ErroMapa as erro:
                registrar_falha(erro)
                continue
            remotas.append((camada, remota))

        pagina_inicial = pagina
        reabrir_editor = False
        for camada, remota in remotas:
            operacao = camada.nome
            for tentativa in (1, 2):
                try:
                    if reabrir_editor:
                        pagina.close()
                        pagina = contexto.new_page()
                        abrir_mapa(pagina, mapa)
                        reabrir_editor = False
                    # Os seletores da checagem inicial apontam para a página original.
                    if pagina is not pagina_inicial:
                        remota = localizar_camada(pagina, camada.nome)
                    log.info("%s — %s — atualizando %d registro(s)", mapa.nome, operacao, camada.quantidade)
                    reimportar_camada(pagina, mapa, remota, camada, coluna, arrastar_csv=arrastar_csv)
                except ErroMapa as erro:
                    reabrir_editor = True
                    if tentativa == 1 and isinstance(erro, ErroUploadTemporario):
                        log.warning(
                            "%s — %s — %s Nova tentativa de upload em %d s.",
                            mapa.nome, operacao, erro, _PAUSA_UPLOAD_SEGUNDOS,
                        )
                        sleep(_PAUSA_UPLOAD_SEGUNDOS)
                        continue
                    registrar_falha(erro)
                else:
                    concluidas += 1
                    log.info("%s — %s — atualização confirmada pela interface", mapa.nome, operacao)
                break
    except (ErroMapa, ErroAutenticacao) as erro:
        registrar_falha(erro)
        if isinstance(erro, ErroAutenticacao):
            raise
        return False
    finally:
        pagina.close()

    if concluidas == total:
        log.info("%s — atualização concluída", mapa.nome)
        return True
    log.warning("%s — atualização encerrada com falhas (%d/%d camada(s) confirmada(s))", mapa.nome, concluidas, total)
    return False


def atualizar_mapas(
    config: Configuracao, raiz: Path, perfil: Path, log: Logger, *, navegador: str = NAVEGADOR_PADRAO,
    arrastar_csv: bool = False,
) -> bool:
    """Retorna se todos os mapas passaram pela validação e atualização."""
    sucesso = True
    contexto = None
    with ExitStack() as recursos:
        for mapa in config.mapas:
            resultado = validar_mapa(mapa, raiz, config.coluna_identificacao)
            if not resultado.valido:
                for erro in resultado.erros:
                    log.error("%s — atualização bloqueada: %s", mapa.nome, erro)
                sucesso = False
                continue

            if contexto is None:
                contexto = recursos.enter_context(abrir_navegador(perfil, navegador=navegador))
            if not _atualizar_mapa(
                contexto, mapa, resultado, config.coluna_identificacao, log, arrastar_csv=arrastar_csv,
            ):
                sucesso = False
    return sucesso
