# Empty Nebius CLI Configuration

The default Docker Compose stack mounts this directory's placeholder
`config.yaml` and `credentials.yaml` files so Local Mock mode never reads a
developer's cloud credentials. File-level mounts leave the CLI installed at
`/root/.nebius/bin` visible inside a serverless-enabled backend image.

For real Nebius Serverless mode, set `NEBIUS_CLI_CONFIG_DIR` to the host
directory that contains `config.yaml` and `credentials.yaml` (normally
`$HOME/.nebius`) before starting Compose.
