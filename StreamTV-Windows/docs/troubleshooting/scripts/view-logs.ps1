# View StreamTV Logs (Windows PowerShell)

param(
    [Parameter(Position=0)]
    [string]$Action = "view",
    
    [Parameter(Position=1)]
    [string]$SearchTerm = ""
)

$LogFile = "streamtv.log"
$LogsDir = "logs"

switch ($Action.ToLower()) {
    "open" {
        if (Test-Path $LogsDir) {
            explorer $LogsDir
        } else {
            Write-Host "Logs directory not found" -ForegroundColor Yellow
        }
    }
    "search" {
        if ($SearchTerm -eq "") {
            Write-Host "Usage: .\view-logs.ps1 search SEARCH_TERM" -ForegroundColor Yellow
            exit 1
        }
        if (Test-Path $LogFile) {
            Select-String -Path $LogFile -Pattern $SearchTerm -CaseSensitive:$false
        } else {
            Write-Host "Log file not found: $LogFile" -ForegroundColor Yellow
        }
    }
    default {
        if (Test-Path $LogFile) {
            Write-Host "Recent log entries:" -ForegroundColor Cyan
            Write-Host "====================" -ForegroundColor Cyan
            Get-Content $LogFile -Tail 50
        } else {
            Write-Host "Log file not found: $LogFile" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Logs will be created when the server starts."
        }
    }
}
