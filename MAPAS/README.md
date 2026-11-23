# Diretório de entrada local

O diretório `MAPAS/` armazena os arquivos CSV utilizados na atualização das camadas do Google My Maps.

Cada mapa deve possuir uma **subpasta com nome idêntico ao `NomeMapa`** definido em `config/mapas.json`.

## Gerando os mapas de teste

Como os arquivos CSV são ignorados pelo Git, eles não estão incluídos no repositório.

Para gerar os dados fictícios utilizados nos testes da automação, execute o seguinte comando na raiz do projeto:

```bash
python MAPAS/gerar_mapas.py
```

O script `gerar_mapas.py` criará automaticamente três mapas fictícios, com coordenadas brasileiras e dados simulados de proprietários.

Os mapas possuem quantidades diferentes de camadas para permitir testar a automação em diferentes cenários:

- **MAPA_TESTE_SAO_PAULO:** 5 camadas.
- **MAPA_TESTE_RIO_DE_JANEIRO:** 1 camada.
- **MAPA_TESTE_BELO_HORIZONTE:** 2 camadas.

Após gerar os arquivos, crie manualmente os três mapas no Google My Maps, importe os CSVs correspondentes e cadastre suas URLs em `config/mapas.json`.

## Estrutura de diretórios

Cada mapa pode conter **de 1 a 5 arquivos CSV**, correspondendo às camadas existentes no Google My Maps.

Os arquivos devem seguir a nomenclatura sequencial `pontos_01.csv`, `pontos_02.csv`, ..., `pontos_05.csv`.

```text
MAPAS/
├── README.md
├── gerar_mapas.py
│
├── MAPA_TESTE_SAO_PAULO/
│   ├── pontos_01.csv
│   ├── pontos_02.csv
│   ├── pontos_03.csv
│   ├── pontos_04.csv
│   └── pontos_05.csv
│
├── MAPA_TESTE_RIO_DE_JANEIRO/
│   └── pontos_01.csv
│
└── MAPA_TESTE_BELO_HORIZONTE/
    ├── pontos_01.csv
    └── pontos_02.csv
```

Não é necessário criar arquivos adicionais para completar cinco camadas.

## Requisitos dos arquivos CSV

- **Codificação:** UTF-8 ou UTF-8 com BOM (`utf-8-sig`).
- **Cabeçalho:** obrigatório na primeira linha.
- **Coordenadas:** colunas `Latitude` e `Longitude`.
- **Identificação:** coluna identificadora definida na configuração do projeto.
- **Limite:** até 2.000 registros por arquivo.
- **Nomenclatura:** `pontos_01.csv` até `pontos_05.csv`, sem saltos na sequência.
- **Quantidade:** mínimo de 1 e máximo de 5 arquivos por mapa.

As colunas adicionais são permitidas e podem ser utilizadas para apresentar informações nos marcadores.

## Regras de atualização

A automação deverá:

1. Identificar os mapas cadastrados em `config/mapas.json`.
2. Localizar a subpasta correspondente ao `NomeMapa`.
3. Identificar os arquivos CSV disponíveis, respeitando a sequência numérica.
4. Validar a estrutura e os dados antes de iniciar a atualização.
5. Atualizar somente as camadas correspondentes aos arquivos encontrados.
6. Preservar os arquivos CSV originais, sem modificá-los.

**Segurança:** arquivos vazios, ausentes na sequência esperada ou com dados inválidos devem impedir a atualização do mapa correspondente, evitando alterações acidentais.

## Versionamento

Todos os arquivos CSV são ignorados pelo `.gitignore` e não devem ser enviados ao GitHub.

O script `MAPAS/gerar_mapas.py` e este `README.md` são versionados normalmente.

Após clonar o repositório, basta executar `python MAPAS/gerar_mapas.py` para recriar os dados fictícios necessários aos testes.
