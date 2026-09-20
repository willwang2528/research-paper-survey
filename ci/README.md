# Optional GitHub Actions configuration

`github-actions.example.yml` is an inactive workflow template. It runs the offline regression suite on Python 3.9, 3.11 and 3.13 without API credentials.

The initial atomic push was rejected because the current GitHub OAuth credential lacks `workflow` scope. Keeping the file here allows the skill/runtime to be delivered without enabling repository automation. With appropriate GitHub authorization, copy it to `.github/workflows/test.yml` to enable it. Local `unittest` and `scripts/evolve.py check` remain fully usable.
