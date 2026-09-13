# Repositório e verificação Git

Repositório: https://github.com/leonardosovienski/cain.git. Branch de uso/publicação: **main**.
Checkout principal nesta máquina: `C:/CAIN/projeto`.

```powershell
git status --short --branch
git fetch origin --prune
git rev-parse HEAD
git ls-remote origin refs/heads/main
git branch -a
```

Os SHAs de HEAD e main remota devem coincidir após publicar. Uma árvore suja exige identificar as alterações antes de concluir equivalência.
Para commits, revisar o diff e selecionar explicitamente arquivos pertinentes. Bancos, modelos, segredos, configurações locais e recibos restritos não entram no repositório.
Não usar `git add .` como substituto dessa revisão, nem apagar worktrees para reduzir a lista de branches.

O estado instalado é documentado separadamente em [ESTADO_DO_PROJETO.md](ESTADO_DO_PROJETO.md).
Uma CI aprovada pertence ao commit que executou; veja o SHA da execução antes de atribuí-la a uma entrega nova.
