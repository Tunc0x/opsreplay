param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

docker compose exec backend `
    /app/.venv/bin/python `
    -m app.cli.dev `
    @CliArgs

exit $LASTEXITCODE