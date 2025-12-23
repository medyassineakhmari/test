# MongoDB Integration for Cybersecurity Predictions

## Overview

MongoDB stores all predictions made by the Spark ML pipeline in a structured document format. This enables:
- ✅ Persistent storage of predictions
- ✅ Easy querying and analysis of attack patterns
- ✅ Alerting on high-confidence attacks
- ✅ Audit trail of detections

---

## Architecture

```
Kafka Messages
     ↓
Spark Job
     ↓
ML Predictions
     ↓
MongoDB Document Storage
     ↓
Query & Analysis Tools
```

---

## Deployment

### 1. Start MongoDB

```bash
# From project root
kubectl apply -f mongodb/mongodb_statefulset.yaml
```

This creates:
- **StatefulSet**: MongoDB with persistent storage (5GB)
- **Service**: `mongodb-service` on port 27017
- **Secret**: Credentials (`admin:mongodb_password_123`)
- **ConfigMap**: Database schema initialization

### 2. Verify MongoDB is running

```bash
kubectl get pods | grep mongodb
kubectl logs mongodb-0

# Test connection
kubectl run -it --rm mongo-test --image=mongo:7.0 --restart=Never -- \
  mongosh mongodb://admin:mongodb_password_123@mongodb-service:27017/cybersecurity_db
```

---

## Document Schema

Each prediction is stored as a MongoDB document with strict schema validation:

```json
{
  "_id": ObjectId("..."),
  "attack_type": "Normal",         // Attack category: Normal, Fuzzers, Exploits, Reconnaissance, or Backdoors
  "prediction": 0,                 // Numeric prediction (0-4)
  "confidence": 0.96,              // Probability [0-1] (stored as Double, required)
  "timestamp": ISODate("2025-12-23T14:30:00Z"),  // When inserted (required, ISODate)
  "proto": "tcp",
  "state": "ACC",
  "service": "https",
  "duration": 2.5,
  "source_bytes": 1200,
  "dest_bytes": 4500,
  "source_packets": 15,
  "dest_packets": 12,
  "source_load": 45.2,
  "dest_load": 32.1,
  "source_loss": 0,
  "dest_loss": 0,
  "source_ttl": 64,
  "dest_ttl": 128,
  "sink_tcpflags": 5,
  "source_tcpflags": 27,
  "rate": 1.5,
  "stime": "2025-12-23T14:29:58Z",
  "ltime": "2025-12-23T14:30:00Z",
  "is_sm_ips_ports": 0,
  "is_sm_ips_bytes": 0
}
```

**Attack Type Mapping:**
- `0` = Normal
- `1` = Fuzzers
- `2` = Exploits
- `3` = Reconnaissance
- `4` = Backdoors

### Schema Validation
MongoDB enforces schema validation via ConfigMap. Required fields:
- `confidence` - Must be numeric (Double)
- `timestamp` - Must be ISODate

### Indexes (for fast queries)
- `attack_type`: Query by attack type
- `timestamp`: Query by time range
- `confidence`: Sort by confidence level

---

## Querying Predictions

### Using MongoDB Shell (Recommended)

```bash
# Port forward to access MongoDB locally
kubectl port-forward svc/mongodb-service 27017:27017 &

# Connect with mongosh
mongosh mongodb://admin:mongodb_password_123@localhost:27017/cybersecurity_db

# Example queries:

# Total predictions count
db.predictions.countDocuments({})

# Count by attack type
db.predictions.aggregate([
  { $group: { _id: "$attack_type", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])

# High-confidence predictions (>0.9)
db.predictions.find({ "confidence": { $gte: 0.9 } }).count()

# Recent predictions (last 1 hour)
db.predictions.find({ 
  "timestamp": { $gte: new Date(new Date() - 3600000) } 
}).count()

# Exploits detected
db.predictions.find({ "attack_type": "Exploits" }).limit(5)
```

### Using Kubernetes Directly

```bash
# Query without local port-forward
kubectl exec mongodb-0 -- mongosh \
  "mongodb://admin:mongodb_password_123@localhost:27017/cybersecurity_db" \
  --eval "db.predictions.countDocuments({})"

# Get attack distribution
kubectl exec mongodb-0 -- mongosh \
  "mongodb://admin:mongodb_password_123@localhost:27017/cybersecurity_db" \
  --eval "db.predictions.aggregate([{ \$group: { _id: '\$attack_type', count: { \$sum: 1 } } }, { \$sort: { count: -1 } }])"
```

---

## Alerts Collection

Currently not implemented. The system focuses on storing raw predictions for analysis.

---

## Performance Considerations

| Metric | Value |
|--------|-------|
| Storage per prediction | ~1-2KB (JSON document) |
| Batch write frequency | Every 10-30 seconds (micro-batch) |
| Records per batch | 5,000-50,000+ |
| Processing rate | 6,000+ rows/second |
| Query latency (indexed) | <10ms |
| PVC size | 5GB (expandable) |
| Connection | PyMongo via `mongodb-service:27017` |

**Tested Metrics (Production Run):**
- Batch 0: 304,456 records in ~50 seconds (6,088 rows/sec)
- Batch 1: 5,673 records in ~18 seconds (313 rows/sec)
- Total stored: 163,166+ documents (verified)

**Retention policy**: Documents kept indefinitely (recommend archiving old data quarterly)

---

## Troubleshooting

### MongoDB pod not starting
```bash
kubectl describe pod mongodb-0
kubectl logs mongodb-0

# Check PVC
kubectl get pvc
```

### Connection failed
```bash
# Verify secret exists
kubectl get secret mongodb-secret

# Verify service DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup mongodb-service
```

### High memory usage
- Reduce PVC size or add TTL index
- Archive old documents to separate collection
- Increase memory limits in manifest

---

## Updating Credentials (Production)

⚠️ **Change default password!**

1. Edit `mongodb/mongodb_statefulset.yaml`
2. Update the secret:
```bash
kubectl create secret generic mongodb-secret \
  --from-literal=username=admin \
  --from-literal=password=YOUR_SECURE_PASSWORD \
  --from-literal=url=mongodb://admin:YOUR_SECURE_PASSWORD@mongodb-service:27017 \
  --dry-run=client -o yaml | kubectl apply -f -
```

3. Restart MongoDB pod:
```bash
kubectl delete pod mongodb-0
```

---

## Backup & Restore

### Backup
```bash
kubectl exec -it mongodb-0 -- mongodump \
  --uri="mongodb://admin:mongodb_password_123@localhost:27017/cybersecurity_db" \
  --out=/data/db/backup
```

### Restore
```bash
kubectl exec -it mongodb-0 -- mongorestore \
  --uri="mongodb://admin:mongodb_password_123@localhost:27017/cybersecurity_db" \
  /data/db/backup/cybersecurity_db
```

---

## Integration with Spark

The Spark job (`spark_code/spark_job.py`) automatically writes predictions to MongoDB using **PyMongo** via the `foreachBatch` callback.

### How it works:
1. Spark Structured Streaming reads from Kafka topic "demo"
2. ML pipeline (Random Forest) makes predictions on 43 network features
3. Predictions are formatted with proper data types:
   - `confidence`: Extracted from Spark ML Vector as Double (required)
   - `timestamp`: Converted from string to MongoDB ISODate (required)
   - `attack_type`: Mapped from numeric prediction (0-4) to string label
4. PyMongo batch inserts records to `cybersecurity_db.predictions`

### Key Functions in spark_job.py:

```python
def write_to_mongodb(df, epoch_id):
    """Write batch of predictions to MongoDB"""
    if df.count() > 0:
        client = MongoClient("mongodb://admin:mongodb_password_123@mongodb-service:27017/")
        db = client["cybersecurity_db"]
        collection = db["predictions"]
        
        records = df.toJSON().map(lambda x: eval(x)).collect()
        
        # Extract confidence from Spark ML Vector
        for record in records:
            if isinstance(record.get('confidence'), dict) and 'values' in record['confidence']:
                confidence_list = record['confidence']['values']
                record['confidence'] = float(max(confidence_list)) if confidence_list else 0.0
            
            # Convert timestamp to datetime
            if isinstance(record.get('timestamp'), str):
                from dateutil import parser
                record['timestamp'] = parser.parse(record['timestamp'])
        
        if records:
            collection.insert_many(records)
            print(f"Batch {epoch_id}: {len(records)} records written")
```

### Connection Details:
- **URI**: `mongodb://admin:mongodb_password_123@mongodb-service:27017`
- **Database**: `cybersecurity_db`
- **Collection**: `predictions`
- **Driver**: PyMongo 4.x (pre-installed in spark-base Docker image)
- **Batch Mode**: `foreachBatch` callback (automatic per micro-batch)
