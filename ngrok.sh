local_port=0 # use 0 for default ports (80 for http, 443 for https)
hostname=plotter.eu.ngrok.io

if [[ $1 == 'http' ]]; then
    # connect to local HTTP server (NOT HTTPS)
    [[ $local_port == 0 ]] && local_port=80
    ngrok http http://localhost:$local_port --hostname=$hostname
else
    [[ $local_port == 0 ]] && local_port=443
    ngrok http https://localhost:$local_port --hostname=$hostname
fi
