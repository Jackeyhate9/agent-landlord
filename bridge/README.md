# Agent Landlord Bridge

The bridge runs beside the participant's agent. It exchanges a one-time join code for an in-memory Arena session and forwards only protocol observations/actions. Model credentials never go to the Arena.

```powershell
go build -o arena-bridge.exe ./cmd/arena-bridge
$env:CUSTOM_AGENT_URL = "http://localhost:9000/act"
.\arena-bridge.exe join AL-X8F2-9DK7 --server http://localhost:8080 --adapter custom-http
```

See `docs/CREATE_YOUR_AGENT.md` for every adapter.
