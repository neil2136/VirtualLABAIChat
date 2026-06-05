import re
import ipaddress
import os
import sys
import time
from collections import OrderedDict
import json
from pprint import pprint
from telnetlib import Telnet
import pexpect
import struct
import hashlib
from tcpping import tcpping
import requests
import urllib3
import subprocess
from requests.auth import HTTPDigestAuth

from .networkdevice import NetworkDevice
# from runner.settings import logger

# from modules.ui.fw_page import FWPage
# from modules.ui.change_password import FWChangePassword

G_PASSWORD = None
new_password = 'password2'
# G_PASSWORD_NEW = 'sonicauto'
G_PASSWORD_NEW = 'S0nicw@ll'
password2 = 'password2'
password3 = 'sonicwall'
# password3 = 'P@ssw0rd'
password4 = 'cdpQa123!@#'
ndpp_password = 'Sonicwall2023@QA'
console_user = 'qa'
console_pwd = 'qa'


# def change_password(new_password=G_PASSWORD_NEW):
#     nav = FWChangePassword(new_password=new_password)
#     nav.change_password(login_type='after_resotre')


# def enable_ssh(ip):
#     fw = FirewallCLI(ip, supported_config_mode='cli-ssh')
#     commands = ['configure', 'dns server inherit', 'commit', 'end']
#     ui_obj = FWPage()
#     for each in range(0, 5):
#         if ui_obj.enable_ssh_for_x0_interface():
#             print('Change DNS to inherit')
#             fw.do_cli_commands(commands)
#             return True
#         print('Sleep 5s for try enable ssh again.')
#         time.sleep(5)
#
#     return False


def is_Firewall_up(ip='192.168.168.168', max=80, console_ip='', console_port='', ssh=True, mode='ping', mode_port=443,
                   pre_sleep=240):
    global G_PASSWORD
    if pre_sleep > 0:
        print(f'Sleep {pre_sleep}s for firewall up.')
        time.sleep(int(pre_sleep))
    reboot_check = False
    for each in range(0, max):
        sleep_time = 30
        if mode == 'ping':
            print(f'start ping fw wan ip {ip}')
            output = os.system('ping ' + ip + ' -c 1 -w 1')
            print('111111111111111111')
            print(output)
            print('22222222222222222')
        elif mode == 'tcp':
            output = not tcpping(ip, mode_port)
        elif mode == 'console':
            fw_ssh = FirewallCLI(ip, user='qa', console_ip=console_ip, console_port=console_port,
                                 password='qa', supported_config_mode='cli-console')
            output, rc = fw_ssh.cli_login(1)
            output = not output
            if not output:
                status = fw_ssh.do_cli_command('show version')
                if 'NSsp 15700' in status:
                    commands = ['configure', 'security-policy ipv4 uuid 0000', 'name any-to-X0', 'source address any',
                                'destination address name X0\ IP', 'action allow', 'action-profile Default\ Profile',
                                'commit', 'end']
                    rc = fw_ssh.do_cli_commands(commands)
            fw_ssh.cli_logout()
        # rc = 0
        # rc1 = True
        # if not output:
        #     if not reboot_check:
        #         reboot_check = True
        #         time.sleep(sleep_time * 2)
        #         continue
        #     print('Firewall is up.')
        #     # fw_ssh = FirewallCLI(ip, user='admin', password='password', supported_config_mode='cli-ssh')
        #     # if console_ip and console_port:
        #     if ssh:
        #         cmd = '/usr/local/node/bin/newman run ' + os.environ[
        #             "PYTHON_COMMON_HOME"] + '/config/enable_ssh.json -k --disable-unicode --delay-request 1200'
        #         cmd1 = '/usr/local/node/bin/newman run ' + os.environ[
        #             "PYTHON_COMMON_HOME"] + '/config/enable_ssh_newpass.json -k --disable-unicode --delay-request 1200'
        #         for i in range(0, 2):
        #             print("enable ssh by api\n")
        #             print(cmd)
        #             cmd_return = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate(timeout=100)[
        #                 0].decode('ASCII')
        #             if re.search(r'Login Your default password must be changed', cmd_return, re.I):
        #                 print(
        #                     f'Firewall enforce to change default password, try to change password to {G_PASSWORD_NEW}')
        #                 # change_password(new_password=G_PASSWORD_NEW)
        #                 G_PASSWORD = True  # True means default password change to sonicauto
        #                 print(f'is_firewall_up: ')
        #                 print(G_PASSWORD)
        #                 print(cmd1)
        #                 rc = os.system(cmd1)
        #                 if rc != 0:
        #                     rc = os.system(cmd1)
        #             elif re.search(r'DigestAuthLoginAdmin.*401 Unauthorized', cmd_return, re.I | re.S):
        #                 G_PASSWORD = True  # True means default password change to sonicauto
        #                 print(cmd1)
        #                 rc = os.system(cmd1)
        #                 if rc != 0:
        #                     rc = os.system(cmd1)
        #             else:
        #                 G_PASSWORD = None
        #             time.sleep(10)
        #             fw = Firewall(ip, supported_config_mode='cli-ssh')
        #             if G_PASSWORD:
        #                 fw.new_password = 'sonicauto'
        #             #####1
        #             commands = ['configure', 'dns server inherit', 'commit', 'log categories', 'logging-level debug',
        #                         'commit', 'end', 'end']
        #             print('Change DNS to inherit')
        #             rc1 = fw.do_cli_commands(commands)
        #             if rc1:
        #                 break
        #             else:
        #                 print(cmd_return)
        #     if (rc != 0 or not rc1):
        #         return False
        #     return True
        print('Sleep {}s for firewall up.'.format(sleep_time))
        time.sleep(sleep_time)
        if each == max - 1:
            print('Firewall not up after {}s'.format((each + 1) * sleep_time))
            return False
    return True


def is_ipv4(ip):
    try:
        if ipaddress.IPv4Address(ip).version == 4:
            return True
    except:
        # ValueError
        print(ip, " is not an IPv4 addr")


class FirewallCLI(NetworkDevice):
    def __init__(self, ip, prompt='>', cli_port='22', cli_encr='', cli_compr=False, mac_spec='', option='',
                 other='', ssh_version=2, logfile='/tmp/snwlssh.log', soniccore=None, blade=1, **kwargs):
        super().__init__(ip, **kwargs)
        self.prompt = prompt
        self.cfgPrompt = "config\(.*\)\# "
        self.genPrompt = "\(.*\)\# "
        self.logfile = logfile
        self.ctrl_code = ''
        self.cli_port = cli_port
        self.cli_encr = cli_encr
        self.cli_compr = cli_compr
        self.mac_spec = mac_spec
        self.ssh_version = ssh_version
        self.option = option
        self.other = other
        self.soniccore = soniccore
        self.blade = blade

    def cli_login(self, errcode=0):
        if self.supported_config_mode == 'cli-ssh':
            return self.ssh_connect(errcode)
        elif self.supported_config_mode == 'cli-console':
            return self.console_connect(errcode)
        else:
            print('Make sure supported_config_mode is one of cli-ssh,cli-console')

    def cli_logout(self):
        if re.search('console', self.supported_config_mode, re.I):
            self.ssh.sendcontrol(']')
        self.ssh.close()

    def ssh_connect(self, errcode=0):
        os.system('sed -i ' + '\'' + '/' + self.ip + '/' + ' d' + '\'' + ' /root/.ssh/known_hosts')
        newSsh = "Are you sure you want to continue connecting"
        cmd = 'ssh -l ' + self.user + ' ' + self.ip
        if self.cli_port != '' and self.cli_port != '22':
            cmd = cmd + ' -p ' + str(self.cli_port)
        if self.cli_encr != '':
            cmd = cmd + ' -c ' + str(self.cli_encr)
        if self.cli_compr:
            cmd = cmd + ' -C'
        if self.mac_spec != '':
            cmd = cmd + ' -m ' + str(self.mac_spec)
        if self.ssh_version == 1:
            cmd = cmd + ' -1'
        if self.option:
            cmd = cmd + ' -o ' + str(self.option)
        if self.other:
            cmd = cmd + ' ' + str(self.other)
        print(cmd)
        self.ssh = pexpect.spawn(cmd)
        enter_password = 0
        while True:
            try:
                index = self.ssh.expect([
                    pexpect.TIMEOUT,
                    '(yes\/no)',
                    '[pP]assword:\s?$',
                    'REMOTE HOST IDEN',
                    '--MORE--*',
                    '\[redisplay\]*|yes\/no\/redisplay*',
                    newSsh,
                    'Maximum login attempts exceeded',
                    self.prompt,
                    'Please enter old password',
                    'Please enter a new password',
                    'Please re-enter new password',
                    'yes:',
                ])
            except:
                print('Could not start ssh to {}'.format(self.ip))
                if errcode:
                    return False, 'Could not start ssh'
                return False
            if index == 0:  # Timeout
                print('Send command timeout')
                if errcode:
                    return False, 'Send command timeout'
                return False
            elif index == 1:  # SSH does not have the public key. Just accept it.
                time.sleep(3)
                self.ssh.sendline('yes')
                time.sleep(3)
                continue
            elif index == 2:  # password
                print(f'start input soniccore password: {self.password}')
                if enter_password == 0:
                    self.ssh.sendline(self.password)
                elif enter_password == 1:
                    self.ssh.sendline(G_PASSWORD_NEW)
                elif enter_password == 2:
                    # self.ssh.sendline(self.wrong_password)
                    self.ssh.sendline(password2)
                elif enter_password == 3:
                    self.ssh.sendline(ndpp_password)
                else:
                    if errcode:
                        print('All the passwords are wrong')
                        return False, f'Try password,{self.new_password},{self.wrong_password} failed'
                    return False
                enter_password += 1
                time.sleep(5)
                continue
            elif index == 3:
                print('FIX: .ssh/know_hosts')
                continue
            elif index == 4:
                self.ssh.send("q")
                continue
            elif index == 5 or index == 6 or index == 12:
                self.ssh.sendline('yes')
                continue
            elif index == 7:
                print('Maximum login attempts exceeded: ' + 'ssh -l ' + self.user + ' ' + self.ip)
                if errcode:
                    return False, 'Maximum login attempts exceeded'
                return False
            elif index == 8:
                print('Successfully login in ' + self.ip)
                if errcode:
                    return True, 'Successfully login in'
                return True
            elif index == 9:
                self.ssh.sendline(self.password)
                continue
            elif index == 10:
                self.ssh.sendline(self.new_password)
                continue
            elif index == 11:
                self.ssh.sendline(self.new_password)
                continue
        if errcode:
            return False, 'Final fail, no error code got'
        return False

    def ssh_connect_admin_user(self, errcode=0):
        os.system('sed -i ' + '\'' + '/' + self.ip + '/' + ' d' + '\'' + ' /root/.ssh/known_hosts')
        newSsh = "Are you sure you want to continue connecting"
        cmd = 'ssh -l ' + self.user + ' ' + self.ip
        print(cmd)
        self.ssh = pexpect.spawn(cmd)
        enter_password = 0
        while True:
            try:
                index = self.ssh.expect([
                    pexpect.TIMEOUT,
                    '(yes\/no)',
                    '[pP]assword:\s?$',
                    'REMOTE HOST IDEN',
                    '--MORE--*',
                    '\[redisplay\]*|yes\/no\/redisplay*',
                    newSsh,
                    'Maximum login attempts exceeded',
                    self.prompt,
                    'Please enter old password',
                    'Please enter a new password',
                    'Please re-enter new password',
                ])
                print(self.ssh.before.decode())
                print(self.ssh.after.decode())
            except:
                print('Could not start ssh to {}'.format(self.ip))
                if errcode:
                    return False, 'Could not start ssh'
                return False
            if index == 0:  # Timeout
                print('Send command timeout')
                if errcode:
                    return False, 'Send command timeout'
                return False
            elif index == 1:  # SSH does not have the public key. Just accept it.
                self.ssh.sendline('yes')
                continue
            elif index == 2:  # password
                if enter_password == 0:
                    self.ssh.sendline(self.password)
                    self.flushbuffer()
                elif enter_password == 1:
                    self.ssh.sendline('')
                    self.flushbuffer()
                elif enter_password == 2:
                    self.ssh.sendline(self.password)
                    self.new_password = new_password
                elif enter_password == 3:
                    self.ssh.sendline(self.wrong_password)
                    self.new_password = self.wrong_password
                else:
                    if errcode:
                        return False, f'Try password,{self.new_password},{self.wrong_password} failed'
                    return False
                enter_password += 1
                time.sleep(2)
                continue
            elif index == 3:
                print('FIX: .ssh/know_hosts')
                continue
            elif index == 4:
                self.ssh.send("q")
                continue
            elif index == 5 or index == 6:
                self.ssh.sendline('yes')
                continue
            elif index == 7:
                print('Maximum login attempts exceeded: ' + 'ssh -l ' + self.user + ' ' + self.ip)
                if errcode:
                    return False, 'Maximum login attempts exceeded'
                return False
            elif index == 8:
                print('Successfully login in ' + self.ip)
                if errcode:
                    return True, 'Successfully login in'
                return True
            elif index == 9:
                self.ssh.sendline(self.password)
                continue
            elif index == 10:
                time.sleep(2)
                self.ssh.sendline(self.new_password)
                continue
            elif index == 11:
                self.ssh.sendline(self.new_password)
                continue
        if errcode:
            return False, 'Final fail, no error code got'
        return False

    def console_connect(self, errcode=0):
        try:
            self.ssh = pexpect.spawn('telnet ' + self.console_ip + ' ' + str(self.console_port))
        except:
            print('Could not start telnet to ' + self.console_ip)
            if errcode:
                return False, 'Could not start telnet to conserver'
            return False
        port_prefix = re.match(r'(\d)', str(self.console_port))
        print(f'port_prefix: {port_prefix.group(1)}')
        if not port_prefix:
            if errcode:
                return False, 'Could not get port prefix'
            return False
        elif port_prefix.group(1) == '2':
            if not self.ssh.expect([pexpect.TIMEOUT, 'login:']):
                print('Unable to Telnet to: ' + self.console_ip + str(self.console_port))
                if errcode:
                    return False, 'Unable to telnet to conserver'
                return False
            print(f'send console user: {console_user}')
            self.ssh.sendline(console_user)
            if not self.ssh.expect([pexpect.TIMEOUT, 'Password:']):
                if errcode:
                    return False, 'Could not get conserver Password prompt'
                return False
            print(f'send console password: {console_pwd}')
            self.ssh.sendline(console_pwd)

        elif port_prefix.group(1) == '6':
            pass

        self.flushbuffer()
        self.ssh.sendline('')
        time.sleep(1)
        enter_password = 0
        enter_new_password = 0
        while True:
            index = self.ssh.expect([
                pexpect.TIMEOUT,    #0
                'User:',            #1
                'Password:',        #2
                'ChassisOS-\d > ',  #3
                self.prompt,        #4
                self.genPrompt,     #5
                self.cfgPrompt,     #6
                '->',               #7
                'Au revior',        #8
                'changes found',    #9
                'console not connected yet. please try again later...',
                'Error: connect failed: Connection refused',
                'CONNECTED!$',
                'localhost login:',
                'Maximum login attempts exceeded',
                'Please enter old password',
                'Please enter a new password',
                'Please re-enter new password',
                'yes:',
                'BGP>',
                'OSPF>',
                'RIP>',
            ])
            try:
                output = bytes.decode(self.ssh.before) + bytes.decode(self.ssh.after)
                print('cmd run print: ---------------------------')
                print(output)
                print('-----------------------------------------')
            except:
                print(
                    'console output {} {} not meet the expected match.'.format(self.ssh.before, self.ssh.after))

            if index == 0:  # Timeout
                print('Firewall has no response.')
                # print(self.ssh.before)
                # print(self.ssh.after)
                self.ssh.sendline('')
                self.close()
                if errcode:
                    return False, 'Firewall has no response'
                return False
            elif index == 1:
                self.ssh.sendline(self.user)
                continue
            elif index == 2:  # password
                if enter_password == 0:
                    print(f'start input dut password: {self.password}')
                    self.ssh.sendline(self.password)
                elif enter_password == 1:
                    print(f'start input dut password: {G_PASSWORD_NEW}')
                    self.ssh.sendline(G_PASSWORD_NEW)
                elif enter_password == 2:
                    print(f'start input dut password: {password2}')
                    self.ssh.sendline(password2)
                elif enter_password == 3:
                    print(f'start input dut password: {password3}')
                    self.ssh.sendline(password3)
                elif enter_password == 4:
                    print(f'start input dut password: {password4}')
                    self.ssh.sendline(password4)
                elif enter_password == 5:
                    print(f'start input dut password: {ndpp_password}')
                    self.ssh.sendline(ndpp_password)
                else:
                    print('all Password not correct.')
                    if errcode:
                        return False, ''
                    return False
                enter_password += 1
                time.sleep(2)
                continue
            elif index == 3:
                self.ssh.sendline('smconsole 1')
                self.ssh.sendline('')
                continue
            elif index == 4:
                if self.blade > 1:
                    return self.changeblade(errcode)
                else:
                    print(
                        'Console to dut via telnet {} {} sucessfully.'.format(self.console_ip, self.console_port))
                    if errcode:
                        return True, 'Console to dut via telnet sucessfully'
                    return True
            elif index == 5 or index == 6:
                self.ssh.sendline("exit")
                continue
            elif index == 7:
                print('Firewall login exception: ->')
                self.ssh.close(force=True)
                if errcode:
                    return False, 'Firewall login exception: ->'
                return False
            elif index == 8:
                self.ssh.sendline('')
                continue
            elif index == 9:
                self.ssh.sendline('no')
                continue
            elif index == 10 or index == 11:
                self.ssh.sendline('')
                time.sleep(30)
                continue
            elif index == 12:
                self.ssh.sendline('')
                self.ssh.sendline('')
                continue
            elif index == 13:
                self.ssh.sendline(self.soniccore['user'])
                # rc = 2
                print('start try to login nssp fw...')
                self.nssplogin(errcode)
                break
            elif index == 14:
                print(
                    'Maximum login attempts exceeded: ' + 'telnet ' + self.console_ip + ' ' + str(self.console_port))
                if errcode:
                    return False, 'Maximum login attempts exceeded'
                return False
            elif index == 15:
                time.sleep(2)
                if enter_new_password == 0:
                    print('111')
                    self.ssh.sendline(self.password)
                else:
                    print('222')
                    self.ssh.sendline('')
                    self.ssh.sendline('')
                    time.sleep(5)
                continue
            elif index == 16:
                time.sleep(2)
                self.ssh.sendline(G_PASSWORD_NEW)
                continue
            elif index == 17:
                time.sleep(2)
                self.ssh.sendline(G_PASSWORD_NEW)
                enter_new_password = 1
                print('+' * 50)
            elif index == 18:
                self.ssh.sendline('yes')
                continue
            elif index == 19 or index == 20 or index == 21:
                self.ssh.sendline('exit')
            continue

        if errcode:
            return False, 'Final fail, no error code got'
        return False

    def nssplogin(self, errcode):
        print(f'nssp Enter soniccore mode on blade {self.blade}...')
        print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        print('start login nssp switch.....................')
        while True:
            index = self.ssh.expect([
                pexpect.TIMEOUT,
                'Password:',
                'ChassisOS-1 >',
                'console not connected yet. please try again later...',
                'Error: connect failed: Connection refused',
                'CONNECTED!',
                'user:$',
                'Secondary>',
            ])

            if index == 0:  # Timeout
                print('ChassisOS has no response.')
                self.ssh.close(force=True)
                if errcode:
                    return False, 'ChassisOS has no response'
                return False
            elif index == 1:  # password
                self.ssh.sendline(self.soniccore['password'])
                continue
            elif index == 2:
                self.ssh.sendline(f'smconsole {self.blade}')
                self.ssh.sendline('')
                continue
            elif index == 3 or index == 4:
                # self.ssh.sendline('')
                # time.sleep(30)
                # continue
                print('ChassisOS-1: connect failed')
                if errcode:
                    return False, 'ChassisOS-1: connect failed'
                return False
            elif index == 5:
                self.ssh.sendline('')
                self.ssh.sendline('')
                if self.blade > 1:
                    break
                continue
            elif index == 6:
                self.ssh.sendline(G_PASSWORD_NEW)
                break
            elif index == 7:
                break
        print('start login sonicos.....................')
        enter_password = 0
        while True:
            index = self.ssh.expect([
                pexpect.TIMEOUT,
                'User:',
                'Password:',
                self.prompt,
                self.genPrompt,
                self.cfgPrompt,
                '->',
                'Au revior',
                'changes found',
                'Please enter old password',
                'Please enter a new password',
                'Please re-enter new password',
                'Maximum login attempts exceeded.',
                'CONNECTED!',
            ])

            if index == 0:  # Timeout
                print('Firewall has no response.')
                # logger.debug(self.ssh.before)
                # logger.debug(self.ssh.after)
                self.ssh.close(force=True)
                if errcode:
                    return False, 'Firewall has no response'
                return False
            elif index == 1:
                self.ssh.sendline(self.user)
                continue
            elif index == 2:  # password
                if enter_password == 0:
                    print(f'start input dut password: {self.password}')
                    self.ssh.sendline(self.password)
                elif enter_password == 1:
                    print(f'start input dut password: {G_PASSWORD_NEW}')
                    self.ssh.sendline(G_PASSWORD_NEW)
                elif enter_password == 2:
                    print(f'start input dut password: {password2}')
                    self.ssh.sendline(password2)
                elif enter_password == 3:
                    print(f'start input dut password: {password3}')
                    self.ssh.sendline(password3)
                elif enter_password == 4:
                    print(f'start input dut password: {password4}')
                    self.ssh.sendline(password4)
                elif enter_password == 5:
                    print(f'start input dut password: {ndpp_password}')
                    self.ssh.sendline(ndpp_password)
                else:
                    print('fw Password not correct.')
                    return False, 'dut failed: fw Password not correct'
                enter_password += 1
                time.sleep(1)
                continue

            elif index == 3:
                if self.blade > 1:
                    print('mark000000000000000000000000000000000000000000000000000')
                    self.ssh.sendcontrol('C')
                    time.sleep(0.5)
                    print(f'send smconsole {self.blade}')
                    self.ssh.sendline(f'smconsole {self.blade}')
                    self.ssh.sendline('')
                    time.sleep(1)
                    self.blade = 0
                    print('mark11111111111111111111111111111111111111111111111111')
                    continue
                else:
                    print(
                        'Console to dut via telnet {} {} sucessfully.'.format(self.console_ip, self.console_port))
                    if errcode:
                        return True, 'Console to dut via telnet sucessfully'
                    return True
            elif index == 4 or index == 5:
                self.ssh.sendline("exit")
                continue
            elif index == 6:
                self.ssh.sendline('exit')
                continue
            elif index == 7:
                self.ssh.sendline('')
                continue
            elif index == 8:
                self.ssh.sendline('no')
                continue
            elif index == 9:
                self.ssh.sendline(self.password)
                continue
            elif index == 10:
                print(f'the new password is: {G_PASSWORD_NEW}')
                self.ssh.sendline(G_PASSWORD_NEW)
                continue
            elif index == 11:
                print(f'the new password is: {G_PASSWORD_NEW}')
                self.ssh.sendline(G_PASSWORD_NEW)
            elif index == 12:
                print('Maximum login fw attempts exceeded')
                self.ssh.sendline('')
                self.ssh.sendcontrol('C')
                if errcode:
                    return False, 'Maximum login fw attempts exceeded'
                return False
            elif index == 13:
                self.ssh.sendline('')
                self.ssh.sendline('')
                continue
            continue
        print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')

    def changeblade(self, errcode):
        self.flushbuffer()
        self.ssh.sendcontrol('C')
        time.sleep(0.5)
        print(f'send smconsole {self.blade}')
        self.ssh.sendline(f'smconsole {self.blade}')
        # self.ssh.sendline('')
        time.sleep(1)
        self.blade = 0
        print(f'login sonicos again via blade {self.blade}.....................')
        enter_password = 0
        while True:
            index = self.ssh.expect([
                pexpect.TIMEOUT,
                'User:',
                'Password:',
                self.prompt,
                'CONNECTED!',
            ])

            if index == 0:  # Timeout
                print('Firewall has no response.')
                # logger.debug(self.ssh.before)
                # logger.debug(self.ssh.after)
                self.ssh.close(force=True)
                return False
            elif index == 1:
                self.ssh.sendline(self.user)
                continue
            elif index == 2:  # password
                print(f'enter_password: {enter_password}')
                if enter_password == 0:
                    self.ssh.sendline(self.password)
                elif enter_password == 1:
                    self.ssh.sendline(G_PASSWORD_NEW)
                elif enter_password == 2:
                    self.ssh.sendline(password2)
                elif enter_password == 3:
                    self.ssh.sendline(ndpp_password)
                else:
                    print('fw Password not correct.')
                    return False, 'dut failed: fw Password not correct'
                enter_password += 1
                time.sleep(1)
                continue

            elif index == 3:
                print(
                    'Console to dut via telnet {} {} sucessfully.'.format(self.console_ip, self.console_port))
                if errcode:
                    return True, 'Console to dut via telnet sucessfully'
                return True
            elif index == 4:
                self.ssh.sendline('')
                self.ssh.sendline('')
                continue

    def do_cli_command(self, command, customPrompt='>#', timeout=10):
        '''send a single command'''
        print('Send command:' + command)
        self.flushbuffer()
        output = ""
        self.ssh.sendline(command)
        time.sleep(0.1)
        while True:
            index = self.ssh.expect([
                pexpect.TIMEOUT,
                "-next|\-MORE",
                "preempt them \(yes\/no\)",
                "[Ee]rror:",
                r'exiting\(yes\/no\/cancel\)',
                r'\(yes(\/no)?(\/cancel)?',
                r'[Rr]estart .* \(yes',
                r'Restart now\?\(yes/no\)',
                r'Booting current firmware',
                r'Restoring to factory defaults',
                self.genPrompt,
                self.cfgPrompt,
                self.prompt,
                customPrompt,
                r'@.*password:',
                r'continue connecting \(yes\/no',
                r'User:$',
                r'Enter into the safemode now'],
                timeout=timeout)
            try:
                output += bytes.decode(self.ssh.before) + bytes.decode(self.ssh.after)
            except:
                print('output {} {} not meet the expected match.'.format(self.ssh.before, self.ssh.after))
            if index == 0:  # Timeout
                print('Wrong command: ' + bytes.decode(self.ssh.before) + str(self.ssh.after))
                return False
            elif index == 1:
                self.ssh.send(' ')
                continue
            elif index == 2:
                self.ssh.sendline('y')
                continue
            elif index == 3:
                print('Command ' + '\'' + command + '\'' + ' has error')
            elif index == 4 or index == 5 or index == 15:
                self.ssh.sendline('yes')
                self.flushbuffer()
                continue
            elif index == 6 or index == 7 or index == 8:
                self.flushbuffer()
                print('======>' + output)
                self.ssh.sendline('cancel')
                print('Firewall need restart.')
                # is_Firewall_up(ip=self.ip, ssh=False)
                if re.search('console', self.supported_config_mode, re.I):
                    self.ssh.send('')
                    continue
                self.ssh.close()
                return output
            elif index == 9:
                self.flushbuffer()
                print('=>' + output)
                print('Firewall need factory default.')
                self.flushbuffer()
                #    is_Firewall_up(ip=self.ip, ssh=True)
                mode = 'ping'
                if re.search('console', self.supported_config_mode, re.I):
                    mode = 'console'
                # is_Firewall_up(ip=self.ip, ssh=False, console_ip=self.console_ip, console_port=self.console_port,
                #                mode=mode)
                if re.search('console', self.supported_config_mode, re.I):
                    self.ssh.sendline('')
                    continue
                self.ssh.close()
                return output
            elif index == 10 or index == 11 or index == 12 or index == 13 or index == 14 or index == 16 or index == 17:
                break
        # print('=>' + output)
        return output

    def do_cli_commands(self, commands, tag=0, timeout=10):
        for i in range(0, 2):
            rc, output = self.cli_login(1)
            if rc:
                break
            print('Fail to login. try again')
            if (i == 1):
                # self.ssh.sendline('exit')
                try:
                    self.ssh.close()
                except:
                    print('Maximum try, Login fail.')
                finally:
                    if tag == 1:
                        print('Login failed log: {}'.format(output))
                        return False, output
                    return False
        self.flushbuffer()
        output = ''
        for command in commands:
            tmp = self.do_cli_command(command, timeout=timeout)
            if tmp:
                output = output + tmp
                if re.match(r'exiting \(yes\/no\/cancel\)', tmp, re.I):
                    self.ssh.sendline('yes')
                elif (re.search(r'Restart', tmp, re.I | re.M) or re.search(r'Restoring to factory defaults', tmp,
                                                                           re.I | re.M)) and not re.search(
                        r'Restart Required:', tmp):
                    if 'Error:' in output:
                        result = False
                    else:
                        result = True
                    if tag == 1:
                        return result, output
                    else:
                        return result
        print('Send command: exit')
        self.ssh.sendline('exit')
        time.sleep(2)
        if re.search('console', self.supported_config_mode, re.I):
            self.ctrl_code = ']'
            self.ssh.sendcontrol(self.ctrl_code)
        self.close()

        if 'Error:' in output:
            result = False
        else:
            result = True
        if tag == 1:
            return result, output
        else:
            return result

    def flushbuffer(self):
        self.ssh.buffer = b''

    @staticmethod
    def _is_key_exist(commands, kwargs, key, key_new=None, tag=False):
        if not key_new:
            key_new = key
        if (tag and key in kwargs.keys()) or not tag:
            if key in kwargs.keys():
                if isinstance(kwargs[key], bool):
                    if kwargs[key]:
                        commands.append(key_new)
                    elif not kwargs[key]:
                        commands.append('no ' + key_new)
                elif not str(kwargs[key]).isspace() and kwargs[key]:
                    value = FirewallCLI.process_name(str(kwargs[key]))
                    commands.append(key_new + ' ' + value)
                else:
                    print('Make sure {} is valid'.format(kwargs[key]))
                    return False
            else:
                pass
        else:
            print('Key {} Must be specified!'.format(key))
            return False
        return True

    @staticmethod
    def simple_check_box(symbol, check):
        if check is True:
            return symbol
        else:
            return 'no ' + symbol

    @staticmethod
    def value_check_box(symbol, value):
        if (isinstance(value, bool) and value is False) or \
                (isinstance(value, str) and value.lower() in ['no', 'disable']) or \
                (isinstance(value, int) and value == 0):
            return 'no ' + symbol
        else:
            return symbol + ' ' + str(value)

    @staticmethod
    def simple_value(symbol, value):
        return symbol + ' ' + str(value)

    @staticmethod
    def process_name(name):
        if re.search(r'[\'\"].*[\'\"]', name, re.S) is not None or \
                re.search(r' ', name, re.S) is None:
            return name
        else:
            return '\'' + name + '\''


class FirewallAPI(NetworkDevice):
    headers1 = OrderedDict([('Accept', 'application/json'),
                            ('Content-Type', 'application/json'),
                            ('Accept-Encoding', 'application/json'),
                            ('charset', 'UTF-8')])
    # headers2 = OrderedDict([('Accept', 'application/json'),
    # ('charset', 'UTF-8')])
    urllib3.disable_warnings()

    def __init__(self, ip, prompt='>', headers=headers1, port=443, logfile='/tmp/snwlapi.log', **kwargs):
        super().__init__(ip, **kwargs)
        self.logfile = logfile
        self.headers = headers
        if port != 443:
            self.ip += ":" + str(port)

    def api_login(self, check_login=True):
        if self.is_api_login_valid():
            print('Already login in, returning success.')
            return True
        payload = {"override": True}
        payload = json.dumps(payload)
        url = 'https://' + self.ip + '/api/sonicos/auth'
        urllib3.disable_warnings()
        resp = requests.post(url, auth=HTTPDigestAuth(self.user, self.new_password), data=payload, headers=self.headers,
                             verify=False)
        response = resp.content.decode('utf-8')
        print("Login response after decode:\r\n{}".format(response))
        try:
            login_response = json.loads(response)
            print(login_response)

            if login_response['status']['success']:
                print('Successfully login sonincos')
                time.sleep(3)
                if check_login:
                    if self.is_api_login_valid():
                        return True
                    else:
                        return False
                return True
            elif login_response['status']['info'][0]['message'] == 'Incorrect name/password':
                print(f'Old password fail to login, try use {G_PASSWORD_NEW}.')
                self.new_password = G_PASSWORD_NEW
                #   resp = requests.post(url, auth=(self.user, self.new_password), data=payload, headers=self.headers, verify=False)
                return self.api_login()
            else:
                print("Login error\nResponse is " + login_response['status']['info'][0]['message'])
                return "Login error\nResponse is " + login_response['status']['info'][0]['message']
        except:
            print('Login failed')
            return False

    def api_logout(self):
        url = 'https://' + self.ip + '/api/sonicos/auth'
        resp = requests.delete(url, headers=self.headers, verify=False)
        print("Logout response:")
        print(resp)
        status_code = resp.status_code
        print(status_code)
        response = resp.content.decode('utf-8')
        logout_response = json.loads(response)
        print(logout_response)
        if not logout_response['status']['success']:
            print("Response is " + logout_response['status']['info'][0]['message'])
            return "Logout error\nResponse is " + logout_response['status']['info'][0]['message']
        else:
            print('Successfully logout sonincos')
            return True

    def is_api_login_valid(self):
        url = 'https://' + self.ip + '/api/sonicos/user/status/name/' + self.user
        try:
            response = requests.get(url, headers=self.headers, params=None, timeout=60, verify=False)
            resp = response.content.decode('utf-8', "ignore")
            print(resp)
            return_msg = json.dumps(resp)
            if re.search(r'[\(\"]config[\s_]mode|\W config[\s_]mode', return_msg, re.I):
                print('Already in config mode.')
                return True
            elif re.search(r'status.*Non-config mode', return_msg, re.I) or re.search(r'status.*Non config mode',
                                                                                      return_msg, re.I):
                print('Firewall in non-config mode, try switch to config mode.')
                # self.api_post('api/sonicos/config-mode')
                requests.post('https://' + self.ip + '/api/sonicos/config-mode', headers=self.headers, data=None,
                              params=None, timeout=60, verify=False)
                return True
            else:
                print(f'Fail to get {url}, try re-login')
                return False
        except Exception as e:
            print("GET request is not successful {}".format(e))
            return False

    def api_get(self, url, params=None, nologin=False, log_switch=True):
        url = 'https://' + str(self.ip) + '/' + url
        return_msg = {}
        if not nologin:
            self.api_login()
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=60, verify=False)
        except Exception as e:
            print("GET request is not successful {}".format(e))
            return False
        resp = response.content.decode('utf-8', "ignore")
        try:
            return_msg = json.loads(resp)
            if log_switch == True:
                print(return_msg)
        except Exception as e:
            return_msg = resp
            if log_switch == True:
                print(resp)
        if not nologin:
            print("Get " + url)
            if log_switch == True:
                print(return_msg)
        return return_msg

    def api_put(self, url, msg=False, data=None, params=None, headers=headers1, nologin=False, check_online='ping'):
        if not nologin:
            self.api_login()
        url = 'https://' + str(self.ip) + '/' + url
        print(url)

        try:
            print(json.dumps(data, indent=1))
            if data:
                if type(data) is str and re.match('@.*', data, re.I):
                    data = open(data.replace('@', ''), 'rb').read()
                elif type(data) is bytes:
                    data = data
                else:
                    data = json.dumps(data)
            response = requests.put(url, headers=headers, data=data, params=params, timeout=60, verify=False)
        except Exception as e:
            print("POST request is not successful {}".format(e))
            return False
        print('#######################%')
        status_code = response.status_code
        print("status code:" + str(status_code))
        if status_code == 200:
            return_value = True
        else:
            return_value = False
        resp = response.content.decode('utf-8')
        resp = re.sub('^%.*?{', '{', resp, flags=re.S)
        try:
            return_msg = json.loads(resp)
            print(return_msg)
        except:
            print(resp)
        pending_value = True
        pedding_msg = ''
        try:
            if return_msg['status']['cli']['pending_config']:
                if msg:
                    pending_value, pending_msg = self.api_post_pendingchanges(msg=msg)
                else:
                    pending_value = self.api_post_pendingchanges(msg=msg)
        except:
            print("Fail to get ['status']['cli']['pending_config'] in response")
        try:
            if return_msg['status']['cli']['restart_required'] and \
                    return_msg['status']['cli']['restart_required'].lower() == 'true':
                print('Restart needed as per response, so restarting firewall')
                self.api_restart(check_online=check_online)
        except KeyError as reason:
            print("Not get key return_msg['status']['cli']['restart_required']")
        if msg:
            if not pending_value:
                return (return_value & pending_value, pending_msg)
            else:
                return (return_value & pending_value, return_msg)
        else:
            return return_value & pending_value

    def api_post(self, url, msg=False, data=None, params=None, headers=headers1, nologin=False, check_online='ping'):
        if not nologin:
            self.api_login()
        url = 'https://' + str(self.ip) + '/' + url
        print(url)
        try:
            print(json.dumps(data, indent=1))

            if data:
                data = json.dumps(data)
            response = requests.post(url, headers=headers, data=data, params=params, timeout=60, verify=False)
        except Exception as e:
            print("ERR:POST request is not successful {}".format(e))
            return False
        status_code = response.status_code
        print("status code:" + str(status_code))
        if status_code == 200:
            return_value = True
        else:
            return_value = False
        resp = response.content.decode('utf-8')
        resp = re.sub('^%.*?{', '{', resp, flags=re.S)

        try:
            return_msg = json.loads(resp)
            print(return_msg)
        except:
            print(resp)
        pending_value = True
        pedding_msg = ''
        try:
            if return_msg['status']['cli']['pending_config']:
                if msg:
                    pending_value, pending_msg = self.api_post_pendingchanges(msg=msg)
                else:
                    pending_value = self.api_post_pendingchanges(msg=msg)
        except:
            print("Fail to get ['status']['cli']['pending_config'] in response")
        try:
            if return_msg['status']['cli']['restart_required'] and \
                    return_msg['status']['cli']['restart_required'].lower() == 'true':
                print('Restart needed as per response, so restarting firewall')
                self.api_restart(check_online=check_online)
        except KeyError as reason:
            print("Not get key return_msg['status']['cli']['restart_required']")
        if msg:
            if not pending_value:
                return (return_value & pending_value, pending_msg)
            else:
                return (return_value & pending_value, return_msg)
        else:
            return return_value & pending_value

    def api_post_no_need_pending(self, url, msg=False, data=None, params=None, headers=headers1, nologin=False,
                                 check_online='ping'):
        if not nologin:
            self.api_login()
        url = 'https://' + str(self.ip) + '/' + url
        print(url)
        try:
            print(json.dumps(data, indent=1))
            if data:
                data = json.dumps(data)
            response = requests.post(url, headers=headers, data=data, params=params, timeout=60, verify=False)
            time.sleep(5)
            response = requests.post(url, headers=headers, data=data, params=params, timeout=60, verify=False)
        except Exception as e:
            print("ERR:POST request is not successful {}".format(e))
            return False
        status_code = response.status_code
        print("status code:" + str(status_code))
        if status_code == 200:
            resp = response.content.decode('utf-8')
            resp = re.sub('^%.*?{', '{', resp, flags=re.S)
            try:
                return_msg = json.loads(resp)
                print(return_msg)
                return return_msg
            except:
                print(resp)
                return resp
        else:
            resp = 'status code :' + str(status_code)
            return resp

    def api_post_pendingchanges(self, msg=False, headers=headers1, nologin=False, check_online='ping'):
        #        if not nologin:
        #            self.api_login()
        pending_changes = 'https://' + self.ip + '/api/sonicos/config/pending'
        r = requests.post(pending_changes, headers=headers, timeout=60, verify=False)
        status_code = r.status_code
        resp = r.content.decode('utf-8')
        return_value = True
        try:
            return_msg = json.loads(resp)
            print(return_msg)
            return_value = return_msg['status']['success']
            print(f'Pending changes is: {return_value}')
            if return_msg['status']['info'][0]['message'] == 'Non config mode' or return_msg['status']['info'][0][
                'message'] == 'Not allowed in current mode':
                print('non config mode, re-login')
                requests.post('https://' + self.ip + '/api/sonicos/config-mode', headers=self.headers, data=None,
                              params=None, timeout=60, verify=False)
                r = requests.post(pending_changes, headers=headers, timeout=60, verify=False)
                status_code = r.status_code
                resp = r.content.decode('utf-8')
                return_msg = json.loads(resp)
                print(return_msg)
                return_value = return_msg['status']['success']
        except:
            print(resp)
        try:
            if return_msg['status']['cli']['restart_required'] and \
                    return_msg['status']['cli']['restart_required'].lower() == 'true':
                print('Restart needed as per response, so restarting firewall')
                self.api_restart(check_online=check_online)
        except KeyError as reason:
            print("Not get key return_msg['status']['cli']['restart_required']")
        # if status_code == 200:
        #     print(status_code)
        #     return_value = True
        # else:
        #     print('^^^^^^^^^')
        #     return_value = False
        print(return_value)
        # if not response['status']['success']:
        # return "{\"Error\" : \"" + response['status']['info'][0]['message'] + "\" }"
        if not return_value:
            requests.delete(pending_changes, headers=headers, verify=False)
        if msg:
            return return_value, return_msg
        else:
            return return_value

    def api_delete(self, url, msg=False, data=None, params=None):
        self.api_login()
        url = 'https://' + str(self.ip) + '/' + url
        print(url)
        try:
            print(json.dumps(data, indent=1))
            if data:
                data = json.dumps(data)
            response = requests.delete(url, headers=self.headers, data=data, params=params, timeout=60, verify=False)
        except:
            print("DELETE request is not successful")
            return False
        status_code = response.status_code
        print("status code:" + str(status_code))
        if status_code == 200:
            return_value = True
        else:
            return_value = False
        resp = response.content.decode('utf-8')
        return_msg = json.loads(resp)
        print(return_msg)
        if msg:
            pending_value, pending_msg = self.api_post_pendingchanges(msg=msg)
        else:
            pending_value = self.api_post_pendingchanges(msg=msg)
        try:
            if return_msg['status']['cli']['restart_required'] and \
                    return_msg['status']['cli']['restart_required'].lower() == 'true':
                print('Restart needed as per response, so restarting firewall')
                self.api_restart()
        except KeyError as reason:
            print("Not get key return_msg['status']['cli']['restart_required']")
        if msg:
            if not pending_value:
                return (return_value & pending_value, pending_msg)
            else:
                return (return_value & pending_value, return_msg)
        else:
            return return_value & pending_value

    def api_restart(self, check_online='ping'):
        restart_url = 'https://' + self.ip + '/api/sonicos/restart'
        self.api_login()
        restart_resp = requests.post(restart_url, data='', headers=self.headers, verify=False)
        status_code = restart_resp.status_code
        time.sleep(20)

        response = restart_resp.content.decode('utf-8')
        logout_response = json.loads(response)
        print(logout_response)
        # restart_resp = self.api_post(restart_url, headers=headers, msg=True, data='')
        if status_code == 200:
            status = is_Firewall_up(ssh=False, mode=check_online)
            return status
        else:
            print('Restart fail, error code:{}'.format(status_code))
            return False

    # add by ldu
    def api_get_header(self, url, params=None, headers=headers1, nologin=False, log_switch=True):
        url = 'https://' + str(self.ip) + '/' + url
        return_msg = {}
        if not nologin:
            self.api_login()
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60, verify=False)
        except Exception as e:
            print("GET request is not successful {}".format(e))
            return False
        resp = response.content.decode('utf-8', "ignore")
        try:
            return_msg = json.loads(resp)
            if log_switch == True:
                print(return_msg)
        except Exception as e:
            return_msg = resp
            if log_switch == True:
                print(resp)
        if not nologin:
            print("Get " + url)
            if log_switch == True:
                print(return_msg)
        return return_msg


# class FirewallCGI(NetworkDevice):
#     urllib3.disable_warnings()
#
#     def __init__(self, ip, logfile='/tmp/snwlcgi.log', **kwargs):
#         super().__init__(ip, **kwargs)
#         self.logfile = logfile
#         self.serial = ''
#         self.msw_user = 'auto_email@sonicwall.com'
#         self.msw_pass = 'automation'
#         self.http_mode = 'https'
#         if 'http_mode' in kwargs.keys():
#             self.http_mode = kwargs['http_mode']
#         self.session = requests.Session()
#
#     def cgi_get(self, page):
#         '''
#         Get FW page
#         :param page: page name, for example main.html
#         :return: page source
#         '''
#         url = self.http_mode + '://' + self.ip + '/' + page
#         return self.session.get(url, verify=False).text
#
#     def cgi_post(self, page, postdata):
#         '''
#         Post data to page
#         :param page: page name, for example auth.cgi
#         :param postdata: post string
#         :return: post response
#         '''
#         url = self.http_mode + '://' + self.ip + '/' + page
#         return self.session.post(url, data=postdata, verify=False)
#
#     def _b2hex(self, s):
#         '''
#         Transit string to hex string
#         :return: hex string
#         '''
#         send_buf = b''
#         for i in range(len(s)):
#             if (i % 2) == 0:
#                 c = s[i] + s[i + 1]
#                 send_buf += struct.pack('B', int(c, 16))
#         return send_buf
#
#     def _s2byte(self, s):
#         '''
#         Transit string to bytes
#         :return: bytes
#         '''
#         return bytes(s, encoding='utf-8')
#
#     def _s2arr(self, line):
#         '''
#         change '1234abcd' to [12,34,ab,cd]
#         :return: Array
#         '''
#         temp = line
#         text = ""
#         li = []
#         while temp:
#             text = text + temp[:2]
#             li.append(temp[:2])
#             temp = temp[2:]
#         return li
#
#     def _get_login_data(self):
#         '''
#         Get login post data
#         :return: login post string
#         '''
#         try:
#             html = self.cgi_get('auth1.html')
#         except:
#             print('Get auth1.html failed. Login failed.')
#             return ('', '')
#
#         find = re.search(r'param1\W+VALUE="(\w+)"', html, re.M | re.I)
#         if find is not None:
#             param1 = find.group(1)
#         # print(param1)
#         find = re.search(r'param2\W+VALUE="(\w+)"', html, re.M | re.I)
#         if find is not None:
#             param2 = find.group(1)
#         # print(param2)
#         find = re.search(r'id\W+VALUE="(\w+)"', html, re.M | re.I)
#         if find is not None:
#             id = find.group(1)
#         # print(id)
#         if not 'param1' in locals().keys() or \
#                 not 'param2' in locals().keys() or \
#                 not 'id' in locals().keys():
#             print('Get rNumbers failed.')
#             return ('', '')
#
#         dig_p1 = self._b2hex(param1)
#         dig_id = self._b2hex(id)
#         dig_pw = bytes(self.new_password, encoding='utf-8')
#         m = hashlib.md5()
#         m.update(dig_id)
#         m.update(dig_pw)
#         m.update(dig_p1)
#         digest = m.hexdigest()
#
#         postdata = "id=" + id + "&select2=English&uName=" + self.user + "&pass=&digest=" + \
#                    digest + '&adminMode=0'
#         return (postdata, param2)
#
#     def _cal_sessid(self, ssid_str, param2):
#         sessIdLen = 16
#         find = re.search(r':', ssid_str)
#         if find is None:
#             ### ssid_str doesn't contain ':', it is the real Sessid.
#             ### Otherwise, it is encrypted Sessid, needs decrypt
#             return (ssid_str)
#         rNum = ssid_str.split(':')[0]
#         cipher = ssid_str.split(':')[1][2:]
#
#         dig_p2 = self._s2byte(param2)
#         dig_pw = self._s2byte(self.new_password)
#         m = hashlib.md5()
#         m.update(dig_p2)
#         m.update(dig_pw)
#         pageseed = self._s2byte(m.hexdigest())
#
#         dig_rn = self._b2hex(rNum)
#         sha1 = hashlib.sha1()
#         sha1.update(dig_rn)
#         sha1.update(pageseed)
#         sha1.update(dig_pw)
#         digest = sha1.hexdigest()
#
#         arr_dg = self._s2arr(digest)
#         arr_cp = self._s2arr(cipher)
#         sessId = ''
#         for i in range(sessIdLen):
#             v1 = int(arr_cp[i], 16)
#             v2 = int(arr_dg[i], 16)
#             vx = hex(v1 ^ v2)[2:]
#             if len(vx) < 2:
#                 vx = '0' + vx
#             sessId = sessId + vx
#         return sessId.upper()
#
#     def cgi_login(self):
#         '''
#         Use admin to login firewall
#         :return: True | False
#         '''
#         (poststr, param2) = self._get_login_data()
#         if poststr is '':
#             print('Login failed.')
#             return False
#         response = self.cgi_post('auth.cgi', poststr)
#         find = re.search(r'sessIdStr\W+(.*?)"', response.text, re.M | re.I)
#         en_ssid = ''
#         if find is not None:
#             en_ssid = find.group(1)
#         sessId = self._cal_sessid(en_ssid, param2)
#         self.cookie = {'temp': '', 'SessId': sessId}
#         self.session.cookies.update(self.cookie)
#
#         response = self.cgi_get('management.html')
#         if re.search(r'Redirecting', response, re.M | re.I) is None:
#             print('Get Management.html failed. Login failed.')
#             return False
#
#         time.sleep(2)
#         html = self.cgi_get('main.html')
#         find = re.search(r'SonicWall Administrator', html, re.M | re.I)
#         if find is None:
#             print('main.html failed. Login failed.')
#             return False
#         find = re.search(r'<title>.*\s+(\w+)</title>', html, re.M | re.I)
#         if find is not None:
#             self.serial = find.group(1).replace('-', '')
#
#         print('Login passed. FW serial is {}'.format(self.serial))
#         return True
#
#     def register(self):
#         '''
#         Online register with cgi
#         :return: True | False
#         '''
#         if not self.cgi_login():
#             print('Login FW failed.')
#             return False
#
#         page = self.cgi_get('Security_Services/Registration.html')
#         if self.serial is '':
#             find = re.search(r'name="sn"\s+value="(\w+)">', page, re.M | re.I)
#             if find is not None:
#                 self.serial = find.group(1)
#             else:
#                 print('Get serial number failed. Registeration failed.')
#                 return False
#         print('Serial number is {}'.format(self.serial))
#
#         reg_data = {
#             'login': self.msw_user,
#             'pwd': self.msw_pass,
#             'Submit': 'Submit',
#             'sn': self.serial,
#             'fwReg': 0,
#             'TFAEnabled': 1
#         }
#         response = self.cgi_post('servlet/dea/register', reg_data)
#
#         pass_str = 'Registration completed successfully|' \
#                    'Manage Services Online|' \
#                    'Registration is finished'
#         fail_str = 'The Serial Number is not associated with this user|' \
#                    'Your session has been timed out'
#         warn_srt = 'Username/Email or Password is incorrect'
#         rc = 1
#
#         if re.search(pass_str, response.text, re.M | re.I) is not None:
#             rc = 0
#         elif re.search(warn_srt, response.text, re.M | re.I) is not None:
#             print('Maybe wrong mysonicwall account')
#             reg_data = {
#                 'login': 'test1003',
#                 'pwd': 'test1003',
#                 'Submit': 'Submit',
#                 'sn': self.serial,
#                 'fwReg': 0,
#                 'TFAEnabled': 1
#             }
#             response = self.cgi_post('servlet/dea/register', reg_data)
#             if re.search(pass_str, response.text, re.M | re.I) is not None:
#                 rc = 0
#         else:
#             print('Register failed. Registration is failed.\n{}'.format(response.text))
#             return False
#
#         if rc == 0:
#             page = self.cgi_get('activationView.html')
#             print('Dump License : \n'
#                   '------------------------------------------------------------------\n'
#                   + page +
#                   '------------------------------------------------------------------\n'
#                   'Register successful. Registration is finished.')
#             return True
#
#         print('Register failed. Registration is failed.\n{}'.format(response.text))
#         return False


# class Firewall(FirewallCLI, FirewallAPI, FirewallCGI):
class Firewall(FirewallCLI, FirewallAPI):
    def __init__(self, ip, **kwargs):
        super().__init__(ip, **kwargs)


# if __name__ == "__main__":
#     print('run main............................')
#     r_fw_console = Firewall(
#         '10.8.200.14',
#         console_ip='10.8.0.102',
#         console_port='2019',
#         user='admin',
#         password='password2',
#         supported_config_mode='cli-console')
#     print('login fw via console...............................')
#     r_fw_console.do_cli_commands(['show version', 'show interface X1 ip'])
# if __name__ == "__main__":
# ip = '192.168.168.168'
# fw = Firewall(ip, user='admin', password='password', supported_config_mode='cgi')
# fw.cgi_login()

