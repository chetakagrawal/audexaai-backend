# Database Access Options

## Option 1: Adminer (Web UI) - Easiest ✅

**Already set up!** Access at: http://localhost:8080

### Connection Details:
- **System**: PostgreSQL
- **Server**: `172.17.0.1` ✅ (Docker bridge gateway - **This works!**)
- **Username**: `postgres`
- **Password**: `audexa123`
- **Database**: `audexa`

**Note**: `172.17.0.1` is the Docker bridge gateway IP that allows containers to reach services on the host.

### If Adminer container isn't running:
```bash
docker start adminer
```

### To stop Adminer:
```bash
docker stop adminer
```

---

## Option 2: pgAdmin (Desktop App)

1. **Download**: https://www.pgadmin.org/download/
2. **Install** pgAdmin
3. **Add Server**:
   - Name: `Audexa Local`
   - Host: `localhost`
   - Port: `5432`
   - Username: `postgres`
   - Password: `audexa123`
   - Database: `audexa`

---

## Option 3: DBeaver (Universal DB Tool)

1. **Download**: https://dbeaver.io/download/
2. **Install** DBeaver
3. **New Connection** → PostgreSQL:
   - Host: `localhost`
   - Port: `5432`
   - Database: `audexa`
   - Username: `postgres`
   - Password: `audexa123`

---

## Option 4: VS Code Extension

1. Install **"PostgreSQL"** extension in VS Code
2. Add connection:
   - Host: `localhost`
   - Port: `5432`
   - Database: `audexa`
   - User: `postgres`
   - Password: `audexa123`

---

## Option 5: Command Line (psql)

```bash
# Connect via Docker
docker exec -it postgres-audexa psql -U postgres -d audexa

# Or if you have psql installed locally
psql -h localhost -p 5432 -U postgres -d audexa
```

### Useful psql commands:
```sql
\dt              -- List all tables
\d tenants       -- Describe tenants table
\d users         -- Describe users table
SELECT * FROM tenants;
SELECT * FROM users;
\q               -- Quit
```

---

## Connection String Reference

```
postgresql+psycopg://postgres:audexa123@localhost:5432/audexa
```

**Breakdown:**
- Protocol: `postgresql+psycopg`
- User: `postgres`
- Password: `audexa123`
- Host: `localhost`
- Port: `5432`
- Database: `audexa`

