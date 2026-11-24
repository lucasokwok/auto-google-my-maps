import json
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pytest

from auto_googlemymaps import atualizacao
from auto_googlemymaps.__main__ import main
from auto_googlemymaps.csvs import CAMADAS
from auto_googlemymaps.mymaps import ErroAtualizacaoRevertida, ErroMapa, ErroUploadTemporario
from auto_googlemymaps.navegador import ErroAutenticacao

CSV = b"CHAVE,Latitude,Longitude,Nome\nID_FICTICIO,0,0,DADO_FICTICIO\n"


@pytest.fixture
def execucao(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config"
    config.mkdir()
    mapas = [
        {"NomeMapa": nome, "URL": f"https://www.google.com/maps/d/edit?mid=FICTICIO_{nome}"}
        for nome in ("A", "B", "C")
    ]
    (config / "mapas.json").write_text(
        json.dumps({"coluna_identificacao": "CHAVE", "mapas": mapas}), encoding="utf-8",
    )
    for mapa, quantidade in zip(mapas, (2, 1, 5)):
        pasta = tmp_path / "MAPAS" / mapa["NomeMapa"]
        pasta.mkdir(parents=True)
        for nome in CAMADAS[:quantidade]:
            (pasta / nome).write_bytes(CSV)

    chamadas = Mock()
    chamadas.abrir_navegador.return_value = nullcontext(chamadas.contexto)
    chamadas.localizar.side_effect = lambda pagina, nome: nome
    monkeypatch.setattr(atualizacao, "abrir_navegador", chamadas.abrir_navegador)
    monkeypatch.setattr(atualizacao, "abrir_mapa", chamadas.abrir_mapa)
    monkeypatch.setattr(atualizacao, "localizar_camada", chamadas.localizar)
    monkeypatch.setattr(atualizacao, "reimportar_camada", chamadas.reimportar)
    return chamadas


@pytest.mark.parametrize("acao", ["validar", "planejar"])
def test_comando_local_nao_inicia_navegador(execucao, acao, capsys):
    assert main([acao]) == 0
    execucao.abrir_navegador.assert_not_called()
    saida = capsys.readouterr().out
    assert "B — 1 camada" in saida and "C — 5 camada" in saida
    assert "mid=" not in saida


def test_filtra_um_mapa_e_valida_todas_as_camadas_antes_de_enviar(execucao, tmp_path):
    (tmp_path / "MAPAS" / "B" / CAMADAS[0]).unlink()
    assert main(["atualizar", "--mapa", "A", "--perfil-dir", "runtime/isolado"]) == 0
    assert [chamada.args[1].nome for chamada in execucao.abrir_mapa.call_args_list] == ["A"]
    etapas = [chamada[0] for chamada in execucao.mock_calls
              if chamada[0] in {"abrir_mapa", "localizar", "reimportar"}]
    assert etapas == ["abrir_mapa", "localizar", "localizar", "reimportar", "reimportar"]
    assert [chamada.args[2] for chamada in execucao.reimportar.call_args_list] == list(CAMADAS[:2])
    assert all(chamada.args[3].conteudo == CSV and chamada.args[4] == "CHAVE"
               for chamada in execucao.reimportar.call_args_list)
    assert execucao.abrir_navegador.call_args.args[0].as_posix() == "runtime/isolado"
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "pontos_02.csv — atualização confirmada" in log
    assert all(valor not in log for valor in ("mid=", "FICTICIO_A", "DADO_FICTICIO", "ID_FICTICIO"))


def test_rejeita_mapa_desconhecido(execucao):
    assert main(["atualizar", "--mapa", "DESCONHECIDO"]) == 2
    execucao.abrir_navegador.assert_not_called()


def test_atualizar_com_edge_usa_o_mesmo_perfil_padrao_do_login(execucao):
    assert main(["atualizar", "--mapa", "B", "--navegador", "edge"]) == 0
    execucao.abrir_navegador.assert_called_once_with(Path("runtime/google_profile_edge"), navegador="edge")


def test_atualizar_com_arrastar_csv_encaminha_metodo_de_upload(execucao):
    assert main(["atualizar", "--mapa", "B", "--arrastar-csv"]) == 0
    assert execucao.reimportar.call_args.kwargs == {"arrastar_csv": True}


def test_dados_invalidos_bloqueiam_mapa_sem_impedir_validos(execucao, tmp_path):
    (tmp_path / "MAPAS" / "B" / CAMADAS[0]).write_bytes(b"")
    assert main(["atualizar"]) == 1
    assert [chamada.args[1].nome for chamada in execucao.abrir_mapa.call_args_list] == ["A", "C"]
    assert execucao.reimportar.call_count == 7
    execucao.abrir_navegador.assert_called_once()


def test_nenhum_csv_valido_nao_inicia_navegador(execucao, tmp_path):
    (tmp_path / "MAPAS" / "B" / CAMADAS[0]).unlink()
    assert main(["atualizar", "--mapa", "B", "--pausar-em-erro"]) == 1
    execucao.abrir_navegador.assert_not_called()


def test_camada_ausente_e_registrada_e_outra_camada_continua(execucao, tmp_path):
    execucao.localizar.side_effect = [ErroMapa("Camada ausente"), CAMADAS[1]]
    assert main(["atualizar", "--mapa", "A"]) == 1
    execucao.reimportar.assert_called_once()
    assert execucao.reimportar.call_args.args[3].nome == CAMADAS[1]
    execucao.contexto.new_page.return_value.close.assert_called_once()
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "A — pontos_01.csv — verificação da camada existente — Camada ausente" in log
    assert "A — pontos_02.csv — atualização confirmada" in log
    assert "A — atualização encerrada com falhas (1/2 camada(s) confirmada(s))" in log


@pytest.mark.parametrize("mensagem", ["Falha no seletor de upload", "Resultado indeterminado"])
def test_falha_de_camada_reabre_editor_e_continua_sem_repetir(execucao, tmp_path, mensagem):
    paginas = [Mock() for _ in range(4)]
    execucao.contexto.new_page.side_effect = paginas
    execucao.reimportar.side_effect = [ErroMapa(mensagem)] + [None] * 7
    assert main(["atualizar"]) == 1
    tentativas = [chamada.args for chamada in execucao.reimportar.call_args_list]
    assert [args[1].nome for args in tentativas] == ["A", "A", "B"] + ["C"] * 5
    assert [(args[0], args[3].nome) for args in tentativas[:2]] == list(zip(paginas[:2], CAMADAS[:2]))
    execucao.localizar.assert_any_call(paginas[1], CAMADAS[1])
    for pagina in paginas:
        pagina.close.assert_called_once()
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert f"A — pontos_01.csv — {mensagem} (0/2 camada(s) confirmada(s))" in log
    assert "A — pontos_02.csv — atualização confirmada" in log
    assert "C — atualização concluída" in log


def test_falha_ao_reabrir_editor_e_registrada_e_restante_continua(execucao, tmp_path):
    paginas = [Mock() for _ in range(3)]
    execucao.contexto.new_page.side_effect = paginas
    execucao.abrir_mapa.side_effect = [None, ErroMapa("Editor indisponível"), None]
    execucao.reimportar.side_effect = [ErroMapa("Falha inicial"), None, None, None]
    assert main(["atualizar", "--mapa", "C"]) == 1
    tentativas = [chamada.args for chamada in execucao.reimportar.call_args_list]
    assert [args[3].nome for args in tentativas] == [CAMADAS[0], *CAMADAS[2:]]
    assert [args[0] for args in tentativas] == [paginas[0], paginas[2], paginas[2], paginas[2]]
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "C — pontos_02.csv — Editor indisponível" in log
    assert "C — atualização encerrada com falhas (3/5 camada(s) confirmada(s))" in log


@pytest.mark.parametrize("recuperou", [True, False])
def test_upload_temporario_tem_uma_nova_tentativa_e_processa_a_proxima_camada(
    execucao, tmp_path, monkeypatch, recuperou,
):
    paginas = [Mock() for _ in range(2 if recuperou else 3)]
    execucao.contexto.new_page.side_effect = paginas
    erro = ErroUploadTemporario("HTTP do upload: 503.")
    execucao.reimportar.side_effect = [erro, None if recuperou else erro, None]
    pausa = Mock()
    monkeypatch.setattr(atualizacao, "sleep", pausa)

    assert main(["atualizar", "--mapa", "A"]) == (0 if recuperou else 1)
    pausa.assert_called_once_with(2)
    tentativas = [chamada.args for chamada in execucao.reimportar.call_args_list]
    assert [(args[0], args[3].nome) for args in tentativas] == [
        (paginas[0], CAMADAS[0]), (paginas[1], CAMADAS[0]), (paginas[-1], CAMADAS[1]),
    ]
    execucao.localizar.assert_any_call(paginas[1], CAMADAS[0])
    for pagina in paginas:
        pagina.close.assert_called_once()
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "A — pontos_01.csv — HTTP do upload: 503. Nova tentativa de upload em 2 s." in log
    assert "A — pontos_02.csv — atualização confirmada" in log
    assert ("ERROR" in log) is not recuperou


@pytest.mark.parametrize(("reversoes", "recuperou"), [(2, True), (5, True), (6, False)])
def test_reversao_permite_ate_cinco_retentativas_e_segue_para_a_proxima_camada(
    execucao, tmp_path, monkeypatch, reversoes, recuperou,
):
    erro = ErroAtualizacaoRevertida("Ocorreu um erro. Sua última ação foi revertida.")
    paginas = [Mock() for _ in range(reversoes + 1)]
    execucao.contexto.new_page.side_effect = paginas
    execucao.reimportar.side_effect = [erro] * reversoes + [None, None]
    pausa = Mock()
    monkeypatch.setattr(atualizacao, "sleep", pausa)

    assert main(["atualizar", "--mapa", "A"]) == (0 if recuperou else 1)
    tentativas = [chamada.args for chamada in execucao.reimportar.call_args_list]
    paginas_primeira = paginas if recuperou else paginas[:-1]
    esperadas = [(pagina, CAMADAS[0]) for pagina in paginas_primeira] + [(paginas[-1], CAMADAS[1])]
    assert [(args[0], args[3].nome) for args in tentativas] == esperadas
    retentativas = min(reversoes, 5)
    assert [chamada.args for chamada in pausa.call_args_list] == [(2,)] * retentativas
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert log.count("após reversão em 2 s.") == retentativas
    assert f"Retentativa {retentativas}/5 após reversão" in log
    assert "A — pontos_02.csv — atualização confirmada" in log
    if not recuperou:
        assert f"A — pontos_01.csv — {erro} (0/2 camada(s) confirmada(s))" in log


@pytest.mark.parametrize(("erro", "codigo", "proximo_passo"), [
    (ErroMapa("Falha na camada"), 1, "continuar"),
    (ErroUploadTemporario("Seletor ficou aberto"), 0, "tentar novamente"),
    (ErroAtualizacaoRevertida("Sua última ação foi revertida."), 0, "tentar novamente"),
])
def test_opcao_pausa_com_a_pagina_da_falha_aberta(execucao, tmp_path, monkeypatch, erro, codigo, proximo_passo):
    pagina, seguinte = Mock(), Mock()
    pagina.is_closed.return_value = False
    execucao.contexto.new_page.side_effect = [pagina, seguinte]
    execucao.reimportar.side_effect = [erro, None, None]
    pausa_upload = Mock()
    monkeypatch.setattr(atualizacao, "sleep", pausa_upload)

    def inspecionar(_):
        pagina.close.assert_not_called()
        pagina.bring_to_front.assert_called_once()
        execucao.reimportar.assert_called_once()
        pausa_upload.assert_not_called()
        log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
        assert f"A — pontos_01.csv — {erro}" in log

    entrada = Mock(side_effect=inspecionar)
    monkeypatch.setattr("builtins.input", entrada)
    assert main(["atualizar", "--mapa", "A", "--pausar-em-erro"]) == codigo
    entrada.assert_called_once()
    mensagem = entrada.call_args.args[0]
    assert "A — pontos_01.csv — Inspecione o navegador." in mensagem
    assert f"Pressione Enter no terminal para {proximo_passo}" in mensagem
    assert execucao.reimportar.call_count == (2 if codigo else 3)
    pagina.close.assert_called_once()
    seguinte.close.assert_called_once()


@pytest.mark.parametrize(("interrupcao", "codigo"), [(EOFError, 1), (KeyboardInterrupt, 130)])
def test_pausa_libera_a_pagina_quando_a_entrada_termina(execucao, tmp_path, monkeypatch, interrupcao, codigo):
    pagina = execucao.contexto.new_page.return_value
    pagina.is_closed.return_value = False
    execucao.reimportar.side_effect = ErroMapa("Falha na camada")
    monkeypatch.setattr("builtins.input", Mock(side_effect=interrupcao))

    assert main(["atualizar", "--mapa", "B", "--pausar-em-erro"]) == codigo
    pagina.close.assert_called_once()
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    mensagem = "Terminal sem entrada disponível" if codigo == 1 else "Atualização interrompida pelo usuário"
    assert mensagem in log


def test_sessao_expirada_interrompe_lote(execucao, tmp_path):
    execucao.abrir_mapa.side_effect = ErroAutenticacao("Sessão expirada. Execute login.")
    assert main(["atualizar"]) == 1
    execucao.abrir_mapa.assert_called_once()
    execucao.reimportar.assert_not_called()
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "Atualização interrompida — Sessão expirada. Execute login." in log


def test_sessao_expirada_em_camada_interrompe_lote(execucao, tmp_path):
    execucao.reimportar.side_effect = ErroAutenticacao("Sessão expirada. Execute login.")
    assert main(["atualizar"]) == 1
    execucao.reimportar.assert_called_once()
    execucao.abrir_mapa.assert_called_once()
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "A — pontos_01.csv — Sessão expirada. Execute login." in log
