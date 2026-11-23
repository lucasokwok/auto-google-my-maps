# Playwright e Google My Maps

## Escopo da integração de navegador

Usar Playwright **somente** para as interações na interface web do Google My Maps. Nenhuma API de planilhas ou método não oficial de escrita no Google é necessário para este desenho.

A rotina ainda a implementar deverá:

1. Utilizar uma sessão autenticada previamente, guardada localmente em `runtime/`.
2. Navegar para a URL de edição do mapa (sem registrar essa URL em logs).
3. Encontrar cada camada pelo nome exato do arquivo: `pontos_01.csv`, ..., `pontos_05.csv`.
4. Acionar **Reimportar e mesclar → Reimportar → Atualizar itens correspondentes**.
5. Selecionar o CSV local apropriado no seletor de upload.
6. Informar a coluna de identificação para a correspondência, quando solicitada.
7. Verificar o resultado da operação antes de seguir para a próxima camada.

### Autenticação

Execute `python -m auto_googlemymaps login` para abrir o navegador e entrar manualmente na conta Google que possui acesso de edição aos mapas. O aplicativo **não solicita, lê ou armazena a senha**. A pasta persistente do navegador fica em `runtime/chromium-profile/` e está ignorada pelo Git.

### Confiabilidade

- Preferir locators semânticos (`get_by_role`, `get_by_text`) e esperas explícitas.
- Não basear a lógica em pausas fixas nem coordenadas de tela.
- Usar `set_input_files()` quando houver `<input type="file">` acessível.
- Processar uma camada por vez e registrar o status por mapa/camada.
- Falhar de forma fechada: se a interface divergir, interromper o mapa em vez de adivinhar cliques.
- Não publicar capturas, rastros, perfil autenticado ou URLs.
- Não automatizar digitação de senha ou contornar desafios de segurança.

A reimportação está descrita na ajuda oficial do My Maps: https://support.google.com/mymaps/answer/3024836?hl=pt-BR.

**Estado:** esta parte é uma especificação de implementação; a rotina de reimportação ainda não foi implementada.
