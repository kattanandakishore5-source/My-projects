Get-ChildItem -Path . -Include __pycache__,"*.pyc" -Recurse -Force | Remove-Item -Recurse -Force
Write-Host "Successfully cleaned all __pycache__ and .pyc files."
