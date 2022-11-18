import zeroconf

zc = None

def get_lanip():
    import socket
    ipaddrlist = socket.gethostbyname_ex(socket.gethostname())[2]
    if len(ipaddrlist) == 0 or ipaddrlist[-1] == '127.0.0.1':
        return None
    return ipaddrlist[-1]

def add_zeroconf_service(hostname, port):
    global zc
    # print('Registering zeroconf service...')
    lanip = get_lanip()
    if lanip == None:
        print('Zeroconf couldn\'t get local LAN IP')
        return False
    service_info = zeroconf.ServiceInfo(
        "_ws._tcp.local.",
        f'{hostname}._ws._tcp.local.',
        addresses=[lanip],
        port=port,
        server=f"{hostname}.local."
    )
    zc = zeroconf.Zeroconf()
    zc.register_service(service_info)
    print(f'Zeroconf: Registered {hostname}.local -> {lanip} (Port {port})')

def remove_zeroconf_service():
    if zc != None: 
        print('Unregistering zeroconf service...')
        zc.unregister_all_services()
