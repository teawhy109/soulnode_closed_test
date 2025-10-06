# test_suite.ps1
# Smoke test suite for SoulNode memory + GPT fallback

$headers = @{ "Content-Type" = "application/json" }
$base = "http://127.0.0.1:5000/ask"

# --- Pam Facts ---
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="what's Pam's full name" } | ConvertTo-Json) -Headers $headers
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="where was Pam born" } | ConvertTo-Json) -Headers $headers
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="what's Pam's hometown" } | ConvertTo-Json) -Headers $headers
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="who were Pam's prayer warriors" } | ConvertTo-Json) -Headers $headers
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="what kind of dog was Yasha" } | ConvertTo-Json) -Headers $headers

# --- User Memory (store / recall / forget) ---
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="remember Ty's favorite color is forest green" } | ConvertTo-Json) -Headers $headers
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="what's Ty's favorite color" } | ConvertTo-Json) -Headers $headers
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="forget Ty's favorite color" } | ConvertTo-Json) -Headers $headers
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="what's Ty's favorite color" } | ConvertTo-Json) -Headers $headers

# --- GPT Fallback ---
Invoke-WebRequest -Uri $base -Method Post -Body (@{ text="how many books are in the Bible" } | ConvertTo-Json) -Headers $headers