#!/usr/bin/env python
import pexpect, time, re
# from ..lib.global_var import *
from .mongodb import mongo
# from .. lib.mongodb import mongo
import telnetlib

class CDU(object):
    def __init__(self):
        self.db = mongo()
        self.cduparam = self.db.find_one('GlobalConfig', 'id', 'CDU')

    def Telnet_Old_CDU(self, ip):
        # 即将 telnet 所要登录的远程主机的域名
        # 提示符，可能是’ $ ’ , ‘ # ’或’ > :’
        loginprompt = '[$#>:]'
        # 拼凑 telnet 命令
        cmd = 'telnet ' + ip
        # 为 telnet 生成 spawn 类子程序
        child = pexpect.spawn(cmd)
        # 期待'login'字符串出现，从而接下来可以输入用户名
        index = child.expect(["Username:", "(?i)Unknown host", pexpect.EOF, pexpect.TIMEOUT])
        # print('index---------> %s' % index)
        if (index == 0):
            # 匹配'login'字符串成功，输入用户名.
            child.sendline(self.cduparam['CDUAdmin'])
            # 期待 "[pP]assword" 出现.
            index = child.expect(["Password:", pexpect.EOF, pexpect.TIMEOUT])
            # 匹配 "[pP]assword" 字符串成功，输入密码.
            child.sendline(self.cduparam['CDUPass'])
            # 期待提示符出现.
            child.expect(loginprompt)
            if (index == 0):
                return child
            else:
                # 匹配到了 pexpect.EOF 或 pexpect.TIMEOUT，表示超时或者 EOF，程序打印提示信息并退出.
                print("telnet login failed, due to TIMEOUT or EOF")
                child.close(force=True)
                return None
        else:
            # 匹配到了 pexpect.EOF 或 pexpect.TIMEOUT，表示超时或者 EOF，程序打印提示信息并退出.
            print("telnet login failed, due to TIMEOUT or EOF")
            child.close(force=True)
            return None

    def SSH_APC_CDU(self, ip):
        child = pexpect.spawn('ssh %s@%s -c aes256-cbc' % (self.cduparam['CDUAdmin'], ip))
        # print(f'ssh {self.cduparam["CDUAdmin"]}@{ip} -c aes256-cbc')
        ssh_newkey = 'Are you sure you want to continue connecting'
        i = child.expect([pexpect.TIMEOUT, ssh_newkey, 'password', pexpect.EOF])
        # if login timeout, print error and end.
        if i == 0:
            print("ssh login failed, due to TIMEOUT")
            return None
        # if ssh have not public key, just accept it.
        elif i == 1:
            child.sendline('yes')
            child.expect('password')
            i = child.expect([pexpect.TIMEOUT, 'password'])
            if i == 0:
                print("telnet login failed, due to TIMEOUT")
                return None
        elif i == 3:
            print("telnet login failed, due to EOF")
            return None
        # print(f'input pwd: {self.cduparam["CDUPass"]}')
        child.sendline(self.cduparam['CDUPass'])
        child.expect('>')
        return child

    def SSH_BULL_CDU(self, ip):
        """Establish telnet connection to BULL PDU"""
        try:
            tn = telnetlib.Telnet(ip, timeout=10)
            time.sleep(1)

            # Wait for login prompt
            tn.read_until(b"Mediatek login: ", timeout=10)
            tn.write(self.cduparam['CDUAdmin'].encode('ascii') + b"\n")

            # Wait for password prompt
            tn.read_until(b"Password: ", timeout=10)
            if self.cduparam['CDUPass']:
                tn.write(self.cduparam['CDUPass'].encode('ascii') + b"\n")
            else:
                tn.write(b"\n")

            # Wait for command prompt
            time.sleep(2)
            return tn
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def Reboot_CDU(self, cduip, channel):
        if self.cduparam['BULLCDUIP'].count(cduip):
            """System reboot"""
            child = self.SSH_BULL_CDU(cduip)
            # Send reboot command
            child.read_very_eager().decode('ascii')
            # print(f'control reboot 0 {channel}')
            child.write(f"control off 0 {channel}".encode('ascii') + b"\n")
            child.read_very_eager().decode('ascii')
            time.sleep(5)  # Wait for command to take effect
            child.write(f"control on 0 {channel}".encode('ascii') + b"\n")
            child.read_very_eager().decode('ascii')
            time.sleep(3)  # Wait for command to take effect
            # Query outlet status to verify
            child.write(f"query outlet 0 {channel}".encode('ascii') + b"\n")
            time.sleep(3)  # Wait for command to take effect
            response = child.read_very_eager().decode('ascii')
            if response:
                lines = response.split('\n')
                for line in lines:
                    if 'Switch' in line:
                        switch_value = line.split(':')[-1].strip()
                        if switch_value == '1':
                            return "ok"
                        else:
                            return None
        elif self.cduparam['NewCDUIP'].count(cduip):
            child = self.SSH_APC_CDU(cduip)
            if child == None:
                return None
            else:
                child.sendline('olReboot ' + channel)
                child.expect('>')
                child.sendline('olStatus ' + channel)
                child.expect('olStatus ' + channel)
                child.expect('>')
                str1 = child.before.decode()
                # print('status show : %s' % str1)
                child.close(force=True)
                if re.findall('On\*', str1) == ['On*'] or re.findall('Off\*', str1) == ['Off*']:
                    print('cdu channel reboot -- set ip: %s, channel: %s to Reboot successful!' % (cduip, channel))
                    return 'ok'
                else:
                    print('set cdu ip: %s channel %s to Reboot failed!' % (cduip, channel))
                    return str1
        else:
            child = self.Telnet_Old_CDU(cduip)
            if child == None:
                return None
            else:
                child.sendline('reboot .' + channel)
                child.expect(':')
                child.sendline('status .' + channel)
                child.expect('status .' + channel)
                child.expect(':')
                str = child.before.decode()
                child.close(force=True)
                return str

    # def Reboot_CDU(self, cduip, channel):
    #     checknewcdu = self.cduparam['NewCDUIP'].count(cduip)
    #     if checknewcdu == 0:
    #         child = self.Telnet_Old_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             child.sendline('reboot .' + channel)
    #             child.expect(':')
    #             child.sendline('status .' + channel)
    #             child.expect('status .' + channel)
    #             child.expect(':')
    #             str = child.before.decode()
    #             child.close(force=True)
    #             return str
    #     else:
    #         child = self.SSH_APC_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             child.sendline('olReboot ' + channel)
    #             child.expect('>')
    #             child.sendline('olStatus ' + channel)
    #             child.expect('olStatus ' + channel)
    #             child.expect('>')
    #             str1 = child.before.decode()
    #             # print('status show : %s' % str1)
    #             child.close(force=True)
    #             if re.findall('On\*', str1) == ['On*'] or re.findall('Off\*', str1) == ['Off*']:
    #                 print('cdu channel reboot -- set ip: %s, channel: %s to Reboot successful!' % (cduip, channel))
    #                 return 'ok'
    #             else:
    #                 print('set cdu ip: %s channel %s to Reboot failed!' % (cduip, channel))
    #                 return str1

    def Off_CDU(self, cduip, channel):
        if self.cduparam['BULLCDUIP'].count(cduip):
            """System off"""
            child = self.SSH_BULL_CDU(cduip)
            print(f'control off 0 {channel}')
            child.write(f"query outlet 0 {channel}".encode('ascii') + b"\n")
            time.sleep(5)
            result = child.read_very_eager().decode('ascii')
            print(result)
            if re.findall(r'Switch.*0', result, re.IGNORECASE):
                return 'ok'
            else:
                res = child.write(f"control off 0 {channel}".encode('ascii') + b"\n")
                time.sleep(5)
                print(f'res: {res}')
                response = child.read_very_eager().decode('ascii')
                print(f'response: {response}')
                matches = re.findall(r'success: .* set to off', response, re.IGNORECASE)
                return "ok" if matches else "on"
        elif self.cduparam['NewCDUIP'].count(cduip):
            child = self.SSH_APC_CDU(cduip)
            if child == None:
                return None
            else:
                child.sendline('olOff ' + channel)
                child.expect('>')
                time.sleep(2)
                child.sendline('olStatus ' + channel)
                child.expect('olStatus ' + channel)
                child.expect('>')
                str1 = child.before.decode()
                # print('status show : %s' % str1)
                child.close(force=True)
                tmp = re.findall('off', str1)
                # print('new cdu----------------%s' % tmp)
                if len(tmp) != 0:
                    if tmp[0] == 'off':
                        print('set cdu ip %s channel %s to Off successful!' % (cduip, channel))
                        return 'ok'
                    else:
                        print('set cdu ip %s channel %s to Off failed!' % (cduip, channel))
                        return str1
                else:
                    print('get cdu ip %s channel %s information failed!' % (cduip, channel))
                    return str1
        else:
            child = self.Telnet_Old_CDU(cduip)
            if child == None:
                return None
            else:
                child.sendline('off .' + channel)
                time.sleep(8)
                child.expect('off .' + channel)
                child.expect(':')
                str = child.before.decode()
                # print('old cdu off set result---------->%s' % str)
                child.close(force=True)
                if len(re.findall('Shutdown', str)):
                    print('cdu channel off -- set ip: %s, channel: %s to Shutdown successful!' % (cduip, channel))
                    return 'ok'
                elif len(re.findall('Off', str)):
                    print('cdu channel off -- set ip: %s, channel: %s to Off successful!' % (cduip, channel))
                    return 'ok'
                else:
                    print('cdu channel off -- get ip: %s, channel: %s information failed!' % (cduip, channel))
                    return str

    # def Off_CDU(self, cduip, channel):
    #     count = self.cduparam['NewCDUIP'].count(cduip)
    #     # print('count----------%s' % count)
    #     if count == 0:
    #         child = self.Telnet_Old_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             child.sendline('off .' + channel)
    #             time.sleep(8)
    #             child.expect('off .' + channel)
    #             child.expect(':')
    #             str = child.before.decode()
    #             # print('old cdu off set result---------->%s' % str)
    #             child.close(force=True)
    #             if len(re.findall('Shutdown', str)):
    #                 print('cdu channel off -- set ip: %s, channel: %s to Shutdown successful!' % (cduip, channel))
    #                 return 'ok'
    #             elif len(re.findall('Off', str)):
    #                 print('cdu channel off -- set ip: %s, channel: %s to Off successful!' % (cduip, channel))
    #                 return 'ok'
    #             else:
    #                 print('cdu channel off -- get ip: %s, channel: %s information failed!' % (cduip, channel))
    #                 return str
    #     else:
    #         child = self.SSH_APC_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             child.sendline('olOff ' + channel)
    #             child.expect('>')
    #             time.sleep(2)
    #             child.sendline('olStatus ' + channel)
    #             child.expect('olStatus ' + channel)
    #             child.expect('>')
    #             str1 = child.before.decode()
    #             # print('status show : %s' % str1)
    #             child.close(force=True)
    #             tmp = re.findall('off', str1)
    #             # print('new cdu----------------%s' % tmp)
    #             if len(tmp) != 0:
    #                 if tmp[0] == 'off':
    #                     print('set cdu ip %s channel %s to Off successful!' % (cduip, channel))
    #                     return 'off'
    #                 else:
    #                     print('set cdu ip %s channel %s to Off failed!' % (cduip, channel))
    #                     return str1
    #             else:
    #                 print('get cdu ip %s channel %s information failed!' % (cduip, channel))
    #                 return str1

    def On_CDU(self, cduip, channel):
        if self.cduparam['BULLCDUIP'].count(cduip):
            """System on"""
            child = self.SSH_BULL_CDU(cduip)
            print(f'control on 0 {channel}')
            child.write(f"query outlet 0 {channel}".encode('ascii') + b"\n")
            time.sleep(5)
            result = child.read_very_eager().decode('ascii')
            print(result)
            if re.findall(r'Switch.*1', result, re.IGNORECASE):
                return 'ok'
            else:
                res = child.write(f"control on 0 {channel}".encode('ascii') + b"\n")
                time.sleep(5)
                print(f'res: {res}')
                response = child.read_very_eager().decode('ascii')
                print(f'response: {response}')
                matches = re.findall(r'success: .* set to on', response, re.IGNORECASE)
                return "ok" if matches else "off"
        elif self.cduparam['NewCDUIP'].count(cduip):
            child = self.SSH_APC_CDU(cduip)
            if child == None:
                return None
            else:
                child.sendline('olOn ' + channel)
                child.expect('>')
                time.sleep(1)
                child.sendline('olStatus ' + channel)
                child.expect('olStatus ' + channel)
                child.expect('>')
                str1 = child.before.decode()
                # print('status show : %s' % str1)
                child.close(force=True)
                tmp = re.findall('On', str1)
                if len(tmp) != 0:
                    if tmp[0] == 'On':
                        print('set cdu ip %s channel %s to On successful!' % (cduip, channel))
                        return 'ok'
                    else:
                        print('set cdu ip %s channel %s to On failed!' % (cduip, channel))
                        return str1
                else:
                    print('get cdu ip %s channel %s information failed!' % (cduip, channel))
                    return str1
        else:
            child = self.Telnet_Old_CDU(cduip)
            if child == None:
                return None
            else:
                child.sendline('status .' + channel)
                child.expect('status .' + channel)
                child.expect(':')
                check = child.before.decode()
                if re.findall('Shutdown|Reboot', check):
                    return 'Shutdown'
                child.sendline('on .' + channel)
                child.expect('on .' + channel)
                child.expect(':')
                check2 = child.before.decode()
                child.close(force=True)
                tmp = re.findall('On', check2)
                if tmp:
                    if tmp[1] == 'On':
                        print('set cdu ip %s channel %s to On successful!' % (cduip, channel))
                        return 'ok'
                    else:
                        print('set cdu ip %s channel %s to On failed!' % (cduip, channel))
                        return str
                else:
                    print('get cdu ip %s channel %s information failed!' % (cduip, channel))
                    return str

    # def On_CDU(self, cduip, channel):
    #     count = self.cduparam['NewCDUIP'].count(cduip)
    #     # print('count----------%s' % count)
    #     if count == 0:
    #         child = self.Telnet_Old_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             child.sendline('status .' + channel)
    #             child.expect('status .' + channel)
    #             child.expect(':')
    #             check = child.before.decode()
    #             if re.findall('Shutdown|Reboot', check):
    #                 return 'Shutdown'
    #             child.sendline('on .' + channel)
    #             child.expect('on .' + channel)
    #             child.expect(':')
    #             check2 = child.before.decode()
    #             child.close(force=True)
    #             tmp = re.findall('On', check2)
    #             if tmp:
    #                 if tmp[1] == 'On':
    #                     print('set cdu ip %s channel %s to On successful!' % (cduip, channel))
    #                     return 'ok'
    #                 else:
    #                     print('set cdu ip %s channel %s to On failed!' % (cduip, channel))
    #                     return str
    #             else:
    #                 print('get cdu ip %s channel %s information failed!' % (cduip, channel))
    #                 return str
    #     else:
    #         child = self.SSH_APC_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             child.sendline('olOn ' + channel)
    #             child.expect('>')
    #             time.sleep(1)
    #             child.sendline('olStatus ' + channel)
    #             child.expect('olStatus ' + channel)
    #             child.expect('>')
    #             str1 = child.before.decode()
    #             # print('status show : %s' % str1)
    #             child.close(force=True)
    #             tmp = re.findall('On', str1)
    #             if len(tmp) != 0:
    #                 if tmp[0] == 'On':
    #                     print('set cdu ip %s channel %s to On successful!' % (cduip, channel))
    #                     return 'ok'
    #                 else:
    #                     print('set cdu ip %s channel %s to On failed!' % (cduip, channel))
    #                     return str1
    #             else:
    #                 print('get cdu ip %s channel %s information failed!' % (cduip, channel))
    #                 return str1

    def Check_CDU(self, cduip, channel):
        # checknewcdu = self.cduparam['NewCDUIP'].count(cduip)
        if self.cduparam['BULLCDUIP'].count(cduip):
            """System check"""
            child = self.SSH_BULL_CDU(cduip)
            # Send reboot command
            # print(f'query outlet 0 {channel}')
            child.write(f"query outlet 0 {channel}".encode('ascii') + b"\n")
            time.sleep(3)
            final_response = child.read_very_eager().decode('ascii')

            # Check if reboot was initiated
            if final_response:
                lines = final_response.split('\n')
                for line in lines:
                    if 'Switch' in line:
                        switch_value = line.split(':')[-1].strip()
                        if switch_value == '1':
                            return "On"
                        elif switch_value == '0':
                            return "Off"
            else:
                return 'Off'
        elif self.cduparam['NewCDUIP'].count(cduip):
            child = self.SSH_APC_CDU(cduip)
            if child == None:
                return None
            else:
                child.sendline('olStatus ' + channel)
                child.expect('>')
                temp_str = child.before.decode()
                # print(temp_str)
                child.close(force=True)
                checkon = re.findall('On', temp_str)
                if checkon:
                    if checkon[0] == 'On':
                        checkresult = 'On'
                    else:
                        checkresult = 'Off'
                else:
                    checkresult = 'Off'
                return checkresult
        else:
            child = self.Telnet_Old_CDU(cduip)
            if child == None:
                return None
            else:
                # 匹配提示符成功，输入执行命令 'list outlets'
                child.sendline('status .' + channel)
                # 立马匹配，目的是为了清除刚刚被 echo 回显的命令.
                child.expect('status .' + channel)
                # 期待提示符出现.
                child.expect(':')
                str = child.before.decode()
                # 将 telnet 子程序的执行权交给用户.
                # child.interact()
                # print('Left interactve mode.')
                child.close(force=True)
                checkon = re.findall('On', str)
                if checkon:
                    if checkon[1] == 'On':
                        checkresult = 'On'
                    else:
                        checkresult = 'Off'
                else:
                    checkresult = 'Off'
                return checkresult

    # def Check_CDU(self, cduip, channel):
    #     count = self.cduparam['NewCDUIP'].count(cduip)
    #     # print('count----------%s' % count)
    #     if count == 0:
    #         child = self.Telnet_Old_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             # 匹配提示符成功，输入执行命令 'list outlets'
    #             child.sendline('status .' + channel)
    #             # 立马匹配，目的是为了清除刚刚被 echo 回显的命令.
    #             child.expect('status .' + channel)
    #             # 期待提示符出现.
    #             child.expect(':')
    #             str = child.before.decode()
    #             # 将 telnet 子程序的执行权交给用户.
    #             # child.interact()
    #             # print('Left interactve mode.')
    #             child.close(force=True)
    #             checkon = re.findall('On', str)
    #             if checkon:
    #                 if checkon[1] == 'On':
    #                     checkresult = 'On'
    #                 else:
    #                     checkresult = 'Off'
    #             else:
    #                 checkresult = 'Off'
    #             return checkresult
    #     else:
    #         child = self.SSH_APC_CDU(cduip)
    #         if child == None:
    #             return None
    #         else:
    #             child.sendline('olStatus ' + channel)
    #             child.expect('>')
    #             temp_str = child.before.decode()
    #             # print(temp_str)
    #             child.close(force=True)
    #             checkon = re.findall('On', temp_str)
    #             if checkon:
    #                 if checkon[0] == 'On':
    #                     checkresult = 'On'
    #                 else:
    #                     checkresult = 'Off'
    #             else:
    #                 checkresult = 'Off'
    #             return checkresult
