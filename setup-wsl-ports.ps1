# WSL2 Port Forwarding Script
# Run this in Windows PowerShell as Administrator

$wslIP = (wsl -- ip route show | grep default | awk '{print $3}').Trim()
$frontendPort = 5173
$backendPort = 8080

Write-Host "WSL IP: $wslIP"
Write-Host "Setting up port forwarding..."

# Remove existing rules if they exist
netsh interface portproxy delete v4tov4 listenport=$frontendPort listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov4 listenport=$backendPort listenaddress=0.0.0.0 2>$null

# Add new port forwarding rules
netsh interface portproxy add v4tov4 listenport=$frontendPort listenaddress=0.0.0.0 connectport=$frontendPort connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=$backendPort listenaddress=0.0.0.0 connectport=$backendPort connectaddress=$wslIP

# Show current rules
Write-Host "Current port forwarding rules:"
netsh interface portproxy show v4tov4

Write-Host "Access your application at:"
Write-Host "Frontend: http://localhost:$frontendPort"
Write-Host "Backend: http://localhost:$backendPort"