# Projet Systeme Distribué Pour le Traitement des Données
Le thème de projet : **Détection d’attaques de cybersécurité en temps réel** 

## Lancement de projet en local sur Minikube
en utilisant le makefile en execute les étapes suivantes:
1. lancer minikube :
```
make start-minikube
```
> si vous avez deja une contenaire minikube deja initié, il est recommandé de supprimer le container et le recrée pour n'avoir plus des problème vers la suite à cause des difference entre les version de projet.

2. lancer les pods de kafka:
```
make start-kafka
```

3. lancer les pods de spark:
```
make start-spark-pods
```
> Note: Il se peut que certain pods ne se lance plus et reste bloquer dans la phase de creation. Vous pouvez toujours verifier ça avec `make status` et trouver le pods avec status `ContainerCreating`. Puis le supprimer en utilisant `Kubectl delete -f spark_k8/spark_client_statefulset.yaml` par exemple. Enfin relancer le make command associé.

4. lancer le pod de producer :
```
make start-python-producer
```
> Note: Maintenant juste avec cette command le pod de producer est crée puis lancé directement et il commence le streaming des données vers Kafka.

5. lancer les pods de spark:
```
make submit-spark-job
```
> Note: il se peut qu'un erreur se produit qui est en relation avec le fichier spark_submit.sh. sur VScode en ouvrant se fichier, assurer que le fichier est en encodage LF et pas CRLF (verifier sur la barre de vscode au dessous à droite).

> Note: vous pouvez à chaque étape verifier le status de tous le cluster en utilisant : 
```
make status
```
Vous pouvez voir le status des pods , les PVC et les services.

6. lancer le monitoring de prometheus: 
```
make setup-monitoring
```
> ATTENTION: il faut vérifier si vous avez `helm` installé sur votre système ou pas.

Si vous sur windows ou linux, installer suivant ce guide: [helm.sh](https://helm.sh/docs/intro/install/#from-apt-debianubuntu)

7. acceder l'interface de monitoring de Grafana: 
```
make access-grafana
```

## Suppression des elements de cluster
1. Si vous vouler supprimer juste les pods:
```
make delete-resources
```

2. Si vous voulez supprimer tous (pods, PVCs, services)
```
make nuke
```

## Les éléments existant de Cluster
### Producer: 
- Deployement:
    - une seul replica
    - utilise l'image docker ``rabii10/python_producer:v4.2.2`` (contient l'app python et les données de dataset)
- configuration possible depuis ``producer_deployment.yaml`` :
    - ``BOOTSTRAP_SERVERS`` (pour se connecter à kafka quelque soit le nombre des brokers de kafka)
    - ``TOPIC`` (le nom de topic de kafka)
    - ``MSG_RATE`` (le taux des lignes de dataset à envoyer par seconde)
    - ``BURST_PROB`` (la Probabilité d'avoir des pics de taux des messages envoy", pour simuler un système réel avec des variation soudaine de taux des logs reçus par kafka)
    - ``BURST_POWER`` (la puissance de ces augmentations soudaine de taux des logs envoyé, une valeur plus petit > des pics de MSG_RATE plus massives avec valeur minimum de 1.1)
> Note: si votre système crash à cause des gros volume des message, réduire le MSG_RATE à 5 ou 10.

### Kafka:
#### Brokers
- Statefulset
    - replica : 3
    - utilise l'image : ``apache/kafka:3.8.0``
    - PVC de 1Gi pour chaque broker
- Service
    - pas d'IP externe

#### Controllers 
- Statefulset
    - replica : 3
    - utilise l'image : ``apache/kafka:3.8.0``
    - PVC de 1Gi pour chaque controller
- Service
    - pas d'IP externe

#### Job création de topic
- Job
- créer un topic avec les configs suivantes:
    - Topic name : demo
    - partitions : 6
    - replication factor : 3

### Spark:
#### Dossier spark_code:
ce dossier contient:
- Les éléments qui ont aidé à entraîner le modèle de classification multiclasse (Random Forest) en utilisant PySpark, avec les fichiers exportés du modèle entraîné, ainsi que le fichier ``spark_job.py`` qui va être exécuté sur Spark.
- Le Dockerfile nécessaire pour les pods Spark afin de faire le traitement des données reçues de Kafka.

#### Spark_k8
##### Client
- Statefulset
    - replica : 1
    - utilise l'image : ``rabii10/myspark:v4.1``
- Service
    - pas d'IP externe

##### Master
- Statefulset
    - replica : 1
    - utilise l'image : ``rabii10/myspark:v4.1``
- Service
    - cluster IP existe

##### Worker
- Statefulset
    - replica : 1
    - utilise l'image : ``rabii10/myspark:v4.1``
- Service
    - cluster IP existe

### Monitoring:
Monitoring avec prometheus et affichage avec Grafana.

## Contributing

Pour les devs :
-Pour chaque nouvelle feature, créez une nouvelle branche et nommez-la avec le nom de la feature, puis créez une merge request vers dev pour être évaluée.

Pour les devops :
- La branche dev est la branche principale pour toutes les versions finales de développement. Vous pouvez tirer les derniers changements de cette branche vers votre branche devops, mais pas l'inverse.