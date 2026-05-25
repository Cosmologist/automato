#!/bin/bash

# remove installed snap-apps
for snap in $(snap list | awk 'NR>1 {print $1}' | grep -v snapd); do
    sudo snap remove "$snap"
done

sudo apt purge snapd

sudo rm -rf /snap /var/snap /var/lib/snapd /home/*/snap