import os, json, time
import pandas as pd
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

# ---------- Paramètres ----------
BOOTSTRAP = os.getenv(
    "BOOTSTRAP_SERVERS",
    "kafka-broker-0.kafka-broker-service:19092,"
    "kafka-broker-1.kafka-broker-service:19092,"
    "kafka-broker-2.kafka-broker-service:19092"
)
TOPIC = os.getenv("TOPIC", "demo")
DATASET_DIR = os.getenv("DATASET_DIR", "./events_logs_dataset")
FEATURES_FILE = os.path.join(DATASET_DIR, "NUSW-NB15_features.csv")  # <== CORRIGÉ (UNSW)
CSV_FILES = [
    os.path.join(DATASET_DIR, "UNSW-NB15_1.csv"),
    os.path.join(DATASET_DIR, "UNSW-NB15_2.csv"),
    os.path.join(DATASET_DIR, "UNSW-NB15_3.csv"),
    os.path.join(DATASET_DIR, "UNSW-NB15_4.csv"),
]

# ---------- Producer ----------
producer_conf = {
    "bootstrap.servers": BOOTSTRAP,
    "enable.idempotence": True,   # acks=all, retries & in-flight sécurisés
    "acks": "all",
    "compression.type": "lz4",    # ou "snappy"
    "linger.ms": 20,              # petit batching
    "batch.num.messages": 10000,
    "socket.timeout.ms": 30000,
    "message.timeout.ms": 120000,
}
p = Producer(producer_conf)

def on_delivery(err, msg):
    if err:
        print(f"❌ Delivery failed: {err}")
    else:
        print(f"✅ {msg.topic()}[{msg.partition()}] offset={msg.offset()}")

# ---------- Utilitaires ----------
def ensure_topic(admin: AdminClient, topic: str, partitions=6, rf=3):
    """Crée le topic s’il n’existe pas (RF=3 pour 3 brokers)."""
    md = admin.list_topics(timeout=10)
    if topic in md.topics and not md.topics[topic].error:
        return
    fs = admin.create_topics([NewTopic(topic, num_partitions=partitions, replication_factor=rf)])
    # attendre le résultat proprement (ignore si déjà créé en parallèle)
    try:
        fs[topic].result()
        print(f"ℹ️ Topic '{topic}' créé (partitions={partitions}, RF={rf}).")
    except Exception as e:
        if "Topic already exists" in str(e):
            print(f"ℹ️ Topic '{topic}' existe déjà.")
        else:
            raise

def send_row_as_json(topic: str, row: pd.Series):
    payload = row.to_dict()
    p.produce(topic=topic, value=json.dumps(payload).encode("utf-8"), on_delivery=on_delivery)
    # vidage de la file d’événements internes (callbacks)
    p.poll(0)

# ---------- Main ----------
if __name__ == "__main__":
    # (1) Vérifier / créer le topic
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})
    ensure_topic(admin, TOPIC, partitions=6, rf=3)

    # (2) Charger les noms de colonnes
    features_pd = pd.read_csv(FEATURES_FILE, encoding="utf-8", encoding_errors="ignore")
    feature_names = features_pd["Name"].tolist()

    try:
        file_idx = 0
        while True:
            csv_path = CSV_FILES[file_idx]
            print(f"➡️ Lecture: {csv_path}")
            # Les fichiers UNSW n’ont pas d’en-tête → header=None puis on applique les colonnes
            for chunk in pd.read_csv(csv_path, header=None, chunksize=1000, low_memory=False):
                df = chunk.copy()
                df.columns = feature_names

                # Optionnel: ignorer les colonnes label/attaque si tu ne veux que des features
                if "attack_cat" in df.columns: df = df.drop(columns=["attack_cat"])
                if "Label" in df.columns: df = df.drop(columns=["Label"])

                for i, row in df.iterrows():
                    send_row_as_json(TOPIC, row)
                    if i % 10 == 0:
                        time.sleep(1)  # petit throttle toutes les 10 lignes

            file_idx = (file_idx + 1) % len(CSV_FILES)

    except KeyboardInterrupt:
        print("🛑 Arrêt demandé.")
    finally:
        print("⏳ Vidage des messages en attente…")
        p.flush(30)
        print("✅ Terminé.")
