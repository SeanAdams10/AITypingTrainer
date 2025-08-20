uv lock --upgrade
uv sync
# uv pip list --outdated --format=json | ConvertFrom-Json | ForEach-Object { uv pip install --upgrade $_.name }
pip list --outdated --format=json | ConvertFrom-Json | ForEach-Object { pip install --upgrade $_.name }