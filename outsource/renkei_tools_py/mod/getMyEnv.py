#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

import os
import sys

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from . import common as cmn

# 環境変数取得してごにょ
ENV_MODE = os.getenv('ENV_DAI_RENKEI_MODE', 'development')
if ENV_MODE in cmn.envMode:
	ENV_MODE = cmn.envMode[ENV_MODE]
else:
	logger.error('unknwon ENV_DAI_RENKEI_MODE: {}'.format(ENV_MODE))
	sys.exit(1)


# ログディレクトリ
# 環境変数で指定する場合、フルPATHを記述すること
ENV_LOG_DIR = os.getenv('ENV_DAI_RENKEI_LOG_DIR', 'default')

# 入出力ディレクトリ
# 環境変数で指定する場合、フルPATHを記述すること
ENV_BASE_DIR = os.getenv('ENV_DAI_RENKEI_BASE_DIR', 'default')


# CPUアフィニティの設定
ENV_CPU_AFFINITY_GET = os.getenv('ENV_DAI_CPU_AFFINITY', 'default')
if ENV_CPU_AFFINITY_GET == 'default':
	ENV_CPU_AFFINITY = None
else:
	check = ENV_CPU_AFFINITY_GET.split(',')
	ENV_CPU_AFFINITY = [int(k) for k in check if k.isdecimal() and 0 <= int(k) < 255]


# DBコード
# 20051
# 20052
# 90005
# 90006
ENV_DB_CODE = os.getenv('ENV_DAI_RENKEI_DB_CODE', 'default')

# ログレベルCRITICAL発生時にメールを送信するかしないか
ENV_SEND_MAIL_MODE = os.getenv('ENV_DAI_RENKEI_MAIL_MODE', 0)
#（中国はgmail不可なのでON(1)にしても意味なし）
if ENV_SEND_MAIL_MODE == 1:
	ENV_SEND_MAIL_MODE = cmn.mode_gmail
