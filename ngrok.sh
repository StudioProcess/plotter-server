if [[ $1 == 'http' ]]; then
    # connect to local HTTP server
    ngrok http http://localhost:4321 --hostname=plotter-server.eu.ngrok.io
else
    
    ngrok http https://localhost:4321 --hostname=plotter-server.eu.ngrok.io
fi
