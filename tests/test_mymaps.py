from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call

import pytest
from playwright.sync_api import Error, Page, TimeoutError

from auto_googlemymaps import mymaps
from auto_googlemymaps.configuracao import Mapa
from auto_googlemymaps.csvs import Camada
from auto_googlemymaps.navegador import ErroAutenticacao

MAPA = Mapa("FICTICIO", "https://www.google.com/maps/d/edit?mid=MAPA_FICTICIO")
CAMADA = Camada("pontos_01.csv", 1, b"ID,Latitude,Longitude\n1,0,0\n", Path("pontos_01.csv"))


@pytest.fixture
def pagina():
    pagina = Mock(spec=Page)
    pagina.url = MAPA.url
    pagina.frames = []
    pagina.is_closed.return_value = False
    pagina.goto.return_value.ok = True
    pagina.locator.return_value.count.return_value = 0
    pagina.get_by_role.return_value.first.is_visible.return_value = False
    pagina.get_by_text.return_value.first.is_visible.return_value = False
    return pagina


def test_abre_editor_sem_depender_do_botao_adicionar_camada(pagina):
    pagina.get_by_role.return_value.wait_for.side_effect = TimeoutError("Botão ausente")
    mymaps.abrir_mapa(pagina, MAPA)
    pagina.goto.assert_called_once_with(MAPA.url, wait_until="domcontentloaded")
    pagina.get_by_role.return_value.wait_for.assert_not_called()


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


def test_visualizacao_do_mesmo_mapa_bloqueada(pagina):
    pagina.url = MAPA.url.replace("/edit?", "/viewer?")
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


@pytest.fixture
def cabecalhos(pagina):
    return pagina.get_by_label.return_value.or_.return_value.or_.return_value.locator.return_value


def test_localiza_menu_no_cabecalho_do_titulo_exato(pagina, cabecalhos):
    titulo = pagina.get_by_text.return_value.and_.return_value
    cabecalho = cabecalhos.filter.return_value
    remota = mymaps.localizar_camada(pagina, CAMADA.nome)
    pagina.get_by_text.assert_called_once_with(CAMADA.nome, exact=True)
    cabecalhos.filter.assert_called_once_with(has=titulo)
    assert remota.cabecalho is cabecalho
    assert remota.opcoes is cabecalho.get_by_label.return_value.or_.return_value.or_.return_value
    remota.opcoes.wait_for.assert_called_once_with(state="attached")


def test_cabecalho_ambiguo_nao_e_aceito(pagina, cabecalhos):
    cabecalhos.filter.return_value.wait_for.side_effect = Error("múltiplos cabeçalhos")
    with pytest.raises(mymaps.ErroMapa, match="um único menu"):
        mymaps.localizar_camada(pagina, CAMADA.nome)


def test_distingue_titulo_ausente_de_menu_sem_associacao(pagina):
    titulo = pagina.get_by_text.return_value.and_.return_value
    titulo.first.wait_for.side_effect = TimeoutError("DETALHE_FICTICIO")
    with pytest.raises(mymaps.ErroMapa, match="O nome exato da camada não apareceu") as erro:
        mymaps.localizar_camada(pagina, CAMADA.nome)
    assert "DETALHE_FICTICIO" not in str(erro.value)


@pytest.fixture
def camada_local(tmp_path):
    arquivo = tmp_path / CAMADA.nome
    arquivo.write_bytes(CAMADA.conteudo)
    return Camada(CAMADA.nome, CAMADA.quantidade, CAMADA.conteudo, arquivo)


def test_procurar_abre_o_seletor_e_envia_o_arquivo_validado(pagina, camada_local):
    iframe = pagina.locator.return_value.and_.return_value
    iframe.is_visible.return_value = False
    picker = iframe.content_frame
    picker.locator.return_value.wait_for.side_effect = TimeoutError("Campo específico ausente")
    pagina.expect_file_chooser.return_value = MagicMock()
    escolha = pagina.expect_file_chooser.return_value.__enter__.return_value

    mymaps._enviar_csv(pagina, camada_local)
    pagina.expect_file_chooser.assert_called_once()
    picker.get_by_role.assert_any_call("button", name=mymaps._PROCURAR)
    escolha.value.set_files.assert_called_once_with(camada_local.arquivo)


def test_preferencia_pelo_campo_csv_especifico_sem_abrir_procurar(pagina, camada_local):
    iframe = pagina.locator.return_value.and_.return_value
    iframe.is_visible.return_value = False
    picker = iframe.content_frame
    campo = picker.locator.return_value

    mymaps._enviar_csv(pagina, camada_local)

    picker.locator.assert_called_once_with('input[type="file"][jsname="G1bupd"][accept*=".csv" i]')
    campo.wait_for.assert_called_once_with(state="attached", timeout=2_000)
    assert campo.evaluate_handle.call_args.args[1] == {"nome": camada_local.nome, "bytes": len(camada_local.conteudo)}
    campo.set_input_files.assert_called_once_with(camada_local.arquivo)
    campo.evaluate_handle.return_value.dispose.assert_called_once()
    pagina.expect_file_chooser.assert_not_called()


def test_arrastar_entrega_o_arquivo_validado_na_area_do_picker(pagina, camada_local):
    iframe = pagina.locator.return_value.and_.return_value
    iframe.is_visible.return_value = False
    zona = iframe.content_frame.get_by_text.return_value
    zona.bounding_box.return_value = {"x": 100, "y": 50, "width": 40, "height": 20}
    sessao = pagina.context.new_cdp_session.return_value

    mymaps._enviar_csv(pagina, camada_local, arrastar_csv=True)

    iframe.content_frame.get_by_text.assert_called_once_with(mymaps._ARRASTAR_ARQUIVO)
    pagina.expect_file_chooser.assert_not_called()
    dados = {"items": [], "files": [str(camada_local.arquivo)], "dragOperationsMask": 1}
    assert sessao.send.call_args_list == [
        call("Input.dispatchDragEvent", {"type": etapa, "x": 120, "y": 60, "data": dados})
        for etapa in ("dragEnter", "dragOver", "drop")
    ]
    sessao.detach.assert_called_once()


def test_csv_alterado_e_bloqueado_antes_de_abrir_procurar(pagina, camada_local):
    camada_local.arquivo.write_bytes(b"conteudo diferente")

    with pytest.raises(mymaps.ErroMapa, match="mudou desde a validação"):
        mymaps._enviar_csv(pagina, camada_local)
    pagina.expect_file_chooser.assert_not_called()


def test_csv_alterado_durante_upload_impede_reimportacao(pagina, camada_local, monkeypatch):
    pagina.expect_file_chooser.return_value = MagicMock()
    monkeypatch.setattr(
        mymaps, "_aguardar_fim_do_upload", lambda *_: camada_local.arquivo.write_bytes(b"conteudo diferente"),
    )

    with pytest.raises(mymaps.ErroMapa, match="mudou desde a validação"):
        mymaps._enviar_csv(pagina, camada_local)


@pytest.mark.parametrize(("operacao", "etapa"), [
    ("seletor", "aguardar a abertura do seletor de arquivos do Google"),
    ("aba", 'abrir "Fazer upload" no seletor do Google'),
    ("campo", "preparar o campo de arquivo do Picker"),
    ("procurar", 'abrir o seletor nativo pelo botão "Procurar"'),
])
def test_prazo_esgotado_antes_de_entregar_csv_pode_repetir(pagina, camada_local, operacao, etapa):
    iframe = pagina.locator.return_value.and_.return_value
    picker = iframe.content_frame
    campo = picker.locator.return_value
    upload = picker.get_by_role.return_value.or_.return_value.or_.return_value
    erro_ui = TimeoutError("DETALHE_FICTICIO")
    if operacao == "procurar":
        campo.wait_for.side_effect = erro_ui
        pagina.expect_file_chooser.return_value = MagicMock()
    acoes = {
        "seletor": iframe.wait_for, "aba": upload.click, "campo": campo.evaluate_handle,
        "procurar": picker.get_by_role.return_value.click,
    }
    acoes[operacao].side_effect = erro_ui

    with pytest.raises(mymaps.ErroUploadTemporario) as erro:
        mymaps._enviar_csv(pagina, camada_local)
    assert f"Tempo esgotado ao {etapa}." in str(erro.value)
    assert "DETALHE_FICTICIO" not in str(erro.value)
    campo.set_input_files.assert_not_called()
    assert pagina.remove_listener.call_count == 2


def test_falha_na_entrega_do_csv_preserva_diagnostico_e_exige_sinal_para_repetir(pagina, camada_local):
    picker = pagina.locator.return_value.and_.return_value.content_frame
    campo = picker.locator.return_value
    campo.set_input_files.side_effect = TimeoutError("DETALHE_FICTICIO")
    campo.evaluate_handle.return_value.json_value.return_value = {"mudou": True, "corresponde": True}

    with pytest.raises(mymaps.ErroMapa) as erro:
        mymaps._enviar_csv(pagina, camada_local)
    assert type(erro.value) is mymaps.ErroMapa
    assert "Tempo esgotado ao entregar o CSV ao campo de arquivo do Picker." in str(erro.value)
    assert "O campo recebeu um arquivo com o nome e tamanho esperados." in str(erro.value)
    assert "DETALHE_FICTICIO" not in str(erro.value)
    campo.evaluate_handle.return_value.dispose.assert_called_once()


def test_login_exigido_durante_abertura_do_picker_impede_repeticao(pagina, camada_local):
    iframe = pagina.locator.return_value.and_.return_value

    def abrir_seletor(**kwargs):
        pagina.frames = [SimpleNamespace(url="https://accounts.google.com/v3/signin/identifier")]
        raise TimeoutError("Seletor não ficou disponível")

    iframe.wait_for.side_effect = abrir_seletor
    with pytest.raises(ErroAutenticacao, match="Execute login"):
        mymaps._enviar_csv(pagina, camada_local)


def test_upload_pode_fechar_picker_automaticamente():
    iframe, selecionar = Mock(), Mock()
    iframe.is_visible.return_value = True
    selecionar.is_visible.return_value = False

    mymaps._aguardar_fim_do_upload(iframe, selecionar)
    assert iframe.wait_for.call_args.kwargs["state"] == "hidden"
    selecionar.click.assert_not_called()


def test_upload_explicito_aguarda_selecionar_ser_habilitado():
    iframe, selecionar = Mock(), Mock()
    iframe.is_visible.return_value = True
    selecionar.is_visible.return_value = True
    selecionar.is_enabled.side_effect = [False, True]
    iframe.wait_for.side_effect = [TimeoutError("Picker ainda aberto"), None]

    mymaps._aguardar_fim_do_upload(iframe, selecionar)
    selecionar.click.assert_called_once()
    assert iframe.wait_for.call_count == 2


def test_picker_aberto_apos_upload_informa_status_sem_urls(pagina, camada_local, monkeypatch):
    eventos = {}
    pagina.on.side_effect = eventos.__setitem__
    iframe = pagina.locator.return_value.and_.return_value
    quadro = iframe.element_handle.return_value.content_frame.return_value
    estado = iframe.content_frame.locator.return_value.evaluate_handle.return_value
    estado.json_value.return_value = {"mudou": True, "corresponde": True}
    upload = SimpleNamespace(
        method="POST", url="https://docs.google.com/upload?token=DETALHE_FICTICIO",
        frame=quadro, failure="net::ERR_CONNECTION_RESET",
    )
    rpc_picker = SimpleNamespace(method="POST", url="https://docs.google.com/rpc", frame=quadro)
    outra_requisicao = SimpleNamespace(method="POST", url="https://docs.google.com/outra", frame=None)

    def aguardar_upload(iframe, selecionar):
        eventos["response"](SimpleNamespace(request=upload, status=403, headers={}))
        eventos["response"](SimpleNamespace(request=rpc_picker, status=400))
        eventos["response"](SimpleNamespace(request=outra_requisicao, status=500))
        eventos["requestfailed"](upload)
        raise TimeoutError("DETALHE_FICTICIO")

    monkeypatch.setattr(mymaps, "_aguardar_fim_do_upload", aguardar_upload)
    with pytest.raises(mymaps.ErroMapa, match="Tempo esgotado ao confirmar o fim do envio") as erro:
        mymaps._enviar_csv(pagina, camada_local)
    assert type(erro.value) is mymaps.ErroMapa
    assert "HTTP do upload: 400, 403. Falhas de rede observadas: 1 (ERR_CONNECTION_RESET)." in str(erro.value)
    assert "O campo recebeu um arquivo com o nome e tamanho esperados." in str(erro.value)
    assert "500" not in str(erro.value)
    assert "DETALHE_FICTICIO" not in str(erro.value)
    for evento, callback in eventos.items():
        pagina.remove_listener.assert_any_call(evento, callback)


@pytest.mark.parametrize(("status", "rede", "cabecalhos", "tipo"), [
    ([503], None, {}, mymaps.ErroUploadTemporario),
    ([], "net::ERR_CONNECTION_RESET", {}, mymaps.ErroUploadTemporario),
    ([503], None, {"retry-after": "120"}, mymaps.ErroMapa),
    ([429], None, {}, mymaps.ErroMapa),
    ([200, 503], None, {}, mymaps.ErroMapa),
    ([308, 503], None, {}, mymaps.ErroMapa),
    ([], "net::ERR_ABORTED", {}, mymaps.ErroMapa),
    ([], None, {}, mymaps.ErroMapa),
])
def test_retentativa_exige_sinal_transitorio_sem_aceite_do_envio(
    pagina, camada_local, monkeypatch, status, rede, cabecalhos, tipo,
):
    eventos = {}
    pagina.on.side_effect = eventos.__setitem__
    iframe = pagina.locator.return_value.and_.return_value
    estado = iframe.content_frame.locator.return_value.evaluate_handle.return_value
    estado.json_value.return_value = {"mudou": True, "corresponde": True}
    upload = SimpleNamespace(method="POST", url="https://docs.google.com/upload", failure=rede)
    preflight = SimpleNamespace(method="OPTIONS", url=upload.url)
    picker_rpc = SimpleNamespace(
        method="POST", url="https://docs.google.com/rpc", frame=iframe.element_handle().content_frame(),
    )

    def aguardar_upload(iframe, selecionar):
        eventos["response"](SimpleNamespace(request=preflight, status=204, headers={}))
        eventos["response"](SimpleNamespace(request=picker_rpc, status=503, headers={}))
        for codigo in status:
            eventos["response"](SimpleNamespace(request=upload, status=codigo, headers=cabecalhos))
        if rede:
            eventos["requestfailed"](upload)
        raise TimeoutError("O seletor permaneceu aberto")

    monkeypatch.setattr(mymaps, "_aguardar_fim_do_upload", aguardar_upload)
    with pytest.raises(mymaps.ErroMapa) as erro:
        mymaps._enviar_csv(pagina, camada_local)
    assert type(erro.value) is tipo


@pytest.mark.parametrize("ocorrencias", [0, 2])
def test_rejeita_coluna_ausente_ou_duplicada_no_editor(ocorrencias):
    dialogo = Mock()
    campo = dialogo.get_by_role.return_value.or_.return_value
    campo.evaluate.side_effect = ["SELECT", ocorrencias]
    with pytest.raises(mymaps.ErroMapa, match="ausente ou é ambígua"):
        mymaps._selecionar_coluna(dialogo, mymaps._DADOS_CAMADA, "CHAVE")
    campo.select_option.assert_not_called()


@pytest.fixture
def correspondencia_radio(pagina):
    opcoes = pagina.locator.return_value.and_.return_value
    opcoes.first.is_visible.return_value = True
    painel = opcoes.locator.return_value
    grupos = {seletor: Mock() for seletor in (mymaps._RADIOS_CAMADA, mymaps._RADIOS_CSV)}
    painel.locator.side_effect = lambda seletor: grupos.get(seletor, painel)
    radios = [grupo.get_by_role.return_value.and_.return_value for grupo in grupos.values()]
    for radio, nome in zip(radios, ("\ufeffID", "ID")):
        radio.locator.return_value.get_attribute.return_value = nome
        radio.get_attribute.return_value = "false"
    return painel, grupos, radios


def test_seleciona_id_em_ambos_os_grupos_com_ou_sem_bom(pagina, correspondencia_radio):
    painel, grupos, radios = correspondencia_radio
    selecionado, _ = mymaps._preparar_correspondencia(pagina, "ID")
    assert selecionado is painel
    for grupo in grupos.values():
        nome = grupo.get_by_role.call_args.kwargs["name"]
        assert nome.fullmatch("ID") and nome.fullmatch("\ufeffID")
        assert not nome.fullmatch("OutroID")
    for radio in radios:
        radio.click.assert_called_once()
        radio.and_.return_value.wait_for.assert_called_once_with(state="visible")


def test_nome_divergente_no_csv_impede_marcar_qualquer_lado(pagina, correspondencia_radio):
    _, _, radios = correspondencia_radio
    radios[1].locator.return_value.get_attribute.return_value = "Outra"
    with pytest.raises(mymaps.ErroMapa, match="não corresponde ao configurado"):
        mymaps._preparar_correspondencia(pagina, "ID")
    for radio in radios:
        radio.click.assert_not_called()


@pytest.fixture
def importacao(pagina, monkeypatch):
    estado = Mock()
    avisos = Mock()
    locators = dict(visivel=Mock(), sucesso=Mock(), falha=Mock(), captcha=Mock(), radios=Mock(), butterbar=Mock())
    locators["captcha"].count.return_value = 0
    locators["falha"].count.return_value = 0
    locators["radios"].and_.return_value.first.is_visible.return_value = False
    pagina.locator.side_effect = lambda css: (
        locators["radios"] if css == mymaps._RADIOS_CAMADA
        else locators["visivel"] if css == ":visible"
        else locators["butterbar"] if css == mymaps._SELETOR_AVISO_CAMADA
        else avisos if 'role="status"' in css else locators["captcha"]
    )

    def aviso(regex):
        candidato = Mock()
        alternativas = candidato.or_.return_value
        if regex.search("Import successful"):
            alternativas.or_.return_value.and_.return_value = locators["sucesso"]
        else:
            alternativas.and_.return_value = locators["falha"]
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
    estado.enviar.assert_called_once_with(pagina, CAMADA, arrastar_csv=False)
    assert [chamada.args for chamada in estado.coluna.call_args_list] == [
        (dialogo, mymaps._DADOS_CAMADA, "CHAVE"), (dialogo, mymaps._DADOS_ENVIADOS, "CHAVE"),
    ]
    dialogo.get_by_role.return_value.click.assert_called_once()
    locators["butterbar"].get_by_text.assert_called_once_with(
        "A camada foi atualizada com novo conteúdo.", exact=True,
    )
    locators["sucesso"].first.wait_for.assert_called_once_with(state="hidden")
    locators["sucesso"].or_.return_value.first.wait_for.assert_called_once_with(state="visible", timeout=45_000)
    dialogo.wait_for.assert_called_once_with(state="hidden")


def test_aviso_anterior_ainda_visivel_impede_concluir(pagina, importacao):
    _, remota, dialogo, locators = importacao
    locators["sucesso"].first.wait_for.side_effect = TimeoutError("AVISO_ANTERIOR")
    with pytest.raises(mymaps.ErroMapa, match="confirmar o resultado"):
        mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    dialogo.get_by_role.return_value.click.assert_not_called()


@pytest.mark.parametrize(("rotulo", "aceito"), [
    ("Atualizar itens relacionados", True),
    ("Atualizar itens correspondentes", True),
    ("Update matching items", True),
    ("Mesclar itens relacionados", False),
    ("Substituir todos os itens", False),
])
def test_aceita_apenas_rotulos_da_atualizacao_por_correspondencia(rotulo, aceito):
    assert bool(mymaps._CORRESPONDENTES.fullmatch(rotulo)) is aceito


def test_falha_na_opcao_de_itens_relacionados_informa_etapa_e_impede_upload(pagina, importacao):
    estado, remota, _, _ = importacao
    opcoes = [Mock(), Mock(), Mock()]
    opcoes[-1].click.side_effect = TimeoutError("DETALHE_FICTICIO")
    estado.menu.side_effect = opcoes
    with pytest.raises(mymaps.ErroMapa, match='selecionar "Atualizar itens relacionados"') as erro:
        mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    assert "DETALHE_FICTICIO" not in str(erro.value)
    estado.enviar.assert_not_called()


def test_falha_no_picker_impede_confirmacao(pagina, importacao):
    estado, remota, dialogo, _ = importacao
    estado.enviar.side_effect = TimeoutError("DETALHE_FICTICIO")
    with pytest.raises(mymaps.ErroMapa, match="enviar o CSV") as erro:
        mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    assert "DETALHE_FICTICIO" not in str(erro.value)
    dialogo.get_by_role.return_value.click.assert_not_called()


def test_aviso_de_falha_no_picker_impede_retentativa(pagina, importacao):
    estado, remota, dialogo, locators = importacao
    locators["falha"].count.return_value = 1
    estado.enviar.side_effect = mymaps.ErroUploadTemporario("Tempo esgotado ao preparar o campo.")
    with pytest.raises(mymaps.ErroMapa, match="indicou falha") as erro:
        mymaps.reimportar_camada(pagina, MAPA, remota, CAMADA, "CHAVE")
    assert type(erro.value) is mymaps.ErroMapa
    assert "Tempo esgotado ao preparar o campo." in str(erro.value)
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
