"""Validação não destrutiva dos cinco CSVs de cada mapa."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from .configuracao import Configuracao, Mapa

CAMADAS = tuple(f"pontos_{numero:02d}.csv" for numero in range(1, 6))
MAX_REGISTROS = 2000


@dataclass(frozen=True)
class Camada:
    nome: str
    quantidade: int


@dataclass(frozen=True)
class ResultadoMapa:
    nome: str
    camadas: tuple[Camada, ...]
    erros: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return not self.erros


def _coord(texto: object, limite: int) -> bool:
    try:
        valor = float(texto)
    except (TypeError, ValueError):
        return False
    return math.isfinite(valor) and -limite <= valor <= limite


def validar_mapa(mapa: Mapa, raiz: Path, coluna_identificacao: str) -> ResultadoMapa:
    raiz = Path(raiz)
    pasta = raiz / mapa.nome
    erros: list[str] = []
    camadas: list[Camada] = []
    identificadores: set[str] = set()

    if not pasta.is_dir():
        return ResultadoMapa(mapa.nome, (), ("pasta do mapa ausente",))

    for nome in CAMADAS:
        arquivo = pasta / nome
        if not arquivo.is_file():
            erros.append(f"{nome}: arquivo obrigatório ausente")
            continue
        try:
            with arquivo.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                cabecalhos = reader.fieldnames or []
                if not cabecalhos or len(cabecalhos) != len(set(cabecalhos)):
                    erros.append(f"{nome}: cabeçalho ausente ou duplicado")
                    continue
                obrigatorias = {coluna_identificacao, "Latitude", "Longitude"}
                if obrigatorias - set(cabecalhos):
                    erros.append(f"{nome}: faltam colunas obrigatórias")
                    continue
                quantidade = 0
                for linha in reader:
                    quantidade += 1
                    numero = reader.line_num
                    if quantidade > MAX_REGISTROS:
                        erros.append(f"{nome}: ultrapassa {MAX_REGISTROS} registros")
                        break
                    if None in linha or any(valor is None for valor in linha.values()):
                        erros.append(f"{nome}: estrutura inválida na linha {numero}")
                        continue
                    chave = (linha.get(coluna_identificacao) or "").strip()
                    if not chave:
                        erros.append(f"{nome}: identificação vazia na linha {numero}")
                    elif chave in identificadores:
                        erros.append(f"{nome}: identificação duplicada na linha {numero}")
                    else:
                        identificadores.add(chave)
                    if not _coord(linha.get("Latitude"), 90) or not _coord(linha.get("Longitude"), 180):
                        erros.append(f"{nome}: coordenada inválida na linha {numero}")
                if quantidade == 0:
                    erros.append(f"{nome}: arquivo sem registros; atualização bloqueada")
                camadas.append(Camada(nome, quantidade))
        except (OSError, UnicodeError, csv.Error):
            erros.append(f"{nome}: falha de leitura ou codificação; use CSV UTF-8")
    return ResultadoMapa(mapa.nome, tuple(camadas), tuple(erros))


def validar_todos(config: Configuracao, raiz: Path) -> tuple[ResultadoMapa, ...]:
    return tuple(validar_mapa(mapa, raiz, config.coluna_identificacao) for mapa in config.mapas)
