# Roadmap

## Implementado

- Cadastro privado com links de edição e associação aos diretórios locais.
- Validação de um a cinco CSVs consecutivos por mapa.
- Perfil persistente, login manual e tratamento de pedidos de nova autenticação.
- Fluxo Playwright para reimportar por correspondência, com pré-checagem de camadas individuais e verificação do resultado.
- Atualização em lote ou por nome de mapa, com log local sanitizado.
- Testes unitários com mocks e ensaio em Chromium com uma interface simulada.

## Homologação no Google My Maps

- [ ] Confirmar login manual, reutilização do perfil e detecção de sessão expirada.
- [ ] Confirmar os seletores do editor, dos menus, do Picker e do assistente de correspondência.
- [ ] Identificar os sinais reais de sucesso e falha e confirmar que podem ser detectados.
- [ ] Executar o procedimento do README nos mapas fictícios de uma, duas e cinco camadas.
- [ ] Reabrir os mapas e verificar adição, remoção, atualização e preservação do estilo dos itens correspondentes.
