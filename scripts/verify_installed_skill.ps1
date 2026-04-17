$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$installed = Join-Path $repoRoot "_skill_install_test"

Push-Location $repoRoot
try {
    if (Test-Path -LiteralPath $installed) {
        Remove-Item -LiteralPath $installed -Recurse -Force
    }

    rtk python .\scripts\install_skill.py --target $installed | Out-Host

    rtk python "$installed\scripts\remember_transcript.py" "$repoRoot\examples\transcript.json" | Out-Host
    rtk python "$installed\scripts\recall_memory.py" memory communication | Out-Host
    rtk python "$installed\scripts\run_prune_mem.py" report --emit | Out-Host
}
finally {
    Pop-Location
}
