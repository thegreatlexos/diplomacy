# Diplomacy AI - VPS Deployment Guide

Complete guide to deploy the Diplomacy AI platform to your TransIP VPS.

## Prerequisites

**On your VPS:**
- Ubuntu 20.04+ (or Debian-based distro)
- Root or sudo access
- Domain pointed to VPS IP (optional but recommended)

## Step 1: VPS Setup

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y postgresql postgresql-contrib nginx python3 python3-pip git

# Install Node.js (for frontend build on local machine)
# You'll build frontend locally and upload the static files
```

## Step 2: Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE diplomacy_ai;
CREATE USER diplomacy WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE diplomacy_ai TO diplomacy;
\q

# Load schema
psql -U diplomacy -d diplomacy_ai -f /path/to/deployment/database/schema.sql
# Enter password when prompted
```

## Step 3: Upload Files to VPS

**From your local machine:**

```bash
# Create deployment package
cd /Users/alexandergroot/Documents/Personal/Repository/diplomacy

# Copy deployment folder to VPS
scp -r deployment root@your-vps-ip:/var/www/

# Copy games folder (this is large, ~500MB-1GB)
scp -r games root@your-vps-ip:/var/www/deployment/
```

## Step 4: Load Game Data

**On VPS:**

```bash
cd /var/www/deployment

# Install Python dependencies
pip3 install psycopg2-binary

# Load games into database
python3 database/load_games.py \
  --games-dir games \
  --db-url "postgresql://diplomacy:your-secure-password@localhost/diplomacy_ai"

# Verify data loaded
psql -U diplomacy -d diplomacy_ai -c "SELECT COUNT(*) FROM games;"
# Should show 25 games
```

## Step 5: Backend Setup

```bash
cd /var/www/deployment/backend

# Install Python dependencies
pip3 install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://diplomacy:your-secure-password@localhost/diplomacy_ai
CORS_ORIGINS=https://yourdomain.com,http://yourdomain.com
EOF

# Test backend
python3 main.py
# Press Ctrl+C after verifying it starts
```

## Step 6: Frontend Build & Upload

**On your local machine:**

```bash
cd /Users/alexandergroot/Documents/Personal/Repository/diplomacy/frontend

# Update API URL for production
cat > .env.production << EOF
VITE_API_URL=https://yourdomain.com/api
EOF

# Build frontend
npm run build

# Copy build to VPS
scp -r build root@your-vps-ip:/var/www/deployment/frontend-build/
```

## Step 7: Nginx Configuration

**On VPS:**

```bash
# Create Nginx config
cat > /etc/nginx/sites-available/diplomacy-ai << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Frontend (static files)
    location / {
        root /var/www/deployment/frontend-build;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    client_max_body_size 10M;
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/diplomacy-ai /etc/nginx/sites-enabled/

# Test Nginx config
nginx -t

# Restart Nginx
systemctl restart nginx
```

## Step 8: Backend as Systemd Service

```bash
# Create systemd service
cat > /etc/systemd/system/diplomacy-backend.service << 'EOF'
[Unit]
Description=Diplomacy AI Backend
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/deployment/backend
Environment="PATH=/usr/bin"
EnvironmentFile=/var/www/deployment/backend/.env
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Fix permissions
chown -R www-data:www-data /var/www/deployment

# Start and enable service
systemctl daemon-reload
systemctl start diplomacy-backend
systemctl enable diplomacy-backend

# Check status
systemctl status diplomacy-backend
```

## Step 9: SSL Certificate (Optional but Recommended)

```bash
# Install certbot
apt install -y certbot python3-certbot-nginx

# Get SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured by default
# Test renewal
certbot renew --dry-run
```

## Step 10: Verify Deployment

```bash
# Check backend is running
curl http://localhost:8000/

# Check frontend is accessible
curl http://localhost/

# Check from outside
curl https://yourdomain.com/
```

## Maintenance

### Update Backend Code

```bash
# On local machine, copy updated backend files
scp backend/main.py root@your-vps-ip:/var/www/deployment/backend/

# On VPS, restart service
systemctl restart diplomacy-backend
```

### Update Frontend

```bash
# On local machine, rebuild and upload
npm run build
scp -r build/* root@your-vps-ip:/var/www/deployment/frontend-build/

# No restart needed - Nginx serves static files
```

### View Logs

```bash
# Backend logs
journalctl -u diplomacy-backend -f

# Nginx access logs
tail -f /var/log/nginx/access.log

# Nginx error logs
tail -f /var/log/nginx/error.log
```

### Database Backup

```bash
# Create backup
pg_dump -U diplomacy diplomacy_ai > /backups/diplomacy_ai_$(date +%Y%m%d).sql

# Restore backup
psql -U diplomacy -d diplomacy_ai < /backups/diplomacy_ai_20260630.sql
```

## Troubleshooting

### Backend won't start
```bash
# Check logs
journalctl -u diplomacy-backend -n 50

# Test manually
cd /var/www/deployment/backend
python3 main.py
```

### Frontend shows blank page
```bash
# Check Nginx config
nginx -t

# Check file permissions
ls -la /var/www/deployment/frontend-build

# Check browser console for errors
# (API URL might be wrong)
```

### Database connection failed
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Test connection
psql -U diplomacy -d diplomacy_ai -c "SELECT 1;"

# Check DATABASE_URL in .env
cat /var/www/deployment/backend/.env
```

## Security Checklist

- [ ] Strong database password set
- [ ] Firewall configured (ufw allow 80,443)
- [ ] SSH key-only authentication
- [ ] SSL certificate installed
- [ ] Regular backups configured
- [ ] CORS_ORIGINS restricted to your domain

## Performance Tips

- Enable gzip compression in Nginx
- Set up Cloudflare for CDN (optional)
- Monitor with `htop` and `iotop`
- PostgreSQL tuning if needed

## Done!

Your Diplomacy AI platform should now be live at `https://yourdomain.com`

- Homepage: `https://yourdomain.com`
- Games list: `https://yourdomain.com/games`
- About page: `https://yourdomain.com/about`
- API: `https://yourdomain.com/api/games`
