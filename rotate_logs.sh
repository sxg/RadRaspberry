#!/bin/bash

# 0 0 1 * 0 every month

DIR=/home/pennradiology/.local/state/rad_raspberry
BACKUP_DIR=${DIR}/backup
LOG_DIR=${DIR}/log

mv ${BACKUP_DIR} ${BACKUP_DIR}-prior
mv ${LOG_DIR} ${LOG_DIR}-prior
mkdir ${BACKUP_DIR} ${LOG_DIR}
