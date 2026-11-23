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


@pytest.mark.parametrize("url", [
    "http://www.google.com/maps/d/edit?mid=FICTICIO",
    "https://www.google.com.exemplo.invalid/maps/d/edit?mid=FICTICIO",
    "https://mymaps.google.com/maps/d/viewer?mid=FICTICIO",
    "https://www.google.com/maps/d/edit",
    "https://www.google.com/maps/d/edit?mid=",
    "https://www.google.com/maps/d/edit?mid=A&mid=B",
    "https://www.google.com/maps/d/edit?mid=A%20B",
    "https://www.google.com/maps/d/edit?mid=FICTICIO#",
    "https://usuario@www.google.com/maps/d/edit?mid=FICTICIO",
    "https://www.google.com:123/maps/d/edit?mid=FICTICIO",
    "https://[malformado",
])
def test_bloqueia_urls_invalidas(tmp_path, url):
    dados = config_base()
    dados["mapas"][0]["URL"] = url
    with pytest.raises(ErroConfiguracao):
        carregar_configuracao(salvar(tmp_path, dados))


def test_aceita_links_com_indice_da_conta_e_id_legado(tmp_path):
    dados = config_base()
    dados["mapas"][0]["URL"] = "https://mymaps.google.com/maps/d/u/1/edit?mid=LEGADO.FICTICIO"
    assert carregar_configuracao(salvar(tmp_path, dados)).mapas[0].url == dados["mapas"][0]["URL"]


def test_rejeita_duas_urls_para_mesmo_mapa(tmp_path):
    dados = config_base()
    dados["mapas"].append({
        "NomeMapa": "NomeMapa_B",
        "URL": "https://mymaps.google.com/maps/d/u/1/edit?mid=EXEMPLO_FICTICIO&hl=pt-BR",
    })
    with pytest.raises(ErroConfiguracao, match="mesmo mapa"):
        carregar_configuracao(salvar(tmp_path, dados))


def test_rejeita_estrategia_de_substituicao(tmp_path):
    dados = config_base()
    dados["estrategia_reimportacao"] = "substituir_todos"
    with pytest.raises(ErroConfiguracao, match="atualizar_correspondentes"):
        carregar_configuracao(salvar(tmp_path, dados))
