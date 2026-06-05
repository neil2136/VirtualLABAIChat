from flask import render_template, redirect, url_for, abort, request, \
    jsonify, session
from flask_login import login_required
from flask_sqlalchemy import get_debug_queries
from . import main
from ..email import send_cdu_email, dut_change_user_email, send_pwd_email, send_all_email, ticket_email, send_vlab_pwd_email
from ..lib.fwlogin import *
from ..lib.flashandlog import LogSorted, long_tasks_log, LongTasksLogSorted, flash_and_log_info, flash_and_log_error, \
    LogAndCounts
from ..lib.serversslcfg import *
from ..lib.switchcfg import *
from ..lib.dutpowercfg import dutpowercfg, judgeduttype
from ..lib.mydevices import RegetDUTInfo, DUTPortRefresh, UpdateDBInterfaces, DeviceVLANCheckInDB, VMsVLANCheckInDB, \
    MyVMVLANRange
from ..lib.sidebar import GetSidebarList, GetVMsName, RefreshDUT, RefreshVM, RefreshVLAN, RefreshG7
from ..lib.topbar import GetVMInfo, SearchDeviceVLAN, TransferDevice, TransferLog
from ..lib.mongodb import mongo
from ..lib.esxi.get_vic_info import GetVICInfo, SyncAVMNic
from ..lib.esxi.getvminfo import SyncAVM, SyncAllVM, SyncMyVM
from ..lib.esxi.vmconfig import ChangeVLANAndPower
from ..lib.esxi.portgroup_to_vswitch import ESXIPortGroups
from ..lib.esxi.change_vm_name import ChangeVMName
from ..lib.esxi.change_vm_vlan import ChangeVMVlan
from ..lib.esxi.vm_power_control import VMPowerCtrl
from ..lib.cductrl import CDU
from ..lib.labdut import InsertPowerAndCMIp
from .tasks import *
from datetime import datetime
from ..lib.changepwd import LDAPSettings
from ..lib.esxi.vmlogin import RestartAdapter


# from concurrent.futures import ThreadPoolExecutor
# from config import Config
# import json

@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    db = mongo()

    totals = db.find_one('deshboard', 'id', 'totals')
    userlogs = db.find_all('userlog', 'user')
    if userlogs:
        userlogs = sorted(userlogs, key=lambda i: i['unixtime'], reverse=True)
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()

    # Deshboard list
    deshs = db.find_one('deshboard', 'id', 'userconfcount')
    userconfcounts = deshs['userlist']

    topdevices = db.find_one('deshboard', 'id', 'topdevice')
    topdevice = topdevices['devicelist']

    topusers = db.find_one('deshboard', 'id', 'topuser')
    topuser = topusers['userlist']

    # allg7dut = db.find_all('DUT', 'id')
    # for dutinfo in allg7dut:
    #     # print(dutinfo)
    #     db.update_one('DUT', 'id', dutinfo['id'], 'FWScripts', 'yes')

    return render_template('index.html', **locals())
    # return render_template('index.html', mydeviceslist=mydevicesget(), fwfilters=fwfilters, spfilters=spfilters, lentlist=lentlist, myvmslist=GetVMsName(), totals=totals, userlogs=userlogs)


@main.route('/refreshdut', methods=['GET', 'POST'])
@login_required
def refreshdut():
    RefreshDUT()
    flash_and_log_info('DUT Configure: Refresh Firewall and SonicPoint List successful !')
    return redirect(url_for('.myhome'))

@main.route('/refreshg7', methods=['GET', 'POST'])
@login_required
def refreshg7():
    g7res = RefreshG7('mydevice')
    if g7res == 'ok':
        flash_and_log_info('Processing Refresh Gen7 Firewall information,Please check result in Long Tasks Log. ')
    else:
        flash_and_log_info(g7res)
    return redirect(url_for('.asynctasklog'))

@main.route('/refreshvm', methods=['GET', 'POST'])
@login_required
def refreshvm():
    RefreshVM()
    flash_and_log_info('DUT Configure: Refresh VM List from DB successful !')
    return redirect(url_for('.index'))


@main.route('/refreshvlan', methods=['GET', 'POST'])
@login_required
def refreshvlan():
    RefreshVLAN()
    flash_and_log_info('DUT Configure: Refresh VLAN from DB List successful !')
    return redirect(url_for('.index'))


@main.route('/refreshdesh', methods=['GET', 'POST'])
@login_required
def refreshdesh():
    db = mongo()
    dutcount = len(db.find_all('DUT', 'id')) + len(db.find_all('SonicPoint', 'id'))
    print('dutcount: %s' % dutcount)
    db.update_one('deshboard', 'id', 'totals', 'sonicwall', str(dutcount))
    esxicount = len(db.find_all('ESX', 'id'))
    print('esxicount: %s' % esxicount)
    db.update_one('deshboard', 'id', 'totals', 'esxi', str(esxicount))
    vmcount = len(db.find_all('VM', 'uuid'))
    print('vmcount: %s' % vmcount)
    db.update_one('deshboard', 'id', 'totals', 'vm', str(vmcount))
    swcount = len(db.find_all('Switch', 'id'))
    print('swcount: %s' % swcount)
    db.update_one('deshboard', 'id', 'totals', 'switch', str(swcount))
    effectivecount = len(db.find_many('configlog', 'effective', '1'))
    print('effectivecount: %s' % effectivecount)
    db.update_one('deshboard', 'id', 'totals', 'effective', str(effectivecount))
    invalidcount = len(db.find_many('configlog', 'effective', '0'))
    print('invalidcount: %s' % invalidcount)
    db.update_one('deshboard', 'id', 'totals', 'invalid', str(invalidcount))
    userlogcount = len(db.find_all('userlog', 'action'))
    print('userlogcount: %s' % userlogcount)
    db.update_one('deshboard', 'id', 'totals', 'visits', str(userlogcount))

    userlist = []
    userlists = db.find_many('User', 'Group', 'QA2')
    for user in userlists:
        usercount = db.find_many('configlog', 'svname', user['svname'])
        userlist.append({'User': user['svname'], 'Count': len(usercount)})
    print(userlist)
    db.update_one('deshboard', 'id', 'userconfcount', 'userlist', userlist)

    devicelists = {}
    deshlogs = db.find_all('configlog', 'device')
    for deshlog in deshlogs:
        if deshlog['device'] not in devicelists:
            devicelists[deshlog['device']] = 1
        else:
            devicelists[deshlog['device']] = devicelists[deshlog['device']] + 1
    devicelist = sorted(devicelists.items(), key=lambda keys: (keys[1], keys[0]), reverse=True)
    # print(devicelist)
    topdevice = []
    if len(devicelist) > 5:
        maxcount = devicelist[0][1]
        top1 = {'name': devicelist[0][0], 'count': devicelist[0][1], 'rate': 100}
        topdevice.append(top1)
        for i in range(1, 5):
            rate = devicelist[i][1] / maxcount * 100
            secdevice = {'name': devicelist[i][0], 'count': devicelist[i][1], 'rate': int(rate)}
            topdevice.append(secdevice)
        print(topdevice)
        db.update_one('deshboard', 'id', 'topdevice', 'devicelist', topdevice)
    else:
        flash_and_log_info('Can not find top 5 devices in devices log !')

    userlists = {}
    deshlogs = db.find_all('configlog', 'svname')
    for deshlog in deshlogs:
        if deshlog['svname'] not in userlists:
            userlists[deshlog['svname']] = 1
        else:
            userlists[deshlog['svname']] = userlists[deshlog['svname']] + 1
    userlist = sorted(userlists.items(), key=lambda keys: (keys[1], keys[0]), reverse=True)
    print(userlist)
    topuser = []
    if len(userlist) > 5:
        maxcount = userlist[0][1]
        top1 = {'name': userlist[0][0], 'count': userlist[0][1], 'rate': 100}
        topuser.append(top1)
        for i in range(1, 5):
            rate = userlist[i][1] / maxcount * 100
            secdevice = {'name': userlist[i][0], 'count': userlist[i][1], 'rate': int(rate)}
            topuser.append(secdevice)
        print(topuser)
        db.update_one('deshboard', 'id', 'topuser', 'userlist', topuser)
    else:
        flash_and_log_info('Can not find top 5 user in devices log !')

    flash_and_log_info('Deshboard Configure: Refresh Firewall and SonicPoint totals successful !')
    return redirect(url_for('.index'))


@main.route('/deltransfer', methods=['POST'])
@login_required
def deltransfer():
    db = mongo()
    devicetype = request.form['deviceType']
    deviceid = request.form['deviceId']
    ts = request.form['ts']
    print('deviceType: %s, deviceId: %s, ts: %s' % (devicetype, deviceid, ts))
    findts = db.find_one('transferdevices', 'ts', ts)
    if findts:
        db.delete_one('transferdevices', 'ts', ts)
    flash_and_log_info('Transfer Devices: Deleted %s: %s log successful !' % (devicetype, deviceid))
    return redirect(url_for('.index'))


@main.route('/showlabvlans', methods=['GET', 'POST'])
@login_required
def showlabvlans():
    db = mongo()
    # vmname = request.args.get('vmname')
    vmname = 'centos7(237-240)'
    # print(vmname)
    frompage = 'myvms'
    vmsinfo = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vmname', vmname)
    vlanranges = MyVMVLANRange()

    dutlists = db.find_many('DUT', 'User', current_user.svname)
    splists = db.find_many('SonicPoint', 'User', current_user.svname)
    mylists = dutlists + splists
    convids = []
    for aid in mylists:
        convid = int(aid['id'])
        aid['id'] = convid
        convids.append(aid)
    dutinfo = sorted(convids, key=lambda keys: keys['id'])

    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('labmgmt/showlabvlans.html', **locals())


@main.route('/labdut', methods=['GET', 'POST'])
@login_required
def labdut():
    db = mongo()
    user_check = db.find_one('User', 'id', current_user.svname)

    if request.method == 'POST':
        operate = request.form['operate']
        if operate == 'Add':
            product = request.form['product']
            duttype = request.form['duttype']
            sn = request.form['sn']
            sncheck = db.find_one('cubedut', 'sn', sn)
            if sncheck:
                LogAndCounts('Cubedut', 'Operated', 'Add the cube device SN %s is exist in DB  !' % sn, 0)
                return redirect(url_for('.cubedut'))
            authenticationcode = request.form['authenticationcode']
            owner = request.form['owner']
            findall = db.find_all_sort('cubedut', 'id', 'up')
            insetdata = {'id': findall[-1]['id'] + 1, 'product': product, 'classify': '', 'type': duttype,
                         'sn': sn, 'authenticationcode': authenticationcode, 'registrationcode': '',
                         'maintenancekey': '', 'owner': owner, 'tackup': 'released', 'user': 'NA'}
            if duttype == 'G7':
                classify = request.form['classify']
                registrationcode = request.form['registrationcode']
                maintenancekey = request.form['maintenancekey']
                insetdata['classify'] = classify
                insetdata['registrationcode'] = registrationcode
                insetdata['maintenancekey'] = maintenancekey
            elif duttype == 'G6':
                registrationcode = request.form['registrationcode']
                insetdata['registrationcode'] = registrationcode
            elif duttype == 'SP':
                pass
            db.insert_one('cubedut', insetdata)
            LogAndCounts('Cubedut', 'Operated', 'Add the cube device SN %s Successful  !' % sn, 1)
        elif operate == 'Edit':
            dutid = request.form['id']
            product = request.form['product']
            duttype = request.form['duttype']
            sn = request.form['sn']
            authenticationcode = request.form['authenticationcode']
            owner = request.form['owner']

            orgdutinfo = db.find_one('cubedut', 'id', int(dutid))
            insetdata = {'id': int(dutid), 'product': product, 'classify': '', 'type': duttype,
                         'sn': sn, 'authenticationcode': authenticationcode, 'registrationcode': '',
                         'maintenancekey': '', 'owner': owner, 'tackup': orgdutinfo['tackup'],
                         'user': orgdutinfo['user']}
            if duttype == 'G7':
                classify = request.form['classify']
                registrationcode = request.form['registrationcode']
                maintenancekey = request.form['maintenancekey']
                insetdata['classify'] = classify
                insetdata['registrationcode'] = registrationcode
                insetdata['maintenancekey'] = maintenancekey
            elif duttype == 'G6':
                registrationcode = request.form['registrationcode']
                insetdata['registrationcode'] = registrationcode
            elif duttype == 'SP':
                pass
            db.delete_one('cubedut', 'id', int(dutid))
            db.insert_one('cubedut', insetdata)
            LogAndCounts('Cubedut', 'Operated', 'Edit the cube device ID %s Successful  !' % dutid, 1)
        elif operate == 'Delete':
            dutid = request.form['id']
            db.delete_one('cubedut', 'id', int(dutid))
            LogAndCounts('Cubedut', 'Operated', 'Delete the cube device ID %s Successful  !' % dutid, 1)
        elif operate == 'takeup':
            dutid = request.form['id']
            owner = request.form['owner']
            if owner == 'occupied':
                getdutinfo = db.find_one('cubedut', 'id', int(dutid))
                # print(getdutinfo)
                ownerinfo = db.find_one('User', 'fullname', getdutinfo['owner'])
                db.update_one('cubedut', 'id', int(dutid), 'tackup', owner)
                db.update_one('cubedut', 'id', int(dutid), 'user', current_user.fullname)
                cuberesult = db.find_many('cubedut', 'id', int(dutid))
                print(cuberesult)
                dut_change_user_email(ownerinfo['email'], 'Device transaction notification', 'mail/cubedutborrow',
                                      cuberesult, ownerinfo['fullname'])
                LogAndCounts('Cubedut', 'Operated', 'Occupied the DUT id %s successfully !' % dutid, 1)
                cubedata = db.find_one('cubedut', 'id', 1)
            elif owner == 'released':
                getdutinfo = db.find_one('cubedut', 'id', int(dutid))
                db.update_one('cubedut', 'id', int(dutid), 'tackup', owner)
                db.update_one('cubedut', 'id', int(dutid), 'user', 'NA')
                cuberesult = db.find_many('cubedut', 'id', int(dutid))
                ownerinfo = db.find_one('User', 'fullname', getdutinfo['owner'])
                dut_change_user_email(ownerinfo['email'], 'Device transaction notification', 'mail/cubedutreturn',
                                      cuberesult, ownerinfo['fullname'])
                LogAndCounts('Cubedut', 'Operated', 'Released the DUT id %s successfully !' % dutid, 1)

    # dutinfo = db.find_all('DUT', 'id')
    fwinfo = db.find_all_lab_dut('DUT', 'id')
    # fwinfo = InsertPowerAndCMIp(dutinfo)

    # spsinfo = db.find_all('SonicPoint', 'id')
    spinfo = db.find_all_lab_dut('SonicPoint', 'id')
    # spinfo = InsertPowerAndCMIp(spsinfo)

    users = current_user.svname
    # alluser = db.find_many('User', 'Group', 'QA2')
    # alluser = sorted(alluser, key=lambda keys: keys['fullname'])
    # logs = LogSorted()
    # transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('labmgmt/labdut.html', **locals())


@main.route('/cubedut', methods=['GET', 'POST'])
@login_required
def cubedut():
    db = mongo()
    user_check = db.find_one('User', 'id', current_user.svname)
    if request.method == 'POST':
        operate = request.form['operate']
        if operate == 'Add':
            product = request.form['product']
            duttype = request.form['duttype']
            sn = request.form['sn']
            sncheck = db.find_one('cubedut', 'sn', sn)
            if sncheck:
                LogAndCounts('Cubedut', 'Operated', 'Add the cube device SN %s is exist in DB  !' % sn, 0)
                return redirect(url_for('.cubedut'))
            authenticationcode = request.form['authenticationcode']
            owner = request.form['owner']
            findall = db.find_all_sort('cubedut', 'id', 'up')
            insetdata = {'id': findall[-1]['id'] + 1, 'product': product, 'classify': '', 'type': duttype,
                         'sn': sn, 'authenticationcode': authenticationcode, 'registrationcode': '',
                         'maintenancekey': '', 'owner': owner, 'tackup': 'released', 'user': 'NA'}
            if duttype == 'G7':
                classify = request.form['classify']
                registrationcode = request.form['registrationcode']
                maintenancekey = request.form['maintenancekey']
                insetdata['classify'] = classify
                insetdata['registrationcode'] = registrationcode
                insetdata['maintenancekey'] = maintenancekey
            elif duttype == 'G6':
                registrationcode = request.form['registrationcode']
                insetdata['registrationcode'] = registrationcode
            elif duttype == 'SP':
                pass
            db.insert_one('cubedut', insetdata)
            LogAndCounts('Cubedut', 'Operated', 'Add the cube device SN %s Successful  !' % sn, 1)
        elif operate == 'Edit':
            dutid = request.form['id']
            product = request.form['product']
            duttype = request.form['duttype']
            sn = request.form['sn']
            authenticationcode = request.form['authenticationcode']
            owner = request.form['owner']
            orgdutinfo = db.find_one('cubedut', 'id', int(dutid))
            insetdata = {'id': int(dutid), 'product': product, 'classify': '', 'type': duttype,
                         'sn': sn, 'authenticationcode': authenticationcode, 'registrationcode': '',
                         'maintenancekey': '', 'owner': owner, 'tackup': orgdutinfo['tackup'],
                         'user': orgdutinfo['user']}
            if duttype == 'G7':
                classify = request.form['classify']
                registrationcode = request.form['registrationcode']
                maintenancekey = request.form['maintenancekey']
                insetdata['classify'] = classify
                insetdata['registrationcode'] = registrationcode
                insetdata['maintenancekey'] = maintenancekey
            elif duttype == 'G6':
                registrationcode = request.form['registrationcode']
                insetdata['registrationcode'] = registrationcode
            elif duttype == 'SP':
                pass
            db.delete_one('cubedut', 'id', int(dutid))
            db.insert_one('cubedut', insetdata)
            LogAndCounts('Cubedut', 'Operated', 'Edit the cube device ID %s Successful  !' % dutid, 1)
        elif operate == 'Delete':
            dutid = request.form['id']
            db.delete_one('cubedut', 'id', int(dutid))
            LogAndCounts('Cubedut', 'Operated', 'Delete the cube device ID %s Successful  !' % dutid, 1)
        elif operate == 'takeup':
            dutid = request.form['id']
            owner = request.form['owner']
            if owner == 'occupied':
                getdutinfo = db.find_one('cubedut', 'id', int(dutid))
                # print(getdutinfo)
                ownerinfo = db.find_one('User', 'fullname', getdutinfo['owner'])
                db.update_one('cubedut', 'id', int(dutid), 'tackup', owner)
                db.update_one('cubedut', 'id', int(dutid), 'user', current_user.fullname)
                cuberesult = db.find_many('cubedut', 'id', int(dutid))
                print(cuberesult)
                dut_change_user_email(ownerinfo['email'], 'Device transaction notification', 'mail/cubedutborrow',
                                      cuberesult, ownerinfo['fullname'])
                LogAndCounts('Cubedut', 'Operated', 'Occupied the DUT id %s successfully !' % dutid, 1)
                cubedata = db.find_one('cubedut', 'id', 1)
            elif owner == 'released':
                getdutinfo = db.find_one('cubedut', 'id', int(dutid))
                db.update_one('cubedut', 'id', int(dutid), 'tackup', owner)
                db.update_one('cubedut', 'id', int(dutid), 'user', 'NA')
                cuberesult = db.find_many('cubedut', 'id', int(dutid))
                ownerinfo = db.find_one('User', 'fullname', getdutinfo['owner'])
                dut_change_user_email(ownerinfo['email'], 'Device transaction notification', 'mail/cubedutreturn',
                                      cuberesult, ownerinfo['fullname'])
                LogAndCounts('Cubedut', 'Operated', 'Released the DUT id %s successfully !' % dutid, 1)
    # cubedata = db.find_one('cubedut', 'id', 1)
    # cubedata['sn'] = '2CB8ED9Dxxxx'
    alluser = db.find_many('User', 'Group', 'QA2')
    alluser = sorted(alluser, key=lambda keys: keys['fullname'])
    g7fwlist = db.find_many_sort('cubedut', 'type', 'G7', 'id', 'down')
    g6fwlist = db.find_many_sort('cubedut', 'type', 'G6', 'id', 'down')
    spfwlist = db.find_many_sort('cubedut', 'type', 'SP', 'id', 'down')
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('labmgmt/cubedut.html', **locals())


@main.route('/myhome', methods=['GET', 'POST'])
@login_required
def myhome():
    db = mongo()
    user_check = db.find_one('User', 'id', current_user.svname)
    # cubedata = db.find_one('cubedut', 'id', 1)
    # cubedata['sn'] = '2CB8ED9Dxxxx'
    alluser = db.find_many('User', 'Group', 'QA2')
    alluser = sorted(alluser, key=lambda keys: keys['fullname'])
    alldut = db.find_many_sort('DUT', 'User', current_user.svname, 'id', 'up')

    g7list = db.find_by_multi_field('DUT', 'User', current_user.svname, 'ProductType', 'G7')
    g7sortlist = sorted(g7list, key=lambda keys: keys['id'])

    g7fwlist = db.find_many_sort('DUT', 'type', 'G7', 'id', 'down')
    g6fwlist = db.find_many_sort('cubedut', 'type', 'G6', 'id', 'down')
    spfwlist = db.find_many_sort('cubedut', 'type', 'SP', 'id', 'down')
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('myhome/myhome.html', **locals())


@main.route('/allg7status', methods=['GET', 'POST'])
@login_required
def allg7status():
    db = mongo()
    g7fwlist = db.find_many_sort('DUT', 'ProductType', 'G7', 'id', 'up')
    newg7list = []
    for g7fw in g7fwlist:
        del g7fw['InterfaceInfo']
        del g7fw['ConsoleInfo']
        del g7fw['PowerInfo']
        if 'FWStatus' in g7fw.keys():
            newg7list.append(g7fw)
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('vlabadmin/allg7status.html', **locals())


@main.route('/devicesearch', methods=['GET', 'POST'])
@login_required
def devicesearch():
    db = mongo()
    if request.method == 'POST':
        duttype = request.form['type']
        searchby = request.form['searchby']
        keyword = request.form['keyword']
        print('type: %s, searchby: %s, keyword: %s' % (duttype, searchby, keyword))
        if searchby == 'all':
            dutsinfo = db.find_all(duttype, 'id')
            dutinfo = InsertPowerAndCMIp(dutsinfo)
            flash_and_log_info('Operated Result: Device Search Finished ！type: %s Searchby: %s Keyword: %s ' % (
            duttype, searchby, keyword))
        elif duttype == 'DUT':
            if searchby == 'id':
                fwinfo = db.find_many(duttype, searchby, keyword)
            elif searchby == 'Product':
                keyword = keyword.upper()
                fwinfo = db.find_by_regex(duttype, searchby, keyword)
            elif searchby == 'Owner':
                capkeyword = keyword.capitalize()
                fwinfo = db.find_by_regex(duttype, searchby, keyword) + db.find_by_regex(duttype, searchby, capkeyword)
            else:
                fwinfo = db.find_by_regex(duttype, searchby, keyword)
            fwinfo = InsertPowerAndCMIp(fwinfo)
            flash_and_log_info(
                'Operated Result: DUT Search Finished ！type: %s Searchby: %s Keyword: %s ' % (
                duttype, searchby, keyword))
        elif duttype == 'SonicPoint':
            if searchby == 'id':
                spinfo = db.find_many(duttype, searchby, keyword)
            elif searchby == 'Product':
                keyword = keyword.upper()
                spinfo = db.find_by_regex(duttype, searchby, keyword)
            elif searchby == 'Owner':
                capkeyword = keyword.capitalize()
                spinfo = db.find_by_regex(duttype, searchby, keyword) + db.find_by_regex(duttype, searchby, capkeyword)
            else:
                spinfo = db.find_by_regex(duttype, searchby, keyword)
            spinfo = InsertPowerAndCMIp(spinfo)
            flash_and_log_info(
                'Operated Result: SonicPoint Search Finished ！type: %s Searchby: %s Keyword: %s ' % (
                duttype, searchby, keyword))
        elif duttype == 'VM':
            if searchby == 'mac':
                vminfo = db.find_many(duttype, 'nicsinfo.' + searchby, keyword)
                layerkey = 'mac'
            else:
                vminfo = db.find_many(duttype, searchby, keyword)
            frompage = 'devicesearch'
            if vminfo == []:
                flash_and_log_error('VM Search Result: Can not find the VM Owner %s in all VMs NIC !' % keyword)
            else:
                flash_and_log_info('VM Search Result: Search type: %s VM Owner: %s Finished ！' % (duttype, keyword))

            # logs = LogSorted()
            transferlist, transfercont = TransferLog()
            fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
            return render_template('topsearch/vmsearch.html', **locals())
        else:
            dutinfo = []
            flash_and_log_error('Device Search Result: Only support search SonicWall and SonicPoint !')
        productinfo = db.find_many('filter', 'type', 'firewall')
        userfilter = db.find_all('User', 'id')
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        return render_template('labmgmt/labdut.html', **locals())
    return redirect(url_for('.index'))


@main.route('/vlansearch', methods=['GET', 'POST'])
@login_required
def vlansearch():
    db = mongo()
    duttype = ''
    vlanid = ''
    vlanlist = []
    if request.method == 'POST':
        duttype = request.form['searchtype']
        vlanid = request.form['searchvlan']
        if ',' in vlanid:
            vlanlist += vlanid.split(',')
        pagefrom = 'top'
    else:
        duttype = request.args.get('searchtype')
        vlanid = request.args.get('searchvlan')
        portmode = request.args.get('portmode')
        # print('portmode:     '+portmode)
        if portmode == 'trunk':
            vlanid = 'trunk_4095'
        pagefrom = 'deviceid'
    print('duttype: %s, vlanid: %s' % (duttype, vlanid))
    # vlanranges = MyVMVLANRange()
    if duttype == 'vm':
        if vlanlist:
            vminfo = []
            for vlan in vlanlist:
                vminfo += db.find_many('VM', 'nicsinfo.vlan', vlan)
            vminfo = sorted(vminfo, key=lambda keys: keys['esxihost'], reverse=False)
        else:
            vminfo = db.find_many('VM', 'nicsinfo.vlan', vlanid)
            vlanlist.append(vlanid)
        if not vminfo:
            flash_and_log_error('VLAN Search Result: Can not find the VLAN %s in all VMs NIC !' % vlanid)
        else:
            flash_and_log_info('VLAN Search Result: Search type: %s vlanid: %s Finished ！' % (duttype, vlanid))
        frompage = 'vlansearch'
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        return render_template('topsearch/searchall.html', **locals())
    elif duttype == 'device':
        if vlanlist:
            fwinfos = []
            for vlan in vlanlist:
                fwinfos += SearchDeviceVLAN(vlan)
            fwinfos = sorted(fwinfos, key=lambda keys: keys['id'], reverse=False)
        else:
            fwinfos = SearchDeviceVLAN(vlanid)
        flash_and_log_info('Operated Result: VLAN Search Finished ! type: %s vlanid: %s' % (duttype, vlanid))
        frompage = 'devicesearch'
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        return render_template('topsearch/searchall.html', **locals())
    elif duttype == 'searchall':
        if vlanlist:
            vminfo = []
            fwinfos = []
            for vlan in vlanlist:
                vminfo += db.find_many('VM', 'nicsinfo.vlan', vlan)
                fwinfos += SearchDeviceVLAN(vlan)
            vminfo = sorted(vminfo, key=lambda keys: keys['esxihost'], reverse=False)
            fwinfos = sorted(fwinfos, key=lambda keys: keys['id'], reverse=False)
        else:
            vminfo = db.find_many('VM', 'nicsinfo.vlan', vlanid)
            vlanlist.append(vlanid)
            fwinfos = SearchDeviceVLAN(vlanid)

        # vminfo = db.find_many('VM', 'nicsinfo.vlan', vlanid)
        # if not vminfo:
        #     flash_and_log_error('VLAN Search Result: Can not find the VLAN %s in all devices NIC !' % vlanid)
        # fwinfos = SearchDeviceVLAN(vlanid)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        flash_and_log_info('Operated Result: VLAN Search Finished ! type: %s, vlanid: %s' % (duttype, vlanid))
        return render_template('topsearch/searchall.html', **locals())
    return redirect(url_for('.index'))


@main.route('/resetvlan', methods=['POST'])
@login_required
def resetvlan():
    db = mongo()
    duttype = request.form['devicetype']
    dutid = request.form['deviceid']
    portname = request.form['devicename']
    untagid = request.form['portvlan']
    portmode = request.form['portmode']
    if portmode == 'trunk':
        untagid = 'trunk_4095'
    print('duttype:{},dutid:{},portname:{},untagid:{},portmode:{}'.format(duttype, dutid, portname, untagid, portmode))

    dutinfo = db.find_one(duttype, 'id', dutid)
    portline = dutinfo['InterfaceInfo']['Interface']
    for intname in portline:
        if intname['name'] == portname:
            porttype = intname['porttype']
            swfind = db.find_one('Switch', 'id', intname['SwitchID'])
            swip = swfind['ConsoleServer']
            swchannel = intname['SwitchPort']
            setting_dict = {'sw_type': porttype, 'sw_ip': swip, 'sw_port': swchannel,
                            'port_mode': intname['portpower'], 'port_status': 'access',
                            'untag_vlan': 'UnusedNetwork', 'tag_vlan': 1, 'stp': 'on',
                            'port_power': intname['portpower']}
            logindbg, consoledata = sw_port_set(**setting_dict)
            # logindbg, consoledata = sw_port_set(porttype, swip, swchannel, intname['portpower'], 'access',
            #                                     'UnusedNetwork', 1, 'on',
            #                                     intname['portpower'])
            eventhead = 'Configure Result(type %s, id %s, interface %s): ' % (duttype, dutid, portname)
            if logindbg == 'ok':
                UpdateDBInterfaces(dutid, duttype, portname, 'access', 'UnusedNetwork', 1, 'on', intname['portpower'])
                LogAndCounts(duttype, dutinfo['Product'],
                             eventhead + 'DUT Port Setting successfully ！SW Port ' + swip + ':' + swchannel, 1)
            else:
                LogAndCounts(duttype, dutinfo['Product'],
                             eventhead + 'DUT Port Setting failed ！SW Port ' + swip + ':' + swchannel, 1)

    if portmode == 'trunk':
        untagid = '4095'
    vminfo = db.find_many('VM', 'nicsinfo.vlan', untagid)
    fwinfos = SearchDeviceVLAN(untagid)
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('topsearch/searchall.html', **locals())


@main.route('/myvms', methods=['GET', 'POST'])
@login_required
def myvms():
    db = mongo()
    vmname = request.args.get('vmname')
    operate = request.args.get('operate')
    if operate == 'refreshvmnics':
        esxiip = request.args.get('esxihost')
        if esxiip:
            esx = db.find_one('ESX', 'IPAddress', esxiip)
            syncsvm = SyncAVM(esxiip, esx['AdminUser'], esx['AdminPass'], vmname, current_user.svname)
            if syncsvm:
                db.delete_one('VM', 'uuid', syncsvm['uuid'])
                instrst = db.insert_one('VM', syncsvm)
                if instrst:
                    LogAndCounts('VM', vmname, 'Sync VM NICs information successful !', 1)
                else:
                    LogAndCounts('VM', vmname, 'Sync VM NICs information to DB failed !', 0)
            else:
                LogAndCounts('VM', vmname, 'Can not find the VM name %s in esxi %s' % (vmname, esxiip), 0)
        else:
            LogAndCounts('VM', vmname,
                         'Can not find the VM NICs in DB, Please sync VMs information in top menu first !', 0)
    vminfo = db.find_one('VM', 'vmname', vmname)
    frompage = 'myvms'
    vlanranges = MyVMVLANRange()
    logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('myhome/myvms.html', **locals())


@main.route('/vmcfg', methods=['GET', 'POST'])
@login_required
def vmcfg():
    db = mongo()
    vlanranges = MyVMVLANRange()
    if request.method == 'POST':
        esxiip = request.form['esxihost']
        vmname = request.form['vmname']
        adapter = request.form['adapter']
        mac = request.form['mac']
        vlan = request.form['vlan']
        nicpower = request.form['nicpower']
        frompage = request.form['from']
        if vlan == 'UnusedNetwork':
            portgroup = 'UnusedNetwork'
        elif vlan == 'trunk_4095':
            portgroup = 'trunk_4095'
        else:
            portgroup = current_user.svname + '_vlan' + vlan
        esx = db.find_one('ESX', 'IPAddress', esxiip)
        # changeresult = ChangeVMVlan(esxiip, esx['AdminUser'], esx['AdminPass'], vmname, adapter, portgroup, nicpower)
        changeresult = ChangeVLANAndPower(esxiip, esx['AdminUser'], esx['AdminPass'], vmname, adapter, portgroup,
                                          nicpower)
        if changeresult == 'success':
            db.update_subkey('VM', 'vmname', vmname, 'nicsinfo', 'mac', mac, 'vlan', vlan)
            db.update_subkey('VM', 'vmname', vmname, 'nicsinfo', 'mac', mac, 'portgroup', portgroup)
            db.update_subkey('VM', 'vmname', vmname, 'nicsinfo', 'mac', mac, 'nicpower', nicpower)
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s Successfully !' % (
                esx['IPAddress'], vmname, adapter, portgroup), 1)
        else:
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s failed !' % (
                esx['IPAddress'], vmname, adapter, portgroup), 0)
        # logs = LogSorted()
        if frompage == 'mydevices':
            vminfo = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vlan', vlan)
        else:
            vminfo = db.find_one('VM', 'vmname', vmname)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        return render_template('myhome/myvms.html', **locals())
    vlan = request.args.get('vlan')
    portmode = request.args.get('portmode')
    frompage = request.args.get('from')
    # print('untag: %s, portmode: %s' % (untag, portmode))
    if portmode == 'trunk':
        vmsfilter = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vlan', 'trunk_4095')
    else:
        vmsfilter = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vlan', vlan)
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('myhome/myvms.html', **locals())


'''
@main.route('/changevmvlan', methods=['GET', 'POST'])
@login_required
def changevmvlan():
    db = mongo()
    vlanranges = MyVMVLANRange()
    if request.method == 'POST':
        esxiip = request.form['esxiip']
        vmname = request.form['vmname']
        adapter = request.form['adapter']
        mac = request.form['mac']
        vlan = request.form['vlan']
        untag = request.form['untag']
        frompage = request.form['from']
        # print('vmname: %s, adapter: %s, mac: %s vlan: %s' % (vmname, adapter, mac, vlan))
        # VMVLANSet(vmname, adapter, mac, vlan)
        # LogAndCounts('VM', vmname, 'Modified the '+adapter+' to VLAN '+vlan+' Successfully !', 1)
        if vlan == 'UnusedNetwork':
            portgroup = 'UnusedNetwork'
        elif vlan == 'trunk_4095':
            portgroup = 'trunk_4095'
        else:
            portgroup = current_user.svname + '_vlan' + vlan
        esx = db.find_one('ESX', 'IPAddress', esxiip)
        changeresult = ChangeVMVlan(esxiip, esx['AdminUser'], esx['AdminPass'], vmname, adapter, portgroup)
        if changeresult == 'success':
            db.update_one('EsxiVMs', 'mac', mac, 'vlan', vlan)
            db.update_one('EsxiVMs', 'mac', mac, 'portgroup', portgroup)
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s Successfully !' % (
                esx['IPAddress'], vmname, adapter, portgroup), 1)
        else:
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s failed !' % (
                esx['IPAddress'], vmname, adapter, portgroup), 0)
        logs = LogSorted()
        if frompage == 'mydevices':
            vmsinfo = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vlan', untag)
            logs = LogSorted()
            transferlist, transfercont = TransferLog()
            fwfilters, spfilters, lentlist, vmlists, vlanlists = GetSidebarList()
            return render_template('myhome/myvms.html', **locals())
        else:
            vmsinfo = db.find_many('EsxiVMs', 'vmname', vmname)
            logs = LogSorted()
            transferlist, transfercont = TransferLog()
            fwfilters, spfilters, lentlist, vmlists, vlanlists = GetSidebarList()
            return render_template('myhome/myvms.html', **locals())
    untag = request.args.get('untag')
    portmode = request.args.get('portmode')
    frompage = request.args.get('from')
    # print('untag: %s, portmode: %s' % (untag, portmode))
    if portmode == 'trunk':
        vmsfilter = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vlan', 'trunk_4095')
    else:
        vmsfilter = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vlan', untag)
    # vmsinfo = db.find_many('EsxiVMs', 'owner', current_user.svname)
    logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists = GetSidebarList()
    return render_template('myhome/myvms.html', **locals())
'''


@main.route('/syncmyvm', methods=['GET', 'POST'])
@login_required
def syncmyvm():
    db = mongo()
    if request.method == 'POST':
        # executor = ThreadPoolExecutor(1)
        getuserinfo = db.find_one('User', 'svname', current_user.svname)
        db.delete_many('VM', 'owner', current_user.svname)
        for esxiip in getuserinfo['ESXServer']:
            esx = db.find_one('ESX', 'IPAddress', esxiip)
            syncallvm = SyncMyVM(esxiip, esx['AdminUser'], esx['AdminPass'], current_user.svname)
            db.insert_many('VM', syncallvm)
        flash_and_log_info(
            'Operated Result: Refresh and Update the ESX %s VMs information to DB running ! Please check the process in Operated Log.' % esxiip)
    RefreshVM()
    return redirect(url_for('.index'))


@main.route('/syncallvm', methods=['GET', 'POST'])
@login_required
def syncallvm():
    db = mongo()
    esxlist = db.find_all('ESX', 'IPAddress')
    i = 0
    for esx in esxlist:
        i += 1
        print(i, esx['IPAddress'], esx['AdminUser'], esx['AdminPass'], current_user.svname)
        async_allexsivm.apply_async((esx['IPAddress'], esx['AdminUser'], esx['AdminPass']))
        time.sleep(1)
    # async_syncallvm.apply_async((esxlist[2]['IPAddress'], esxlist[2]['AdminUser'], esxlist[2]['AdminPass'], current_user.svname))
    flash_and_log_info('Sync VM progressing ! Please check the process in Operated Log.')
    logs = LongTasksLogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('log/asynctasklog.html', **locals())


'''
@main.route('/syncvm', methods=['GET', 'POST'])
@login_required
def syncvm():
    global taskid, getvmstatus, esxiip
    db = mongo()
    if request.method == 'POST':
        # executor = ThreadPoolExecutor(1)
        esxiip = request.form['esxiip']
        if esxiip == None:
            flash_and_log_info('Input Error: Please selete a vaild ESXi IP !')
            return redirect(url_for('.index'))
        if esxiip == 'all':
            getuserinfo = db.find_one('User', 'svname', current_user.svname)
            db.delete_many('EsxiVMs', 'owner', current_user.svname)
            for aip in getuserinfo['ESXServer']:
                aesx = db.find_one('ESX', 'IPAddress', aip)
                long_tasks_log('ESX', 'RefreshVMs', 'ESX %s Operated: Start update VMs information... ' % aesx['IPAddress'])
                async_getesxvminfo.delay(aesx['IPAddress'], aesx['AdminUser'], aesx['AdminPass'], current_user.svname)
            flash_and_log_info('Operated Result: Refresh and Update all VMs information to DB running ! Please check the process in Operated Log.')
        else:
            db.delete_many_multi('VM', 'esxihost', esxiip, 'owner', current_user.svname)
            esx = db.find_one('ESX', 'IPAddress', esxiip)
            syncallvm = SyncMyVM(esxiip, esx['AdminUser'], esx['AdminPass'], current_user.svname)
            for vminfo in syncallvm:
                db.insert_one('VM', vminfo)

            # db.delete_many_multi('EsxiVMs', 'esxihost', esxiip, 'owner', current_user.svname)
            # aesx = db.find_one('ESX', 'IPAddress', esxiip)
            # # executor.submit(GetVMInfo(esxiip, aesx['AdminUser'], aesx['AdminPass']))
            # long_tasks_log('ESX', 'RefreshVMs', 'ESX %s Operated: Start update VMs information... ' % aesx['IPAddress'])
            # # print(aesx['IPAddress'], aesx['AdminUser'], aesx['AdminPass'], current_user.svname)
            # # GetVICInfo(aesx['IPAddress'], aesx['AdminUser'], aesx['AdminPass'], current_user.svname)
            # task_process = async_getesxvminfo.apply_async((aesx['IPAddress'], aesx['AdminUser'], aesx['AdminPass'], current_user.svname))
            flash_and_log_info('Operated Result: Refresh and Update the ESX %s VMs information to DB running ! Please check the process in Operated Log.' % esxiip)
    logs = LongTasksLogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists = GetSidebarList()
    return render_template('log/asynctasklog.html', **locals())
'''


@main.route('/changevmname', methods=['POST'])
@login_required
def changevmname():
    db = mongo()
    vmname = request.form['vmname']
    newname = request.form['newname']
    if vmname == '' or newname == '':
        LogAndCounts('VM', vmname, 'Input Error: Please choose and input a valid vm old name and new name !', 0)
        return redirect(url_for('.index'))
    vmcheck = db.find_one('VM', 'vmname', vmname)
    if vmcheck is None:
        LogAndCounts('VM', vmname,
                     'Changed VMname %s to %s failed, Can not find vmname in DB, Please Sync VMs From Vcenter first !' % (
                     vmname, newname), 0)
        return redirect(url_for('.index'))
    if newname == vmname:
        LogAndCounts('VM', vmname,
                     'Changed VMname %s to %s failed, new name cannot same with old name !' % (vmname, newname), 0)
        return redirect(url_for('.index'))
    esxinfo = db.find_one('ESX', 'IPAddress', vmcheck['esxihost'])
    state = ChangeVMName(vmcheck['esxihost'], esxinfo['AdminUser'], esxinfo['AdminPass'], vmname, newname)
    print(state)
    if state == 'success':
        db.delete_one('VM', 'vmname', vmname)
        getvminfo = SyncAVM(vmcheck['esxihost'], esxinfo['AdminUser'], esxinfo['AdminPass'], newname,
                            current_user.svname)
        if getvminfo:
            db.insert_one('VM', getvminfo)
            LogAndCounts('VM', vmname, 'Operated Result: Changed VMname %s to %s successful !' % (vmname, newname), 1)
    else:
        LogAndCounts('VM', vmname, 'Operated Result: Changed VMname %s to %s failed !' % (vmname, newname), 0)
    return redirect(url_for('.index'))


'''
@main.route('/refreshallnic', methods=['GET', 'POST'])
@login_required
def refreshallnic():
    db = mongo()
    vmname = request.form['vmname']
    print(vmname)

    vmsinfo = getvmnics(vmname)
    GetVICInfo(vmsinfo[0]['esxihost'], current_user.svname)

    frompage = 'myvms'
    vlanranges = MyVMVLANRange()
    logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists = GetSidebarList()
    return render_template('myhome/myvms.html', **locals())
'''


@main.route('/vmpowerctrl', methods=['GET', 'POST'])
@login_required
def vmpowerctrl():
    db = mongo()
    if request.method == 'POST':
        vmname = request.form['vmname']
        operate = request.form['operate']
        frompage = request.form['frompage']
        if vmname == 'none' or operate == 'none':
            LogAndCounts('VM', vmname, 'Input Error: Please choose a valid vmname and operate !', 0)
            return redirect(url_for('.index'))
        vmcheck = db.find_one('EsxiVMs', 'vmname', vmname)
        if vmcheck is None:
            LogAndCounts('VM', vmname,
                         'Changed VM %s to %s failed, Can not find vmname in DB, Please Refresh VMs in VLAB first !' % (
                         vmname, operate), 0)
            return redirect(url_for('.index'))
        esxinfo = db.find_one('ESX', 'IPAddress', vmcheck['esxihost'])
        state = VMPowerCtrl(vmcheck['esxihost'], esxinfo['AdminUser'], esxinfo['AdminPass'], vmname, operate)
        if state == 'success':
            if operate == 'poweredOff':
                db.update_one('VM', 'vmname', vmname, 'vmpower', 'poweredOff')
            else:
                db.update_one('VM', 'vmname', vmname, 'vmpower', 'poweredOn')
            LogAndCounts('VM', vmname, 'VMname %s to %s successful !' % (vmname, operate), 1)
        else:
            LogAndCounts('VM', vmname, 'VMname %s to %s failed !' % (vmname, operate), 0)
        if frompage == 'myvms':
            vminfo = db.find_one('VM', 'vmname', vmname)
            vlanranges = MyVMVLANRange()
            # logs = LogSorted()
            transferlist, transfercont = TransferLog()
            fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
            return render_template('myhome/myvms.html', **locals())
    return redirect(url_for('.index'))


@main.route('/mydeviceinfo', methods=['GET', 'POST'])
@login_required
def mydeviceinfo():
    db = mongo()
    cdu = CDU()
    consoledata = {}
    deviceid = request.args.get('id')
    devicetype = request.args.get('type')
    adeviceget = db.find_one(devicetype, 'id', deviceid)
    # print(adeviceget)

    deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
    # print(deviceinfo)
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    # print(vmvlanpool)
    return render_template('myhome/mydevices.html', **locals())


@main.route('/devicepool', methods=['GET', 'POST'])
@login_required
def devicepool():
    db = mongo()
    cdu = CDU()
    consoledata = {}
    deviceid = request.args.get('id')
    devicetype = request.args.get('type')
    adeviceget = db.find_one(devicetype, 'id', deviceid)
    usercheck = True if current_user.svname in adeviceget['User'] else False

    username = current_user.svname
    publicduts = db.find_one('GlobalConfig', 'id', 'Public_DUT_Settings')
    publicdutlist = publicduts['disable_configure_dut_list']
    VMsVLANCheckInDB(devicetype, deviceid)
    deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('myhome/devicepool.html', **locals())


@main.route('/commentconf', methods=['GET', 'POST'])
@login_required
def commentconf():
    db = mongo()
    cdu = CDU()
    consoledata = {}
    if request.method == 'POST':
        deviceid = request.form['deviceid']
        devicetype = request.form['devicetype']
        tagpage = request.form['tagpage']
        comment = request.form['comment']
        # print('deviceid: %s, devicetype: %s' % (deviceid, devicetype))
        getdevice = db.find_one(devicetype, 'id', deviceid)
        if comment:
            newcomment = comment + ' ---' + datetime.now().ctime()
        else:
            newcomment = comment
        db.update_one(devicetype, 'id', deviceid, 'Comment', newcomment)
        flash_and_log_info('Update the comment successful! new is: %s' % newcomment)

        adeviceget = db.find_one(devicetype, 'id', deviceid)
        usercheck = True if current_user.svname in adeviceget['User'] else False

        VMsVLANCheckInDB(devicetype, deviceid)
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        if tagpage == 'mydevices':
            return render_template('myhome/mydevices.html', **locals())
        else:
            return render_template('myhome/devicepool.html', **locals())
    return redirect(url_for('.index'))

@main.route('/savedfwpwd', methods=['GET', 'POST'])
@login_required
def savedfwpwd():
    db = mongo()
    cdu = CDU()
    consoledata = {}
    if request.method == 'POST':
        deviceid = request.form['deviceid']
        devicetype = request.form['devicetype']
        tagpage = request.form['tagpage']
        savedfwpwd = request.form['changepwd']
        print('deviceid: %s, devicetype: %s' % (deviceid, devicetype))
        getdevice = db.find_one(devicetype, 'id', deviceid)
        db.update_one(devicetype, 'id', deviceid, 'savedfwpwd', savedfwpwd)
        flash_and_log_info('Update the fw password successful! new is: %s' % savedfwpwd)

        adeviceget = db.find_one(devicetype, 'id', deviceid)
        usercheck = True if current_user.svname in adeviceget['User'] else False

        VMsVLANCheckInDB(devicetype, deviceid)
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        if tagpage == 'mydevices':
            return render_template('myhome/mydevices.html', **locals())
        else:
            return render_template('myhome/devicepool.html', **locals())
    return redirect(url_for('.index'))

@main.route('/publicuserconfig', methods=['GET', 'POST'])
@login_required
def publicuserconfig():
    db = mongo()
    cdu = CDU()
    consoledata = {}
    if request.method == 'POST':
        deviceid = request.form['deviceid']
        operate = request.form['operate']
        # print('deviceid: %s, operate: %s' % (deviceid, operate))
        getdevice = db.find_one('DUT', 'id', deviceid)
        if operate == 'join':
            newuser = getdevice['User'] + ',' + current_user.svname
            db.update_one('DUT', 'id', deviceid, 'User', newuser.strip(','))
            flash_and_log_info(
                'joined the current user in User group list successful ! new user is: %s' % newuser.strip(','))
        elif operate == 'leave':
            usersplit = getdevice['User'].split(',')
            if usersplit:
                newuser = ''
                for auser in usersplit:
                    if auser != current_user.svname:
                        newuser += auser + ','
                db.update_one('DUT', 'id', deviceid, 'User', newuser.strip(','))
                flash_and_log_info(
                    'Leaved the current user in User group list successful ! new user is: %s' % newuser.strip(','))

        adeviceget = db.find_one('DUT', 'id', deviceid)
        usercheck = True if current_user.svname in adeviceget['User'] else False

        VMsVLANCheckInDB('DUT', deviceid)
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo('DUT', deviceid)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        return render_template('myhome/devicepool.html', **locals())
    return redirect(url_for('.index'))


@main.route('/mydeviceid', methods=['GET', 'POST'])
@login_required
def mydeviceid():
    deviceid = request.args.get('id')
    devicetype = request.args.get('type')
    operateauth = request.args.get('operateauth')
    deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
    # vlan_ranges = CombineRanges(user_check['AdminVLAN'], user_check['VLAN'])
    consoledata = {}
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    if deviceinfo['Owner'] == 'Public':
        return render_template('myhome/devicepool.html', **locals())
    return render_template('myhome/mydevices.html', **locals())


@main.route('/dutportrefresh', methods=['GET', 'POST'])
@login_required
def dutportrefresh():
    if request.method == 'POST':
        deviceid = request.form['id']
        devicetype = request.form['devicetype']
        dutportname = request.form['portname']
        operate = request.form['operate']
        dutpool = request.form['dutpool']
        # print(deviceid, devicetype, dutportname, operate, dutpool)
        consoledata = DUTPortRefresh(deviceid, devicetype, dutportname, operate)

        DeviceVLANCheckInDB(devicetype, deviceid, dutportname)
        VMsVLANCheckInDB(devicetype, deviceid)
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
        RefreshVLAN()
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        if dutpool == 'enabled':
            return render_template('myhome/devicepool.html', **locals())
        return render_template('myhome/mydevices.html', **locals())
    return redirect(url_for('.index'))


@main.route('/dutportcfg', methods=['GET', 'POST'])
@login_required
def dutportcfg():
    if request.method == 'POST':
        deviceid = request.form['deviceid']
        devicetype = request.form['devicetype']
        dutportname = request.form['portname']
        portmode = request.form['portmode']
        untagvlan = request.form['untagvlan']
        if portmode == 'access':
            tagvlan = '--'
        else:
            tagvlan = request.form['tagvlan']
        stp = request.form['stp']
        lag = request.form['lag']
        if untagvlan == 'UnusedNetwork' and portmode != 'trunk':
            portpower = 'shutdown'
        else:
            portpower = request.form['portpower']
        dutpool = request.form['dutpool']
        deviceinfo = db.find_one(devicetype, 'id', deviceid)
        # print('lag------%s' % lag)
        eventhead = 'Configure Result(type %s, id %s, interface %s): ' % (devicetype, deviceid, dutportname)
        if lag == 'on':
            LogAndCounts(devicetype, deviceinfo['Product'], eventhead + 'Commit warning: the LAG is on in Switch !', 0)
        else:
            if untagvlan in SplitRanges(tagvlan) and portmode == 'trunk':
                LogAndCounts(devicetype, deviceinfo['Product'],
                             eventhead + 'Trunk Input warning: Untag VLAN can not included in Tag VLAN pool !', 0)
            else:
                adeviceget = db.find_one(devicetype, 'id', deviceid)
                # print(adeviceget)
                portline = adeviceget['InterfaceInfo']['Interface']
                for intname in portline:
                    if intname['name'] == dutportname:
                        porttype = intname['porttype']
                        swfind = db.find_one('Switch', 'id', intname['SwitchID'])
                        swip = swfind['ConsoleServer']
                        swchannel = intname['SwitchPort']
                        # std_link = os.system('ping -c 2 ' + swfind['ConsoleServer'])
                        # if std_link:
                        #     LogAndCounts(devicetype, adeviceget['Product'], eventhead + 'Ping SW Failed !', 0)
                        if untagvlan == '1':
                            LogAndCounts(devicetype, adeviceget['Product'],
                                         eventhead + 'First Operated: Must press Refresh SW button to get the Switch setting first !',
                                         0)
                        else:
                            setting_dict = {'sw_type': porttype, 'sw_ip': swip, 'sw_port': swchannel,
                                            'port_mode': portmode, 'port_status': intname['portpower'],
                                            'untag_vlan': untagvlan, 'tag_vlan': tagvlan, 'stp': stp,
                                            'port_power': portpower}
                            logindbg, consoledata = sw_port_set(**setting_dict)
                            if logindbg == 'login fail':
                                LogAndCounts(devicetype, adeviceget['Product'],
                                             eventhead + 'Login Failed. Can not Telnet to switch !', 0)
                            # dutportrefresh(id, type, dutport, operate)
                            else:
                                if portmode == 'access':
                                    tagvlan = '--'
                                UpdateDBInterfaces(deviceid, devicetype, dutportname, portmode, untagvlan, tagvlan,
                                                   stp, portpower)
                                LogAndCounts(devicetype, adeviceget['Product'],
                                             eventhead + 'DUT Port Setting successfully ！SW Port ' + swip + ':' + swchannel,
                                             1)
        DeviceVLANCheckInDB(devicetype, deviceid, dutportname)
        VMsVLANCheckInDB(devicetype, deviceid)
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
        RefreshVLAN()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        if dutpool == 'enabled':
            return render_template('myhome/devicepool.html', **locals())
        return render_template('myhome/mydevices.html', **locals())
    return redirect(url_for('.index'))


@main.route('/dutvmcfg', methods=['GET', 'POST'])
@login_required
def dutvmcfg():
    if request.method == 'POST':
        deviceid = request.form['deviceid']
        devicetype = request.form['devicetype']
        vmname = request.form['vmname']
        vmnic = request.form['vmnic']
        vlan = request.form['untagvlan']
        # portmode = request.form['portmode']
        dutpool = request.form['dutpool']
        if vlan == 'trunk_4095':
            portgroup = 'trunk_4095'
        elif vlan == 'UnusedNetwork':
            portgroup = 'UnusedNetwork'
        else:
            portgroup = current_user.svname + '_vlan' + vlan
        adapter = 'Network adapter ' + vmnic.split(' ')[-1]
        vminfo = db.find_by_multi_field('EsxiVMs', 'vmname', vmname, 'adapter', adapter)[0]
        esx = db.find_one('ESX', 'IPAddress', vminfo['esxihost'])
        changeresult = ChangeVLANAndPower(vminfo['esxihost'], esx['AdminUser'], esx['AdminPass'], vmname,
                                          vminfo['adapter'], portgroup, 'keep')
        if changeresult == 'success':
            db.update_one('VM', 'mac', vminfo['mac'], 'vlan', vlan)
            db.update_one('VM', 'mac', vminfo['mac'], 'portgroup', portgroup)
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s Successfully !' % (
                esx['IPAddress'], vmname, vminfo['adapter'], portgroup), 1)
        else:
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s failed !' % (
                esx['IPAddress'], vmname, vminfo['adapter'], portgroup), 0)

        VMsVLANCheckInDB(devicetype, deviceid)
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        if dutpool == 'enabled':
            return render_template('myhome/devicepool.html', **locals())
        return render_template('myhome/mydevices.html', **locals())
    return redirect(url_for('.index'))


@main.route('/refreshallport', methods=['GET', 'POST'])
@login_required
def refreshallport():
    consoledata = {}
    db = mongo()
    if request.method == 'POST':
        deviceid = request.form['dutid']
        devicetype = request.form['duttype']
        dutpool = request.form['dutpool']
        # print('deviceid: %s, devicetype: %s' % (deviceid, devicetype))
        deviceinfos = db.find_one(devicetype, 'id', deviceid)
        interfaces = deviceinfos['InterfaceInfo']['Interface']
        for interace in interfaces:
            DUTPortRefresh(deviceid, devicetype, interace['name'], 'refreshall')
            DeviceVLANCheckInDB(devicetype, deviceid, interace['name'])
        LogAndCounts(devicetype, devicetype, 'Refresh all DUT Ports Setting Successful ！', 1)

        VMsVLANCheckInDB(devicetype, deviceid)
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        RefreshVLAN()
        if dutpool == 'enabled':
            return render_template('myhome/devicepool.html', **locals())
        return render_template('myhome/mydevices.html', **locals())
    return redirect(url_for('.index'))


@main.route('/dutreboot', methods=['GET', 'POST'])
@login_required
def dutreboot():
    if request.method == 'POST':
        dutid = request.form['id']
        duttype = request.form['type']
        print('dutid: %s, duttype: %s' % (dutid, duttype))
        powercfgresult = dutpowercfg(dutid, 'Reboot', duttype)
        if powercfgresult == 'ok':
            flash_and_log_info('The operate: reboot DUT ID: %s, type: %s Successfully !' % (dutid, duttype))
        else:
            flash_and_log_error(
                'The operate: reboot DUT ID: %s, type: %s Failed ! Please try again later.' % (dutid, duttype))
    return redirect(url_for('.index'))


@main.route('/ndppcfg', methods=['POST'])
@login_required
def ndppcfg():
    if request.method == 'POST':
        dutid = request.form['id']
        duttype = request.form['type']
        dutip = request.form['dutip']
        dutuser = request.form['dutuser']
        dutpwd = request.form['dutpwd']
        print(f'dutid: {dutid}, duttype: {duttype}, dutip: {dutip}, dutuser: {dutuser}, dutpwd: {dutpwd}')
        if not dutid or not duttype or not dutip or not dutuser or not dutpwd:
            flash_and_log_error(f'Must input valid value in ndpp configure page !!!')
            return redirect(url_for('.index'))
        adeviceget = db.find_one(duttype, 'id', dutid)
        consoleip = db.find_one('ConsoleManager', 'id', adeviceget['ConsoleInfo']['ConsoleManager'])
        adeviceget['ConsoleInfo']['ip'] = consoleip['IPAddress']
        if adeviceget['ProductType'] == 'G7':
            pass
            task_process = async_ndppconfig.apply_async((dutip,
                                                         consoleip['IPAddress'],
                                                         adeviceget['ConsoleInfo']['TelnetPort'],
                                                         dutuser, dutpwd, adeviceget, current_user.svname))
            print(f'run ndpp configure to long task finished. task_process: {task_process}')
        else:
            flash_and_log_error(f'Must choose G7 DUT to enable ndpp and required input do not empty !!!')
        return redirect(url_for('.asynctasklog'))

    return redirect(url_for('.index'))


@main.route('/dutborrow', methods=['POST'])
@login_required
def dutborrow():
    db = mongo()
    dutid = request.form['dut_id']
    duttype = request.form['duttype']
    print('dut_id: %s, duttype: %s' % (dutid, duttype))
    getdutinfo = db.find_one(duttype, 'id', dutid)
    ownerinfo = db.find_one('User', 'svname', getdutinfo['User'])
    db.update_one(duttype, 'id', dutid, 'User', current_user.svname)

    dutfilter = db.find_many(duttype, 'id', dutid)
    dut_change_user_email(ownerinfo['email'], 'Device transaction notification', 'mail/dutborrow', dutfilter,
                          ownerinfo['fullname'])
    LogAndCounts(duttype, getdutinfo['Product'], 'Borrowed Device id ' + dutid + ' successfully !', 1)

    # reset all ports to UnusedNetwork
    long_tasks_log('DUT', 'BorrowDUT', 'Borrow DUT %s Process: Start Initial Ports...' % dutid)
    task_process = async_initialdutports.apply_async((getdutinfo, 'Borrow', current_user.svname))

    lender = db.find_one('User', 'fullname', getdutinfo['Owner'])
    TransferDevice(duttype, dutid, current_user.svname, lender['svname'], 'borrowed')
    refreshdut()
    logs = LongTasksLogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('log/asynctasklog.html', **locals())


@main.route('/dutreturn', methods=['POST'])
@login_required
def dutreturn():
    db = mongo()
    dutid = request.form['id']
    duttype = request.form['type']
    print('dut_id: %s, duttype: %s' % (dutid, duttype))
    getdutinfo = db.find_one(duttype, 'id', dutid)
    print(getdutinfo['Owner'])
    ownerinfo = db.find_one('User', 'fullname', getdutinfo['Owner'])
    print(ownerinfo)
    db.update_one(duttype, 'id', dutid, 'User', ownerinfo['svname'])
    dutfilter = db.find_many(duttype, 'id', dutid)
    dut_change_user_email(ownerinfo['email'], 'Device transaction notification', 'mail/dutreturn', dutfilter,
                          getdutinfo['User'])
    LogAndCounts(duttype, getdutinfo['Product'], 'Retruned Device id ' + dutid + ' successfully !', 1)

    # reset all ports to UnusedNetwork
    long_tasks_log('DUT', 'RetrunDUT', 'Return DUT %s Process: Start Initial Ports...' % dutid)
    async_initialdutports.apply_async((getdutinfo, 'Return', current_user.svname))

    lender = db.find_one('User', 'fullname', getdutinfo['Owner'])
    TransferDevice(duttype, dutid, current_user.svname, lender['svname'], 'retruned')
    refreshdut()
    logs = LongTasksLogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('log/asynctasklog.html', **locals())


@main.route('/runfwscripts', methods=['POST'])
@login_required
def runfwscripts():
    db = mongo()
    dut_id = request.form['dutid']
    kind = request.form['cduoperator']
    duttype = request.form['duttype']
    if kind == 'yes':
        db.update_one(duttype, 'id', dut_id, 'FWScripts', 'Forbidden by '+current_user.svname)
    elif kind == 'no':
        db.update_one(duttype, 'id', dut_id, 'FWScripts', 'yes')
    return redirect(url_for('.labdut'))


@main.route('/keeppoweron', methods=['GET', 'POST'])
@login_required
def keeppoweron():
    db = mongo()
    users = current_user.svname
    if request.method == "POST":
        dut_id = request.form['dutid']
        kind = request.form['cduoperator']
        duttype = request.form['duttype']
        if kind == 'yes':
            db.update_one(duttype, 'id', dut_id, 'Operator', current_user.svname)
            if db.find_one(duttype, 'id', dut_id)['Operator'] == current_user.svname:
                LogAndCounts('CDU', duttype + ':' + dut_id, 'Set keep alive in next week successful !', 1)
            else:
                flash_and_log_error('DUT id %s: Set keep alive in the following week failed !' % dut_id)
                LogAndCounts('CDU', duttype + ':' + dut_id, 'Set keep alive in next week failed !', 0)
        elif kind == 'no':
            db.update_one(duttype, 'id', dut_id, 'Operator', 'NA')
            if db.find_one(duttype, 'id', dut_id)['Operator'] == 'NA':
                LogAndCounts('CDU', duttype + ':' + dut_id, 'Release keep alive in next week successful !', 1)
            else:
                LogAndCounts('CDU', duttype + ':' + dut_id, 'Release keep alive in next week failed !', 0)
        dutinfo = db.find_many(duttype, 'id', dut_id)
        userfilter = db.find_all('User', 'id')
        if duttype == 'DUT':
            # productinfo = db.find_many('filter', 'type', 'sonicwall')
            # print('dut_id: %s, duttype: %s' % (dut_id, duttype))
            fwinfo = db.find_many('DUT', 'id', dut_id)
            # logs = LogSorted()
            transferlist, transfercont = TransferLog()
            fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
            return render_template('labmgmt/labdut.html', **locals())
        elif duttype == 'SonicPoint':
            # productinfo = db.find_many('filter', 'type', 'sonicpoint')
            # print('dut_id: %s, duttype: %s' % (dut_id, duttype))
            spinfo = db.find_many('SonicPoint', 'id', dut_id)
            # logs = LogSorted()
            transferlist, transfercont = TransferLog()
            fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
            return render_template('labmgmt/labdut.html', **locals())
    return redirect(url_for('.labdut'))


@main.route('/powercontrol', methods=['GET', 'POST'])
@login_required
def powercontrol():
    db = mongo()
    users = current_user.svname
    if request.method == "POST":
        deviceid = request.form['deviceid']
        devicekind = request.form['devicekind']
        devicetype = request.form['devicetype']
        dutpool = request.form['dutpool']
        user_filter = db.find_all('User', 'id')
        # product_filter = judgeduttype(devicetype, deviceid)
        powerstatus = dutpowercfg(deviceid, devicekind, devicetype)
        filterdut = db.find_many(devicetype, 'id', deviceid)
        if powerstatus == 'fail':
            LogAndCounts(devicetype, filterdut['Product'], 'Operated result: Power Control failed!', 0)
            return redirect(url_for('myhome/mydevices.html'))
        consoledata = []
        deviceinfo, dutvlanpool, vmvlanpool = RegetDUTInfo(devicetype, deviceid)
        # logs = LogSorted()
        transferlist, transfercont = TransferLog()
        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
        if dutpool == 'enabled':
            return render_template('myhome/devicepool.html', **locals())
        return render_template('myhome/mydevices.html', **locals())
    return redirect(url_for('.index'))


@main.route('/phywpc', methods=['GET', 'POST'])
@login_required
def phywpc():
    db = mongo()
    if request.method == "POST":
        wpcid = request.form['wpcid']
        wpcowner = request.form['wpcowner']
        if wpcowner == 'occupied':
            db.update_one('phywpc', 'wpc_id', wpcid, 'wpc_owner', wpcowner)
            db.update_one('phywpc', 'wpc_id', wpcid, 'wpc_user', current_user.fullname)
            wpcreslut = db.find_one('phywpc', 'wpc_id', wpcid)
            if wpcreslut['wpc_user'] == current_user.fullname:
                send_pwd_email(current_user.email, 'Wireless PC RDP info', 'mail/wpcinfo', wpcreslut,
                               wpcreslut['wpc_user'])
                LogAndCounts('WPC', wpcreslut['wpc_os'], 'Occupied wireless PC No. ' + wpcid + ' successfully !', 1)
            else:
                LogAndCounts('WPC', wpcreslut['wpc_os'], 'Occupied wireless PC No. ' + wpcid + ' failed !', 0)
        elif wpcowner == 'released':
            wpcreslut = db.find_one('phywpc', 'wpc_id', wpcid)
            wpcolduser = db.find_one('User', 'fullname', wpcreslut['wpc_user'])
            db.update_one('phywpc', 'wpc_id', wpcid, 'wpc_owner', wpcowner)
            db.update_one('phywpc', 'wpc_id', wpcid, 'wpc_user', 'NA')
            if wpcolduser['email']:
                send_pwd_email(wpcolduser['email'], 'Wireless PC RDP info', 'mail/releasewpc', wpcreslut,
                               wpcolduser['fullname'])
                LogAndCounts('WPC', wpcreslut['wpc_os'], 'Released wireless PC No. ' + wpcid + ' successfully !', 1)
            else:
                LogAndCounts('WPC', wpcreslut['wpc_os'],
                             'Released wireless PC No. ' + wpcid + ' failed ! Not valid Email address', 0)
    wpcinfo = db.find_all('phywpc', 'wpc_id')
    if wpcinfo:
        wpcinfo = sorted(wpcinfo, key=lambda keys: keys['wpc_id'])
    # logs = LogSorted()
    username = current_user.fullname
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('labmgmt/phywpc.html', **locals())


@main.route('/ixia', methods=['GET', 'POST'])
@login_required
def ixia():
    db = mongo()
    if request.method == "POST":
        if request.form['ixiatype'] == 'ixiaport':
            ixiaid = request.form['ixiaid']
            ixiaowner = request.form['ixiaowner']
            if ixiaowner == 'occupied':
                db.update_one('ixia', 'ixia_id', ixiaid, 'ixia_owner', ixiaowner)
                db.update_one('ixia', 'ixia_id', ixiaid, 'ixia_user', current_user.fullname)
                ixiareslut = db.find_one('ixia', 'ixia_id', ixiaid)
                if ixiareslut['ixia_user'] == current_user.fullname:
                    LogAndCounts('IXIA', ixiareslut['ixia_card'],
                                 'Occupied IXIA port No. ' + ixiaid + ' successfully !', 1)
                else:
                    LogAndCounts('IXIA', ixiareslut['ixia_card'], 'Occupied IXIA port No. ' + ixiaid + ' failed !', 0)
            elif ixiaowner == 'released':
                ixiareslut = db.find_one('ixia', 'ixia_id', ixiaid)
                db.update_one('ixia', 'ixia_id', ixiaid, 'ixia_owner', ixiaowner)
                db.update_one('ixia', 'ixia_id', ixiaid, 'ixia_user', 'NA')
                LogAndCounts('IXIA', ixiareslut['ixia_card'], 'Released IXIA port No. ' + ixiaid + ' successfully !', 1)
        elif request.form['ixiatype'] == 'ixiavm':
            ixiavmid = request.form['ixiaid']
            ixiavmowner = request.form['ixiaowner']
            if ixiavmowner == 'occupied':
                db.update_one('ixia', 'ixia_vmid', ixiavmid, 'ixia_owner', ixiavmowner)
                db.update_one('ixia', 'ixia_vmid', ixiavmid, 'ixia_user', current_user.fullname)
                ixiareslut = db.find_one('ixia', 'ixia_vmid', ixiavmid)
                if ixiareslut['ixia_user'] == current_user.fullname:
                    LogAndCounts('IXIA', ixiareslut['ixia_vmip'],
                                 'Occupied IXIA VM No. ' + ixiavmid + ' successfully !', 1)
                else:
                    LogAndCounts('IXIA', ixiareslut['ixia_vmip'], 'Occupied IXIA VM No. ' + ixiavmid + ' failed !', 0)
            elif ixiavmowner == 'released':
                ixiareslut = db.find_one('ixia', 'ixia_vmid', ixiavmid)
                db.update_one('ixia', 'ixia_vmid', ixiavmid, 'ixia_owner', ixiavmowner)
                db.update_one('ixia', 'ixia_vmid', ixiavmid, 'ixia_user', 'NA')
                LogAndCounts('IXIA', ixiareslut['ixia_vmip'], 'Released IXIA VM No. ' + ixiavmid + ' successfully !', 1)
    ixiainfo = db.find_many('ixia', 'type', 'ixia')
    if ixiainfo:
        ixiainfo = sorted(ixiainfo, key=lambda keys: keys['ixia_id'])
    vminfo = db.find_many('ixia', 'type', 'vm')
    if vminfo:
        vminfo = sorted(vminfo, key=lambda keys: keys['ixia_vmid'])
    vlaninfo = db.find_many('ixia', 'type', 'vlan')
    if vlaninfo:
        vlaninfo = sorted(vlaninfo, key=lambda keys: keys['vlanid'])
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('labmgmt/ixia.html', **locals())


@main.route('/batchfwcfg', methods=['GET', 'POST'])
@login_required
def batchfwcfg():
    if request.method == 'POST':
        fwfunc = request.form['fwfunction']
        dutip = request.form['dutip']
        dutuser = request.form['dutuser']
        dutpwd = request.form['dutpwd']
        # accessstatus = request.form['sshpingenable']
        # client old ssh key
        os.system('ssh-keygen -R %s' % dutip)
        if fwfunc == 'none':
            flash_and_log_error('Please select a valid DUT function !')
            return redirect(url_for('.batchfwcfg'))
        '''
        if accessstatus == 'no':
            wan_check, X1_ip = enable_ping_ssh(dutip, dutuser, dutpwd)
            if wan_check == 'fail':
                current_app.logger.error(
                    '[' + current_user.fullname + ']--Interface X1 has not valid WAN Mode such as DHCP or Static !')
                return redirect(url_for('.batchfwcfg'))
            current_app.logger.warning(
                '[' + current_user.fullname + ']--enable SSH and ping finished, the X1 Ip is %s  !' % X1_ip)
            dutip = X1_ip
        '''
        print(dutip)

        std_link = os.system('ping -c 3 ' + dutip)
        if std_link == 0:
            current_app.logger.warning('[' + current_user.fullname + ']-- start test SSH Settings to FW %s ...' % dutip)
            child, check_utm_login = try_ssh_login(dutip, dutuser, dutpwd)
            if check_utm_login == 'refused':
                flash_and_log_error('ssh: connect to host %s port 22: Connection refused' % dutip)
                return redirect(url_for('.batchfwcfg'))
            elif check_utm_login == None:
                if try_ssh_login(dutip, dutuser, dutpwd) == None:
                    flash_and_log_error('login DUT failed, Please check Network!')

                    return redirect(url_for('.batchfwcfg'))
            elif check_utm_login == 'error':
                flash('SSH could not login : EOF or Timeout ERROR')
                return redirect(url_for('.batchfwcfg'))
            elif check_utm_login == 'denied':
                flash_and_log_error('SSH could not login : Permission denied ERROR')
                return redirect(url_for('.batchfwcfg'))
            else:
                child.sendline('exit')
                current_app.logger.warning(
                    '[' + current_user.fullname + ']--SSH login UTM successfully !')

        else:
            flash_and_log_error('Ping DUT failed. Please check Its config or LAB Network.')
            return redirect(url_for('.batchfwcfg'))
        current_app.logger.warning('[' + current_user.fullname + ']--Login check ok, start run object...')
        # dutssh = request.form['dutssh']
        if fwfunc == 'addaddressobjects':
            aoname = request.form['aoname']
            aozone = request.form['aozone']
            aoip = request.form['aoip']
            times = request.form['times']
            # print(fwfunc, dutip, dutuser, dutpwd, dutssh, aoname, aozone, aoip, times)
            cont = add_address_objects(dutip, dutuser, dutpwd, aoname, aozone, aoip, times)
            flash('Total add address objects times is : %s' % cont)
        elif fwfunc == 'addaddressgroups':
            agname = request.form['agname']
            agmemberof = request.form['agmemberof']
            times = request.form['times']
            cont = add_address_groups(dutip, dutuser, dutpwd, agname, agmemberof, times)
            flash('Total add Address Groups times is : %s' % cont)
        elif fwfunc == 'addlocalusers':
            localname = request.form['localname']
            localpwd = request.form['localpwd']
            memberof = request.form['memberof']
            times = request.form['times']
            # print(fwfunc, dutip, dutuser, dutpwd, localname, localpwd, memberof, times)
            cont = add_local_users(dutip, dutuser, dutpwd, localname, localpwd, memberof, times)
            flash('Total add Local Users times is : %s' % cont)
        elif fwfunc == 'addlocalgroups':
            localname = request.form['gpname']
            memberof = request.form['memberof']
            times = request.form['times']
            cont = add_local_groups(dutip, dutuser, dutpwd, localname, memberof, times)
            flash('Total add Local Groups times is : %s' % cont)
        elif fwfunc == 'addVPN':
            policytype = request.form['policytype']
            vpnname = request.form['vpnname']
            primaryip = request.form['primaryip']
            sharedsecret = request.form['sharedsecret']
            localnetwork = request.form['localnetwork']
            remotenetwork = request.form['remotenetwork']
            keepalive = request.form['keepalive']
            times = request.form['times']
            cont = add_vpn_policies(dutip, dutuser, dutpwd, policytype, vpnname, primaryip, sharedsecret, localnetwork,
                                    remotenetwork, keepalive, times)
            flash('Total add VPN times is : %s' % cont)
        elif fwfunc == 'addroute':
            routename = request.form['routename']
            interface = request.form['interface']
            metric = request.form['metric']
            source = request.form['source']
            destination = request.form['destination']
            service = request.form['service']
            times = request.form['times']
            cont = add_route_policies(dutip, dutuser, dutpwd, routename, interface, metric, source, destination,
                                      service, times)
            flash('Total add route times is : %s' % cont)
        elif fwfunc == 'addnat':
            natname = request.form['natname']
            inbound = request.form['inbound']
            outbound = request.form['outbound']
            source = request.form['source']
            translatedsource = request.form['translatedsource']
            destination = request.form['destination']
            translatedservice = request.form['translatedservice']
            translateddestination = request.form['translateddestination']
            service = request.form['service']
            natenable = request.form['natenable']
            times = request.form['times']
            cont = add_nat_policies(dutip, dutuser, dutpwd, natname, inbound, outbound, source, translatedsource,
                                    destination, translateddestination, service, translatedservice, natenable, times)
            flash('Total add NAT times is : %s' % cont)
        # elif fwfunc == 'ndpp':
        #     ndppconfig(dutip, dutuser, dutpwd)
        #     flash_and_log_info(
        #         'finished running Script, Please Turn off SSH and ping manually and enable NDPP on UTM. ')
        #     flash_and_log_info('The password for the current super administrator is : %s' % utm_new_pwd)
        elif fwfunc == 'sslserver':
            add_server_ssl(dutip, dutuser, dutpwd)
            flash_and_log_info('Finished added max ssl server polices ! ')
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('autotools/batchfwcfg.html', **locals())


@main.route('/connectiontool', methods=['GET', 'POST'])
@login_required
def connectiontool():
    db = mongo()
    vlanranges = MyVMVLANRange()
    if request.method == "POST":
        contype = request.form['contype']
        if contype == 'tackup':
            vmid = request.form['vmid']
            vmowner = request.form['vmowner']
            if vmowner == 'occupied':
                db.update_one('connectiontool', 'id', vmid, 'tackup', vmowner)
                db.update_one('connectiontool', 'id', vmid, 'user', current_user.fullname)
                vmresult = db.find_one('connectiontool', 'id', vmid)
                if vmresult['user'] == current_user.fullname:
                    # send_pwd_email(current_user.email, 'Wireless PC RDP info', 'mail/wpcinfo', vmresult, vmresult['user'])
                    LogAndCounts('Testbed', 'Connection Tool', 'Occupied the VM include Connection tool successfully !',
                                 1)
                else:
                    LogAndCounts('Testbed', 'Connection Tool',
                                 'Occupied Connection the VM include Connection tool failed !', 0)
            elif vmowner == 'released':
                vmresult = db.find_one('connectiontool', 'id', vmid)
                db.update_one('connectiontool', 'id', vmid, 'tackup', vmowner)
                db.update_one('connectiontool', 'id', vmid, 'user', 'NA')
                LogAndCounts('Testbed', 'Connection Tool', 'Released the VM include Connection tool successfully !', 1)
        elif contype == 'changevlan':
            vmid = request.form['vmid']
            vlan = request.form['vmvlan']
            vminfo = db.find_one('connectiontool', 'id', vmid)
            esxiip = vminfo['ESXi']
            vmname = vminfo['vmname']
            adapter = vminfo['vmnic']
            if vlan == 'UnusedNetwork':
                portgroup = 'UnusedNetwork'
            elif vlan == 'trunk_4095':
                portgroup = 'trunk_4095'
            else:
                portgroup = current_user.svname + '_vlan' + vlan
            esx = db.find_one('ESX', 'IPAddress', esxiip)
            changeresult = ChangeVMVlan(esxiip, esx['AdminUser'], esx['AdminPass'], vmname, adapter, portgroup, 'On')
            if changeresult == 'success':
                db.update_one('connectiontool', 'id', vmid, 'vlan', vlan)
                # RestartAdapter('10.8.2.126', 'qa', 'password')
                LogAndCounts('Testbed', 'Connection Tool', 'Change the adapter vlan to %s Successfully !' % vlan, 1)
            else:
                LogAndCounts('Testbed', 'Connection Tool', 'Change the adapter vlan to %s Failed !' % vlan, 0)
    vminfo = db.find_all('connectiontool', 'id')
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('autotools/connectiontool.html', **locals())


@main.route('/vmcontrol', methods=['GET', 'POST'])
@login_required
def vmcontrol():
    consoledata = []
    usercheck = db.find_one('User', 'svname', current_user.svname)
    if request.method == "POST":
        select = request.form['select']
        esxiip = request.form['esxiip']
        pgname = request.form['pgname']
        svname = request.form['svname']
        vlanstart = request.form['vlanstart']
        vlanend = request.form['vlanend']
        print('select: %s, esxiip: %s, svname: %s, vlanstart: %s, vlanend: %s' % (
        select, esxiip, svname, vlanstart, vlanend))
        if select == 'none' or esxiip == '' or svname == '' or vlanstart == '' or vlanend == '':
            flash_and_log_error('Input check error: Please input a good value for key option(*)')
        else:
            consoledata = ESXIPortGroups(select, esxiip, pgname, svname, vlanstart, vlanend)
            # print(pgs)
            flash_and_log_info('Operated Result: %s in VMs Finished !' % select)
            # logs = LogSorted()
            transferlist, transfercont = TransferLog()
            fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
            return render_template('vlabadmin/vmcontrol.html', **locals())
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('vlabadmin/vmcontrol.html', **locals())


@main.route('/usersetting', methods=['GET', 'POST'])
@login_required
def usersetting():
    db = mongo()
    consoledata = []
    userdata = {"AdminVLAN": '54-55,104-106', "ESXServer": ['10.8.2.25'], "Group": 'QA2', "VLAN": '731-733,734-737',
                "allowedGroups": 'user', "svname": 'lezhang', "fullname": 'lezhang (Neil Zhang)',
                "email": 'lezhang@sonicwall.com'}
    usercheck = db.find_one('User', 'svname', current_user.svname)
    if usercheck['allowedGroups'] == 'admin':
        if request.method == "POST":
            select = request.form['select']
            svname = request.form['svname']
            fullname = request.form['fullname']
            email = request.form['email']
            team = request.form['team']
            allowgroup = request.form['allowgroup']
            adminvlan = request.form['adminvlan']
            privatevlan = request.form['privatevlan']
            esxiserver = request.form['esxiserver']
            print(
                'select: %s, svname: %s, fullname: %s, email: %s, team: %s allowgroup: % adminvlan: %s privatevlan: %s esxiserver: %s' % (
                select, svname, fullname, email, team, allowgroup, adminvlan, privatevlan, esxiserver))
            if select == 'adduser':
                if select == 'none' or svname == '' or fullname == '' or email == '' or team == '' or allowgroup == '' or adminvlan == '' or privatevlan == '' or esxiserver == '':
                    flash_and_log_error('Input check error: Please input a vaild value for key option(*)')
                else:
                    checkuser = db.find_one('User', 'svname', svname)
                    if checkuser:
                        if checkuser['svname'] == svname:
                            flash_and_log_error('svname: %s has been existed in DB, do not need add again !' % svname)
                            consoledata = [svname + ' has been existed in DB']
                            # logs = LogSorted()
                            transferlist, transfercont = TransferLog()
                            fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                            return render_template('vlabadmin/vmcontrol.html', **locals())
                    adminvlan = SplitRanges(adminvlan)
                    privatevlan = SplitRanges(privatevlan)
                    userid = len(db.find_all('User', 'svname'))
                    atemp = []
                    for esxipstr in esxiserver.strip('[\']').split(','):
                        atemp.append(esxipstr.strip().strip('\''))
                    userdoc = {"AdminVLAN": adminvlan, "DefaultAdminVLAN": "999", "DefaultLogLevel": "info",
                               "ESXServer": atemp, "Group": team, "VLAN": privatevlan, "allowedGroups": allowgroup,
                               "id": svname, "username": fullname, "userid": str(userid + 1), "svname": svname,
                               "fullname": fullname, "email": email}
                    db.insert_one('User', userdoc)
                    usercheck = db.find_one('User', 'svname', svname)
                    consoledata.append(usercheck)
                    flash_and_log_info('Add Finished: a New User %s has been added in DB !' % svname)
                    usercheck['AdminVLAN'] = CombineRanges(usercheck['AdminVLAN'], [])
                    usercheck['VLAN'] = CombineRanges([], usercheck['VLAN'])
                    flash_and_log_info('Operated Result: add the user to DB Finished !')
                    userdata = usercheck
                    # logs = LogSorted()
                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('vlabadmin/usersetting.html', **locals())
            elif select == 'searchuser':
                usercheck = db.find_one('User', 'svname', svname)
                if usercheck:
                    consoledata.append(usercheck)
                    flash_and_log_info('Search Finished: User %s is exist in DB !' % svname)
                    usercheck['AdminVLAN'] = CombineRanges(usercheck['AdminVLAN'], [])
                    usercheck['VLAN'] = CombineRanges([], usercheck['VLAN'])
                    userdata = usercheck
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('vabadmin/usersetting.html', **locals())
                else:
                    flash_and_log_error('Search finished: Can not search the svname: %s in DB !' % svname)
            elif select == 'edituser':
                if select == 'none' or svname == '' or fullname == '' or email == '' or team == '' or allowgroup == '' or adminvlan == '' or privatevlan == '' or esxiserver == '':
                    flash_and_log_error('Input check error: Please input a vaild value for key option(*)')
                else:
                    checkuser = db.find_one('User', 'svname', svname)
                    if checkuser is None:
                        flash_and_log_error('svname: %s was not exist in DB, Please add it first !' % svname)
                        consoledata = 'svname: %s was not exist in DB, Please add it first !' % svname
                        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                        return render_template('vlabadmin/usersetting.html', **locals())
                    adminvlan = SplitRanges(adminvlan)
                    privatevlan = SplitRanges(privatevlan)
                    atemp = []
                    for esxipstr in esxiserver.strip('[\']').split(','):
                        atemp.append(esxipstr.strip().strip('\''))
                    userdoc = {"AdminVLAN": adminvlan, "DefaultAdminVLAN": "999", "DefaultLogLevel": "info",
                               "ESXServer": atemp, "Group": team, "VLAN": privatevlan, "allowedGroups": allowgroup,
                               "id": svname, "username": fullname, "userid": checkuser['userid'], "svname": svname,
                               "fullname": fullname, "email": email}
                    db.delete_one('User', 'svname', svname)
                    db.insert_one('User', userdoc)
                    usercheck = db.find_one('User', 'svname', svname)
                    consoledata.append(usercheck)
                    flash_and_log_info('Modify Finished: The User %s has been edited in DB successfully!' % svname)
                    usercheck['AdminVLAN'] = CombineRanges(usercheck['AdminVLAN'], [])
                    usercheck['VLAN'] = CombineRanges([], usercheck['VLAN'])
                    userdata = usercheck

                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('vlabadmin/usersetting.html', **locals())
            elif select == 'deluser':
                usercheck = db.find_one('User', 'svname', svname)
                if usercheck:
                    db.delete_one('User', 'svname', svname)
                    consoledata.append('User %s has been deleted in DB successfully !' % svname)
                    flash_and_log_info('Delete Finished: User %s has been deleted in DB !' % svname)
                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('vlabadmin/usersetting.html', **locals())
                else:
                    consoledata.append('Can not search the svname: %s in DB !' % svname)
                    flash_and_log_error(
                        'Search finished: Can not search the svname: %s in DB. do not need delete !' % svname)
    else:
        flash_and_log_info('User Setting: Do not have permission !')
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('vlabadmin/usersetting.html', **locals())


@main.route('/devicesetting', methods=['GET', 'POST'])
@login_required
def devicesetting():
    db = mongo()
    consoledata = []
    devicedata = {"RegistrationCode": "2EWSC4VS", "Product": "TZ570P", "User": "lezhang", "Group": "Default",
                  "Description": "RowE-Rack4-24U", "Owner": "lezhang (Neil Zhang)", "SN": "2CB8ED694666",
                  "keepAlive": "1", "id": "888", "Operator": "NA",
                  "InterfaceInfo": "['X0:Core_Switch-12:gi1/6:dell', 'X1:Core_Switch-12:gi1/7:dell', 'X2:Core_Switch-12:gi1/8:dell', 'X3:Core_Switch-12:gi1/9:dell', 'X4:Core_Switch-12:gi1/10:dell']",
                  "ConsoleInfo": "['CM-2:2019:2019']", "PowerInfo": "['shg-rwE-rk4a:AC5']", "DeviceType": "DUT"}
    usercheck = db.find_one('User', 'svname', current_user.svname)
    if usercheck['allowedGroups'] == 'admin':
        if request.method == "POST":
            select = request.form['select']
            sn = request.form['sn']
            devicetype = request.form['devicetype']
            if select == 'none':
                flash_and_log_error('Please selete a function in Device Operate first !')
            elif select == 'adddevice':
                dutid = request.form['dutid']
                product = request.form['product']
                regcode = request.form['regcode']
                description = request.form['description']
                group = request.form['group']
                owner = request.form['owner']
                user = request.form['user']
                operator = request.form['operator']
                keepalive = request.form['keepalive']
                interfaceinfo = request.form['interfaceinfo']
                consoleinfo = request.form['consoleinfo']
                powerinfo = request.form['powerinfo']
                print(
                    'select: %s, dutid: %s, product: %s, sn: %s, regcode: %s, devicetype: %s, description: %s, group: %s, user: %s, operator: %s, keepalive: %s, interfaceinfo: %s, consoleinfo: %s, powerinfo: %s' % (
                        select, dutid, product, sn, regcode, devicetype, description, group, user, operator, keepalive,
                        interfaceinfo, consoleinfo, powerinfo))
                if product == '' or sn == '' or regcode == '' or devicetype == '' or description == '' or group == '' or user == '' or operator == '' or keepalive == '' or interfaceinfo == '' or consoleinfo == '' or powerinfo == '':
                    flash_and_log_error('Input check error: Please input a vaild value for key option(*)')
                else:
                    checkdevice = db.find_one(devicetype, 'SN', sn)
                    if checkdevice:
                        flash_and_log_error('svname: %s has been existed in DB, do not need add again !' % sn)
                        transferlist, transfercont = TransferLog()
                        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                        checkdevice = devicedata
                        consoledata = [sn + ' has been existed in DB']
                        return render_template('vlabadmin/devicesetting.html', **locals())
                    interports = []
                    infoid = 0
                    for ainfo in interfaceinfo.split(','):
                        asplit = ainfo.strip().strip('[\']').split(':')
                        if len(asplit) == 4:
                            ainterport = {"portpower": "Down", "lag": "off", "SwitchPort": asplit[2], "id": infoid,
                                          "name": asplit[0], "SwitchID": asplit[1], "untagvlan": "1",
                                          "portmode": "access",
                                          "tagvlan": "--", "porttype": asplit[3], "vmname": [], "stp": "on"}
                            interports.append(ainterport)
                            infoid = infoid + 1
                        else:
                            flash_and_log_error(
                                'the InterfaceInfo %s is invalid, please check it again !' % interfaceinfo)
                            transferlist, transfercont = TransferLog()
                            fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                            return render_template('vlabadmin/devicesetting.html', **locals())
                    InterfaceInfo = {"Interface": interports}
                    # print(InterfaceInfo)
                    consoleinfo = consoleinfo.strip('[\']').split(',')
                    if consoleinfo[0]:
                        aconsolesplit = consoleinfo[0].split(':')
                        ConsoleInfo = {"ConsoleManager": aconsolesplit[0], "SSHPort": aconsolesplit[1],
                                       "TelnetPort": aconsolesplit[2]}
                    else:
                        flash_and_log_error(
                            'the ConsoleInfo: %s input value invalid, please check it again !' % consoleinfo)
                        transferlist, transfercont = TransferLog()
                        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                        return render_template('vlabadmin/devicesetting.html', **locals())
                    powerinfo = powerinfo.strip('[\']').split(',')
                    # print(powerinfo)
                    if powerinfo[0]:
                        apowersplit = powerinfo[0].split(':')
                        PowerInfo = {"PowerController": apowersplit[0], "PowerChannel": apowersplit[1]}
                    else:
                        flash_and_log_error(
                            'the ConsoleInfo: %s input value invalid, please check it again !' % powerinfo)
                        transferlist, transfercont = TransferLog()
                        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                        return render_template('vlabadmin/devicesetting.html', **locals())
                    userdoc = {"RegistrationCode": regcode, "Product": product, "User": user, "Group": group,
                               "Description": description, "Owner": owner, "SN": sn, "keepAlive": keepalive,
                               "id": dutid, "Operator": operator, "InterfaceInfo": InterfaceInfo,
                               "ConsoleInfo": ConsoleInfo, "PowerInfo": PowerInfo, "DeviceType": devicetype}
                    db.insert_one(devicetype, userdoc)
                    devicecheck = db.find_one(devicetype, 'SN', sn)
                    consoledata.append(devicecheck)
                    flash_and_log_info('Add Finished: a New Device SN: %s has been added in DB !' % sn)
                    devicedata = devicecheck
                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('vlabadmin/devicesetting.html', **locals())
            elif select == 'searchdevice':
                devicecheck = db.find_one(devicetype, 'SN', sn)
                if devicecheck:
                    consoledata.append(devicecheck)
                    flash_and_log_info('Search Finished: Device %s is exist in DB !' % sn)
                    # print(devicecheck)
                    portinfos = []
                    devinterinfo = devicecheck['InterfaceInfo']['Interface']
                    for portinfo in devinterinfo:
                        portinfos.append(
                            portinfo['name'] + ':' + portinfo['SwitchID'] + ':' + portinfo['SwitchPort'] + ':' +
                            portinfo['porttype'])
                    devicecheck['InterfaceInfo'] = portinfos
                    devicecheck['ConsoleInfo'] = [
                        devicecheck['ConsoleInfo']['ConsoleManager'] + ':' + devicecheck['ConsoleInfo'][
                            'SSHPort'] + ':' + devicecheck['ConsoleInfo']['TelnetPort']]
                    devicecheck['PowerInfo'] = [
                        devicecheck['PowerInfo']['PowerController'] + ':' + devicecheck['PowerInfo']['PowerChannel']]
                    devicedata = devicecheck
                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('vlabadmin/devicesetting.html', **locals())
                else:
                    flash_and_log_error('Search finished: Can not search the SN: %s in DB !' % sn)
                    devicedata = ('Search finished: Can not search the SN: %s in DB !' % sn)

            elif select == 'editdevice':
                changename = request.form['column']
                changevalue = request.form['columnvalue']
                if changename == 'none' or changevalue == '':
                    flash_and_log_error('Input check error: Please input a vaild value for key option(*)')
                else:
                    checkdevice = db.find_one(devicetype, 'SN', sn)
                    if checkdevice is None:
                        flash_and_log_error('SN: %s was not exist in DB, Please add it first !' % sn)
                        consoledata = 'SN: %s was not exist in DB, Please add it first !' % sn
                        fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                        return render_template('vlabadmin/devicesetting.html', **locals())
                    if changename == 'InterfaceInfo':
                        for ainfo in changevalue.split(','):
                            asplit = ainfo.strip().strip('[\']').split(':')
                            if len(asplit) == 4:
                                db.update_one_inerface(devicetype, checkdevice['id'], asplit[0], 'SwitchID', asplit[1])
                                db.update_one_inerface(devicetype, checkdevice['id'], asplit[0], 'SwitchPort',
                                                       asplit[2])
                                db.update_one_inerface(devicetype, checkdevice['id'], asplit[0], 'porttype', asplit[3])
                                # db.update_one_inerface('DUT', '868', 'X0', 'SwitchID', 'test1')
                            else:
                                flash_and_log_error(
                                    'the InterfaceInfo %s is invalid, please check it again !' % changevalue)
                                transferlist, transfercont = TransferLog()
                                fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                                return render_template('vlabadmin/devicesetting.html', **locals())
                    elif changename == 'ConsoleInfo':
                        consoleinfo = changevalue.strip('[\']').split(',')
                        if consoleinfo:
                            aconsolesplit = consoleinfo[0].split(':')
                            if len(aconsolesplit) == 3:
                                db.update_one(devicetype, 'id', checkdevice['id'], 'ConsoleInfo',
                                              {"ConsoleManager": aconsolesplit[0], "SSHPort": aconsolesplit[1],
                                               "TelnetPort": aconsolesplit[2]})
                                flash_and_log_info(
                                    'Modify Finished: Change the SN: %s, ConsoleInfo: %s successfully to DB !' % (
                                    sn, consoleinfo))
                            else:
                                flash_and_log_error(
                                    'ConsoleInfo: %s input fromat is invalid, please check it again !' % consoleinfo)
                        else:
                            flash_and_log_error(
                                'ConsoleInfo: %s input value is invalid, please check it again !' % consoleinfo)
                    elif changename == 'PowerInfo':
                        powerinfo = changevalue.strip('[\']').split(',')
                        if powerinfo:
                            apowersplit = powerinfo[0].split(':')
                            if len(apowersplit) == 2:
                                db.update_one('DUT', 'SN', sn, 'PowerInfo',
                                              {"PowerController": apowersplit[0], "PowerChannel": apowersplit[1]})
                                flash_and_log_info(
                                    'Modify Finished: Changed the SN: %s, PowerInfo: %s successfully to DB !' % (
                                    sn, powerinfo))
                            else:
                                flash_and_log_error(
                                    'PowerInfo: %s input fromat is invalid, please check it again !' % powerinfo)
                        else:
                            flash_and_log_error(
                                'PowerInfo: %s input value is invalid, please check it again !' % powerinfo)
                    else:
                        aresult = db.update_one(devicetype, 'SN', sn, changename, changevalue)
                        print(aresult)
                        flash_and_log_info(
                            'Modify Finished: Changed the SN: %s, changename: %s changevalue: %s successfully to DB !' % (
                            sn, changename, changevalue))
                    devicecheck = db.find_one(devicetype, 'SN', sn)
                    consoledata.append(devicecheck)
                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    devicedata = devicecheck
                    myvmslist = GetVMsName()
                    return render_template('vlabadmin/devicesetting.html', **locals())
            elif select == 'deldevice':
                usercheck = db.find_one(devicetype, 'SN', sn)
                if usercheck:
                    db.delete_one(devicetype, 'SN', sn)
                    consoledata.append('Device %s has been deleted in DB successfully !' % sn)
                    flash_and_log_info('Delete Finished: Device %s has been deleted in DB !' % sn)
                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('vlabadmin/devicesetting.html', **locals())
                else:
                    consoledata.append('Can not search the device: %s in DB !' % sn)
                    flash_and_log_error(
                        'Search finished: Can not search the device: %s in DB. do not need delete !' % sn)
    else:
        flash_and_log_info('Device Setting: Do not have permission !')
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('vlabadmin/devicesetting.html', **locals())


@main.route('/changepwd', methods=['GET', 'POST'])
@login_required
def changepwd():
    db = mongo()
    DomainUserName = f'vlab\\{current_user.svname}'
    UserPass = request.form['userpass']
    NewUserPass = request.form['newpass']
    ConfirmNewUserPass = request.form['confirmpass']
    user_info = {
        'DomainUserName': current_user.svname,
        'UserPass': UserPass,
        'NewUserPass':  NewUserPass
    }
    # print(user_info)
    ldap = LDAPSettings(DomainUserName, UserPass, NewUserPass, ConfirmNewUserPass)
    res = ldap.modifypwd()

    if res[0]:
        send_vlab_pwd_email(current_user.email, 'vlab user password changed information', 'mail/changepwdinfo', user_info, current_user.fullname)
        LogAndCounts('VLAB', 'Change Password', f'user {current_user.svname} changed login password successful! ', 0)
        dutinfo = db.find_one('DUT', 'User', current_user.svname)
        db.update_one('DUT', 'id', dutinfo['id'], 'Password', NewUserPass)
    else:
        flash_and_log_info(res[1])
    print(f'{current_user.svname}: {res}')
    return redirect(url_for('.myhome'))


@main.route('/ticket', methods=['GET', 'POST'])
@login_required
def ticket():
    db = mongo()
    userlist = db.find_many_sort('User', 'allowedGroups', 'admin', 'username', 'up')
    ticketcfg = db.find_one('GlobalConfig', 'id', 'Ticket')
    if request.method == "POST":
        operate = request.form['operate']
        if operate == 'Edit':
            action = request.form['action']
            ticketid = request.form['id']
            # print('operate: %s, ticketid: %s' % (operate, ticketid))
            title = request.form['title']
            tickettype = request.form['type']
            priority = request.form['priority']
            assign = request.form['assign']
            content = request.form['content']
            org_dict = db.find_one('ticket', 'id', int(ticketid))
            if action == 'Assign' or action == 'Progress' or action == 'Close':
                org_dict = db.find_one('ticket', 'id', int(ticketid))
                changed_dict = {'title': title, 'type': tickettype, 'priority': priority, 'content': content,
                                'id': int(ticketid), 'time': org_dict['time'],
                                'author': org_dict['author'], 'status': action, 'assign': ''}
                if assign == 'General':
                    # changed_dict['assign'] = Config.defaultadmin
                    changed_dict['assign'] = ticketcfg['defaultadmin']
                elif assign == 'none':
                    LogAndCounts('ticket', 'action', 'Action operated failed. Please Select a valid admin account !', 1)
                    return redirect(url_for('.ticket'))
                else:
                    changed_dict['assign'] = assign
                content = content + '\r\n' + action + ' by ' + current_user.svname + '---' + time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime())
                changed_dict['content'] = content
                db.delete_one('ticket', 'id', int(ticketid))
                db.insert_one('ticket', changed_dict)
                mailcontent = db.find_many('ticket', 'id', int(ticketid))
                userinfo = db.find_one('User', 'fullname', mailcontent[0]['author'])
                ticket_email(userinfo['email'], 'Ticket transaction notification', 'mail/ticketaction', mailcontent,
                             current_user.fullname)
                LogAndCounts('ticket', 'action', 'Administrator changed the status to %s finished !' % action, 1)

            elif action == 'Modify':
                if assign == 'none':
                    status = 'New'
                    assign = 'NA'
                elif assign == 'general':
                    status = 'Assign'
                    assign = ticketcfg['defaultadmin']
                    edit_dict = {'title': title, 'type': tickettype, 'priority': priority, 'content': content,
                                 'id': int(ticketid), 'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                 'author': org_dict['author'], 'status': status, 'assign': assign}
                    db.delete_one('ticket', 'id', int(ticketid))
                    db.insert_one('ticket', edit_dict)
                else:
                    status = 'Assign'
                edit_dict = {'title': title, 'type': tickettype, 'priority': priority, 'content': content,
                             'id': int(ticketid), 'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                             'author': org_dict['author'], 'status': status, 'assign': assign}
                db.delete_one('ticket', 'id', int(ticketid))
                db.insert_one('ticket', edit_dict)
        elif operate == 'Add':
            title = request.form['title']
            addtype = request.form['type']
            priority = request.form['priority']
            content = request.form['content']
            assign = request.form['assign']
            allids = db.find_all_sort('ticket', 'id', 'up')
            # print(allids[-1])
            contents = {'title': title, 'type': addtype, 'priority': priority, 'content': content,
                        'id': allids[-1]['id'] + 1, 'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                        'author': current_user.fullname, 'status': '', 'assign': ''}
            if assign == 'none':
                contents['status'] = 'New'
                contents['assign'] = 'NA'
                db.insert_one('ticket', contents)
                mailcontent = db.find_many('ticket', 'id', allids[-1]['id'] + 1)
                for sendto in ticketcfg['addsendto']:
                    ticket_email(sendto, 'Ticket transaction notification', 'mail/ticketadd', mailcontent,
                                 current_user.fullname)
            elif assign == 'General':
                contents['status'] = 'Assign'
                # contents['assign'] = Config.defaultadmin
                contents['assign'] = ticketcfg['defaultadmin']
                db.insert_one('ticket', contents)
                mailcontent = db.find_many('ticket', 'id', allids[-1]['id'] + 1)
                for sendto in ticketcfg['addsendto']:
                    ticket_email(sendto, 'Ticket transaction notification', 'mail/ticketadd', mailcontent,
                                 current_user.fullname)
            else:
                contents['status'] = 'Assign'
                contents['assign'] = assign
                db.insert_one('ticket', contents)
                sendto = db.find_one('User', 'username', assign)
                mailcontent = db.find_many('ticket', 'id', allids[-1]['id'] + 1)
                ticket_email(sendto['email'], 'Ticket transaction notification', 'mail/ticketadd', mailcontent,
                             current_user.fullname)
            LogAndCounts('ticket', 'add', 'Add a Ticket to admin finished !', 1)
        elif operate == 'Delete':
            ticketid = request.form['id']
            db.delete_one('ticket', 'id', int(ticketid))
        return redirect(url_for('.ticket'))
    ticketinfos = db.find_all_sort('ticket', 'status', 'down')
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('vlabadmin/ticket.html', **locals())


@main.route('/ticketfilter', methods=['GET'])
@login_required
def ticketfilter():
    db = mongo()
    filtername = request.args.get('filtername')
    select = request.args.get('select')
    if select == 'All':
        ticketinfos = db.find_all_sort('ticket', filtername, 'down')
    else:
        ticketinfos = db.find_many_sort('ticket', filtername, select, 'time', 'down')
    # logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    userlist = db.find_many_sort('User', 'allowedGroups', 'admin', 'username', 'up')
    return render_template('vlabadmin/ticket.html', **locals())


@main.route('/resetsw', methods=['GET', 'POST'])
@login_required
def resetsw():
    consoledata = []
    db = mongo()
    if request.method == "POST":
        select = request.form['select']
        dutid = request.form['id']
        dutport = request.form['port']
        print('select: %s, dutid: %s, dutport: %s' % (select, dutid, dutport))
        if select == 'none' or dutid == '' or dutport == '':
            flash_and_log_error('Input check error: Please input a good value for key option(*)')
        else:
            dutinfo = db.find_one(select, 'id', dutid)
            portinfo = dutinfo['InterfaceInfo']['Interface']
            for port in portinfo:
                if port['name'] == dutport:
                    swidinfo = db.find_one('Switch', 'id', port['SwitchID'])
                    initrst, logs = SWInitial(port['porttype'], swidinfo['ConsoleServer'], port['SwitchPort'])
                    if initrst == 'fail':
                        flash_and_log_error('Connect Core Switch failed !')
                    elif initrst == 'lag on':
                        flash_and_log_info('DUT id %s, port %s: LAG is on in Switch, can not initial this port !' % (
                        dutid, port['name']))
                    else:
                        flash_and_log_info('Initial Switch Port Successful !')
                    # print(logs)
                    consoledata = logs
                    transferlist, transfercont = TransferLog()
                    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
                    return render_template('swconfig/resetsw.html', **locals())
                    # return render_template('swconfig/resetsw.html', mydeviceslist=mydevicesget(), myvmslist=GetVMsName(),consoledata=logs)
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('swconfig/resetsw.html', **locals())
    # return render_template('swconfig/resetsw.html', mydeviceslist=mydevicesget(), myvmslist=GetVMsName(), consoledata=consoledata)


@main.route('/asynctasklog', methods=['GET'])
@login_required
def asynctasklog():
    global taskid, getvmstatus, esxiip
    db = mongo()
    logs = LongTasksLogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('log/asynctasklog.html', **locals())


@main.route('/deviceconfiglog', methods=['GET'])
@login_required
def deviceconfiglog():
    db = mongo()
    logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('log/deviceconfiglog.html', **locals())


@main.route('/test', methods=['GET', 'POST'])
@login_required
def test():
    db = mongo()
    dutsinfo = db.find_one('DUT', 'id', '188')
    # vmsinfo = db.find_many('EsxiVMs', 'user', current_user.svname)

    dutinterfaces = dutsinfo['InterfaceInfo']['Interface']
    # vmname = request.args.get('vmname')
    vmname = 'centos7(237-240)'
    # print(vmname)
    frompage = 'myvms'
    vmsinfo = db.find_by_multi_field('EsxiVMs', 'owner', current_user.svname, 'vmname', vmname)
    vlanranges = MyVMVLANRange()

    dutlists = db.find_many('DUT', 'User', current_user.svname)
    splists = db.find_many('SonicPoint', 'User', current_user.svname)
    mylists = dutlists + splists
    convids = []
    for aid in mylists:
        convid = int(aid['id'])
        aid['id'] = convid
        convids.append(aid)
    dutinfo = sorted(convids, key=lambda keys: keys['id'])
    deviceinfo = dutinfo

    logs = LogSorted()
    transferlist, transfercont = TransferLog()
    fwfilters, spfilters, lentlist, vmlists, vlanlists, publicpool = GetSidebarList()
    return render_template('test.html', **locals())


'''
@main.route('/longtask', methods=['POST'])
def longtask():
    # 开启异步任务
    task = long_task.apply_async()
    # task = async_getvminfo.apply_async(('10.8.2.25', 'root', 'sonicpassword', current_user.svname))
    print('task id-----'+task.id)
    return jsonify({}), 202, {'Location': url_for('main.taskprogress', task_id=task.id)}

@main.route('/progress/<task_id>')
def taskprogress(task_id):
    # 获取异步任务结果
    task = long_task.AsyncResult(task_id)
    # task = async_getvminfo.AsyncResult(task_id)
    print('task status-----'+task.state)
    # 等待处理
    if task.state == 'PENDING':
        response = {'state': task.state, 'current': 0, 'total': 1}
    elif task.state != 'FAILURE':
        response = {'state': task.state, 'current': task.info.get('current', 0), 'total': task.info.get('total', 1)}
        # 处理完成
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # 后台任务出错
        response = {'state': task.state, 'current': 1, 'total': 1}
    return jsonify(response)

@main.route('/tasktest', methods=['GET', 'POST'])
def tasktest():
    if request.method == 'GET':
        return render_template('tasktest.html', email=session.get('email', ''))
    email = request.form['email']
    # session['email'] = email

    # msg = Message('Hello from Flask', sender=app.config['MAIL_USERNAME'], recipients=[email])
    # msg.body = 'This is a test email sent from a background Celery task.'
    # print(msg)
    # send the email
    email_data = {
        'subject': 'Hello from Flask',
        'to': email,
        'body': 'This is a test email sent from a background Celery task.'
    }
    print(email_data)
    if request.form['submit'] == 'Send':
        # 立即发送
        # delay 是 apply_async 的快捷快捷方式
        # 相比于 delay，当使用 apply_async 时，我们能够对后台任务的执行方式有更多的控制。例如任务在何时执行
        # delay 和 apply_async 的返回值是一个 AsyncResult 的对象。通过该对象，能够获得任务的状态信息
        send_async_email.delay(email_data)
        flash('Sending email to {0}'.format(email))
    else:
        # 1分钟后发送
        send_async_email.apply_async(args=[email_data], countdown=60)
        flash('An email will be sent to {0} in one minute'.format(email))
    return redirect(url_for('main.tasktest'))
'''
