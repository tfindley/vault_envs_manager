# VEM - Vault Envs Manager

This script will manage your environmental variables (envs) by pulling them from a Hashicorp Vault key/value (kv) secrets engine.


To run the command:

./main.py {authmode} --vault-addr {urll} --env-token-var {ENV}  --kv-engine {name} --kv-path {secret} --kv-path {secret} (optional: --output {env|json} --output-file {path/to/filename.[env|json]} --ca-cert {path/to/cacert.pem} --no-verify -i/--identifier {username or roleID} -s/--secret {roleSecret or Password})