"""Abre navegador com perfil local persistente para autenticação manual."""

from pathlib import Path


def login_interativo(pasta_perfil: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('Instale a dependência opcional: python -m pip install -e ".[browser]"') from exc

    pasta_perfil = Path(pasta_perfil)
    pasta_perfil.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(pasta_perfil), headless=False)
        try:
            pagina = context.pages[0] if context.pages else context.new_page()
            pagina.goto("https://www.google.com/maps/d/", wait_until="domcontentloaded")
            input("Entre manualmente na sua conta Google. Pressione ENTER para fechar o navegador: ")
        finally:
            context.close()
