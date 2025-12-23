# MongoDB Security Best Practices Guide

## Overview
This guide covers securing MongoDB credentials and implementing security best practices in your Kubernetes cluster.

---

## 1. Generate a Strong Password

Use one of these methods to generate a secure password:

### Option A: Using `openssl` (Recommended)
```bash
# Generate a 32-character random password
openssl rand -base64 32
# Example output: aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890+=

# Save to environment variable
MONGO_PASSWORD=$(openssl rand -base64 32)
echo "Generated password: $MONGO_PASSWORD"
```

### Option B: Using Python
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Option C: Using `pwgen`
```bash
# Install: sudo apt-get install pwgen
pwgen -s 32 1  # 32 character secure password
```

### ⚠️ Password Requirements
- ✅ Minimum 32 characters
- ✅ Mix of uppercase, lowercase, numbers, special characters
- ✅ No quotes or shell special characters: `"`, `'`, `$`, `` ` ``, `\`, `|`, `;`
- ⚠️ If password contains special characters, URL-encode them: [URL Encoder](https://www.urlencoder.org/)

---

## 2. Create Kubernetes Secret

### Step 1: Set Your Secure Password
```bash
# Generate new password
MONGO_PASSWORD=$(openssl rand -base64 32)
echo "Save this password securely: $MONGO_PASSWORD"

# Or use your own password
MONGO_PASSWORD="your_secure_password_here"
```

### Step 2: Create the Secret
```bash
# Create the secret in Kubernetes
kubectl create secret generic mongodb-secret \
  --from-literal=username=admin \
  --from-literal=password="$MONGO_PASSWORD" \
  --from-literal=url="mongodb://admin:$MONGO_PASSWORD@mongodb-service:27017" \
  --dry-run=client -o yaml | kubectl apply -f -

# Verify secret was created
kubectl get secret mongodb-secret
kubectl describe secret mongodb-secret
```

### Step 3: Verify Secret Content (Development Only)
```bash
# View secret (base64 encoded)
kubectl get secret mongodb-secret -o yaml

# Decode and view
kubectl get secret mongodb-secret -o jsonpath='{.data.password}' | base64 -d
```

---

## 3. Update Configuration Files

### MongoDB StatefulSet
The `mongodb_statefulset.yaml` already reads password from the secret:

```yaml
env:
- name: MONGO_INITDB_ROOT_USERNAME
  value: "admin"
- name: MONGO_INITDB_ROOT_PASSWORD
  valueFrom:
    secretKeyRef:
      name: mongodb-secret
      key: password
```

✅ **No changes needed** - It automatically uses the secret!

### Makefile (Update the secret creation)
```bash
# Edit your Makefile's start-spark-pods target:
start-spark-pods:
	# Create mongodb secret (use environment variable)
	kubectl create secret generic mongodb-secret \
	  --from-literal=username=admin \
	  --from-literal=password="$(MONGO_PASSWORD)" \
	  --from-literal=url="mongodb://admin:$(MONGO_PASSWORD)@mongodb-service:27017" \
	  --dry-run=client -o yaml | kubectl apply -f -
	...
```

Use it with:
```bash
make start-spark-pods MONGO_PASSWORD="your_secure_password"
```

---

## 4. Update Spark Job (spark_job.py)

**Option A: Read from Kubernetes Secret (Recommended for Production)**

Create a script to inject credentials:
```bash
#!/bin/bash
# save-credentials.sh

# Read secret from Kubernetes
PASSWORD=$(kubectl get secret mongodb-secret -o jsonpath='{.data.password}' | base64 -d)

# Create Python config file
cat > /tmp/mongo_config.py << EOF
MONGODB_URI = "mongodb://admin:$PASSWORD@mongodb-service:27017"
MONGODB_DB = "cybersecurity_db"
MONGODB_COLLECTION = "predictions"
EOF
```

Then in spark_job.py:
```python
import sys
sys.path.insert(0, '/tmp')
from mongo_config import MONGODB_URI, MONGODB_DB, MONGODB_COLLECTION

def write_to_mongodb(df, epoch_id):
    if df.count() > 0:
        try:
            client = MongoClient(MONGODB_URI)
            db = client[MONGODB_DB]
            collection = db[MONGODB_COLLECTION]
            # ... rest of function
```

**Option B: Read from Environment Variables**

```python
import os
from pymongo import MongoClient

MONGODB_USER = os.getenv("MONGO_USER", "admin")
MONGODB_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGODB_HOST = os.getenv("MONGO_HOST", "mongodb-service")
MONGODB_PORT = os.getenv("MONGO_PORT", "27017")
MONGODB_DB = os.getenv("MONGO_DB", "cybersecurity_db")

MONGODB_URI = f"mongodb://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_HOST}:{MONGODB_PORT}"

def write_to_mongodb(df, epoch_id):
    if df.count() > 0:
        try:
            client = MongoClient(MONGODB_URI)
            # ... rest of function
```

Then update Kubernetes manifests to inject environment variables from secret:
```yaml
env:
- name: MONGO_USER
  valueFrom:
    secretKeyRef:
      name: mongodb-secret
      key: username
- name: MONGO_PASSWORD
  valueFrom:
    secretKeyRef:
      name: mongodb-secret
      key: password
- name: MONGO_HOST
  value: "mongodb-service"
- name: MONGO_PORT
  value: "27017"
```

---

## 5. Network Security

### Enable Network Policies (Optional but Recommended)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mongodb-network-policy
spec:
  podSelector:
    matchLabels:
      app: mongodb
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: spark-client
    - podSelector:
        matchLabels:
          app: spark-worker
    ports:
    - protocol: TCP
      port: 27017
```

Apply it:
```bash
kubectl apply -f mongodb-network-policy.yaml
```

### Disable Direct Port Access
```bash
# ❌ DON'T expose MongoDB externally
# ❌ DON'T port-forward unnecessarily

# When debugging, use restricted port-forward
kubectl port-forward svc/mongodb-service 27017:27017
# Then connect only from localhost
```

---

## 6. RBAC (Role-Based Access Control)

### Create a MongoDB User (in-database)

```bash
# Connect to MongoDB
kubectl exec -it mongodb-0 -- mongosh \
  "mongodb://admin:$MONGO_PASSWORD@localhost:27017"

# Create application user with minimal privileges
db = db.getSiblingDB('admin')
db.createUser({
  user: "spark-user",
  pwd: "spark_user_password_123",
  roles: [
    { role: "readWrite", db: "cybersecurity_db" }
  ]
})

# Verify
db.getUser("spark-user")
```

Update spark_job.py to use this user:
```python
MONGODB_URI = "mongodb://spark-user:spark_user_password_123@mongodb-service:27017"
```

---

## 7. Data Encryption

### Enable Encryption at Rest (Enterprise Only)
MongoDB Community Edition doesn't support encryption at rest.

For development: Ensure disk is encrypted at host level (LUKS on Linux).

### Enable TLS/SSL (Advanced)

For production, enable TLS:

```bash
# Generate self-signed certificate
openssl req -newkey rsa:2048 -new -x509 -days 365 -nodes \
  -out mongodb.pem -keyout mongodb.pem

# Create Kubernetes secret
kubectl create secret tls mongodb-tls \
  --cert=mongodb.pem \
  --key=mongodb.pem
```

---

## 8. Backup & Disaster Recovery

### Backup Before Password Change
```bash
# Backup current database
kubectl exec mongodb-0 -- mongodump \
  --uri="mongodb://admin:$OLD_PASSWORD@localhost:27017/cybersecurity_db" \
  --out=/data/db/backup_$(date +%Y%m%d_%H%M%S)
```

### Backup Strategy
```bash
# Daily automated backup
kubectl exec mongodb-0 -- mongodump \
  --uri="mongodb://admin:$MONGO_PASSWORD@localhost:27017" \
  --out=/data/db/backups/daily_$(date +%Y%m%d)
```

---

## 9. Monitoring & Auditing

### Enable Audit Logging
```yaml
# In mongodb_statefulset.yaml
- name: MONGO_INITDB_ROOT_USERNAME
  value: "admin"
- name: MONGO_INITDB_ROOT_PASSWORD
  valueFrom:
    secretKeyRef:
      name: mongodb-secret
      key: password
# Add audit logging command (Enterprise feature)
```

### Monitor Failed Login Attempts
```bash
# Check MongoDB logs for auth failures
kubectl logs mongodb-0 | grep -i "auth\|failed"
```

---

## 10. Regular Security Maintenance

### Rotation Schedule
- **Passwords**: Every 90 days (or sooner if compromised)
- **TLS Certificates**: Annually
- **Keys**: When team members leave

### Password Rotation Procedure
```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Update MongoDB user
kubectl exec mongodb-0 -- mongosh \
  "mongodb://admin:$OLD_PASSWORD@localhost:27017" \
  --eval "db.changeUserPassword('admin', '$NEW_PASSWORD')"

# 3. Update Kubernetes secret
kubectl delete secret mongodb-secret
kubectl create secret generic mongodb-secret \
  --from-literal=username=admin \
  --from-literal=password="$NEW_PASSWORD" \
  --from-literal=url="mongodb://admin:$NEW_PASSWORD@mongodb-service:27017"

# 4. Update Spark pods (restart to pick up new secret)
kubectl rollout restart statefulset/spark-client
kubectl rollout restart deployment/spark-worker

# 5. Verify connectivity
kubectl logs spark-client-0 | grep -i "connected\|error"
```

---

## 11. Secrets Management (Production)

### Use HashiCorp Vault or AWS Secrets Manager

```bash
# Install Vault
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  -n vault --create-namespace

# Store MongoDB password in Vault
vault kv put secret/mongodb \
  password="$MONGO_PASSWORD"

# Reference in K8s manifests using Vault agent
```

### Use External Secrets Operator (ESO)

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: mongodb-secret-store
spec:
  provider:
    vault:
      server: "http://vault:8200"
      path: "secret"
```

---

## 12. Compliance Checklist

- [ ] Password is 32+ characters with mixed case and special characters
- [ ] Password never logged or committed to git
- [ ] Secret stored in Kubernetes Secret (not in ConfigMap)
- [ ] Secret uses `stringData` (not base64 in YAML)
- [ ] Network policy restricts MongoDB access
- [ ] MongoDB user created with limited privileges
- [ ] TLS enabled for production (if applicable)
- [ ] Audit logging enabled
- [ ] Regular backups scheduled
- [ ] Password rotation schedule established
- [ ] Team members briefed on security practices
- [ ] `.gitignore` includes `*.pem`, `secrets/`, `config/`

---

## Quick Start: Immediate Action Items

1. **Generate password immediately:**
   ```bash
   MONGO_PASSWORD=$(openssl rand -base64 32)
   echo "Save this: $MONGO_PASSWORD"
   ```

2. **Delete existing insecure secret:**
   ```bash
   kubectl delete secret mongodb-secret
   ```

3. **Create new secure secret:**
   ```bash
   kubectl create secret generic mongodb-secret \
     --from-literal=username=admin \
     --from-literal=password="$MONGO_PASSWORD" \
     --from-literal=url="mongodb://admin:$MONGO_PASSWORD@mongodb-service:27017" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

4. **Restart MongoDB pod:**
   ```bash
   kubectl delete pod mongodb-0
   # Wait for it to restart and pick up new password
   kubectl wait --for=condition=ready pod mongodb-0 --timeout=60s
   ```

5. **Test connection:**
   ```bash
   kubectl exec -it mongodb-0 -- mongosh \
     "mongodb://admin:$MONGO_PASSWORD@localhost:27017"
   ```

---

## Troubleshooting

### Connection Refused After Password Change
```bash
# Check if pod restarted with new secret
kubectl describe pod mongodb-0 | grep "mongodb-secret"

# View actual password in use
kubectl exec mongodb-0 -- env | grep MONGO
```

### Authentication Failed
```bash
# Verify secret exists
kubectl get secret mongodb-secret -o yaml

# Check Spark pod has access to secret
kubectl describe pod spark-client-0 | grep mongodb-secret

# View MongoDB logs for auth errors
kubectl logs mongodb-0 | tail -50
```

### Secret Not Updated in Running Pods
```bash
# Kubernetes doesn't automatically reload secrets
# You must restart the pod
kubectl rollout restart statefulset/mongodb
kubectl rollout restart statefulset/spark-client
kubectl rollout restart deployment/spark-worker
```

---

## References
- [MongoDB Security Checklist](https://docs.mongodb.com/manual/administration/security-checklist/)
- [Kubernetes Secrets Best Practices](https://kubernetes.io/docs/concepts/configuration/secret/#best-practices)
- [OWASP Password Guidelines](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
