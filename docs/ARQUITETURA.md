# Arquitetura da automação

A aplicação usa CSVs locais para atualizar pontos de camadas já cadastradas no Google My Maps. O nome da camada é o nome exato do CSV, incluindo a extensão.

## Componentes

| Arquivo | Responsabilidade |
| --- | --- |
| `configuracao.py` | Lê o JSON privado. Valida os nomes locais, os links de edição, a estratégia e a unicidade dos mapas. |
| `csvs.py` | Descobre séries contíguas de um a cinco CSVs e verifica conteúdo, limites e coordenadas. Mantém o caminho e o conteúdo validado de cada arquivo para conferir o CSV original durante o envio. |
| `navegador.py` | Inicia o navegador visível com perfil persistente, confirma o login manual e detecta pedidos de autenticação. |
| `mymaps.py` | Confirma o editor e o mapa de destino, identifica as camadas, opera o seletor de arquivos e o assistente de correspondência e verifica a resposta da interface. |
| `atualizacao.py` | Coordena a validação e a atualização por mapa e registra o resultado de cada operação. |
| `__main__.py` | Expõe `validar`, `planejar`, `login` e `atualizar`, seleciona o mapa solicitado e configura os logs. |

## Sequência de execução

1. Valide o cadastro completo e selecione o mapa solicitado quando houver `--mapa`.
2. Para cada mapa selecionado, valide todos os seus CSVs locais. Erros em um mapa impedem a abertura daquele mapa. O navegador é iniciado após a primeira validação bem-sucedida.
3. Abra cada mapa em uma página própria do mesmo perfil persistente. Confirme que o editor corresponde ao `mid` do cadastro e que todos os nomes de camada esperados têm um menu associado.
4. Reimporte e verifique uma camada por vez. Apenas as camadas com CSV local são selecionadas.

Resultados são registrados por camada. Em caso de falha, feche a página do mapa e siga para os demais. Camadas já concluídas podem ter sido salvas antes da falha. Se o Google exigir autenticação ou uma verificação de segurança, a execução inteira é interrompida.

Os testes verificam validação local, filtragem, ordem das checagens, isolamento de falhas e o tratamento de operações do navegador com mocks.
