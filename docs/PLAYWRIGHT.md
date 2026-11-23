# Playwright e Google My Maps

## Autenticação e recuperação de sessão

`login` usa `launch_persistent_context()` com uma janela visível. O padrão é o Chromium do Playwright. Com `--navegador edge`, o Playwright abre o Microsoft Edge instalado pelo canal `msedge`. Conclua o login manual na conta com acesso de edição e pressione Enter quando a página Minha Conta abrir. O programa verifica o acesso à página pela mesma sessão antes de fechar o navegador. [Navegadores com suporte no Playwright](https://playwright.dev/python/docs/browsers#google-chrome--microsoft-edge)

`atualizar` reutiliza o perfil indicado em `--perfil-dir` e abre uma página por mapa. Os perfis padrão são `runtime/google_profile/` no Chromium e `runtime/google_profile_edge/` no Edge. Se o Google redirecionar para o login, sinalizar sessão não autorizada ou apresentar uma verificação reconhecida, a atualização é interrompida com uma mensagem no terminal e no log. Renove a sessão com o mesmo navegador e perfil e confira a última camada processada antes de repetir o comando.

Mantenha o perfil em um diretório local persistente. Use um processo por perfil de cada vez. Se o navegador não iniciar, confirme a instalação, a disponibilidade de uma sessão gráfica e se outro processo está usando o perfil. A aceitação do login pelo Google depende do ambiente em que o navegador é executado.

### Sessão dedicada no Edge do Windows

Em um teste manual no Windows, o login aberto pelo Playwright recebeu a mensagem **Este navegador ou app pode não ser seguro**. A sessão foi criada no Edge iniciado diretamente, com `--user-data-dir` apontando para `%LOCALAPPDATA%\auto-google-my-maps\edge-profile`. Após fechar essa janela, o comando `login --navegador edge --perfil-dir` reabriu o mesmo perfil e confirmou o acesso à página **Minha Conta**. [Comandos no README](../README.md#login-confirmado-com-o-edge-no-windows) · [Configuração UserDataDir do Edge](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-browser-policies/userdatadir)

O caminho em `%LOCALAPPDATA%` mantém o perfil fora do repositório e do OneDrive. Em `edge://version`, verifique se o **Caminho do perfil** fica dentro do diretório configurado. O comando deve receber o diretório informado a `--user-data-dir`. Feche as janelas desse perfil antes de trocar entre o Edge aberto diretamente e o Playwright.

Se a sessão expirar, abra o Edge diretamente com a mesma pasta e faça o login manual. Feche a janela e repita a verificação com o Playwright. Use o mesmo `--navegador` e o mesmo `--perfil-dir` para atualizar.

## Reimportação

1. Abra a URL de edição cadastrada e confirme o `mid` do mapa de destino.
2. Aguarde o título exato de cada camada e associe-o a um único cabeçalho da legenda com controle de visibilidade e menu de opções. O log distingue um título ausente de um título que não pôde ser associado ao menu.
3. Acesse **Reimportar e mesclar → Reimportar → Atualizar itens relacionados**. A opção também pode aparecer como **Atualizar itens correspondentes** ou **Update matching items**.
4. No seletor de arquivos do Google, abra **Fazer upload → Procurar**. O Playwright entrega o caminho do CSV original ao seletor acionado pelo botão. Para testar a área **ou arraste um arquivo até aqui**, adicione `--arrastar-csv` ao comando `atualizar`. Nos dois modos o aplicativo confere o conteúdo do arquivo original, confirma em **Selecionar** quando necessário e aguarda o fechamento da tela de upload. Se o seletor continuar aberto, o log informa os códigos HTTP reconhecidos para o upload e a contagem de falhas de rede, sem URLs ou dados da requisição.
5. Selecione a coluna configurada nos campos **Dados da camada** e **Dados enviados**. Clique em **Concluir**.
6. Aguarde um aviso novo e explícito de sucesso e o fechamento do assistente. Um aviso de falha, um diálogo inesperado ou a ausência de confirmação após o envio interrompe o mapa.

Pela semântica documentada pelo Google, a operação inclui os itens novos, atualiza os correspondentes e remove os ausentes do CSV. Os correspondentes podem manter estilos personalizados e fotos. [Ajuda oficial do Google My Maps](https://support.google.com/mymaps/answer/3024836?hl=pt-BR)

## Validação efetiva e limites

Os testes automatizados com mocks cobrem a navegação para o editor, a seleção de camadas, as etapas do Picker, a correspondência e os caminhos de erro. Um ensaio em Chromium com páginas simuladas exercitou a interação em português e inglês, incluindo o envio de um CSV com BOM.

O reaproveitamento da sessão no Edge foi confirmado na página **Minha Conta** em um teste no Windows. A homologação ainda precisa confirmar, no editor autenticado, a estrutura real do cabeçalho e dos menus, o seletor de arquivos, os dois campos de correspondência e o aviso de sucesso ou erro. Os seletores usam textos e nomes acessíveis em inglês e português e dependem da estrutura semântica da legenda. Variações de interface podem interromper a operação.

Fechar um diálogo não é confirmação de sucesso. Se o log indicar **resultado indeterminado**, abra o mapa, confira os dados e o estilo da camada indicada e só então decida se é necessário repetir. A atualização de várias camadas não é uma transação única. Execute primeiro em mapas fictícios e compare o efeito por ID depois de reabrir o mapa.
