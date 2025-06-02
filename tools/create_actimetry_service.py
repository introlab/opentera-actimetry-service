import os
import subprocess
import sys
import requests
from requests.auth import _basic_auth_str
from opentera.db.models.TeraSessionType import TeraSessionType
import argparse

required_roles = []
required_user_groups = []


def create_session_type_for_actimetry(server_url: str, headers: str, service_info: dict) -> bool:
    # Verify if session type exists
    params = {'id_service': service_info['id_service']}
    response = requests.get(url=server_url + '/api/user/sessiontypes',
                            headers=headers, params=params, verify=False, timeout=5)


    found = False
    if response.status_code == 200 and len(response.json()) > 0:
        for session_type_info in response.json():
            if session_type_info['session_type_name'] == 'Actimetry':
                print(f"Session type Actimetry already exists")
                found = True
                break

    if not found:
        json_data = {
            "session_type": {
                "id_session_type": 0, #new
                "id_service": service_info['id_service'],
                "session_type_category": 1, # 1 = Service
                "session_type_name": "Actimetry",
                "session_type_color": "#FF0000",
                "session_type_online": False
            }
        }

        response = requests.post(url=server_url + '/api/user/sessiontypes',
                                headers=headers, json=json_data, verify=False, timeout=5)
        if response.status_code != 200:
            return False

        print(f"Session type Actimetry created")

    return True


def create_user_roles_and_user_groups(server_url: str, headers: str, service_info: dict) -> bool:

    if len(required_roles) != len(required_user_groups):
        print("Error: roles and user groups must have the same number of elements!")
        return False

    roles = []
    groups = []

    # Setup roles
    for role in required_roles:

        # Try to get role, if it exists skip creation
        params = {'id_service': service_info['id_service']}
        response = requests.get(url=server_url + '/api/user/services/roles',
                                headers=headers, params=params, verify=False, timeout=5)
        found = False
        if response.status_code == 200 and len(response.json()) > 0:
            for role_info in response.json():
                if role_info['service_role_name'] == role:
                    print(f"Role {role} already exists")
                    roles.append(role_info)
                    found = True
                    break
        if not found:
            json_data = {
                "service_role": {
                    "id_service": service_info['id_service'],
                    "id_service_role": 0, #new
                    "service_role_name": role
                }
            }

            response = requests.post(url=server_url + '/api/user/services/roles',
                                    headers=headers, json=json_data, verify=False, timeout=5)
            if response.status_code != 200:
                return False
            print(f"Role {role} created")
            roles.append(response.json())

    # Setup groups
    for group in required_user_groups:
        found = False
        # Verify if group already exists
        params = {'user_group_name': group}
        response = requests.get(url=server_url + '/api/user/usergroups',
                                headers=headers, params=params, verify=False, timeout=5)

        if response.status_code == 200 and len(response.json()) > 0:
            for group_info in response.json():
                if group_info['user_group_name'] == group:
                    print(f"User group {group} already exists")
                    groups.append(group_info)
                    found = True
                    break

        if not found:
            json_data = {
                "user_group": {
                    "id_user_group": 0, # new
                    "user_group_name": group,
                }
            }
            response = requests.post(url=server_url + '/api/user/usergroups',
                                    headers=headers, json=json_data, verify=False, timeout=5)
            if response.status_code != 200:
                return False

            print(f"User group {group} created")
            groups.append(response.json()[0])


     # Setup Service Roles
    for group, role in zip(groups, roles):
        found = False
        # Verify if service access already exists
        params = {'id_user_group': group['id_user_group'], 'id_service': service_info['id_service']}
        response = requests.get(url=server_url + '/api/user/services/access',
                                headers=headers, params=params, verify=False, timeout=5)

        if response.status_code == 200 and len(response.json()) > 0:
            for access_info in response.json():
                if access_info['id_service_role'] == role['id_service_role']:
                    print(f"Service access already exists for group {group['user_group_name']} and role {role['service_role_name']}")
                    found = True
                    break

        if not found:
            json_data = {
                "service_access": {
                    "id_service_access": 0, #new
                    "id_user_group": group['id_user_group'],
                    "id_service_role": role['id_service_role']
                }
            }

            response = requests.post(url=server_url + '/api/user/services/access',
                                    headers=headers, json=json_data, verify=False, timeout=5)
            if response.status_code != 200:
                return False

            print(f"Service access created for group {group['user_group_name']} and role {role['service_role_name']}")


    return True

def create_service(username: str, password: str, server_url: str, service_key: str) -> bool:

    headers = {'Authorization': _basic_auth_str(username, password)}
    params = {'service_key': service_key}
    response = requests.get(url=server_url + '/api/user/services',
                            headers=headers,params=params,verify=False, timeout=5)

    if response.status_code == 200:

        if len(response.json()) == 0:

            json_data = {
                'service': {
                        "id_service": 0,
                        "service_clientendpoint": "/actimetry",
                        "service_enabled": True,
                        "service_endpoint": "/",
                        "service_hostname": "actimetry-service",
                        "service_name": "ActimetryService",
                        "service_port": 4088,
                        "service_key": service_key,
                        "service_endpoint_participant": "/participant",
                        "service_endpoint_user": "/user",
                        "service_endpoint_device": "/device"
                }
            }

            response = requests.post(url=server_url + '/api/user/services',
                                        headers=headers, json=json_data, verify=False, timeout=5)
            if response.status_code != 200:
                return False

        service_info = response.json()[0]

        print(f"Service created with id: {service_info['id_service']}")
        if not create_user_roles_and_user_groups(server_url, headers, service_info):
            return False
        if not create_session_type_for_actimetry(server_url, headers, service_info):
            return False

        return True

    # Default return false
    return False


def script_main():
    # Use argparse to get the service key
    parser = argparse.ArgumentParser(description='Create a service for ActimetryService')
    parser.add_argument('--service_key', type=str, help='Service key', default='ActimetryService')
    parser.add_argument('--server_url', type=str, help='Server URL', default='https://proxy:40075')
    parser.add_argument('--username', type=str, help='Username', default='admin')
    parser.add_argument('--password', type=str, help='Password', default='admin')
    args = parser.parse_args()

    # Update global variables
    service_key = args.service_key
    server_url = args.server_url

    # Ask user to enter username and password
    if args.username == '' or args.password == '':
        args.username = input('Enter username: ')
        # TODO Hide password
        args.password = input('Enter password: ')


    if create_service(args.username, args.password, server_url, service_key):
        print('Service created')
    else:
        print('Error creating service')
        sys.exit(-1)

    sys.exit(0)

if __name__ == '__main__':
    script_main()
