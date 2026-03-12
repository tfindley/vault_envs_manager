# VEM - Vault Envs Manager

Pull secrets from a HashiCorp Vault KV v2 secrets engine and export them as shell environment variables.

## Requirements

- Python >= 3.10
- Compatible with Linux/macOS only - Windows users, please use WSL

## Installation

### pip install (recommended)

Install directly from the git repository into any Python virtual environment:

```bash
pip install "vem @ git+https://github.com/tfindley/vault_envs_manager.git"
```

To pin a specific version/tag:

```bash
pip install "vem @ git+https://github.com/tfindley/vault_envs_manager.git@v1.0.0"
```

This creates a `vem` executable in your venv's `bin/` directory with the correct shebang automatically - no manual shebang editing, symlinks, or chmod required.

### Docker / CI

In a Dockerfile or CI pipeline, install into any venv with a single pip line:

```dockerfile
RUN /path/to/venv/bin/pip install --no-cache-dir \
        "vem @ git+https://github.com/tfindley/vault_envs_manager.git@v1.0.0"
```

### Development install

```bash
git clone https://github.com/tfindley/vault_envs_manager.git
cd vault_envs_manager
make install    # Creates .venv and installs in editable mode
```

## Usage

To see available authentication methods, run `vem --help`

### Quick start

```bash
# Display secrets as shell export statements (default output)
vem userpass \
  -i username \
  --kv-engine kv_name \
  --kv-path myapp \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem

# Load secrets directly into your shell
eval $(vem userpass \
  -i username \
  --kv-engine kv_name \
  --kv-path myapp \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem)
```

You will be prompted for your password interactively. To pass it non-interactively, use `-s password`.

## Command Reference

All options below are shared across every auth method. Run `vem <method> --help` for full details.

### Vault Connection

| Flag         | Short | Env Variable | Description                                                    |
| ------------ | ----- | ------------ | -------------------------------------------------------------- |
| --vault-addr |       | VAULT_ADDR   | Vault server address (default: `http://127.0.0.1:8200`)        |
| --ca-cert    |       |              | Path to custom CA certificate for TLS verification             |
| --no-verify  |       |              | Disable TLS certificate verification (insecure)                |

### Secrets

| Flag        | Short | Description                                                          |
| ----------- | ----- | -------------------------------------------------------------------- |
| --kv-engine |       | Mount point of the KV v2 secrets engine (e.g., `kv_user_tristan`)    |
| --kv-path   |       | Secret path to fetch (can be repeated; later paths override earlier) |

### Output

| Flag            | Short | Description                                                      |
| --------------- | ----- | ---------------------------------------------------------------- |
| --output        |       | Output format: `env`, `json`, `none` (default: export for eval)  |
| --output-file   |       | Write output to a file instead of stdout                         |
| --env-token-var |       | Include the Vault token in output as this variable name          |

### Auth: Token

Authenticate with an existing Vault token.

| Flag    | Short | Env Variable | Description  |
| ------- | ----- | ------------ | ------------ |
| --token | -t    | VAULT_TOKEN  | Vault token  |

```bash
vem token \
  -t $VAULT_TOKEN \
  --kv-engine kv_name \
  --kv-path testenv \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem
```

### Auth: UserPass

Authenticate with username and password (with optional MFA). If `-i` or `-s` are omitted, you will be prompted interactively.

| Flag         | Short | Description                           |
| ------------ | ----- | ------------------------------------- |
| --identifier | -i    | Username                              |
| --secret     | -s    | Password                              |
| --mfa-path   |       | MFA method path (enables MFA)         |
| --mfa-code   |       | MFA code (prompted if --mfa-path set) |

```bash
vem userpass \
  -i username \
  -s password \
  --kv-engine kv_name \
  --kv-path testenv \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem
```

### Auth: AppRole

Authenticate with AppRole credentials. If `-i` or `-s` are omitted, you will be prompted interactively.

| Flag         | Short | Description        |
| ------------ | ----- | ------------------ |
| --identifier | -i    | AppRole role ID    |
| --secret     | -s    | AppRole secret ID  |

```bash
vem approle \
  -i $ROLE_ID \
  -s $SECRET_ID \
  --kv-engine kv_name \
  --kv-path testenv \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem
```

## Walkthrough

### Creating your Envs

Log into Vault using the userpass method at your Vault address (e.g., `https://vault.example.com:8200`).

If Python doesn't trust your Vault's TLS certificate, download the root and intermediate CAs as a PEM file (e.g., `cacert.pem`) and pass it via `--ca-cert`.

In Vault, find your KV secret engine (e.g., `kv_user/<login_id>`). Create a secret (e.g., `testing`) and add key/value pairs:

```plaintext
KEY1: VALUE1
KEY2: VALUE2
```

### Retrieving Secrets

Display your secrets to verify everything works. You will be prompted for your password:

```bash
vem userpass \
  --kv-engine kv_user/tristan.findley \
  --kv-path testing \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem \
  --env-token-var VAULT_TOKEN \
  --output env \
  -i tristan.findley
```

Expected output:

```plaintext
KEY1='VALUE1'
KEY2='VALUE2'
VAULT_TOKEN='hvs.YourTokenValue'
```

To load these into your current shell, wrap the command in `eval` and drop the `--output` flag:

```bash
eval $(vem userpass \
  --kv-engine kv_user/tristan.findley \
  --kv-path testing \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem \
  --env-token-var VAULT_TOKEN \
  -i tristan.findley)
```

You should see no output (except the password prompt). Run `env` to verify your variables are set.

### Multiple paths

You can fetch from multiple KV paths by repeating `--kv-path`. They load in order, so later paths overwrite earlier ones for duplicate keys:

```bash
vem userpass -i username \
  --kv-engine kv_name \
  --kv-path defaults \
  --kv-path overrides \
  --vault-addr https://vault.example.com:8200
```

## FAQ

**Q: Can this be used to generate environment files?**

**A:** Yes. Use `--output env --output-file environment.env` (don't wrap in eval when writing to a file).

**Q: Can I pass my password on the command line?**

**A:** Yes, use `-s password` - though be aware this is visible in process listings. It's safe when injected from a secrets manager or CI variable. This works the same for AppRole's role ID and secret ID.

**Q: I already have a Vault token. Can I just use that?**

**A:** Yes, use the `token` auth method with `-t`. Note that in most deployments, Vault tokens expire.

```bash
vem token \
  -t "$VAULT_TOKEN" \
  --kv-engine kv_name \
  --kv-path testing \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem \
  --env-token-var VAULT_TOKEN2 \
  --output json \
  --output-file secrets.json
```

**Q: What does `--env-token-var` do?**

**A:** It exports the authenticated Vault token as an environment variable with the name you specify. e.g., `--env-token-var VAULT_TOKEN` adds `VAULT_TOKEN='hvs.xxx'` to the output.
