# CLS PreToolUse Hook Template
# Copy to {PROJECT_ROOT}/.claude/hooks/PreToolUse.ps1
# Customize {PLACEHOLDER} values before use.

param([string] , [string] )

# Configuration
 = "{PROJECT_ROOT}/data/state/cog_step.json"
 = 300
 = {MAX_RECURSION_DEPTH}
 = @("{PROJECT_ROOT}/scripts/safety", "{PROJECT_ROOT}/data/safety")

# CHECK 1: COG_STEP declaration for Write/Edit
if ( -match "^(Write|Edit)$") {
    if (-not (Test-Path )) {
        Write-Output "[COG_STEP] Blocked: no cognitive step declared"
        exit 1
    }
    try {
         = Get-Content  -Raw | ConvertFrom-Json
         = [datetime]::Parse(.declared_at)
        if (((Get-Date) - ).TotalSeconds -gt ) {
            Write-Output "[COG_STEP] Declaration expired"
            exit 1
        }
    } catch {
        Write-Output "[COG_STEP] Cog step file corrupted"
        exit 1
    }
}

# CHECK 2: WRITE_PROTECT
if ( -eq "Write" -or  -eq "Edit") {
    foreach ( in ) {
        if ( -match ) {
            Write-Output "[FUSE_BOARD] WRITE_PROTECT: "
            exit 1
        }
    }
}

# CHECK 3: RECURSION_LIMIT
 = (Get-PSCallStack | Measure-Object).Count
if ( -gt ) {
    Write-Output "[FUSE_BOARD] RECURSION: depth="
    exit 1
}

# All passed
@{ ok =  } | ConvertTo-Json
