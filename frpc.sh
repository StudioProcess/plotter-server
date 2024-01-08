#!/usr/bin/env bash

quit() {
    >&2 echo 'Shutting down frpc.sh...'
    pkill -P $$ # kill all child processes
    exit 0
}
trap quit EXIT

echo "Plotter URL (via frp): wss://plotter.process.studio:8000"
frpc -c frpc.toml
