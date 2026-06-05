#!/usr/bin/env python
import re, time, random
from flask import current_app
from flask_login import current_user
from ..lib.fwlogin import ssh_login

loginprompt = '[$#>:]'
cert_pool = ['auto_httpsclient', 'auto_httpsserver', 'auto_self2k01', 'auto_self4k02', 'auto_self2k03']
cleartext = [' ', 'cleartext']

def zone_type_create():
    tmp_time = str(time.time())
    unid_ip = tmp_time.split('.')[0][-2:]
    ten_ip = tmp_time.split('.')[1][-2:]
    han_ip = tmp_time.split('.')[1][-4:-2]
    host_ipv4 = 'host 123.' + han_ip + '.' + ten_ip + '.' + unid_ip
    range_ipv4 = 'range 139.' + ten_ip + '.' + unid_ip + '.10 139.' + ten_ip + '.' + unid_ip + '.12'
    host_ipv6 = 'ipv6 host 1001:' + han_ip + ':' + ten_ip + '::' + unid_ip
    range_ipv6 = 'ipv6 range 1001:' + han_ip + ':' + ten_ip + ':' + unid_ip + '::10 1001:' + han_ip + ':' + ten_ip + ':' + unid_ip + '::20'
    fqdn_domain = 'fqdn auto' + han_ip + ten_ip + unid_ip + '.com'
    zone_pool = random.choice([host_ipv4, range_ipv4, host_ipv6, range_ipv6, fqdn_domain])
    #print(zone_pool)
    return zone_pool

def zone_type_pool():
    host_ipv4_pool = {}
    network_ipv4_pool = {}
    fqdn_pool = {}
    for j in range(0, 5):
        start_ip, start_network_ip, fqdn_start = zone_type_create()
        host_ipv4_pool[j] = 'host ' + start_ip
        network_ipv4_pool[j] = 'network ' + start_network_ip + ' 255.255.255.254'
        fqdn_pool[j] = 'fqdn ' + fqdn_start
    zone_pool = random.choice([host_ipv4_pool, network_ipv4_pool, fqdn_pool])
    print(zone_pool)
    return zone_pool

def add_cert(child):
    current_app.logger.warning(
        '[' + current_user.username + ']--Start add certs: auto_httpsclient,auto_httpsserver,auto_self2k01,auto_self4k02,auto_self2k03.')
    child.sendline('certificates')
    child.expect('#')
    child.sendline('import ca-cert ftp ftp://10.8.255.104/xca/xca-root.p7b')
    child.expect('#')
    child.sendline('import cert-key-pair auto_httpsclient password password ftp ftp://10.8.255.104/xca/httpsclient.p12')
    child.expect('#')
    child.sendline('import cert-key-pair auto_httpsserver password password ftp ftp://10.8.255.104/xca/qaserver.p12')
    child.expect('#')
    child.sendline('import cert-key-pair auto_self2k01 password password ftp ftp://10.8.255.104/xca/vlab-key1.p12')
    child.expect('#')
    child.sendline('import cert-key-pair auto_self4k02 password password ftp ftp://10.8.255.104/xca/vlab-key2.p12')
    child.expect('#')
    child.sendline('import cert-key-pair auto_self2k03 password password ftp ftp://10.8.255.104/xca/vlab-key3.p12')
    child.expect('#')
    child.sendline('exit')
    child.expect('#')
    '''
    child.sendline('show certificates status imported')
    child.expect('#')
    
    tmp = child.before.decode()
    sys_end_2_line = tmp.split('\r\n')[1:20]
    current_app.logger.warning(
        '[' + current_user.username + ']--show certificates status imported : \n %s' % sys_end_2_line)
    '''
    return child

def add_server_ssl(utm_ip, utm_user, utm_pwd):
    child = ssh_login(utm_ip, utm_user, utm_pwd)
    current_app.logger.warning('[' + current_user.username + ']--start add server ssl...')
    child.sendline('show certificates status imported')
    child.expect('#')
    cert_tmp = child.before.decode()
    if re.findall('auto_httpsclient' or 'auto_httpsserver' or 'auto_self2k01' or 'auto_self4k02' or 'auto_self2k03', cert_tmp):
        current_app.logger.warning('[' + current_user.username + ']--certificates had been added, skip add certs.')
    else:
        child = add_cert(child)
    child.sendline('dpi-ssl server')
    child.expect('#')

    for i in range(1, 70):
        zone_pool = zone_type_create()
        child.sendline('ssl-server %s certificate %s %s' % (zone_pool, random.choice(cert_pool), random.choice(cleartext)))
        child.expect(loginprompt)
        child.sendline('yes')
        child.expect('#')
        child.sendline('commit')
        child.expect('#')
        ssl_tmp = child.before.decode()
        #print('i-----------%s: %s' % (i, ssl_tmp))
        end_2_line = ssl_tmp.split('\r\n')[-2]
        current_app.logger.warning(
            '[' + current_user.username + ']--server ssl setting result %d: %s %s' % (i, zone_pool, end_2_line))

    child.sendline('exit')
    child.sendline('exit')
    current_app.logger.warning('[' + current_user.username + ']--server ssl setting successfully !')

