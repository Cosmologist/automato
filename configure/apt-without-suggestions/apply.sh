#!/bin/bash
printf 'APT::Install-Recommends "0";\nAPT::Install-Suggests "0";\n' | sudo tee /etc/apt/apt.conf.d/999norecommend