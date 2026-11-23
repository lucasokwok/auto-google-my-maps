"""Descobre e valida os CSVs locais sem alterar os arquivos."""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .configuracao import Configuracao, Mapa

CAMADAS = tuple(f"pontos_{numero:02d}.csv" for numero in range(1, 6))
MAX_REGISTROS = 2000
MAX_BYTES = 40_000_000


@dataclass(frozen=True)
class Camada:
    nome: str
    quantidade: int
    conteudo: bytes = field(repr=False, compare=False)
    arquivo: Path = field(repr=False, compare=False)


@dataclass(frozen=True)
class ResultadoMapa:
    nome: str
    camadas: tuple[Camada, ...]
    erros: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return not self.erros


def _coord(texto: str, limite: int) -> bool:
    if "_" in texto:
        return False
    try:
        valor = float(texto)
    except ValueError:
        return False
    return math.isfinite(valor) and -limite <= valor <= limite


def _validar_csv(arquivo: Path, coluna: str) -> tuple[Camada | None, list[str]]:
    nome = arquivo.name
    if arquivo.is_symlink() or not arquivo.is_file():
        return None, [f"{nome}: não é um arquivo local regular"]

    erros = []
    try:
        with arquivo.open("rb") as dados:
            conteudo = dados.read(MAX_BYTES + 1)
        if len(conteudo) > MAX_BYTES:
            return None, [f"{nome}: ultrapassa 40 MB"]

        with io.TextIOWrapper(io.BytesIO(conteudo), encoding="utf-8-sig", newline="") as texto:
            leitor = csv.reader(texto, strict=True)
            cabecalhos = next(leitor, [])
            if not cabecalhos or len(cabecalhos) != len(set(cabecalhos)):
                return None, [f"{nome}: cabeçalho ausente ou duplicado"]
            if not {coluna, "Latitude", "Longitude"}.issubset(cabecalhos):
                return None, [f"{nome}: faltam colunas obrigatórias"]
            id_pos = cabecalhos.index(coluna)
            lat_pos = cabecalhos.index("Latitude")
            lon_pos = cabecalhos.index("Longitude")
            identificadores: set[str] = set()
            quantidade = 0

            for linha in leitor:
                if not linha:
                    continue
                quantidade += 1
                numero = leitor.line_num
                if quantidade > MAX_REGISTROS:
                    erros.append(f"{nome}: ultrapassa {MAX_REGISTROS} registros")
                    break
                if len(linha) != len(cabecalhos) or any("\x00" in valor for valor in linha):
                    erros.append(f"{nome}: estrutura inválida na linha {numero}")
                    continue
                chave = linha[id_pos].strip()
                if not chave:
                    erros.append(f"{nome}: identificação vazia na linha {numero}")
                elif chave in identificadores:
                    erros.append(f"{nome}: identificação duplicada na linha {numero}")
                identificadores.add(chave)
                if not _coord(linha[lat_pos], 90) or not _coord(linha[lon_pos], 180):
                    erros.append(f"{nome}: coordenada inválida na linha {numero}")
    except (OSError, UnicodeError, csv.Error):
        return None, [f"{nome}: falha de leitura ou formato; use CSV UTF-8 separado por vírgulas"]

    if quantidade == 0:
        erros.append(f"{nome}: arquivo sem registros; atualização bloqueada")
    camada = None if erros else Camada(nome, quantidade, conteudo, arquivo.absolute())
    return camada, erros


def validar_mapa(mapa: Mapa, raiz: Path, coluna_identificacao: str) -> ResultadoMapa:
    pasta = Path(raiz) / mapa.nome
    erros: list[str] = []
    camadas: list[Camada] = []

    if pasta.is_symlink() or not pasta.is_dir():
        return ResultadoMapa(mapa.nome, (), ("pasta local do mapa ausente ou inválida",))
    try:
        arquivos = {entrada.name for entrada in pasta.iterdir() if entrada.suffix.lower() == ".csv"}
    except OSError:
        return ResultadoMapa(mapa.nome, (), ("não foi possível listar a pasta do mapa",))

    if arquivos.difference(CAMADAS):
        erros.append("há CSVs com nomes fora do padrão pontos_01.csv a pontos_05.csv")
    previstos = [nome for nome in CAMADAS if nome in arquivos]
    if not previstos:
        erros.append("nenhum CSV de camada encontrado")
    else:
        for nome in CAMADAS[:CAMADAS.index(previstos[-1]) + 1]:
            if nome not in arquivos:
                erros.append(f"{nome}: arquivo ausente na sequência")
                continue
            camada, falhas = _validar_csv(pasta / nome, coluna_identificacao)
            erros.extend(falhas)
            if camada is not None:
                camadas.append(camada)

    return ResultadoMapa(mapa.nome, tuple(camadas), tuple(erros))


def validar_todos(config: Configuracao, raiz: Path) -> Iterator[ResultadoMapa]:
    for mapa in config.mapas:
        yield validar_mapa(mapa, raiz, config.coluna_identificacao)
