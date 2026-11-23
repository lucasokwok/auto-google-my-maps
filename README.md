# auto-googlemymaps

Automação local para **atualizar as camadas de mapas já existentes no Google My Maps** a partir de arquivos CSV disponíveis no computador, utilizando Python e Playwright.

## Objetivo

Manter os **mesmos mapas e links**, atualizando diariamente os pontos das suas cinco camadas. Cada mapa é identificado pelo campo `NomeMapa` em uma configuração privada; esse nome corresponde exatamente a uma pasta dentro de `MAPAS/`.

O aplicativo **somente lê** os cinco CSVs de cada pasta. Não altera os CSVs nem gerencia outras etapas fora do Google My Maps.

## Estrutura esperada

```text
MAPAS/
  NomeMapa_A/
    pontos_01.csv
    pontos_02.csv
    pontos_03.csv
    pontos_04.csv
    pontos_05.csv
  NomeMapa_B/
    pontos_01.csv
    pontos_02.csv
    pontos_03.csv
    pontos_04.csv
    pontos_05.csv
```

Cada mapa no arquivo privado `config/mapas.json` deve possuir `NomeMapa` e `URL`. O `NomeMapa` deve ser idêntico ao nome da pasta. Os cinco arquivos são obrigatórios. As cinco camadas no Google My Maps também devem corresponder a esses nomes.

## Configuração (privada)

Copie `config/mapas.example.json` para `config/mapas.json` e preencha apenas **na cópia privada**. O `.gitignore` impede que `config/mapas.json`, as URLs reais, dados locais e sessões autenticadas sejam incluídos normalmente no Git.

Modelo:

```json
{
  "coluna_identificacao": "ID",
  "estrategia_reimportacao": "atualizar_correspondentes",
  "mapas": [
    {"NomeMapa": "NomeMapa_A", "URL": "COLE_A_URL_PRIVADA_AQUI"}
  ]
}
```

`coluna_identificacao` é o nome exato de uma coluna presente em **todos** os CSVs; configure-a conforme seus arquivos. `Latitude` e `Longitude` também são esperadas. Não existem credenciais no arquivo de configuração: a autenticação é manual, com perfil persistente do navegador mantido fora do Git.

## Instalação

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
# Ative o ambiente virtual antes de instalar:
python -m pip install -e ".[dev,browser]"
python -m playwright install chromium
```

## Comandos disponíveis

```bash
python -m auto_googlemymaps validar
python -m auto_googlemymaps planejar
python -m auto_googlemymaps login
python -m pytest -q
```

- `validar`: lê o cadastro privado e verifica a existência, codificação, cabeçalhos, IDs e limites dos cinco CSVs por mapa.
- `planejar`: apresenta um resumo local dos mapas e das cinco camadas, **sem imprimir URLs**.
- `login`: abre o navegador para autenticação manual no Google, sem salvar senha no projeto.

**Estado atual:** infraestrutura, validação e abertura do navegador implementadas. A etapa que controla os menus **Reimportar e mesclar** do My Maps **ainda não está implementada**. Nenhum comando modifica mapas remotos nesta versão. A implementação será adicionada após testes no My Maps com um mapa de teste.

## Comportamento planejado da sincronização

1. Ler `config/mapas.json` e associar cada `NomeMapa` a `MAPAS/<NomeMapa>/`.
2. Validar os cinco CSVs e interromper a execução em caso de inconsistência.
3. Abrir a URL privada de edição de cada mapa em um navegador autenticado.
4. Localizar cada uma das cinco camadas e acionar **Reimportar e mesclar → Atualizar itens correspondentes**, usando `coluna_identificacao`.
5. Verificar o resultado e registrar êxito/falha localmente **sem expor URLs ou identificadores de pontos**.

É possível configurar uma estratégia alternativa de substituição total, mas ela também exige validação na interface antes de uso real. Por segurança, **camadas vazias não são liberadas para atualização** por esta estrutura inicial.

## Privacidade e segurança

Nunca faça `git add -f` para arquivos protegidos pelo `.gitignore`. Confira `git status` e `git diff --cached` antes de enviar alterações. O arquivo `config/mapas.example.json` contém apenas valores ilustrativos, sem URLs reais. Veja [docs/SEGURANCA.md](docs/SEGURANCA.md).

## Documentação

- [Arquitetura](docs/ARQUITETURA.md)
- [Integração Playwright](docs/PLAYWRIGHT.md)
- [Segurança](docs/SEGURANCA.md)
- [Próximas etapas](docs/ROADMAP.md)
- [Projeto público de referência](references/README.md)

Documentação oficial: https://support.google.com/mymaps/answer/3024836?hl=pt-BR
