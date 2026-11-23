"""Configuração privada: NomeMapa corresponde ao nome de uma pasta local."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, parse_qs

_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)
}
_STRATEGIES = {"atualizar_correspondentes", "substituir_todos"}


class ErroConfiguracao(ValueError):
    """Configuração inválida (não incluir URLs privadas na mensagem)."""


@dataclass(frozen=True)
class Mapa:
    nome: str
    url: str


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


def validar_url(url: object) -> str:
    if not isinstance(url, str) or not url.strip() or url != url.strip():
        raise ErroConfiguracao("URL de mapa não informada")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"google.com", "www.google.com", "mymaps.google.com"}:
        raise ErroConfiguracao("URL precisa ser um link HTTPS válido do Google My Maps")
    if not (parsed.path.startswith("/maps/d/") or parsed.hostname == "mymaps.google.com"):
        raise ErroConfiguracao("URL não corresponde à edição do Google My Maps")
    if not parse_qs(parsed.query).get("mid"):
        raise ErroConfiguracao("URL precisa conter o identificador mid do mapa")
    if parsed.username or parsed.password or parsed.fragment:
        raise ErroConfiguracao("URL contém partes não permitidas")
    return url


def carregar_configuracao(caminho: Path) -> Configuracao:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroConfiguracao("Configuração privada ausente; copie config/mapas.example.json para config/mapas.json")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ErroConfiguracao("Não foi possível ler config/mapas.json; confira o formato JSON e a codificação") from None
    if not isinstance(dados, dict):
        raise ErroConfiguracao("O JSON precisa conter um objeto")
    coluna = dados.get("coluna_identificacao")
    if not isinstance(coluna, str) or not coluna.strip():
        raise ErroConfiguracao("Informe a coluna_identificacao")
    estrategia = dados.get("estrategia_reimportacao", "atualizar_correspondentes")
    if estrategia not in _STRATEGIES:
        raise ErroConfiguracao("estrategia_reimportacao inválida")
    entradas = dados.get("mapas")
    if not isinstance(entradas, list) or not entradas:
        raise ErroConfiguracao("Informe uma lista não vazia de mapas")
    mapas = []
    nomes = set()
    urls = set()
    for item in entradas:
        if not isinstance(item, dict):
            raise ErroConfiguracao("Cada mapa deve ser um objeto com NomeMapa e URL")
        nome = validar_nome(item.get("NomeMapa"))
        url = validar_url(item.get("URL"))
        if nome.casefold() in nomes:
            raise ErroConfiguracao("Há NomeMapa duplicado")
        if url in urls:
            raise ErroConfiguracao("Há URLs repetidas na configuração")
        nomes.add(nome.casefold())
        urls.add(url)
        mapas.append(Mapa(nome=nome, url=url))
    return Configuracao(coluna, estrategia, tuple(mapas))
