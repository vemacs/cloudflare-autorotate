from pyflare import PyflareClient
import mcstatus, yaml

with open('config.yml', 'r') as cfg_file:
    config = yaml.load(cfg_file)

email = config['email']
api_key = config['api-key']
domain = config['domain']
ip_pool = config['ips']
entry = config['entry']

cf = PyflareClient(email, api_key)

def get_slp_results(ips):
    results = {}
    for ip in ips:
        status = mcstatus.McServer(ip, '25565')
        status.Update()
        results[ip] = status.available
    return results

def get_records_for_name(name):
    records = {}
    response = cf.rec_load_all(domain)
    for entry in response:
        entry_name = entry['name']
        if entry_name == name:
            records[str(entry['display_content'])] = str(entry['rec_id'])
    return records

def update_entries_with_available(records, results):
    for ip in results.keys():
        if results[ip]:
            if ip not in records:
                print 'Adding ' + ip + ' to entries'
                cf.rec_new(domain, 'A', 'sub', ip)
        else:
            if ip in records:
                print 'Removing ' + ip + ' from entries (id ' + records[ip] +')'
                cf.rec_delete(domain, records[ip])
    for ip in records.keys():
        if ip not in results:
            print 'Removing obselete IP ' + ip + ' from entries (id ' + records[ip] +')'
            cf.rec_delete(domain, records[ip])

slp_results = get_slp_results(ip_pool)
cf_records = get_records_for_name(entry)

# print slp_results
# print cf_records

update_entries_with_available(cf_records, slp_results)
