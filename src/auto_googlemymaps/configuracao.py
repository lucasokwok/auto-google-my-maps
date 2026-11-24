"""Configuração privada: NomeMapa corresponde ao nome de uma pasta local."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)
}
ESTRATEGIA = "atualizar_correspondentes"
_HOSTS = {"google.com", "www.google.com", "mymaps.google.com"}
_CAMINHO_EDICAO = re.compile(r"/maps/d/(?:u/[0-9]+/)?edit/?")


class ErroConfiguracao(ValueError):
    """Configuração inválida (não incluir URLs privadas na mensagem)."""


@dataclass(frozen=True)
class Mapa:
    nome: str
    url: str = field(repr=False)


@dataclass(frozen=True)
class Configuracao:
    coluna_identificacao: str
    estrategia_reimportacao: str
    mapas: tuple[Mapa, ...]


def validar_nome(nome: object) -> str:
    if not isinstance(nome, str) or not nome.strip() or nome != nome.strip():
        raise ErroConfiguracao("NomeMapa deve ser um texto não vazio, sem espaços nas extremidades")
    if nome in {".", ".."} or re.search(r'[<>:"/\\|?*\x00-\x1f]', nome):
        raise ErroConfiguracao("NomeMapa contém caracteres inválidos para nome de pasta")
    if nome.endswith((" ", ".")) or nome.upper().split(".")[0] in _RESERVED:
        raise ErroConfiguracao("NomeMapa não é válido como pasta no Windows")
    return nome


def identificador_mapa(url: str) -> str:
    """Valida um link de edição e devolve o identificador para comparar destinos."""
    if not url or re.search(r"[\s\x00-\x1f\x7f\\]", url):
        raise ErroConfiguracao("URL de mapa ausente ou malformada")
    try:
        partes = urlsplit(url)
    except ValueError:
        raise ErroConfiguracao("URL de mapa malformada") from None
    if partes.scheme != "https" or partes.netloc.lower() not in _HOSTS or "#" in url:
        raise ErroConfiguracao("URL precisa ser um link HTTPS válido do Google My Maps")
    if not _CAMINHO_EDICAO.fullmatch(partes.path):
        raise ErroConfiguracao("URL não corresponde à edição do Google My Maps")
    mids = parse_qs(partes.query, keep_blank_values=True).get("mid", [])
    if len(mids) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", mids[0]):
        raise ErroConfiguracao("URL precisa conter um único identificador mid válido")
    return mids[0]


def validar_url(url: object) -> str:
    if not isinstance(url, str):
        raise ErroConfiguracao("URL de mapa não informada")
    identificador_mapa(url)
    return url


def carregar_configuracao(caminho: Path) -> Configuracao:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroConfiguracao("Configuração privada ausente; copie config/mapas.example.json para config/mapas.json")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ErroConfiguracao("Não foi possível ler config/mapas.json; confira o formato JSON e a codificação") from None
    if not isinstance(dados, dict):
        raise ErroConfiguracao("O JSON precisa conter um objeto")
    coluna = dados.get("coluna_identificacao")
    if not isinstance(coluna, str) or not coluna.strip():
        raise ErroConfiguracao("Informe a coluna_identificacao")
    estrategia = dados.get("estrategia_reimportacao", ESTRATEGIA)
    if estrategia != ESTRATEGIA:
        raise ErroConfiguracao(f"estrategia_reimportacao deve ser {ESTRATEGIA}")
    entradas = dados.get("mapas")
    if not isinstance(entradas, list) or not entradas:
        raise ErroConfiguracao("Informe uma lista não vazia de mapas")
    mapas = []
    nomes = set()
    identificadores = set()
    for item in entradas:
        if not isinstance(item, dict):
            raise ErroConfiguracao("Cada mapa deve ser um objeto com NomeMapa e URL")
        nome = validar_nome(item.get("NomeMapa"))
        try:
            url = validar_url(item.get("URL"))
        except ErroConfiguracao as exc:
            raise ErroConfiguracao(f"{nome} — {exc}") from None
        identificador = identificador_mapa(url)
        if nome.casefold() in nomes:
            raise ErroConfiguracao("Há NomeMapa duplicado")
        if identificador in identificadores:
            raise ErroConfiguracao("Há links para o mesmo mapa na configuração")
        nomes.add(nome.casefold())
        identificadores.add(identificador)
        mapas.append(Mapa(nome=nome, url=url))
    return Configuracao(coluna, estrategia, tuple(mapas))
