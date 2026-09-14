param(
    [string[]]$Browsers = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    )
)

$fixture = Join-Path $PSScriptRoot "fixtures\quality-harness.html"
$outputRoot = Join-Path $env:TEMP "customer-form-context-menu-quality"
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$ran = 0
foreach ($browser in $Browsers) {
    if (-not (Test-Path -LiteralPath $browser)) { Write-Output "browser unavailable: $browser"; continue }
    $name = [IO.Path]::GetFileNameWithoutExtension($browser).ToLowerInvariant()
    $profile = Join-Path $outputRoot "$name-profile"
    $screenshot = Join-Path $outputRoot "$name.png"
    $dom = & $browser --headless=new --no-sandbox --disable-gpu --no-first-run --no-default-browser-check --window-size=1440,1000 --virtual-time-budget=1000 "--user-data-dir=$profile" "--screenshot=$screenshot" --dump-dom "file:///$($fixture.Replace('\', '/'))" 2>$null
    $ran += 1
    if ($dom -notmatch 'id="result"[^>]*data-status="passed"') { throw "Quality harness failed in ${name}: $dom" }
    Write-Output "quality acceptance passed: $name; screenshot=$screenshot"
}
if ($ran -eq 0) { throw "No supported browser executable was available" }
