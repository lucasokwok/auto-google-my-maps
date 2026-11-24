# CSVs locais dos mapas

Cada mapa cadastrado em `config/mapas.json` tem uma pasta em `MAPAS/` cujo nome corresponde exatamente a `NomeMapa`. O aplicativo lê apenas os CSVs que representam as camadas existentes.

```text
MAPAS/
  MAPA_TESTE_SAO_PAULO/
    pontos_01.csv
    pontos_02.csv
    pontos_03.csv
    pontos_04.csv
    pontos_05.csv
  MAPA_TESTE_RIO_DE_JANEIRO/
    pontos_01.csv
  MAPA_TESTE_BELO_HORIZONTE/
    pontos_01.csv
    pontos_02.csv
```

- Cada mapa pode ter de um a cinco CSVs. Os nomes devem ser consecutivos, a partir de `pontos_01.csv`, e corresponder aos títulos das camadas no editor. Use pastas e arquivos locais regulares.
- Use vírgulas como separador, UTF-8 com ou sem BOM e um cabeçalho com as colunas `Latitude`, `Longitude` e a coluna de identificação configurada. Colunas adicionais são aceitas.
- Cada arquivo deve conter de 1 a 2.000 registros e até 40 MB. Use valores finitos, com latitude de −90 a 90 e longitude de −180 a 180. IDs precisam estar preenchidos e ser únicos dentro do arquivo. IDs coincidentes em camadas diferentes são aceitos.

O comando `python -m auto_googlemymaps validar` reporta problemas sem abrir o navegador. Qualquer lacuna, arquivo vazio ou CSV inválido bloqueia a atualização do mapa. Os arquivos originais são preservados e os CSVs são ignorados pelo Git.
