# Roadmap

## Etapa 1 — Estrutura segura (incluída neste ZIP)

- [x] Cadastro privado de mapas por `NomeMapa` e `URL`.
- [x] Associação de `NomeMapa` a `MAPAS/<NomeMapa>/`.
- [x] Validação de cinco arquivos CSV por mapa.
- [x] Ignorar configurações reais, dados de mapas, sessões e logs no Git.
- [x] Login manual por perfil local persistente.
- [x] Testes unitários básicos.

## Etapa 2 — Automação da interface (pendente)

- [ ] Identificar os seletores reais do My Maps em uma conta de teste.
- [ ] Localizar as cinco camadas pelo nome exibido.
- [ ] Automatizar a reimportação do CSV para cada camada.
- [ ] Selecionar a coluna para correspondência dos pontos.
- [ ] Confirmar a conclusão e fazer tratamento de falhas.
- [ ] Validar preservação dos estilos e exclusão dos pontos ausentes.

## Etapa 3 — Operação (pendente)

- [ ] Relatório local de êxitos/falhas sem URLs ou dados de pontos.
- [ ] Tentativas controladas e recuperação de falhas de navegação.
- [ ] Execução agendada pelo sistema operacional.
- [ ] Testes de regressão após mudanças na interface do Google.

A automação não deverá prosseguir quando faltar qualquer CSV ou quando o arquivo estiver vazio, até haver uma política explícita e homologada para esse caso.
