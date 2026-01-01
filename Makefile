
# this makefile may not work on Windows
# execute in this order to start the full pipeline:

start_minikube:
	minikube start --driver=docker --memory=4096 --cpus=2

# make take a while to download the images and start the pods
start_kafka:
	kubectl apply -f apache_kafka/kafka_broker_statefulset.yaml
	kubectl apply -f apache_kafka/kafka_controller_statefulset.yaml

# make take a while to download the images and start the pods
start_spark_pods:
	# the base image for all spark pods is built from spark_k8/Dockerfile
	# i have built and pushed the image to my public docker hub asghcr.io/giangnguyen2007/myspark:v3
	kubectl apply -f spark_k8/spark_master_deployment.yaml
	kubectl apply -f spark_k8/spark_worker_deployment.yaml
	kubectl apply -f spark_k8/spark_client_statefulset.yaml
	echo "Waiting for Spark master..."
	kubectl rollout status deployment/spark-master --timeout=300s
	echo "Waiting for Spark workers..."
	kubectl rollout status deployment/spark-worker --timeout=300s
	echo "Waiting for Spark client..."
	kubectl rollout status statefulset/spark-client --timeout=300s
	echo "All Spark pods are running."




start_python_producer:
	kubectl apply -f python_producer/producer_pod.yaml

launch_producer:
	#copy the producer.py into the producer pod
	kubectl cp python_producer/producer.py python-producer:/producer.py
	#execute the producer.py inside the producer pod
	# script download CSV data from internet and produce messages to Kafka topic
	# keep it running to continuously produce messages to Kafka
	kubectl exec -it python-producer -- python3 /producer.py

submit_spark_job:
	#copy the spark_job.py into the spark-client pod
	kubectl cp spark_code/spark_job.py spark-client-0:/opt/spark/work-dir/spark_job.py

	#copy the models folder into the spark-client pod
	# no longer necessary as the model is copied inside the docker image
	#kubectl cp spark_code/models/ spark-client-0:/opt/spark/work-dir/models/

	kubectl cp spark_code/spark_submit.sh spark-client-0:/opt/spark/work-dir/spark_submit.sh

	#execute the spark_job.py inside the spark-client pod
	#may take a while to execute (download dependencies, connect to master, dag scheduling, etc)
	# it will process new message as they arrive in Kafka topic
	# if no more message, it will just wait for new messages
	kubectl exec -it spark-client-0 -- /bin/bash /opt/spark/work-dir/spark_submit.sh


stop-minikube:
	minikube stop

restart-minikube:
	minikube delete

delete-resources:
	kubectl delete all --all


# check current running pods
check:
	kubectl get pods


delete_spark_pods:
	kubectl delete -f spark_k8/spark_master_deployment.yaml
	kubectl delete -f spark_k8/spark_worker_deployment.yaml
	kubectl delete -f spark_k8/spark_client_statefulset.yaml

exec_spark_client:
	kubectl exec -it spark-client-0 -- /bin/bash
