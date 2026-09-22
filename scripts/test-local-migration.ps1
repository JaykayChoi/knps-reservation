param(
    [string]$PostgresImage = "postgres:17"
)

$ErrorActionPreference = "Stop"
$container = "knps-monitor-migration-$PID"
$password = "local-migration-only"
$root = Split-Path -Parent $PSScriptRoot

function Invoke-PsqlFile([string]$localPath, [string]$remoteName) {
    docker cp $localPath "${container}:/tmp/$remoteName" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not copy $localPath" }
    docker exec -e PGPASSWORD=$password $container psql -v ON_ERROR_STOP=1 -U postgres -d postgres -f "/tmp/$remoteName"
    if ($LASTEXITCODE -ne 0) { throw "SQL failed: $localPath" }
}

try {
    docker run --name $container -e "POSTGRES_PASSWORD=$password" -d $PostgresImage | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not start disposable PostgreSQL" }
    $ready = $false
    foreach ($attempt in 1..30) {
        docker exec $container pg_isready -U postgres | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "Disposable PostgreSQL did not become ready" }

    Invoke-PsqlFile "$root/tests/database/legacy_baseline.sql" "01-baseline.sql"
    Invoke-PsqlFile "$root/scripts/db/monitor_refactor_preflight.sql" "02-preflight.sql"
    Invoke-PsqlFile "$root/supabase/migrations/20260922010000_generalize_monitors.sql" "03-forward.sql"
    Invoke-PsqlFile "$root/scripts/db/monitor_refactor_verify.sql" "04-verify.sql"
    Invoke-PsqlFile "$root/tests/database/refactor_assertions.sql" "05-assert.sql"
    Invoke-PsqlFile "$root/scripts/db/monitor_refactor_rollback.sql" "06-rollback.sql"
    Invoke-PsqlFile "$root/tests/database/legacy_rollback_assertions.sql" "07-rollback-assert.sql"
    Invoke-PsqlFile "$root/supabase/migrations/20260922010000_generalize_monitors.sql" "08-forward-again.sql"
    Write-Host "Monitor migration forward/verify/rollback/forward test passed."
}
finally {
    docker rm -f $container 2>$null | Out-Null
}
