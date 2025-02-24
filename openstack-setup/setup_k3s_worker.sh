#!/bin/bash

# Set variables
SSH_KEY_PATH="/home/ubuntu/.ssh/cluster-key"
RC_FILE="/home/ubuntu/IMBench/openstack-setup/UPPMAX_2024_1-4-openrc.sh"
CLOUD_CONFIG_FILE="/home/ubuntu/IMBench/openstack-setup/cloud-config-worker.yml"
START_INSTANCE_SCRIPT="/home/ubuntu/IMBench/openstack-setup/start_instance.py"

# Generate SSH key (if not already created)
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "Generating SSH key..."
    ssh-keygen -t rsa -f "$SSH_KEY_PATH" -N "" # No passphrase
else
    echo "SSH key already exists."
fi

# Retrieve necessary values
echo "Retrieving values..."
SSH_KEY_CONTENT=$(sudo cat "$SSH_KEY_PATH.pub")
K3S_IP=$(hostname -I | awk '{print $1}')  # Get the first IP
K3S_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/node-token)

# Validate values
if [[ -z "$SSH_KEY_CONTENT" || -z "$K3S_IP" || -z "$K3S_TOKEN" ]]; then
    echo "Error: Could not retrieve one or more required values."
    exit 1
fi

# Update cloud-config-worker.yml
echo "Updating cloud-config-worker.yml..."
sed -i "s|<SSH_AUTHORIZED_KEYS>|$SSH_KEY_CONTENT|g" "$CLOUD_CONFIG_FILE"
sed -i "s|<K3S_IP>|$K3S_IP|g" "$CLOUD_CONFIG_FILE"
sed -i "s|<K3S_TOKEN>|$K3S_TOKEN|g" "$CLOUD_CONFIG_FILE"

echo "cloud-config-worker.yml updated successfully."

# Run start_instance.py
echo "Starting worker nodes..."
python3 "$START_INSTANCE_SCRIPT"

echo "Setup complete!"