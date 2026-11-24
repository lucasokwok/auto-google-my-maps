# Cadastro de mapas

Copie `mapas.example.json` para `mapas.json` e edite a cópia privada. O Git ignora `config/mapas.json`.

| Campo | Valor |
| --- | --- |
| `NomeMapa` | Nome exato da pasta em `MAPAS/`, sem separadores de caminho. |
| `URL` | Link HTTPS de edição do Google My Maps, com caminho `/maps/d/edit` ou `/maps/d/u/<n>/edit` e um `mid` válido. Cada mapa remoto deve aparecer uma única vez. |
| `coluna_identificacao` | Nome exato da coluna que identifica os pontos nos CSVs e nas camadas correspondentes, como `ID`. |
| `estrategia_reimportacao` | `atualizar_correspondentes`, também usada quando o campo é omitido. |

Guarde apenas os dados do cadastro neste JSON. A autenticação usa um perfil persistente separado.
