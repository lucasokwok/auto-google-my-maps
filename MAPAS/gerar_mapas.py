"""Gera três mapas fictícios brasileiros para testar a reimportação no My Maps.

Cria, ao lado deste script, uma pasta para cada mapa, contendo sempre
pontos_01.csv, pontos_02.csv, ..., pontos_05.csv.

Exemplos:
    python gerar_mapas_ficticios.py
    python gerar_mapas_ficticios.py --rodada 2
    python gerar_mapas_ficticios.py --rodada 3 --pontos-por-camada 40

Use a mesma quantidade de pontos por camada em todas as rodadas. A rodada 2
remove 20% dos IDs da rodada 1; a rodada 3 remove 40%. Os demais dados são
reproduzíveis, permitindo testar a exclusão de pontos no mesmo mapa.

Os nomes, idades, observações e identificadores são fictícios. As coordenadas
são aleatórias dentro de pequenas regiões urbanas brasileiras e não indicam
endereços ou pessoas reais.
"""

import argparse
import csv
import random
from pathlib import Path

MAPAS = (
    {
        "nome": "MAPA_TESTE_SAO_PAULO",
        "cidade": "São Paulo",
        "uf": "SP",
        "latitude": -23.5505,
        "longitude": -46.6333,
        "camadas": 5,
    },
    {
        "nome": "MAPA_TESTE_RIO_DE_JANEIRO",
        "cidade": "Rio de Janeiro",
        "uf": "RJ",
        "latitude": -22.9068,
        "longitude": -43.1729,
        "camadas": 1,
    },
    {
        "nome": "MAPA_TESTE_BELO_HORIZONTE",
        "cidade": "Belo Horizonte",
        "uf": "MG",
        "latitude": -19.9167,
        "longitude": -43.9345,
        "camadas": 2,
    },
)

NOMES = (
    "Ana", "Antônio", "Beatriz", "Bruna", "Caio", "Carolina", "Cecília",
    "Cláudia", "Débora", "Eduardo", "Érica", "Fábio", "Fernanda",
    "Gabriel", "Helena", "Ícaro", "Isabela", "João", "José", "Júlia",
    "Lara", "Lívia", "Luísa", "Márcia", "Mariana", "Otávio",
    "Patrícia", "Rafaela", "Renata", "Sérgio", "Sônia", "Tiago",
    "Valéria", "Vinícius", "Yasmin",
)
SOBRENOMES = (
    "Almeida", "Araújo", "Barbosa", "Batista", "Cardoso", "Carvalho",
    "Conceição", "Costa", "Dias", "Fernandes", "Ferreira", "Gonçalves",
    "Lima", "Macedo", "Martins", "Mendes", "Nogueira", "Oliveira",
    "Pereira", "Ribeiro", "Rocha", "Santos", "Silva", "Souza",
)
OBSERVACOES = (
    "Inspeção pendente — acesso liberado",
    "Avaliação técnica necessária",
    "Endereço fictício; conferir localização",
    "Observação: área com árvores 🌳",
    "Agendar visita — período da manhã",
    "Atenção: portão de acesso (simulação)",
    "Revisão de campo: ligação e medição",
    "Sem observações adicionais",
)
COLUNAS = (
    "ID", "NomeProprietario", "IdadeProprietario", "Municipio",
    "UF", "Observacao", "Latitude", "Longitude",
)


def registro_ficticio(mapa: dict, camada: int, indice: int, seed: int) -> dict:
    """Mantém os mesmos dados/IDs em execuções com parâmetros iguais."""
    gerador = random.Random(f"{seed}|{mapa['nome']}|{camada}|{indice}")
    nome = f"{gerador.choice(NOMES)} {gerador.choice(SOBRENOMES)}"
    latitude = mapa["latitude"] + gerador.uniform(-0.045, 0.045)
    longitude = mapa["longitude"] + gerador.uniform(-0.045, 0.045)
    return {
        "ID": f"TESTE-{mapa['uf']}-{camada:02d}-{indice:04d}",
        "NomeProprietario": nome,
        "IdadeProprietario": gerador.randint(18, 90),
        "Municipio": mapa["cidade"],
        "UF": mapa["uf"],
        "Observacao": gerador.choice(OBSERVACOES),
        "Latitude": f"{latitude:.6f}",
        "Longitude": f"{longitude:.6f}",
    }


def gerar(rodada: int, pontos_por_camada: int, seed: int) -> None:
    diretorio_base = Path(__file__).resolve().parent
    quantidade_removida = (rodada - 1) * pontos_por_camada // 5
    total = 0

    for mapa in MAPAS:
        pasta = diretorio_base / mapa["nome"]
        pasta.mkdir(parents=True, exist_ok=True)
        for camada in range(1, mapa["camadas"] + 1):
            destino = pasta / f"pontos_{camada:02d}.csv"
            with destino.open("w", newline="", encoding="utf-8-sig") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
                escritor.writeheader()
                for indice in range(quantidade_removida + 1, pontos_por_camada + 1):
                    escritor.writerow(registro_ficticio(mapa, camada, indice, seed))
                    total += 1
        print(
            f"{mapa['nome']}: {mapa['camadas']} CSVs | "
            f"{pontos_por_camada - quantidade_removida} pontos por camada"
        )

    print(f"\nRodada {rodada}: {total} pontos fictícios em 3 mapas.")
    print(f"Pastas criadas em: {diretorio_base}")
    print("URLs dos mapas: cadastre manualmente na configuração do projeto de automação.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera três mapas fictícios para testes do Google My Maps.")
    parser.add_argument("--rodada", type=int, choices=(1, 2, 3), default=1,
                        help="1 = base completa; 2 = remove 20%%; 3 = remove 40%% (padrão: 1).")
    parser.add_argument("--pontos-por-camada", type=int, default=50,
                        help="Quantidade de pontos na rodada 1, de 1 a 2000 (padrão: 50).")
    parser.add_argument("--seed", type=int, default=2026,
                        help="Semente dos dados fictícios (padrão: 2026).")
    args = parser.parse_args()
    if not 1 <= args.pontos_por_camada <= 2000:
        parser.error("--pontos-por-camada deve estar entre 1 e 2000.")
    gerar(args.rodada, args.pontos_por_camada, args.seed)


if __name__ == "__main__":
    main()
