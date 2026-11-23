from auto_googlemymaps.configuracao import Mapa
from auto_googlemymaps.csvs import validar_mapa

MAPA = Mapa("NomeMapa_A", "https://www.google.com/maps/d/edit?mid=EXEMPLO_FICTICIO")


def criar_cinco(tmp_path, linha="1,-23.0,-46.0,Observação com acentos"):
    pasta = tmp_path / "NomeMapa_A"
    pasta.mkdir()
    for i in range(1, 6):
        (pasta / f"pontos_{i:02d}.csv").write_text(
            "ID,Latitude,Longitude,Nome\n" + linha.replace("1,", f"{i},", 1) + "\n",
            encoding="utf-8-sig",
        )
    return pasta


def test_cinco_csvs_validos_com_utf8_sig(tmp_path):
    criar_cinco(tmp_path)
    resultado = validar_mapa(MAPA, tmp_path, "ID")
    assert resultado.valido
    assert len(resultado.camadas) == 5
    assert sum(c.quantidade for c in resultado.camadas) == 5


def test_falta_um_csv(tmp_path):
    pasta = criar_cinco(tmp_path)
    (pasta / "pontos_05.csv").unlink()
    assert not validar_mapa(MAPA, tmp_path, "ID").valido


def test_arquivos_vazios_bloqueados(tmp_path):
    pasta = criar_cinco(tmp_path)
    (pasta / "pontos_03.csv").write_text("ID,Latitude,Longitude,Nome\n", encoding="utf-8")
    assert not validar_mapa(MAPA, tmp_path, "ID").valido


def test_id_duplicado_bloqueado(tmp_path):
    pasta = criar_cinco(tmp_path)
    (pasta / "pontos_02.csv").write_text("ID,Latitude,Longitude\n1,-22,-45\n", encoding="utf-8")
    assert not validar_mapa(MAPA, tmp_path, "ID").valido


def test_coordenada_invalida_bloqueada(tmp_path):
    criar_cinco(tmp_path, linha="1,900,-46.0,Exemplo")
    assert not validar_mapa(MAPA, tmp_path, "ID").valido
