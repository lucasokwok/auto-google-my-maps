# auto-googlemymaps

Automação local em Python e Playwright para atualizar pontos em **camadas existentes** do Google My Maps. O aplicativo reimporta os CSVs pelo recurso **Atualizar itens correspondentes**, preservando os mapas, seus links e as configurações de compartilhamento.

**Estado da integração.** O reaproveitamento de uma sessão Google criada manualmente no Edge foi confirmado em um teste no Windows. A validação local e o fluxo de atualização têm testes automatizados. A reimportação ainda precisa ser validada em um editor Google My Maps autenticado. Faça a primeira execução em mapas de teste com dados fictícios.

## Instalação

Use Python 3.10 ou superior e, para `login` e `atualizar`, um ambiente com interface gráfica. O navegador padrão é o Chromium do Playwright. A opção `--navegador edge` usa o Microsoft Edge já instalado no computador.

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
- `login` abre o navegador selecionado. Entre manualmente na conta Google com permissão de edição, conclua eventuais verificações e pressione Enter no terminal. O perfil padrão é `runtime/google_profile/` no Chromium e `runtime/google_profile_edge/` no Edge. Se a sessão expirar, execute `login` novamente com o mesmo navegador e perfil.
- `atualizar` valida os CSVs e verifica se todas as camadas esperadas existem antes da primeira reimportação do mapa. Use `--mapa` com o `NomeMapa` exato para processar apenas aquele mapa. Uma falha de camada encerra o mapa em andamento. Uma falha de autenticação encerra o lote.

As opções `--config` e `--mapas-dir` substituem os caminhos locais padrão. Use o mesmo `--navegador` e, se definir um caminho alternativo, o mesmo `--perfil-dir` em `login` e `atualizar`. Em ambientes temporários, faça login novamente se o perfil local tiver sido perdido.

A atualização registra progresso e erros no terminal e em `logs/atualizacao.log`. Os logs contêm nomes de mapas e camadas, contagens e mensagens sanitizadas. O código de saída é `0` para sucesso, `1` para falha operacional ou de validação dos CSVs, `2` para erro de configuração, uso ou abertura do log e `130` para interrupção no login ou na atualização. [Segurança e privacidade](docs/SEGURANCA.md)

## Login confirmado com o Edge no Windows

O teste no Windows confirmou o seguinte procedimento. Abra o Edge diretamente com um perfil dedicado em `%LOCALAPPDATA%`. No Prompt de Comando, com o `.venv` ativo, execute os comandos abaixo.

```bat
set "PERFIL_MYMAPS=%LOCALAPPDATA%\auto-google-my-maps\edge-profile"
start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --user-data-dir="%PERFIL_MYMAPS%" "https://myaccount.google.com/"
```

Entre manualmente na conta Google com acesso de edição. Feche a janela desse perfil e, no mesmo terminal, confirme que o Playwright consegue reutilizar a sessão.

```bat
python -m auto_googlemymaps login --navegador edge --perfil-dir "%PERFIL_MYMAPS%"
```

Quando a página **Minha Conta** abrir autenticada, pressione Enter no terminal. A mensagem `Login Google confirmado. Perfil salvo localmente.` confirma que a sessão foi reutilizada. Mantenha o perfil dedicado no mesmo computador. [Detalhes do perfil e recuperação de sessão](docs/PLAYWRIGHT.md#sessão-dedicada-no-edge-do-windows)

## Primeiro teste manual

1. Cadastre o link de edição de `MAPA_TESTE_RIO_DE_JANEIRO` em `config/mapas.json`. Confirme que o mapa tem a camada `pontos_01.csv` e que a coluna configurada para correspondência existe na camada.
2. Para verificar os efeitos da reimportação, use dados fictícios com um ID mantido e alterado, um ID novo e um ID ausente do CSV atualizado. Aplique um estilo personalizado ao ponto mantido para conferi-lo depois. Se a mesma versão do CSV já tiver sido importada, use uma versão com diferenças conhecidas para esse teste.
3. Execute `validar` e `planejar`. Confirme que o Rio aparece com uma camada válida. Depois do login confirmado, teste só esse mapa. Para o perfil dedicado no Edge do Windows, use o comando abaixo.

   ```bat
   set "PERFIL_MYMAPS=%LOCALAPPDATA%\auto-google-my-maps\edge-profile"
   python -m auto_googlemymaps atualizar --navegador edge --perfil-dir "%PERFIL_MYMAPS%" --mapa MAPA_TESTE_RIO_DE_JANEIRO
   ```

4. Confira no terminal ou em `logs/atualizacao.log` se apareceu `pontos_01.csv — atualização confirmada pela interface`. Reabra o mapa e confira a alteração, a inclusão e a remoção pelos IDs e a preservação do estilo. Se aparecer `Resultado indeterminado`, confira o estado da camada antes de tentar de novo.
5. Depois de confirmar o Rio, teste Belo Horizonte, com duas camadas, e São Paulo, com cinco. Mantenha os mesmos parâmetros do navegador e do perfil e altere apenas `--mapa`. Para rodar o lote após validar os três casos, retire `--mapa`.

## Testes e documentação

```bash
python -m pytest -q
```

Os testes usam arquivos fictícios e mocks de Playwright. A suíte roda sem autenticação, sem binário de navegador e sem acesso a mapas reais.

- [Arquitetura](docs/ARQUITETURA.md)
- [Integração Playwright, confirmação e limites](docs/PLAYWRIGHT.md)
- [Próximas etapas](docs/ROADMAP.md)
- [Projeto de referência](references/README.md)
