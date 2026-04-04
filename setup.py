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
    parser.add_argument('--max-global-vms', '-g', type=int, help='Global max concurrent VMs (hard limit)')
    parser.add_argument('--dev-whitelist', '-w', help='Comma-separated developer IDs to whitelist (disables allow-all)')
    parser.add_argument('--max-free-vms', type=int, help='Maximum concurrent free VMs (premium VMs do not count towards this limit)')
    parser.add_argument('--max-premium-vms', type=int, help='Maximum concurrent premium VMs (0 = unlimited)')
    parser.add_argument('--max-cpu-threads', type=int, help='Maximum CPU threads (cores) per VM instance')
    parser.add_argument('--max-ram-gb', type=int, help='Maximum RAM (GB) per VM instance')
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

    # Global hard cap for concurrent VMs across all developers
    max_global_vms = args.max_global_vms if args.max_global_vms is not None else (
        int(get_input(f"Enter Global max concurrent VMs (hard limit) [{existing_config.get('MAX_GLOBAL_VMS', '10')}]: ", existing_config.get('MAX_GLOBAL_VMS', '10')))
        if not non_interactive else int(existing_config.get('MAX_GLOBAL_VMS', '10'))
    )

    # Whitelist behavior: by default allow all developers. If a whitelist is provided,
    # restrict creation to those developer IDs.
    dev_whitelist = ''
    allow_all_developers = True
    if args.dev_whitelist:
        dev_whitelist = args.dev_whitelist
        allow_all_developers = False
    else:
        if not non_interactive:
            allow_input = get_input(f"Allow any developer to create VMs? [Y/n] [{ 'Y' if existing_config.get('ALLOW_ALL_DEVELOPERS', '1') in ('1','true','True') else 'n'}]: ", existing_config.get('ALLOW_ALL_DEVELOPERS', '1'))
            if str(allow_input).lower() in ('n','no','0'):
                allow_all_developers = False
                dev_whitelist = get_input(f"Enter comma-separated developer IDs to allow [{existing_config.get('DEV_WHITELIST', '')}]: ", existing_config.get('DEV_WHITELIST',''))
        else:
            allow_all_developers = existing_config.get('ALLOW_ALL_DEVELOPERS', '1') in ('1','true','True')
            dev_whitelist = existing_config.get('DEV_WHITELIST', '')

    # New options for VM limits and resource caps
    max_free_vms = args.max_free_vms if args.max_free_vms is not None else (
        int(get_input(f"Enter Max Free VMs (premium excluded) [{existing_config.get('MAX_FREE_VMS', '10')}]: ", existing_config.get('MAX_FREE_VMS', '10')))
        if not non_interactive else int(existing_config.get('MAX_FREE_VMS', '10'))
    )

    max_premium_vms = args.max_premium_vms if args.max_premium_vms is not None else (
        int(get_input(f"Enter Max Premium VMs (0=unlimited) [{existing_config.get('MAX_PREMIUM_VMS', '0')}]: ", existing_config.get('MAX_PREMIUM_VMS', '0')))
        if not non_interactive else int(existing_config.get('MAX_PREMIUM_VMS', '0'))
    )

    max_cpu_threads = args.max_cpu_threads if args.max_cpu_threads is not None else (
        int(get_input(f"Enter Max CPU Threads per VM [{existing_config.get('MAX_CPU_THREADS', '4')}]: ", existing_config.get('MAX_CPU_THREADS', '4')))
        if not non_interactive else int(existing_config.get('MAX_CPU_THREADS', '4'))
    )

    max_ram_gb = args.max_ram_gb if args.max_ram_gb is not None else (
        int(get_input(f"Enter Max RAM (GB) per VM [{existing_config.get('MAX_RAM_GB', '8')}]: ", existing_config.get('MAX_RAM_GB', '8')))
        if not non_interactive else int(existing_config.get('MAX_RAM_GB', '8'))
    )

    with open(env_path, "w") as f:
        f.write(f"ADMIN_PASSWORD={admin_password}\n")
        f.write(f"MAX_VMS_PER_DEV={max_vms}\n")
        f.write(f"MAX_GLOBAL_VMS={max_global_vms}\n")
        f.write(f"MAX_INACTIVITY_MINUTES={max_inactivity}\n")
        f.write(f"MAX_SESSION_MINUTES={max_session}\n")
        f.write(f"ALLOW_ALL_DEVELOPERS={1 if allow_all_developers else 0}\n")
        if dev_whitelist:
            f.write(f"DEV_WHITELIST={dev_whitelist}\n")
        if premium_code:
            f.write(f"PREMIUM_CODE={premium_code}\n")
        f.write(f"MAX_FREE_VMS={max_free_vms}\n")
        f.write(f"MAX_PREMIUM_VMS={max_premium_vms}\n")
        f.write(f"MAX_CPU_THREADS={max_cpu_threads}\n")
        f.write(f"MAX_RAM_GB={max_ram_gb}\n")

    print(f"\nConfiguration saved to {env_path}")
    print("==========================================\n")

if __name__ == "__main__":
    main()
