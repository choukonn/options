#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import re
from collections import defaultdict


# 有効な医療機関番号のチェック用変数
enableSidMorgList = []

success = 0
warning = 1
error = 2

# モード指定用
plgUnit = 1
morgUnit = 2

envMode = {
	'development': 1,
	'prototype': 2,
	'production': 3,
}

# メール送信用
mode_gmail = 1

flagThreadLoop = True
baseConf = {}
# local_config.jsonのデータを格納
localConf = {}

# スレッド間のファイルやりとりで使用するキュー
pQueue = {}
# ファイル検索用スレッドでのキュー作成完了フラグ
fileSearchWorkThreadFlag = None
# プラグインとは別のワーカースレッド情報格納用
jobWokerThread = {}

# myapp
from . import mycfg
from . import my_file as modFile
from . import my_sql as modSql

# ランダムウェイト
def delayRandom(sec=None):
	from time import sleep
	from random import randrange
	if sec is None: sec = 10
	if sec == 0: return
	sleep(randrange(sec))


def plgConfigGet():
	from renkei_tools_py import plgConfig as pconf
	pconf._config.plgPathList = defaultdict(lambda: defaultdict(set))
	pconf._config.plgTargetSuffixPath = defaultdict(lambda: defaultdict(set))
	pconf._config.sidMorgPlgList = defaultdict(list)
	# TODO: システムディレクトリは拒否しておく？
	dropList = re.compile(r'^/$|^/bin/?|^/boot/?|^/dev/?|^/etc/?|^/lib/?|^/lib64/?|^/lost\+found/?|^/proc/?|^/sbin/?|^/sys/?|^/usr/?')

	# プラグインコンフィグの多次元配列を差し替えている・・・
	# FIXME: 入出力ディレクトリのチェック処理とかぶって冗長になってる。そのうち元気があれば修正
	if localConf is not None and 'plgConfig' in localConf and localConf['plgConfig'] is not None and len(localConf['plgConfig']) > 0:
		for pName, key1 in localConf['plgConfig'].items():
			for keyItem, keyValue in key1.items():
				for sidMorg, value in keyValue.items():
					if pName not in pconf._config.plg: continue
					elif keyItem not in pconf._config.plg[pName]: continue

					# 医療機関固有がないだけなら単純に突っ込む
					if sidMorg not in pconf._config.plg[pName][keyItem]:
						pconf._config.plg[pName][keyItem][sidMorg] = value
					# dict型ならマージ
					else:
						if type(pconf._config.plg[pName][keyItem][sidMorg]) == dict:
							pconf._config.plg[pName][keyItem][sidMorg].update(value)
						elif type(pconf._config.plg[pName][keyItem][sidMorg]) == str:
							pconf._config.plg[pName][keyItem][sidMorg] = value
						elif type(pconf._config.plg[pName][keyItem][sidMorg]) == list:
							pconf._config.plg[pName][keyItem][sidMorg] = value


	def inputDirCheck(item):
		if 'in' not in item: return item
		tmpSp = item['in'].split(',')
		if len(tmpSp) > 1:
			item['in'] = ','.join([_k.replace('\t', '').strip() for _k in tmpSp if _k is not None and len(_k) > 0]).strip(',')
		return item

	# TODO: inディレクトリ定義の解析（パース）＆ローカルコンフィグ内に定義されていたら上書き
	def analyzeDir(plgName, sidMorg, item):
		try:
			retItem = inputDirCheck(item)
			if plgName is None or sidMorg is None or item is None or len(item) < 1:
				return retItem
			# ローカルコンフィグのチェック
			if localConf is None or len(localConf) < 1:
				return retItem
			# ローカルコンフィグにプラグインの入出力ディレクトリ設定があるかチェック
			elif 'plgConfig' not in localConf or localConf['plgConfig'] is None or plgName not in localConf['plgConfig']:
				return retItem
		except:
			raise

		try:
			tmpItem = item
			if 'path' in localConf['plgConfig'][plgName]:
				if sidMorg in localConf['plgConfig'][plgName]['path']:
					for key in localConf['plgConfig'][plgName]['path'][sidMorg]:
						if key in tmpItem:
							tmpItem[key] = localConf['plgConfig'][plgName]['path'][sidMorg][key]

			tmpItem = inputDirCheck(tmpItem)

		except:
			raise

		return tmpItem


	def get():
		# プラグインが有効な医療機関番号
		pconf._config.plgUseSidMorg = {k:pconf._config.plg[k]['useMorg'] for k in pconf._config.plg}
		# 医療機関単位のプラグインリスト
		{pconf._config.sidMorgPlgList[k2].append(k1) for k1 in pconf._config.plgUseSidMorg for k2 in pconf._config.plgUseSidMorg[k1]}

		# PATHリスト
		try:
			for k1, v1 in pconf._config.plgUseSidMorg.items():
				for k2 in v1:
					tmp = None
					# PATHリスト
					if k2 in pconf._config.plg[k1]['path'].keys():
						tmp = pconf._config.plg[k1]['path'][k2]
					else:
						tmp = pconf._config.plg[k1]['path']['default']

					tmp = analyzeDir(k1, k2, tmp)

					pconf._config.plgPathList[k1][k2] = tmp

					# 入力ディレクトリ
					# 複数指定されていた場合をふんわりな感じで考慮。ディレクトリ名にカンマが使用されていたらアウト
					pconf._config.plgTargetSuffixPath[k1][k2] = ','.join([k.strip() + '/*' for k in pconf._config.plgPathList[k1][k2]['in'].replace('\t','').split(',') if len(k) > 0 and dropList.match(k) is None])

		except Exception as err:
			logger.error(err)

		return pconf._config

	config = get()

	return config


