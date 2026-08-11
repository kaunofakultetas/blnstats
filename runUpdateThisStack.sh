#!/bin/bash



# STEP 1: Create necessary files and directories
# ==============================================
mkdir -p ./_DATA/mysql/data
mkdir -p ./_DATA/_PUBLIC_FILES/INPUT
mkdir -p ./_DATA/_PUBLIC_FILES/GENERATED
touch .env
sudo chown -R 1000:1000 ./_DATA




# STEP 2: Run the stack
# =====================
echo "TZ=$(timedatectl show --value --property=Timezone)" > .env
sudo docker-compose down
sudo docker-compose up -d --build
