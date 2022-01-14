#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

## ロガー用の設定ファイル

import logging
import logging.handlers
import pathlib
import re

# my環境変数
from . import getMyEnv

myLoggerName = 'days_renkei'
BASE_LOG_DIR = getMyEnv.ENV_LOG_DIR if getMyEnv.ENV_LOG_DIR != 'default' else '/var/log/daidai/renkei'
BASE_LOG_NAME = 'server.log'
BASE_LOG_FMT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
BASE_LOG_FMT_DBG = '[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s'
BASE_LOG_FMT_PLG = '[%(asctime)s] [%(levelname)s] %(message)s'
BASE_LOG_FMT_PLG_DBG = '[%(asctime)s] [%(levelname)s] [%(funcName)s:%(lineno)d] %(message)s'
BASE_LOG_INTERVAL = 1
BASE_LOG_BACKUPCOUNT = 90

logger = logging.getLogger(myLoggerName)

# 変数に再格納
development = getMyEnv.cmn.envMode['development']
prototype = getMyEnv.cmn.envMode['prototype']
production = getMyEnv.cmn.envMode['production']
mode_gmail = getMyEnv.cmn.mode_gmail

def setBaseLogger():
	logger = logging.getLogger(myLoggerName)

	logName = BASE_LOG_NAME
	if getMyEnv.ENV_DB_CODE is not None and len(getMyEnv.ENV_DB_CODE) > 0:
		nameSplit = BASE_LOG_NAME.split('.')
		logName = nameSplit[0] + '_' + getMyEnv.ENV_DB_CODE + '.' + nameSplit[1]

	logFileHandlerBase = logging.handlers.TimedRotatingFileHandler(
				filename = pathlib.Path(BASE_LOG_DIR).joinpath(logName),
				when = 'midnight',
				interval = BASE_LOG_INTERVAL,
				backupCount = BASE_LOG_BACKUPCOUNT,
				encoding = 'UTF-8',
			)

	if getMyEnv.ENV_MODE == production or getMyEnv.ENV_MODE == prototype:
		logger.setLevel(logging.INFO)
		logFileHandlerBase.setLevel(logging.INFO)
		logFileHandlerBase.setFormatter(logging.Formatter(BASE_LOG_FMT))

		# ログレベルCRITICALのメール送信用
		if getMyEnv.ENV_SEND_MAIL_MODE == mode_gmail:
			logMailHandler = logging.handlers.SMTPHandler(
				mailhost = ('smtp.gmail.com', 587),
				fromaddr = 'bit.days.systeminfo@gmail.com',
				toaddrs = 'y.kadena@systembit.co.jp',
				subject = '[days-renkei-test] renkei server critical error',
				# G-Mailの2段階認証を有効にして、アプリパスワードというのを発行し、それを使用する
				credentials = ('bit.days.systeminfo@gmail.com','nkcyjpdfjctkaizk'),
				secure = ()
			)
			logMailHandler.setLevel(logging.CRITICAL)
			logger.addHandler(logMailHandler)

	else:
		logger.setLevel(logging.DEBUG)
		logFileHandlerBase.setLevel(logging.DEBUG)
		logFileHandlerBase.setFormatter(logging.Formatter(BASE_LOG_FMT_DBG))

	logger.addHandler(logFileHandlerBase)


def setPlgLogger(plgPathName):
	plgLogger = logging.getLogger(plgPathName)
	# ハンドラが1個いたら登録済み扱いとし、何もしない
	#if len(plgLogger.handlers) > 0 and plgLogger.level > 0:
	#	return
	logName = 'plg.log'
	plgName = plgPathName.split('.')[1]
	sidMorg = plgPathName.split('.')[2]
	logPath = pathlib.Path(BASE_LOG_DIR).joinpath(sidMorg, plgName, logName)

	# プラグイン用ログディレクトリ作成
	try:
		pathlib.Path(logPath.parent).mkdir(parents=True, exist_ok=True)
	except Exception as err:
		logger.error(err)

	logFileHandlerPlg = logging.handlers.TimedRotatingFileHandler(
				filename = logPath,
				when = 'midnight',
				interval = BASE_LOG_INTERVAL,
				backupCount = BASE_LOG_BACKUPCOUNT,
				encoding = 'UTF-8',
			)

	if getMyEnv.ENV_MODE == production or getMyEnv.ENV_MODE == prototype:
		plgLogger.setLevel(logging.INFO)
		logFileHandlerPlg.setLevel(logging.INFO)
		logFileHandlerPlg.setFormatter(logging.Formatter(BASE_LOG_FMT_PLG))
	else:
		plgLogger.setLevel(logging.DEBUG)
		logFileHandlerPlg.setLevel(logging.DEBUG)
		logFileHandlerPlg.setFormatter(logging.Formatter(BASE_LOG_FMT_PLG_DBG))

	plgLogger.addHandler(logFileHandlerPlg)

	# ログ出力
	plgLogger.info('setup logger: {}'.format(logPath))

	return


# ワーカーjobのロガー設定
def setJobLogger(jobName):
	jobLogger = logging.getLogger(jobName)
	logFormat = BASE_LOG_FMT_DBG
	logExecInfoFlag = True

	logDir = pathlib.Path(BASE_LOG_DIR)
	logNameBase = jobName.split('.')[1]
	logDir = logDir.joinpath(logNameBase)
	logSuffix = '.log'

	logName = logNameBase
	if getMyEnv.ENV_DB_CODE is not None and len(getMyEnv.ENV_DB_CODE) > 0:
		logName += '_' + str(getMyEnv.ENV_DB_CODE)
	else:
		logName = logNameBase
	logName += logSuffix

	logPath = logDir.joinpath(logName)

	if logPath.parent.is_dir() is False:
		logPath.parent.mkdir(parents=True, exist_ok=True)

	logFileHandlerJob = logging.handlers.RotatingFileHandler(
		filename=logPath,
		mode='a',
		# 1M
		maxBytes = 5 * 1024 * 1024,
		# トータルで約600M分まで保持する予定。ファイル個数が規定数を超える場合は古いものから随時削除される（ディスク枯渇対策）
		backupCount = 100,
		encoding = 'UTF-8',
	)

	logLevel = logging.DEBUG
	if getMyEnv.ENV_MODE == production:
		logLevel = logging.INFO
		logFormat = BASE_LOG_FMT

	logFileHandlerJob.setFormatter(logging.Formatter(logFormat))

	jobLogger.setLevel(logLevel)
	jobLogger.addHandler(logFileHandlerJob)

	return jobLogger
