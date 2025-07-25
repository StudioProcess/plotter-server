# Dynamic DNS and SSL Certificate Downloader using the Porkbun API

import json
import requests
import os

CONFIG_FILE = 'porkbun.config.json'
FORCE_UPDATE_DNS = False

def get_lanip():
    import socket
    ipaddrlist = socket.gethostbyname_ex(socket.gethostname())[2]
    if len(ipaddrlist) == 0 or ipaddrlist[-1] == '127.0.0.1':
        return None
    return ipaddrlist[-1]
    
def get_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Porkbun (DNS Service) config file is missing: {CONFIG_FILE}")
        exit()
    with open(CONFIG_FILE) as f:
        api_config = json.load(f)
    return api_config
    
def get_records(domain):
    params = get_config()
    return requests.post(f'{params["endpoint"]}/dns/retrieve/{domain}', json=params).json()

def get_a_record(domain, subdomain):
    params = get_config()
    return requests.post(f'{params["endpoint"]}/dns/retrieveByNameType/{domain}/A/{subdomain}', json=params).json()

def update_a_record(domain, subdomain, a, ttl):
    params = get_config();
    params['content'] = a
    params['ttl'] = ttl
    return requests.post(f'{params["endpoint"]}/dns/editByNameType/{domain}/A/{subdomain}', json=params).json()
    
def get_cert_bundle(domain):
    params = get_config();
    return requests.post(f'{params["endpoint"]}/ssl/retrieve/{domain}', json=params).json()



def ddns_update(root_domain, subdomain, ttl):
    lanip = get_lanip()
    if not lanip:
        print('Couldn\'t get LAN IP')
        return False
    print('LAN IP:', lanip)
    
    res = get_a_record(root_domain, subdomain)
    if res['status'] == 'SUCCESS' and len(res['records']) > 0:
        if res['records'][0]['content'] == lanip and res['records'][0]['ttl'] == str(ttl) and not FORCE_UPDATE_DNS:
            print(f'DNS ok: {subdomain}.{root_domain} A={res["records"][0]["content"]} TTL={res["records"][0]["ttl"]}')
            return True
        else:
            print("Updating DNS...")
    else:
        print('Couldn\'t get DNS, trying to update...')
    
    res = update_a_record(root_domain, subdomain, lanip, ttl)
    # print(res)
    if res['status'] != 'SUCCESS':
        print(f'Couldn\'t update DNS:', res['message'])
        return False
    print(f'Updated DNS: {subdomain}.{root_domain} A={lanip} TTL={ttl}')
    return True

def cert_update(root_domain, ssl_outfile):
    res = get_cert_bundle(root_domain)
    if res['status'] != 'SUCCESS':
        print(f'Couldn\'t retrieve SSL certficate for {root_domain}')
        return False
    pem_file = os.path.join( os.path.dirname(__file__), ssl_outfile )
    with open(pem_file, 'w') as f:
        f.write(res['certificatechain'])
        f.write('\n\n')
        f.write(res['privatekey'])
    print(f'Updated certificate: {ssl_outfile}')
    return True
