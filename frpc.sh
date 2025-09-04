#!/usr/bin/env bash

quit() {
    >&2 echo 'Shutting down frpc.sh...'
    pkill -P $$ # kill all child processes
    exit 0
}
trap quit EXIT

# find frpc
frpc=$(which "frpc")
if [[ -z $frpc ]]; then
    frpc=$(which "../frp-mac/latest/frpc")
    if [[ -z $frpc ]]; then
        >&2 echo "Error: frpc not found; Try installing with 'brew install frpc'"
        exit 1
    fi
fi

if [[ ! -f ./frp.auth ]]; then
    >&2 echo "Error: Missing frp auth file: frp.auth"
    exit 1
fi

source frp.auth # read auth token from file
export FRP_AUTH_TOKEN

>&2 echo "Using frpc: $frpc"
>&2 echo "Plotter URL (via frp): wss://plotter.process.tools"

$frpc -c frpc.toml
