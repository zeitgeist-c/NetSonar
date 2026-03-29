$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath "NetSonar.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

$CurrentDir = Get-Location
$PythonPath = Join-Path $CurrentDir ".venv\Scripts\pythonw.exe"
$ScriptPath = Join-Path $CurrentDir "main.py"
$IconPath = Join-Path $CurrentDir "netsonar.ico"

$Shortcut.TargetPath = $PythonPath
$Shortcut.Arguments = "`"$ScriptPath`""
$Shortcut.WorkingDirectory = $CurrentDir
$Shortcut.IconLocation = $IconPath
$Shortcut.Description = "NetSonar — AI Destekli Ağ İzleme"
$Shortcut.Save()

# "Yönetici Olarak Çalıştır" (Run as Admin) bitini ayarla (Offset 21, bit 5)
try {
    $Stream = New-Object System.IO.FileStream($ShortcutPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite)
    $Stream.Seek(21, [System.IO.SeekOrigin]::Begin) | Out-Null
    $Byte = $Stream.ReadByte()
    $Stream.Seek(21, [System.IO.SeekOrigin]::Begin) | Out-Null
    $Stream.WriteByte($Byte -bor 0x20)
    $Stream.Close()
} catch {
    Write-Warning "Yönetici yetkisi bayrağı otomatik ayarlanamadı, ancak program kendi içinde bunu yine de isteyecektir."
}

Write-Host "Kısayol başarıyla Masaüstüne oluşturuldu: NetSonar.lnk"
