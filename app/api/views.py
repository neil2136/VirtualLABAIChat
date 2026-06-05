"""
Author: Neil Zhang
Time: 2020/1/4
Descriptions:
  this file contains all of the API functions that can be called externally that are reserved for scripts. Its service obijects are: Jenkins scripts, testbed...
"""
from flask import jsonify, current_app, request, Response, stream_with_context
from ..lib.mongodb import mongo
import requests
from . import api
from ..lib.dutpowercfg import dutpowercfg
from ..email import send_cdu_email, send_all_email, jira_issues_email
from ..lib.flashandlog import log_print
from ..lib.aptest import *
from ..lib.ai_search import AISearchService
from jira import JIRA
import datetime
from ..email import send_crash_email
from ..email import send_device_borrow_request_email
from ..email import dut_change_user_email
from ..lib.cductrl import CDU
from ..lib.refreshg7 import checkdutinfo
from ..main.tasks import async_checkdutinfo
from ..lib.sidebar import RefreshG7
from flask_login import current_user

# Local AI Agent Configuration
LOCAL_AI_BASE_URL = "https://10.103.2.128:10443"
LOCAL_AI_TIMEOUT = 30


def get_current_username():
    """获取当前登录用户名"""
    if current_user.is_authenticated:
        username = current_user.svname
        print(f"[LOCAL_AI] Current user from session: {username}")
        return username
    print("[LOCAL_AI] User not authenticated, using anonymous")
    return "anonymous"


def get_local_ai_headers():
    """构造Local AI Agent请求头"""
    headers = {
        "X-User-Id": get_current_username(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    print(f"[LOCAL_AI] Generated headers: {headers}")
    return headers


# only test api, http//(ip)/api/test
@api.route('/test')
def test():
    print('22222')
    return jsonify({'status': 'test successed'})


# run in Shanghai Jenkins. keep the devices power off. Project Wpc-pwd-set and CDU-Poweroff.
@api.route('/keeppoweron/<duttype>/poweroff')
def cductrlapi(duttype):
    db = mongo()
    alldutinfo = db.find_all(duttype, 'id')
    # alldutinfo = find_many(duttype, 'id', '34')
    for dut_rst in alldutinfo:
        # dut_rst = find_one(duttype, 'id', str(i))
        # print('----------------------%s' % dut_rst)
        dutid = dut_rst['id']
        operator = dut_rst['Operator']
        keepalive_db = dut_rst['keepAlive']
        power_name = dut_rst['PowerInfo']['PowerController']
        power_channel = dut_rst['PowerInfo']['PowerChannel']
        power_map = db.find_many('PowerController', 'id', power_name)
        power_ip = power_map[0]['IPAddress']
        # print('dutid: %s, keepalive_db: %s, operator: %s, power_name: %s, power_channel: %s, power_ip: %s' % (dutid, keepalive_db, operator, power_name, power_channel, power_ip))
        if operator == 'NA':
            # replace_one(duttype, 'id', dutid, 'Operator', 'NA')
            # print('dutid: %s -- Start power off CDU: %s, Channel: %s' % (dutid, power_channel, power_ip))
            current_app.logger.warning(
                'dutid: %s -- Start power off CDU: %s, Channel: %s' % (dutid, power_ip, power_channel))
            time.sleep(5)
            off_result = dutpowercfg(dutid, 'Down', duttype)
            if off_result == None:
                current_app.logger.warning(
                    'dutid: %s, CDU: %s, Channel: %s -- login CDU failed !' % (dutid, power_ip, power_channel))
                # print('get power info failed. login failed, due to TIMEOUT or EOF ' + power_ip + power_channel)
            elif off_result == 'ok':
                if keepalive_db == '1':
                    db.update_one(duttype, 'id', dutid, 'keepAlive', 0)
                    current_app.logger.warning('dutid: %s, CDU: %s, Channel: %s -- CDU power off successful !' % (
                    dutid, power_ip, power_channel))
                elif keepalive_db == 0:
                    # log_info('Switch and DB are same! do not do anything')
                    current_app.logger.warning(
                        'dutid: %s, CDU: %s, Channel: %s -- Switch and DB are same! do not do anything' % (
                        dutid, power_ip, power_channel))
        else:
            db.update_one(duttype, 'id', dutid, 'Operator', 'NA')
            # print('dutid: %s, CDU: %s, Channel: %s -- device keep alive by user' % (dutid, power_channel, power_ip))
            current_app.logger.warning(
                'dutid: %s, CDU: %s, Channel: %s -- device keep alive by user' % (dutid, power_ip, power_channel))

    send_cdu_email('qigu@sonicwall.com', 'devices forced power off result', 'auth/email/cduoff', log_print)
    send_cdu_email('lezhang@sonicwall.com', 'devices forced power off result', 'auth/email/cduoff', log_print)
    return jsonify('code: ok')


# run in Shanghai Jenkins. Change the wireless PC password. Project Wpc-pwd-set and CDU-Poweroff.
@api.route('/changepwd/<pcip>/<pwd>')
def changepwd(pcip, pwd):
    db = mongo()
    if pcip and pwd:
        db.update_one('phywpc', 'wpc_ip', pcip, 'wpc_pwd', pwd)
        return jsonify({'status': 'successed'})
    else:
        return jsonify({'status': 'pcip or pwd is empty !'})


# run in Shanghai Jenkins. reset user value in DB. Project Wpc-pwd-set and CDU-Poweroff.
@api.route('/rstuser')
def rstuser():
    db = mongo()
    wpclists = db.find_all('phywpc', 'wpc_id')
    if len(wpclists):
        print(len(wpclists))
        for wpclist in wpclists:
            print(wpclist['wpc_id'])
            db.update_one('phywpc', 'wpc_id', wpclist['wpc_id'], 'wpc_user', 'NA')
            db.update_one('phywpc', 'wpc_id', wpclist['wpc_id'], 'wpc_owner', 'released')
        return jsonify({'status': 'reset wireless PC user and owner successful !'})
    else:
        return jsonify({'status': 'Can not find Wireless PC information in DB !'})


@api.route('/rstbgtooluser')
def rstbgtooluser():
    db = mongo()
    bgtoolhosts = db.find_all('connectiontool', 'id')
    if len(bgtoolhosts):
        print(len(bgtoolhosts))
        for bgtoolhost in bgtoolhosts:
            print(bgtoolhost['id'])
            db.update_one('connectiontool', 'id', bgtoolhost['id'], 'user', 'NA')
            db.update_one('connectiontool', 'id', bgtoolhost['id'], 'tackup', 'released')
        return jsonify({'status': 'reset connection tools user successful !'})
    else:
        return jsonify({'status': 'Can not find hosts information in DB !'})


# run in Shanghai Jenkins. send mail to all users. Project Wpc-pwd-set and CDU-Poweroff.
@api.route('/sendmailtoall')
def sendmailtoall():
    db = mongo()
    # auser = db.find_one('User', 'userid', '30')
    # send_all_email(auser['email'], 'Virtual lab Notes: Reset operation finished', 'mail/sendall', auser, auser['email'])
    alluser = db.find_all('User', 'userid')
    # print(len(alluser))
    for i in range(1, len(alluser) + 1):
        auser = db.find_one('User', 'userid', str(i))
        if auser['svname'] == 'NA':
            print('not a valid user name !')
        else:
            send_email = auser['email']
            # print(send_email)
            send_all_email(send_email, 'Virtual lab Notes: Reset operation finished', 'mail/sendall', auser, send_email)
            time.sleep(3)
    return jsonify({'status': 'set mail to all users ok !'})


@api.route('/jirasearch')
def jirasearch():
    db = mongo()
    db.delete_all('jiraresult')
    jiraurl = 'https://track.eng.sonicwall.com/'
    jirauser = db.find_one('GlobalConfig', 'id', 'jira')
    jirapwd = db.find_one('GlobalConfig', 'id', 'jira')

    jiralogin = JIRA(jiraurl, basic_auth=(jirauser['username'], jirapwd['password']))

    qa2dtslist = jiralogin.search_issues(
        'project in (WSC, GEN7, ACP, EXP, ZTA) AND status in ("Need Info", "In Test") AND "QA Assignee" in (membersOf("Eng Staff AN"))',
        fields="summary, priority, updated, status, customfield_12305, customfield_12310, customfield_10110",
        maxResults=-1,
        json_result='true')
    # print(intestdts['issues'][1])
    count = 1
    for dts in qa2dtslist['issues']:
        # print('count:   %s' % count)
        try:
            reqrelease = 'Yes' if 'Yes' in dts['fields']['customfield_12305']['value'] else "No"
        except:
            reqrelease = 'No'
        try:
            batabloker = dts['fields']['customfield_12310']['value']
        except:
            batabloker = 'No'
        nowtime = datetime.datetime.now()
        jiratime = dts['fields']['updated'].split('T')[0]
        updatetime = datetime.datetime.strptime(jiratime, "%Y-%m-%d")
        delay = nowtime - updatetime
        # print('data... %s' % delay.days)
        jiraname = dts['fields']['customfield_10110']['name']
        dtsdict = {'NO': str(count),
                   'ID': dts['key'],
                   'priority': dts['fields']['priority']['name'],
                   'status': dts['fields']['status']['name'],
                   'project': 'Gen7',
                   'delay': str(delay.days),
                   'batabloker': batabloker,
                   'reqrelease': reqrelease,
                   'summary': dts['fields']['summary'],
                   'owner': jiraname}
        checkuser = db.find_one('User', 'svname', jiraname)
        if checkuser:
            dtsdict['team'] = checkuser['Group']
        # print('dtsdict.... %s' % dtsdict)
        db.insert_one('jiraresult', dtsdict)
        count += 1

    userinfos = db.find_all('User', 'svname')
    for user in userinfos:
        # if user['Group'] == 'QA2' and user['svname'] == 'qshi':
        if user['Group'] == 'QA2':
            mailcontent = db.find_by_multi_field('jiraresult', 'team', 'QA2', 'owner', user['svname'])
            if mailcontent:
                intestcount = db.find_by_multi_field('jiraresult', 'status', 'In Test', 'owner', user['svname'])
                needinfocount = db.find_by_multi_field('jiraresult', 'status', 'Need Info', 'owner', user['svname'])
                jira_issues_email(user['email'], 'QA2 DTS Reminder(jira total: %s In Test, %s Need Info)' % (
                str(len(intestcount)), str(len(needinfocount))), 'mail/jiraresult', mailcontent, user['fullname'])
                time.sleep(1)
                print('the account: %s can not find issue in jira result.' % user['svname'])

    return jsonify({'status': 'jira search finished !'})


@api.route('/aptest/report')
def aptestreport():
    db = mongo()
    aptest = ApTest('701-6-5058')

    output = aptest.update_aptest()
    return jsonify({'status': 'aptest filter reports finished !'})


@api.route('get/firewall/status')
def getstauts():
    # RefreshG7('mydevice')
    RefreshG7('all')
    return jsonify({'status': 'get all G7 dut status in lab finished.'})


# @api.route('get/firewall/status')
# def getstauts():
#     db = mongo()
#     cdu = CDU()
#
#     # allg7dut = db.find_many_sort('DUT', 'User', 'zye', 'id', 'up')
#     # allg7dut = db.find_many('DUT', 'id', '308')
#     # allg7dut = db.find_by_multi_field('DUT', 'User', 'rmeng', 'ProductType', 'G7')
#     allg7dut = db.find_many('DUT', 'ProductType', 'G7')
#     for adutinfo in allg7dut:
#         powerstatus = []
#         print('start**********************************************************************')
#         print(f'start check dut: {adutinfo["id"]}, {adutinfo["Product"]}')
#         if adutinfo['id'] == '312' or adutinfo['id'] == '311':
#             print('the dut do not need check device info because of owner requirement.')
#         else:
#             for powerinfo in adutinfo['PowerInfo']:
#                 power_name = powerinfo['PowerController']
#                 power_channel = powerinfo['PowerChannel']
#                 power_map = db.find_one('PowerController', 'id', power_name)
#                 powercheck = cdu.Check_CDU(power_map['IPAddress'], power_channel)
#                 powerstatus.append(True if powercheck == 'On' else False)
#             print(f'dut power: {powerstatus}')
#             if not all(powerstatus):
#                 dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
#                 fwstatus = {'errormsg': 'dut power off',
#                             'updatelog': f'{dates}: Auto update FW Status failed. DUT power off.'}
#                 db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
#                 print('get firewall status failed,DUT power off.')
#                 # return jsonify({'status': 'get firewall status failed,DUT power off.'})
#             else:
#                 res = False
#                 output = ''
#                 cmds = ['show status system', 'show status interfaces', 'diag show build-info',
#                         'export core-dump ' + chr(9)]
#                 consoleinfo = db.find_one('ConsoleManager', 'id', adutinfo['ConsoleInfo']['ConsoleManager'])
#                 if '15700' in adutinfo['Product'] or '14700' in adutinfo['Product']:
#                     soniccore = adutinfo['Soniccore'][0]
#                     fw = FirewallCLI(soniccore=soniccore, console_ip=consoleinfo['IPAddress'],
#                                      console_port=adutinfo['ConsoleInfo']['TelnetPort'])
#                     for i in range(1):
#                         (res, output) = fw.do_cli_commands(cmds, tag=1, product='nssp')
#                         if res:
#                             for j in range(2, 5):
#                                 (loginres, loginmsg) = fw.nssplogin(errcode=1, blade=j)
#                                 print(f'nssp login: {loginres}, {loginmsg}')
#                                 if loginres:
#                                     (res, msg) = fw.do_cli_commands(['export core-dump ' + chr(9)], tag=1, product='nssp')
#                                     if res:
#                                         output += msg
#                             break
#                 else:
#                     soniccore = {'user': '', 'password': ''}
#                     fw = FirewallCLI(soniccore=soniccore, console_ip=consoleinfo['IPAddress'],
#                                      console_port=adutinfo['ConsoleInfo']['TelnetPort'])
#                     for i in range(2):
#                         (res, output) = fw.do_cli_commands(cmds, tag=1)
#                         if res:
#                             break
#                 if res:
#                     (fwstatus, fwips, errormsg) = fwcheck(output)
#                     if errormsg:
#                         dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
#                         fwstatus = {'errormsg': errormsg, 'updatelog': f'{dates}: Auto update FW Status failed. telnet console manager or login FW failed.'}
#                         db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
#                         print('get firewall status failed, telnet console manager or login FW failed.')
#                     else:
#                         db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
#                         db.update_one('DUT', 'id', adutinfo['id'], 'ProductType', 'G7')
#                         for fwip in fwips:
#                             for interinfo in adutinfo['InterfaceInfo']['Interface']:
#                                 if fwip['port'] == interinfo['name']:
#                                     # print(f'interinfo: {interinfo}')
#                                     db.update_one_inerface('DUT', adutinfo['id'], interinfo['name'], 'fwip', fwip['ip'])
#                                     db.update_one_inerface('DUT', adutinfo['id'], interinfo['name'], 'linkstatus', fwip['linkstatus'])
#                         print('get firewall all status successed')
#
#                 else:
#                     print('send cmd to dut failed.')
#                     dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
#                     fwstatus = {'errormsg': output,
#                                 'updatelog': f'{dates}: {output}'}
#                     db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
#                     print('get firewall status failed, telnet console manager or login FW failed.')
#             print(f'sync dut: {adutinfo["id"]} status finished! ')
#             print('end%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
#     print('sync all dut status finished.')
#     return jsonify({'status': 'get all dut status finished.'})


@api.route('crash/gpg/sendmail')
def sendmails():
    db = mongo()
    g7fwlist = db.find_many_sort('DUT', 'ProductType', 'G7', 'id', 'up')
    newg7list = []
    for g7fw in g7fwlist:
        del g7fw['InterfaceInfo']
        del g7fw['ConsoleInfo']
        del g7fw['PowerInfo']
        newg7list.append(g7fw)
    for g7info in newg7list:
        if 'coredump' in g7info['FWStatus'].keys() and g7info['FWStatus']['coredump']:
            # print(g7info['User'])
            # print(g7info['FWStatus']['coredump'])
            # send_crash_email('lezhang' + '@sonicwall.com', 'DUT Crash in 7 days info', 'mail/dutcrashinfo',
            #                  g7info, )
            send_crash_email(g7info['User'] + '@sonicwall.com', 'DUT Crash in 7 days info', 'mail/dutcrashinfo',
                             g7info, )
    print('check all crash gpg file in all dut finished.')
    return jsonify({'status': 'check all crash gpg finished.'})


@api.route('/ai-search', methods=['POST'])
def ai_search():
    """AI-powered device search API"""
    print(f"[API] ===== AI Search API Called =====")
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            print("[API] Missing query parameter")
            return jsonify({
                'error': 'Missing query parameter',
                'type': 'error'
            }), 400
        
        user_query = data['query'].strip()
        username = data.get('username', None)
        print(f"[API] Processing query: '{user_query}', username: {username}")
        
        if not user_query:
            print("[API] Empty query")
            return jsonify({
                'error': 'Empty query',
                'type': 'error'
            }), 400
        
        # Initialize AI search service
        ai_service = AISearchService()
        
        # Process query with username for borrowing
        result = ai_service.process_user_query(user_query, username)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[API] Exception occurred: {str(e)}")
        current_app.logger.error(f"AI search error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'type': 'error',
            'message': 'Failed to process your request'
        }), 500
        
@api.route('/send-device-borrow-request/<device_id>', methods=['POST'])
def send_device_borrow_request(device_id):
    """Send device borrow request email to device owner"""
    print(f"[API] ===== Send Device Borrow Request API Called =====")
    try:
        data = request.get_json()
        print(f"[API] Received data: {data}")
        print(f"[API] Device ID from URL: {device_id}")
        
        device_type = data.get('device_type', 'Unknown') if data else 'Unknown'  # This is product name, not collection name
        requester_name = data.get('requester_name', 'Unknown') if data else 'Unknown'
        
        print(f"[API] Processing borrow request: device_id={device_id}, device_type={device_type}, requester={requester_name}")
        
        # Get device information from database - search in both DUT and SonicPoint collections
        db = mongo()
        device_info = db.find_one('DUT', 'id', device_id)
        actual_collection = 'DUT'
        
        if not device_info:
            device_info = db.find_one('SonicPoint', 'id', device_id)
            actual_collection = 'SonicPoint'
        
        if not device_info:
            print(f"[API] Device not found: {device_id}")
            return jsonify({
                'error': 'Device not found',
                'type': 'error'
            }), 404
        
        print(f"[API] Found device in collection: {actual_collection}")
        
        # Extract owner name and email
        owner_full_name = device_info.get('Owner', '')
        owner_username = owner_full_name.split(' ')[0] if owner_full_name else ''
        
        # Get owner email from User collection
        user_info = db.find_one('User', 'fullname', owner_full_name)
        if not user_info:
            print(f"[API] User not found: {owner_full_name}")
            return jsonify({
                'error': 'Device owner not found in user database',
                'type': 'error'
            }), 404
        
        owner_email = user_info.get('email', '')
        if not owner_email:
            print(f"[API] Owner email not found for user: {owner_full_name}")
            return jsonify({
                'error': 'Owner email not found',
                'type': 'error'
            }), 404
        
        print(f"[API] Sending email to owner: {owner_email}")
        
        # Send email
        send_device_borrow_request_email(
            to=owner_email,
            subject='Device Borrow Request',
            template='mail/deviceborrowrequest',
            device_info=[device_info],
            requester_name=requester_name,
            owner_name=owner_full_name
        )
        
        print(f"[API] Email sent successfully")
        return jsonify({
            'status': 'success',
            'message': 'Device borrow request email sent successfully',
            'type': 'success'
        })
        
    except Exception as e:
        print(f"[API] Exception occurred: {str(e)}")
        current_app.logger.error(f"Send device borrow request error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'type': 'error',
            'message': 'Failed to send borrow request email'
        }), 500


@api.route('/borrow-device/<device_id>', methods=['POST'])
def borrow_device(device_id):
    """Borrow device - reference dutborrow function"""
    print(f"[API] ===== Borrow Device API Called =====")
    try:
        data = request.get_json()
        print(f"[API] Received data: {data}")
        print(f"[API] Device ID from URL: {device_id}")
        
        requester_name = data.get('requester_name', 'Unknown') if data else 'Unknown'
        
        print(f"[API] Processing borrow request: device_id={device_id}, requester={requester_name}")
        
        # Get device information from database - search in both DUT and SonicPoint collections
        db = mongo()
        device_info = db.find_one('DUT', 'id', device_id)
        actual_collection = 'DUT'
        
        if not device_info:
            device_info = db.find_one('SonicPoint', 'id', device_id)
            actual_collection = 'SonicPoint'
        
        if not device_info:
            print(f"[API] Device not found: {device_id}")
            return jsonify({
                'error': 'Device not found',
                'type': 'error'
            }), 404
        
        print(f"[API] Found device in collection: {actual_collection}")
        
        # Extract owner and current user info
        current_user_name = device_info.get('User', '')
        owner_full_name = device_info.get('Owner', '')
        
        print(f"[API] Current User: {current_user_name}, Owner: {owner_full_name}")
        
        # Check if device can be borrowed (user should be in owner name)
        # If current_user_name is contained in owner_full_name, device is not borrowed
        if current_user_name.lower() not in owner_full_name.lower():
            print(f"[API] Device is already borrowed by: {current_user_name}")
            return jsonify({
                'error': f'Device is already borrowed by {current_user_name}',
                'type': 'error'
            }), 400
        
        # Find owner info to send email
        owner_info = db.find_one('User', 'svname', current_user_name)
        if not owner_info:
            print(f"[API] Owner user not found: {current_user_name}")
            # Continue without sending email
            owner_info = {'email': '', 'fullname': current_user_name}
        
        # Update device's User field to requester
        print(f"[API] Updating device User field from {current_user_name} to {requester_name}")
        update_result = db.update_one(actual_collection, 'id', device_id, 'User', requester_name)
        
        if not update_result:
            print(f"[API] Failed to update device User field")
            return jsonify({
                'error': 'Failed to update device information',
                'type': 'error'
            }), 500
        
        # Send email to owner about the transaction
        if owner_info.get('email'):
            print(f"[API] Sending email to owner: {owner_info['email']}")
            dutfilter = db.find_many(actual_collection, 'id', device_id)
            dut_change_user_email(
                owner_info['email'], 
                'Device transaction notification', 
                'mail/dutborrow', 
                dutfilter,
                owner_info['fullname']
            )
        else:
            print(f"[API] No email available for owner, skipping email notification")
        
        print(f"[API] Device borrowed successfully")
        return jsonify({
            'status': 'success',
            'message': f'Successfully borrowed device {device_id}',
            'type': 'success',
            'device_id': device_id,
            'requester': requester_name
        })
        
    except Exception as e:
        print(f"[API] Exception occurred: {str(e)}")
        current_app.logger.error(f"Borrow device error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'type': 'error',
            'message': 'Failed to borrow device'
        }), 500


@api.route('/return-device/<device_id>', methods=['POST'])
def return_device(device_id):
    """Return device - reference dutreturn function"""
    print(f"[API] ===== Return Device API Called =====")
    try:
        data = request.get_json()
        print(f"[API] Received data: {data}")
        print(f"[API] Device ID from URL: {device_id}")
        
        requester_name = data.get('requester_name', 'Unknown') if data else 'Unknown'
        
        print(f"[API] Processing return request: device_id={device_id}, requester={requester_name}")
        
        # Get device information from database - search in both DUT and SonicPoint collections
        db = mongo()
        device_info = db.find_one('DUT', 'id', device_id)
        actual_collection = 'DUT'
        
        if not device_info:
            device_info = db.find_one('SonicPoint', 'id', device_id)
            actual_collection = 'SonicPoint'
        
        if not device_info:
            print(f"[API] Device not found: {device_id}")
            return jsonify({
                'error': 'Device not found',
                'type': 'error'
            }), 404
        
        print(f"[API] Found device in collection: {actual_collection}")
        
        # Extract owner and current user info
        current_user_name = device_info.get('User', '')
        owner_full_name = device_info.get('Owner', '')
        
        print(f"[API] Current User: {current_user_name}, Owner: {owner_full_name}")
        
        # Find owner info to restore device to owner
        owner_info = db.find_one('User', 'fullname', owner_full_name)
        if not owner_info:
            print(f"[API] Owner not found: {owner_full_name}")
            return jsonify({
                'error': 'Device owner not found in user database',
                'type': 'error'
            }), 404
        
        # Update device's User field to owner's svname
        print(f"[API] Updating device User field from {current_user_name} to {owner_info['svname']}")
        update_result = db.update_one(actual_collection, 'id', device_id, 'User', owner_info['svname'])
        
        if not update_result:
            print(f"[API] Failed to update device User field")
            return jsonify({
                'error': 'Failed to update device information',
                'type': 'error'
            }), 500
        
        # Send email to owner about the transaction
        if owner_info.get('email'):
            print(f"[API] Sending email to owner: {owner_info['email']}")
            dutfilter = db.find_many(actual_collection, 'id', device_id)
            dut_change_user_email(
                owner_info['email'], 
                'Device transaction notification', 
                'mail/dutreturn', 
                dutfilter,
                current_user_name
            )
        else:
            print(f"[API] No email available for owner, skipping email notification")
        
        print(f"[API] Device returned successfully")
        return jsonify({
            'status': 'success',
            'message': f'Successfully returned device {device_id} to {owner_full_name}',
            'type': 'success',
            'device_id': device_id,
            'owner': owner_full_name
        })
        
    except Exception as e:
        print(f"[API] Exception occurred: {str(e)}")
        current_app.logger.error(f"Return device error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'type': 'error',
            'message': 'Failed to return device'
        }), 500


# ========== Local AI Agent Proxy APIs ==========

@api.route('/local-ai/conversations', methods=['POST'])
def create_local_ai_conversation():
    """创建Local AI Agent会话"""
    print(f"[LOCAL_AI] ===== Create Conversation Request =====")
    
    try:
        url = f"{LOCAL_AI_BASE_URL}/conversations"
        headers = get_local_ai_headers()
        payload = {"message": "开始新会话"}
        
        print(f"[LOCAL_AI] POST {url}")
        print(f"[LOCAL_AI] Payload: {payload}")
        
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=LOCAL_AI_TIMEOUT,
            verify=False
        )
        
        print(f"[LOCAL_AI] Response status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"[LOCAL_AI] Created conversation: {data.get('conversation_id')}")
            print(f"[LOCAL_AI] Expires at: {data.get('expires_at')}")
            return jsonify(data), 201
        else:
            print(f"[LOCAL_AI] Failed to create conversation: {response.text}")
            return jsonify({
                'error': 'Failed to create conversation',
                'status_code': response.status_code
            }), response.status_code
            
    except requests.exceptions.ConnectionError as e:
        print(f"[LOCAL_AI] Connection error: {str(e)}")
        return jsonify({
            'error': 'Local AI Agent unavailable',
            'message': '无法连接到AI服务，请检查服务状态'
        }), 503
    except Exception as e:
        print(f"[LOCAL_AI] Exception: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@api.route('/local-ai/conversations/<conversation_id>/messages/stream', methods=['POST'])
def send_local_ai_message(conversation_id):
    """发送消息并流式返回响应"""
    print(f"[LOCAL_AI] ===== Send Message Stream =====")
    print(f"[LOCAL_AI] Conversation ID: {conversation_id}")
    
    try:
        data = request.get_json()
        user_message = data.get('message', '') if data else ''
        print(f"[LOCAL_AI] User message: {user_message}")
        
        url = f"{LOCAL_AI_BASE_URL}/conversations/{conversation_id}/messages/stream"
        headers = {
            "X-User-Id": get_current_username(),
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }
        payload = {"message": user_message}
        
        print(f"[LOCAL_AI] POST {url}")
        print(f"[LOCAL_AI] Headers: {headers}")
        print(f"[LOCAL_AI] Body: {payload}")
        
        def generate():
            try:
                with requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=300,
                    verify=False
                ) as resp:
                    print(f"[LOCAL_AI] Stream response status: {resp.status_code}")
                    
                    # 直接转发原始字节，保持SSE格式完整
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            print(f"[LOCAL_AI] Forwarding chunk: {len(chunk)} bytes")
                            yield chunk
                            
            except Exception as e:
                print(f"[LOCAL_AI] Stream error: {str(e)}")
                yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'.encode('utf-8')
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        print(f"[LOCAL_AI] Exception in send message: {str(e)}")
        return jsonify({
            'error': 'Failed to send message',
            'message': str(e)
        }), 500


@api.route('/local-ai/conversations/<conversation_id>', methods=['DELETE'])
def delete_local_ai_conversation(conversation_id):
    """删除会话"""
    print(f"[LOCAL_AI] ===== Delete Conversation =====")
    print(f"[LOCAL_AI] Conversation ID: {conversation_id}")
    
    try:
        url = f"{LOCAL_AI_BASE_URL}/conversations/{conversation_id}"
        headers = {"X-User-Id": get_current_username()}
        
        print(f"[LOCAL_AI] DELETE {url}")
        
        response = requests.delete(
            url,
            headers=headers,
            timeout=LOCAL_AI_TIMEOUT,
            verify=False
        )
        
        print(f"[LOCAL_AI] Delete response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data), 200
        else:
            return jsonify({
                'error': 'Failed to delete conversation',
                'status_code': response.status_code
            }), response.status_code
            
    except Exception as e:
        print(f"[LOCAL_AI] Delete exception: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500
