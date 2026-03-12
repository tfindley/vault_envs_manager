# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VEM (Vault Envs Manager) is a CLI tool that pulls secrets from HashiCorp Vault KV v2 secrets engines and exports them as shell environment variables. It supports three auth methods: userpass, token, and approle. Linux/macOS only.

## Architecture

Installable Python package with a console script entry point. Package structure:

```text
vault_envs_manager/
    __init__.py
    main.py          # All logic: arg parsing, auth, secret fetching, output
pyproject.toml       # Package metadata, dependencies, entry point
```

`pyproject.toml` defines a `vem` console script that calls `vault_envs_manager.main:main`. When installed via `pip install`, pip auto-generates the `vem` executable with the correct shebang.

Single-file CLI (`vault_envs_manager/main.py`) using `argparse` with subcommands for each auth method. The `hvac` library handles all Vault API interaction. Flow: parse args -> init hvac client -> authenticate -> fetch/merge KV v2 secrets -> output (shell export, env, json, or none).

Key functions in `main.py`:
- `parse_args()` - argparse setup with common args shared via parent parser
- `get_client()` / `authenticate_*()` - Vault client init and auth
- `fetch_kv2_secrets()` - reads and merges secrets from multiple `--kv-path` entries
- `output_secrets()` - formats output; default (no `--output`) produces `export KEY='VALUE'` for eval usage

## Commands

```bash
make venv          # Create .venv
make install       # Install package in editable mode (pip install -e .)
make run           # Run vem interactively
make test          # Run with hardcoded token auth to localhost Vault
make format        # Auto-format with black
make clean         # Remove .venv, __pycache__, test output, egg-info
```

Direct usage after install: `vem <auth_method> --kv-engine <engine> --kv-path <path> [options]`

## Deployment

Install from git in any venv or container:
```bash
pip install "vem @ git+https://github.com/tfindley/vault_envs_manager.git@<version>"
```

## Dependencies

Single runtime dependency: `hvac>=2.3.0` (HashiCorp Vault Python client). Dev formatting: `black`.
