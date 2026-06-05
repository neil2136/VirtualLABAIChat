#!/usr/bin/env python
import re, os, pexpect, string, time, requests
from bs4 import BeautifulSoup

def SWDevice(dut_id, interface):
    '''
    UTM 180 has the following properties..

    User: xchen
    Owner: xyu (May Yu)
    Product: TZ-500
    SN: C0EAE4AF62E4
    Rack:
    X0 Switch: Core_Switch-10 Port: g3/8
    X1 Switch: Core_Switch-10 Port: g3/9
    X2 Switch: Core_Switch-10 Port: g3/10
    X3 Switch: Core_Switch-10 Port: g3/11
    X4 Switch: Core_Switch-1 Port:
    Power Controller: shg-rwF-rk8a
    Power Channel: AA5
    Console Manager: CM-11
    Telnet: 2024
    SSH: 2024
    :return:
    '''
    # User-Agent信息
    user_agent = r'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.94 Safari/537.36'
    # Headers信息
    header = {'User-Agnet': user_agent, 'Connection': 'keep-alive'}

    r1 = requests.get('http://10.103.2.135:3000/showDevice?devId=' + dut_id +'&kind=UTM', headers=header, verify=False)  # 获得get请求的对象
    s1 = BeautifulSoup(r1.text, 'html.parser')  # 使用bs4解析HTML对象
    #print(r1.text)
    if re.findall('Select a device that EXISTS', s1.text):
        owner = 0
        user = 0
        product = 0
        sn = 0
    else:
        owner = re.findall('Owner: \S+', s1.text)
        if owner == []: owner = ['']
        else:
            owner = owner[0].split(' ')
            #print(owner[-1])
        user = re.findall('User: \S+', s1.text)
        if user == []: user = ['']
        else:
            user = user[0].split(' ')
            #print(user[-1])
        product = re.findall('Product: \S+', s1.text)
        if product == []: product = ['']
        else:
            product = product[0].split(' ')
            #print(product[-1])
        sn = re.findall('SN: \S+', s1.text)
        if sn == []: sn = ['']
        else:
            sn = sn[0].split(' ')
            #print(sn[-1])

        port = interface.split(' ')[-1]
        str = re.findall(('\S+ \S+ \S+ Port: gi' + port) + '|' + ('\S+ \S+ \S+ Port: g' + port), s1.text)
        print('str========%s' % str)
        if len(str) != 0:
            interface = str[0].split(' ')
            print(interface[-1])
        else:
            owner = ['']
            user = ['']
            product = ['']
            sn = ['']
            interface = ['']

    return owner[-1], user[-1], product[-1], sn[-1], interface[0]
#SWDevice('231', 'Gi 0/24')

def getDeviceVlan(dut_id, kind):

    # User-Agent信息
    user_agent = r'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.94 Safari/537.36'
    # Headers信息
    header = {'User-Agnet': user_agent, 'Connection': 'keep-alive'}

    r1 = requests.get('http://10.103.2.135/cgi-bin/getDeviceVlan.cgi?devId=' + dut_id +'&kind=' + kind, headers=header, verify=False)  # 获得get请求的对象
    s1 = BeautifulSoup(r1.text, 'html.parser')  # 使用bs4解析HTML对象
    #print(r1.text)
    data_list = []
    if re.findall('Interface', s1.text):
        for idx, tr in enumerate(s1.find_all('tr')):
            if idx != 0:
                tds = tr.find_all('td')
                # print(tds)
                data_list.append({
                    'Interface': tds[0].contents,
                    'VlabinDB': tds[1].contents,
                    'VlabinSwitch': tds[2].contents,
                    'SwitchName': tds[3].contents,
                    'SwitchPort': tds[4].contents,
                    'PortStatus': tds[5].contents
                })
        # data into a dict
        data_key = sorted(list(data_list[0].keys()))
        for i in range(0, len(data_list)):
            data_list[i]['id'] = str(i + 1)
            for j in range(0, len(data_key)):
                if len(data_list[i][data_key[j]]) == 0:
                    data_list[i][data_key[j]] = ''
                else:
                    data_list[i][data_key[j]] = data_list[i][data_key[j]][0]
        #print(data_list)
        return data_list
    else:
        #print('can not get dut_id %s' % dut_id)
        data_list = []
        return data_list

#getDeviceVlan('180', 'UTM')
def getstplist(dut_id, kind):
    data_list = getDeviceVlan(dut_id, kind)
    for i in range(0, len(data_list)):
        data_list[i].pop('PortStatus')
        data_list[i].pop('VlabinDB')
        data_list[i].pop('VlabinSwitch')
        data_list[i]['stpstatus'] = 0
    #print(data_list)
    return data_list

#getstplist('180', 'UTM')

def Get_DUT_info(data_list):
    data_db_list = []
    if len(data_list) != 0:
        for i in range(0, len(data_list)):
            print(data_list[i]['deviceid'])
            owner, user, product, sn, interface = SWDevice(data_list[i]['deviceid'], data_list[i]['swport'])
            print('owner: %s user: %s product: %s sn: %s' % (owner, user, product, sn))
            data_db_list.append({
                'id': i + 1,
                'deviceid': data_list[i]['deviceid'],
                'swip': data_list[i]['swip'],
                'swport': data_list[i]['swport'],
                'swportstatus': data_list[i]['swportstatus'],
                'vlan': data_list[i]['vlan'],
                'owner': owner,
                'user': user,
                'product': product,
                'sn': sn,
                'interface': interface
            })
    print('data_db_list======%s' % data_db_list)
    return data_db_list

#data_list = [{'vlan': '733', 'swport': 'Gi 0/24', 'id': 1, 'swip': '10.8.0.10', 'swportstatus': 'Down', 'deviceid': '231'}, {'vlan': '733', 'swport': 'Gi 1/34', 'id': 2, 'swip': '10.8.0.10', 'swportstatus': 'Down', 'deviceid': '249'}, {'vlan': '733', 'swport': 'Gi 1/35', 'id': 3, 'swip': '10.8.0.10', 'swportstatus': 'Up', 'deviceid': '249'}, {'vlan': '733', 'swport': 'Gi 2/42', 'id': 4, 'swip': '10.8.0.10', 'swportstatus': 'Down', 'deviceid': '255'}]
#Get_DUT_info(data_list)

def vlabdevice(dut_id):
    # User-Agent信息
    user_agent = r'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.94 Safari/537.36'
    # Headers信息
    header = {'User-Agnet': user_agent, 'Connection': 'keep-alive'}

    r1 = requests.get('http://10.103.2.135:3000/showDevice?devId=' + str(dut_id) +'&kind=UTM', headers=header, verify=False)  # 获得get请求的对象
    s1 = BeautifulSoup(r1.text, 'html.parser')  # 使用bs4解析HTML对象
    #print(s1.text)
    if re.findall('Select a device that EXISTS', s1.text):
        print('can not get %s' % dut_id)
        return None, None, None, None, None
    else:
        powerctrler = re.findall('Power Controller:.*', s1.text)
        if powerctrler == ['powerctrler: ']:
            powerctrler = None
        else:
            powerctrler = powerctrler[0].split('Power Controller: ')[1]

        powerchannel = re.findall('Power Channel:.*', s1.text)
        #print('powerchannel---------> %s' % powerchannel)
        if powerchannel == ['Product: ']:
            powerchannel = None
        else:
            powerchannel = powerchannel[0].split('Power Channel: ')[1]

        product = re.findall('Product:.*', s1.text)
        if product == ['Product: ']:
            product = None
        else:
            product = product[0].split('Product: ')[1]
        #print(product)

        #dutsn = re.findall('SN:.*', s1.text)[0].split()[1]
        dutsn = re.findall('SN:.*', s1.text)
        #print('dutsn---------> %s'% dutsn)
        if dutsn == ['SN: ']:
            dutsn = None
        else:
            dutsn = dutsn[0].split('SN: ')[1]

        dutowner = re.findall('Owner:.*', s1.text)[0].split('Owner: ')[1]
        #print(dutowner)

    return powerctrler, powerchannel, product, dutsn, dutowner
