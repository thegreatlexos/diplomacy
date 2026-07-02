# Diplomacy AI Deployment

This folder contains everything needed to deploy the Diplomacy AI platform to TransIP VPS.

## Structure

```
deployment/
├── backend/          # FastAPI backend + DB loader
├── database/         # Postgres schema + migration scripts
├── frontend-build/   # Built SvelteKit static files (after npm run build)
└── README.md
```

## Deployment Steps (TransIP VPS)

1. **Database Setup**
   ```bash
   # Install Postgres
   sudo apt install postgresql postgresql-contrib
   
   # Create database
   sudo -u postgres createdb diplomacy_ai
   
   # Run schema
   psql -U postgres -d diplomacy_ai -f database/schema.sql
   
   # Load game data
   python3 database/load_games.py
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Frontend Setup**
   ```bash
   # Copy built frontend to nginx
   sudo cp -r frontend-build/* /var/www/diplomacy-ai/
   
   # Configure nginx (see nginx.conf example)
   sudo systemctl restart nginx
   ```

## Environment Variables

Create `backend/.env`:
```
DATABASE_URL=postgresql://user:password@localhost/diplomacy_ai
CORS_ORIGINS=https://yourdomain.com
```

## Game Data

Games to include (25 total, excluding DeepSeek stalemates):
- Loaded via `database/load_games.py` from parent `games/` directory
- Script filters out excluded games automatically
