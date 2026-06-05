#!/usr/bin/env python
from flask import flash
from flask_login import current_user
from flask import current_app
# from .global_var import log_system_dir
from .mongodb import mongo
from config import Config
import time

def LogSorted():
    db = mongo()
    logs = db.find_all('configlog', 'svname')
    if logs:
        logs = sorted(logs, key=lambda keys: keys['time'], reverse=True)
    return logs

def LongTasksLogSorted():
    db = mongo()
    # logs = db.find_all('longtasklog', 'svname')
    logs = db.find_many('longtasklog', 'svname', current_user.svname)
    if logs:
        logs = sorted(logs, key=lambda keys: keys['time'], reverse=True)
    return logs

def LogAndCounts(type, device, operated, effective):
    db = mongo()
    dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
    deshdata = {"svname": current_user.svname, 'type': type, 'device': device,
                'operated': operated, 'effective': str(effective), 'time': dtime}
    db.insert_one('configlog', deshdata)
    desh = db.find_one('deshboard', 'id', 'totals')
    if effective == 0:
        deshdata['effective'] = '0'
        db.update_one('deshboard', 'id', 'totals', 'invalid', str(int(desh['invalid']) + 1))
    else:
        db.update_one('deshboard', 'id', 'totals', 'effective', str(int(desh['effective']) + 1))
    flash(operated)

def log_print():
    with open(Config.log_system_dir, 'r') as f:
        logprint = f.readlines()[::-1][0:1000]
    #print('logprit:    %s'% type(logprint))
    #print('logprit len:    %s' % len(logprint))
    #print(logprint)
    return logprint

# def log_pri_user(priority, info):
#     if priority == 'warning':
#         current_app.logger.warning('[' + current_user.fullname + ']-- %s' % info)
#     elif priority == 'error':
#         current_app.logger.error('[' + current_user.fullname + ']-- %s' % info)

def long_tasks_log(type, device, operated):
    db = mongo()
    dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
    deshdata = {'svname': current_user.svname, 'type': type, 'device': device,
                'operated': operated, 'time': dtime}
    db.insert_one('longtasklog', deshdata)

def insert_log_info(type, device, operated):
    db = mongo()
    dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
    deshdata = {'svname': current_user.svname, 'type': type, 'device': device,
                'operated': operated, 'effective': '1', 'time': dtime}
    db.insert_one('deshlog', deshdata)

def flash_and_log_info(info):
    db = mongo()
    desh = db.find_one('deshboard', 'id', 'totals')
    db.update_one('deshboard', 'id', 'totals', 'effective', str(int(desh['effective']) + 1))
    flash(info)
    # current_app.logger.warning('[' + current_user.fullname + ']-- %s' % info)
def flash_and_log_error(info):
    db = mongo()
    desh = db.find_one('deshboard', 'id', 'totals')
    db.update_one('deshboard', 'id', 'totals', 'invalid', str(int(desh['invalid']) + 1))
    flash(info)
    # current_app.logger.error('[' + current_user.fullname + ']-- %s' % info)
# def log_info(info):
#     current_app.logger.warning('[' + current_user.fullname + ']-- %s' % info)
#
# def log_data_info(info, data):
#
#     current_app.logger.warning('[' + current_user.fullname + ']-- %s: %s' % (info, data))
#
# def log_dutid_info(id, info):
#
#     current_app.logger.warning('[' + current_user.fullname + ']device id:' + id + '-- %s' % info)
#
# def log_error(info):
#
#     current_app.logger.error('[' + current_user.fullname + ']-- %s' % info)
#
# def log_dutid_error(id, info):
#
#     current_app.logger.error('[' + current_user.fullname + ']device id:' + id + '-- %s' % info)
#
# def log_vlan_info(id, info):
#
#     current_app.logger.warning('[' + current_user.fullname + ']vlan id:' + id + '-- %s' % info)
#
# def log_vlan_error(id, info):
#
#     current_app.logger.error('[' + current_user.fullname + ']device id:' + id + '-- %s' % info)