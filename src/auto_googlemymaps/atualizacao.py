"""Coordena as validações e atualizações de mapas independentes."""

from __future__ import annotations

from contextlib import ExitStack
from logging import Logger
from pathlib import Path

from playwright.sync_api import BrowserContext

from .configuracao import Configuracao, Mapa
from .csvs import ResultadoMapa, validar_mapa
from .mymaps import ErroMapa, abrir_mapa, localizar_camada, reimportar_camada
from .navegador import NAVEGADOR_PADRAO, ErroAutenticacao, abrir_navegador


def _atualizar_mapa(
    contexto: BrowserContext, mapa: Mapa, resultado: ResultadoMapa, coluna: str, log: Logger,
) -> bool:
    pagina = contexto.new_page()
    operacao = "acesso ao editor"
    concluidas = 0
    log.info("%s — iniciando atualização de %d camada(s)", mapa.nome, len(resultado.camadas))
    try:
        abrir_mapa(pagina, mapa)
        remotas = []
        for camada in resultado.camadas:
            operacao = f"{camada.nome} — verificação da camada existente"
            remotas.append(localizar_camada(pagina, camada.nome))

        for camada, remota in zip(resultado.camadas, remotas):
            operacao = camada.nome
            log.info("%s — %s — atualizando %d registro(s)", mapa.nome, operacao, camada.quantidade)
            reimportar_camada(pagina, mapa, remota, camada, coluna)
            concluidas += 1
            log.info("%s — %s — atualização confirmada pela interface", mapa.nome, operacao)
    except (ErroMapa, ErroAutenticacao) as erro:
        log.error(
            "%s — %s — %s (%d/%d camada(s) confirmada(s))",
            mapa.nome, operacao, erro, concluidas, len(resultado.camadas),
        )
        if isinstance(erro, ErroAutenticacao):
            raise
        return False
    finally:
        pagina.close()

    log.info("%s — atualização concluída", mapa.nome)
    return True


def atualizar_mapas(
    config: Configuracao, raiz: Path, perfil: Path, log: Logger, *, navegador: str = NAVEGADOR_PADRAO,
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
            if not _atualizar_mapa(contexto, mapa, resultado, config.coluna_identificacao, log):
                sucesso = False
    return sucesso
