#!/usr/bin/env bash

quit() {
    >&2 echo 'Shutting down frpc.sh...'
    pkill -P $$ # kill all child processes
    exit 0
}
trap quit EXIT

>&2 echo "Plotter URL (via frp): wss://plotter.process.tools"
source ./frp.auth # read auth token from file
export FRP_AUTH_TOKEN
frpc -c frpc.toml
