# auto-googlemymaps

Automação local em Python e Playwright para atualizar pontos em **camadas existentes** do Google My Maps. O aplicativo reimporta os CSVs pelo recurso **Atualizar itens correspondentes**, preservando os mapas, seus links e as configurações de compartilhamento.

**Estado da integração.** A validação local e o fluxo de atualização têm testes automatizados. A reimportação ainda precisa ser validada em um editor Google My Maps autenticado. Faça a primeira execução em mapas de teste com dados fictícios.

## Instalação

Use Python 3.10 ou superior e, para `login` e `atualizar`, um ambiente com interface gráfica e o Chromium do Playwright.

```bash
python -m venv .venv
```

Ative o ambiente virtual (`source .venv/bin/activate` em macOS e Linux ou `\.venv\Scripts\Activate.ps1` no PowerShell). Na raiz do repositório, execute os comandos abaixo.

```bash
python -m pip install -e ".[browser,dev]"
python -m playwright install chromium
```

Se faltarem bibliotecas do sistema no Linux, use `python -m playwright install --with-deps chromium`. Para executar apenas `validar` e `planejar`, basta instalar o pacote com `python -m pip install -e .`.

## Cadastro privado e arquivos locais

Copie `config/mapas.example.json` para `config/mapas.json`. Preencha a URL HTTPS de **edição** de cada mapa com seu parâmetro `mid` e use em `NomeMapa` o nome exato da pasta local. Configure a coluna usada para identificar os pontos, como `ID`. Ela precisa existir nos CSVs e nas camadas remotas.

```text
config/
  mapas.json
MAPAS/
  MAPA_TESTE_RIO_DE_JANEIRO/
    pontos_01.csv
  MAPA_TESTE_BELO_HORIZONTE/
    pontos_01.csv
    pontos_02.csv
  MAPA_TESTE_SAO_PAULO/
    pontos_01.csv
    pontos_02.csv
    pontos_03.csv
    pontos_04.csv
    pontos_05.csv
runtime/
  google_profile/
logs/
  atualizacao.log
```

Cada mapa aceita de um a cinco CSVs, com nomes consecutivos começando em `pontos_01.csv`. Cada arquivo deve usar UTF-8 com ou sem BOM, separador vírgula e as colunas `Latitude`, `Longitude` e a coluna de identificação. Use coordenadas numéricas válidas e de 1 a 2.000 registros por arquivo, com IDs preenchidos e únicos dentro da camada. O aplicativo envia os bytes que validou e preserva o conteúdo dos arquivos locais. [Detalhes do cadastro](config/README.md) · [Regras dos CSVs](MAPAS/README.md)

## Execução

```bash
python -m auto_googlemymaps validar
python -m auto_googlemymaps planejar
python -m auto_googlemymaps login
python -m auto_googlemymaps atualizar --mapa MAPA_TESTE_RIO_DE_JANEIRO
python -m auto_googlemymaps atualizar
```

- `validar` verifica o cadastro e os dados locais. `planejar` também mostra as camadas e as contagens de registros. Ambos funcionam sem abrir o navegador.
- `login` abre o Chromium. Entre manualmente na conta Google com permissão de edição, conclua eventuais verificações e pressione Enter no terminal. O perfil é salvo em `runtime/google_profile/`. Se a sessão expirar, execute `login` novamente com o mesmo perfil.
- `atualizar` valida os CSVs e verifica se todas as camadas esperadas existem antes da primeira reimportação do mapa. Use `--mapa` com o `NomeMapa` exato para processar apenas aquele mapa. Uma falha de camada encerra o mapa em andamento. Uma falha de autenticação encerra o lote.

As opções `--config` e `--mapas-dir` substituem os caminhos locais padrão. Use o mesmo `--perfil-dir` em `login` e `atualizar` se precisar de um caminho alternativo, inclusive para reutilizar um perfil existente em `runtime/chromium-profile/`. Em ambientes temporários, faça login novamente se o perfil local tiver sido perdido.

A atualização registra progresso e erros no terminal e em `logs/atualizacao.log`. Os logs contêm nomes de mapas e camadas, contagens e mensagens sanitizadas. O código de saída é `0` para sucesso, `1` para falha operacional ou de validação dos CSVs, `2` para erro de configuração, uso ou abertura do log e `130` para interrupção no login ou na atualização. [Segurança e privacidade](docs/SEGURANCA.md)

## Primeiro teste manual

1. Prepare no Google My Maps os três mapas fictícios com uma camada no Rio de Janeiro, duas em Belo Horizonte e cinco em São Paulo. Use os nomes exatos dos CSVs para as camadas, incluindo `.csv`.
2. No mapa de uma camada, escolha dados de teste com pelo menos um ID mantido e alterado, um ID novo e um ID que ficará ausente no CSV atualizado. Aplique uma personalização ao ponto mantido para poder conferi-la depois.
3. Cadastre os links de edição em `config/mapas.json`. Execute `validar` e `login`, depois rode `atualizar --mapa MAPA_TESTE_RIO_DE_JANEIRO` como nos exemplos acima.
4. Confira no editor e no log a conclusão. Reabra o mapa e verifique os dados e as coordenadas do ponto mantido, a inclusão do novo, a remoção do ausente e a preservação do estilo. Se o resultado for indeterminado, confira a camada antes de repetir.
5. Repita com `--mapa MAPA_TESTE_BELO_HORIZONTE` e `--mapa MAPA_TESTE_SAO_PAULO`. Após validar os três casos, execute o lote com `atualizar`.

## Testes e documentação

```bash
python -m pytest -q
```

Os testes usam arquivos fictícios e mocks de Playwright. A suíte roda sem autenticação, sem binário de navegador e sem acesso a mapas reais.

- [Arquitetura](docs/ARQUITETURA.md)
- [Integração Playwright, confirmação e limites](docs/PLAYWRIGHT.md)
- [Próximas etapas](docs/ROADMAP.md)
- [Projeto de referência](references/README.md)
