import os, json, time
import pandas as pd
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import numpy as np

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
BASE_RATE = int(os.getenv("MSG_RATE"))
BURST_PROB = float(os.getenv("BURST_PROB"))
BURST_POWER = float(os.getenv("BURST_POWER"))

print("="*10)
print("env vars: ")
print(f"BOOTSTRAP={BOOTSTRAP}")
print(f"TOPIC={TOPIC}")
print(f"DATASET_DIR={DATASET_DIR}")


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
        print(f"Delivery failed: {err}")
    #else:
    #    print(f"{msg.topic()}[{msg.partition()}] offset={msg.offset()}")

# ---------- Utilitaires ----------
def topic_exists(broker_address, topic_name):
    """
    Returns True si topic exist, False sinon.
    """
    client = AdminClient({'bootstrap.servers': broker_address})
    metadata = client.list_topics(timeout=10)
    
    return topic_name in metadata.topics

def get_log_rate_steady(base_rate, burst_prob=0.05, burst_power=3.0):
    """
    Calculates a specific target count for the current second 
    using Poisson (noise) + Pareto (bursts).
    """
    current_lambda = base_rate
    
    # 1. Burst Check (Pareto)
    if np.random.random() < burst_prob:
        multiplier = (np.random.pareto(a=burst_power) + 1) * 2
        current_lambda = base_rate * multiplier

    # 2. Natural Variance (Poisson)
    final_count = np.random.poisson(current_lambda)
    return int(final_count)
 
def send_row_as_json(topic: str, row: pd.Series):
    try:
        payload = row.to_dict()
        p.produce(topic=topic, value=json.dumps(payload).encode("utf-8"), on_delivery=on_delivery)
        # vidage de la file d’événements internes (callbacks)
        p.poll(0)
    except Exception as e:
        print(f"Erreur lors produce() à kafka: {e}")

# ---------- Main ----------
if __name__ == "__main__":
    # (1) verifier l'existence du topic
    if topic_exists(BOOTSTRAP, TOPIC):
        print("Topic trouve!")
    else:
        print("Topic n'existe pas.")
        raise Exception(f"Topic {TOPIC} n'existe pas dans le broker {BOOTSTRAP}.")

    ml_dataset = ['id', 'dur', 'proto', 'service', 'state', 'spkts', 'dpkts', 'sbytes',
       'dbytes', 'rate', 'sttl', 'dttl', 'sload', 'dload', 'sloss', 'dloss',
       'sinpkt', 'dinpkt', 'sjit', 'djit', 'swin', 'stcpb', 'dtcpb', 'dwin',
       'tcprtt', 'synack', 'ackdat', 'smean', 'dmean', 'trans_depth',
       'response_body_len', 'ct_srv_src', 'ct_state_ttl', 'ct_dst_ltm',
       'ct_src_dport_ltm', 'ct_dst_sport_ltm', 'ct_dst_src_ltm',
       'is_ftp_login', 'ct_ftp_cmd', 'ct_flw_http_mthd', 'ct_src_ltm',
       'ct_srv_dst', 'is_sm_ips_ports', 'attack_cat', 'label']

    # (2) Charger les noms de colonnes
    features_pd = pd.read_csv(FEATURES_FILE, encoding="utf-8", encoding_errors="ignore")
    feature_names = features_pd["Name"].tolist()
    feature_names = [name.lower() for name in feature_names]

    try:
        file_idx = 0
        total_rows_sent = 0

        current_second_target = get_log_rate_steady(BASE_RATE, burst_prob=BURST_PROB, burst_power=BURST_POWER)
        logs_in_current_second = 0
        second_start_time = time.time()
        while True:
            csv_path = CSV_FILES[file_idx]
            print(f" Lecture: {csv_path}")
            # Les fichiers UNSW n’ont pas d’en-tête → header=None puis on applique les colonnes
            for chunk in pd.read_csv(csv_path, header=None, chunksize=1000, low_memory=False):
                df = chunk.copy()
                df.columns = feature_names

                # mini preprocessing
                feature_names = [name.replace('sintpkt', 'sinpkt').replace('dintpkt', 'dinpkt').replace('smeansz', 'smean').replace('dmeansz', 'dmean').replace('res_bdy_len', 'response_body_len') for name in feature_names]
                df.columns = feature_names
                df['rate'] = np.nan
                df = df.reindex(columns=ml_dataset, fill_value=0)
                df = df.drop(columns=["attack_cat", "label", "id"]) 

                for i, row in df.iterrows():
                    send_row_as_json(TOPIC, row)

                    logs_in_current_second += 1
                    total_rows_sent += 1

                    # Check if we reached the target for THIS specific second
                    if logs_in_current_second >= current_second_target:
                        elapsed = time.time() - second_start_time
                        
                        # If we finished fast, sleep the remainder of the second
                        if elapsed < 1.0:
                            time.sleep(1.0 - elapsed)
                        
                        # Logging for visibility
                        is_spike = current_second_target > (BASE_RATE * 1.5)
                        status = " [!!! SPIKE]" if is_spike else ""
                        print(f"Sec complete. Sent: {logs_in_current_second}/{current_second_target} | Total: {total_rows_sent}{status}")

                        # Reset logic for the NEXT second
                        logs_in_current_second = 0
                        second_start_time = time.time()
                        current_second_target = get_log_rate_steady(BASE_RATE, burst_prob=BURST_PROB, burst_power=BURST_POWER)

            file_idx = (file_idx + 1) % len(CSV_FILES)

    except KeyboardInterrupt:
        print(" Arrêt demandé.")
    except Exception as e:
        print(f"Erreur dans main: {e}")
    finally:
        print(" Vidage des messages en attente…")
        p.flush(30)
        print(" Terminé.")
