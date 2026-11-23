"""Perfil persistente e autenticação manual do Google."""

from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

NAVEGADOR_PADRAO = "chromium"
PERFIS_PADRAO = {
    "chromium": "runtime/google_profile",
    "edge": "runtime/google_profile_edge",
}
CONTA_GOOGLE = "https://myaccount.google.com/"
PRAZO_UI_MS = 12_000
PRAZO_NAVEGACAO_MS = 30_000
_LOGIN_NECESSARIO = "Sessão Google ausente ou expirada. Execute login com o mesmo --navegador e --perfil-dir."
_DESAFIO_GOOGLE = "O Google solicitou uma verificação de segurança. Resolva-a manualmente no comando login."
_ENTRAR = re.compile(r"^(?:Sign in|Fazer login|Iniciar sessão)$", re.IGNORECASE)
_NAVEGADOR_RECUSADO = re.compile(
    r"^(?:This browser or app may not be secure|(?:Esse|Este) navegador ou app pode não ser seguro)[.!]?$",
    re.IGNORECASE,
)


class ErroNavegador(RuntimeError):
    """Erro de navegador com mensagem adequada para o log."""


class ErroAutenticacao(ErroNavegador):
    """Autenticação manual necessária."""


@contextmanager
def abrir_navegador(pasta_perfil: Path, *, navegador: str = NAVEGADOR_PADRAO):
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        raise ErroNavegador('Instale o Playwright com python -m pip install -e ".[browser]".') from None

    canal = "msedge" if navegador == "edge" else None
    try:
        pasta_perfil.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            contexto: BrowserContext = playwright.chromium.launch_persistent_context(
                str(pasta_perfil), channel=canal, headless=False, locale="pt-BR",
            )
            try:
                contexto.set_default_timeout(PRAZO_UI_MS)
                contexto.set_default_navigation_timeout(PRAZO_NAVEGACAO_MS)
                yield contexto
            finally:
                contexto.close()
    except (Error, OSError):
        nome = "Microsoft Edge" if canal else "Chromium do Playwright"
        raise ErroNavegador(
            f"Falha no navegador ou no perfil. Confira se o {nome} está instalado, "
            "se há interface gráfica e se o perfil está acessível e livre."
        ) from None


def exigir_sessao(pagina: Page) -> None:
    if pagina.is_closed():
        return
    partes = urlsplit(pagina.url)
    if partes.hostname == "accounts.google.com" and pagina.get_by_text(
        _NAVEGADOR_RECUSADO
    ).first.is_visible():
        raise ErroAutenticacao("O Google recusou o login neste navegador. A automação foi interrompida.")
    if partes.path.startswith(("/sorry/", "/challenge/")) or pagina.locator(
        'iframe[title*="captcha" i]:visible, iframe[src*="/recaptcha/api2/bframe"]:visible'
    ).count():
        raise ErroAutenticacao(_DESAFIO_GOOGLE)
    quadros = (urlsplit(quadro.url) for quadro in pagina.frames)
    login_em_quadro = any(
        quadro.hostname == "accounts.google.com"
        and ("/signin/" in quadro.path.lower() or quadro.path == "/ServiceLogin")
        for quadro in quadros
    )
    if (
        partes.hostname == "accounts.google.com"
        or login_em_quadro
        or pagina.get_by_role("link", name=_ENTRAR).first.is_visible()
        or pagina.get_by_role("button", name=_ENTRAR).first.is_visible()
    ):
        raise ErroAutenticacao(_LOGIN_NECESSARIO)


def login_interativo(pasta_perfil: Path, *, navegador: str = NAVEGADOR_PADRAO) -> None:
    with abrir_navegador(pasta_perfil, navegador=navegador) as contexto:
        pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
        pagina.goto(CONTA_GOOGLE, wait_until="domcontentloaded")
        try:
            input("Depois de concluir o login Google ou ver um erro no navegador, pressione ENTER neste terminal: ")
        except EOFError:
            raise ErroAutenticacao("Execute login em um terminal interativo.") from None

        exigir_sessao(pagina)
        resposta = pagina.goto(CONTA_GOOGLE, wait_until="domcontentloaded")
        exigir_sessao(pagina)
        destino = urlsplit(pagina.url)
        if (
            destino.hostname != "myaccount.google.com"
            or not re.fullmatch(r"/(?:u/[0-9]+/?)?", destino.path)
            or resposta is None
            or not resposta.ok
        ):
            raise ErroAutenticacao("O login Google não pôde ser confirmado no navegador.")
