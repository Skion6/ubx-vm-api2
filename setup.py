import os

def main():
    print("==========================================")
    print("    Xcloud - Configuration Script")
    print("==========================================")

    env_path = ".env"
    existing_config = {}

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    existing_config[key] = value

    admin_password = input(f"Enter API Admin Password [{existing_config.get('ADMIN_PASSWORD', 'secret_password')}]: ") or existing_config.get('ADMIN_PASSWORD', 'secret_password')
    max_vms = input(f"Enter Max VMs per Developer [{existing_config.get('MAX_VMS_PER_DEV', '100')}]: ") or existing_config.get('MAX_VMS_PER_DEV', '100')
    max_inactivity = input(f"Enter Max Inactivity Time (minutes) [{existing_config.get('MAX_INACTIVITY_MINUTES', '5')}]: ") or existing_config.get('MAX_INACTIVITY_MINUTES', '5')
    max_session = input(f"Enter Max Session Lifetime (minutes) [{existing_config.get('MAX_SESSION_MINUTES', '60')}]: ") or existing_config.get('MAX_SESSION_MINUTES', '60')

    with open(env_path, "w") as f:
        f.write(f"ADMIN_PASSWORD={admin_password}\n")
        f.write(f"MAX_VMS_PER_DEV={max_vms}\n")
        f.write(f"MAX_INACTIVITY_MINUTES={max_inactivity}\n")
        f.write(f"MAX_SESSION_MINUTES={max_session}\n")

    print("\nConfiguration saved to .env")
    print("==========================================\n")

if __name__ == "__main__":
    main()
