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
    force:
        required: false
        default: false
        choices: [ true, false]
        description:
            - Force the update action to overwrite the entire user entry.
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

    template:
        required: false
        default: false
        choices: [ true, false ]
        description:
            - Use a golang template version of the cloud-init. 
              Requires a matching property binding.

    update_password:
        required: false
        default: "always"
        choices: [ always, on_create ]
        description:
            - Update a user with an existing password.
              By default, this B(will) overwrite an existing password

    validate:
        required: false
        default: true
        choices: [ true, false ]
        description:
            - Validate the generated cloudconfig and do not overwrite if failed.


'''

EXAMPLES = '''
# Add the user 'johnd' without password and groups of 'admin'
- user: name=johnd password="*" groups=admin

# Add the user 'james' with a bash shell, appending the group 'admins' and 'developers' to the user's groups
- user: name=james password="sdf$Kll..." groups=admins,developers update_password=yes

# Remove the user 'johnd'
- user: name=johnd state=absent

# Create user with SSH key for user jsmith
- user: name=jsmith sshkeys="ssh-rsa AAAAAA..... a@me.com", "ssh-rsa BBBBB..... b@me.com" state=present
'''

import os
import syslog
import platform
import socket
import time
import json

class CloudConfig_User(object):
    """
    This is a generic CloudConfig_User manipulation class. Normally it would be subclassed
    based on platform. However we are using a golang binary under the hood, so usage is consistent.
    Also note that this is specific to CoreOS-cloudinit at the moment.

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
        self.src                 = module.params['src']
        self.dest                = module.params['dest']
        self.name                = module.params['name']
        self.force               = module.params['force']
        self.groups              = module.params['groups']
        self.password            = module.params['password']
        self.ssh_authorized_keys = module.params['ssh_authorized_keys']
        self.template            = module.params['template']
        self.update_password     = module.params['update_password']
        self.validate            = module.params['validate']

        # select whether we dump additional debug info through syslog
        self.syslogging = False


    def execute_command(self, cmd, use_unsafe_shell=False, data=None):
        if self.syslogging:
            syslog.openlog('ansible-%s' % os.path.basename(__file__))
            syslog.syslog(syslog.LOG_NOTICE, 'Command %s' % '|'.join(cmd))

        return self.module.run_command(cmd, use_unsafe_shell=use_unsafe_shell, data=data)

    def remove_user_cloudconfig(self):
        cmd = [self.module.get_bin_path('cloudconfig', True)]

        cmd.append("users")
        cmd.append("-action")
        cmd.append("remove")
        
        if self.src is not None:
            cmd.append('-src')
            cmd.append(self.src)

        if self.dest is not None:
            cmd.append('-dest')
            cmd.append(self.dest)

        cmd.append(self.name)
        return self.execute_command(cmd)

    def create_user_cloudconfig(self, command_name='cloudconfig'):
        cmd = [self.module.get_bin_path(command_name, True)]

        cmd.append("users")
        cmd.append("-action")
        cmd.append("add")

        if self.src is not None:
            cmd.append('-src')
            cmd.append(self.src)

        if self.dest is not None:
            cmd.append('-dest')
            cmd.append(self.dest)

        if self.groups is not None and len(self.groups):
            cmd.append('-groups')
            cmd.append(self.groups)

        if self.update_password == 'always' and self.password is not None:
            cmd.append('-passwd')
            cmd.append(self.password)

        if self.ssh_authorized_keys is not None and len(self.ssh_authorized_keys):
            cmd.append('-ssh-authorized-keys')
            cmd.append(','.join(self.ssh_authorized_keys))

        if self.template:
            cmd.append('-template')

        if self.validate:
            cmd.append('-validate')

        cmd.append(self.name)
        return self.execute_command(cmd)

    def modify_user_cloudconfig(self):
        cmd = [self.module.get_bin_path('cloudconfig', True)]
        cmd.append('users')
        cmd.append('-action')
        cmd.append('update')

        info = self.user_info()

        if self.src is not None:
            cmd.append('-src')
            cmd.append(self.src)

        if self.dest is not None:
            cmd.append('-dest')
            cmd.append(self.dest)

        if self.force:
            cmd.append('-force')
            cmd.append(self.force)

        if self.groups is not None:
            cmd.append('-groups')
            cmd.append(self.groups)

        if self.password is not None:
            cmd.append('-passwd')
            cmd.append(self.password)

        if self.ssh_authorized_keys is not None:
            cmd.append('-ssh-authorized-keys')
            # keys = (os.linesep))
            # keys = "%s" % keys
            cmd.append(''.join(self.ssh_authorized_keys))

        if self.template:
            cmd.append('-template')

        if self.validate:
            cmd.append('-validate')

        cmd.append('-format')
        cmd.append('json')

        # skip if no changes to be made
        if len(cmd) == 4:
            return (None, '', '')
        elif self.module.check_mode:
            return (0, '', '')

        cmd.append(self.name)
        (rc,out,err) = self.execute_command(cmd)

        return (rc,out,err)

    def user_exists(self):
        try:
            cmd = [self.module.get_bin_path('cloudconfig', True)]
            cmd.append('users')
            cmd.append('-action')
            cmd.append('view')

            if self.src is not None:
                cmd.append('-src')
                cmd.append(self.src)

            if self.dest is not None:
                cmd.append('-dest')
                cmd.append(self.dest)

            if self.template:
                cmd.append('-template')

            cmd.append('-format')
            cmd.append('json')

            cmd.append(self.name)

            (rc,out,err) = self.execute_command(cmd)

            if rc == 0:
                return True
            else:
                return False
        except KeyError:
            return False

    def user_info(self):
        if not self.user_exists():
            return False

        cmd = [self.module.get_bin_path('cloudconfig', True)]
        cmd.append('users')
        cmd.append('-action')
        cmd.append('view')
        
        if self.src is not None:
            cmd.append('-src')
            cmd.append(self.src)

        if self.dest is not None:
            cmd.append('-dest')
            cmd.append(self.dest)

        if self.template:
            cmd.append('-template')

        cmd.append('-format')
        cmd.append("json")

        cmd.append(self.name)
        (rc,out,err) = self.execute_command(cmd)

        
        #nobody:x:65534:65534:nobody:/nonexistent:/bin/sh
        try:
            info = json.loads(out)
        except:
            self.module.fail_json(msg="Failed to parse cloudconfig output %s" % (out))
            return False

        return info

    def create_user(self):
        # by default we use the create_user_cloudconfig method
        return self.create_user_cloudconfig()

    def remove_user(self):
        # by default we use the remove_user_cloudconfig method
        return self.remove_user_cloudconfig()

    def modify_user(self):
        # by default we use the modify_user_cloudconfig method
        return self.modify_user_cloudconfig()


# ===========================================

def main():
    module = AnsibleModule(
        argument_spec = dict(
            state=dict(default='present', choices=['present', 'absent'], type='str'),
            name=dict(required=True, aliases=['user'], type='str'),
            force=dict(default=False, type='bool'),
            groups=dict(default=None, type='str'),
            src=dict(default="/etc/configdrive/cloud-config.yml", type='str'),
            dest=dict(default="/etc/configdrive/cloud-config.yml", type='str'),
            update_password=dict(default='always',choices=['always','on_create'],type='str'),
            password=dict(default=None, type='str'),
            ssh_authorized_keys=dict(aliases=['sshkeys'], default=None, type='str'),
            template=dict(default=False, type='bool'),
            validate=dict(default=True, type='bool')
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
            if rc == 0 and re.match("not found, exiting", out) is not None:
                result['changed'] = False    
            elif rc == 0 and re.match("not found, exiting", out) is None:
                result['changed'] = True    
            
            result['force'] = user.force
    elif user.state == 'present':
        if not user.user_exists():
            if module.check_mode:
                module.exit_json(changed=True)
            (rc, out, err) = user.create_user()
            if rc == 0 and re.match("found, exiting", out) is not None:
                result['changed'] = False
            elif rc == 0 and re.match("found, exiting", out) is None:
                result['changed'] = True

        else:
            # modify user (note: this function is check mode aware)
            if module.check_mode:
                module.exit_json(changed=True)
            (rc, out, err) = user.modify_user()

            if rc == 0 and re.match("ignoring user",out) is not None:
                result['changed'] = False
            elif rc == 0 and re.match("updating user",out) is not None:
                result['changed'] = True

        # if rc is not None and rc != 0:
        #     module.fail_json(name=user.name, msg=err, rc=rc)

        # obscure some stuff from the log
        if user.password is not None:
            result['password'] = 'NOT_LOGGING_PASSWORD'
        if user.ssh_authorized_keys is not None:
            result['ssh_authorized_keys'] = 'NOT_LOGGING_SSH_KEYS'

    if rc is None:
        result['changed'] = False
    
    if rc > 0:
        result['changed'] = False

    if out:
        result['stdout'] = out
    if err:
        result['stderr'] = err

    if user.user_exists():
        info = user.user_info()
        if info == False:
            result['msg'] = "failed to look up user name: %s" % user.name
            result['failed'] = True

        groups = info['Message']['Groups']
        if groups is not None:
            result['groups'] = groups

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()