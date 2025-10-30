# opentera-actimetry-service
Actimetry service

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

## Running the service (configure once)

### Create a systemd service
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

### Register the service in OpenTera

Go to your project directory and execute the following commands:

```bash
# First enable the conda environment
source <Path to your opentera-actimetry-service.git repository>/venv/bin/activate
# Then register the service
python3 <Path to your opentera-actimetry-service.git repository>/tools/create_actimetry_service.py --server_url="your_opentera_server_url" --admin_user="your_admin_username" --admin_password="your_admin_password"
```

### Reload systemd and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable opentera-actimetry-service
sudo systemctl start opentera-actimetry-service
```
