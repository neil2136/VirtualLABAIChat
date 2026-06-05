import pexpect
import re
import time
# from ..dbcollect import *
from ..mongodb import mongo

db = mongo()
swaccount = db.find_one('GlobalConfig', 'id', 'Switch')
SwitchAdmin = swaccount['SwitchAdmin']
SwitchPass = swaccount['SwitchPass']
# SwitchAdmin = 'admin'
# SwitchPass = 'sonicpassword'
loginprompt = '[$#>:]'


class Switch:
    def __init__(self, ip, port=23, prompt='>', errcode=True, **kwargs):
        self.ip = ip
        self.port = port
        self.errcode = errcode
        self.prompt = prompt

    def Cisco(self):
        try:
            self.telnet = pexpect.spawn(f'telnet {self.ip} {self.port}', timeout=3)
        except Exception as e:
            print(f'Could not start telnet to {self.ip}\nError: {repr(e)}')
            return False, 'Could not start telnet to conserver'

        # print(f'send console user: {SwitchAdmin}')
        self.telnet.sendline(SwitchAdmin)
        if not self.telnet.expect([pexpect.TIMEOUT, 'Password:']):
            return False, 'Could not get conserver Password prompt'
        # print(f'send console password: {SwitchPass}')
        self.telnet.sendline(SwitchPass)

        self.telnet.buffer = b''
        self.telnet.sendline('')
        time.sleep(1)
        enter_password = 0
        while True:
            index = self.telnet.expect([
                pexpect.TIMEOUT,
                pexpect.EOF,
                "Username:",
                'Password:',
                '#',
                "(?i)Unknown host",
                ])
            try:
                output = bytes.decode(self.telnet.before) + bytes.decode(self.telnet.after)
                print('login sw output------------------------------')
                print(output)
            except Exception as e:
                cmdmsg = f'output not meet the expected match'
                print(cmdmsg)
            if index == 0 or index == 1:
                print('Switch has no response.')
                # print(self.ssh.before)
                # print(self.ssh.after)
                self.telnet.sendline('')
                self.telnet.close(force=True)
                return False, 'Switch has no response'
            elif index == 2:
                self.telnet.sendline(SwitchAdmin)
                continue
            elif index == 3:  # password
                print(f'start input soniccore password: {SwitchPass}')
                if enter_password == 0:
                    self.telnet.sendline(SwitchPass)
                elif enter_password == 1:
                    self.telnet.sendline(SwitchPass)
                else:
                    print('Switch Password not correct.')
                    return False, 'Switch Password not correct'
                enter_password += 1
                time.sleep(2)
                continue
            elif index == 4:
                # print('telnet to Switch successful.')
                return True, self.telnet

    def Cisco_not_bit(self):
        cmd = f'telnet {self.ip} {self.port}'
        child = pexpect.spawn(cmd, encoding='utf-8')
        index = child.expect(["Username:", "(?i)Unknown host", pexpect.EOF, pexpect.TIMEOUT])
        if index == 0:
            child.sendline(SwitchAdmin)
            index = child.expect(["Password:", pexpect.EOF, pexpect.TIMEOUT])
            if index == 0:
                child.sendline(SwitchPass)
                index = child.expect(["#", pexpect.EOF, pexpect.TIMEOUT])
                if index == 0:
                    # print('telnet to Switch successful.')
                    return True, child
        else:
            print(f'Could not start telnet to {self.ip}')
            return False, 'Could not start telnet to conserver'

    def Dell(self):
        cmd = f'telnet {self.ip} {self.port}'
        self.telnet = pexpect.spawn(cmd, encoding='utf-8')
        index = self.telnet.expect(["Login:", "(?i)Unknown host", pexpect.EOF, pexpect.TIMEOUT])
        if index == 0:
            # 匹配'login'字符串成功，输入用户名.
            # child.sendline(sw7_11_login_name)
            # print(f'send console user: {SwitchAdmin}')
            self.telnet.sendline(SwitchAdmin)
            # 期待 "[pP]assword" 出现.
            index = self.telnet.expect(["Password:", pexpect.EOF, pexpect.TIMEOUT])
            # 匹配 "[pP]assword" 字符串成功，输入密码.
            # child.sendline(sw7_11_login_password)
            # print(f'send console password: {SwitchPass}')
            self.telnet.sendline(SwitchPass)
            # 期待提示符出现.
            self.telnet.expect(loginprompt)
            if index == 0:
                # print('telnet to Switch successful.')
                return True, self.telnet
        else:
            print(f'Could not start telnet to {self.ip}')
            return False, 'Could not start telnet to conserver'

    def do_dell_command(self, command, timeout=10):
        """send a dell sw single command"""
        output = ""
        print('Send dell sw command: ' + command)
        self.telnet.buffer = ''
        self.telnet.sendline(command)
        time.sleep(0.1)
        while True:
            index = self.telnet.expect([
                pexpect.TIMEOUT,
                "--More--",
                "#"
                ],
                timeout=timeout)
            output += self.telnet.before + self.telnet.after
            if index == 0:  # Timeout
                return False
            elif index == 1:
                self.telnet.send(' ')
                continue
            elif index == 2:
                break
        return output

    def do_dell_commands(self, commands, tag=0, timeout=5):
        res = False
        output = ''
        for i in range(0, 2):
            (res, output) = self.Dell()
            self.telnet.buffer = ''
            if res:
                break
            print('Fail to login dell sw. try again')
            if i == 1:
                try:
                    self.telnet.close()
                except:
                    print('Maximum try, Login dell sw fail.')
                finally:
                    if tag == 1:
                        print('Login dell sw failed log: {}'.format(output))
                        return False, output
                    return False
        if res:
            for command in commands:
                tmp = self.do_dell_command(command, timeout=timeout)
                if tmp:
                    output += tmp
                    if re.match(r'exiting \(yes/no/cancel\)', tmp, re.I):
                        self.telnet.sendline('yes')
        print('Send dell sw command: exit')
        self.telnet.sendline('exit')
        time.sleep(2)
        self.telnet.close(force=True)
        if tag == 1:
            return res, output
        else:
            return res

    def do_cisco_command(self, command, timeout=10):
        """send a cisco sw single command"""
        output = ""
        print('Send command: ' + command)
        self.telnet.buffer = b''
        self.telnet.sendline(command)
        time.sleep(0.1)
        while True:
            index = self.telnet.expect([
                pexpect.TIMEOUT,
                "--More--",
                "#"
                ],
                timeout=timeout)
            try:
                output += bytes.decode(self.telnet.before) + bytes.decode(self.telnet.after)
            except:
                print('output {} {} not meet the expected match.'.format(self.telnet.before, self.telnet.after))
            if index == 0:  # Timeout
                print('Wrong command: ' + bytes.decode(self.telnet.before) + str(self.telnet.after))
                return False
            elif index == 1:
                self.telnet.send(' ')
                continue
            elif index == 2:
                break
        return output

    def do_cisco_commands(self, commands, tag=0, timeout=5):
        for i in range(0, 2):
            (res, output) = self.Cisco()
            self.telnet.buffer = b''
            if res:
                break
            print('Fail to login cisco sw. try again')
            if i == 1:
                try:
                    self.telnet.close()
                except:
                    print('Maximum try, Login cisco sw fail.')
                finally:
                    if tag == 1:
                        print('Login cisco sw failed log: {}'.format(output))
                        return False, output
                    return False
        output = ''
        for command in commands:
            tmp = self.do_cisco_command(command, timeout=timeout)
            if tmp:
                output += tmp
                if re.match(r'exiting \(yes/no/cancel\)', tmp, re.I):
                    self.telnet.sendline('yes')
        print('Send cisco sw command: exit')
        self.telnet.sendline('exit')
        time.sleep(2)
        self.telnet.close(force=True)
        result = True if 'QA_CORE_SWITCH' in output else False
        if tag == 1:
            return result, output
        else:
            return result

# debug sw login function
# sw = Switch(ip='10.8.1.13')
# cmdres = sw.do_dell_commands(['show running-config interface gi1/6'], tag=1)
# print('***********************************')
# print(cmdres)
# print('***********************************')
# sw = Switch(ip='10.8.1.4')
# cmdres = sw.do_cisco_commands(['show etherchannel summary'], tag=1)
# print('***********************************')
# print(cmdres)
# print('***********************************')

