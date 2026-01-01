output "gateway_public_ip" {
  description = "IP publique de la Gateway (à mettre dans inventory.ini)"
  value       = google_compute_instance.gateway.network_interface[0].access_config[0].nat_ip
}

output "master_private_ip" {
  description = "IP privée du Master"
  value       = google_compute_instance.master.network_interface[0].network_ip
}

output "worker_private_ips" {
  description = "Liste des IPs privées des Workers"
  value       = google_compute_instance.worker[*].network_interface[0].network_ip
}

output "ssh_command_gateway" {
  description = "Commande pour se connecter à la Gateway"
  value       = "ssh -i ../id_rsa_gcp ubuntu@${google_compute_instance.gateway.network_interface[0].access_config[0].nat_ip}"
}