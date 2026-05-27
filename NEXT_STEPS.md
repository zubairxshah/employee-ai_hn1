# Next Steps - AI Personal Employee

**Last Updated:** March 4, 2026
**Current Status:** Platinum Tier Complete + Repo Cleaned

---

## Phase 1: Git Setup (Do First)

### 1.1 Initialize Main Code Repo
- [ ] `cd D:\prompteng\employee`
- [ ] `git init`
- [ ] `git add -A`
- [ ] `git commit -m "Initial commit - Platinum tier complete"`
- [ ] Create private GitHub repo (e.g., `ai-employee`)
- [ ] `git remote add origin git@github.com:YOUR_USER/ai-employee.git`
- [ ] `git push -u origin main`

### 1.2 Initialize Vault Repo (Separate)
- [ ] `cd D:\prompteng\AI_Employee_Vault`
- [ ] `git init`
- [ ] Add `.gitignore` for vault (no `.env`, no token files)
- [ ] `git add -A`
- [ ] `git commit -m "Initial vault sync"`
- [ ] Create private GitHub repo (e.g., `ai-employee-vault`)
- [ ] `git remote add origin git@github.com:YOUR_USER/ai-employee-vault.git`
- [ ] `git push -u origin main`
- [ ] Update `.env`: `VAULT_REMOTE_URL=git@github.com:YOUR_USER/ai-employee-vault.git`

---

## Phase 2: Two-Terminal Local Test (Verify Before Cloud)

### 2.1 Run Cloud Agent Locally
```bash
cd D:\prompteng\employee
set AGENT_ROLE=cloud
python cloud_orchestrator.py
```

### 2.2 Run Local Agent in Second Terminal
```bash
cd D:\prompteng\employee
set AGENT_ROLE=local
python local_orchestrator.py
```

### 2.3 Test the Flow
- [ ] Drop a test email task into `AI_Employee_Vault\Needs_Action\email\`
- [ ] Watch cloud agent claim it and create draft in `Pending_Approval\email\`
- [ ] Move the draft to `Approved\email\` (simulating human approval)
- [ ] Watch local agent execute it and move to `Done\email\`
- [ ] Check `Dashboard.md` for updates

### 2.4 Quick Demo (Single Terminal)
```bash
python run_demo.py
```
All 5 checks should pass.

---

## Phase 3: Odoo Setup (Docker)

- [ ] Install Docker Desktop (if not already)
- [ ] Follow `ODOO_NEXT_STEPS.md` step by step
- [ ] Start Odoo: `docker-compose up -d`
- [ ] Open http://localhost:8069, create database
- [ ] Install modules: Invoicing, Sales, Contacts
- [ ] Create test customer and product
- [ ] Update `.env` with Odoo credentials
- [ ] Test: `python mcp_servers/odoo_mcp.py` then `curl http://localhost:8005/health`

---

## Phase 4: Oracle Cloud VM Deployment

### 4.1 Create VM
- [ ] Sign up at https://cloud.oracle.com (free tier)
- [ ] Create VM: **VM.Standard.A1.Flex** (ARM, 2 vCPU, 4 GB RAM, 50 GB disk)
- [ ] Image: Ubuntu 22.04
- [ ] Add SSH key, note Public IP
- [ ] Open firewall ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)

### 4.2 Install Software on VM
- [ ] SSH into VM: `ssh -i ~/.ssh/your_key ubuntu@YOUR_IP`
- [ ] Run `deploy/setup_cloud.sh` or install Docker manually
- [ ] Clone code repo: `git clone git@github.com:YOUR_USER/ai-employee.git ~/ai-employee`
- [ ] Clone vault repo: `git clone git@github.com:YOUR_USER/ai-employee-vault.git ~/ai-employee/vault`

### 4.3 Configure
- [ ] `cp deploy/cloud.env.example deploy/cloud.env`
- [ ] Edit `cloud.env` with credentials (Gmail read-only, LinkedIn, Odoo, social APIs)
- [ ] **DO NOT add**: GMAIL_APP_PASSWORD, WHATSAPP_*, BANK_API_TOKEN

### 4.4 Deploy
- [ ] `docker-compose -f deploy/docker-compose.cloud.yml up -d`
- [ ] Verify: `curl http://localhost:9000/health`
- [ ] Set up Odoo on VM (follow ODOO_NEXT_STEPS.md)
- [ ] Verify all containers running: `docker ps`

Full details: see `CLOUD_VM_DEPLOYMENT.md`

---

## Phase 5: HTTPS + Domain (Optional)

- [ ] Buy a domain (~$12/year) or use free subdomain
- [ ] Point DNS A record to VM public IP
- [ ] Install certbot on VM
- [ ] Get Let's Encrypt certificate
- [ ] Update `deploy/nginx/nginx.conf` to enable HTTPS block
- [ ] Restart nginx

---

## Phase 6: Automated Backups

- [ ] `chmod +x ~/ai-employee/deploy/backup_odoo.sh`
- [ ] Add cron job: `0 2 * * * /home/ubuntu/ai-employee/deploy/backup_odoo.sh`
- [ ] Verify backup files appear in `~/backups/`

---

## Phase 7: Pending Fixes

### Twitter API Credits
- **Issue:** Free tier credits depleted (402 error)
- **Fix:** Wait for reset or upgrade to Basic tier ($100/month)
- **Impact:** Tweeting doesn't work, everything else does

### Facebook Token Refresh
- **Issue:** Graph API Explorer token expires
- **Fix:** Set up long-lived token via app review
- **Impact:** Facebook posting will stop when token expires

---

## Quick Reference

| What | Command |
|------|---------|
| Run demo | `python run_demo.py` |
| Run all tests | `python -m unittest discover tests/ -p "test_platinum_*.py"` |
| Start MCP servers (local) | `python start_mcp_servers.py` |
| Start MCP servers (cloud) | `python start_mcp_servers_cloud.py` |
| Cloud agent | `set AGENT_ROLE=cloud && python cloud_orchestrator.py` |
| Local agent | `set AGENT_ROLE=local && python local_orchestrator.py` |
| Start Odoo | `docker-compose up -d` (in deploy/ or project root) |
| Health check | `curl http://localhost:9000/health` |

---

**Start with Phase 1 (Git setup), then Phase 2 (local test). Cloud deployment can wait until local is verified.**
