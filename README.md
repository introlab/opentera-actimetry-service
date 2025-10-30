# opentera-actimetry-service
Actimetry service for the OpenTera platform. This service manages actimetry data files and their processing. It is based on [OpenTera](https://github.com/introlab/opentera) and uses its service architecture. Data processing is done using [OpenIMU](https://github.com/introlab/OpenIMU) libraries.

Base concept:

- Actimetry data files are uploaded by clients to the OpenTera server using REST API calls.
- The Actimetry Service retrieves these files from the server, stores them locally, and processes them using OpenIMU tools in a participant database.
- Processed data and reports are accessible through the REST API that can be used by other services or clients.

## Authors
- Simon Brière (@sbriere)
- Dominic Létourneau (@doumdi)

## Configuration

### 1. Create conda virtual environment

Make sure conda is installed first. Then create the conda environment:

```bash
# This will also install the required packages in requirements.txt
./create_conda_venv.sh
```

### 2. Build the service with CMake

```bash
# This will build the service in the build/ folder and update all the translations.
mkdir build
cd build
cmake ..
make
```

### 3. Update the configuration file

Edit the [ActimetryService.json](ActimetryService.json) to fit your specific setup (database connection, files directory, etc.)

### 4. Update your nginx configuration to add the Actimetry Service path

Add the [config/opentera-actimetry-service.conf](config/opentera-actimetry-service.conf) to your nginx configuration file to forward requests to the Actimetry Service.

### 5. Create database and user for actimetry service
Create a database and a user for the actimetry service in your PostgreSQL server. You can use the following SQL commands as an example:

```sql
CREATE DATABASE opentera_actimetry;
CREATE USER actimetry_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE opentera_actimetry TO actimetry_user;
```
>Update your [ActimetryService.json](ActimetryService.json) configuration file with the database connection details.

## Running the service (configure once)

### 5. Create a systemd service
Create a systemd service file in the /lib/systemd/system folder named `opentera-actimetry-service.service` with the following content:

```ini
[Unit]
Description=OpenTeraActimetryService
After=opentera.service
Requires=opentera.service
PartOf=opentera.service

[Service]
User=opentera
Group=opentera
Environment=PYTHONPATH=<Path to your opentera-actimetry-service.git repository>
# You can change the --conf parameter to point to your configuration file
ExecStart=<Path to your opentera-actimetry-service.git repository>/venv/bin/python3 <Path to your opentera-actimetry-service.git repository>/ActimetryService.py --conf=ActimetryService.json
WorkingDirectory=<Path to your opentera-actimetry-service.git repository>
StandardOutput=syslog+console
StandardError=syslog+console
Restart=always
RestartSec=10s
KillMode=process
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target opentera.service
```

### 6. Register the service in OpenTera

Go to your project directory and execute the following commands:

```bash
# First enable the conda environment
source <Path to your opentera-actimetry-service.git repository>/venv/bin/activate
# Then register the service
python3 <Path to your opentera-actimetry-service.git repository>/tools/create_actimetry_service.py --server_url="your_opentera_server_url" --admin_user="your_admin_username" --admin_password="your_admin_password"
```

### 7. Reload systemd and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable opentera-actimetry-service
sudo systemctl start opentera-actimetry-service
```
