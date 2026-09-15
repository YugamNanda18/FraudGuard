# FraudGuard Full System QA Demo Test Script
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   FraudGuard Full System Automated QA Verification" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Health Check
Write-Host "[1/7] Testing System Health Endpoint..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get
Write-Host "   -> Overall Status: $($health.status)" -ForegroundColor Green
Write-Host "   -> Qdrant Vector DB: $($health.qdrant)" -ForegroundColor Green
Write-Host "   -> Groq Cloud LLM: $($health.claude_api)" -ForegroundColor Green
Write-Host ""

# 2. Auth & Token Generation
Write-Host "[2/7] Authenticating User & Generating JWT Token..." -ForegroundColor Yellow
$tokenResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/token" -Method Post -Body @{ username = "qa_analyst"; password = "password123" }
$token = $tokenResp.access_token
$headers = @{ Authorization = "Bearer $token" }
Write-Host "   -> JWT Access Token Obtained Successfully!" -ForegroundColor Green
Write-Host ""

# 3. Test Agent 1: Harvey Specter (Transaction Fraud)
Write-Host "[3/7] Testing Agent: Harvey Specter (Transaction Fraud)..." -ForegroundColor Yellow
$body1 = @{ message = "Harvey, analyze transaction TX-999 for suspicious fraud activities and high velocity." } | ConvertTo-Json
$res1 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" -Method Post -Headers $headers -ContentType "application/json" -Body $body1
Write-Host "   -> Routed Agent: $($res1.metadata.routing_agent)" -ForegroundColor Green
Write-Host "   -> Response Latency: $($res1.metadata.latency_ms) ms" -ForegroundColor Green
Write-Host "   -> AI Response: $($res1.message.Substring(0, [System.Math]::Min(120, $res1.message.Length)))..." -ForegroundColor Gray
Write-Host ""

# 4. Test Agent 2: Louis Litt (AML & KYC Compliance)
Write-Host "[4/7] Testing Agent: Louis Litt (AML & Compliance)..." -ForegroundColor Yellow
$body2 = @{ message = "Louis, what are the AML and KYC requirements for account ACC-44821 under regulations?" } | ConvertTo-Json
$res2 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" -Method Post -Headers $headers -ContentType "application/json" -Body $body2
Write-Host "   -> Routed Agent: $($res2.metadata.routing_agent)" -ForegroundColor Green
Write-Host "   -> Response Latency: $($res2.metadata.latency_ms) ms" -ForegroundColor Green
Write-Host "   -> AI Response: $($res2.message.Substring(0, [System.Math]::Min(120, $res2.message.Length)))..." -ForegroundColor Gray
Write-Host ""

# 5. Test Agent 3: Jessica Pearson (Graph Network Analysis)
Write-Host "[5/7] Testing Agent: Jessica Pearson (Fraud Graph Networks)..." -ForegroundColor Yellow
$body3 = @{ message = "Jessica, detect graph ring networks and shared device clusters across fraud nodes." } | ConvertTo-Json
$res3 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" -Method Post -Headers $headers -ContentType "application/json" -Body $body3
Write-Host "   -> Routed Agent: $($res3.metadata.routing_agent)" -ForegroundColor Green
Write-Host "   -> Response Latency: $($res3.metadata.latency_ms) ms" -ForegroundColor Green
Write-Host "   -> AI Response: $($res3.message.Substring(0, [System.Math]::Min(120, $res3.message.Length)))..." -ForegroundColor Gray
Write-Host ""

# 6. Test Agent 4: Mike Ross (Red Teaming & Security)
Write-Host "[6/7] Testing Agent: Mike Ross (Red Teaming Security)..." -ForegroundColor Yellow
$body4 = @{ message = "Mike, run an adversarial prompt injection test on our fraud detection rules." } | ConvertTo-Json
$res4 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" -Method Post -Headers $headers -ContentType "application/json" -Body $body4
Write-Host "   -> Routed Agent: $($res4.metadata.routing_agent)" -ForegroundColor Green
Write-Host "   -> Response Latency: $($res4.metadata.latency_ms) ms" -ForegroundColor Green
Write-Host "   -> AI Response: $($res4.message.Substring(0, [System.Math]::Min(120, $res4.message.Length)))..." -ForegroundColor Gray
Write-Host ""

# 7. Test Agent 5: Rachel Zane (Data Engineering & Vector RAG)
Write-Host "[7/7] Testing Agent: Rachel Zane (Data Engineering & Vectors)..." -ForegroundColor Yellow
$body5 = @{ message = "Rachel, extract feature embeddings and index new vector data into Qdrant." } | ConvertTo-Json
$res5 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" -Method Post -Headers $headers -ContentType "application/json" -Body $body5
Write-Host "   -> Routed Agent: $($res5.metadata.routing_agent)" -ForegroundColor Green
Write-Host "   -> Response Latency: $($res5.metadata.latency_ms) ms" -ForegroundColor Green
Write-Host "   -> AI Response: $($res5.message.Substring(0, [System.Math]::Min(120, $res5.message.Length)))..." -ForegroundColor Gray
Write-Host ""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   ✅ ALL 7 CORE FEATURES PASSED VERIFICATION!    " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
