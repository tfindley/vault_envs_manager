#!/usr/bin/env python3

"""VEM (Vault Envs Manager) - Pull secrets from HashiCorp Vault and export as environment variables."""

import argparse
import os
import getpass
import sys
import hvac
import json

# -----------------------------------
# Argument parsing
# -----------------------------------


def _build_common_parser():
    """Build a parent parser with arguments shared by all auth methods."""
    common = argparse.ArgumentParser(add_help=False)

    vault = common.add_argument_group("vault connection")
    vault.add_argument(
        "--vault-addr",
        default=os.getenv("VAULT_ADDR", "http://127.0.0.1:8200"),
        help="Vault server address (env: VAULT_ADDR, default: http://127.0.0.1:8200)",
    )
    vault.add_argument(
        "--ca-cert",
        help="path to custom CA certificate for TLS verification",
    )
    vault.add_argument(
        "--no-verify",
        action="store_true",
        help="disable TLS certificate verification (insecure)",
    )

    secrets = common.add_argument_group("secrets")
    secrets.add_argument(
        "--kv-engine",
        required=True,
        help="mount point of the KV v2 secrets engine (e.g. 'kv_user_tristan')",
    )
    secrets.add_argument(
        "--kv-path",
        action="append",
        required=True,
        help="secret path to fetch (can be repeated; later paths override earlier ones)",
    )

    output = common.add_argument_group("output")
    output.add_argument(
        "--output",
        choices=["env", "json", "none"],
        help="output format (default: 'export KEY=VAL' for use with eval)",
    )
    output.add_argument(
        "--output-file",
        metavar="FILE",
        help="write output to FILE instead of stdout",
    )
    output.add_argument(
        "--env-token-var",
        metavar="VAR",
        help="include the Vault token in output as VAR",
    )

    return common


def parse_args():
    common = _build_common_parser()

    parser = argparse.ArgumentParser(
        prog="vem",
        description="Pull secrets from HashiCorp Vault KV v2 and export as environment variables.",
        epilog=(
            "examples:\n"
            "  vem userpass -i user --kv-engine kv_name --kv-path myapp\n"
            "  vem token -t $VAULT_TOKEN --kv-engine kv_name --kv-path myapp --output json\n"
            "  eval $(vem approle -i $ROLE_ID -s $SECRET_ID --kv-engine kv_name --kv-path myapp)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="auth_method",
        required=True,
        title="auth methods",
        metavar="{userpass,token,approle}",
    )

    # userpass
    p_userpass = subparsers.add_parser(
        "userpass",
        parents=[common],
        help="authenticate with username and password",
        description="Authenticate to Vault using username/password (with optional MFA).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="if -i or -s are omitted, you will be prompted interactively.",
    )
    auth_up = p_userpass.add_argument_group("authentication")
    auth_up.add_argument("-i", "--identifier", metavar="USER", help="username")
    auth_up.add_argument("-s", "--secret", metavar="PASS", help="password")
    auth_up.add_argument("--mfa-path", help="MFA method path (enables MFA)")
    auth_up.add_argument("--mfa-code", help="MFA code (prompted if --mfa-path set)")

    # token
    p_token = subparsers.add_parser(
        "token",
        parents=[common],
        help="authenticate with an existing Vault token",
        description="Authenticate to Vault using a token directly.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    auth_tk = p_token.add_argument_group("authentication")
    auth_tk.add_argument(
        "-t", "--token",
        default=os.getenv("VAULT_TOKEN"),
        help="Vault token (env: VAULT_TOKEN)",
    )

    # approle
    p_approle = subparsers.add_parser(
        "approle",
        parents=[common],
        help="authenticate with AppRole (role ID + secret ID)",
        description="Authenticate to Vault using AppRole credentials.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="if -i or -s are omitted, you will be prompted interactively.",
    )
    auth_ar = p_approle.add_argument_group("authentication")
    auth_ar.add_argument("-i", "--identifier", metavar="ROLE_ID", help="AppRole role ID")
    auth_ar.add_argument("-s", "--secret", metavar="SECRET_ID", help="AppRole secret ID")

    return parser.parse_args()


# -----------------------------------
# Vault client and auth methods
# -----------------------------------


def get_client(addr, ca_cert=None, verify=True):
    """Initialize Vault client with TLS options."""
    return hvac.Client(url=addr, verify=verify if ca_cert is None else ca_cert)


def authenticate_userpass(client, username, password, mfa_path=None, mfa_code=None):
    """Authenticate using userpass (with optional MFA)."""
    if not username:
        username = input("Username: ")
    if not password:
        password = getpass.getpass("Password: ")

    login_payload = {"password": password}
    if mfa_path:
        if not mfa_code:
            mfa_code = input("MFA code: ")
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
                raise_on_deleted_version=True,  # Avoid deprecation warnings
            )
            merged_data.update(secret["data"]["data"])
        except Exception as e:
            print(f"Failed to read from '{engine}/{path}': {e}", file=sys.stderr)
    return merged_data


def _emit(text, filename=None):
    """Write text to a file or print to stdout."""
    if filename:
        with open(filename, "w") as f:
            f.write(text + "\n")
    else:
        print(text)


def output_secrets(data, mode=None, filename=None):
    """Output secrets in different formats depending on mode."""

    if mode == "json":
        _emit(json.dumps(data, indent=2), filename)

    elif mode == "env":
        _emit("\n".join(f"{key}='{value}'" for key, value in data.items()), filename)

    elif mode is None:
        # Default: Single-line export-prefixed shell-safe format
        _emit("export " + " ".join(
            f"{key}='{value}'" for key, value in data.items()
        ), filename)

    elif mode == "none":
        pass


# -----------------------------------
# Main program flow
# -----------------------------------


def main():
    args = parse_args()

    # Initialize Vault client
    client = get_client(
        args.vault_addr, ca_cert=args.ca_cert, verify=not args.no_verify
    )

    # Authenticate based on the chosen method
    try:
        if args.auth_method == "userpass":
            token = authenticate_userpass(
                client,
                args.identifier,
                args.secret,
                mfa_path=args.mfa_path,
                mfa_code=args.mfa_code,
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

    # Fetch and merge all secrets from Vault
    secrets = fetch_kv2_secrets(client, args.kv_engine, args.kv_path)

    # Optionally include the token itself in the output
    if args.env_token_var:
        secrets[args.env_token_var] = token

    # Output the result
    output_secrets(secrets, args.output, args.output_file)


# Entry point
if __name__ == "__main__":
    main()
