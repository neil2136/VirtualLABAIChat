# from flask import redirect
# from ..models import *
# from ..email import *
# from ..lib.cductrl import *
# from ..lib.fwlogin import *
# from ..lib.log_old import *
from .. lib.mongodb import mongo
from ..lib.cductrl import CDU
from .flashandlog import flash_and_log_error, flash_and_log_info

def judgeduttype(duttype, dut_id):
    db = mongo()
    if duttype == 'DUT':
        product_filter = db.find_many('filter', 'type', 'sonicwall')
        print('dut_id: %s, duttype: %s' % (dut_id, duttype))
        return product_filter
    elif duttype == 'SonicPoint':
        product_filter = db.find_many('filter', 'type', 'sonicpoint')
        print('dut_id: %s, duttype: %s' % (dut_id, duttype))
        return product_filter

def dutpowercfg(dutid, kind, duttype):
    db = mongo()
    cdu = CDU()
    result = []
    idfilter = db.find_one(duttype, 'id', dutid)
    keepalive_db = idfilter['keepAlive']
    for powerinfo in idfilter['PowerInfo']:
        power_name = powerinfo['PowerController']
        power_channel = powerinfo['PowerChannel']
        power_map = db.find_one('PowerController', 'id', power_name)
        # print('power-----------------------%s  %s' % (power_name, power_channel))
        if power_map:
            power_ip = power_map['IPAddress']
            if kind == 'Up':
                on_result = cdu.On_CDU(power_ip, power_channel)
                if on_result == None:
                    flash_and_log_error('get power info failed. login failed, due to TIMEOUT or EOF ' + power_ip +'   '+ power_channel)
                elif on_result == 'Shutdown':
                    flash_and_log_info('the current CDU Channel is under Shutdown/Reboot. Please wait 1 Min to try again !')
                elif on_result != 'ok':
                    flash_and_log_info('set power info failed. can not set the channel to \'On\' in CDU. ' + power_ip +'   '+ power_channel + '\n console print: ' + on_result)
                else:
                    if keepalive_db == '1':
                        flash_and_log_info('Check in Core Switch and DB they are same! do not do anything. power status: ' + kind)
                    elif keepalive_db == 0:
                        #print('duttype----------------%s' % duttype)
                        change_status = db.update_one(duttype, 'id', dutid, 'keepAlive', '1')
                        #print('changestatus----------------%s %s' % (change_status.matched_count, change_status.modified_count))
                        if change_status.modified_count == 1:
                            flash_and_log_info('Set successfully! Now Switch and DB are same, power status: ' + kind)
                        else:
                            flash_and_log_error('Set the keepAlive to On failed in DB, current power status in Switch is: ' + kind)
            elif kind == 'Down':
                off_result = cdu.Off_CDU(power_ip, power_channel)
                if off_result == None:
                    flash_and_log_error('get power info failed. login failed, due to TIMEOUT or EOF ' + power_ip +'   '+ power_channel)
                elif off_result == 'ok':
                    if keepalive_db == '1':
                        #print('duttype----------------%s' % duttype)
                        change_status = db.update_one(duttype, 'id', dutid, 'keepAlive', 0)
                        #print('changestatus----------------%s %s' % (change_status.matched_count, change_status.modified_count))
                        if change_status.modified_count == 1:
                            flash_and_log_info(
                                'completed send \'Shutdown\' to CDU %s %s, Due to the delay of the CDU configuration itself,\
                                the operation result needs to wait for more than 10 seconds. Please check the console status of DUT' % (
                                    power_ip, power_channel))
                            # portline = idfilter['InterfaceInfo']['Interface']
                            # for dutport in portline:
                            #     #print(dutport)
                            #     db.update_one_inerface(duttype, dutid, dutport['name'], 'portpower', 'Down')
                        else:
                            flash_and_log_error('Set the keepAlive to Off failed in DB, current power status in CDU is: ' + kind)
                    elif keepalive_db == 0:
                        flash_and_log_info('Check in Core Switch and DB they are same! do not do anything. power status: ' + kind)
            elif kind == 'Reboot':
                print(f'start login cdu, power_ip: {power_ip}, power_channel: {power_channel}')
                reboot_result = cdu.Reboot_CDU(power_ip, power_channel)
                if reboot_result == None:
                    flash_and_log_error('get power info failed. login failed, due to TIMEOUT or EOF ' + power_ip +'   '+ power_channel)
                else:
                    if keepalive_db == 0:
                        db.update_one(duttype, 'id', dutid, 'keepAlive', '1')
                    flash_and_log_info('Reboot the DUT ID %s Successfully ! The operation will take effect within 10 seconds : CDU ip: %s, Channel: %s' % (dutid, power_ip, power_channel))
            elif kind == 'Refresh':
                refresh_result = cdu.Check_CDU(power_ip, power_channel)
                if refresh_result:
                    result.append(refresh_result)
            else:
                flash_and_log_error(('can not get parameters from page:   ' + power_ip + ':  ' + power_channel))
                return 'fail'
        else:
            flash_and_log_error('Can not find PowerController information in DB !')
            return 'fail'
    if kind == 'Refresh':
        # print(f'11111111111111: {result}')
        if len(result) == 0:
            flash_and_log_error(
                'get power info failed. login failed, due to TIMEOUT or EOF ')
        else:
            if result.count('On') > 0:
                db.update_one(duttype, 'id', dutid, 'keepAlive', '1')
            else:
                db.update_one(duttype, 'id', dutid, 'keepAlive', 0)
            flash_and_log_info('Refresh the DUT ID %s finished!' % dutid)
    return 'ok'

