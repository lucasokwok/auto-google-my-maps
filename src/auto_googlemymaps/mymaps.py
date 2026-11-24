"""Interações com o editor do My Maps e reimportação por correspondência."""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

from playwright.sync_api import Error, Frame, FrameLocator, JSHandle, Locator, Page, Request, Response, TimeoutError

from .configuracao import ErroConfiguracao, Mapa, identificador_mapa
from .csvs import Camada
from .navegador import ErroAutenticacao, exigir_sessao

_OPCOES_CAMADA = re.compile(r"^(?:Layer options|Opções (?:da|de) camada)$", re.IGNORECASE)
_CONTROLE_VISIBILIDADE = (
    '@role="checkbox" or self::input[@type="checkbox"] or '
    'contains(concat(" ", normalize-space(@class), " "), " goog-checkbox ")'
)
_REIMPORTAR_MESCLAR = re.compile(r"^(?:Reimport and merge|Reimportar e mesclar)\s*[►▸›]?$", re.IGNORECASE)
_REIMPORTAR = re.compile(r"^(?:Reimport|Reimportar)\s*[►▸›]?$", re.IGNORECASE)
_CORRESPONDENTES = re.compile(
    r"^(?:Update matching items|Atualizar itens (?:correspondentes|relacionados))$", re.IGNORECASE,
)
_ENVIAR = re.compile(r"^(?:Upload|Fazer upload|Enviar)$", re.IGNORECASE)
_PROCURAR = re.compile(r"^(?:Browse|Procurar)$", re.IGNORECASE)
_CAMPO_CSV_PICKER = 'input[type="file"][jsname="G1bupd"][accept*=".csv" i]'
_ARRASTAR_ARQUIVO = re.compile(r"^(?:ou arraste um arquivo até aqui|or drag (?:a file|files) here)$", re.IGNORECASE)
_SELECIONAR = re.compile(r"^(?:Select|Selecionar)$", re.IGNORECASE)
_DADOS_CAMADA = re.compile(r"^(?:Layer data|Dados da camada)\s*:?$", re.IGNORECASE)
_DADOS_ENVIADOS = re.compile(r"^(?:Uploaded data|Dados enviados|Dados carregados)\s*:?$", re.IGNORECASE)
_CONCLUIR = re.compile(r"^(?:Finish|Concluir)$", re.IGNORECASE)
_RADIOS_CAMADA = '[id^="upload-radio-left-"][data-name]'
_RADIOS_CSV = '[id^="upload-radio-right-"][data-name]'
_SELETOR_AVISO_CAMADA = '#butterbar-wrap [data-content-id="undo"] [aria-live="assertive"]'
_SUCESSO_CAMADA = "A camada foi atualizada com novo conteúdo."
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
_PAUSA_INICIALIZACAO_CAMPO_CSV_MS = 2_000
_PRAZO_UPLOAD_SEGUNDOS = 60
_HTTP_UPLOAD_TRANSITORIOS = {408, 500, 502, 503, 504}
_REDE_UPLOAD_TRANSITORIOS = {
    "ERR_CONNECTION_CLOSED", "ERR_CONNECTION_RESET", "ERR_CONNECTION_TIMED_OUT",
    "ERR_NETWORK_CHANGED", "ERR_TIMED_OUT",
}


class ErroMapa(RuntimeError):
    """Falha de operação que pode ser registrada sem divulgar dados do mapa."""


class ErroUploadTemporario(ErroMapa):
    """Falha na seleção ou no envio do CSV que admite uma nova tentativa."""


class _SeletorUploadPendente(TimeoutError):
    """O Picker continuou aberto até o prazo, antes do assistente de correspondência."""


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


def _opcoes_camada(escopo: Page | Locator) -> Locator:
    return escopo.get_by_label(_OPCOES_CAMADA).or_(
        escopo.get_by_role("button", name=_OPCOES_CAMADA)
    ).or_(escopo.get_by_title(_OPCOES_CAMADA))


def localizar_camada(pagina: Page, nome: str) -> CamadaRemota:
    titulo = pagina.get_by_text(nome, exact=True).and_(pagina.locator(":visible"))
    # O menu e o seletor de visibilidade delimitam o cabeçalho, antes da lista de pontos.
    cabecalhos = _opcoes_camada(pagina).locator(
        f'xpath=ancestor::*[not(self::body or self::html) and .//*[{_CONTROLE_VISIBILIDADE}]][1]'
    )
    cabecalho = cabecalhos.filter(has=titulo)
    opcoes = _opcoes_camada(cabecalho)
    etapa = "O nome exato da camada não apareceu na página do editor."
    try:
        titulo.first.wait_for(state="visible")
        etapa = "Não foi possível associar o título a um único menu de camada na legenda."
        cabecalho.wait_for(state="visible")
        cabecalho.locator(f'xpath=.//*[{_CONTROLE_VISIBILIDADE}]').wait_for(state="attached")
        cabecalho.get_by_text(nome, exact=True).and_(cabecalho.locator(":visible")).wait_for(state="visible")
        opcoes.wait_for(state="attached")
    except Error:
        exigir_sessao(pagina)
        raise ErroMapa(etapa) from None
    return CamadaRemota(cabecalho, opcoes)


def _item_menu(pagina: Page, nome: re.Pattern[str]) -> Locator:
    return pagina.get_by_text(nome).and_(pagina.locator(":visible"))


def _conferir_csv_local(camada: Camada) -> None:
    try:
        if camada.arquivo.is_symlink() or not camada.arquivo.is_file():
            raise OSError
        with camada.arquivo.open("rb") as arquivo:
            if arquivo.read(len(camada.conteudo) + 1) != camada.conteudo:
                raise ErroMapa("O CSV mudou desde a validação. Rode a atualização novamente com o arquivo estável.")
    except OSError:
        raise ErroMapa("O CSV validado não está acessível para o navegador.") from None


def _requisicao_de_upload(requisicao: Request, quadro: Frame | None) -> bool:
    destino = urlsplit(requisicao.url)
    dominio = destino.hostname or ""
    origem_google = dominio == "google.com" or dominio.endswith(
        (".google.com", ".googleapis.com", ".googleusercontent.com"),
    )
    if not origem_google or destino.scheme != "https" or requisicao.method not in {"POST", "PUT", "PATCH", "OPTIONS"}:
        return False
    if "upload" in destino.path.lower():
        return True
    if quadro is not None:
        with suppress(Error):
            return requisicao.frame == quadro
    return False


def _observar_campo_csv(campo: Locator, camada: Camada) -> JSHandle:
    return campo.evaluate_handle(
        """(entrada, esperado) => {
            const estado = {mudou: false, corresponde: false};
            entrada.addEventListener("change", () => {
                const arquivo = entrada.files?.[0];
                estado.mudou = true;
                estado.corresponde = entrada.files?.length === 1 &&
                    arquivo.name === esperado.nome && arquivo.size === esperado.bytes;
            }, {capture: true, once: true});
            return estado;
        }""",
        {"nome": camada.nome, "bytes": len(camada.conteudo)},
    )


def _diagnosticar_campo_csv(estado: JSHandle | None) -> str:
    if estado is None:
        return ""
    with suppress(Error):
        observado = estado.json_value()
        if observado["corresponde"]:
            return " O campo recebeu um arquivo com o nome e tamanho esperados."
        if observado["mudou"]:
            return " O campo mudou, mas o arquivo não corresponde ao nome e tamanho esperados."
        return " O campo não emitiu o evento de seleção do arquivo."
    return " O estado do campo de arquivo ficou indisponível."


def _diagnosticar_picker(picker: FrameLocator, selecionar: Locator) -> str:
    with suppress(Error):
        estado_selecionar = "ausente"
        if selecionar.first.is_visible():
            estado_selecionar = "habilitado" if selecionar.first.is_enabled(timeout=500) else "desabilitado"
        procurar = "visível" if picker.get_by_role("button", name=_PROCURAR).first.is_visible() else "ausente"
        progresso = "visível" if picker.get_by_role("progressbar").first.is_visible() else "ausente"
        alerta = "visível" if picker.get_by_role("alert").first.is_visible() else "ausente"
        return (
            f" Seletor aberto — Selecionar: {estado_selecionar}, Procurar: {procurar}, "
            f"progresso: {progresso}, alerta: {alerta}."
        )
    return " O estado dos controles do seletor ficou indisponível."


def _soltar_arquivo(pagina: Page, zona: Locator, arquivo: Path) -> None:
    zona.hover()
    caixa = zona.bounding_box()
    if caixa is None:
        raise ErroMapa("A área de arrastar o CSV não está visível no seletor do Google.")
    posicao = {"x": caixa["x"] + caixa["width"] / 2, "y": caixa["y"] + caixa["height"] / 2}
    # O protocolo Chromium usa a máscara 1 para a operação de cópia.
    dados = {"items": [], "files": [str(arquivo)], "dragOperationsMask": 1}
    sessao = pagina.context.new_cdp_session(pagina)
    try:
        for evento in ("dragEnter", "dragOver", "drop"):
            sessao.send("Input.dispatchDragEvent", {"type": evento, **posicao, "data": dados})
    finally:
        sessao.detach()


def _enviar_csv(pagina: Page, camada: Camada, *, arrastar_csv: bool = False) -> None:
    _conferir_csv_local(camada)
    iframe = pagina.locator(_IFRAME_PICKER).and_(pagina.locator(":visible"))
    picker: FrameLocator = iframe.content_frame
    upload = picker.get_by_role("option", name=_ENVIAR).or_(picker.get_by_role("tab", name=_ENVIAR)).or_(
        picker.get_by_role("button", name=_ENVIAR)
    )
    selecionar = picker.get_by_role("button", name=_SELECIONAR)

    quadro = None
    status_http: set[int] = set()
    status_envio: set[int] = set()
    falhas_de_rede = 0
    codigos_de_rede: set[str] = set()
    falhas_envio: set[str] = set()
    servidor_pediu_espera = False
    estado_campo = None
    envio_iniciado = False
    etapa = "aguardar a abertura do seletor de arquivos do Google"

    def registrar_resposta(resposta: Response) -> None:
        nonlocal servidor_pediu_espera
        requisicao = resposta.request
        if not _requisicao_de_upload(requisicao, quadro):
            return
        status_http.add(resposta.status)
        if _requisicao_de_upload(requisicao, None):
            # Uma resposta à verificação CORS não confirma o recebimento do arquivo.
            if requisicao.method != "OPTIONS":
                status_envio.add(resposta.status)
            if resposta.status >= 400 and resposta.headers.get("retry-after"):
                servidor_pediu_espera = True

    def registrar_falha(requisicao: Request) -> None:
        nonlocal falhas_de_rede
        if _requisicao_de_upload(requisicao, quadro):
            falhas_de_rede += 1
            falha = requisicao.failure or ""
            if re.fullmatch(r"(?:net::)?ERR_[A-Z0-9_]+", falha):
                codigo = falha.removeprefix("net::")
                codigos_de_rede.add(codigo)
                if _requisicao_de_upload(requisicao, None):
                    falhas_envio.add(codigo)

    pagina.on("response", registrar_resposta)
    pagina.on("requestfailed", registrar_falha)
    try:
        iframe.wait_for(state="visible")
        etapa = 'abrir "Fazer upload" no seletor do Google'
        upload.click()
        etapa = "localizar o quadro de upload"
        quadro = iframe.element_handle().content_frame()

        if arrastar_csv:
            etapa = "soltar o CSV na área de upload"
            _conferir_csv_local(camada)
            envio_iniciado = True
            _soltar_arquivo(pagina, picker.get_by_text(_ARRASTAR_ARQUIVO), camada.arquivo)
        else:
            campo = picker.locator(_CAMPO_CSV_PICKER)
            etapa = "localizar o campo de arquivo do Picker"
            try:
                campo.wait_for(state="attached", timeout=2_000)
            except TimeoutError:
                etapa = 'abrir o seletor nativo pelo botão "Procurar"'
                with pagina.expect_file_chooser() as escolha:
                    picker.get_by_role("button", name=_PROCURAR).click()
                etapa = "entregar o CSV ao seletor nativo"
                _conferir_csv_local(camada)
                envio_iniciado = True
                escolha.value.set_files(camada.arquivo)
            else:
                etapa = "preparar o campo de arquivo do Picker"
                # O campo pode aparecer antes de o Picker estar pronto para receber o arquivo.
                pagina.wait_for_timeout(_PAUSA_INICIALIZACAO_CAMPO_CSV_MS)
                estado_campo = _observar_campo_csv(campo, camada)
                etapa = "entregar o CSV ao campo de arquivo do Picker"
                _conferir_csv_local(camada)
                envio_iniciado = True
                campo.set_input_files(camada.arquivo)

        etapa = "confirmar o fim do envio no seletor do Google"
        _aguardar_fim_do_upload(iframe, selecionar)
        _conferir_csv_local(camada)
    except (Error, OSError) as erro:
        exigir_sessao(pagina)
        _conferir_csv_local(camada)
        expirou = isinstance(erro, TimeoutError)
        seletor_pendente = isinstance(erro, _SeletorUploadPendente)
        motivo = "Tempo esgotado" if expirou else "Falha do navegador"
        codigos = ", ".join(str(codigo) for codigo in sorted(status_http)) or "nenhuma resposta reconhecida"
        erros_de_rede = f" ({', '.join(sorted(codigos_de_rede))})" if codigos_de_rede else ""
        envio_transitorio = bool(status_envio & _HTTP_UPLOAD_TRANSITORIOS or falhas_envio & _REDE_UPLOAD_TRANSITORIOS)
        houve_aceite = any(200 <= codigo < 300 or codigo == 308 for codigo in status_envio)
        houve_recusa = any(400 <= codigo < 500 and codigo not in _HTTP_UPLOAD_TRANSITORIOS for codigo in status_http)
        prazo_antes_da_entrega = expirou and not envio_iniciado
        # Uma resposta de sucesso do upload ainda pode deixar o Picker aberto, antes de Concluir.
        erro_transitorio = seletor_pendente or (not houve_aceite and (envio_transitorio or prazo_antes_da_entrega))
        pode_repetir = (
            erro_transitorio and not (houve_recusa or servidor_pediu_espera or pagina.is_closed())
        )
        tipo = ErroUploadTemporario if pode_repetir else ErroMapa
        espera = " O servidor pediu um intervalo antes de nova tentativa." if servidor_pediu_espera else ""
        controles = _diagnosticar_picker(picker, selecionar) if seletor_pendente else ""
        raise tipo(
            f"{motivo} ao {etapa}. "
            f"HTTP do upload: {codigos}. Falhas de rede observadas: {falhas_de_rede}{erros_de_rede}."
            f"{_diagnosticar_campo_csv(estado_campo)}{controles}{espera}"
        ) from None
    finally:
        if estado_campo is not None:
            with suppress(Error):
                estado_campo.dispose()
        pagina.remove_listener("requestfailed", registrar_falha)
        pagina.remove_listener("response", registrar_resposta)


def _aguardar_fim_do_upload(iframe: Locator, selecionar: Locator) -> None:
    prazo = monotonic() + _PRAZO_UPLOAD_SEGUNDOS
    # O Picker pode fechar sozinho ou oferecer Selecionar quando o arquivo estiver pronto.
    while (restante := int((prazo - monotonic()) * 1000)) > 0:
        if not iframe.is_visible():
            return
        confirmar = False
        try:
            confirmar = selecionar.is_visible() and selecionar.is_enabled(timeout=min(restante, 500))
            if confirmar:
                selecionar.click(timeout=restante)
            restante = max(1, int((prazo - monotonic()) * 1000))
            iframe.wait_for(state="hidden", timeout=restante if confirmar else min(restante, 500))
            return
        except TimeoutError:
            if confirmar:
                break
        except Error:
            if iframe.is_visible():
                raise
            return
    if iframe.is_visible():
        raise _SeletorUploadPendente("O seletor de arquivos continuou aberto após o envio do CSV.")


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


def _preparar_correspondencia(pagina: Page, coluna: str) -> tuple[Locator, Locator]:
    visivel = pagina.locator(":visible")
    opcoes_camada = pagina.locator(_RADIOS_CAMADA).and_(visivel)
    campo_camada = pagina.get_by_role("combobox", name=_DADOS_CAMADA).or_(
        pagina.get_by_role("button", name=_DADOS_CAMADA)
    )
    dialogo_lista = pagina.get_by_role("dialog").filter(has=campo_camada)
    opcoes_camada.or_(dialogo_lista.and_(visivel)).first.wait_for(state="visible")
    if not opcoes_camada.first.is_visible():
        _selecionar_coluna(dialogo_lista, _DADOS_CAMADA, coluna)
        _selecionar_coluna(dialogo_lista, _DADOS_ENVIADOS, coluna)
        return dialogo_lista, dialogo_lista.get_by_role("button", name=_CONCLUIR)

    # Os dois grupos pertencem ao mesmo painel, mesmo quando o editor não usa role="dialog".
    painel = opcoes_camada.locator(
        'xpath=ancestor::*[not(self::html or self::body) and '
        './/*[@data-name and starts-with(@id, "upload-radio-right-")]][1]'
    )
    painel.wait_for(state="visible")
    nome = re.compile(rf"^\ufeff?{re.escape(coluna)}$")
    radios = [
        painel.locator(grupo).get_by_role("radio", name=nome).and_(visivel)
        for grupo in (_RADIOS_CAMADA, _RADIOS_CSV)
    ]
    for radio in radios:
        # Limitar a compatibilidade com BOM a um marcador inicial no nome da coluna.
        if radio.locator("xpath=..").get_attribute("data-name") not in {coluna, "\ufeff" + coluna}:
            raise ErroMapa("O nome da coluna de identificação no seletor não corresponde ao configurado.")
    for radio in radios:
        if radio.get_attribute("aria-checked") != "true":
            radio.click()
    for radio in radios:
        radio.and_(pagina.locator('[aria-checked="true"]')).wait_for(state="visible")

    concluir = pagina.get_by_role("button", name=_CONCLUIR).and_(visivel)
    assistente = painel.locator("xpath=ancestor-or-self::*[not(self::html or self::body)]").filter(has=concluir).last
    return painel, assistente.get_by_role("button", name=_CONCLUIR).and_(visivel)


def reimportar_camada(
    pagina: Page, mapa: Mapa, remota: CamadaRemota, camada: Camada, coluna_identificacao: str,
    *, arrastar_csv: bool = False,
) -> None:
    visivel = pagina.locator(":visible")
    avisos = pagina.locator('[role="status"], [role="alert"], [aria-live], [role="dialog"]')
    aviso_da_camada = pagina.locator(_SELETOR_AVISO_CAMADA).get_by_text(_SUCESSO_CAMADA, exact=True)
    sucesso = avisos.get_by_text(_SUCESSO).or_(avisos.filter(has_text=_SUCESSO)).or_(aviso_da_camada).and_(visivel)
    falha = avisos.get_by_text(_FALHA).or_(avisos.filter(has_text=_FALHA)).and_(visivel)
    etapa = "abrir o menu de opções da camada"
    enviada = False
    try:
        _confirmar_destino(pagina, mapa)
        remota.cabecalho.hover()
        remota.opcoes.click()
        etapa = 'selecionar "Reimportar e mesclar"'
        _item_menu(pagina, _REIMPORTAR_MESCLAR).click()
        etapa = 'selecionar "Reimportar"'
        _item_menu(pagina, _REIMPORTAR).click()
        etapa = 'selecionar "Atualizar itens relacionados"'
        _item_menu(pagina, _CORRESPONDENTES).click()

        etapa = "enviar o CSV no seletor de arquivos do Google"
        _confirmar_destino(pagina, mapa)
        _enviar_csv(pagina, camada, arrastar_csv=arrastar_csv)

        etapa = "selecionar a coluna de identificação nos dados da camada e do CSV"
        _confirmar_destino(pagina, mapa)
        dialogo, concluir = _preparar_correspondencia(pagina, coluna_identificacao)

        etapa = "confirmar o resultado da reimportação na interface"
        sucesso.first.wait_for(state="hidden")
        if falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU)
        _confirmar_destino(pagina, mapa)
        concluir.wait_for(state="visible")
        enviada = True
        concluir.click()
        sucesso.or_(falha).first.wait_for(state="visible", timeout=45_000)
        if falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU)
        dialogo.wait_for(state="hidden")
        _confirmar_destino(pagina, mapa)
        if falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU)
    except ErroUploadTemporario as erro:
        if not pagina.is_closed() and falha.count():
            raise ErroMapa(f"{_IMPORTACAO_FALHOU} {erro}") from None
        raise
    except Error:
        exigir_sessao(pagina)
        if not pagina.is_closed() and falha.count():
            raise ErroMapa(_IMPORTACAO_FALHOU) from None
        if enviada:
            raise ErroMapa(
                "Resultado indeterminado após enviar a atualização. Confira a camada antes de tentar novamente."
            ) from None
        raise ErroMapa(f"Não foi possível {etapa}. Confira a interface atual do My Maps.") from None
