param(
    [string[]]$Browsers = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    )
)

$fixture = Join-Path $PSScriptRoot "fixtures\acceptance-harness.html"
$outputRoot = Join-Path $env:TEMP "customer-form-context-menu-acceptance"
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
if (-not (Test-Path -LiteralPath $fixture)) { throw "Acceptance fixture not found: $fixture" }

$ran = 0
foreach ($browser in $Browsers) {
    if (-not (Test-Path -LiteralPath $browser)) { Write-Output "browser unavailable: $browser"; continue }
    $name = [IO.Path]::GetFileNameWithoutExtension($browser).ToLowerInvariant()
    $profile = Join-Path $outputRoot "$name-profile"
    $screenshot = Join-Path $outputRoot "$name.png"
    $dom = & $browser --headless=new --no-sandbox --disable-gpu --no-first-run --no-default-browser-check --window-size=1440,1000 --virtual-time-budget=1000 "--user-data-dir=$profile" "--screenshot=$screenshot" --dump-dom "file:///$($fixture.Replace('\', '/'))" 2>$null
    $ran += 1
    if ($dom -notmatch 'id="result"[^>]*data-status="passed"') {
        throw "Acceptance harness failed in ${name}: $dom"
    }
    Write-Output "browser acceptance passed: $name; screenshot=$screenshot"
}
if ($ran -eq 0) { throw "No supported browser executable was available" }
