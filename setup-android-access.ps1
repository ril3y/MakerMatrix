# WSL2 Android Access Setup Script
# Run this in Windows PowerShell as Administrator

Write-Host "Setting up Android access to MakerMatrix..." -ForegroundColor Green

# Get WSL IP address
$wslIP = wsl -- ip route show default | wsl -- awk '{print $3}' | wsl -- head -1
Write-Host "WSL IP Address: $wslIP" -ForegroundColor Yellow

# Get Windows IP address
$windowsIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*" | Where-Object {$_.IPAddress -like "192.168.*"}).IPAddress
if (-not $windowsIP) {
    $windowsIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Ethernet*" | Where-Object {$_.IPAddress -like "192.168.*"}).IPAddress
}
Write-Host "Windows IP Address: $windowsIP" -ForegroundColor Yellow

# Remove existing port forwarding rules
Write-Host "Removing existing port forwarding rules..." -ForegroundColor Cyan
netsh interface portproxy delete v4tov4 listenport=8080 listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov4 listenport=5173 listenaddress=0.0.0.0 2>$null

# Add new port forwarding rules
Write-Host "Adding port forwarding rules..." -ForegroundColor Cyan
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=5173 listenaddress=0.0.0.0 connectport=5173 connectaddress=$wslIP

# Configure Windows Firewall
Write-Host "Configuring Windows Firewall..." -ForegroundColor Cyan
netsh advfirewall firewall delete rule name="MakerMatrix Backend" 2>$null
netsh advfirewall firewall delete rule name="MakerMatrix Frontend" 2>$null
netsh advfirewall firewall add rule name="MakerMatrix Backend" dir=in action=allow protocol=TCP localport=8080
netsh advfirewall firewall add rule name="MakerMatrix Frontend" dir=in action=allow protocol=TCP localport=5173

# Show current port forwarding rules
Write-Host "`nCurrent port forwarding rules:" -ForegroundColor Green
netsh interface portproxy show v4tov4

Write-Host "`n" -ForegroundColor Green
Write-Host "=== ANDROID CONNECTION INFO ===" -ForegroundColor Green
Write-Host "Backend API: http://$windowsIP`:8080" -ForegroundColor Yellow
Write-Host "Frontend: http://$windowsIP`:5173" -ForegroundColor Yellow
Write-Host "Use the Windows IP address ($windowsIP) in your Android app" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Green

# Test connectivity
Write-Host "`nTesting connectivity..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ Backend is accessible via localhost" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend not accessible via localhost" -ForegroundColor Red
}

Write-Host "`nSetup complete! Make sure both backend and frontend are running in WSL." -ForegroundColor Green