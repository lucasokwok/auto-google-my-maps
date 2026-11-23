# Segurança e privacidade

## O que deve permanecer exclusivamente no computador

- `config/mapas.json` e qualquer outra configuração privada (incluindo URLs de edição).
- Todo conteúdo de `MAPAS/`, inclusive subpastas, CSVs e nomes reais de mapas.
- Perfis de navegador, cookies, sessões e qualquer estado de autenticação (`runtime/`, `auth/`, `.auth/`).
- Logs, screenshots, traces e demais evidências de execução.
- `.env`, arquivos de credenciais e chaves privadas, se existirem.

O `.gitignore` bloqueia esses caminhos. Não substitui a revisão de `git status` e `git diff --cached`: arquivos adicionados anteriormente ao índice do Git podem continuar versionados mesmo depois de incluídos no `.gitignore`.

Se algo privado já estiver rastreado, utilize `git rm --cached CAMINHO` (sem apagar o arquivo local), faça novo commit e avalie a necessidade de remover o conteúdo do histórico e revogar segredos eventualmente expostos.

## Arquivos públicos permitidos

Código-fonte, documentação genérica, `config/mapas.example.json` com placeholders, testes com dados fictícios e link para uma referência pública de código.

## Antes de enviar ao repositório remoto

```bash
git status --short
git diff --cached --name-only
git check-ignore -v config/mapas.json MAPAS/NomeMapa_A/pontos_01.csv runtime/chromium-profile
```

Nunca use `git add -f` para os caminhos protegidos. Não capture o perfil do navegador em backups públicos. Se precisar reportar erros, compartilhe apenas mensagens sanitizadas, sem nomes reais de mapas, coordenadas, identificadores ou URLs.
