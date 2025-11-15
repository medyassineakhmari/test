# Real-Time Cyber Attack Detection Platform

This project is a distributed streaming application for **real-time detection and classification of cybersecurity attacks**.

Network and security events are ingested into a **Kafka cluster** (3 controllers, 3 brokers), processed in real time by **Apache Spark** streaming jobs, and passed through a **machine learning model** that predicts the **category of each attack**.  
All components are **orchestrated by Kubernetes** and deployed on **Google Cloud Platform (GCP)**, with **Prometheus** and **Grafana** providing end-to-end observability. A REST API documented with **Swagger/OpenAPI** exposes the results and control endpoints.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Architecture Diagram](#architecture-diagram)

---

## Architecture Overview

The platform is built around a streaming data pipeline:

1. **Data Ingestion – Kafka Cluster (3 controllers, 3 brokers)**  
   Network and security events are pushed to Kafka topics. The cluster is configured with three controllers and three brokers to provide high availability and fault tolerance.

2. **Streaming Processing – Spark**  
   A Spark Structured Streaming application consumes Kafka messages, performs real-time **aggregations** and feature engineering, and prepares the data for classification.

3. **Attack Classification – ML Model**  
   A trained machine learning model predicts the **attack category** for each event (e.g., benign vs malicious, and specific attack type). Predictions and enriched events are published to output topics or persisted to storage.

4. **Results / Outputs**  
   Classified results can be consumed by downstream services, dashboards, or alerting systems.

5. **Monitoring – Prometheus & Grafana**  
   All major components (Kafka, Spark, API, model service) expose metrics that are scraped by Prometheus and visualized via Grafana dashboards.

6. **Orchestration & Cloud – Kubernetes on GCP**  
   The entire stack runs inside a **Kubernetes** cluster on **Google Cloud Platform (GCP)**, enabling scalable, resilient, and cloud-native deployment.

---

## Architecture Diagram

Below is a high-level architecture diagram (Mermaid).  
If Mermaid rendering fails in your Git host, you can still copy this into any Mermaid-enabled tool.

```mermaid
%%{init: { "themeVariables": { "fontSize": "16px" }, "flowchart": { "nodeSpacing": 40, "rankSpacing": 50 } }}%%
flowchart LR
    %% Data source outside the cluster
    dataSrc["Network / Security Data"]

    %% Outer cluster: GCP + Kubernetes
    subgraph GCP_K8S["GCP Cloud - Kubernetes Cluster"]
        
        %% Kafka cluster
        subgraph Kafka["Kafka Cluster"]
            direction TB
            controllers["3 × Controllers"]
            brokers["3 × Brokers"]
        end

        %% Spark + ML
        subgraph SparkML["Spark Streaming + ML Model"]
            direction TB
            sparkProc["Spark Streaming (Aggregations)"]
            mlModel["Attack Classification Model"]
        end

        %% Outputs
        subgraph Outputs["Outputs"]
            results["Classified Events / Alerts"]
        end

        %% Monitoring
        subgraph Monitoring["Monitoring (Prometheus + Grafana)"]
            prom["Prometheus"]
            grafana["Grafana"]
        end
    end

    %% Main data flow
    dataSrc --> Kafka
    Kafka --> sparkProc
    sparkProc --> mlModel
    mlModel --> results

    %% Monitoring flow
    Kafka --> prom
    sparkProc --> prom
    mlModel --> prom
    results --> prom
    prom --> grafana
