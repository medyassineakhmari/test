
import os, json, time
import pandas as pd

import numpy as np
import subprocess

# ---------- Paramètres ----------



# adjust the path to your CSV files directory
DATASET_DIR = "../../CSV_Files"
FEATURES_FILE = os.path.join(DATASET_DIR, "NUSW-NB15_features.csv")  # <== CORRIGÉ (UNSW)

CSV_FILES = [
    os.path.join(DATASET_DIR, "UNSW-NB15_1.csv"),
    os.path.join(DATASET_DIR, "UNSW-NB15_2.csv"),
    os.path.join(DATASET_DIR, "UNSW-NB15_3.csv"),
    os.path.join(DATASET_DIR, "UNSW-NB15_4.csv"),
]


# ---------- Main ----------
if __name__ == "__main__":
    # (1) Vérifier / créer le topic

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


    csv_path = CSV_FILES[0]
    print(f" Lecture: {csv_path}")
    # Les fichiers UNSW n’ont pas d’en-tête → header=None puis on applique les colonnes
    df = pd.read_csv(csv_path, nrows=2000, header=None, low_memory=False)
    df.columns = feature_names

    # mini preprocessing
    feature_names = [name.replace('sintpkt', 'sinpkt').replace('dintpkt', 'dinpkt').replace('smeansz', 'smean').replace(
            'dmeansz', 'dmean').replace('res_bdy_len', 'response_body_len') for name in feature_names]
    df.columns = feature_names
    df['rate'] = np.nan
    df = df.reindex(columns=ml_dataset, fill_value=0)
    df = df.drop(columns=["attack_cat", "label", "id"])

    print(df.head(10))

    df.to_csv("mini_sample.csv", index=False)


