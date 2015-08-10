#!/bin/bash

# setup environment
cd /ansible && source ./hacking/env-setup && cd ~-

if [ $TERM = "xterm" ];
then
  /bin/bash
fi
