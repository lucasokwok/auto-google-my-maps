from unittest.mock import Mock, patch

import pytest
from playwright.sync_api import Error

from auto_googlemymaps.__main__ import main
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
        pagina.get_by_text.return_value.first.is_visible.return_value = False
        yield chromium, contexto, pagina


@pytest.mark.parametrize(("opcoes", "nome_perfil", "canal"), [
    ([], "google_profile", None),
    (["--navegador", "edge"], "google_profile_edge", "msedge"),
])
def test_login_manual_confirma_sessao_no_perfil(tmp_path, monkeypatch, navegador, opcoes, nome_perfil, canal):
    chromium, contexto, pagina = navegador
    monkeypatch.chdir(tmp_path)
    with patch("builtins.input", return_value="") as entrada:
        assert main(["login", *opcoes]) == 0
    perfil = (tmp_path / "runtime" / nome_perfil)
    assert perfil.is_dir()
    chromium.launch_persistent_context.assert_called_once_with(
        str(perfil.relative_to(tmp_path)), channel=canal, headless=False, locale="pt-BR",
    )
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


@pytest.mark.parametrize(("opcao", "nome"), [("chromium", "Chromium"), ("edge", "Microsoft Edge")])
def test_falha_no_navegador_tem_mensagem_sanitizada(tmp_path, navegador, opcao, nome):
    chromium, _, _ = navegador
    chromium.launch_persistent_context.side_effect = Error("DETALHE_DE_PERFIL_FICTICIO")
    with pytest.raises(ErroNavegador, match=nome) as erro:
        with abrir_navegador(tmp_path, navegador=opcao):
            pytest.fail("O contexto não deveria ser aberto")
    assert "DETALHE_DE_PERFIL_FICTICIO" not in str(erro.value)


def test_recusa_do_google_interrompe_login_sem_nova_tentativa(tmp_path, navegador):
    _, contexto, pagina = navegador
    pagina.url = "https://accounts.google.com/v3/signin/identifier"
    pagina.get_by_text.return_value.first.is_visible.return_value = True
    with patch("builtins.input", return_value=""), pytest.raises(ErroAutenticacao, match="recusou o login"):
        login_interativo(tmp_path, navegador="edge")
    assert pagina.get_by_text.call_args.args[0].fullmatch("Esse navegador ou app pode não ser seguro.")
    pagina.goto.assert_called_once()
    contexto.close.assert_called_once()
