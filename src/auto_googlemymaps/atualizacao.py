"""Coordena as validações e atualizações de mapas independentes."""

from __future__ import annotations

from contextlib import ExitStack, suppress
from logging import Logger
from pathlib import Path
from time import sleep

from playwright.sync_api import BrowserContext, Error

from .configuracao import Configuracao, Mapa
from .csvs import ResultadoMapa, validar_mapa
from .mymaps import (
    ErroAtualizacaoRevertida,
    ErroMapa,
    ErroUploadTemporario,
    abrir_mapa,
    localizar_camada,
    reimportar_camada,
)
from .navegador import NAVEGADOR_PADRAO, ErroAutenticacao, abrir_navegador

_MAX_RETENTATIVAS_CAMADA = 5
_PAUSA_RETENTATIVA_SEGUNDOS = 2


def _atualizar_mapa(
    contexto: BrowserContext, mapa: Mapa, resultado: ResultadoMapa, coluna: str, log: Logger, *, arrastar_csv: bool,
    pausar_em_erro: bool = False,
) -> bool:
    pagina = contexto.new_page()
    operacao = "acesso ao editor"
    concluidas = 0
    total = len(resultado.camadas)

    def aguardar_inspecao(proximo_passo: str) -> None:
        if not pausar_em_erro or pagina.is_closed():
            return
        with suppress(Error):
            pagina.bring_to_front()
        try:
            input(
                f"{mapa.nome} — {operacao} — Inspecione o navegador. "
                f"Pressione Enter no terminal para {proximo_passo} ou Ctrl+C para interromper. "
            )
        except EOFError:
            log.warning("%s — %s — Terminal sem entrada disponível para a pausa.", mapa.nome, operacao)

    def registrar_falha(erro: ErroMapa | ErroAutenticacao, *, proximo_passo: str = "continuar") -> None:
        log.error(
            "%s — %s — %s (%d/%d camada(s) confirmada(s))",
            mapa.nome, operacao, erro, concluidas, total,
        )
        aguardar_inspecao(proximo_passo)

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
            repetiu_upload = False
            for tentativa in range(1, _MAX_RETENTATIVAS_CAMADA + 2):
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
                    retentativa = None
                    if tentativa <= _MAX_RETENTATIVAS_CAMADA:
                        if isinstance(erro, ErroAtualizacaoRevertida):
                            retentativa = f"Retentativa {tentativa}/{_MAX_RETENTATIVAS_CAMADA} após reversão"
                        elif isinstance(erro, ErroUploadTemporario) and not repetiu_upload:
                            repetiu_upload = True
                            retentativa = "Nova tentativa de upload"
                    if retentativa:
                        log.warning(
                            "%s — %s — %s %s em %d s%s.",
                            mapa.nome, operacao, erro, retentativa, _PAUSA_RETENTATIVA_SEGUNDOS,
                            " após a pausa de inspeção" if pausar_em_erro else "",
                        )
                        aguardar_inspecao("tentar novamente")
                        sleep(_PAUSA_RETENTATIVA_SEGUNDOS)
                        continue
                    registrar_falha(erro)
                else:
                    concluidas += 1
                    log.info("%s — %s — atualização confirmada pela interface", mapa.nome, operacao)
                break
    except ErroAutenticacao as erro:
        registrar_falha(erro, proximo_passo="encerrar a atualização")
        raise
    except ErroMapa as erro:
        registrar_falha(erro)
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
    arrastar_csv: bool = False, pausar_em_erro: bool = False,
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
                pausar_em_erro=pausar_em_erro,
            ):
                sucesso = False
    return sucesso
