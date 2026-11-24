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
- [x] Confirmar os seletores do editor, dos menus e do envio pelo Picker no mapa fictício do Rio.
- [ ] Confirmar a seleção automática da coluna de identificação nos dois grupos do assistente.
- [x] Identificar a mensagem real de sucesso exibida após concluir a atualização no Edge.
- [ ] Confirmar a detecção automática dos avisos de sucesso e falha no editor autenticado.
- [ ] Executar o procedimento do README nos mapas fictícios de uma, duas e cinco camadas.
- [ ] Reabrir os mapas e verificar adição, remoção, atualização e preservação do estilo dos itens correspondentes.
