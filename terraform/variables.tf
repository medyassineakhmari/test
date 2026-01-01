variable "project" {
  description = "L'ID de votre projet GCP"
  type        = string
  default     = "sdtd-2"
}

variable "region" {
  description = "Région de déploiement"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "Zone de déploiement"
  type        = string
  default     = "europe-west1-b"
}