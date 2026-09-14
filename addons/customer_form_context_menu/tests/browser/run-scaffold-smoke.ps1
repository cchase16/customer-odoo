param(
    [string]$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
)

$fixture = Join-Path $PSScriptRoot "fixtures\surface-harness.html"
$profile = Join-Path $env:TEMP "customer-form-context-menu-smoke"
if (-not (Test-Path -LiteralPath $Chrome)) {
    throw "Chrome executable not found: $Chrome"
}
if (-not (Test-Path -LiteralPath $fixture)) {
    throw "Browser fixture not found: $fixture"
}

$dom = & $Chrome --headless=new --no-sandbox --disable-gpu --no-first-run --no-default-browser-check "--user-data-dir=$profile" --dump-dom "file:///$($fixture.Replace('\', '/'))" 2>$null
if ($dom -notmatch 'id="smoke-result"[^>]*data-status="passed"') {
    throw "Surface harness did not pass: $dom"
}
Write-Output "browser scaffold smoke: passed"
