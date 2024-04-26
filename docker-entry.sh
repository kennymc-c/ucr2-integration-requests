#!/bin/bash

pip install --no-cache-dir -q -r /usr/src/app/requirements.txt
cd /usr/src/app/intg-requests
python driver.py