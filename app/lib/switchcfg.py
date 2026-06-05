#!/usr/bin/env python
import pexpect
import re
import time
from ..lib.mongodb import mongo
from ..lib.dbcollect import *
from ..lib.switch.sw import Switch
from ..lib.fwlogin import *

db = mongo()
swaccount = db.find_one('GlobalConfig', 'id', 'Switch')
SwitchAdmin = swaccount['SwitchAdmin']
SwitchPass = swaccount['SwitchPass']
prompt = '[$#>:]'
refres = {
            'msg': '',
            'port_power': '',
            'port_mode': '',
            'untag_vlan': '',
            'tag_vlan': '',
            'stp': 'off',
            'lag': 'off',
            'consoledata': '',
        }

# class Login(object):
#     def Cisco(self, ip):
#         # 即将 telnet 所要登录的远程主机的域名
#         # 提示符，可能是’ $ ’ , ‘ # ’或’ > :’
#         loginprompt = '[$#>:]'
#         # 拼凑 telnet 命令
#         cmd = 'telnet ' + ip
#         # print('swip---------------------------%s' % ip)
#         # 为 telnet 生成 spawn 类子程序
#         child = pexpect.spawn(cmd, encoding='utf-8')
#         # 期待'login'字符串出现，从而接下来可以输入用户名
#         index = child.expect(["Username:", "(?i)Unknown host", pexpect.EOF, pexpect.TIMEOUT])
#         if (index == 0):
#             # 匹配'login'字符串成功，输入用户名.
#             child.sendline(SwitchAdmin)
#             # 期待 "[pP]assword" 出现.
#             index = child.expect(["Password:", pexpect.EOF, pexpect.TIMEOUT])
#             # 匹配 "[pP]assword" 字符串成功，输入密码.
#             child.sendline(SwitchPass)
#             # 期待提示符出现.
#             child.expect(loginprompt)
#             if (index == 0):
#                 # print(child.before)
#                 return child
#         else:
#             # print(child.before)
#             # 匹配到了 pexpect.EOF 或 pexpect.TIMEOUT，表示超时或者 EOF，程序打印提示信息并退出.
#             print("telnet login failed, due to TIMEOUT or EOF")
#             child.close(force=True)
#             return None
#
#     def Dell(self, ip):
#         loginprompt = '[$#>:]'
#         cmd = 'telnet ' + ip
#         child = pexpect.spawn(cmd, encoding='utf-8')
#         index = child.expect(["Login:", "(?i)Unknown host", pexpect.EOF, pexpect.TIMEOUT])
#         if (index == 0):
#             # 匹配'login'字符串成功，输入用户名.
#             # child.sendline(sw7_11_login_name)
#             child.sendline(SwitchAdmin)
#             # 期待 "[pP]assword" 出现.
#             index = child.expect(["Password:", pexpect.EOF, pexpect.TIMEOUT])
#             # 匹配 "[pP]assword" 字符串成功，输入密码.
#             # child.sendline(sw7_11_login_password)
#             child.sendline(SwitchPass)
#             # 期待提示符出现.
#             child.expect(loginprompt)
#             if (index == 0):
#                 # print(child.before)
#                 # print(child.after)
#                 return child
#         else:
#             print("telnet login failed, due to TIMEOUT or EOF")
#             child.close(force=True)
#             return None


class Cisco(object):
    def __init__(self, refreshpath='',setpath=''):
        self.refreshpath = refreshpath
        self.setpath = setpath

    def Set(self, **kwargs):
        # print('***************************************************************************')
        # try to login switch.
        sw = Switch(kwargs['sw_ip'])
        loginres, child = sw.Cisco_not_bit()
        if not loginres:
            return 'login fail', ['Login core Switch failed']

        child.buffer = ''
        child.sendline(f'show running-config interface {kwargs["sw_port"]}')
        child.expect('#')
        portcheck = child.before
        consolelog = open(self.setpath, 'w+')
        child.logfile = consolelog
        child.sendline('configure terminal')
        child.expect('#')
        child.sendline(f'interface {kwargs["sw_port"]}')
        child.expect('#')
        if kwargs['port_mode'] == 'access':
            if re.findall('switchport trunk', portcheck):
                nativecheck = re.findall('switchport trunk native vlan \d+', portcheck)
                if nativecheck:
                    child.sendline('no ' + nativecheck[0])
                    child.expect('#')
                allowedcheck = re.findall('switchport trunk allowed vlan \d+', portcheck)
                if allowedcheck:
                    child.sendline('no ' + allowedcheck[0])
                    child.expect('#')
                child.sendline('switchport mode access')
                child.expect('#')
                if kwargs["untag_vlan"] == 'UnusedNetwork':
                    child.sendline('switchport access vlan 1')
                    child.expect('#')
                else:
                    child.sendline(f'switchport access vlan {kwargs["untag_vlan"]}')
                    child.expect('#')
                child.sendline(f'description vlab-Vlan{kwargs["untag_vlan"]}')
                child.expect('#')
                child.sendline('switchport nonegotiate')
                child.expect('#')
                child.sendline('no switchport trunk encapsulation dot1q')
                child.expect('#')
            else:
                child.sendline('switchport mode access')
                child.expect('#')
                if kwargs["untag_vlan"] == 'UnusedNetwork':
                    child.sendline('switchport access vlan 1')
                    child.expect('#')
                else:
                    child.sendline(f'switchport access vlan {kwargs["untag_vlan"] }')
                    child.expect('#')
                child.sendline(f'description vlab-Vlan{kwargs["untag_vlan"]}')
                child.expect('#')
                child.sendline('switchport nonegotiate')
                child.expect('#')
            if kwargs["stp"] == 'on':
                child.sendline('spanning-tree portfast')
                child.expect('#')
                child.sendline('spanning-tree bpdufilter disable')
                child.expect('#')
            else:
                child.sendline('spanning-tree portfast')
                child.expect('#')
                # child.sendline('spanning-tree portfast edge')
                # child.expect('#')
                child.sendline('spanning-tree bpduguard enable')
                child.expect('#')
                child.sendline('spanning-tree bpdufilter enable')
                child.expect('#')
            child.sendline('no cdp enable')
            child.expect('#')
        elif kwargs["port_mode"] == 'trunk':
            if re.findall('switchport access vlan', portcheck):
                child.sendline('switchport access vlan 1')
                child.expect('#')
            child.sendline('switchport trunk encapsulation dot1q')
            child.expect('#')
            child.sendline('switchport mode trunk')
            child.expect('#')
            child.sendline('switchport nonegotiate')
            child.expect('#')
            child.sendline('no cdp enable')
            child.expect('#')
            if kwargs["stp"] == 'on':
                child.sendline('spanning-tree portfast trunk')
                child.expect('#')
                child.sendline('spanning-tree bpduguard enable')
                child.expect('#')
                child.sendline('spanning-tree bpdufilter disable')
                child.expect('#')
            else:
                child.sendline('spanning-tree portfast trunk')
                child.expect('#')
                # child.sendline('spanning-tree portfast edge trunk')
                # child.expect('#')
                child.sendline('spanning-tree bpduguard enable')
                child.expect('#')
                child.sendline('spanning-tree bpdufilter enable')
                child.expect('#')
            child.sendline('description vlab-Trunk')
            child.expect('#')
            if kwargs["untag_vlan"] == 'UnusedNetwork':
                child.sendline(f'switchport trunk allow vlan {kwargs["untag_vlan"]}')
                child.expect('#')
                child.sendline('switchport trunk native vlan 1')
                child.expect('#')
            else:
                child.sendline(f'switchport trunk allow vlan {kwargs["untag_vlan"]},{kwargs["tag_vlan"]}')
                child.expect('#')
                # child.sendline(f'switchport trunk allow vlan {kwargs["tag_vlan"]}')
                # child.expect('#')
                child.sendline(f'switchport trunk native vlan {kwargs["untag_vlan"]}')
                child.expect('#')
        child.sendline('shutdown')
        child.expect('#')
        if kwargs["port_power"] == 'reboot':
            child.sendline('shutdown')
            child.expect('#')
            child.sendline('no shutdown')
            child.expect('#')
        else:
            child.sendline(kwargs["port_power"])
            child.expect('#')
        child.sendline('end')
        child.expect('#')
        child.close(force=True)
        with open(self.setpath, 'r') as f:
            consoledata = f.readlines()
        return 'ok', consoledata

    def Refresh(self, ip, port):
        cmdlog = ''
        # print('***************************************************************************')
        # try login switch.
        sw = Switch(ip)
        loginres, child = sw.Cisco_not_bit()
        # print(loginres, child)
        if not loginres:
            refres['msg'] = 'login fail'
            refres['consoledata'] = list(child)
            return refres

        # print('***************************************************************************')
        # send check cmd to switch and save log.
        portsub = re.sub('[a-zA-Z]', '', port)
        show_list = [
            f'show etherchannel summary | include {portsub}',
            f'show interfaces {port} status | include 0',
            f'show running-config interface {port}',
            f'show interfaces {port} | include protocol',
        ]
        child.buffer = ''
        for showcmd in show_list:
            child.sendline(showcmd)
            child.expect('#')
            temp = child.before
            cmdlog += '\r\n' + '*' * 60 + '\r\n' + temp
        # print(cmdlog)
        # recover and write the show print in console
        with open(self.refreshpath, 'a+') as f:
            f.writelines(cmdlog)

        # print('***************************************************************************')
        # check the power status.
        # show show interfaces gi4/21 | include protocol
        # print(len(re.findall('down', cmdlog)))
        if re.search('line protocol is up', cmdlog):
            refres['port_power'] = 'no shutdown'
        elif re.search('error-disabled', cmdlog):
            refres['port_power'] = 'err-disabled'
        elif len(re.findall('down', cmdlog)) == 2:
            refres['port_power'] = 'Abnormal Cable'
        else:
            refres['port_power'] = 'shutdown'

        lagcheck1 = None
        lagcheck2 = None
        for cmdinfo in cmdlog.split('QA_SWITCH_'):
            # check the lag config
            # show etherchannel summary | include 4/21
            # show running-config interface gi4/21
            if f'show etherchannel summary | include {portsub}' in cmdinfo:
                # print('***************************************************************************')
                lagcheck1 = re.findall(portsub + '\(', cmdinfo)
            if f'show running-config interface {port}' in cmdinfo:
                lagcheck2 = re.findall('channel-group', cmdinfo)

            if lagcheck1 or lagcheck2:
                print('Cisco refresh: lag is on----------------')
                child.close(force=True)
                with open(self.refreshpath, 'r+') as f:
                    consoledata = f.readlines()
                lagres = {
                    'msg': 'lag on',
                    'port_power': refres['port_power'],
                    'port_mode': '',
                    'untag_vlan': '',
                    'tag_vlan': '',
                    'stp': 'off',
                    'lag': 'on',
                    'consoledata': consoledata,
                }
                return lagres

            # check stp configure
            # show running-config interface gi4/21
            if f'show running-config interface {port}' in cmdinfo:
                # print(cmdinfo)
                stpline = re.findall('spanning-tree bpdufilter disable', cmdinfo)
                # print('stpstatus-----------------%s' % stpline)
                if stpline:
                    refres['stp'] = 'on'
                else:
                    refres['stp'] = 'off'

            # check sw port status
            # show interfaces gi4/21 status | include 0
            # Gi4/21    vlab-Vlan735       notconnect   735          auto   auto 10/100/1000-TX
            if f'show interfaces {port} status | include 0' in cmdinfo:
                portstatuscheck = re.split(' \s*', cmdinfo)
                if portstatuscheck[-4] == '1' and 'Trunk' not in cmdinfo:
                    child.close(force=True)
                    with open(self.refreshpath, 'r+') as f:
                        consoledata = f.readlines()
                    powerres = {
                        'msg': 'UnusedNetwork',
                        'port_power': refres['port_power'],
                        'port_mode': 'access',
                        'untag_vlan': '1',
                        'tag_vlan': '--',
                        'stp': 'off',
                        'lag': 'off',
                        'consoledata': consoledata,
                    }
                    return powerres

            # switchport mode can not be set in sw, get vlan information.
            # show running-config interface gi4/21
            if f'show running-config interface {port}' in cmdinfo:
                swportmodeline = re.findall('switchport mode \S+', cmdinfo)
                # print('swportmodeline----------------%s' % swportmodeline)
                if not swportmodeline:
                    swportmoderes = {
                        'msg': 'not switchport',
                        'port_power': refres['port_power'],
                        'port_mode': 'access',
                        'untag_vlan': '1',
                        'tag_vlan': '--',
                        'stp': 'off',
                        'lag': 'off',
                        'consoledata': ['the Switch port pre-configured are not fit for the VLAB'],
                    }
                    return swportmoderes
                swportmode = swportmodeline[0].split(' ')[-1]
                # print('swportmode----------------%s' % swportmode)
                refres['tag_vlan'] = '--'
                refres['untag_vlan'] = '--'
                if swportmode == 'trunk':
                    refres['port_mode'] = 'trunk'
                    trunkcheck = re.findall('allowed vlan \S+', cmdinfo)
                    # print('trunkcheck-----------%s' % trunkcheck)
                    if trunkcheck:
                        refres['tag_vlan'] = trunkcheck[0].split('allowed vlan ')[-1]
                    nativecheck = re.findall('native vlan \S+', cmdinfo)
                    # print('nativecheck-----------%s' % nativecheck)
                    if nativecheck:
                        refres['untag_vlan'] = nativecheck[0].split('native vlan ')[-1]
                else:
                    refres['port_mode'] = 'access'
                    accesscheck = re.findall('access vlan \S+', cmdinfo)
                    # print('accesscheck-----------%s' % accesscheck)
                    refres['untag_vlan'] = accesscheck[0].split('access vlan ')[-1]
        # print('port_power=%s, port_mode=%s, native_vlan=%s, ,trunk_vlan=%s, stp=%s' % (
        #     refres['port_power'], refres['port_mode'], refres['untag_vlan'],  refres['tag_vlan'], refres['stp']))
        child.close(force=True)
        with open(self.refreshpath, 'r+') as f:
            refres['consoledata'] = f.readlines()
            # print(consoledata)
        refres['msg'] = 'refresh ok'
        return refres

    def LAGCheck(self, child, port):
        portsub = re.sub('[a-zA-Z]', '', port)
        child.sendline('show etherchannel summary | include ' + portsub)
        child.expect('#')
        portchannel = child.before
        # print('showports---------------\n %s' % showports)
        child.sendline('show running-config interface ' + port)
        child.expect('#')
        showruncfg = child.before
        # print('showruncfg--------------- %s' % showruncfg)
        # check the lag config
        lagcheck1 = re.findall(portsub + '\(', portchannel)
        lagcheck2 = re.findall('channel-group', showruncfg)
        if lagcheck1 or lagcheck2:
            print('Cisco check: lag is on----------------')
            child.close(force=True)
            return 'lag on'
        else:
            # print('Cisco check: lag is off----------------')
            return 'lag off'

    def Initial(self, swip, swport):
        sw = Switch(swip)
        loginres, child = sw.Cisco_not_bit()
        if not loginres:
            return 'fail', ['Login core Switch failed']
        # child = Login().Cisco(swip)
        # if child == None:
        #     return 'fail', None
        lagresult = self.LAGCheck(child, swport)
        if lagresult == 'lag on':
            laginfo = ['LAG is on in Switch, can not initial this port !']
            return 'lag on', laginfo
        else:
            # print(child.before)
            child.sendline('configure terminal')
            child.expect('#')
            child.sendline('interface ' + swport)
            child.expect('#')
            child.sendline('switchport mode access')
            child.expect('#')
            child.sendline('switchport access vlan 1')
            child.expect('#')
            child.sendline('spanning-tree bpdufilter disable')
            child.expect('#')
            child.sendline('spanning-tree bpduguard enable')
            child.expect('#')
            child.sendline('spanning-tree portfast')
            child.expect('#')
            child.sendline('shutdown')
            child.expect('#')
            child.sendline('end')
            child.expect('#')
            # child.sendline('show interface '+swport+' status')
            # child.expect('#')
            # print(child.before)
            child.close(force=True)
            return 'ok', None


class Dell(object):
    def __init__(self, refreshpath='', setpath=''):
        self.refreshpath = refreshpath
        self.setpath = setpath

    def vlan_list(self, vlans):
        if vlans == '--' or vlans == ' ' or vlans == '1':
            return ['--']
        vlanlist = []
        vlans_split = vlans.split(',')
        if len(vlans_split) > 1:
            for i in range(0, len(vlans_split)):
                # print(i)
                vlans_range = vlans_split[i].split('-')
                # print(vlans_range)
                if vlans_range[0].isdigit() is True or vlans_range[-1] is True:
                    for j in range(int(vlans_range[0]), int(vlans_range[-1]) + 1):
                        vlanlist.append(str(j))
            # print(vlanlist)
        else:
            vlanrm = vlans.strip(')')
            vlans_range = vlanrm.split('-')
            if len(vlans_range) > 1:
                if vlans_range[0].isdigit() is True or vlans_range[-1] is True:
                    for j in range(int(vlans_range[0]), int(vlans_range[-1]) + 1):
                        vlanlist.append(str(j))
            else:
                vlanlist.append(vlans_range[0])
        # print('vlanlist---------%s' % vlanlist)
        return vlanlist
    # print(dell_sw_vlan_list('731-734,811-814'))

    def port_list(self, ports, end):
        if len(ports):
            tag = ''
            for i in range(0, len(ports)):
                port_split = ports[i].split(' ')
                tag = port_split[0]
                tmp_str = port_split[-1].split('/')[-1]
                # print('ports: %s, tmp_str: %s, end: %s' % (ports, tmp_str, end))
                tmp_str = Dell().vlan_list(tmp_str)
                if end in tmp_str:
                    # print('tag-------%s' % tag)
                    return tag
            # print('port list-------------%s' % portlist)
            return tag
        else:
            print('ports is empty')
            return False
    # dell_sw_port_list(['T Gi 0/2-5,8', 'T Te 0/49'], '5')

    def Set(self, **kwargs):
        # print('***************************************************************************')
        # try to login switch.
        sw = Switch(kwargs['sw_ip'])
        loginres, child = sw.Dell()
        if not loginres:
            return 'login fail', ['Login core Switch failed']

        # check support-assist and get vlan status.
        # show interfaces gi1/6 status
        # Port                 Description  Status Speed        Duplex Vlan
        # Gi 1/6               vlabVlan739  Up     1000 Mbit    Full   --
        # QA_SWITCH_12
        child.sendline(f'show interfaces {kwargs["sw_port"]} status')
        child.expect('#')
        check_vlan = child.before
        # print('check_vlan----------%s' % check_vlan)
        if 'support-assist' in check_vlan:
            child.expect('#')
            child.sendline(f'show interfaces {kwargs["sw_port"]} status')
            child.expect('#')
            check_vlan = child.before
            # print('check_vlan----------%s' % check_vlan)
        split1 = re.split('\r\n', check_vlan)
        split_check_vlan = re.split(' ', split1[-2])
        # split_check_vlan = [.... '', 'Full', '', '', '--']
        # print('split_check_vlan-------%s' % split_check_vlan)
        # start write console print to set log.
        consolelog = open(self.setpath, 'w+')
        child.logfile = consolelog
        child.sendline('configure terminal')
        child.expect('#')
        # start mutli vlan setting.
        if split_check_vlan[-1] != '--':
            # split_check_vlan[-1]: 104-106,737
            # print(f'split_check_vlan[-1]: {split_check_vlan[-1]}')
            vlan_range = re.split(',', split_check_vlan[-1])
            # vlan_range-----['104-106', '737']
            # print('vlan_range-----%s' % vlan_range)
            for vlanid in vlan_range:
                child.sendline(f'interface range vlan {vlanid}')
                child.expect('#')
                child.sendline(f'no untagged {kwargs["sw_port"]}')
                child.expect('#')
                child.sendline(f'no tagged {kwargs["sw_port"]}')
                child.expect('#')
                child.sendline('exit')
                child.expect('#')

        # start access mode setting.
        if kwargs["port_mode"] == 'access':
            if kwargs["untag_vlan"] == 'UnusedNetwork':
                kwargs["untag_vlan"] = '1'
            # print(kwargs)
            child.sendline(f'interface vlan {kwargs["untag_vlan"]}')
            child.expect('#')
            child.sendline(f'untagged {kwargs["sw_port"]}')
            child.expect('#')
            child.sendline(f'interface {kwargs["sw_port"]}')
            child.expect('#')
            child.sendline(f'description vlabVlan')
            child.expect('#')

        # start trunk mode setting
        elif kwargs["port_mode"] == 'trunk':
            # check mutli tag vlan setting. 104-106,912
            if len(kwargs["tag_vlan"].split(',')) > 1:
                temptagvlan = kwargs["tag_vlan"].split(',')[0]
                for i in range(1, len(kwargs["tag_vlan"].split(','))):
                    temptagvlan = temptagvlan + ',vlan' + kwargs["tag_vlan"].split(',')[i]
                # temptagvlan-------------------104-106,vlan912
                # print('temptagvlan-------------------% s' % temptagvlan)
                child.sendline('interface range vlan' + temptagvlan)
                child.expect('#')
            else:
                child.sendline(f'interface range vlan {kwargs["tag_vlan"]}')
                child.expect('#')
            child.sendline(f'tagged {kwargs["sw_port"]}')
            child.expect('#')
            # start untag vlan setting
            if kwargs["untag_vlan"] != 'UnusedNetwork':
                child.sendline(f'interface vlan {kwargs["untag_vlan"]}')
                child.expect('#')
                child.sendline(f'untagged {kwargs["sw_port"]}')
                child.expect('#')
            child.sendline(f'interface {kwargs["sw_port"]}')
            child.expect('#')
            child.sendline('description vlab-Trunk')
            child.expect('#')
        # start stp setting
        if kwargs["stp"] == 'on':
            child.sendline('spanning-tree mstp edge-port bpduguard shutdown-on-violation')
            child.expect('#')
            child.sendline('spanning-tree rstp edge-port bpduguard shutdown-on-violation')
            child.expect('#')
            child.sendline('spanning-tree')
            child.expect('#')
        else:
            child.sendline('no spanning-tree')
            child.expect('#')
        child.sendline('protocol lldp')
        child.expect('#')
        child.sendline('disable')
        child.expect('#')
        child.sendline('exit')
        child.expect('#')
        # start port power setting
        if kwargs["port_power"] == 'reboot':
            child.sendline('shutdown')
            child.expect('#')
            child.sendline('no shutdown')
            child.expect('#')
        else:
            child.sendline(kwargs["port_power"])
            child.expect('#')
        child.sendline('end')
        child.expect('#')
        child.close(force=True)
        with open(self.setpath, 'r+') as f:
            consoledata = f.readlines()
            # print(consoledata)
        return 'ok', consoledata

    def Refresh(self, ip, port, refresh):
        tags, untags = [], []
        portsub = re.sub('[a-zA-Z]', '', port)
        show_list = [
            f'show running-config interface {port}',
            f'show interfaces {port} status',
            f'show interfaces {port} | grep protocol',
            f'show interfaces port-channel | grep {portsub}',
        ]
        # if the switch enabled support-assist function, must add a extra expect.
        # if 'support-assist' in portchannel:
        #     child.expect('#')
        cmdlog = ''
        # print('***************************************************************************')
        # try login switch.
        sw = Switch(ip)
        loginres, child = sw.Dell()
        if not loginres:
            loginres = {'msg': 'login fail', 'port_power': '', 'port_mode': '', 'untag_vlan': '', 'tag_vlan': '',
                      'stp': 'off', 'lag': 'off', 'consoledata': list(child)}
            return loginres

        # print('***************************************************************************')
        # send check cmd to switch and save log.
        child.buffer = ''
        for showcmd in show_list:
            child.sendline(showcmd)
            child.expect('#')
            temp = child.before
            cmdlog += '\r\n' + '*'*60 + '\r\n' + temp

        # print(cmdlog)
        # recover and write the show print in console
        with open(self.refreshpath, 'a+') as f:
            f.writelines(cmdlog)

        # print('***************************************************************************')
        # check the power status.
        # show interfaces gi1/6 | grep protocol
        if re.search('line protocol is up', cmdlog):
            port_power = 'no shutdown'
        elif re.search('error-disabled', cmdlog):
            port_power = 'err-disabled'
        elif len(re.findall('down', cmdlog)) == 2:
            port_power = 'Abnormal Cable'
        else:
            port_power = 'shutdown'

        # check the lag config.
        # show interfaces port-channel | grep {portsub}
        for cmdinfo in cmdlog.split('QA_SWITCH_'):
            if f'show interfaces port-channel' in cmdinfo:
                lagcheck1 = len(re.findall(portsub, cmdinfo)) - len(re.findall(portsub + '\d', cmdinfo))
                # print(lagcheck1)
                if lagcheck1 > 1 or 'lacp' in cmdlog:
                    print('dell refresh: lag is on----------------')
                    child.close(force=True)
                    with open(self.refreshpath, 'r') as f:
                        consoledata = f.readlines()
                    lagres = {
                        'msg': 'lag on',
                        'port_power': port_power,
                        'port_mode': '',
                        'untag_vlan': '',
                        'tag_vlan': '',
                        'stp': 'off',
                        'lag': 'on',
                        'consoledata': consoledata,
                    }
                    return lagres
        lag = 'off'

        # check switchport mode.
        # show running-config interface gi1/6
        if 'switchport' not in cmdlog:
            child.close(force=True)
            swportres = {
                'msg': 'not switchport',
                'port_power': port_power,
                'port_mode': 'access',
                'untag_vlan': '1',
                'tag_vlan': '--',
                'stp': 'off',
                'lag': 'off',
                'consoledata': ['the Switch port pre-configured are not fit for the VLAB'],
            }
            return swportres

        # check the active vlans.
        # show interfaces gi1/6 status
        port_mode = ''
        for cmdinfo in cmdlog.split('QA_SWITCH_'):
            if f'show interfaces {port} status' in cmdinfo:
                portsplits = re.split('\r\n', cmdinfo)
                if portsplits:
                    portvlans = re.split(' ', portsplits[-2])
                    # print('portvlans**************** %s' % portvlans)
                else:
                    # print('portsplits can not be split. ' + port)
                    child.close(force=True)
                    with open(self.refreshpath, 'r') as f:
                        consoledata = f.readlines()
                    vlanres = {
                        'msg': 'vlan fail',
                        'port_power': port_power,
                        'port_mode': '',
                        'untag_vlan': '',
                        'tag_vlan': '',
                        'stp': 'off',
                        'lag': 'on',
                        'consoledata': consoledata,
                    }
                    return vlanres
                if portvlans:
                    portvlan = portvlans[-1]
                else:
                    portvlan = ''
                if portvlan == '--':
                    vlancheck = '--'
                else:
                    vlancheck = Dell().vlan_list(portvlan)
                # vlancheck------['732', '733', '738', '911']
                # print('vlancheck------%s' % vlancheck)
                # extract sw port name: 3/35
                swport = re.sub('[a-zA-Z]', '', port).replace(' ', '')
                # sw_port-------------1/8
                # print('sw_port-------------%s' % swport)
                first_sport = swport.split('/')[0]
                end_sport = swport.split('/')[-1]
                # port mode judge
                port_mode = ''
                if vlancheck == '--' or vlancheck == '':
                    port_mode = 'access'
                else:
                    tags = []
                    untags = []
                    if len(vlancheck) == 1:
                        # print('check single untag vlan configure print.')
                        child.buffer = ''
                        child.sendline('show vlan id ' + vlancheck[0])
                        child.expect('#')
                        showtag = child.before
                        # increment and write the vlan print in console
                        with open(self.refreshpath, 'a+') as f:
                            f.writelines(cmdlog)
                        tagsearchresult = re.findall('\S \S* ' + first_sport + '\S*', showtag)
                        # print('tagsearchresult----------------%s' % tagsearchresult)
                        port_check = Dell().port_list(tagsearchresult, end_sport)
                        if port_check:
                            if port_check == 'T':
                                # print('check trunk sign in show vlan')
                                tags.append(vlancheck[0])
                                port_mode = 'trunk'
                            else:
                                # print('check access sign in show vlan')
                                untags.append(vlancheck[0])
                                port_mode = 'access'
                        else:
                            print('can not find the port status: %s in vlan: %s' % (swport, vlancheck[0]))
                    else:
                        # print('check tag vlan configure print.')
                        for i in range(0, len(vlancheck)):
                            child.buffer = ''
                            child.sendline('show vlan id ' + vlancheck[i])
                            child.expect('#')
                            showtag = child.before
                            # increment and write the vlan print in console
                            with open(self.refreshpath, 'a+') as f:
                                f.writelines(cmdlog)
                            tagsearchresult = re.findall('\S \S* ' + first_sport + '\S*', showtag)
                            # mutli tagsearchresult------------['U Po1(Gi 1/9-1/10)', 'T Gi 1/8', 'T Te 1/50']
                            # print('mutli tagsearchresult------------%s' % tagsearchresult)
                            tag_check = Dell().port_list(tagsearchresult, end_sport)
                            # mutli tag_check------------T
                            # print('mutli tag_check------------%s' % tag_check)
                            if tag_check:
                                if tag_check == 'T':
                                    # print('TTTTTTTTTTTTT')
                                    tags.append(vlancheck[i])
                                else:
                                    # print('UUUUUUUUUUUUU')
                                    untags.append(vlancheck[i])
                            else:
                                print('can not find the port status: %s in vlan: %s' % (swport, vlancheck[i]))
                        port_mode = 'trunk'

        # check spaning tree
        # show running-config interface gi1/6
        if 'no spanning-tree' in cmdlog or 'spanning-tree mstp' not in cmdlog:
            stp = 'off'
        else:
            stp = 'on'

        # set vlan value
        tags = ','.join(tags)
        if tags == '':
            tags = '--'
        untags = ','.join(untags)
        if untags == '':
            untags = '--'
        if len(tags.split(',')) > 1:
            tags = CombineRanges(tags.split(','), [])
        with open(self.refreshpath, 'r') as f:
            consoledata = f.readlines()
        refres = {
            'msg': 'refresh ok',
            'port_power': port_power,
            'port_mode': port_mode,
            'untag_vlan': untags,
            'tag_vlan': tags,
            'stp': stp,
            'lag': lag,
            'consoledata': consoledata,
        }
        # print(f'port_power={refres["port_power"]}, port_mode={refres["port_mode"]}, untag_vlan={refres["untag_vlan"]}'
        #       f', tag_vlan={refres["tag_vlan"]}, stp={refres["stp"]}, lag={refres["lag"]}')
        return refres

    def LAGCheck(self, child, port):
        portsub = re.sub('[a-zA-Z]', '', port)
        child.sendline('show interfaces port-channel | grep ' + portsub)
        child.expect('#')
        portchannel = child.before
        # print('portchannel--------------- %s' % portchannel)
        if 'support-assist' in portchannel:
            child.expect('#')
        child.sendline('show running-config interface ' + port)
        child.expect('#')
        interport = child.before
        # print('interport--------------- %s' % interport)
        # check the lag config
        lagcheck1 = len(re.findall(portsub, portchannel)) - len(re.findall(portsub + '\d', portchannel))
        lagcheck2 = re.search('lacp', interport)
        # print('lagcheck1: %s, lagcheck2: %s' % (lagcheck1, lagcheck2))
        if lagcheck1 > 1 or lagcheck2:
            print('dell check: lag is on----------------')
            child.close(force=True)
            return 'lag on'
        else:
            return 'lag off'

    def Initial(self, swip, swport):
        sw = Switch(swip)
        loginres, child = sw.Cisco_not_bit()
        if not loginres:
            return 'fail', ['Login core Switch failed']
        # child = Login().Dell(swip)
        # if child == None:
        #     return 'fail', ['Login switch failed !']
        lagresult = self.LAGCheck(child, swport)
        if lagresult == 'lag on':
            laginfo = ['LAG is on in Switch, can not initial this port !']
            return 'lag on', laginfo
        else:
            child.sendline('configure terminal')
            child.expect('#')
            child.sendline('interface range Vlan 10 - 1099')
            child.expect('#')
            child.sendline('no untagged ' + swport)
            child.expect('#')
            child.sendline('no tagged ' + swport)
            child.expect('#')
            child.sendline('interface ' + swport)
            child.expect('#')
            child.sendline('switchport')
            child.expect('#')
            child.sendline('portmode hybrid')
            child.expect('#')
            child.sendline('spanning-tree mstp edge-port bpduguard shutdown-on-violation')
            child.expect('#')
            child.sendline('spanning-tree rstp edge-port bpduguard shutdown-on-violation ')
            child.expect('#')
            child.sendline('shutdown')
            child.expect('#')
            child.sendline('end')
            child.expect('#')
            # child.sendline('show interface '+swport+' status')
            # child.expect('#')
            # print(child.before)
            child.close(force=True)
            return 'ok', None


def sw_port_refresh(swtype, swip, swport, refresh):
    refreshpath = f'users/{current_user.svname}/refreshsw.log'
    with open(refreshpath, 'w+') as f:
        f.writelines(f'Start check {swtype} Switch configure\n' + '='*50)
    if swtype == 'dell':
        # print('dell sw port refresh----------------------------')
        return Dell(refreshpath=refreshpath).Refresh(swip, swport, refresh)
    else:
        # print('cisco sw power refresh----------------------------')
        return Cisco(refreshpath=refreshpath).Refresh(swip, swport)


def sw_port_set(**setting_dict):
    setpath = f'users/{current_user.svname}/setsw.log'
    with open(setpath, 'w+') as f:
        f.writelines(f'Start set {setting_dict["sw_type"]} Switch configure\n' + '='*50)
    if setting_dict['sw_type'] == 'dell':
        # print('start dell sw port set portmode,vlan,stp,lag----------------------------')
        return Dell(setpath=setpath).Set(**setting_dict)
    else:
        # print('start cisco sw port set portmode,vlan,stp,lag----------------------------')
        return Cisco(setpath=setpath).Set(**setting_dict)


def SWInitial(type, swip, swport):
    if type == 'dell':
        return Dell().Initial(swip, swport)
    else:
        # print('initial cisco setting...')
        return Cisco().Initial(swip, swport)

