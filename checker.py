#!/usr/bin/env python
"""
A Python Script To Check The Server Update Status And The Currently Installed Kernel.
https://github.com/APenketh/server-kernel-status-checker
"""

import os
import sys
import platform
import socket
import time
import subprocess
import re
from subprocess import PIPE, Popen
import yum

yumB = yum.YumBase()
yumB.preconf.debuglevel = 0

"""Check the verion of Python running. Returns True for Python version 2.7 and above. False for 2.6 and below."""
def checkPythonInstall():
    versionToCheck = (2, 7)
    currentVersion = sys.version_info
    return bool(True
                if currentVersion[0] >= versionToCheck[0]
                and currentVersion[1] >= versionToCheck[1]
                else False)

"""Checks the oeprating system type. Supported types are returned while unsupported are printed and exited."""
def getDist():
    distName = platform.linux_distribution()[0]
    if distName.upper() in ["RHEL", "CENTOS", "FEDORA",
                            "CENTOS LINUX", "RED HAT ENTERPRISE LINUX SERVER"]:
        return distName + " " + platform.linux_distribution()[1]
    elif distName.upper() in ["DEBIAN", "UBUNTU"]:
        print "{0} Based Systems Are Currently Not Compatible With This Script.".format(distName)
        exit()
    else:
        print "Platform {0} Is Not Compatible With This Script.".format(distName)
        exit()

"""Performs checks agasint the Kernel & provides a logical output."""
def kernelCheck():
    currentKernel = "kernel-" + platform.release()
    if checkPythonInstall() is True:
        latestInstalledKernel = (
            subprocess.check_output(["rpm -q kernel | tail -n 1"], shell=True).strip())
        latestKernel = (subprocess.check_output([
            "yum list updates kernel -q --disableexcludes=all | grep -vi 'updated' | awk {'print $2'} 2>&1"
            ], shell=True, stderr=open('/dev/null', 'w')).strip())
    elif checkPythonInstall() is False:
        latestInstalledKernelOut = Popen(["rpm -q kernel | tail -n 1"], shell=True, stdout=PIPE)
        latestInstalledKernel = latestInstalledKernelOut.communicate()[0].strip()
        latestKernelOut = Popen([
            "yum list updates kernel -q --disableexcludes=all | grep -vi 'updated' | awk {'print $2'} 2>&1"
            ], shell=True, stderr=open('/dev/null', 'w'), stdout=PIPE)
        latestKernel = latestKernelOut.communicate()[0].strip()

    if latestKernel == "":
        if currentKernel == latestInstalledKernel:
            kcrr = "    Server Kernel Is On The Latest Version: {0}".format(currentKernel)
        else:
            kcrr = ("You Need To Reboot The Server To Make Use Of The Latest Kernel."
                    + "\n    Server is on the Kernel version:\t{0}".format(currentKernel)
                    + "\n    Latest Kernel installed is:\t\t{0}".format(latestInstalledKernel))
    else:
        if currentKernel != latestKernel:
            kcrr = ("You Need To Download The Latest Kernel And Reboot The Server."
                    + "\n    Server is on the Kernel version:\t{0}".format(currentKernel)
                    + "\n    Latest Kernel To Download Is:\tkernel-{0}.x86_64".format(latestKernel))
        else:
            kcrr = "There Was An Error Processing Your Kernels. Please Check Manually"
    return kcrr

class yumCheck():
    """Checks for how many avalible updates are pending within the system."""
    def updateChecker(self):
        package_list = yumB.doPackageLists(pkgnarrow='updates', patterns='', ignore_case=True)
        totalUpdatesAv = 0

        if package_list.updates:
            for pkg in package_list.updates:
                totalUpdatesAv += 1
            totalUpdatesAv = str(totalUpdatesAv) + " Updates"
        else:
            totalUpdatesAv = "Zero. You Are Up To Date"
        return totalUpdatesAv

    """Gets the time and date fo the last update from yum history and returns that value."""
    def lastUpdateChecker(self):
        for old in yumB.history.old():
            if "Update" in (hpkg.state for hpkg in old.trans_data):
                lucr = time.ctime(old.beg_timestamp)
        return lucr

    """Checks for any exclusions defined within the yum configuration file."""
    def yumExChecker(self):
        yumConfFile = yumB.conf.config_file_path
        if os.path.exists("{0}".format(yumConfFile)):
            if subprocess.call(["grep --quiet ^exclude=$ /etc/yum.conf"], shell=True) == False:
                yumExResu = "You Have No Exclusions Set Up"
            elif subprocess.call(["grep --quiet ^exclude= /etc/yum.conf"], shell=True) == False:
                if checkPythonInstall() is True:
                    yumExResu = (subprocess.check_output([
                        "grep ^exclude= /etc/yum.conf | sed 's/exclude=//' | tr '\n' ' '"
                        ], shell=True, stderr=open('/dev/null', 'w')).strip())
                elif checkPythonInstall() is False:
                    yumExcludesResOut = (Popen([
                        "grep ^exclude= /etc/yum.conf | sed 's/exclude=//' | tr '\n' ' '"
                        ], shell=True, stderr=open('/dev/null', 'w'), stdout=PIPE))
                    yumExResu = yumExcludesResOut.communicate()[0].strip()
            else:
                yumExResu = "You Have No Exclusions Set Up"
        else:
            yumExResu = "Cannot Locate The Yum Configuration File, Please Check Manually."
        return yumExResu

class ThreeColTable(object):

    MIN_WIDTH = 80
    MAX_WIDTH = 95

    _ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')

    def __init__(self, width=None):
        self.width = width
        self._left = []
        self._center = []
        self._right = []

    def _raw(self, s):
        return self._ANSI_ESCAPE.sub('', s)

    def _trim(self, s, maxlen, suffix='...'):
        rawlen = len(self._raw(s))
        if rawlen <= maxlen:
            return s
        markup = list(reversed([(m.start(), m.end()) for m in self._ANSI_ESCAPE.finditer(s)]))
        end = len(s)
        cut = rawlen-maxlen+len(suffix)
        while len(markup):
            s1, s2 = s[:end-min(end-markup[0][1], cut)], s[end:]
            cut -= end-markup[0][1]
            if cut < 0:
                s = s1+suffix+s2
                break
            s = s1+s2
            end = markup[0][0]
            markup.pop(0)
        return s

    def _lines(self):
        height = max(len(self._left), len(self._center), len(self._right))
        for i in range(height):
            left = center = right = ''
            if i < len(self._left):
                left = self._left[i]
            if i < len(self._center):
                center = self._center[i]
            if i < len(self._right):
                right = self._right[i]
            yield (left, center, right)

    def _compute_width(self):
        mwidth = 0
        for l, c, r in self._lines():
            width = len(self._raw(l))+len(self._raw(c))+len(self._raw(r))
            if c or r:
                width += 8
            mwidth = max(mwidth, width)
        return max(self.MIN_WIDTH, min(self.MAX_WIDTH, mwidth))

    def left(self, s):
        if not isinstance(s, list):
            s = [str(s)]
        self._left.extend(s)

    def right(self, s, alignright=False):
        if not isinstance(s, list):
            s = [str(s)]
        if not alignright:
            maxlen = max([len(self._raw(x)) for x in s])
            s = [x + (maxlen-len(self._raw(x)))*' ' for x in s]
        self._right.extend(s)

    def line(self, left, right):
        self.left(left)
        self.right(right)

    def space(self, ruler=False):
        height = max(len(self._left), len(self._center), len(self._right))
        for col in (self._left, self._center, self._right):
            col.extend((height+1-len(col))*[''])
        if ruler:
            self._left[-1] = '---'

    def render(self):
        if self.width is None:
            self.width = self._compute_width()
        ret = []
        ret.append(self.width * '=')
        for left, center, right in self._lines():
            if left == '---':
                ret.append(self.width * '-')
                continue
            if not center and not right:
                ret.append(self._trim(left, self.width))
                continue
            padding1 = max(4, (self.width-len(self._raw(center)))/2-len(self._raw(left))) * ' '
            padding2 = max(4, self.width-len(self._raw(left))-len(padding1)-len(self._raw(center))-len(self._raw(right))) * ' '
            line = left + padding1 + center + padding2 + right
            ret.append(line)
        ret.append(self.width * '=')
        return '\n'.join(ret)

def overview():
    yumC = yumCheck()
    tbl = ThreeColTable()

    tbl.line('Server Name: %s' % socket.gethostname(), 'OS Version: %s' % getDist())
    tbl.space(ruler=True)
    tbl.left('Server Update Status:')
    tbl.left('--------------')
    tbl.left('    Avalible Updates To Download:\t%s' % yumC.updateChecker())
    tbl.left('    Last Package Update Time:\t\t%s' % yumC.lastUpdateChecker())
    tbl.left('    Packages Excluded From Updating:\t%s' % yumC.yumExChecker())
    tbl.space(ruler=True)
    tbl.left('Kernel Version Status:')
    tbl.left('--------------')
    tbl.left(kernelCheck())

    print tbl.render()

if __name__ == '__main__':
    overview()
