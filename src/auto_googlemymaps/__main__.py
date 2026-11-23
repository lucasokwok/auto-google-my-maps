"""CLI: validação local e autenticação; não executa reimportação nesta versão."""

from __future__ import annotations

import argparse
from pathlib import Path

from .configuracao import ErroConfiguracao, carregar_configuracao
from .csvs import validar_todos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Automação de camadas existentes no Google My Maps")
    parser.add_argument("acao", choices=("validar", "planejar", "login"))
    parser.add_argument("--config", default="config/mapas.json")
    parser.add_argument("--mapas-dir", default="MAPAS")
    parser.add_argument("--perfil-dir", default="runtime/chromium-profile")
    args = parser.parse_args(argv)

    if args.acao == "login":
        from .navegador import login_interativo
        login_interativo(Path(args.perfil_dir))
        return 0

    try:
        config = carregar_configuracao(Path(args.config))
    except ErroConfiguracao as exc:
        print(f"Configuração inválida: {exc}")
        return 2

    resultados = validar_todos(config, Path(args.mapas_dir))
    falhas = 0
    for resultado in resultados:
        estado = "OK" if resultado.valido else "ERRO"
        print(f"[{estado}] {resultado.nome} — {len(resultado.camadas)}/5 camada(s) localizadas")
        if args.acao == "planejar":
            for camada in resultado.camadas:
                print(f"  {camada.nome}: {camada.quantidade} registro(s)")
        for mensagem in resultado.erros:
            print(f"  - {mensagem}")
            falhas += 1
    print("Validação concluída. Nenhum mapa remoto foi modificado.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
