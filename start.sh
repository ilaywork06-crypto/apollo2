#!/bin/bash

# ─── AmoSight — הרצת השרת והפרונטאנד ─────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "🚀  מפעיל AmoSight..."
echo ""

# הרג תהליכים קודמים אם קיימים
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# הפעל שרת Python
echo "⚙️   מפעיל שרת..."
cd "$ROOT"
python -m src.api.app &
BACKEND_PID=$!

# הפעל פרונטאנד
echo "🌐  מפעיל פרונטאנד..."
cd "$ROOT/frontend/web"
npm start &
FRONTEND_PID=$!

# המתן שהשרת יהיה מוכן ואז פתח דפדפן
echo "⏳  ממתין שהכל יעלה..."
sleep 6
open http://localhost:3000

echo ""
echo "✅  AmoSight פועל!"
echo "   שרת:      http://localhost:8000"
echo "   אפליקציה: http://localhost:3000"
echo ""
echo "   לעצירה — לחץ Ctrl+C"
echo ""

# כשלוחצים Ctrl+C — עצור הכל
trap "echo ''; echo '🛑  עוצר...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
