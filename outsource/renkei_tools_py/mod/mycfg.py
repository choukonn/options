#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import pathlib

# myapp
from . import common as cmn

# 自身のファイル起点にしてTOPを指定
myCurDir = pathlib.Path(__file__).parent.resolve().joinpath('../')

# mainで環境変数を参照して決定（デフォルトは医療機関＋プラグイン単位）
THREAD_MODE = None

conf = {
	# CPUアフィニティ(True | False)
	'affinityUse': True,
	'affinityNum': [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,],
	# DB更新時のシステムユーザSID
	'systemUserSid': '0',
	'name': 'サーバ本体',
	'basePath': '/mnt/DD-ISC',
	# スレッドを立ち上げる単位 (plgUnit:プラグイン単位 | morgUnit:医療機関単位)
	'threadUnitType': THREAD_MODE,
	# 各ワーカーのメインsleep時間(数値：sec)
	'workersDelay': 5,
	# 起動モード（本番／ST／開発）# これは初期値
	'envMode': 'development',
	# DB設定（起動時に環境変数を見て選択する）
	'db': {
		# デフォルト
		'timeOut': 120,
		'development':{'url': 'mysql://ddadmin:1anNw7j$@localhost:3306/dd_data'},
		# 開発系じゃない場合、クラウド本番のhost名を指定
		'default':{'url': 'mysql://ddadmin:1anNw7j$@bs-dd-dbs:3306/dd_data'},
		# オンプレ
		'20051':{'url': 'mysql://ddadmin:z5er#RdDz#@localhost:3306/dd_data'},
		'20052':{'url': 'mysql://ddadmin:z5er#RdDz#@localhost:3306/dd_data'},
		'90005':{'url': 'mysql://ddadmin:)P&#dnVch2?09txO@localhost:3306/dd_data'},
		'90006':{'url': 'mysql://ddadmin:z$9CR1#a@hcs-dbs:3306/dd_data'},
		'90007':{'url': 'mysql://ddadmin:j7V_Ldm2@hcs-dbs:3306/dd_data'},
	},
	'mlgdb':{
		'timeOut': 120,
		'development':{'url': 'mysql://testUser:testPass@localhost:3306/mlg_data'},
		'default':{'url': 'mysql://mlgadmin:Hd7J#T4a@localhost:3306/mlg_data'},
		# オンプレ
		'20051':{'url': 'mysql://mlgadmin:Hd7J#T4a@localhost:3306/mlg_data'},
		'20052':{'url': 'mysql://mlgadmin:Hd7J#T4a@localhost:3306/mlg_data'},
		'90005':{'url': 'mysql://mlgadmin:Hd7J#T4a@localhost:3306/mlg_data'},
		'90006':{'url': 'mysql://mlgadmin:y$8DS1#b@hcs-dbs:3306/mlg_data'},
		'90007':{'url': 'mysql://mlgadmin:j9Y_nfo4@hcs-dbs:3306/mlg_data'},
	},
	# XMLテンプレ
	'templateXML': {
		'ccard': {
			'1': str(myCurDir.joinpath('template', 'template_ccard_1.xml')),
		},
		'examinee': {
			'1' : str(myCurDir.joinpath('template', 'template_examinee_1.xml')),
		},
		'org': {
			'1' : str(myCurDir.joinpath('template', 'template_org_1.xml')),
			'2' : str(myCurDir.joinpath('template', 'template_xinorg_1.xml')),
		},
		'extOrder': {
			'1' : str(myCurDir.joinpath('template', 'template_extOrder_1.xml')),
		},
		'pkOrder': {
			# オーダー連携データ作成用テンプレ
			'1' : str(myCurDir.joinpath('template', 'template_pkOrderinfo_1.xml')),
			# 受診者メモ連携データ作成用テンプレ
			'2' : str(myCurDir.joinpath('template', 'template_pkOrderExamLink_1.xml')),
		},
		'appoint': {
			'1' : str(myCurDir.joinpath('template', 'template_appoint_1.xml')),
		},
		'extLink': {
			'1' : str(myCurDir.joinpath('template', 'template_externalLinkage_1.xml')),
		},
	}
}


# 使用するDBを指定
def setDbConfig(dbCode, envMode):
	import urllib.parse
	global conf
	db = {}
	mlg = {}

	def setDB(dbconf):
		dbConfig = {}
		# 特殊文字を%xx形式にエスケープ（safeで指定した文字は対象外、文字、数字、および '_.-' も対象外）
		url = urllib.parse.quote(dbconf['url'], safe=':@/')
		# 分解
		url = urllib.parse.urlparse(url, scheme='mysql', allow_fragments=False)
		dbConfig['host'] = url.hostname
		dbConfig['port'] = url.port
		dbConfig['dbName'] = url.path[1:]
		# エスケープしていた文字を戻す
		dbConfig['user'] = urllib.parse.unquote(url.username)
		dbConfig['pass'] = urllib.parse.unquote(url.password)
		return dbConfig

	# 開発環境
	if envMode in [cmn.envMode['prototype'], cmn.envMode['development']]:
		db = setDB(conf['db']['development'])
		mlg = setDB(conf['mlgdb']['development'])
		# 例）国内：dd_data_jp
		if dbCode == 'default':
			dbSuffix = '_jp'
		# 例）オンプレ：dd_data_90005
		else:
			dbSuffix = '_' + dbCode
		db['dbName'] = db['dbName'] + dbSuffix
		#mlg['dbName'] = mlg['dbName'] + dbSuffix
	# 開発環境ではない
	elif dbCode in conf['db'] and conf['db'][dbCode] is not None:
		db = setDB(conf['db'][dbCode])
		mlg = setDB(conf['mlgdb'][dbCode])
	else:
		raise Exception('db setting faild, dbCode:{}'.format(dbCode))

	# ローカルコンフィグで上書き
	if cmn.localConf is not None and len(cmn.localConf) > 0:
		for key in cmn.localConf.keys():
			if key in cmn.localConf and len(cmn.localConf[key]) > 0:
				# 単純マージ
				if key == "db":
					if dbCode in cmn.localConf[key]:
						db = setDB(cmn.localConf[key][dbCode])
					if 'timeOut' in cmn.localConf[key]:
						conf[key]['timeOut'] = cmn.localConf[key]['timeOut']
				elif key == "mlgdb" and dbCode in cmn.localConf[key]:
					if dbCode in cmn.localConf[key]:
						mlg = setDB(cmn.localConf[key][dbCode])
					if 'timeOut' in cmn.localConf[key]:
						conf[key]['timeOut'] = cmn.localConf[key]['timeOut']

	db['timeOut'] = conf['db']['timeOut']
	mlg['timeOut'] = conf['mlgdb']['timeOut']

	# 起動モードを文字列で入れる（TODO: 目視でわかるほうがよい？）
	#conf['envMode'] = [k for k, v in cmn.envMode.items() if v == envMode][0]
	conf['useDBconf'] = db
	conf['useMLGconf'] = mlg
	logger.info('use DataBase config, host: {}, port: {}, dbName: {}'.format(conf['useDBconf']['host'], conf['useDBconf']['port'], conf['useDBconf']['dbName']))

	return
