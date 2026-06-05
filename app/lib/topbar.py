from .mongodb import mongo
from flask_login import current_user
from ..lib.esxi.get_vic_info import GetVICInfo
from ..lib.flashandlog import flash_and_log_error, flash_and_log_info
from datetime import datetime

def GetVMInfo(esxiip, user, password, currentname):
    db = mongo()
    getvmsinfo = GetVICInfo(esxiip, user, password, currentname)
    # print(getvmsinfo)
    for vminfo in getvmsinfo:
        vminfo['owner'] = currentname
        vminfo['user'] = currentname
        vminfo['esxihost'] = esxiip
        db.insert_one('EsxiVMs', vminfo)
    return 'ok'

def DelVM(esxiip):
    db =mongo

def SearchDeviceVLAN(vlanid):
    db = mongo()
    fwinfos = []
    if vlanid == '4095':
        fwsearch = db.find_by_multi_field('DUT', 'User', current_user.svname, 'InterfaceInfo.Interface.' + 'portmode',
                                          'trunk')
        spsearch = db.find_by_multi_field('SonicPoint', 'User', current_user.svname,
                                          'InterfaceInfo.Interface.' + 'portmode', 'trunk')
        searchall = fwsearch + spsearch
        # print(searchall)
        if searchall == []:
            pass
            # flash_and_log_error('VLAN Search Result: Can not find the VLAN %s in all devices Interface !' % vlanid)
        else:
            for searchone in searchall:
                afwinfo = {}
                portlist = searchone['InterfaceInfo']['Interface']
                for portinfo in portlist:
                    if portinfo['portmode'] == 'trunk':
                        afwinfo['DeviceType'] = searchone['DeviceType']
                        afwinfo['id'] = searchone['id']
                        afwinfo['Product'] = searchone['Product']
                        afwinfo['SN'] = searchone['SN']
                        afwinfo['Owner'] = searchone['Owner']
                        afwinfo['User'] = searchone['User']
                        afwinfo['name'] = portinfo['name']
                        afwinfo['untagvlan'] = portinfo['untagvlan']
                        afwinfo['portmode'] = portinfo['portmode']
                        afwinfo['tagvlan'] = portinfo['tagvlan']
                        afwinfo['portpower'] = portinfo['portpower']
                        fwinfos.append(afwinfo)
                    afwinfo = {}
    else:
        fwsearch = db.find_many('DUT', 'InterfaceInfo.Interface.' + 'untagvlan', vlanid)
        spsearch = db.find_many('SonicPoint', 'InterfaceInfo.Interface.' + 'untagvlan', vlanid)
        searchall = fwsearch + spsearch
        if searchall == []:
            pass
            # flash_and_log_error('VLAN Search Result: Can not find the VLAN %s in all devices Interface !' % vlanid)
        else:
            for searchone in searchall:
                afwinfo = {}
                portlist = searchone['InterfaceInfo']['Interface']
                for portinfo in portlist:
                    if portinfo['untagvlan'] == vlanid:
                        afwinfo['DeviceType'] = searchone['DeviceType']
                        afwinfo['id'] = searchone['id']
                        afwinfo['Product'] = searchone['Product']
                        afwinfo['SN'] = searchone['SN']
                        afwinfo['Owner'] = searchone['Owner']
                        afwinfo['User'] = searchone['User']
                        afwinfo['name'] = portinfo['name']
                        afwinfo['untagvlan'] = vlanid
                        afwinfo['portmode'] = portinfo['portmode']
                        afwinfo['tagvlan'] = portinfo['tagvlan']
                        afwinfo['portpower'] = portinfo['portpower']
                        fwinfos.append(afwinfo)
                    afwinfo = {}
    # print(searchall)

    return fwinfos

def DelTransfer(duttype, dutid, borrower, lender, status):
    db = mongo()

def TransferLog():
    db = mongo()
    transferlist = db.find_many('transferdevices', 'lender', current_user.svname)
    transfercont = len(transferlist)
    if transferlist:
        transferlist = sorted(transferlist, key=lambda i: i['ts'], reverse=True)
    return transferlist, transfercont

def TransferDevice(duttype, dutid, borrower, lender, status):
    db = mongo()
    if duttype == 'DUT':
        duttype = 'Firewall'
    times = datetime.now().ctime()
    doct = {'deviceType': duttype, 'deviceId': dutid, 'borrower': borrower, 'lender': lender, 'status': status, 'ts': times}
    db.insert_one('transferdevices', doct)
    return 'ok'



