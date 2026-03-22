import os
import sys
import argparse

def is_interactive():
    """Check if stdin is a tty (interactive terminal)"""
    return sys.stdin.isatty()

def get_input(prompt, default):
    """Get input interactively if terminal is available, otherwise use default"""
    if is_interactive():
        try:
            value = input(prompt)
            return value if value else default
        except (EOFError, KeyboardInterrupt):
            pass
    return default

def main():
    parser = argparse.ArgumentParser(description='Xcloud Configuration Script')
    parser.add_argument('--admin-password', '-a', help='API Admin Password')
    parser.add_argument('--max-vms', '-m', type=int, help='Max VMs per Developer')
    parser.add_argument('--max-inactivity', '-i', type=int, help='Max Inactivity Time (minutes)')
    parser.add_argument('--max-session', '-s', type=int, help='Max Session Lifetime (minutes)')
    parser.add_argument('--premium-code', '-p', help='Premium Code(s), comma-separated')
    parser.add_argument('--non-interactive', '-n', action='store_true', help='Use defaults without prompting')
    args = parser.parse_args()

    print("==========================================")
    print("    Xcloud - Configuration Script")
    print("==========================================")

    # Use absolute path based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    existing_config = {}

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    existing_config[key] = value

    # Use command-line args first, then interactive input, then defaults
    non_interactive = args.non_interactive or not is_interactive()

    admin_password = args.admin_password if args.admin_password else (
        get_input(f"Enter API Admin Password [{existing_config.get('ADMIN_PASSWORD', 'secret_password')}]: ", existing_config.get('ADMIN_PASSWORD', 'secret_password'))
        if not non_interactive else existing_config.get('ADMIN_PASSWORD', 'secret_password')
    )

    max_vms = args.max_vms if args.max_vms else (
        int(get_input(f"Enter Max VMs per Developer [{existing_config.get('MAX_VMS_PER_DEV', '100')}]: ", existing_config.get('MAX_VMS_PER_DEV', '100')))
        if not non_interactive else int(existing_config.get('MAX_VMS_PER_DEV', '100'))
    )

    max_inactivity = args.max_inactivity if args.max_inactivity else (
        int(get_input(f"Enter Max Inactivity Time (minutes) [{existing_config.get('MAX_INACTIVITY_MINUTES', '5')}]: ", existing_config.get('MAX_INACTIVITY_MINUTES', '5')))
        if not non_interactive else int(existing_config.get('MAX_INACTIVITY_MINUTES', '5'))
    )

    max_session = args.max_session if args.max_session else (
        int(get_input(f"Enter Max Session Lifetime (minutes) [{existing_config.get('MAX_SESSION_MINUTES', '60')}]: ", existing_config.get('MAX_SESSION_MINUTES', '60')))
        if not non_interactive else int(existing_config.get('MAX_SESSION_MINUTES', '60'))
    )

    premium_code = args.premium_code if args.premium_code else (
        get_input(f"Enter Premium Code(s), comma-separated (leave empty for none) [{existing_config.get('PREMIUM_CODE', '')}]: ", existing_config.get('PREMIUM_CODE', ''))
        if not non_interactive else existing_config.get('PREMIUM_CODE', '')
    )

    with open(env_path, "w") as f:
        f.write(f"ADMIN_PASSWORD={admin_password}\n")
        f.write(f"MAX_VMS_PER_DEV={max_vms}\n")
        f.write(f"MAX_INACTIVITY_MINUTES={max_inactivity}\n")
        f.write(f"MAX_SESSION_MINUTES={max_session}\n")
        if premium_code:
            f.write(f"PREMIUM_CODE={premium_code}\n")

    print(f"\nConfiguration saved to {env_path}")
    print("==========================================\n")

if __name__ == "__main__":
    main()
