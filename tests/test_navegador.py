from unittest.mock import Mock, patch

import pytest
from playwright.sync_api import Error

from auto_googlemymaps.navegador import (
    CONTA_GOOGLE,
    ErroAutenticacao,
    ErroNavegador,
    abrir_navegador,
    login_interativo,
)


@pytest.fixture
def navegador():
    with patch("playwright.sync_api.sync_playwright") as sync:
        chromium = sync.return_value.__enter__.return_value.chromium
        contexto = chromium.launch_persistent_context.return_value
        pagina = Mock()
        contexto.pages = [pagina]
        pagina.url = CONTA_GOOGLE
        pagina.frames = []
        pagina.goto.return_value.ok = True
        pagina.locator.return_value.count.return_value = 0
        pagina.is_closed.return_value = False
        pagina.get_by_role.return_value.first.is_visible.return_value = False
        yield chromium, contexto, pagina


def test_login_manual_confirma_sessao_no_perfil(tmp_path, navegador):
    chromium, contexto, pagina = navegador
    perfil = tmp_path / "perfil"
    with patch("builtins.input", return_value="") as entrada:
        login_interativo(perfil)
    chromium.launch_persistent_context.assert_called_once_with(str(perfil), headless=False, locale="pt-BR")
    assert perfil.is_dir()
    assert pagina.goto.call_count == 2
    entrada.assert_called_once()
    contexto.close.assert_called_once()


@pytest.mark.parametrize(("destino", "erro"), [
    ("https://accounts.google.com/v3/signin/identifier", "ausente ou expirada"),
    ("https://accounts.google.com/challenge/", "verificação de segurança"),
    ("https://myaccount.google.com/intro", "não pôde ser confirmado"),
])
def test_login_incompleto(tmp_path, navegador, destino, erro):
    _, contexto, pagina = navegador
    pagina.url = destino
    with patch("builtins.input", return_value=""), pytest.raises(ErroAutenticacao, match=erro):
        login_interativo(tmp_path)
    contexto.close.assert_called_once()


def test_falha_no_chromium_tem_mensagem_sanitizada(tmp_path, navegador):
    chromium, _, _ = navegador
    chromium.launch_persistent_context.side_effect = Error("DETALHE_DE_PERFIL_FICTICIO")
    with pytest.raises(ErroNavegador, match="Chromium") as erro:
        with abrir_navegador(tmp_path):
            pytest.fail("O contexto não deveria ser aberto")
    assert "DETALHE_DE_PERFIL_FICTICIO" not in str(erro.value)
