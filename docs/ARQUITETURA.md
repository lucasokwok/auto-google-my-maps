# Arquitetura da automação

## Responsabilidade

Este repositório tem **uma única responsabilidade**: utilizar arquivos CSV já disponíveis localmente para atualizar as camadas de mapas existentes no Google My Maps. Não cria mapas novos por padrão e não altera o conteúdo dos CSVs.

## Associação entre mapa e diretório

A configuração privada mantém uma lista de entradas `{ "NomeMapa": "...", "URL": "..." }`.

Para cada entrada, a aplicação procura `MAPAS/<NomeMapa>/` e os arquivos `pontos_01.csv` até `pontos_05.csv`. A URL é usada somente no navegador durante a futura sincronização; os comandos de diagnóstico não a mostram.

## Componentes

- `configuracao.py`: lê e valida o JSON privado; barra nomes de pastas inseguros e URLs que não sejam do My Maps.
- `csvs.py`: valida a estrutura das cinco camadas, UTF-8, chave de identificação, coordenadas e máximo de registros.
- `navegador.py`: inicializa um perfil local persistente para o login interativo.
- `__main__.py`: interface de linha de comando (`validar`, `planejar`, `login`).
- `references/`: documentação e local opcional para consultar uma implementação pública sem misturá-la ao aplicativo.

## Pré-validação obrigatória

A futura sincronização deve ser bloqueada se qualquer mapa tiver pasta ausente, algum CSV obrigatório ausente, arquivo vazio, ID duplicado, coordenadas inválidas ou mais de 2.000 registros por camada. Erros de validação não podem resultar em remoção de pontos no My Maps.

## Princípio operacional

Atualizar uma camada **existente** e manter o mesmo mapa/link. O comportamento específico da interface deverá ser homologado por meio de testes antes de uma execução agendada.
