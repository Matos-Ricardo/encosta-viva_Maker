# Como publicar no GitHub (única forma de entrega aceita)

O enunciado da MakerLab só aceita **link do GitHub**. Arquivos ZIP, RAR, DOC, DOCX e PDF não são aceitos.

1. No GitHub, crie um repositório **público** novo (sugestão: `encosta-viva-makerlab`), sem README inicial.
   - Atenção: o repositório `jzampieri/cp_04_iot` já contém outro projeto (o assistente de voz Nexus). Use um repositório separado ou outra pasta, para a correção não se confundir.
2. Extraia o ZIP e entre na pasta `encosta-viva`. Ela deve virar a **raiz** do repositório (README.md, api/, firmware/, hardware/, docs/, .github/).
3. Confira os segredos antes de enviar:
   - `firmware/.../encosta_viva_esp32.ino` deve estar com `SEU_WIFI` e `SUA_SENHA`.
   - Não pode existir `api/.env` nem arquivos `.db` (o `.gitignore` já bloqueia).
4. Envie:
   ```bash
   git init
   git add .
   git commit -m "Encosta Viva: robô sentinela com IA (MakerLab, GS 2026.2)"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/encosta-viva-makerlab.git
   git push -u origin main
   ```
5. Na aba **Actions** do GitHub, confirme que o workflow `testes` ficou verde.
6. Suba o vídeo no YouTube (não listado serve), cole o link em **dois lugares** (README.md e docs/FICHA_TECNICA.md, procure `COLE AQUI`) e cole também o link do repositório na ficha.
7. Abra o repositório em aba anônima para confirmar que está público. Só **um** integrante entrega o link no Teams da disciplina, até 19/11 às 23h55.
