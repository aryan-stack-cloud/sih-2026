$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$voiceDir = Join-Path $PSScriptRoot 'assets\voice'
foreach ($line in Get-Content -LiteralPath (Join-Path $root 'narration.txt')) {
    $parts = $line.Split('|', 2)
    $id = $parts[0]
    $text = $parts[1]
    $textFile = Join-Path $voiceDir "$id.txt"
    Set-Content -LiteralPath $textFile -Value $text -Encoding utf8
    & npx --yes hyperframes@0.8.73 tts $textFile -o (Join-Path $voiceDir "$id.wav") -v af_heart -s 1.08
    if ($LASTEXITCODE -ne 0) { throw "TTS failed for $id" }
    Write-Host "Finished voice $id"
}
