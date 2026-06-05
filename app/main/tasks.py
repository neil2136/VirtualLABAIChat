from celery import Celery
import time, random
from ..lib.topbar import GetVMInfo
from ..lib.mongodb import mongo
from ..lib.switchcfg import SWInitial
from ..lib.esxi.getvminfo import SyncAllVM
from ..lib.ndppcfg import fwndppconfig
from ..lib.refreshg7 import checkdutinfo

# Initialize Celery
celery = Celery("views", broker="redis://localhost:6379/0",
                backend="redis://localhost:6379/0")
db = mongo()

@celery.task
def async_ndppconfig(fw_ip, console_ip, console_port, fw_user, fw_password, adeviceget, svname):
    confres = fwndppconfig(fw_ip, console_ip, console_port, fw_user, fw_password, adeviceget, svname)
    print(f'run fwndppconfig result: {confres}')

@celery.task
def async_checkdutinfo(console_ip, console_port, adeviceget, svname, taskcount):
    confres = checkdutinfo(console_ip, console_port, adeviceget, svname, taskcount)
    print(f'run check dut info result: {confres}')

@celery.task
def syncallvm(esxip, esxuser, esxpassword):
    return SyncAllVM(esxip, esxuser, esxpassword)

@celery.task
def async_syncallvm(esxip, esxuser, esxpassword, currentname):
    db = mongo()
    task_process = syncallvm.apply_async((esxip, esxuser, esxpassword))
    print('task_process id-----' + task_process.id)
    while True:
        task = syncallvm.AsyncResult(task_process.id)
        print('task state-----' + task.state)
        dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
        deshdata = {'svname': currentname, 'type': 'VM', 'device': 'RefreshVMs',
                    'operated': 'operated', 'time': dtime}
        if task.state == 'PENDING':
            deshdata['operated'] = 'Sync VMs From ESXI ' + esxip + 'Process:      PENDING... '
            db.insert_one('longtasklog', deshdata)
            time.sleep(10)
        elif task.state == 'PROGRESS':
            deshdata['operated'] = 'Sync VMs From ESXI ' + esxip + 'Process      PROGRESS... '
            db.insert_one('longtasklog', deshdata)
            time.sleep(10)
        elif task.state == 'FAILURE':
            deshdata['operated'] = 'Sync VMs From ESXI ' + esxip + 'Process:      FAILURE ! '
            db.insert_one('longtasklog', deshdata)
            break
        elif task.state == 'SUCCESS':
            deshdata['operated'] = 'Sync VMs From ESXI ' + esxip + 'Process:      SUCCESS. '
            db.insert_one('longtasklog', deshdata)
            break

@celery.task
def async_allexsivm(esxip, esxuser, esxpassword):
    task_process = syncallvm.apply_async((esxip, esxuser, esxpassword))
    print('task_process id-----' + task_process.id)

@celery.task
def VMsInfo(esxip, esxuser, esxpassword, currentname):
    return GetVMInfo(esxip, esxuser, esxpassword, currentname)

@celery.task
def async_getesxvminfo(esxip, esxuser, esxpassword, currentname):
    db = mongo()
    task_process = VMsInfo.apply_async((esxip, esxuser, esxpassword, currentname))
    print('task_process id-----' + task_process.id)
    while True:
        task = VMsInfo.AsyncResult(task_process.id)
        print('task state-----' + task.state)
        dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
        deshdata = {'svname': currentname, 'type': 'VM', 'device': 'RefreshVMs',
                    'operated': 'operated', 'time': dtime}
        if task.state == 'PENDING':
            deshdata['operated'] = 'ESX ' + esxip + ' Refresh VMs Process:      PENDING... '
            db.insert_one('longtasklog', deshdata)
            time.sleep(2)
        elif task.state == 'PROGRESS':
            deshdata['operated'] = 'ESX ' + esxip + ' Refresh VMs Process:      PROGRESS... '
            db.insert_one('longtasklog', deshdata)
            time.sleep(2)
        elif task.state == 'FAILURE':
            deshdata['operated'] = 'ESX ' + esxip + ' Refresh VMs Process:      FAILURE ! '
            db.insert_one('longtasklog', deshdata)
            break
        elif task.state == 'SUCCESS':
            deshdata['operated'] = 'ESX ' + esxip + ' Refresh VMs Process:      SUCCESS. '
            db.insert_one('longtasklog', deshdata)
            break

@celery.task
def async_initialdutports(getdutinfo, action, currentname):
    portinfo = getdutinfo['InterfaceInfo']['Interface']
    for aport in portinfo:
        dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
        deshdata = {'svname': currentname, 'type': 'DUT', 'device': action + 'DUT',
                    'operated': action, 'time': dtime}
        swidinfo = db.find_one('Switch', 'id', aport['SwitchID'])
        initrst, logs = SWInitial(aport['porttype'], swidinfo['ConsoleServer'], aport['SwitchPort'])
        if initrst == 'fail':
            deshdata['operated'] = action+' DUT ' + getdutinfo['id'] + ' Process: Initial Port ' + aport[
                'name'] + ' Failed.'
        elif initrst == 'lag on':
            deshdata['operated'] = action + ' DUT ' + getdutinfo['id'] + ' Process: Initial Port ' + aport[
                'name'] + ' Failed. Lag on in Switch !'
            db.update_one_inerface(getdutinfo['DeviceType'], getdutinfo['id'], aport['name'], 'lag', 'on')
        else:
            deshdata['operated'] = action+' DUT ' + getdutinfo['id'] + ' Process: Initial Port ' + aport[
                'name'] + ' Successful.'
            db.update_one_inerface(getdutinfo['DeviceType'], getdutinfo['id'], aport['name'], 'portpower', 'shutdown')
            db.update_one_inerface(getdutinfo['DeviceType'], getdutinfo['id'], aport['name'], 'portmode', 'access')
            db.update_one_inerface(getdutinfo['DeviceType'], getdutinfo['id'], aport['name'], 'untagvlan', 'UnusedNetwork')
            db.update_one_inerface(getdutinfo['DeviceType'], getdutinfo['id'], aport['name'], 'tagvlan', '--')
            db.update_one_inerface(getdutinfo['DeviceType'], getdutinfo['id'], aport['name'], 'stp', 'on')
            db.update_one_inerface(getdutinfo['DeviceType'], getdutinfo['id'], aport['name'], 'lag', 'off')
        db.insert_one('longtasklog', deshdata)
    # insertlog.apply_async((getdutinfo, action, currentname))
    db.update_one(getdutinfo['DeviceType'], 'id', getdutinfo['id'], 'keepAlive', '1')

    dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
    deshdata = {'svname': currentname, 'type': 'DUT', 'device': action + 'DUT', 'time': dtime,
                'operated': action + ' DUT ' + getdutinfo['id'] + ' Process: Finished Initial All Ports.'}
    db.insert_one('longtasklog', deshdata)

@celery.task
def send_async_email(email_data):
    print('send maill ------')
    time.sleep(3)
    print('end send mail...')

@celery.task(bind=True)
def long_task(self):
    """Background task that runs a long function with progress reports."""
    verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
    adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
    noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
    message = ''
    total = random.randint(10, 50)
    for i in range(total):
        if not message or random.random() < 0.25:
            message = '{0} {1} {2}...'.format(random.choice(verb),
                                              random.choice(adjective),
                                              random.choice(noun))
        self.update_state(state='PROGRESS',
                          meta={'current': i, 'total': total,
                                'status': message})
        time.sleep(1)
    return {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': 42}
# @celery.task(bind=True)
# def async_getvminfo(self, esxip, esxuser, esxpassword, currentname):
#
#     GetVMInfo(esxip, esxuser, esxpassword, currentname)
#     """Background task that runs a long function with progress reports."""
#     verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
#     adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
#     noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
#     message = ''
#     total = random.randint(10, 50)
#     for i in range(total):
#         if not message or random.random() < 0.25:
#             message = '{0} {1} {2}...'.format(random.choice(verb),
#                                               random.choice(adjective),
#                                               random.choice(noun))
#         self.update_state(state='PROGRESS',
#                           meta={'current': i, 'total': total,
#                                 'status': message})
#         time.sleep(1)
#     return {'current': 100, 'total': 100, 'status': 'Task completed!',
#             'result': 42}