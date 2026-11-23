import pytest

from auto_googlemymaps.configuracao import Mapa
from auto_googlemymaps.csvs import CAMADAS, MAX_REGISTROS, validar_mapa

MAPA = Mapa("NomeMapa_A", "https://www.google.com/maps/d/edit?mid=EXEMPLO_FICTICIO")
CABECALHO = "ID,Latitude,Longitude,Nome\n"
REGISTRO = "1,-23.0,-46.0,Observação fictícia\n"


def criar_csvs(tmp_path, nomes, conteudo=CABECALHO + REGISTRO, encoding="utf-8"):
    pasta = tmp_path / MAPA.nome
    pasta.mkdir()
    for nome in nomes:
        (pasta / nome).write_text(conteudo, encoding=encoding)
    return pasta


@pytest.mark.parametrize("quantidade", range(1, 6))
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_camadas_validas_com_ids_reutilizados(tmp_path, quantidade, encoding):
    nomes = CAMADAS[:quantidade]
    pasta = criar_csvs(tmp_path, nomes, encoding=encoding)
    resultado = validar_mapa(MAPA, tmp_path, "ID")
    assert resultado.valido
    assert [camada.nome for camada in resultado.camadas] == list(nomes)
    for camada in resultado.camadas:
        assert camada.quantidade == 1
        assert camada.conteudo == (pasta / camada.nome).read_bytes()


@pytest.mark.parametrize(("nomes", "mensagem"), [
    ((), "nenhum CSV"),
    ((CAMADAS[1],), "pontos_01.csv: arquivo ausente"),
    ((CAMADAS[0], CAMADAS[2]), "pontos_02.csv: arquivo ausente"),
    ((*CAMADAS, "pontos_06.csv"), "fora do padrão"),
    ((CAMADAS[0], "pontos_2.csv"), "fora do padrão"),
])
def test_csvs_ausentes_ou_fora_da_sequencia(tmp_path, nomes, mensagem):
    criar_csvs(tmp_path, nomes)
    resultado = validar_mapa(MAPA, tmp_path, "ID")
    assert not resultado.valido
    assert any(mensagem in erro for erro in resultado.erros)


def test_pasta_ausente(tmp_path):
    assert not validar_mapa(MAPA, tmp_path, "ID").valido


@pytest.mark.parametrize(("conteudo", "mensagem"), [
    ("", "cabeçalho"),
    (CABECALHO, "sem registros"),
    ("ID,Latitude,Nome\n1,-23,Teste\n", "faltam colunas obrigatórias"),
    ("ID,Latitude,Longitude,ID\n1,0,0,1\n", "cabeçalho"),
    (CABECALHO + REGISTRO + " 1 ,-24,-45,Outro\n", "identificação duplicada"),
    (CABECALHO + " ,0,0,Nenhum\n", "identificação vazia"),
    (CABECALHO + "1,91,0,Teste\n", "coordenada inválida"),
    (CABECALHO + "1,0,-181,Teste\n", "coordenada inválida"),
    (CABECALHO + "1,NaN,0,Teste\n", "coordenada inválida"),
    (CABECALHO + "1,0,infinito,Teste\n", "coordenada inválida"),
    (CABECALHO + "1,0,1_0,Teste\n", "coordenada inválida"),
    (CABECALHO + "1,0,0\n", "estrutura inválida"),
    (CABECALHO + '1,0,0,"Aspas sem fechar', "falha de leitura ou formato"),
])
def test_conteudo_invalido(tmp_path, conteudo, mensagem):
    criar_csvs(tmp_path, CAMADAS[:1], conteudo)
    resultado = validar_mapa(MAPA, tmp_path, "ID")
    assert not resultado.valido
    assert any(mensagem in erro for erro in resultado.erros)
    assert not resultado.camadas


def test_codificacao_invalida(tmp_path):
    criar_csvs(tmp_path, CAMADAS[:1], encoding="latin-1")
    resultado = validar_mapa(MAPA, tmp_path, "ID")
    assert not resultado.valido
    assert "UTF-8" in resultado.erros[0]


def test_coluna_identificadora_configuravel(tmp_path):
    criar_csvs(tmp_path, CAMADAS[:1], ("Chave" + CABECALHO[2:]) + REGISTRO)
    assert validar_mapa(MAPA, tmp_path, "Chave").valido


@pytest.mark.parametrize("extra", [0, 1])
def test_limite_de_registros(tmp_path, extra):
    linhas = "".join(f"{n},-90,180,Teste\n" for n in range(MAX_REGISTROS + extra))
    criar_csvs(tmp_path, CAMADAS[:1], CABECALHO + linhas)
    assert validar_mapa(MAPA, tmp_path, "ID").valido == (extra == 0)
