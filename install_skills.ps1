# Link this workshop's skills into %USERPROFILE%\.claude\skills on Windows.
#
#   cd <workshop>; .\install_skills.ps1
#
# Junctions, not copies: the repo stays the one source and an edit here is live
# immediately. Junctions need no admin rights; symlinks on Windows do.
#
# Skills are picked up when a session STARTS -- the one you run this in will not
# see them. And a skill that did not load fails SILENTLY, which is why every role
# brief says to name the skills you can actually see, first thing.
$shop = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$skills = Join-Path $shop "skills"
$n = 0
if (Test-Path $skills) {
    Get-ChildItem -Path $skills -Directory | ForEach-Object {
        $link = Join-Path $dest $_.Name
        if (Test-Path $link) { cmd /c rmdir "$link" 2>$null }
        cmd /c mklink /J "$link" "$($_.FullName)" | Out-Null
        Write-Host "ok    $link -> $($_.FullName)"
        $script:n++
    }
}
if ($n -eq 0) {
    Write-Host "note  skills/ is empty, so nothing was linked. That is the shipped state."
    Write-Host "      Skills come from @scout's survey (card #1). When one earns its place,"
    Write-Host "      put it in skills\<name>\SKILL.md and re-run this. See skills\README.md."
} else {
    Write-Host "done -- $n linked. START A NEW SESSION for them to be picked up."
}
