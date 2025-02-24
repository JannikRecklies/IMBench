#!/bin/bash

# Set variables
SSH_KEY_PATH="/home/ubuntu/.ssh/cluster-key"
RC_FILE="UPPMAX_2024_1-4-openrc.sh"
CLOUD_CONFIG_FILE="cloud-config-worker.yml"
START_INSTANCE_SCRIPT="start_instance.py"
BACKUP_FILE="cloud-config-worker.yml.bak"

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

# Backup the original cloud-config-worker.yml
if [ ! -f "$BACKUP_FILE" ]; then
    cp "$CLOUD_CONFIG_FILE" "$BACKUP_FILE"
    echo "Backup of $CLOUD_CONFIG_FILE created."
else
    echo "Backup already exists."
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

# Restore the original cloud-config-worker.yml
echo "Restoring original cloud-config-worker.yml..."
mv "$BACKUP_FILE" "$CLOUD_CONFIG_FILE"

echo "Setup complete!"