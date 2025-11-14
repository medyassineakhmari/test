# ====== Variables ======
NS ?= default
K  := minikube kubectl --  -n $(NS)

KAFKA_DIR   := apache_kafka
SPARK_DIR   := spark
PRODUCER_DIR:= python_producer

.PHONY: start-minikube start-kafka start-spark-pods start_python_producer \
        launch_producer submit_spark_job status pf-master pf-driver stop-minikube \
        delete-resources nuke

# ------- Cluster -------
start-minikube:
	minikube start --driver=docker --memory=4096 --cpus=2
	# (optionnel mais utile pour les PVC dynamiques)
	minikube addons enable storage-provisioner || true
	minikube addons enable default-storageclass || true
	minikube addons enable metrics-server || true

# ------- Kafka (contrôleurs -> brokers) -------
start-kafka:
	$(K) apply -f $(KAFKA_DIR)/kafka_controller_statefulset.yaml
	$(K) wait --for=condition=ready pod -l app=kafka-controller --timeout=300s
	$(K) apply -f $(KAFKA_DIR)/kafka_broker_statefulset.yaml
	$(K) wait --for=condition=ready pod -l app=kafka-broker --timeout=300s

# ------- Spark (master -> workers -> client) -------
start-spark-pods:
	$(K) apply -f $(SPARK_DIR)/spark_master_deployment.yaml
	$(K) rollout status deploy/spark-master --timeout=180s
	$(K) apply -f $(SPARK_DIR)/spark_worker_deployment.yaml
	$(K) rollout status deploy/spark-worker --timeout=300s
	$(K) apply -f $(SPARK_DIR)/spark_client_statefulset.yaml
	$(K) wait --for=condition=ready pod -l app=spark-client --timeout=180s

# ------- Producteur Python -------
start_python_producer:
	$(K) apply -f $(PRODUCER_DIR)/producer_pod.yaml
	$(K) wait --for=condition=ready pod/python-producer --timeout=180s

launch_producer:
	# copie le script et lance en interactif
	minikube kubectl -- -n $(NS) cp $(PRODUCER_DIR)/producer.py python-producer:/producer.py
	$(K) exec -it python-producer -- python3 /producer.py

# ------- Job Spark -------
submit_spark_job:
	# copie le job et le script de submit dans le pod client
	minikube kubectl -- -n $(NS) cp $(SPARK_DIR)/spark_job.py spark-client-0:/opt/spark/work-dir/spark_job.py
	minikube kubectl -- -n $(NS) cp $(SPARK_DIR)/model_utils.py spark-client-0:/opt/spark/work-dir/model_utils.py
	minikube kubectl -- -n $(NS) cp $(SPARK_DIR)/pretrained_models/ spark-client-0:/opt/spark/work-dir/pretrained_models/

	minikube kubectl -- -n $(NS) cp $(SPARK_DIR)/spark_submit.sh spark-client-0:/opt/spark/work-dir/spark_submit.sh
	# lance le job (peut prendre du temps la 1ère fois : téléchargement des packages)
	$(K) exec -it spark-client-0 -- /bin/bash /opt/spark/work-dir/spark_submit.sh


# ------- Aides -------
status:
	@echo "== Pods ==" && $(K) get pods -o wide
	@echo "== PVC =="  && $(K) get pvc
	@echo "== Services ==" && $(K) get svc

pf-master:
	# UI Master sur http://localhost:8080
	minikube kubectl -- -n $(NS) port-forward svc/spark-master-service 8080:8080

pf-driver:
	# UI Driver sur http://localhost:4040
	minikube kubectl -- -n $(NS) port-forward pod/spark-client-0 4040:4040

# ------- Stop/Clean -------
stop-minikube:
	minikube stop

# Supprime ce que tu as créé via apply (propre)
delete-resources:
	-$(K) delete -f $(KAFKA_DIR)/kafka_broker_statefulset.yaml
	-$(K) delete -f $(KAFKA_DIR)/kafka_controller_statefulset.yaml
	-$(K) delete -f $(SPARK_DIR)/spark_client_statefulset.yaml
	-$(K) delete -f $(SPARK_DIR)/spark_worker_deployment.yaml
	-$(K) delete -f $(SPARK_DIR)/spark_master_deployment.yaml
	-$(K) delete -f $(PRODUCER_DIR)/producer_pod.yaml

# GROS reset (attention: détruit aussi les PVC)
nuke:
	-minikube kubectl -- -n $(NS) delete all --all
	-minikube kubectl -- -n $(NS) delete pvc --all
