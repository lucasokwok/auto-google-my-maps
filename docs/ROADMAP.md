# Roadmap

## Implementado

- Cadastro privado com links de edição e associação aos diretórios locais.
- Validação de um a cinco CSVs consecutivos por mapa.
- Perfil persistente, login manual e tratamento de pedidos de nova autenticação.
- Fluxo Playwright para reimportar por correspondência, com pré-checagem de camadas individuais e verificação do resultado.
- Atualização em lote ou por nome de mapa, com log local sanitizado.
- Testes unitários com mocks e ensaio em Chromium com uma interface simulada.

## Homologação no Google My Maps

- [x] Confirmar o reaproveitamento da sessão na página Minha Conta, criada manualmente no Edge com perfil dedicado no Windows.
- [ ] Confirmar a detecção de sessão expirada no editor e o reinício após renovar a sessão.
- [ ] Confirmar os seletores do editor, dos menus, do Picker e do assistente de correspondência.
- [ ] Identificar os sinais reais de sucesso e falha e confirmar que podem ser detectados.
- [ ] Executar o procedimento do README nos mapas fictícios de uma, duas e cinco camadas.
- [ ] Reabrir os mapas e verificar adição, remoção, atualização e preservação do estilo dos itens correspondentes.
