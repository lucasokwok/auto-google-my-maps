# Implementação pública de referência

Repositório externo de referência:

https://github.com/jlanza/red-fleet-stations-mymaps-updater

Se quiser examinar o código localmente, clone-o **neste caminho** a partir da raiz do projeto:

```bash
git clone https://github.com/jlanza/red-fleet-stations-mymaps-updater.git references/red-fleet-stations-mymaps-updater
```

O diretório clonado é ignorado pelo `.gitignore` deste repositório, de modo que o código de terceiros **não será commitado por acidente**. O código externo não está incluído neste ZIP. Consulte a licença e a procedência antes de reutilizar trechos.

Interessa, em especial, estudar a navegação com Playwright, a autenticação e o fluxo de interação com as camadas. A integração final será implementada nos módulos próprios deste projeto e adaptada a cinco camadas por mapa.
