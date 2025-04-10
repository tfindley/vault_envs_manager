# VEM - Vault Envs Manager

This script will manage your environmental variables (envs) by pulling them from a Hashicorp Vault key/value (kv) secrets engine.

## Requirements

Compatible with Linux/MacOS only - Windows users, please use WSL

## Command Options

To see available authentication methods, run `./main.py --help`

### Vault Address Options

| Flag            | Option | ENV Variable | Description                                                     |
| --------------- | ------ | ------------ | --------------------------------------------------------------- |
| --vault-addr    |        | VAULT_ADDR   | Address of the Vault server (default: http://127.0.0.1:8200)    |
| --ca-cert       |        |              | Path to a custom CA certificate for TLS verification            |
| --no-verify     |        |              | Disable TLS verification (insecure)                             |

### Token Authentication Method Options

To see all options for Token Authentication Method, run `./main.py token --help`

| Flag            | Option | ENV Variable | Description                                                     |
| --------------- | ------ | ------------ | --------------------------------------------------------------- |
| --token         | -t     | VAULT_TOKEN  | Token                                                           |

Example:

```bash
./main.py token \
  --token $VAULT_TOKEN \
  --kv-engine kv_name \
  --kv-path testenv \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem
```

### UserPass Authenticaiton Method Options

To see all options for UserPass Authentication Method, run `./main.py userpass --help`

To see all options, run `./main.py token --help`

| Flag            | Option | ENV Variable | Description                                                     |
| --------------- | ------ | ------------ | --------------------------------------------------------------- |
| --identifier    | -i     |              | Username                                                        |
| --secret        | -s     |              | Password                                                        |
| --mfa-path      |        |              | Multifactor Authentication path (if user)                       |
| --mfa-code      |        |              | Multifactor Authentication code (if used)                       |

```bash
./main.py userpass \
  -i username \
  -s password \
  --kv-engine kv_name \
  --kv-path testenv \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem
```

### AppRole Authentication Method Options

To see all options for AppRole Authentication Method, run `./main.py approle --help`

| Flag            | Option | ENV Variable | Description                                                     |
| --------------- | ------ | ------------ | --------------------------------------------------------------- |
| --identifier    | -i     |              | RoleID Identifier                                               |
| --secret        | -s     |              | Secret ID                                                       |

```bash
./main.py approle \
  -i $ROLE_ID \
  -s $SECRET_ID \
  --kv-engine kv_name \
  --kv-path testenv \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert ~/certs/ca.pem
```

### Options

| Flag            | Option | ENV Variable | Description                                                     |
| --------------- | ------ | ------------ | --------------------------------------------------------------- |
| --kv-engine     |        |              | Mount point of the KV v2 secrets engine (e.g., kv_user_tristan) |
| --kv-path       |        |              | Secret path (can be passed multiple times for merging)          |
| --env-token-var |        |              | Name of an env variable to export the Vault token into          |
| --output        |        |              | Output format: env, json, none                                  |
| --output-file   |        |              | Optional file to write the output                               |

```bash
./main.py userpass \
  -i username \
  -s password \
  --vault-addr https://vault.example.com:8200 \
  --kv-engine kv_name \
  --kv-path testenv \
  --env-token-var VAULT_TOKEN \
  --output env \
  --output-file /etc/default/servicename
```

## Walkthrough

GIT clone the above repo to a path of your choosing. Ideally place it somewhere from your home directory (like ~/vem)

Once cloned, cd into the directory and create your Python Virtual Environment. run:

```bash
python3 -m venv .venv
```

Now activate the environment and install the required python packages using pip, then finally deactivate the environment.

**Note:** there is a leading . on the first command - be sure not to miss it if you're not copy/pasting the commands 

```bash
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

Now you need to modify the first line of the python script (`main.py`) to point to your new python3 version in the venv. If you have cloned the repo to ~/vem, the full path to the new python binary would be: `/home/username/vem/.venv/bin/python3`. To find yours, just run `pwd` (print working directory).

Edit the `main.py` in your favourite text editor, and replace the `#!` line with the new path. so from the original `#!/usr/bin/env python3` to `#!/home/username/vem/.venv/bin/python3`

Now that's done, you need to make the `main.py` executable

```bash
chmod +x main.py
```

Now you can give it a quick test-run by running `./main.py`, and you should see the following output:

```bash
$ ./main.py
usage: main.py [-h] {userpass,token,approle} ...
main.py: error: the following arguments are required: auth_method
```

This mean's its working as expeted. 

### Creating your Envs

So now where do you store your secure key/value pairs?

Log into vault using the userpass method at: https://vault.example.com:8200

While you're here, if you don't already have it somewhere on your system, download the root and intermediate CA's from below the same directory as the python script as cacert.pem. This is needed because Python doesn't always use the systems ca store.

Now you're logged into Vault, look for the secret engine: kv_user/<login_id> . so mine will be kv_user/tristan.findley. If you don't have one yet, let me know and I'll create one for you. Don't worry, only you can see your secrets that are stored in here. No-one else has access.

Open this kv secret engine. In here you can create a secret. For now, call it testing. In this secret, you need to create key/value pairs. Create the following test data:

```plaintext
KEY1: VALUE1
KEY2: VALUE2
```

That's it! This is how you will be storing your secret key/values that you'll want to populate your envs with.

### Retrieving Secrets

Now you have some secrets to store, it's time to get them into your environment. First we'll run the app to just display the secrets. once we validate we're getting them correctly we'll populate our shell with them.



use the following code to display your secrets from Vault. When you run this, you will be prompted for your password.

**WARNING:** Be sure to change the kv-engine value and -i value in the example below. Also update the full path for the ca-cert.

```bash
./main.py userpass \
  --kv-engine kv_user/tristan.findley \
  --kv-path testing \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert /home/tristan/vem/cacert.pem \
  --env-token-var VAULT_TOKEN --output env -i tristan.findley
```

If this runs correctly, this should display the following output:

```plaintext
KEY1='VALUE1'
KEY2='VALUE2'
VAULT_TOKEN='hvs.YourTokenValue'
```

Excellent! that's all working.

Note that your Vault token is also exported. If you wish to change the var name for this, use `--env-token-var newvarname`

In order to get these into your environment, you need to wrap this in an `eval` string and drop the `--output` flag. Use the following example, being sure to replace the same variables as you did previously:

```bash
eval $(./main.py userpass \
  --kv-engine kv_user/tristan.findley \
  --kv-path testing \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert /home/tristan/vem/cacert.pem \
  --env-token-var VAULT_TOKEN -i tristan.findley)
```

If this worked correctly, you should see no output (except for the password prompt)

To check it worked, run the command env. you should see your environmental variables are now set!

### Going forward

Now it's working in test, you can create a new secret in your Vault KV engine and populate it with real keys/values.


If you want to call multiple key/value secrets, you can. just add more `--kv-path` flags. they will load in the order you provide them, so if you have variables of the same name in multiple paths, the latter ones will overwrite the former ones.

## FAQ

**Q: Can this be used to securely generate environment files?**

**A:** Yes. there's an `--output-file` flag that can be used. just set the `--output` flag to env. e.g: `--output env --output-file environment.env` (be sure not to run it inside eval)

**Q: Can this be automated?**

**A:** Yes - I have built in support for auth ID and auth Secret, though I haven't fully tested or documented this yet. Coming soon!



**Q: Can i pass my password to it in the command line?**

**A:** Yes - though be warned this is insecure (Unless you're wrapping it in a script and injecting the password through another method). use `-s` to do this.

e.g: `-i username -s password`

This is the same for roleid and role secret.

**Q: I already have my Vault Token. Can't I just use that?**

**A:** Yes, but in most Vault deployments your vault token will expire.

To use a token, change the auth method from userpass to token and pass the token using -t

e.g:

```bash
token \
  --kv-engine kv_name \
  --kv-path testing \
  --vault-addr https://vault.example.com:8200 \
  --ca-cert /home/username/vem/cacert.pem \
  -t "$VAULT_TOKEN" \
  --env-token-var VAULT_TOKEN2 --output json --output-file test2.json
```

**Q: What does `--env-token-var` do?**

**A:** This is used to change the variable name that your Vault Token is exported to. e.g: `--env-token-var newvarname`