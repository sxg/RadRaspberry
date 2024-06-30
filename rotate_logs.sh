#!/bin/bash

# 0 0 * * 0

LOG_DIR=/home/pennradiology/.local/state/rad_raspberry/log

rm ${LOG_DIR}/last_week/*.log
mv ${LOG_DIR}/*.log ${LOG_DIR}/last_week/
