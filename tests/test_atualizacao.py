import json
from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from auto_googlemymaps import atualizacao
from auto_googlemymaps.__main__ import main
from auto_googlemymaps.csvs import CAMADAS
from auto_googlemymaps.mymaps import ErroMapa
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


def test_dados_invalidos_bloqueiam_mapa_sem_impedir_validos(execucao, tmp_path):
    (tmp_path / "MAPAS" / "B" / CAMADAS[0]).write_bytes(b"")
    assert main(["atualizar"]) == 1
    assert [chamada.args[1].nome for chamada in execucao.abrir_mapa.call_args_list] == ["A", "C"]
    assert execucao.reimportar.call_count == 7
    execucao.abrir_navegador.assert_called_once()


def test_nenhum_csv_valido_nao_inicia_navegador(execucao, tmp_path):
    (tmp_path / "MAPAS" / "B" / CAMADAS[0]).unlink()
    assert main(["atualizar", "--mapa", "B"]) == 1
    execucao.abrir_navegador.assert_not_called()


def test_camada_ausente_impede_qualquer_envio_no_mapa(execucao):
    execucao.localizar.side_effect = [CAMADAS[0], ErroMapa("Camada ausente")]
    assert main(["atualizar", "--mapa", "A"]) == 1
    execucao.reimportar.assert_not_called()
    execucao.contexto.new_page.return_value.close.assert_called_once()


def test_falha_de_upload_interrompe_mapa_e_continua_nos_demais(execucao, tmp_path):
    execucao.reimportar.side_effect = [ErroMapa("Falha no seletor de upload")] + [None] * 6
    assert main(["atualizar"]) == 1
    assert [chamada.args[1].nome for chamada in execucao.reimportar.call_args_list] == ["A", "B"] + ["C"] * 5
    assert execucao.contexto.new_page.return_value.close.call_count == 3
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "A — pontos_01.csv — Falha no seletor de upload (0/2 camada(s) confirmada(s))" in log
    assert "C — atualização concluída" in log


def test_sessao_expirada_interrompe_lote(execucao, tmp_path):
    execucao.abrir_mapa.side_effect = ErroAutenticacao("Sessão expirada. Execute login.")
    assert main(["atualizar"]) == 1
    execucao.abrir_mapa.assert_called_once()
    execucao.reimportar.assert_not_called()
    log = (tmp_path / "logs" / "atualizacao.log").read_text(encoding="utf-8")
    assert "Atualização interrompida — Sessão expirada. Execute login." in log
