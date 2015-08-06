ansible-cloudconfig
===================


- Follow ```http://docs.ansible.com/ansible/developing_modules.html``` in a nutshell you need to:

```
git clone git@github.com:ansible/ansible.git --recursive
source ansible/hacking/env-setup
chmod +x ansible/hacking/test-module
```

- Add these two lines to your ```~/.bash_profile``` or ```~/.zshrc```

```
ansible-dev-init='cd ~/gitroot/ansible && source ./hacking/env-setup && cd ~-'
ansible-test-module='~/gitroot/ansible/hacking/test-module'

```

- Source your config and setup your dev environment

```

. ~/.zshrc && ansible-dev-init

```

- Edit your the module and test with (from your module source folder):

```

ansible-test-module -m ./cloudconfig_user.py 

```
