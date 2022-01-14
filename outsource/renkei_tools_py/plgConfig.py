#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

from renkei_tools_py.analysisFile import modeAppoint, modeExam

class _Container():
	pass

try:
	_config = _Container()
	_config.plg = {
		'p010': {	# TODO: プログラム内部で使用するプラグイン名、ソースファイルがいるディレクトリ名を指定すること
			'name': '受診者インポート（国内標準仕様に近しいもの）',
			'useMorg': [
				'4',			# TODO: [ビットクリニック] 本店 テスト用
				'6',			# TODO: [ビットクリニック] 2号店 テスト用
				'20073',		# [国内クラウド] つげの木海老名健診センター
				],
			'path': {
				'default': {'in':'p010/in', 'out':'p010/out','done':'p010/done','err':'p010/err'},
				'4': {'in':'p010/in', 'out':'p010/out','done':'p010/done','err':'p010/err'},
			},
			'suffix': {
				'default' : ['.csv'],
			},
			'encoding': 'cp932',
			# 1:move, それ以外:delete
			'procEndFile': '1',
		},
		'p020': {
			'name': '一括結果インポート',
			'useMorg': [
				'4',			# TODO: [ビットクリニック] 本店 テスト用
				'6',			# TODO: [ビットクリニック] 2号店 テスト用
				'20051',		# TODO: [HECI] テスト用
				'90005', 		# [オンプレ] 四川
				],
			'path': {
				'default': {'in':'p020/in', 'out':'p020/out','done':'p020/done','err':'p020/err'},
				'4': {'in':'200/in', 'out':'200/out','done':'200/done','err':'200/err'},
			},
			'suffix': {
				'default' : ['.csv'],
			},
			# ファイル名の厳密チェックを行いたい場合は、正規表現を使用可能
			'fileName': {
				'90005' : r'^[Rr][Ee][Ss].+\.[cC][sS][vV]$',
			},
			'givupFileName': {
				'default': 'file_giving_up_on_re_import_'
			},
			'encoding': 'UTF-8',
			# 1:move, それ以外:delete
			'procEndFile': '1',
		},
		'p021': {	# 流用元はp020の一括結果インポート
			'name': '受診者／予約インポート',
			'useMorg': [
				'4',			# TODO: [ビットクリニック] 本店 テスト用
				'6',			# TODO: [ビットクリニック] 2号店 テスト用
				'20073',		# [国内クラウド] つげの木
				'20051', 		# TODO: [HECI] テスト用
				'90006',		# [オンプレ] ハノイ - ビンメック
				'90007',		# [オンプレ] 国際医療福祉大学 成田病院
				],
			'path': {
				'default': {'in':'p021/in', 'out':'p021/out', 'work':'p021/work', 'done':'p021/done','err':'p021/err'},
				'4': {'in':'p021/in', 'out':'p021/out', 'work':'p021/work', 'done':'p021/done','err':'p021/err'},
			},
			'triggerFile': {
				'90006': {
					'fileName' : 'trigger.txt',
					'waitTime': 5,
				},
			},
			'suffix': {
				'default' : ['.csv'],
			},
			# 予約／属性処理モード初期値
			'defaultProcMode' : {
				'default' : modeAppoint,
			},
			# 解析対象とするインポートファイル
			'analysisFileType': {
				'90006': '.json',
				'90007': '.json',
			},
			# ファイル名の厳密チェックを行いたい場合は、正規表現を使用可能
			'fileName': {
				'90006' : r'^[a-zA-Z].+\.[jJ][sS][oO][nN]$',
				'90007' : r'^[0-9a-zA-Z].+\.[jJ][sS][oO][nN]$',
			},
			# K+予約連携
			'useKpAppointLink': [
				'4',
				'6',
				'90006',
				'90007',
			],
			'encoding': 'UTF-8',
			# 1:move, それ以外:delete
			'procEndFile': '1',
		},
		'p030': {
			'name': 'ラボ結果インポート',
			'useMorg': [
				'90006',		# [ビンメック]
				],
			'path': {
				'default': {'in':'p030/in','out':'p030/out','done':'p030/done','err':'p030/err'},
				'90006': {'in':'p030/in','out':'p030/out','done':'p030/done','err':'p030/err'},
			},
			'triggerFile': {
				'90006': {
					'fileName' : 'trigger.txt',
					'waitTime': 5,
				},
			},
			'suffix': '.json',
			# 解析対象とするインポートファイル
			'analysisFileType': {
				'90006': '.json',
			},
			# ファイル名の厳密チェックを行いたい場合は、正規表現を使用可能
			'fileName': {
				'90006' : r'^[a-zA-Z].+\.[jJ][sS][oO][nN]$',
			},
			'encoding': 'UTF-8',
			# 1:move, 1以外:delete
			'procEndFile': '1',
		},
		'p040': {
			'name': 'レポート結果インポート',
			'useMorg': [
				'90006',		# [ビンメック]
				],
			'path': {
				'default': {'in':'p040/in','out':'p040/out','done':'p040/done','err':'p040/err'},
				'90006': {'in':'p040/in','out':'p040/out','done':'p040/done','err':'p040/err'},
			},
			'triggerFile': {
				'90006': {
					'fileName' : 'trigger.txt',
					'waitTime': 5,
				},
			},
			'suffix': '.json',
			# 解析対象とするインポートファイル
			'analysisFileType': {
				'90006': '.json',
			},
			# ファイル名の厳密チェックを行いたい場合は、正規表現を使用可能
			'fileName': {
				'90006' : r'^[a-zA-Z].+\.[jJ][sS][oO][nN]$',
			},
			'encoding': 'UTF-8',
			# 1:move, 1以外:delete
			'procEndFile': '1',
		},
		'p050': {
			'name': '問診結果インポート',
			'useMorg': [
				'90006',		# [ビンメック]
				],
			'path': {
				'default': {'in':'p050/in','out':'p050/out','done':'p050/done','err':'p050/err'},
				'90006': {'in':'p050/in','out':'p050/out','done':'p050/done','err':'p050/err'},
			},
			'triggerFile': {
				'90006': {
					'fileName' : 'trigger.txt',
					'waitTime': 5,
				},
			},
			'suffix': '.json',
			# 解析対象とするインポートファイル
			'analysisFileType': {
				'90006': '.json',
			},
			# ファイル名の厳密チェックを行いたい場合は、正規表現を使用可能
			'fileName': {
				'90006' : r'^[a-zA-Z].+\.[jJ][sS][oO][nN]$',
			},
			'encoding': 'UTF-8',
			# 1:move, 1以外:delete
			'procEndFile': '1',
		},
		'p060': {
			'name': 'K+オーダー連携',
			'useMorg': [
				'4',			# TODO: [ビットクリニック] 本店 テスト用
				'6',			# TODO: [ビットクリニック] 2号店 テスト用
				'20051',		# TODO: テスト用に追加（仮）
				'90006',		# [ビンメック] ハノイ
				'90007',		# [成田] 国際医療福祉大学
				],
			'path': {
				# 入力フォルダは、受診者メモ連携のためのjobファイルが置かれるディレクトリを指定
				'default': {'in':'11/out', 'out':'p060/out','work':'p060/work','done':'p060/done','err':'p060/err'},
				'4': {'in':'600/in', 'out':'600/out','done':'600/done','err':'600/err'},
				# samba経由でファイルの取得を行う場合
				'90006': {'in':'11/out', 'out':'p060/out','done':'p060/done','err':'p060/err', 'smb':'smb://hcs-was:445/90006/11/out&is_direct_tcp=True&domain=WORKGROUP&pattern=*.job'},
				'90007': {'in':'11/out', 'out':'/root/SB/DD_IN/converter/files/90007/daidai_progress_get/daidai_from','work':'p060/work','done':'p060/done','err':'p060/err'},
			},
			'pollingTime' : {
				'default' : 30,
			},
			'fileName': {
				'default' : r'^[0-9]{15}\.[jJ][oO][bB]$',
			},
			'encoding': 'UTF-8',
			'procEndFile': '1',
		},
		'p070': {
			'name': '電子カルテオーダー連携',
			'useMorg': [
				'90007',		# 成田病院
				],
			'path': {
				'default': {'in':'p070/in', 'out':'p070/out', 'work':'p070/work','done':'p070/done','err':'p070/err'},
				'4': {'in':'600/in', 'out':'600/out','done':'600/done','err':'600/err'},
				'90007': {'in':'p070/in', 'out':'/root/SB/DD_IN/converter/files/90007/hope_order_send/daidai_from', 'work':'p070/work','done':'p070/done','err':'p070/err'},
			},
			'pollingTime' : {
				'default' : 15,
			},
			'fileName': None,
			'encoding': 'shift_jis',
			'procEndFile': '1',
		},
		'p071': {
			'name': '受診者属性連携',
			'useMorg': [
				'90007',		# 成田病院
				],
			'path': {
				'default': {'in':'p071/in', 'out':'p071/out','done':'p071/done','err':'p071/err'},
				'4': {'in':'600/in', 'out':'600/out','done':'600/done','err':'600/err'},
				'90007': {'in':'/root/SB/DD_IN/converter/files/90007/hope_patient_get/daidai_to', 'out':'p071/out','done':'p071/done','err':'p070/err'},
			},
			'pollingTime' : {
				'default' : 5,
			},
			'fileName': {
				'90007' : r'^[0-9a-zA-Z].+\.[cC][sS][vV]$',
			},
			'sid_upd': {
				'90007' : 3,
			},
			'encoding': 'UTF-8',
			'procEndFile': '1',
		},
		'p080': {
			'name': '共通結果インポート（コンバータ経由のCSVレイアウト専用）',
			'useMorg': [
				'90007',		# [成田病院]
				],
			'path': {
				'default': {'in':'p080/in','out':'p080/out','done':'p080/done','err':'p080/err'},
				'90007': {
					'in':' \
						/root/SB/DD_IN/converter/files/90007/canon_bone_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/fujifilm_report_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/fukuda_physiological_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/fukuda_mbf1000_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/jmac_report_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/hope_lab_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/navis_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/philips_report_get/daidai_to, \
						',
					'out':'p080/out','done':'p080/done','err':'p080/err'},
			},
			'suffix': {
				'default' : ['.csv'],
			},
			# 解析対象とするインポートファイル
			'analysisFileType': {
				'90007': '.csv',
			},
			# ファイル名の厳密チェックを行いたい場合は、正規表現を使用可能
			'fileName': {
				'90007' : r'^[0-9a-zA-Z].+\.[cC][sS][vV]$',
			},
			'encoding': 'UTF-8',
			# 1:move, 1以外:delete
			'procEndFile': '1',
		},
		'p081': {
			'name': '問診取り込み（コンバータ経由のCSVレイアウト専用）',
			'useMorg': [
				'90007',		# [成田病院]
				],
			'path': {
				'default': {'in':'p081/in','out':'p081/out','done':'p081/done','err':'p081/err'},
				'90007': {
					'in':' \
						/root/SB/DD_IN/converter/files/90007/questionaire_get/daidai_to, \
						/root/SB/DD_IN/converter/files/90007/questionaire_minimun_get/daidai_to, \
						',
					'out':'p081/out','done':'p081/done','err':'p081/err'},
			},
			'suffix': {
				'default' : ['.csv'],
			},
			'pollingTime' : {
				'default' : 5,
			},
			# ファイル名の厳密チェックを行いたい場合は、正規表現を使用可能
			'fileName': {
				'default' : [{'priority': 1, 'reg': r'.+\.[cC][sS][vV]$'}],
				'90007' : [
					{'priority': 1, 'reg': r'^.+_questionaire_get_.*\.[cC][sS][vV]$'},
					{'priority': 2, 'reg': r'^.+_questionaire_minimun_get_.*\.[cC][sS][vV]$'},
					{'priority': 99, 'reg': r'.+\.[cC][sS][vV]$'},
				]
			},
			'encoding': 'UTF-8',
			# 1:move, 1以外:delete
			'procEndFile': '1',
		},
	}	# end


except Exception as err:
	logger.debug(err)
	raise
