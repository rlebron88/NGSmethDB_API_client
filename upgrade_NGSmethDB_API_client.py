#!/usr/bin/env python3

'''
NGSmethDB website: http://bioinfo2.ugr.es:8080/NGSmethDB/
'''

import os, subprocess, requests, dialog, PyZenity

display = 'DISPLAY' in os.environ
local = [int(i) for i in str(subprocess.Popen(['python3', '/opt/NGSmethDB_API_client/NGSmethDB_API_client.py', '--version'], stdout = subprocess.PIPE).communicate()[0]).strip().split(' ')[-1][:-3].split('.')]
url = 'http://bioinfo2.ugr.es:8888/NGSmethAPI/version'
n = 0
while True:
    try:
        res = requests.get(url)
        break
    except:
        n += 1
        if n < retries:
            logger.warning('Internet connection failed. Retrying...')
        else:
            logger.critical('Unable to connect to the Internet! Leaving the program...')
            raise SystemExit
if res.status_code != 200:
    logger.error('API Error: ' + str(res.status_code))
    logger.critical('Unable to reach the NGSmethDB API Server! Leaving the program...')
    raise SystemExit
data = res.json()
remote = data[0]['NGSmethDB_API_client']
changes = local < remote

if changes:
    if display:
        try:
            res = PyZenity.Question('There is an update of NGSmethDB API Client. Do you want to upgrade it?')
            if res:
                os.system('cd /opt/NGSmethDB_API_client && git pull && sudo cp /opt/NGSmethDB_API_client/NGSmethDB_API_client.py /usr/local/bin/NGSmethDB_API_client && sudo chmod +x /usr/local/bin/NGSmethDB_API_client')
                PyZenity.InfoMessage('NGSmethDB API Client Upgraded!')
        except:
            res = dialog.Dialog().yesno(title = 'NGSmethDB API Client', text = 'There is an update of NGSmethDB API Client. Do you want to upgrade it?')
            if res:
                os.system('cd /opt/NGSmethDB_API_client && git pull && sudo cp /opt/NGSmethDB_API_client/NGSmethDB_API_client.py /usr/local/bin/NGSmethDB_API_client && sudo chmod +x /usr/local/bin/NGSmethDB_API_client')
                dialog.Dialog().InfoMessage(text = 'NGSmethDB API Client Upgraded!')
    else:
        res = dialog.Dialog().yesno(title = 'NGSmethDB API Client', text = 'There is an update of NGSmethDB API Client. Do you want to upgrade it?')
        if res:
            os.system('cd /opt/NGSmethDB_API_client && git pull && sudo cp /opt/NGSmethDB_API_client/NGSmethDB_API_client.py /usr/local/bin/NGSmethDB_API_client && sudo chmod +x /usr/local/bin/NGSmethDB_API_client')
            dialog.Dialog().InfoMessage(text = 'NGSmethDB API Client Upgraded!')
