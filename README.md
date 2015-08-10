ansible-cloudconfig
===================

This module is built around cloudconfig: https://github.com/johnt337/cloudconfig



The ansible-galaxy role is currently to install the module on your ansible management host
as well as the cloudconfig utility on each of your coreos instances that your ansible host is managing.


Since its really only parsing and updating yaml with some file writing and validation, 
it probably warrants a full rewrite in python in order to avoid installing
on each host.


In either case, this is repurposed version of the ansible-core users module which is
built around ```useradd```, ```userdel```, ```usermod```, and it's ```group...``` counterpart commands.
Those have all been removed and replaced with cloudinit counterparts with calls to ```cloudconfig users -action ...```.



Install
-------

```
  $ ansible-galaxy install johnt337.cloudconfig

  (add 'library = <yourpath>:/usr/local/etc/ansible/roles/johnt337.cloudconfig/files' to your ansible.cfg)
  (or use '--module-path=<yourpath>:/usr/local/etc/ansible/roles/johnt337.cloudconfig/files')
  (or set '$ANSIBLE_MODULE_PATH=<yourpath>:/usr/local/etc/ansible/roles/johnt337.cloudconfig/files')
```

- change to the cloudconfig coreos installer folder)

```
  $ cd /usr/local/etc/ansible/roles/johnt337.cloudconfig
```

- edit install inventory to point to your coreos instances

```
  $ vi install
```

- run the cloudconfig installer (this will also install the module into /usr/local/etc/ansible/library locally)
```
  $ ansible-playbook -i install install.yml


```

- as an alternative, include the role in your play

```
hosts: coreos
roles:
  - { role: "johnt337.cloudconfig", tags: ['cloudconfig'] }
```

Usage
-----

- Sample Task in Role

```
- name: update user passwd in cloud-config
  cloudconfig_user: name='{{ item.admin }}' password='{{item.password}}' ssh_authorized_keys='{{item.ssh_key}}' groups='docker,sudo,wheel' dest='/tmp/cloud-config.yml' state='{{ item.state }}'
  with_items: users
  when: ansible_os_family == "NA" and ansible_lsb.id == "CoreOS"
  environment:
    PATH: /home/core/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/bin
  tags: ['cloudinit']
  sudo: True
```


Uninstall
---------

```
  $ cd /usr/local/etc/ansible/roles/johnt337.cloudconfig
```

- edit install to point to your coreos instances

```
  $ ansible-playbook -i install install.yml -e uninstall=true
  $ ansible-galaxy remove johnt337.cloudconfig
```

Hacking
-------
- Follow ```http://docs.ansible.com/ansible/developing_modules.html``` in a nutshell you need to:

```
git clone git@github.com:ansible/ansible.git --recursive
source ansible/hacking/env-setup
chmod +x ansible/hacking/test-module
```

- Add these two lines to your ```~/.bash_profile``` or ```~/.zshrc```

```
alias ansible-dev-init='cd ~/gitroot/ansible && source ./hacking/env-setup && cd ~-'
alias ansible-test-module='~/gitroot/ansible/hacking/test-module'

```

- Source your config and setup your dev environment

```

. ~/.zshrc && ansible-dev-init

```

- Edit your the module and test with (from your module source folder):

```

ansible-test-module -m ./files/library/cloudconfig_user.py -a "name=test password=foobar groups=johnt,test,one ssh_authorized_keys=barfoo"

```

- As an alterative, you can run ```make build-ansible/cloudconfig && make interactive```. From within the container run ```. ansible.profile```
