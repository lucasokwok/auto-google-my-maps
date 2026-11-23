"""Perfil persistente e autenticação manual do Google."""

from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

PERFIL_PADRAO = "runtime/google_profile"
CONTA_GOOGLE = "https://myaccount.google.com/"
PRAZO_UI_MS = 12_000
PRAZO_NAVEGACAO_MS = 30_000
_LOGIN_NECESSARIO = "Sessão Google ausente ou expirada. Execute login com o mesmo --perfil-dir."
_DESAFIO_GOOGLE = "O Google solicitou uma verificação de segurança. Resolva-a manualmente no comando login."
_ENTRAR = re.compile(r"^(?:Sign in|Fazer login|Iniciar sessão)$", re.IGNORECASE)


class ErroNavegador(RuntimeError):
    """Erro de navegador com mensagem adequada para o log."""


class ErroAutenticacao(ErroNavegador):
    """Autenticação manual necessária."""


@contextmanager
def abrir_navegador(pasta_perfil: Path):
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        raise ErroNavegador('Instale o Playwright com python -m pip install -e ".[browser]".') from None

    try:
        pasta_perfil.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            contexto: BrowserContext = playwright.chromium.launch_persistent_context(
                str(pasta_perfil), headless=False, locale="pt-BR",
            )
            try:
                contexto.set_default_timeout(PRAZO_UI_MS)
                contexto.set_default_navigation_timeout(PRAZO_NAVEGACAO_MS)
                yield contexto
            finally:
                contexto.close()
    except (Error, OSError):
        raise ErroNavegador(
            "Falha no navegador ou no perfil. Confira se o Chromium do Playwright está "
            "instalado, se há interface gráfica e se o perfil está acessível e livre."
        ) from None


def exigir_sessao(pagina: Page) -> None:
    if pagina.is_closed():
        return
    partes = urlsplit(pagina.url)
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


def login_interativo(pasta_perfil: Path) -> None:
    with abrir_navegador(pasta_perfil) as contexto:
        pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
        pagina.goto(CONTA_GOOGLE, wait_until="domcontentloaded")
        try:
            input("Conclua o login Google no navegador e pressione ENTER neste terminal: ")
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
