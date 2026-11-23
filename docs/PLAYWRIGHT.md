# Playwright e Google My Maps

## Autenticação e recuperação de sessão

`login` usa `launch_persistent_context()` com uma janela visível. O padrão é o Chromium do Playwright. Com `--navegador edge`, o Playwright abre o Microsoft Edge instalado pelo canal `msedge`. Conclua o login manual na conta com acesso de edição e pressione Enter quando a página Minha Conta abrir. O programa verifica o acesso à página pela mesma sessão antes de fechar o navegador. [Navegadores com suporte no Playwright](https://playwright.dev/python/docs/browsers#google-chrome--microsoft-edge)

`atualizar` reutiliza `runtime/google_profile/` no Chromium ou `runtime/google_profile_edge/` no Edge e abre uma página por mapa. Se o Google redirecionar para o login, sinalizar sessão não autorizada ou apresentar uma verificação reconhecida, a atualização é interrompida com uma mensagem no terminal e no log. Execute `login` com o mesmo navegador e perfil e repita o comando após conferir a última camada processada. Conclua verificações de segurança manualmente na sessão interativa.

Mantenha o perfil em um diretório local persistente. Use um processo por perfil de cada vez. Se o navegador não iniciar, confirme a instalação, a disponibilidade de uma sessão gráfica e se outro processo está usando o perfil. A aceitação do login pelo Google depende do ambiente em que o navegador é executado.

## Reimportação

1. Abra a URL de edição cadastrada. Confirme o `mid` e a presença do controle de edição **Adicionar camada**.
2. Identifique cada camada pelo título exato no cabeçalho da legenda e confirme o menu de opções desse cabeçalho.
3. Acesse **Reimportar e mesclar → Reimportar → Atualizar itens correspondentes**.
4. Envie os bytes validados do CSV pelo seletor de arquivos e confirme a seleção no Picker quando indicada.
5. Selecione a coluna configurada nos campos **Dados da camada** e **Dados enviados**. Clique em **Concluir**.
6. Aguarde um aviso novo e explícito de sucesso e o fechamento do assistente. Um aviso de falha, um diálogo inesperado ou a ausência de confirmação após o envio interrompe o mapa.

Pela semântica documentada pelo Google, a operação inclui os itens novos, atualiza os correspondentes e remove os ausentes do CSV. Os correspondentes podem manter estilos personalizados e fotos. [Ajuda oficial do Google My Maps](https://support.google.com/mymaps/answer/3024836?hl=pt-BR)

## Validação efetiva e limites

Os testes automatizados com mocks cobrem a navegação para o editor, a seleção de camadas, as etapas do Picker, a correspondência e os caminhos de erro. Um ensaio em Chromium com páginas simuladas exercitou a interação em português e inglês, incluindo o envio de um CSV com BOM.

A homologação ainda precisa confirmar, no editor autenticado, a estrutura real do cabeçalho e dos menus, o seletor de arquivos, os dois campos de correspondência e o aviso de sucesso ou erro. A aceitação da sessão persistente pelo Google também precisa de verificação manual. Os seletores usam textos e nomes acessíveis em inglês e português e dependem da estrutura semântica da legenda. Variações de interface podem interromper a operação.

Fechar um diálogo não é confirmação de sucesso. Se o log indicar **resultado indeterminado**, abra o mapa, confira os dados e o estilo da camada indicada e só então decida se é necessário repetir. A atualização de várias camadas não é uma transação única. Execute primeiro em mapas fictícios e compare o efeito por ID depois de reabrir o mapa.
