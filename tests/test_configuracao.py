import json
import pytest
from auto_googlemymaps.configuracao import carregar_configuracao, ErroConfiguracao, validar_nome

URL = "https://www.google.com/maps/d/edit?mid=EXEMPLO_FICTICIO"


def salvar(tmp_path, payload):
    arquivo = tmp_path / "mapas.json"
    arquivo.write_text(json.dumps(payload), encoding="utf-8")
    return arquivo


def config_base():
    return {"coluna_identificacao": "ID", "mapas": [{"NomeMapa": "NomeMapa_A", "URL": URL}]}


def test_configuracao_valida(tmp_path):
    cfg = carregar_configuracao(salvar(tmp_path, config_base()))
    assert cfg.mapas[0].nome == "NomeMapa_A"
    assert cfg.coluna_identificacao == "ID"


def test_bloqueia_path_traversal():
    with pytest.raises(ErroConfiguracao):
        validar_nome("../fora")


def test_nao_mostra_url_no_erro(tmp_path):
    privado = "https://example.invalid/nao-mymaps?token=VALOR_FICTICIO"
    obj = config_base()
    obj["mapas"][0]["URL"] = privado
    with pytest.raises(ErroConfiguracao) as err:
        carregar_configuracao(salvar(tmp_path, obj))
    assert privado not in str(err.value)
    assert "VALOR_FICTICIO" not in str(err.value)


def test_nome_duplicado(tmp_path):
    obj = config_base()
    obj["mapas"].append({"NomeMapa": "nomemapa_a", "URL": "https://www.google.com/maps/d/edit?mid=OUTRO_FICTICIO"})
    with pytest.raises(ErroConfiguracao):
        carregar_configuracao(salvar(tmp_path, obj))
