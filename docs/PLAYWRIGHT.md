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
4. No seletor do Google, abra **Fazer upload**. Ao localizar o campo oculto `input[type="file"][jsname="G1bupd"]` que aceita CSV, o Playwright aguarda dois segundos para dar tempo de o seletor inicializar e então entrega o caminho com `set_input_files()`. A mesma pausa vale para uma retentativa pelo campo. Em outras versões da interface, o programa usa **Procurar** para localizar o campo acionado pelo botão. A opção `--arrastar-csv` permite testar a área de soltar arquivos. O aplicativo confere o CSV original, confirma em **Selecionar** quando necessário e aguarda o fechamento da tela de upload. [Envio de arquivos no Playwright](https://playwright.dev/python/docs/input#upload-files)
5. Selecione a coluna configurada nos grupos **Layer data** e **Uploaded data** (ou **Dados da camada** e **Dados enviados**). Nos controles de opção, o programa aceita o BOM inicial que o My Maps pode exibir como parte do nome da coluna e verifica se os dois lados estão marcados antes de clicar em **Concluir**.
6. Aguarde o fechamento do assistente e um novo aviso de sucesso. No teste no Edge, o My Maps exibiu **A camada foi atualizada com novo conteúdo.** após **Concluir**, na barra de notificações. O programa aceita esse texto quando ele aparece depois do clique. Um aviso de falha, um diálogo inesperado ou a ausência de confirmação após o envio encerra a tentativa daquela camada. O erro fica no log e a próxima camada começa em uma nova página do editor.

Pela semântica documentada pelo Google, a operação inclui os itens novos, atualiza os correspondentes e remove os ausentes do CSV. Os correspondentes podem manter estilos personalizados e fotos. [Ajuda oficial do Google My Maps](https://support.google.com/mymaps/answer/3024836?hl=pt-BR)

Se o navegador falhar durante a seleção ou o envio, o log identifica a etapa, como abrir **Fazer upload**, acionar **Procurar**, preparar o campo, entregar o CSV ou aguardar a confirmação do seletor. Quando disponíveis, também registra se o campo recebeu o nome e o tamanho esperados, os códigos HTTP observados e as falhas de rede reconhecidas. Se o seletor continuar aberto, o log também registra o estado de **Selecionar**, **Procurar**, da barra de progresso e dos alertas, sem registrar o conteúdo exibido. A reimportação só é confirmada na interface do mapa. URLs, cabeçalhos e corpos de requisição ficam fora do log.

O programa aguarda dois segundos e tenta a mesma camada uma vez em uma nova página se o prazo se esgotar antes da entrega, se houver uma falha temporária reconhecida no upload ou se o seletor permanecer aberto após 60 segundos. A última condição se aplica mesmo com respostas HTTP `200` ou `204`, pois elas confirmam requisições do navegador e o fluxo ainda está antes de **Concluir**. Recusas de acesso, limites de requisições e pedidos de espera do servidor impedem a retentativa quando reconhecidos. O resultado indeterminado após **Concluir** fica para conferência porque o mapa pode já ter sido atualizado.

## Validação efetiva e limites

Os testes automatizados com mocks cobrem a navegação para o editor, a seleção de camadas, as etapas do Picker, a correspondência e os caminhos de erro. Um ensaio em Chromium com páginas simuladas exercitou a interação em português e inglês, incluindo o envio de um CSV com BOM.

Um teste manual no Edge do Windows reutilizou a sessão e confirmou a atualização de uma camada no editor autenticado. Em outra execução, o campo recebeu o CSV e o seletor continuou aberto após respostas HTTP `200` e `204`. A retentativa desse cenário foi exercitada com páginas simuladas no Chromium e ainda precisa ser confirmada no Edge do Windows. Os seletores usam textos e nomes acessíveis em inglês e português e dependem da estrutura semântica da legenda. Variações de interface podem interromper a operação.

Fechar um diálogo não é confirmação de sucesso. Se o log indicar **resultado indeterminado**, abra o mapa, confira os dados e o estilo da camada indicada e só então decida se é necessário repetir. A atualização de várias camadas não é uma transação única. Execute primeiro em mapas fictícios e compare o efeito por ID depois de reabrir o mapa.
