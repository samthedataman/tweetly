#!/bin/bash

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXQiOiIweDg3YWMzMjRkMjRhMmVlNTk0NTYzMjFjMzdjMzU2MGE4MjRmMzc1YjMiLCJ1c2VyX2lkIjoiMDNiY2I2ZDMtOTVhZC00YjUxLWE2NzAtMjY0OTA3NTI2NDc2IiwiZXhwIjoxNzUxOTUxMzM3LCJpYXQiOjE3NTEzNDY1Mzd9.seDkG5bcv66SisYPIjmLgQHLxkcYCNXEa6EW7GcxOoQ"
WALLET="0x87ac324d24a2ee59456321c37c3560a824f375b3"
TIMESTAMP=$(date +%s)
SESSION_ID="test_session_$TIMESTAMP"

echo "🚀 Testing message save with curl"
echo "Session ID: $SESSION_ID"
echo "Timestamp: $TIMESTAMP"
echo ""

curl -X POST http://localhost:8000/v1/conversations/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Wallet-Address: $WALLET" \
  -d '{
    "message": {
      "id": "msg_'$SESSION_ID'_1",
      "conversation_id": "'$SESSION_ID'",
      "session_id": "'$SESSION_ID'",
      "role": "user",
      "text": "Hello! Testing automatic user creation.",
      "timestamp": '$TIMESTAMP',
      "platform": "claude"
    },
    "conversation_id": "'$SESSION_ID'",
    "session_id": "'$SESSION_ID'",
    "wallet": "'$WALLET'"
  }' \
  -v