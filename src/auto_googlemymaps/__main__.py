"""CLI para validação, login e atualização de camadas existentes."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from .configuracao import Configuracao, ErroConfiguracao, carregar_configuracao
from .csvs import validar_todos
from .navegador import NAVEGADOR_PADRAO, PERFIS_PADRAO, ErroNavegador, login_interativo


def _executar_atualizacao(
    config: Configuracao, raiz: Path, perfil: Path, navegador: str, *, arrastar_csv: bool,
) -> int:
    caminho_log = Path("logs/atualizacao.log")
    try:
        caminho_log.parent.mkdir(parents=True, exist_ok=True)
        arquivo = logging.FileHandler(caminho_log, encoding="utf-8")
    except OSError:
        print("Não foi possível abrir logs/atualizacao.log. Confira as permissões locais.")
        return 2

    try:
        log = logging.Logger("auto_googlemymaps", level=logging.INFO)
        formato = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        for handler in (arquivo, logging.StreamHandler()):
            handler.setFormatter(formato)
            log.addHandler(handler)
        try:
            from .atualizacao import atualizar_mapas
        except ModuleNotFoundError as erro:
            if erro.name not in {"playwright", "playwright.sync_api"}:
                raise
            log.error('Instale o Playwright com python -m pip install -e ".[browser]".')
            return 1
        try:
            atualizado = atualizar_mapas(config, raiz, perfil, log, navegador=navegador, arrastar_csv=arrastar_csv)
            return 0 if atualizado else 1
        except ErroNavegador as erro:
            log.error("Atualização interrompida — %s", erro)
            return 1
        except KeyboardInterrupt:
            log.error("Atualização interrompida pelo usuário. Confira a camada em processamento antes de repetir.")
            return 130
    finally:
        arquivo.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Automação de camadas existentes no Google My Maps")
    parser.add_argument("acao", choices=("validar", "planejar", "login", "atualizar"))
    parser.add_argument("--config", default="config/mapas.json")
    parser.add_argument("--mapas-dir", default="MAPAS")
    parser.add_argument(
        "--navegador", choices=PERFIS_PADRAO, default=NAVEGADOR_PADRAO,
        help="navegador para login e atualizar (padrão: chromium)",
    )
    parser.add_argument("--perfil-dir", help="diretório do perfil persistente (padrão conforme o navegador)")
    parser.add_argument("--mapa", help="NomeMapa exato para atualizar apenas um mapa")
    parser.add_argument(
        "--arrastar-csv", action="store_true", help="usar a área de arrastar e soltar do seletor de upload",
    )
    args = parser.parse_args(argv)

    if args.mapa is not None and args.acao != "atualizar":
        parser.error("--mapa está disponível com atualizar")
    if args.arrastar_csv and args.acao != "atualizar":
        parser.error("--arrastar-csv está disponível com atualizar")

    perfil = Path(args.perfil_dir if args.perfil_dir is not None else PERFIS_PADRAO[args.navegador])
    if args.acao == "login":
        try:
            login_interativo(perfil, navegador=args.navegador)
        except ErroNavegador as erro:
            print(f"Login não confirmado — {erro}")
            return 1
        except KeyboardInterrupt:
            print("Login interrompido pelo usuário.")
            return 130
        print("Login Google confirmado. Perfil salvo localmente.")
        return 0

    try:
        config = carregar_configuracao(Path(args.config))
        if args.mapa is not None:
            mapas = tuple(mapa for mapa in config.mapas if mapa.nome == args.mapa)
            if not mapas:
                raise ErroConfiguracao("O NomeMapa solicitado não está cadastrado.")
            config = replace(config, mapas=mapas)
    except ErroConfiguracao as erro:
        print(f"Configuração inválida — {erro}")
        return 2

    raiz = Path(args.mapas_dir)
    if args.acao == "atualizar":
        return _executar_atualizacao(config, raiz, perfil, args.navegador, arrastar_csv=args.arrastar_csv)

    falhas = False
    for resultado in validar_todos(config, raiz):
        estado = "OK" if resultado.valido else "ERRO"
        print(f"[{estado}] {resultado.nome} — {len(resultado.camadas)} camada(s) válida(s)")
        if args.acao == "planejar":
            for camada in resultado.camadas:
                print(f"  {camada.nome} — {camada.quantidade} registro(s)")
        for mensagem in resultado.erros:
            print(f"  - {mensagem}")
        if not resultado.valido:
            falhas = True
    print("Validação local concluída.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
