#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2015, John Torres <enfermo337@yahoo.com>
#
# This file is part of Ansible-CloudConfig
#
# Ansible-CloudConfig is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible-CloudConfig is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible-CloudConfig.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: cloudconfig_user
author: John Torres
version_added: "0.1"
short_description: Manage user accounts in a cloudconfig file
requirements: [ cloudconfig ]
description:
    - Manage user accounts and user attributes within a user_data cloudconfig file.
options:
    name:
        required: true
        aliases: [ "user" ]
        description:
            - Name of the user to create, remove or modify.
    groups:
        required: false
        description:
            - Puts the user in this comma-delimited list of groups. When set to
              the empty string ('groups='), the user is removed from all groups
              except the primary group.
    password:
        required: false
        description:
            - Optionally set the user's password to this crypted value.  See
              the user example in the github examples directory for what this looks
              like in a playbook. See U(http://docs.ansible.com/faq.html#how-do-i-generate-crypted-passwords-for-the-user-module)
              for details on various ways to generate these password values.
              Beware of security issues.
    state:
        required: false
        default: "present"
        choices: [ present, absent ]
        description:
            - Whether the account should exist or not, taking action if the state is different from what is stated.
    
    ssh_authorized_keys:
        required: false
        aliases: [ "sshkeys" ]
        description:
            - SSH key for the user in question.
              This B(will) overwrite an existing SSH key.

    update_password:
        required: false
        default: "always"
        choices: [ always, on_create ]
        description:
            - Update a user with an existing password.
              By default, this B(will) overwrite an existing password
'''

EXAMPLES = '''
# Add the user 'johnd' without password and groups of 'admin'
- user: name=johnd password="*" groups=admin

# Add the user 'james' with a bash shell, appending the group 'admins' and 'developers' to the user's groups
- user: name=james password="sdf$Kll..." groups=admins,developers update_password=yes

# Remove the user 'johnd'
- user: name=johnd state=absent

# Create user with SSH key for user jsmith
- user: name=jsmith sshkeys="ssh-rsa AAAAAA..... johnt@me.com" state=present
'''

import os
import pwd
import grp
import syslog
import platform
import socket
import time

try:
    import spwd
    HAVE_SPWD=True
except:
    HAVE_SPWD=False


class CloudConfig_User(object):
    """
    This is a generic CloudConfig_User manipulation class. Normally it would be subclassed
    based on platform. However we are using a golang binary under the hood, so usage is consistent.
    Also note that this is specific to CoreOS at the moment.

    A subclass may wish to override the following action methods:-
      - create_user()
      - remove_user()
      - modify_user()
      - user_exists()

    All subclasses MUST define platform and distribution (which may be None).
    """

    platform = 'Generic'
    distribution = None
    CLOUDCONFIG = '/etc/configdrive/cloud-config.yml'
    DATE_FORMAT = '%Y-%m-%d'

    def __new__(cls, *args, **kwargs):
        return load_platform_subclass(CloudConfig_User, args, kwargs)

    def __init__(self, module):
        self.module              = module
        self.state               = module.params['state']
        self.name                = module.params['name']
        self.groups              = module.params['groups']
        self.password            = module.params['password']
        self.ssh_authorized_keys = module.params['ssh_authorized_keys']
        self.update_password     = module.params['update_password']

        # select whether we dump additional debug info through syslog
        self.syslogging = False


    def execute_command(self, cmd, use_unsafe_shell=False, data=None):
        if self.syslogging:
            syslog.openlog('ansible-%s' % os.path.basename(__file__))
            syslog.syslog(syslog.LOG_NOTICE, 'Command %s' % '|'.join(cmd))

        return self.module.run_command(cmd, use_unsafe_shell=use_unsafe_shell, data=data)

    def remove_user_userdel(self):
        cmd = [self.module.get_bin_path('cloudconfig', True)]

        cmd.append("users")
        cmd.append("-action=remove")
        cmd.append(self.name)

        return self.execute_command(cmd)

    def create_user_useradd(self, command_name='cloudconfig'):
        cmd = [self.module.get_bin_path(command_name, True)]

        cmd.append("users")
        cmd.append("-action=add")

        if self.groups is not None and len(self.groups):
            groups = self.get_groups_set()
            cmd.append('-groups=')
            cmd.append(','.join(groups))

        if self.password is not None:
            cmd.append('-passwd=')
            cmd.append(self.password)

        if self.ssh_authorized_keys is not None:
            cmd.append('-ssh-authorized-keys=')
            cmd.append(self.ssh_authorized_keys)

        cmd.append(self.name)
        return self.execute_command(cmd)

    def modify_user_usermod(self):
        cmd = [self.module.get_bin_path('cloudconfig', True)]
        cmd.append('users')

        info = self.user_info()

        if self.groups is not None:
            current_groups = self.user_group_membership()
            groups_need_mod = False
            groups = []

            if self.groups == '':
                if current_groups:
                    groups_need_mod = True
            else:
                groups = self.get_groups_set(remove_existing=False)
                group_diff = set(current_groups).symmetric_difference(groups)

                if group_diff:
                    groups_need_mod = True

            if groups_need_mod:
                cmd.append('-groups=')
                cmd.append(','.join(groups))

        if self.update_password == 'always' and self.password is not None and info[1] != self.password:
            cmd.append('-password=')
            cmd.append(self.password)

        if self.ssh_authorized_keys is not None:
            cmd.append('-ssh-authorized-keys=')
            cmd.append(self.ssh_authorized_keys)

        # skip if no changes to be made
        if len(cmd) == 1:
            return (None, '', '')
        elif self.module.check_mode:
            return (0, '', '')

        cmd.append(self.name)
        return self.execute_command(cmd)

    def group_exists(self,group):
        try:
            # Try group as a gid first
            grp.getgrgid(int(group))
            return True
        except (ValueError, KeyError):
            try:
                grp.getgrnam(group)
                return True
            except KeyError:
                return False

    def group_info(self, group):
        if not self.group_exists(group):
            return False
        try:
            # Try group as a gid first
            return list(grp.getgrgid(int(group)))
        except (ValueError, KeyError):
            return list(grp.getgrnam(group))

    def get_groups_set(self, remove_existing=True):
        if self.groups is None:
            return None
        info = self.user_info()
        groups = set(filter(None, self.groups.split(',')))
        for g in set(groups):
            if not self.group_exists(g):
                self.module.fail_json(msg="Group %s does not exist" % (g))
            if info and remove_existing and self.group_info(g)[2] == info[3]:
                groups.remove(g)
        return groups

    def user_group_membership(self):
        groups = []
        info = self.get_pwd_info()
        for group in grp.getgrall():
            if self.name in group.gr_mem and not info[3] == group.gr_gid:
                groups.append(group[0])
        return groups

    def user_exists(self):
        try:
            if pwd.getpwnam(self.name):
                return True
        except KeyError:
            return False

    def get_pwd_info(self):
        if not self.user_exists():
            return False
        return list(pwd.getpwnam(self.name))

    def user_info(self):
        if not self.user_exists():
            return False
        info = self.get_pwd_info()
        if len(info[1]) == 1 or len(info[1]) == 0:
            info[1] = self.user_password()
        return info

    def user_password(self):
        passwd = ''
        if HAVE_SPWD:
            try:
                passwd = spwd.getspnam(self.name)[1]
            except KeyError:
                return passwd
        if not self.user_exists():
            return passwd
        elif self.CLOUDCONFIG:
            # Read shadow file for user's encrypted password string
            if os.path.exists(self.CLOUDCONFIG) and os.access(self.CLOUDCONFIG, os.R_OK):
                for line in open(self.CLOUDCONFIG).readlines():
                    if line.startswith('%s:' % self.name):
                        passwd = line.split(':')[1]
        return passwd

    def create_user(self):
        # by default we use the create_user_useradd method
        return self.create_user_useradd()

    def remove_user(self):
        # by default we use the remove_user_userdel method
        return self.remove_user_userdel()

    def modify_user(self):
        # by default we use the modify_user_usermod method
        return self.modify_user_usermod()


# ===========================================

def main():
    module = AnsibleModule(
        argument_spec = dict(
            state=dict(default='present', choices=['present', 'absent'], type='str'),
            name=dict(required=True, aliases=['user'], type='str'),
            groups=dict(default=None, type='str'),
            password=dict(default=None, type='str'),
            # following are specific to ssh key generation
            ssh_authorized_keys=dict(aliases=['sshkeys'], default=None, type='str'),
            update_password=dict(default='always',choices=['always','on_create'],type='str'),
        ),
        supports_check_mode=True
    )

    user = CloudConfig_User(module)

    if user.syslogging:
        syslog.openlog('ansible-%s' % os.path.basename(__file__))
        syslog.syslog(syslog.LOG_NOTICE, 'User instantiated - platform %s' % user.platform)
        if user.distribution:
            syslog.syslog(syslog.LOG_NOTICE, 'User instantiated - distribution %s' % user.distribution)

    rc = None
    out = ''
    err = ''
    result = {}
    result['name'] = user.name
    result['state'] = user.state
    if user.state == 'absent':
        if user.user_exists():
            if module.check_mode:
                module.exit_json(changed=True)
            (rc, out, err) = user.remove_user()
            if rc != 0:
                module.fail_json(name=user.name, msg=err, rc=rc)
            result['force'] = user.force
            result['remove'] = user.remove
    elif user.state == 'present':
        if not user.user_exists():
            if module.check_mode:
                module.exit_json(changed=True)
            (rc, out, err) = user.create_user()
        else:
            # modify user (note: this function is check mode aware)
            (rc, out, err) = user.modify_user()
        if rc is not None and rc != 0:
            module.fail_json(name=user.name, msg=err, rc=rc)
        if user.password is not None:
            result['password'] = 'NOT_LOGGING_PASSWORD'
        if user.ssh_authorized_keys is not None:
            result['ssh_authorized_keys'] = 'NOT_LOGGING_KEY'

    if rc is None:
        result['changed'] = False
    else:
        result['changed'] = True
    if out:
        result['stdout'] = out
    if err:
        result['stderr'] = err

    if user.user_exists():
        info = user.user_info()
        if info == False:
            result['msg'] = "failed to look up user name: %s" % user.name
            result['failed'] = True
        if user.groups is not None:
            result['groups'] = user.groups

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()
