"""Interações com o editor do My Maps e reimportação por correspondência."""

from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Error, FrameLocator, Locator, Page

from .configuracao import ErroConfiguracao, Mapa, identificador_mapa
from .csvs import Camada
from .navegador import ErroAutenticacao, exigir_sessao

_OPCOES_CAMADA = re.compile(r"^(?:Layer options|Opções da camada)$", re.IGNORECASE)
_REIMPORTAR_MESCLAR = re.compile(r"^(?:Reimport and merge|Reimportar e mesclar)\s*[►▸›]?$", re.IGNORECASE)
_REIMPORTAR = re.compile(r"^(?:Reimport|Reimportar)\s*[►▸›]?$", re.IGNORECASE)
_CORRESPONDENTES = re.compile(r"^(?:Update matching items|Atualizar itens correspondentes)$", re.IGNORECASE)
_ENVIAR = re.compile(r"^(?:Upload|Fazer upload|Enviar)$", re.IGNORECASE)
_SELECIONAR = re.compile(r"^(?:Select|Selecionar)$", re.IGNORECASE)
_DADOS_CAMADA = re.compile(r"^(?:Layer data|Dados da camada)\s*:?$", re.IGNORECASE)
_DADOS_ENVIADOS = re.compile(r"^(?:Uploaded data|Dados enviados|Dados carregados)\s*:?$", re.IGNORECASE)
_CONCLUIR = re.compile(r"^(?:Finish|Concluir)$", re.IGNORECASE)
_SUCESSO = re.compile(
    r"^(?:Import (?:complete|successful)|(?:Data|Items) (?:imported|updated) successfully|"
    r"Importação (?:concluída|bem-sucedida)|(?:Dados|Itens) (?:importados|atualizados) com sucesso)[.!]?$",
    re.IGNORECASE,
)
_FALHA = re.compile(
    r"^(?:Import failed|(?:Could not|Couldn't|Unable to) import|An error occurred|"
    r"Some rows could not be displayed|Falha na importação|Não foi possível importar|"
    r"Ocorreu um erro|Algumas linhas não puderam ser exibidas)\b",
    re.IGNORECASE,
)
_IMPORTACAO_FALHOU = "A interface indicou falha na importação. Confira a camada antes de tentar novamente."
_IFRAME_PICKER = (
    'iframe.picker-frame, iframe[src^="https://docs.google.com/picker"], '
    'iframe[src^="https://drive.google.com/picker"], iframe[src^="https://www.google.com/picker"]'
)


class ErroMapa(RuntimeError):
    """Falha de operação que pode ser registrada sem divulgar dados do mapa."""


@dataclass(frozen=True)
class CamadaRemota:
    cabecalho: Locator
    opcoes: Locator


def _confirmar_destino(pagina: Page, mapa: Mapa) -> None:
    exigir_sessao(pagina)
    try:
        mesmo_mapa = identificador_mapa(pagina.url) == identificador_mapa(mapa.url)
    except ErroConfiguracao:
        mesmo_mapa = False
    if not mesmo_mapa:
        raise ErroMapa("O destino aberto não é o editor do mapa cadastrado. Confira o link e as permissões.")


def abrir_mapa(pagina: Page, mapa: Mapa) -> None:
    try:
        resposta = pagina.goto(mapa.url, wait_until="domcontentloaded")
        _confirmar_destino(pagina, mapa)
        if resposta is None or not resposta.ok:
            if resposta is not None and resposta.status == 401:
                raise ErroAutenticacao(
                    "Sessão Google não autorizada. Execute login com o mesmo --navegador e --perfil-dir."
                )
            raise ErroMapa("O Google não abriu o editor. Confira o acesso de edição ao mapa.")
    except Error:
        exigir_sessao(pagina)
        raise ErroMapa("O navegador não concluiu a abertura do editor do mapa.") from None


def localizar_camada(pagina: Page, nome: str) -> CamadaRemota:
    # O rótulo da camada está associado ao controle de visibilidade na legenda.
    rotulo = pagina.get_by_text(nome, exact=True).and_(pagina.locator('label[for^="layer "]:visible'))
    seletor_checkbox = '[role="checkbox"][id^="layer "]'
    cabecalho = rotulo.locator(
        'xpath=ancestor::*[.//*[@role="checkbox" and starts-with(@id, "layer ")]][1]'
    )
    controle = cabecalho.locator(seletor_checkbox)
    opcoes = cabecalho.get_by_label(_OPCOES_CAMADA).or_(cabecalho.get_by_role("button", name=_OPCOES_CAMADA))
    etapa = "Camada ausente ou ambígua na legenda. Confira o nome exato no editor."
    try:
        rotulo.wait_for(state="visible")
        etapa = "Não foi possível associar o título a um único controle da camada na legenda."
        controle.wait_for(state="attached")
        if controle.get_attribute("id") != rotulo.get_attribute("for"):
            raise ErroMapa(etapa)
        etapa = "O menu de opções desta camada não apareceu no editor."
        opcoes.wait_for(state="attached")
    except Error:
        exigir_sessao(pagina)
        raise ErroMapa(etapa) from None
    return CamadaRemota(cabecalho, opcoes)


def _item_menu(pagina: Page, nome: re.Pattern[str]) -> Locator:
    return pagina.get_by_text(nome).and_(pagina.locator(":visible"))


def _enviar_csv(pagina: Page, camada: Camada) -> None:
    iframe = pagina.locator(_IFRAME_PICKER).and_(pagina.locator(":visible"))
    picker: FrameLocator = iframe.content_frame
    upload = picker.get_by_role("option", name=_ENVIAR).or_(picker.get_by_role("tab", name=_ENVIAR)).or_(
        picker.get_by_role("button", name=_ENVIAR)
    )
    upload.click()
    arquivo = picker.locator('input[type="file"]')
    arquivo.set_input_files({"name": camada.nome, "mimeType": "text/csv", "buffer": camada.conteudo})
    selecionar = picker.get_by_role("button", name=_SELECIONAR)
    if selecionar.is_visible():
        try:
            selecionar.click()
        except Error:
            # O Picker também pode concluir o upload e fechar sem este botão.
            if iframe.is_visible():
                raise


def _selecionar_coluna(dialogo: Locator, rotulo: re.Pattern[str], coluna: str) -> None:
    campo = dialogo.get_by_role("combobox", name=rotulo).or_(dialogo.get_by_role("button", name=rotulo))
    if campo.evaluate("(elemento) => elemento.tagName") == "SELECT":
        ocorrencias = campo.evaluate(
            "(el, coluna) => Array.from(el.options).filter(opcao => opcao.label === coluna).length", coluna,
        )
        if ocorrencias != 1:
            raise ErroMapa("A coluna de identificação configurada está ausente ou é ambígua na interface.")
        campo.select_option(label=coluna)
        return
    campo.click()
    dialogo.get_by_role("option", name=coluna, exact=True).or_(
        dialogo.get_by_role("menuitem", name=coluna, exact=True)
    ).click()
    if campo.get_attribute("aria-valuetext") != coluna and not campo.get_by_text(coluna, exact=True).count():
        raise ErroMapa("A interface não confirmou a seleção da coluna de identificação.")


def reimportar_camada(
    pagina: Page, mapa: Mapa, remota: CamadaRemota, camada: Camada, coluna_identificacao: str,
) -> None:
    visivel = pagina.locator(":visible")
    avisos = pagina.locator('[role="status"], [role="alert"], [aria-live], [role="dialog"]')
    sucesso = avisos.get_by_text(_SUCESSO).or_(avisos.filter(has_text=_SUCESSO)).and_(visivel)
    falha = avisos.get_by_text(_FALHA).or_(avisos.filter(has_text=_FALHA)).and_(visivel)
    etapa = "abrir o menu de reimportação por correspondência"
    enviada = False
    try:
        _confirmar_destino(pagina, mapa)
        remota.cabecalho.hover()
        remota.opcoes.click()
        _item_menu(pagina, _REIMPORTAR_MESCLAR).click()
        _item_menu(pagina, _REIMPORTAR).click()
        _item_menu(pagina, _CORRESPONDENTES).click()

        etapa = "enviar o CSV no seletor de arquivos do Google"
        _confirmar_destino(pagina, mapa)
        _enviar_csv(pagina, camada)

        etapa = "selecionar a coluna de identificação nos dados da camada e do CSV"
        # O nome acessível dos dois campos identifica o assistente de correspondência.
        campo_camada = pagina.get_by_role("combobox", name=_DADOS_CAMADA).or_(
            pagina.get_by_role("button", name=_DADOS_CAMADA)
        )
        dialogo = pagina.get_by_role("dialog").filter(has=campo_camada)
        _selecionar_coluna(dialogo, _DADOS_CAMADA, coluna_identificacao)
        _selecionar_coluna(dialogo, _DADOS_ENVIADOS, coluna_identificacao)

        etapa = "confirmar o resultado da reimportação na interface"
        sucesso.first.wait_for(state="hidden")
        if falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU)
        _confirmar_destino(pagina, mapa)
        enviada = True
        dialogo.get_by_role("button", name=_CONCLUIR).click()
        sucesso.or_(falha).first.wait_for(state="visible", timeout=45_000)
        if falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU)
        dialogo.wait_for(state="hidden")
        _confirmar_destino(pagina, mapa)
        if falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU)
    except Error:
        exigir_sessao(pagina)
        if not pagina.is_closed() and falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU) from None
        if enviada:
            raise ErroMapa(
                "Resultado indeterminado após enviar a atualização. Confira a camada antes de tentar novamente."
            ) from None
        raise ErroMapa(f"Não foi possível {etapa}. Confira a interface atual do My Maps.") from None
