#!/usr/bin/env python3

import argparse
import os
import getpass
import sys
import hvac
import json

# -----------------------------------
# Argument parsing
# -----------------------------------

def parse_args():
    # Common arguments shared by all subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault-addr", default=os.getenv("VAULT_ADDR", "http://127.0.0.1:8200"),
                        help="Address of the Vault server (default: VAULT_ADDR env var or localhost)")
    common.add_argument("--env-token-var", help="Name of environment variable to set with the Vault token")
    common.add_argument("--kv-engine", required=True,
                        help="Mount point of the Vault KV v2 secrets engine (e.g., 'secret', 'kv_user_tristan')")
    common.add_argument("--kv-path", action="append", required=True,
                        help="KV v2 secret paths to fetch (can be repeated for multiple)")
    common.add_argument("--output", choices=["env", "json", "none"],
                        help="Output mode: env (shell assignments), json, or none" )
    common.add_argument("--output-file", help="File to write output to (optional)")
    common.add_argument("--ca-cert", help="Path to custom CA certificate for TLS verification")
    common.add_argument("--no-verify", action="store_true",
                        help="Disable SSL verification (insecure!)")

    # Main parser (does not include common, to avoid arg duplication)
    parser = argparse.ArgumentParser(description="Pull secrets from Vault and set as env vars.")
    subparsers = parser.add_subparsers(dest="auth_method", required=True)

    # userpass auth method
    p_userpass = subparsers.add_parser("userpass", parents=[common])
    p_userpass.add_argument("-i", "--identifier", help="Username")
    p_userpass.add_argument("-s", "--secret", help="Password")
    p_userpass.add_argument("--mfa-path", help="Path to MFA method (if used)")
    p_userpass.add_argument("--mfa-code", help="MFA code (if used)")

    # token auth method
    p_token = subparsers.add_parser("token", parents=[common])
    p_token.add_argument("-t", "--token", help="Vault token")

    # approle auth method
    p_approle = subparsers.add_parser("approle", parents=[common])
    p_approle.add_argument("-i", "--identifier", help="Role ID")
    p_approle.add_argument("-s", "--secret", help="Secret ID")

    return parser.parse_args()

# -----------------------------------
# Vault client and auth methods
# -----------------------------------

def get_client(addr, ca_cert=None, verify=True):
    """Initialize Vault client with TLS options."""
    return hvac.Client(
        url=addr,
        verify=verify if ca_cert is None else ca_cert
    )

def authenticate_userpass(client, username, password, mfa_path=None, mfa_code=None):
    """Authenticate using userpass (with optional MFA)."""
    if not username:
        username = input("Username: ")
    if not password:
        password = getpass.getpass("Password: ")

    login_payload = {"password": password}
    if mfa_path and mfa_code:
        login_payload["mfa_code"] = mfa_code

    result = client.auth.userpass.login(username=username, **login_payload)
    return result["auth"]["client_token"]

def authenticate_token(client, token):
    """Authenticate using a Vault token directly."""
    client.token = token
    if not client.is_authenticated():
        raise Exception("Token authentication failed.")
    return token

def authenticate_approle(client, role_id, secret_id):
    """Authenticate using AppRole credentials."""
    if not role_id:
        role_id = input("Role ID: ")
    if not secret_id:
        secret_id = getpass.getpass("Secret ID: ")

    result = client.auth.approle.login(role_id=role_id, secret_id=secret_id)
    return result["auth"]["client_token"]

# -----------------------------------
# Secret fetching and output
# -----------------------------------

def fetch_kv2_secrets(client, engine, secret_paths):
    """Fetch and merge key/value secrets from multiple KV v2 paths."""
    merged_data = {}
    for path in secret_paths:
        try:
            secret = client.secrets.kv.v2.read_secret_version(
                mount_point=engine,
                path=path,
                raise_on_deleted_version=True  # Avoid deprecation warnings
            )
            merged_data.update(secret["data"]["data"])
        except Exception as e:
            print(f"Failed to read from '{engine}/{path}': {e}", file=sys.stderr)
    return merged_data

def output_secrets(data, mode=None, filename=None):
    """Output secrets in different formats depending on mode."""
    
    if mode == "json":
        # Output as JSON
        json_data = json.dumps(data, indent=2)
        if filename:
            with open(filename, "w") as f:
                f.write(json_data + "\n")
        else:
            print(json_data)

    elif mode == "env":
        # Multi-line key='value' format (no 'export' prefix)
        lines = [f"{key}='{value}'" for key, value in data.items()]
        if filename:
            with open(filename, "w") as f:
                f.write("\n".join(lines) + "\n")
        else:
            for line in lines:
                print(line)

    elif mode is None:
        # Default: Single-line export-prefixed shell-safe format
        export_line = "export " + " ".join(f"{key}='{value}'" for key, value in data.items())
        if filename:
            with open(filename, "w") as f:
                f.write(export_line + "\n")
        else:
            print(export_line)

    elif mode == "none":
        pass

    else:
        print(f"Unsupported output mode: {mode}", file=sys.stderr)
        sys.exit(1)

# -----------------------------------
# Main program flow
# -----------------------------------

def main():
    args = parse_args()

    # Initialize Vault client
    client = get_client(
        args.vault_addr,
        ca_cert=args.ca_cert,
        verify=not args.no_verify
    )

    # Authenticate based on the chosen method
    try:
        if args.auth_method == "userpass":
            token = authenticate_userpass(
                client,
                args.identifier,
                args.secret,
                mfa_path=args.mfa_path,
                mfa_code=args.mfa_code or (input("MFA code: ") if args.mfa_path else None)
            )
        elif args.auth_method == "token":
            token = authenticate_token(client, args.token or input("Vault token: "))
        elif args.auth_method == "approle":
            token = authenticate_approle(client, args.identifier, args.secret)
        else:
            raise ValueError("Unsupported auth method")
    except Exception as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Store the token in the client session
    client.token = token

    # Optionally export the token itself to the environment
    env_data = {}
    if args.env_token_var:
        env_data[args.env_token_var] = token

    # Fetch and merge all secrets from Vault
    secrets = fetch_kv2_secrets(client, args.kv_engine, args.kv_path)
    secrets.update(env_data)

    # Output the result
    output_secrets(secrets, args.output, args.output_file)

# Entry point
if __name__ == "__main__":
    main()
