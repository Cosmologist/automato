#!/bin/bash
echo "Defaults timestamp_timeout=240" | sudo tee /etc/sudoers.d/sudo_timeout
sudo chmod 0440 /etc/sudoers.d/sudo_timeout
