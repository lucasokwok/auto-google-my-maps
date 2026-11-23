# Segurança e privacidade

## Dados que permanecem locais

- Configurações privadas, incluindo `config/mapas.json` e URLs de edição.
- Dados de mapas, incluindo os CSVs e as pastas desses mapas em `MAPAS/`.
- Perfis do navegador, cookies e estado de autenticação, incluindo `runtime/google_profile/`.
- Logs, capturas de tela, traces e outras evidências que possam mostrar mapas ou sessões.
- Credenciais, chaves privadas e arquivos de ambiente que contenham segredos.

O `.gitignore` protege esses caminhos no fluxo normal. Arquivos já rastreados precisam ser removidos do índice separadamente. Se precisar compartilhar um erro, omita os nomes reais dos mapas e quaisquer referências aos pontos.

## Atualizações remotas

A importação só é liberada após validar todos os CSVs do mapa e identificar as camadas pelo nome e pelo menu do próprio cabeçalho. A automação atua no editor com o identificador cadastrado. A estratégia de correspondência pode remover pontos cujo ID ficou fora do CSV. Falhas após a confirmação precisam de inspeção da camada antes de uma nova tentativa.

O log da atualização usa os nomes dos mapas e camadas, contagens e mensagens fixas. URLs completas, exceções brutas do Playwright, dados dos pontos e credenciais ficam fora do log do aplicativo.

## Conferência antes de publicar

```bash
git status --short
git diff --cached
git check-ignore config/mapas.json MAPAS/EXEMPLO/pontos_01.csv runtime/google_profile logs/atualizacao.log
```

Mantenha o arquivo `config/mapas.example.json` somente com valores ilustrativos. Preserve a proteção dos arquivos ignorados ao preparar commits.
