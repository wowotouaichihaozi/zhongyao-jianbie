[CmdletBinding(SupportsShouldProcess = $true)]
param([Parameter(Mandatory = $true)][string]$Url)
$ErrorActionPreference = 'Stop'
$address = [Uri]$Url
if ($address.Scheme -ne 'http' -or $address.Host -ne '127.0.0.1' -or $address.AbsolutePath -ne '/login' -or $address.UserInfo -or $address.Query -or $address.Fragment) { throw 'Only the local login address can be opened.' }
if ($PSCmdlet.ShouldProcess($address.AbsoluteUri, 'Open the default browser')) {
    $request = New-Object System.Diagnostics.ProcessStartInfo
    $request.FileName = $address.AbsoluteUri
    $request.UseShellExecute = $true
    $request.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Normal
    [System.Diagnostics.Process]::Start($request) | Out-Null
}
