#!/usr/bin/env python
import re, time, os
from ..lib.utm.utm import Firewall
from .mongodb import mongo

utm_new_pwd = 'Sonicwall2023@QA'
loginprompt = '[$#>:]'
prompts = '[>#]'


def LongTasksLog(type, device, operated, snname):
    db = mongo()
    dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
    deshdata = {'svname': snname, 'type': type, 'device': device,
                'operated': operated, 'time': dtime}
    db.insert_one('longtasklog', deshdata)


def Change_Access_Rule_Connection_Limit_v4(show_result):
    cmds = ['configure terminal']
    r1 = re.findall('uuid \S+', str(show_result))
    print('total get v4 access-rules is: %s' % len(r1))
    print('start set the ipv4 connection-limit...')
    for i in range(0, len(r1)):
        uuid = r1[i].split('\\r\\n')[0]
        print(uuid)
        cmds.append(f'access-rule ipv4 {uuid}')
        cmds.append('connection-limit source threshold 12800')
        cmds.append('connection-limit destination threshold 12800')
        cmds.append('exit')
        cmds.append('commit')
    return cmds


def Change_Access_Rule_Connection_Limit_v6(show_result):
    cmds = ['configure terminal']
    r1 = re.findall('uuid \S+', str(show_result))
    print('total get v6 access-rules is: %s' % len(r1))
    print('start set the ipv6 connection-limit...')
    for i in range(0, len(r1)):
        uuid = r1[i].split('\\r\\n')[0]
        print(uuid)
        cmds.append(f'access-rule ipv6 {uuid}')
        cmds.append('connection-limit source threshold 12800')
        cmds.append('connection-limit destination threshold 12800')
        cmds.append('exit')
    cmds.append('commit')
    return cmds


def fwndppconfig(fw_ip, console_ip, console_port, fw_user, fw_password, adeviceget, svname):
    print('start check fw login...')
    cmds = ['show version']
    fw_console = Firewall(fw_ip,
                          console_ip=console_ip,
                          console_port=console_port,
                          user=fw_user,
                          password=fw_password,
                          supported_config_mode='cli-console')
    (res, output) = fw_console.do_cli_commands(cmds, tag=1)
    if not res:
        return False
    print('end check fw login...')

    print('start configure ndpp...')
    output = {}
    r_fw_console = Firewall(fw_ip,
                            console_ip=console_ip,
                            console_port=console_port,
                            user=fw_user,
                            password=fw_password,
                            supported_config_mode='cli-console')

    fw_ssh = Firewall(fw_ip,
                            console_ip=console_ip,
                            console_port=console_port,
                            user=fw_user,
                            password=fw_password,
                            supported_config_mode='cli-ssh')

    # ssh-keygen -f "/root/.ssh/known_hosts" -R "10.8.105.150"
    os.system(f'ssh-keygen -f "/root/.ssh/known_hosts" -R "{fw_ip}"')

    print('configure NoPagerSession via console...')
    cmds = ['configure terminal', 'no cli pager default', 'no cli pager session', 'commit']
    output['NoPagerSession'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure NoPagerSession via console result: {output["NoPagerSession"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('enable X0 ssh in console...')
    cmds = ['configure terminal',
            'interface X0', 'management ssh', 'commit', 'exit',
            'interface X1', 'management ssh', 'commit', 'exit']
    output['interfaces'] = r_fw_console.do_cli_commands(cmds)
    operated = f'enable X0/X1 ssh in console result: {output["interfaces"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure Change_Access_Rule_Connection_Limit_v4 via ssh...')
    showcmd = ['show access-rules ipv4']
    try:
        showres = fw_ssh.do_cli_commands(showcmd, tag=1)
        v4_cmds = Change_Access_Rule_Connection_Limit_v4(showres)
        res = fw_ssh.do_cli_commands(v4_cmds)
    except:
        res = False
        print('configure Change_Access_Rule_Connection_Limit_v4 via ssh failed.')
    output['Change_Access_Rule_Connection_Limit_v4'] = res
    operated = f'Change_Access_Rule_Connection_Limit_v4 via ssh result: {res}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure Change_Access_Rule_Connection_Limit_v6 via console...')
    showcmd = ['show access-rules ipv6']
    try:
        showres = fw_ssh.do_cli_commands(showcmd, tag=1)
        cmds = Change_Access_Rule_Connection_Limit_v6(showres)
        res = fw_ssh.do_cli_commands(cmds)
    except:
        res = False
        print('configure Change_Access_Rule_Connection_Limit_v6 via ssh failed.')
    output['Change_Access_Rule_Connection_Limit_v6'] = res
    operated = f'Change_Access_Rule_Connection_Limit_v6 via console result: {res}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure TSR ike-info vpn-keys via console...')
    cmds = ['configure terminal', 'tech-support-report options', 'no ike-info', 'commit', 'exit']
    output['TSROption'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure TSR ike-info vpn-keys via console result: {output["TSROption"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure SetIPv6Advaced via console...')
    cmds = ['configure terminal', 'firewall', 'ipv6 drop reserved-address-packets', 'commit', 'exit']
    output['SetIPv6Advaced'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure SetIPv6Advaced via console result: {output["SetIPv6Advaced"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure Setsyslog via console...')
    cmds = ['configure terminal', 'vpn policy tunnel-interface syslog01', 'gateway primary 88.88.105.199',
            'auth-method shared-secret', 'shared-secret 99999999999999999999999999', 'exit',
            'proposal ike dh-group 14', 'proposal ike authentication sha-256', 'proposal ike encryption aes-256',
            'proposal ipsec encryption aes-256', 'proposal ipsec authentication sha-256',
            'exit', 'commit',
            # 'vpn policy tunnel-interface syslog01', 'proposal ipsec authentication sha-256', 'commit',
            'address-object ipv4 syslogsvr01 host 11.12.13.11 zone LAN',
            'log syslog',
            'server address name syslogsvr01 port 514 profile 0',
            # 'syslog-server server name syslogsvr01 port 514 profile 0',
            'outbound-interface syslog01',
            'local-interface X2', 'commit', 'exit', 'ndpp', 'commit',
            ]
    output['Setsyslog'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure SetIPv6Advaced via console result: {output["Setsyslog"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure DynamicClientProposal via console...')
    cmds = ['configure terminal', 'vpn', 'ikev2',
            'proposal dh-group 14', 'proposal authentication sha-256',
            'proposal encryption aes-256', 'commit', 'exit', ]
    output['DynamicClientProposal'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure SetIPv6Advaced via console result: {output["DynamicClientProposal"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure UserPolicyBanner via console...')
    cmds = ['configure terminal', 'user authentication', 'policy-banner content autotest',
            'policy-banner-before-login', 'commit', 'exit', ]
    output['UserPolicyBanner'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure UserPolicyBanner via console result: {output["UserPolicyBanner"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure tlsandabove via console...')
    cmds = ['configure terminal', 'administration', 'tls-and-above', 'commit', 'exit']
    output['tlsandabove'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure tlsandabove via console result: {output["tlsandabove"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure SelfCertificates via console...')
    cmds = ['configure terminal', 'certificates',
            'import ca-cert ftp ftp://10.8.255.104/xca/root_ca.cert.pem',
            'import ca-cert ftp ftp://10.8.255.104/xca/intermediate.cert.pem',
            'import cert-key-pair auto_2kcert password 123456 ftp ftp://10.8.255.104/xca/www.rsa2048.com.pfx',
            'import crl ca-name Alice\ Ltd\ Root\ CA directly ftp ftp://10.8.255.104/xca/root_3000_crl.pem',
            'import crl ca-name Alice\ Ltd\ Intermdeiate1ca\ CA directly ftp ftp://10.8.255.104/xca/intermediate_3000.crl.pem',
            'exit',
            # 'administration', 'web-management certificate name auto_2kcert', 'commit', 'cancel', 'exit',
            # 'ssl-vpn server', 'certificate name auto_2kcert', 'commit', 'exit'
            ]
    output['SelfCertificates'] = r_fw_console.do_cli_commands(cmds)
    if not output['SelfCertificates']:
        output['SelfCertificates'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure SelfCertificates via console result: {output["SelfCertificates"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)

    print('config web-management certificate name via console...')
    cmds = ['configure terminal', 'administration', 'web-management certificate name auto_2kcert', 'commit', 'exit']
    output['web_management'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure web-management certificate via console result: {output["web_management"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)

    print('config ssl-vpn server certificate name via console...')
    cmds = ['configure terminal', 'ssl-vpn server', 'certificate name auto_2kcert', 'commit', 'exit']
    output['ssl_vpn_server'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure ssl-vpn server certificate via console result: {output["ssl_vpn_server"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)

    print('configure sonicosapi via console...')
    cmds = ['configure terminal', 'administration', 'sonicos-api', 'rsa-key-size 2048', 'no chap',
            'no md5-digest', 'commit', 'exit']
    output['sonicosapi'] = r_fw_console.do_cli_commands(cmds)
    print(f'Configure sonicosapi via console result: {output["sonicosapi"]}')
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure interfaces via console...')
    cmds = ['configure terminal',
            'interface X0', 'no management ssh', 'no management snmp', 'commit', 'exit',
            'interface X1', 'no management ssh', 'no management snmp', 'management ping', 'management https', 'commit',
            'exit',
            'interface X2', 'no management ssh', 'no management snmp', 'commit', 'exit',
            'interface X3', 'no management ssh', 'no management snmp', 'commit', 'exit',
            ]
    output['interfaces'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure interfaces via console result: {output["interfaces"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    print('configure LoginSecurity via console...')
    cmds = ['configure terminal', 'administration',
            f'admin password old-password {fw_password} new-password {utm_new_pwd} confirm-password {utm_new_pwd}',
            'password enforce-character-difference',
            'password minimum-length 15',
            'password aging duration 90',
            'password complexity alpha-and-numeric-and-symbols',
            'password complexity digital 1',
            'password complexity lower-case 1',
            'password complexity symbolic 1',
            'password complexity upper-case 1',
            'commit', 'exit',
            'user authentication',
            'relogin-after-password-change',
            'commit', 'end', 'exit',
            ]
    output['LoginSecurity'] = r_fw_console.do_cli_commands(cmds)
    operated = f'Configure LoginSecurity via console result: {output["LoginSecurity"]}'
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    if output['LoginSecurity']:
        operated = f'the new login account is： admin/Sonicwall2023@QA'
        LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    else:
        operated = f'change login account password failed, Please change it manually.'
        LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)
    print('====================================================================================')

    operated = f'Run ndpp script finished, Please manual enable your ndpp. '
    LongTasksLog(adeviceget['DeviceType'], adeviceget['Product'], operated, svname)

    # cmds = ['configure terminal', 'ndpp', 'commit', 'yes']
    # r_fw_console.do_cli_commands(cmds)

    return output
