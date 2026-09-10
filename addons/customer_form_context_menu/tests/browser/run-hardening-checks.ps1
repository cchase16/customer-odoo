param(
    [string[]]$Browsers = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    )
)

$moduleRoot = Join-Path $PSScriptRoot "..\.."
$fixture = Join-Path $PSScriptRoot "fixtures\conflict-harness.html"
$outputRoot = Join-Path $env:TEMP "customer-form-context-menu-hardening"
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$sourceFiles = Get-ChildItem (Join-Path $moduleRoot "static\src") -Recurse -File | Where-Object { $_.Extension -in @(".js", ".xml", ".scss") }
$forbidden = @(
    @{ Pattern = '\beval\s*\('; Name = 'dynamic eval' },
    @{ Pattern = 'new\s+Function\s*\('; Name = 'dynamic function construction' },
    @{ Pattern = '\binnerHTML\b|insertAdjacentHTML'; Name = 'raw HTML injection' },
    @{ Pattern = '\bfetch\s*\(|\bXMLHttpRequest\b'; Name = 'direct network request' }
)
foreach ($rule in $forbidden) {
    $matches = Select-String -Path $sourceFiles.FullName -Pattern $rule.Pattern
    if ($matches) { throw "Hardening violation ($($rule.Name)): $($matches | Out-String)" }
}
$coordinator = Get-Content (Join-Path $moduleRoot "static\src\coordinator\context_menu_coordinator.js") -Raw
foreach ($required in @("defaultPrevented", "removeEventListener", "executed", "focus")) {
    if ($coordinator -notmatch [regex]::Escape($required)) { throw "Coordinator lifecycle control missing: $required" }
}
$provider = Get-Content (Join-Path $moduleRoot "static\src\providers\navigation_provider.js") -Raw
foreach ($forbiddenNavigation in @("window.history", "window.location", "location.reload", "\.discard\s*\(")) {
    if ($provider -match $forbiddenNavigation) { throw "Unsafe navigation path found: $forbiddenNavigation" }
}

$ran = 0
foreach ($browser in $Browsers) {
    if (-not (Test-Path -LiteralPath $browser)) { Write-Output "browser unavailable: $browser"; continue }
    $name = [IO.Path]::GetFileNameWithoutExtension($browser).ToLowerInvariant()
    $profile = Join-Path $outputRoot "$name-profile"
    $screenshot = Join-Path $outputRoot "$name.png"
    $dom = & $browser --headless=new --no-sandbox --disable-gpu --no-first-run --no-default-browser-check --window-size=1440,1000 --virtual-time-budget=1000 "--user-data-dir=$profile" "--screenshot=$screenshot" --dump-dom "file:///$($fixture.Replace('\', '/'))" 2>$null
    $ran += 1
    if ($dom -notmatch 'id="result"[^>]*data-status="passed"') { throw "Hardening harness failed in ${name}: $dom" }
    Write-Output "hardening checks passed: $name; screenshot=$screenshot"
}
if ($ran -eq 0) { throw "No supported browser executable was available" }
Write-Output "static source checks passed: $($sourceFiles.Count) source files"
