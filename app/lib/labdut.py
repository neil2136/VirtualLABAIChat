from .mongodb import mongo
def InsertPowerAndCMIp(deviceinfo):
    db = mongo()
    #convenient id str to int
    convids = []
    for aid in deviceinfo:
        consoleinfo = db.find_one('ConsoleManager', 'id', aid['ConsoleInfo']['ConsoleManager'])
        if consoleinfo:
            aid['ConsoleInfo']['ip'] = consoleinfo['IPAddress']
        powerinfo = db.find_one('PowerController', 'id', aid['PowerInfo'][0]['PowerController'])
        if powerinfo:
            aid['PowerInfo'][0]['ip'] = powerinfo['IPAddress']
        aid['id'] = int(aid['id'])
        convids.append(aid)
    deviceinfo = sorted(deviceinfo, key=lambda keys: keys['id'])
    return deviceinfo