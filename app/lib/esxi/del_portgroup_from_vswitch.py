#!/usr/bin/env python

from pyVim.connect import SmartConnect, Disconnect, SmartConnectNoSSL
from pyVmomi import vim
import atexit
import sys
import argparse


def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSpehre service to connect to')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use')

    parser.add_argument('-p', '--password',
                        required=True,
                        action='store',
                        help='Password to use')

    parser.add_argument('-g', '--portgroup',
                        required=True,
                        action='store',
                        help='Portgroup to delete')

    args = parser.parse_args()
    return args


def GetVMHosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj


def DelHostsPortgroup(hosts, portgroupName):
    for host in hosts:
        host.configManager.networkSystem.RemovePortGroup(portgroupName)


def DelHostPortgroup(host, portgroupName):
    host.configManager.networkSystem.RemovePortGroup(portgroupName)


def main():
    args = get_args()
    serviceInstance = SmartConnectNoSSL(host=args.host,
                                   user=args.user,
                                   pwd=args.password,
                                   port=443)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()

    hosts = GetVMHosts(content)
    DelHostsPortgroup(hosts, args.portgroup)


# Main section
if __name__ == "__main__":
    sys.exit(main())
