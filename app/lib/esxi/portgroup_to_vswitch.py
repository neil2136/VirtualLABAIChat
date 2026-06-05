#!/usr/bin/env python
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVmomi import vim
from ..mongodb import mongo as db
import atexit, re

def get_obj(content, vimtype, name):
    """
    get_obj(content, [vim.Datastore], "Datastore Name")
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            # print(Item: + c.name) # for debugging
            obj = c
            break
    if not obj:
        print('not name in portgroup')
        # raise RuntimeError("Managed Object " + name + " not found.")
    return obj

def GetVMHosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj

def AddHostsPortgroup(hosts, vswitchName, portgroupName, vlanId):
    for host in hosts:
        AddHostPortgroup(host, vswitchName, portgroupName, vlanId)

def AddHostPortgroup(host, vswitchName, portgroupName, vlanId):
    portgroup_spec = vim.host.PortGroup.Specification()
    portgroup_spec.vswitchName = vswitchName
    portgroup_spec.name = portgroupName
    portgroup_spec.vlanId = int(vlanId)
    network_policy = vim.host.NetworkPolicy()
    network_policy.security = vim.host.NetworkPolicy.SecurityPolicy()
    network_policy.security.allowPromiscuous = True
    network_policy.security.macChanges = False
    network_policy.security.forgedTransmits = False
    portgroup_spec.policy = network_policy

    host.configManager.networkSystem.AddPortGroup(portgroup_spec)

def SearchPortGroup(content, pgfullname):
    portgroups = []
    # searching for port group
    pg = get_obj(content, [vim.Network], pgfullname)
    if hasattr(pg, 'name'):
        if pgfullname == pg.name:
            portgroups.append({pgfullname: 'Existing'})
    return portgroups

def DelHostsPortgroup(hosts, portgroupName):
    for host in hosts:
        host.configManager.networkSystem.RemovePortGroup(portgroupName)

def ESXIPortGroups(operate, host, pgname, svname, vlanstart, vlanend):
    pgs = []
    vswitch = 'vSwitch0'
    esx = db().find_one('ESX', 'IPAddress', host)
    serviceInstance = SmartConnectNoSSL(host=host, user=esx['AdminUser'], pwd=esx['AdminPass'], port=443)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()
    if operate == 'getpg':
        searchpg = SearchPortGroup(content, pgname)
        if searchpg == []:
            pgs.append({'pg': 'PortGroup: %s is not in ESXI: %s !' % (pgname, host)})
        else:
            pgs.append({'pg': 'PortGroup: %s is in ESXI: %s !' % (pgname, host)})
    elif operate == 'addpg':
        if svname == 'UnusedNetwork':
            searchpg = SearchPortGroup(content, svname)
            if searchpg == []:
                hosts = GetVMHosts(content)
                AddHostsPortgroup(hosts, vswitch, svname, '1')
                pgs.append({'pg': 'PortGroup: %s add to the ESXI: %s sucessful !' % (svname, host)})
            else:
                pgs.append({'pg': 'PortGroup: %s is existing in ESXI, Do not need add.' % svname})
        else:
            for partvlan in range(int(vlanstart), int(vlanend) + 1):
                pgfullname = svname + '_vlan' + str(partvlan)
                print('add pgfullname : %s' % pgfullname)
                searchpg = SearchPortGroup(content, pgfullname)
                if searchpg == []:
                    hosts = GetVMHosts(content)
                    AddHostsPortgroup(hosts, vswitch, pgfullname, partvlan)
                    pgs.append({'pg': 'PortGroup: %s add to the ESXI: %s sucessful !' % (pgfullname, host)})
                else:
                    pgs.append({'pg': 'PortGroup: %s is existing in ESXI, Do not need add.' % pgfullname})
    elif operate == 'delpg':
        for partvlan in range(int(vlanstart), int(vlanend) + 1):
            pgfullname = svname + '_vlan' + str(partvlan)
            print('delete pgfullname : %s' % pgfullname)
            searchpg = SearchPortGroup(content, pgfullname)
            if searchpg:
                hosts = GetVMHosts(content)
                try:
                    DelHostsPortgroup(hosts, pgfullname)
                    pgs.append({'pg': 'Deleted the PortGroup: %s in the ESXI: %s sucessful !' % (pgfullname, host)})
                except:
                    pgs.append(({'pg': 'The PortGroup: %s is using in VMs NIC for ESXI: %s, can not be deleted. Please remove them first in My VMs and try again !'% (pgfullname, host)}))
            else:
                pgs.append({'pg': 'The PortGroup: %s is not existing in ESXI, Do not need delete.' % pgfullname})
    return pgs

