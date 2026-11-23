from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from playwright.sync_api import Error, Page, TimeoutError

from auto_googlemymaps import mymaps
from auto_googlemymaps.configuracao import Mapa
from auto_googlemymaps.csvs import Camada
from auto_googlemymaps.navegador import ErroAutenticacao

MAPA = Mapa("FICTICIO", "https://www.google.com/maps/d/edit?mid=MAPA_FICTICIO")
CAMADA = Camada("pontos_01.csv", 1, b"ID,Latitude,Longitude\n1,0,0\n")


@pytest.fixture
def pagina():
    pagina = Mock(spec=Page)
    pagina.url = MAPA.url
    pagina.frames = []
    pagina.is_closed.return_value = False
    pagina.goto.return_value.ok = True
    pagina.locator.return_value.count.return_value = 0
    pagina.get_by_role.return_value.first.is_visible.return_value = False
    return pagina


def test_falha_na_navegacao_nao_divulga_detalhes(pagina):
    pagina.goto.side_effect = Error(MAPA.url + " DADO_FICTICIO")
    with pytest.raises(mymaps.ErroMapa, match="editor") as erro:
        mymaps.abrir_mapa(pagina, MAPA)
    assert MAPA.url not in str(erro.value)
    assert "DADO_FICTICIO" not in str(erro.value)


def test_redirecionamento_para_outro_mapa_bloqueado(pagina):
    pagina.url = MAPA.url.replace("MAPA_FICTICIO", "OUTRO_FICTICIO")
    with pytest.raises(mymaps.ErroMapa, match="editor do mapa cadastrado"):
        mymaps.abrir_mapa(pagina, MAPA)


def test_redirecionamento_para_login(pagina):
    pagina.url = "https://accounts.google.com/v3/signin/identifier"
    with pytest.raises(ErroAutenticacao, match="Execute login"):
        mymaps.abrir_mapa(pagina, MAPA)


def test_login_exigido_em_quadro_do_picker(pagina):
    pagina.frames = [SimpleNamespace(url="https://accounts.google.com/v3/signin/identifier")]
    with pytest.raises(ErroAutenticacao, match="Execute login"):
        mymaps.abrir_mapa(pagina, MAPA)


def test_bloqueio_de_seguranca(pagina):
    pagina.url = "https://www.google.com/sorry/index"
    with pytest.raises(ErroAutenticacao, match="verificação de segurança"):
        mymaps.abrir_mapa(pagina, MAPA)


def test_localiza_menu_no_cabecalho_do_titulo_exato(pagina):
    rotulo = pagina.get_by_text.return_value.and_.return_value
    cabecalho = rotulo.locator.return_value
    controle = cabecalho.locator.return_value
    controle.count.return_value = 1
    controle.get_attribute.return_value = "layer 1"
    rotulo.get_attribute.return_value = "layer 1"
    remota = mymaps.localizar_camada(pagina, CAMADA.nome)
    pagina.get_by_text.assert_called_once_with(CAMADA.nome, exact=True)
    assert remota.cabecalho is cabecalho
    assert remota.opcoes is cabecalho.get_by_label.return_value.or_.return_value
    remota.opcoes.wait_for.assert_called_once_with(state="attached")


def test_camada_ambigua_nao_e_aceita(pagina):
    rotulo = pagina.get_by_text.return_value.and_.return_value
    rotulo.wait_for.side_effect = Error("múltiplos rótulos")
    with pytest.raises(mymaps.ErroMapa, match="Camada ausente ou ambígua"):
        mymaps.localizar_camada(pagina, CAMADA.nome)


def test_envia_os_bytes_validados_com_o_nome_original(pagina):
    picker = pagina.locator.return_value.and_.return_value.content_frame
    picker.get_by_role.return_value.is_visible.return_value = False
    mymaps._enviar_csv(pagina, CAMADA)
    picker.locator.assert_called_once_with('input[type="file"]')
    picker.locator.return_value.set_input_files.assert_called_once_with({
        "name": CAMADA.nome, "mimeType": "text/csv", "buffer": CAMADA.conteudo,
    })


@pytest.mark.parametrize("ocorrencias", [0, 2])
def test_rejeita_coluna_ausente_ou_duplicada_no_editor(ocorrencias):
    dialogo = Mock()
    campo = dialogo.get_by_role.return_value.or_.return_value
    campo.evaluate.side_effect = ["SELECT", ocorrencias]
    with pytest.raises(mymaps.ErroMapa, match="ausente ou é ambígua"):
        mymaps._selecionar_coluna(dialogo, mymaps._DADOS_CAMADA, "CHAVE")
    campo.select_option.assert_not_called()


@pytest.fixture
def importacao(pagina, monkeypatch):
    estado = Mock()
    avisos = Mock()
    locators = {"visivel": Mock(), "sucesso": Mock(), "falha": Mock(), "captcha": Mock()}
    locators["captcha"].count.return_value = 0
    locators["falha"].count.return_value = 0
    pagina.locator.side_effect = lambda css: (
        locators["visivel"] if css == ":visible" else avisos if 'role="status"' in css else locators["captcha"]
    )

    def aviso(regex):
        candidato = Mock()
        candidato.or_.return_value.and_.return_value = (
            locators["sucesso"] if regex.search("Import successful") else locators["falha"]
        )
        return candidato

    avisos.get_by_text.side_effect = aviso
    monkeypatch.setattr(mymaps, "_enviar_csv", estado.enviar)
    monkeypatch.setattr(mymaps, "_selecionar_coluna", estado.coluna)
    monkeypatch.setattr(mymaps, "_item_menu", estado.menu)
    remota = mymaps.CamadaRemota(estado.cabecalho, estado.opcoes)
    dialogo = pagina.get_by_role.return_value.filter.return_value
    return estado, remota, dialogo, locators


def test_reimporta_correspondentes_e_exige_um_novo_sinal_de_sucesso(pagina, importacao):
    estado, remota, dialogo, locators = importacao
    mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    assert [chamada.args[1] for chamada in estado.menu.call_args_list] == [
        mymaps._REIMPORTAR_MESCLAR, mymaps._REIMPORTAR, mymaps._CORRESPONDENTES,
    ]
    estado.enviar.assert_called_once_with(pagina, CAMADA)
    assert [chamada.args for chamada in estado.coluna.call_args_list] == [
        (dialogo, mymaps._DADOS_CAMADA, "CHAVE"), (dialogo, mymaps._DADOS_ENVIADOS, "CHAVE"),
    ]
    dialogo.get_by_role.return_value.click.assert_called_once()
    locators["sucesso"].first.wait_for.assert_called_once_with(state="hidden")
    locators["sucesso"].or_.return_value.first.wait_for.assert_called_once_with(state="visible", timeout=45_000)
    dialogo.wait_for.assert_called_once_with(state="hidden")


def test_falha_no_picker_impede_confirmacao(pagina, importacao):
    estado, remota, dialogo, _ = importacao
    estado.enviar.side_effect = TimeoutError("DETALHE_FICTICIO")
    with pytest.raises(mymaps.ErroMapa, match="enviar o CSV") as erro:
        mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    assert "DETALHE_FICTICIO" not in str(erro.value)
    dialogo.get_by_role.return_value.click.assert_not_called()


def test_alerta_apos_conclusao_e_falha(pagina, importacao):
    _, remota, dialogo, locators = importacao
    locators["falha"].count.side_effect = [0, 1]
    with pytest.raises(mymaps.ErroMapa, match="indicou falha"):
        mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    dialogo.get_by_role.return_value.click.assert_called_once()


def test_fechamento_do_dialogo_sem_sinal_nao_confirma(pagina, importacao):
    _, remota, dialogo, locators = importacao
    locators["sucesso"].or_.return_value.first.wait_for.side_effect = TimeoutError("SEM_SINAL")
    with pytest.raises(mymaps.ErroMapa, match="Resultado indeterminado") as erro:
        mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    assert "SEM_SINAL" not in str(erro.value)
    dialogo.get_by_role.return_value.click.assert_called_once()
