# Run on a Windows PC that can open the official RISE ETF Finder.
# Read-only: writes a new local capture; no credentials or repository access.
[CmdletBinding()]
param([string]$OutputDirectory = '.')
$ErrorActionPreference = 'Stop'
$root = 'https://kbam.co.kr'
$started = [DateTimeOffset]::UtcNow
function Read-Official([string]$url) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 25 -MaximumRedirection 0
    # Read the original bytes rather than relying on a locale-dependent decoder.
    $stream = $response.RawContentStream
    $stream.Position = 0
    $buffer = New-Object System.IO.MemoryStream
    try {
        $stream.CopyTo($buffer)
        return [Convert]::ToBase64String($buffer.ToArray())
    } finally { $buffer.Dispose() }
}
$overview = Read-Official "$root/find"
$pages = @()
for ($n = 1; ; $n++) {
    $url = "$root/api/products/etfs?page=$n"
    $raw = Read-Official $url
    $data = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($raw)) | ConvertFrom-Json
    if ($n -eq 1) { $last = [int]$data.page_info.total_page }
    if ($last -lt 1 -or $last -gt 100 -or [int]$data.page_info.current_page -ne $n -or [int]$data.page_info.total_page -ne $last) { throw 'Unexpected official pagination; capture not saved.' }
    $pages += [ordered]@{url=$url; body_b64=$raw}
    if ($n -eq $last) { break }
}
$bundle = [ordered]@{format='KBAM_PORTABLE_V1'; started_at=$started.ToString('o'); captured_at=[DateTimeOffset]::UtcNow.ToString('o'); finder_url="$root/find"; overview_b64=$overview; pages=$pages}
$path = Join-Path (Resolve-Path $OutputDirectory) ('RISE-issuer-' + $started.ToString('yyyyMMddTHHmmssfffffffZ') + '.json')
[IO.File]::WriteAllText($path, ($bundle | ConvertTo-Json -Depth 6 -Compress), (New-Object Text.UTF8Encoding($false)))
Write-Output "Saved $path"
