# Cadastro de mapas

Copie `mapas.example.json` para `mapas.json` e edite **somente** `mapas.json`. Esse arquivo está ignorado no Git.

- `NomeMapa`: nome exato da subpasta em `MAPAS/`. Não deve conter separadores de caminho.
- `URL`: link de **edição** do Google My Maps; deve ser guardado somente no arquivo privado.
- `coluna_identificacao`: coluna comum para relacionar os pontos durante a reimportação (deve existir em todos os CSVs).
- `estrategia_reimportacao`: `atualizar_correspondentes` (preferencial) ou `substituir_todos` (a validar).

Não inclua e-mails, senhas, cookies, tokens ou outros segredos no JSON. As URLs não aparecem em logs do aplicativo. O arquivo de exemplo nunca deve conter URLs privadas.
