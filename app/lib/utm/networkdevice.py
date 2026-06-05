import re
import ipaddress
import os
import sys
import time
from telnetlib import Telnet
import pexpect
from collections import OrderedDict
import os
import requests
import json
import urllib3
import paramiko
import subprocess

from pprint import pprint
# from runner.settings import logger


class NetworkDevice:
    '''
     class NetworkDevice: Operation for device like: Switch, PowerControl, PC, Firewall
    '''
    default_options = {
        'console_ip': '',
        'console_port': '',
        'console_user': 'admin',
        'console_password': 'password',
        ###power part
        'power_type': 'None',
        'power_ip': '',
        'power_port': '',
        'power_user': 'admin',
        'power_password': 'password',
        ###switch part
        'switch_type': 'None',
        'switch_ip': '',
        'switch_user': 'admin',
        'switch_password': 'password',
    }

    def __init__(self, ip, user='admin', password='password', new_password='password', wrong_password='Admin@123456789',
                 soniccore_user='techsupport', soniccore_pwd='sonicwall-504', device='none', console_ip='',
                 console_port='', supported_config_mode='cli-ssh', check_login='', **kwargs):
        super().__init__(**kwargs)
        self.ip = ip
        self.user = user
        self.password = password
        self.wrong_password = wrong_password
        self.new_password = new_password
        self.soniccore_user = soniccore_user
        self.soniccore_pwd = soniccore_pwd
        self.console_ip = console_ip
        self.console_port = console_port
        self.supported_config_mode = supported_config_mode
        self.check_login = check_login
        self.options = dict(NetworkDevice.default_options)
        self.options.update(kwargs)

    def __getitem__(self, key):
        return self.options[key]

    def login(self):
        pass

    def power(self, type, device, action, port_num):
        pass

    def console(self, ):
        pass

    def close(self):
        pass


class Switch(NetworkDevice):
    def __init__(self, ip, user='admin', password='password', model='none', type='none'):
        super().__init__(ip, user='admin', password='password')
        self.model = model
        self.type = type

    def config_vlan(self, vlan_id, port, tag):
        pass

    def config_port(self, port, action):
        pass


class Host(NetworkDevice):
    def __init__(self, ip, user='root', password='password'):
        super().__init__(ip, user='root', password='password')
        if self.ip.lower() != 'localhost':
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=ip, port=22, username=self.user, password=self.password)

    def start_service(self, *services):
        for service in services:
            cmd = 'service ' + service + ' start'
            if self.ip.lower() != 'localhost':
                print('Exec cmd: ' + cmd)
                self.ssh.exec_command('service ' + service + ' start')
            else:
                os.system(cmd)

    def stop_service(self, *services):
        for service in services:
            cmd = 'service ' + service + ' stop'
            print('Exec cmd: ' + cmd)
            if self.ip.lower() != 'localhost':
                self.ssh.exec_command('service ' + service + ' start')
            else:
                os.system(cmd)

    def start_DHCPv4_server(self, conf_file='/etc/dhcp/dhcpd.conf'):
        print("Backup /etc/dhcp/dhcpd.conf")
        self.send_command(f"mv /etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf.bak")
        self.send_command(f"cp {conf_file} /etc/dhcp/dhcpd.conf")
        print('Start dhcpd service')
        self.send_command(f"service dhcpd start")
        result = self.send_command(f"service dhcpd status")
        if re.search('dhcpd.*running', result, re.I):
            print('start dhcpd service sucessfully.')
            return True
        print('start dhcpd service unsucessfully.')
        return False

    def stop_DHCPv4_server(self, conf_file='/etc/dhcp/dhcpd.conf'):
        print('Stop dhcpd service')
        self.send_command(f"service dhcpd stop")
        print("Move back /etc/dhcp/dhcpd.conf")
        self.send_command(f"mv /etc/dhcp/dhcpd.conf.bak /etc/dhcp/dhcpd.conf")
        return True

    def start_DHCP_server(self):
        cmd = 'nohup /usr/local/sbin/dibbler-server start 1>&2'
        self.send_command(cmd)
        result = self.send_command('ps aux|grep dibbler')
        if re.search(r'dibbler-server start', result, re.I):
            print('dibbler server start successfully.')
            return True
        return False

    def stop_DHCP_server(self):
        pid = self.get_exe_lnx('/usr/local/sbin/dibbler-server', 'start')
        if pid:
            self.send_command(f'kill -9 {pid}')
            time.sleep(1)
        else:
            print('dibbler server has been killed')
        return True

    def start_PPPoE_server(self, interface=None, local_ip=None, assign_ip=None, ppp_secrets="/etc/ppp/pap-secrets",
                           pppoe_option="/etc/ppp/pppoe-server-options"):
        if not interface or not local_ip or not assign_ip:
            print("Should define interface,local ip,assign ip for pppoe server!")
            return False
        print("Backup /etc/ppp/pap-secrets and /etc/ppp/pppoe-server-options")
        self.send_command(f"mv /etc/ppp/pap-secrets /etc/ppp/pap-secrets.bak")
        self.send_command(f"mv  /etc/ppp/pppoe-server-options /etc/ppp/pppoe-server-options.bak")
        print(f"Copy {ppp_secrets} {pppoe_option} to /etc/ppp")
        self.send_command(f"cp -f {ppp_secrets} /etc/ppp/")
        self.send_command(f"cp -f {pppoe_option} /etc/ppp/")
        print("Stop PPPoE server.")
        self.send_command("pkill pppoe-server")
        print(f"Start PPPoE server...cmd:pppoe-server -I {interface} -L {local_ip} -R {assign_ip} -N 5")
        self.send_command(f"pppoe-server -I {interface} -L {local_ip} -R {assign_ip} -N 5")
        return True

    def stop_PPPoE_server(self):
        print("Stop PPPoE server.")
        self.send_command("pkill pppoe-server")
        print("Restore /etc/ppp/options.pptpd,/etc/ppp/pap-secrets")
        self.send_command("mv -f /etc/ppp/options.pptpd.bak /etc/ppp/options.pptpd")
        self.send_command("mv -f /etc/ppp/pap-secrets.bak /etc/ppp/pap-secrets")
        return True

    def start_HTTPS_server(self, conf_path=None):
        if not conf_path:
            print('Please specify conf_path for your https server.')
            return False
        self.send_command(f"cp -rf {conf_path}/nginx/nginx-1.11.5 /usr/local/")
        self.send_command(
            f"cd /usr/local/nginx-1.11.5;pwd;bash ./configure --with-http_ssl_module --without-http_rewrite_module;make;make install")
        self.send_command(f"cp -rf {conf_path}/nginx/33iq* /usr/local/nginx/conf/")
        self.send_command(f"cp -f {conf_path}/nginx/nginx.conf /usr/local/nginx/conf/")
        self.send_command(f"cp -f {conf_path}/nginx/hello.html /usr/local/nginx/html/")
        self.send_command(f"cd /usr/local/nginx/")
        self.send_command(f"mkdir download")
        self.send_command(f"cd download")
        self.send_command(f"cp -f {conf_path}/files/download.file")
        self.send_command(f"/usr/local/nginx/sbin/nginx -s stop")
        self.send_command(f"/usr/local/nginx/sbin/nginx")
        print("------Make sure https server start on target PC.")
        result = self.send_command("netstat -nlp|grep :443|awk {'print $7'}")
        if not result:
            print('start nginx failed: ')
            return False
        return True

    def get_exe_lnx(self, exe_name, cmd):
        results = self.send_command(f'ps aux | grep {exe_name}')
        try:
            for result in re.split(r'\n', results):
                pattern = re.split(r'\s+', result)
                if patten[10] == exe_name and pattern[11] == cmd:
                    return pattern[1]
        except:
            print(f'Does not find {exe_name}')

    def config_IPv6_ip(self, ip=None, prefix=None, interface=None):
        try:
            return self.send_command(f'ifconfig {interface}  inet6 add {ip}/{prefix}')
        except Expection as e:
            print(f'Send command fail: {e}')
        return False

    def delete_IPv6_ip(self, ip=None, prefix=None, interface=None):
        try:
            self.send_command(f'ifconfig {interface}  inet6 del {ip}/{prefix}')
        except Expection as e:
            print(f'Send command fail: {e}')
        return False

    def config_IPv6_route(self, route=None, prefix=None, gw=None):
        try:
            return self.send_command(f'route -A inet6 add {route}/{prefix} gw {gw}')
        except Expection as e:
            print(f'Send command fail: {e}')
        return False

    def delete_IPv6_route(self, route=None, prefix=None, gw=None):
        try:
            return self.send_command(f'route -A inet6 del {route}/{prefix} gw {gw}')
        except Expection as e:
            print(f'Send command fail: {e}')
        return False

    def ping(self, ip, num=5):
        result = self.send_command(f'ping -c {num} {ip}')
        print(result)
        if re.search("100% packet loss", result, re.I):
            return False
        else:
            return True

    def ping_from_eth(self, ip, eth, num=5):
        result = self.send_command(f'ping -I {eth} -c {num} {ip}')
        print(result)
        if re.search("100% packet loss", result, re.I):
            return False
        else:
            return True

    def ping6(self, ip, num=5):
        result = self.send_command(f'ping6 -c {num} {ip}')
        print(result)
        if re.search("Network is unreachable", result, re.I):
            return False
        else:
            return True

    def send_command(self, cmd, backend=False):
        print('Send command ' + cmd)
        if self.ip.lower() != 'localhost':
            if backend:
                stdin, stdout, stderr = self.ssh.exec_command(cmd + ' 1>&2', get_pty=True)
            else:
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
            result = stdout.read()
            if result:
                print(result)
            else:
                result = stderr.read()
                print(result)
            result = str(result, encoding="utf-8")
        else:
            result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0].decode('ASCII')
        return str(result)

    def system(self, cmd, backend=False):
        print('Send command ' + cmd)
        if self.ip.lower() != 'localhost':
            if backend:
                stdin, stdout, stderr = self.ssh.exec_command(cmd + ' 1>&2', get_pty=True)
            else:
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
            result = stdout.read()
            if result:
                print(result)
            else:
                result = stderr.read()
                print(result)
        else:
            result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
        return result

    # cmds is list: ['pwd', 'cd /var', 'cd www', 'cd html', 'pwd']
    def send_commands(self, cmds, backend=False):
        print(f'cmds list: {cmds}')
        shell_cmds = ''
        for cmd in cmds:
            shell_cmds += cmd + ';'
        print(f'real shell cmds: {shell_cmds}')
        if self.ip.lower() != 'localhost':
            if backend:
                stdin, stdout, stderr = self.ssh.exec_command(shell_cmds + ' 1>&2', get_pty=True)
            else:
                stdin, stdout, stderr = self.ssh.exec_command(shell_cmds)
            result = stdout.read().decode(encoding="utf-8")
            if result:
                print(f'stdout result: {result}')
            else:
                result = stderr.read().decode(encoding="utf-8")
                print(f'stderr result: {result}')
            return result
        else:
            result = subprocess.check_output(shell_cmds, shell=True, stderr=subprocess.STDOUT).decode(encoding="utf-8")
            return result


class Power(NetworkDevice):
    def __init__(self, ip, model='none', type='', **kwargs):
        super().__init__(ip, **kwargs)
        self.model = model
        self.type = type

    #        self.power =

    def power_on(self, port_num):
        action = 'on'
        outlet = port_num
        pass

    def power_off(self, port_num):
        action = 'off'
        pass

    def power_cycle(self, port):
        action = 'cycle'
        pass
