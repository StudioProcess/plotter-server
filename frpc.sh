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
    frpc=$(which "../frp-mac/latest/frpcx")
    if [[ -z $frpc ]]; then
        >&2 echo "frpc not found; try installing with 'brew install frpc'"
        exit 1
    fi
fi

>&2 echo "Using frpc: $frpc"
>&2 echo "Plotter URL (via frp): wss://plotter.process.tools"
source frp.auth # read auth token from file
export FRP_AUTH_TOKEN

$frpc -c frpc.toml
