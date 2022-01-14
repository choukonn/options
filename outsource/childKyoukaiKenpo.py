#!/usr/bin/python3

# -*- coding: utf-8 -*-
# 文字コードはUTF-8で
# ネストが深いので４タブね。
# vim: ts=4 sts=4 sw=4

# 協会けんぽ（生活習慣予防／事業者健診）のCSV出力
# 生活習慣予防と事業者健診はm_outsourceのXMLにパラメータを持たせて振り分ける
# ベースのm_outsourceはsid_morg=0に作成
# 検査法等の医療機関個別情報は今まで通り

# 以下のツールに合わせて作成
# 協会けんぽツールはv3.11
# 事業者健診ツールはv7

#import os
import sys
import signal
import tempfile
import xml.etree.ElementTree as ET
import csv
import datetime
import pathlib as pl
import collections
from operator import itemgetter, attrgetter
import re
import time
import codecs

# https://github.com/ikegami-yukino/jaconv/blob/master/README_JP.rst
import jaconv

import form_tools_py.conf as conf
import form_tools_py.common as cmn
import form_tools_py.read_i18n_translation as ri18n
import form_tools_py.getXmlSid as getXmlSid
import form_tools_py.m_criterion as m_criterion
import form_tools_py.m_me as m_me
import form_tools_py.getXmlSid_kk as kk
import kyoukaikenpo_shikakusya_list
import unicodedata

# signalハンドラの登録(CTRL+Cとkill)
signal.signal(signal.SIGINT, cmn.handler_exit)
signal.signal(signal.SIGTERM, cmn.handler_exit)

# コンフィグ
config_data = {}

# 協会けんぽ用
csvHeaderItemDict = {}
csvDataItemDict = {}
# 受診項目のsid一覧を格納するもの
jyushinEitemList = {}

################################################################################
msg2js = cmn.Log().msg2js
log = cmn.Log().log
dbg_log = cmn.Log().dbg_log
sql = cmn.Sql()
zen2han = cmn.Zenkaku2Hankaku().zen2han

# 変数も参照したいよね
abst_code = conf.abst_code
sort_code = conf.sort_code
form_code = conf.form_code
m_section = conf.m_section

LOG_NOTICE = conf.LOG_NOTICE
LOG_INFO = conf.LOG_INFO
LOG_WARN = conf.LOG_WARN
LOG_ERR = conf.LOG_ERR
LOG_DBG = conf.LOG_DBG

# 出力データが定性値／数字の識別を行う必要がある
valueDataType = {
	# 定性値
	'qualitativeVal': 0,
	# 数字
	'numberVal': 2,
	# 定性値もしくは数字
	'both': 1,
}
# 定性値コード表
qualitativeCode = {
	'-':	'1',
	'+-':	'2',
	'1+':	'3',
	'+':	'3',
	'2+':	'4',
	'3+':	'5',
	'4+':	'6',
	'Without detecyion':	'',
	'No result':	'',
}
# 問診値変換表
questionCode = {
	'001':	'1',
	'002':	'2',
	'003':	'3',
	'004':	'4',
	'005':	'5',
}

################################################################################
## 文字列チェック
# '9'		: # 半角数値・半角ピリオド(半角ピリオドを除く半角英字記号、全角文字が設定された場合、エラー。)
# '9a'		:
# 'X'		: # 半角英数記号・半角カナ(全角文字が設定された場合、エラー)
# 'Xa'		: # 半角数字のみ
# 'Xb'		: # 半角英数記号のみ
# 'N'		: # 全角文字のみ
# 'N/X'		: # 半角英数記号・半角カナ・全角文字
# 'kana'	: # 半角カタカナのみ
# 'KANA'	: # 全角カタカナのみ
def chkStrType(strWord, chkType):
	if (strWord is None or len(strWord) < 1) or (chkType is None or len(chkType) < 1): return False
	chkStrFlag = False
	pos = None
	#chkWord = strWord.encode('UTF-8')
	chkWord = strWord

	attribType9 = re.compile(r'[0-9.ｧ-ﾝﾞﾟ]+')
	attribType9a = re.compile(r'[0-9]+')
	attribTypeX = re.compile(r'[!\"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~0-9a-zA-Zｧ-ﾝﾞﾟ]+')
	attribTypeXa = re.compile(r'[!\"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~0-9a-zA-Z]+')

	chkHanKana = re.compile(r'[ｧ-ﾝﾞﾟｰ\u3000\x20]+')
	chkZenKana = re.compile(r'[ァ-ンー\u3000\x20]+')
	chkHira = re.compile(r'[ぁ-んー\u3000\x20]+')

	if chkType == '9':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = len(attribType9.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == '9a':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = len(attribType9a.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'X':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = len(attribTypeX.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'Xa':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = len(attribTypeXa.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'N':
		# 半角英数記号半角カナに一致する文字が存在するかチェック
		pos = attribTypeX.search(chkWord)
		# 不一致はNoneが返る
		if pos is None: chkStrFlag = True
	elif chkType == 'Na':
		# 半角カナを削除して余計な文字がいるかチェック
		pos = len(chkHanKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'Nb':
		# 全角カナを削除して余計な文字がいるかチェック
		pos = len(chkZenKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'N/X':
		# 何もしない。。。
		chkStrFlag = True
	elif chkType == 'hira':
		# ひらがなチェック
		pos = len(chkHira.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'kana':
		# 半角カタカナチェック
		pos = len(chkHanKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'KANA':
		# 全角カタカナチェック
		pos = len(chkZenKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	else:
		log('unkwon string check type:{}'.format(chkType))

	return chkStrFlag

## 文字列が指定された長さを超えた場合にまるめる
def mojiCheckConvAndCut(moji, keyData):
	mojidel = re.compile(r'^＜総合所見＞')
	# 連続する1個以上の全角スペース
	zenSp = re.compile(r'[\u3000]+')
	try:
		# m_outsource（csvData_item）に@dataSizeが設定されていない、または数値に変換できない場合はエラー
		keyData['@dataSize'] = int(keyData['@dataSize'])
	except Exception as err:
		log('[keyData check] @dataSize is error: [msg:{}], [data:{}]'.format(err, keyData['@dataSize']), LOG_ERR)
		return moji

	if moji is not None and len(moji) > 0:
		moji = mojidel.sub('', moji).strip()
		# 日本語変換をかける
		# jaconvモジュールでは変換対象外の文字は何もせず返すので、ひらがなとカタカナどちらで入力されていて問題ないように変換しておく
		if keyData['@attribType'] == 'N':
			moji = jaconv.normalize(moji, 'NFKC')								# Unicode正規化
			moji = jaconv.h2z(moji, kana=True, ascii=True, digit=True)			# 半角=>全角へ一律変換
		elif keyData['@attribType'] == 'Na':		# 半角カタカナにする
			moji = jaconv.normalize(moji, 'NFKC')								# Unicode正規化
			moji = jaconv.hira2hkata(moji)										# ひらがな=>（半）カタカナ
			moji = jaconv.z2h(moji, kana=True, ascii=True, digit=True)			# （全）カタカナ=>（半）カタカナ
		elif keyData['@attribType'] == 'Nb':		# 全角カタカナにする
			moji = jaconv.normalize(moji, 'NFKC')								# Unicode正規化
			moji = jaconv.hira2kata(moji)										# ひらがな=>（全）カタカナ
			moji = jaconv.h2z(moji, kana=True, ascii=True, digit=True)			# （半）カタカナ=>（全）カタカナ
			# 連続する全角スペースが存在したら1個にまるめる
			moji = zenSp.sub('\u3000', moji)

		# 文字列チェック
		if chkStrType(moji, keyData['@attribType']) == False:
			log('[string check] type:{}, physicalName:{}, data:\"{}\"'.format(keyData['@attribType'], keyData['@physicalName'], moji), LOG_WARN)

		# 文字列長チェック
		if len(moji) > keyData['@dataSize']:
			# 文字列の長さ調整
			if 'f_deleteString_sizeOver' in conf.convert_option and conf.convert_option['f_deleteString_sizeOver'] == '1':
				#（数字のみは除外とする）
				if keyData['@attribType'] not in ['9', '9a']:
					moji = moji[:keyData['@dataSize']]
			else:
				# 超えてるけど、調整フラグOFFの場合はログ出力だけで何もしない
				log('[string length check] [{}:\"{}\", len:{}][max:{}]'.format(keyData['@physicalName'], moji, len(moji), keyData['@dataSize']), LOG_WARN)
	else:
		# 値がNone
		#log('[string check] text:{}, val:{}'.format(keyData['#text'], moji), LOG_WARN)
		pass

	return moji

def warekiGengo2num(gengo):
	gengoNum = None
	if gengo == '明治'			: gengoNum = '1'
	elif gengo == '大正'		: gengoNum = '2'
	elif gengo == '昭和'		: gengoNum = '3'
	elif gengo == '平成'		: gengoNum = '4'
	elif gengo == '令和'		: gengoNum = '5'

	return gengoNum

def dataClear(data, typeFlag):
	deleteDataList = None

	# 区分に関係なく必ず出力する項目（属性情報とか）
	notDeleteData = [
		'KNSKN-CD',					# 健診機関コード
		'KNSN-KBN',					# 健診区分
		'KENSA-KBN',				# 検査区分
		'HHS-HFSNO',				# 氏名カナ
		'BYMD-GENGO-WRK',			# 元号（生年月日）
		'BYMD-Y-WRK',				# 年（生年月日）
		'BYMD-M-WRK',				# 月（生年月日）
		'BYMD-D-WRK',				# 日（生年月日）
		'SEX',						# 性別
		'KENKG-NO',					# 保険者番号
		'SHIBU-CD',					# 支部コード
		'HKNSH-NO',					# 事業所記号
		'KENKG-GAIBU',				# 被保険者番号
		'KENFG-GAIBU',				# 被扶養者番号
		'JSN-YMD-GENGO-WRK',		# 元号（受診）
		'JSN-YMD-Y-WRK',			# 年（受診）
		'JSN-YMD-M-WRK',			# 月（受診）
		'JSN-YMD-D-WRK',			# 日（受診）

		'SGSKN-SDKBN-1',			# 総合所見指導区分（１）
		'SGSKN-SDKBN-2',			# 総合所見指導区分（２）
		'SGSKN-SDKBN-3',			# 総合所見指導区分（３）
		'SGSKN-SDKBN-4',			# 総合所見指導区分（４）
		'SGSKN-SDKBN-5',			# 総合所見指導区分（５）
		'SGSKN-SDKBN-6',			# 総合所見指導区分（６）
	]

	# 健診区分が子宮単独の場合、出力する項目のみ記載
	if typeFlag in ['3']:
		targetList = [
			'SHIKYU-SDKBN',				# 子宮指導区分
			'SHIKYU-SIBSN-SMEA',		# 細胞診（スメア）
			'SHIKYU-SIBSN-VSSD',		# ベセスダ
			]

		#for key in data.keys():
		#	if key not in targetList and key not in notDeleteData:
		#		data[key] = None
		data = {k : None if k not in targetList and k not in notDeleteData else v for k,v in data.items()}

	# 一般健診のとき付加項目は出さない（眼底は除く）
	elif typeFlag in ['1']:
		targetList = [
			'KANKINO-SOU-TNPKU-UM',		# 総蛋白有無
			'KANKINO-SOU-TNPKU',		# 総蛋白
			'KANKINO-ALBMN-UM',			# アルブミン有無
			'KANKINO-ALBMN',			# アルブミン
			'KANKINO-SOU-BLRBN-UM',		# 総ビリルビン有無
			'KANKINO-SOU-BLRBN',		# 総ビリルビン
			'KKN-LDH-IU-UM',			# LDH（IU）有無
			'KKN-LDH-IU',				# LDH（IU）
			'KKN-LDH-WRU-UM',			# LDH（WRU）有無
			'KKN-LDH-WRU',				# LDH（WRU）
			'KKN-AMRZ-IU-UM',			# アミラーゼ（IU）有無
			'KKN-AMRZ-IU',				# アミラーゼ（IU）
			'KKN-AMRZ-SOU-UM',			# アミラーゼ（SOU）有無
			'KKN-AMRZ-SOU',				# アミラーゼ（SOU）
			'KTKPN-KSHBN-UM',			# 血小板有無
			'KTKPN-KSHBN',				# 血小板
			'KTKPN-MKZ-BASO-UM',		# Baso有無
			'KTKPN-MKZ-BASO',			# Baso
			'KTKPN-MKZ-EOSIN-UM',		# Eosino
			'KTKPN-MKZ-EOSIN',
			'KTKPN-MKZ-STAB-UM',		# Stab
			'KTKPN-MKZ-STAB',
			'KTKPN-MKZ-SEG-UM',			# Seg
			'KTKPN-MKZ-SEG',
			'KTKPN-MKZ-NEUTR-UM',		# Neutro
			'KTKPN-MKZ-NEUTR',
			'KTKPN-MKZ-LYMPH-UM',		# Lympho
			'KTKPN-MKZ-LYMPH',
			'KTKPN-MKZ-MONO-UM',		# Mono
			'KTKPN-MKZ-MONO',
			'KTKPN-MKZ-OTHR-UM',		# Other
			'KTKPN-MKZ-OTHR',
			'NIP-JKN-NCS-SKYU',			# 尿沈渣（赤血球）
			'NIP-JKN-NCS-HKYU',			# 尿沈渣（白血球）
			'NIP-JKN-NCS-JHI',			# 尿沈渣（上皮細胞）
			'NIP-JKN-NCS-ECHU',			# 尿沈渣（円柱）
			'NIP-JKN-NCS-SNT',			# 尿沈渣（その他）
			'HAI-KINO-SDKBN',			# 肺指導区分
			'HAI-KINO-HAKARY-UM',		# 肺
			'HAI-KINO-HAKARY',
			'HAI-KINO-1S-RYO-UM',
			'HAI-KINO-1S-RYO',
			'HAI-KINO-1S-RATE-UM',
			'HAI-KINO-1S-RATE',
			'FBCYP-SDKBN',				# 腹部超音波指導区分
			'FBCYP-SHO',				# 腹部超音波
		]

		#for key in data.keys():
		#	if key in targetList:
		#		data[key] = None
		data = {k : v if k not in targetList else None for k,v in data.items()}

	return data

# 言語マスタ取得
def geti18ndictionary(sid_locale):
	try:
		query = 'SELECT * FROM m_i18n_dictionary where sid_morg = 0 and sid_locale = ' + sid_locale + ';'
		rows = cmn.get_sql_query(query)

	except Exception as err:
		log('error', '{}'.format(err))
		raise

	return rows

# 言語コードが含まれているかチェック
def checkComment(target):
	result = False
	checkStr = str(target)

	try:
		pattern = '.*##.+##.*'  # 例. ##D22000##, ##AC10010## など
		repatter = re.compile(pattern)

		if repatter.search(checkStr) is not None:
			result = True

	except Exception as err:
		log('error', '{}'.format(err))
		raise

	return result

# 言語コードを指定言語に変換
def convComment(target):
	result = ""
	conv = ""
	empattern = '.*＃＃.+＃＃.*'  # 例. ＃＃D22000＃＃, ##AC10010## など
	emrepatter = re.compile(empattern)
	try:
		# 改行で分割
		arr = target.splitlines()

		for i in range(len(arr)):
			if emrepatter.search(arr[i]) is not None:
				arr[i] = unicodedata.normalize("NFKC", arr[i])
			conv = arr[i]
			if checkComment(conv):
				conv = arr[i].replace('##', '')
				for k in range(len(langList)):
					if langList[k]['code'] == conv:
						conv = langList[k]['text']
						break
			if result == "":
				result = conv
			else:
				result = result + '　' + conv


	except Exception as err:
		log('error', '{}'.format(err))
		raise

	return result

## 協会けんぽ用のフォーマットチェック及び変換
# TODO: 入力チェックの定義及びチェック方法は未作成、よってべた書き
def getKKcsvDataItemVale(result):
	if result is None: return None
	from decimal import Decimal, ROUND_HALF_UP
	global jyushinEitemList

	data = {}
	nameDictSidData = {}
	ignoreInspMethodName = []
	kensaUmuList = []
	kensaRankDict = {}
	courseSid = conf.examInfo['course_sid']

	# 判定ランクの文字変換
	#daidai
	#Ａ：異常は認められません。
	#Ｂ：軽度の異常はありますが、日常生活に支障はありません。
	#Ｃ：日常生活に注意し経過観察をしてください。症状があれば受診してください。
	#Ｄ：再検査・精密検査を受けてください。
	#Ｅ：治療が必要です。
	#Ｆ：治療を継続してください。

	#協会けんぽ
	#１．この検査の範囲では異常ありません。
	#２．わずかに基準範囲をはずれていますが、日常生活に差し支えありません。
	#３．日常生活に注意を要し、経過の観察を必要とします。
	#４．治療を必要とします。
	#５．精密検査を必要とします。
	#６．治療中
	if config_data['sid_morg'] == '90007':
		#	daidai	協会けんぽ
		rankConvert = {
			'A'		: 1,	# 異常なし
			'B'		: 2,	# 軽度異常
			'C'		: 3,	# 経過観察
			'C1'	: 3,	# 経過観察
			'C3'	: 3,	# 経過観察
			'C6'	: 3,	# 経過観察
			'C12'	: 3,	# 経過観察
			'D'		: 5,	# 再検査
			'M'		: 4,	# 要治療
			'E'		: 6,	# 要治療
			'NE'	: '',	# 空欄
			'F'		: 10,	# 未使用　判定式があるので仮データを入れておく
			}
	else:
		#	daidai	協会けんぽ
		rankConvert = {
			'A'		: 1,	# 異常なし
			'B'		: 2,	# 軽度異常
			'C'		: 3,	# 経過観察
			'C3'	: 3,	# 経過観察
			'C6'	: 3,	# 経過観察
			'C12'	: 3,	# 経過観察
			'D'		: 5,	# 再検査
			'D1'	: 5,	# 再検査
			'D2'	: 5,	# 再検査
			'E'		: 4,	# 要治療
			'F'		: 6,	# 治療中
			}

	# 指導区分チェック
	# 例：「SNSTT-SDKBN-1」「SDZ-SDKBN」「SGSKN-SDKBN-6」など
	shidouKubunString = re.compile(r'-SDKBN$|-SDKBN-[1-9]$')

	# 「xxx-xxxx-UM」から「-UM」を除外するのに使用する
	# 例：心電図の所見有無「SDZ-SHO-UM」⇒「SDZ-SHO」を抽出
	umuString = re.compile(r'-UM$')

	# 特定コメント（所見）は所見なしと扱う
	shokenNashiMoji = re.compile(r'^(異常(なし|無し|みとめず|認めず|を認めません|は指摘できず)|特記(なし|事項なし|所見なし|すべきことなし)|特になし|所見なし|なし|正常(範囲|範囲内))$')

	# 受診項目リストのチェック。1コースで一般／付加／単独受診を行っている（オプション切り替えで対応している）場合があるため、都度取得する必要がある
	#if courseSid not in jyushinEitemList or len(jyushinEitemList[courseSid]) < 1:
	jyushinEitemList[courseSid] = [k for k in conf.inspStdOptData['eitem'] if conf.inspStdOptData['eitem'][k] in ['3','4']]

	# 医療機関情報
	xmlCstminfo = conf.xml_cstminfo['root']['customer_info']
	# 医療機関情報のフォーマット変換
	xmlCstminfoAddress = xmlCstminfo['print_infos']['print_info']['address']
	# 郵便番号はハイフンあり
	if xmlCstminfoAddress['zip'] is not None:
		if re.match(r'[0-9]{3}-[0-9]{4}', xmlCstminfoAddress['zip']) is None:
			log('[医療機関情報の郵便番号フォーマットエラー:{}][999-9999]'.format(xmlCstminfoAddress['zip']))
			return None
	if xmlCstminfo['print_infos']['print_info']['tel'] is not None:
		# 電話番号はハイフンなし
		xmlCstminfo['print_infos']['print_info']['tel'] = re.sub(r'[-]+', '', xmlCstminfo['print_infos']['print_info']['tel'])
	# 住所はadr1～4を結合
	# TODO: ['print_infos']['print_info']['address']['addr']という枠を作って格納する。実際のXMLにはこの枠がないことに注意
	if 'addr' not in xmlCstminfo['print_infos']['print_info']['address'] or len(xmlCstminfo['print_infos']['print_info']['address']['addr']) < 1:
		addr = None
		if ('adr1' in xmlCstminfoAddress and xmlCstminfoAddress['adr1'] is not None) and len(xmlCstminfoAddress['adr1']) > 0:
			addr = xmlCstminfoAddress['adr1']
		if ('adr2' in xmlCstminfoAddress and xmlCstminfoAddress['adr2'] is not None) and len(xmlCstminfoAddress['adr2']) > 0:
			addr += xmlCstminfoAddress['adr2']
		if ('adr3' in xmlCstminfoAddress and xmlCstminfoAddress['adr3'] is not None) and len(xmlCstminfoAddress['adr3']) > 0:
			addr += xmlCstminfoAddress['adr3']
		if ('adr4' in xmlCstminfoAddress and xmlCstminfoAddress['adr4'] is not None) and len(xmlCstminfoAddress['adr4']) > 0:
			addr += xmlCstminfoAddress['adr4']
		# 半角文字=>全角文字へ一律変換
		xmlCstminfo['print_infos']['print_info']['address']['addr'] = jaconv.h2z(addr, kana=True, ascii=True, digit=True)
		del addr

	# コンフィグのグループ名のリスト
	inspecitonGroupName = {k['@sid']:k['#text'] for k in conf.outsource_config['root']['outsource']['resultItems']['group']['item']}
	# コンフィグの検査項目
	outsourceColumnsEitem = conf.outsource_config['root']['outsource']['columns']['csvData_item']['item']
	# コンフィグの検査項目要素
	inspecitonElement = conf.outsource_config['root']['outsource']['resultItems']['element']['item']
	# コンフィグで設定した検査法の取得
	inspectionMethodItem = conf.outsource_config['root']['outsource']['columns']['inspectionElementMethodType']['item']
	# コンフィグで指定された特定項目の検査法種別を取得
	inspectionMethod = {k['sid']: k['inspMethod'] for k in inspectionMethodItem if 'inspMethod' in k.keys()}
	# 検査結果（xmlMeの）sidのリスト
	reskeyList = {kk:k for k in result for kk in result[k]}


	# 生活習慣予防
	if conf.form_code_subType['20030201'] is not None:
		# TODO: 生活習慣予防で使う。事業者健診は不要？
		if 'eitem' in conf.outsource_config['root']['outsource']['resultItems']:
			inspTypeList = {k['@sid']:k['@inspType'] for k in conf.outsource_config['root']['outsource']['resultItems']['eitem']['item']}
			inspTypeNormal = [k for k in inspTypeList if '1' in inspTypeList[k]]			# 一般リスト（eitem）
			inspTypeHuka = [k for k in inspTypeList if '2' in inspTypeList[k]]				# 付加リスト（eitem）
			inspTypeCervicalCancer = [k for k in inspTypeList if '3' in inspTypeList[k]]	# 子宮リスト（eitem）
			inspTypeBreastCancer = [k for k in inspTypeList if '4' in inspTypeList[k]]		# 乳がんリスト（eitem）
			inspTypeHepatitisVirus = [k for k in inspTypeList if '5' in inspTypeList[k]]	# 肝炎リスト（eitem）

		# 健診区分のチェック
		kenshinKubunFlag = '1'			# デフォは一般健診
		# 一般健診の項目を受診しているのかを確認
		resultinspTypeNormal = [k for k in jyushinEitemList[courseSid] if k in inspTypeNormal]	# 0件で未受診
		# TODO: 一般健診で一部検査項目を受診しない場合もあり得るので、厳密チェックは？なので初期値「１」としている
		if len(resultinspTypeNormal) == len(inspTypeNormal):
			kenshinKubunFlag = '1'
		# 付加健診の項目を受診しているのかを確認
		resultinspTypeHuka = [k for k in jyushinEitemList[courseSid] if k in inspTypeHuka]		# 0件で未受診
		# TODO: 付加健診は、セット受診のみ。単独はなし。かつ４０歳と５０歳
		if 40 == conf.examInfo['age'] or 50 == conf.examInfo['age']:
			# 付加項目を１個以上、かつ、肺機能を受診している場合に付加健診とする（協会けんぽツールで確認すると、肺が必須項目かつ、一般項目に含まれない）
			haiKnouSid = [k['@sid'] for k in outsourceColumnsEitem if k['@physicalName'] == 'HAI-KINO-HAKARY']
			if len(resultinspTypeHuka) > 0 and len(haiKnouSid) > 0:
				eSid2EitemCheck = [k for k,v in conf.inspStdOptData['elementSid'].items() if len(set(haiKnouSid) & set(v)) > 0]
				if len(set(eSid2EitemCheck) & set(resultinspTypeHuka)) > 0:
					kenshinKubunFlag = '2'
		# 子宮頸がん単独受診（女性のみ）
		resultinspTypeCervicalCancer = [k for k in jyushinEitemList[courseSid] if k in inspTypeCervicalCancer]	# 0件で未受診
		if conf.examInfo['sex'] == '2':
			if 20 <= conf.examInfo['age'] <= 38 and not conf.examInfo['age'] & 1:	# 年齢チェック
				# TODO: 単独健診は年齢チェックが必要
				if len(resultinspTypeCervicalCancer) > 0:	# 1以上で受診している
					if (int(len(resultinspTypeNormal)) + int(len(resultinspTypeHuka))) < 1:	# 一般項＋負荷を何も受診していない
						kenshinKubunFlag = '3'

	# 出力データ作成
	for keyData in csvDataItemDict['item']:
		value = None
		gHanteiSyokenDataFlag = False		# グループ判定の所見文を突っ込むためのフラグ
		if '@xmlTag' not in keyData and '@sid' not in keyData: continue

		# 指定がないものは枠だけ作成する
		if (keyData['@xmlTag'] is not None and len(keyData['@xmlTag']) < 1) and (keyData['@sid'] is not None and len(keyData['@sid']) < 1):
			value = {keyData['@physicalName']: None}
			# 生活習慣の測定有無を埋めるためにあとで使用する
			if umuString.search(keyData['@physicalName']):
				kensaUmuList.append(keyData['@physicalName'])

		# 指導区分（判定ランク）は枠だけ作成。ランクを入れるのはここではない
		elif shidouKubunString.search(keyData['@physicalName']):
			kensaRankDict.update({keyData['@physicalName']:keyData['@sid'].split(',')})
			value = {keyData['@physicalName']: None}

		# xmlTagを優先使用
		elif len(keyData['@xmlTag']) > 0:
			keyList = keyData['@xmlTag'].split('/')
			searchDictObj = None
			resVal = None
			if 'outsource' in keyList: searchDictObj = conf.outsource_config
			elif 'customer_info' in keyList: searchDictObj = conf.xml_cstminfo
			elif 'data' in keyList:			# 例外：検査結果の格納された変数を参照する
				searchDictObj = {}
				searchDictObj['data'] = {}
				searchDictObj['data']['group'] = result['group']
				if 'group' in keyList and 'finding' in keyList:
					gHanteiSyokenDataFlag = True

			else: continue

			try:
				for key in keyList:
					if gHanteiSyokenDataFlag == True and key == 'finding':
						tmp = searchDictObj[key]
						searchDictObj = {}
						for k,v in tmp.items():
							v2 = re.sub(r'^.*[,]*: ', '', v)
							searchDictObj.update({k:v2})
						del tmp
					else:
						searchDictObj = searchDictObj[key]
			except Exception as err:
				log('[searchDictObj:{}], [type:{}], [msg:{}]'.format(searchDictObj, err.__class__.__name__, err), LOG_ERR)
				return None

			# TODO: ちょっとめんどくさいやり方かも。すまーとなやり方があれば採用
			try:
				# 注意事項には判定所見を全て繋げる
				if keyData['@physicalName'] in ['CHUI-JKU'] and gHanteiSyokenDataFlag == True:
					if config_data['sid_morg'] == '90007':
						for k in searchDictObj:
							searchDictObj[k] = convComment(searchDictObj[k])
					findingGroupName = {str(k)+'_finding':inspecitonGroupName[k] for k in inspecitonGroupName}
					resVal = ''.join([str(findingGroupName[k])+':'+str(searchDictObj[k]) for k in searchDictObj])
				else:
					resVal = result[reskeyList[searchDictObj]][searchDictObj]
			except KeyError:
				# 検査結果に存在しないもの
				resVal = searchDictObj
			except Exception as err:
				log('[result data] get error: [Name:{}] [msg:{}]'.format(keyData['@physicalName'], err), LOG_ERR)

			if resVal is not None:
				# 文字列変換と長さ調整
				resVal = mojiCheckConvAndCut(resVal, keyData)
			else:
				# 値がNone
				#log('[string check] text:{}, val:{}'.format(keyData['#text'], resVal), LOG_WARN)
				pass

			# 左０埋めしたいもの
			# 被保険者番号（KENKG-GAIBU）
			if keyData['@physicalName'] in ['KENKG-GAIBU']:
				resVal = '{v:0>{padding}}'.format(v=resVal, padding=keyData['@dataSize'])

			# {名前: 値}
			value = {keyData['@physicalName']: resVal}

			# 念のためクリア
			del resVal

		# xmlMeの結果を見るので、主に検査項目
		elif len(keyData['@sid']) > 0:
			# 要素sidが複数候補にある場合、１個ずつチェックして有効なやつを採用
			keyDataSid = keyData['@sid'].split(',')
			if len(keyDataSid) > 1:
				try:
					keyData['@sid'] = [k for k in keyDataSid if cmn.get_inspection_status_check(elementSid=k)][0]
				except:
					# 有効な検査項目がみつからない場合は枠だけ作成してスキップ。その際のsidは強制で先頭を選択する
					data.update({keyData['@physicalName']: None})
					nameDictSidData.update({keyData['@physicalName']:keyDataSid[0]})
					continue
			sidValue = None
			try:
				# 検査方法が指定されているが、inspectionMethod内の検査方法と一致しないkeyは枠だけ作成してスキップ
				if ('@inspMethod' in keyData and len(keyData['@inspMethod']) > 0) and keyData['@sid'] in inspectionMethod:
					if keyData['@inspMethod'] != inspectionMethod[keyData['@sid']]:
						ignoreInspMethodName.append(keyData['@physicalName'])
						data.update({keyData['@physicalName']: None})
						nameDictSidData.update({keyData['@physicalName']:keyData['@sid']})
						continue

				# まずは結果データを取得。
				# TODO: 個別処理が必要な場合、適宜加工を行うこと
				try:
					sidValue = result['inspection'][keyData['@sid']]
					#成田用変換
					if config_data['sid_morg'] == '90007':
						sidValue = convComment(sidValue)
				except Exception:
					sidValue = None
					log('[value get error] [sid:{}][physicalName:{}][text:{}]'.format(keyData['@sid'], keyData['@physicalName'], keyData['#text']), LOG_ERR)

				# 定性値コード変換
				ignoreTeisei2Num = ['KEC-KANEN-HCV-KOUTAI', 'KEC-KANEN-HCV-KSZF-KS']
				prefixNum = None
				# 定性値をコードに変換
				if sidValue is not None and keyData['@physicalName'] in ignoreTeisei2Num:
					if sidValue in qualitativeCode:
						sidValue = qualitativeCode[sidValue]
					else:
						log('unknwon question code, msg:[name:{}, val:{}]'.format(keyData['@physicalName'], sidValue), LOG_WARN)
				#成田用変換
				if config_data['sid_morg'] == '90007':
					# 問診値コード変換
					ignoreQuestionNum = ['MSHY-FY1-KA', 'MSHY-FY2-KT','MSHY-FY3-ST','MSHY-KITENRK']
					# 定性値をコードに変換
					if keyData['@physicalName'] in ignoreQuestionNum:
						if sidValue is None:
							sidValue = '2'
						elif sidValue in questionCode:
							sidValue = questionCode[sidValue]
						else:
							log('unknwon teisei code, msg:[name:{}, val:{}]'.format(keyData['@physicalName'], sidValue), LOG_WARN)
					#採血時間の変換(手入力でくる)
					if sidValue is not None and keyData['@physicalName'] in 'SIKT-TIME':
						if sidValue >= 10:
							sidValue = '2'
						elif 4 <= sidValue <= 9:
							sidValue = '3'
						elif sidValue <= 3:
							sidValue = '4'
				# 定性値を持つ項目と、数字または定性値どちらもあり得る項目を変換する(現状、両方あり得るのはHBs抗原のみ)
				if sidValue is not None and (re.search(r'[+\-]+', sidValue) is not None or keyData['@physicalName'] in ['KEB-KANEN-HBS-KOGN']):
					checkVal = None
					# 数字チェック
					try:
						checkVal = Decimal(str(sidValue)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
						checkVal = str(checkVal).split('.')
						valInt = checkVal[0]		# 整数部
						valDec = checkVal[1]		# 小数部
					except Exception:
						valInt = None
						valDec = '0'
					# 定性値をコードに置き換える
					if checkVal is None:
						if sidValue in qualitativeCode:
							sidValue = qualitativeCode[sidValue]
						else:
							log('unknwon teisei code, msg:[name:{}, val:{}]'.format(keyData['@physicalName'], sidValue), LOG_WARN)

					# 「0」付与は生活習慣のみかも
					if conf.form_code_subType['20030201'] is not None:
						# 数値はありえない（定性値のみ）ため、頭は「0」
						if keyData['@physicalName'] in ['DAICY-MENEK-1DAY', 'DAICY-MENEK-2DAY', 'NIP-JKN-NSNKT', 'KETTO-NYOTO-KYTRI', 'KETTO-NYOTO-MKSHO', 'NIP-JKN-NTNPK-KYTRI', 'NIP-JKN-NTNPK-MKSHO']:
							prefixNum = valueDataType['qualitativeVal']
						# 検査結果が、"定性値"または"数値"どちらかの場合がありえーる項目のみ変換時に頭は「1」
						else:
							prefixNum = valueDataType['both']

						# エクセルツールのHBs抗原の枠が特殊
						if keyData['@physicalName'] in ['KEB-KANEN-HBS-KOGN']:
							# 数字である
							if checkVal is not None:
								prefixNum = valueDataType['numberVal']
								sidValue = valInt

				# 数字データの組み立て
				if prefixNum is not None:
					# 数字、または定性値をコードに変換
					if prefixNum == valueDataType['numberVal'] or prefixNum == valueDataType['both']:
						sidValue = '{pn}{sv:0>5}.{vd:0>2}'.format(pn=prefixNum, sv=sidValue, vd=valDec)
					# それ以外
					else:
						sidValue = '{pn}{sv:0>5}{vd}'.format(pn=prefixNum, sv=sidValue, vd='00')

				# 撮影区分 胸部X線／胃部X線
				if keyData['@physicalName'] in ['KBXSN-STEI-KBN', 'IBXSN-STEI-KBN'] and sidValue is not None and len(sidValue) > 0:
					# daidai出力						# CSV出力
					if sidValue == '1'					: sidValue = '1'		# 直接
					elif sidValue == '2'				: sidValue = '2'		# 間接
					elif sidValue == '3'				: sidValue = '1'		# デジタル
					else: # TODO: 一致なしはデータを空にする
						sidValue = None
				# メタボ判定の値を変換
				elif keyData['@physicalName'] in ['ISHD-MSDM-HTCD'] and sidValue is not None and len(sidValue) > 0:
					# daidai出力						# CSV出力
					if sidValue == '3'	or sidValue == '003'	: sidValue = '1'		# 基準該当
					elif sidValue == '2'	or sidValue == '002'	: sidValue = '2'		# 予備群該当
					elif sidValue == '1'	or sidValue == '001'	: sidValue = '3'		# 非該当
					elif sidValue == '4'	or sidValue == '004'	: sidValue = '4'		# 判定不能
					else: # TODO: 一致なしはデータを空にする
						sidValue = None
				# 保健指導レベルの値を変換
				elif keyData['@physicalName'] in ['ISHD-HKSD-LVL'] and sidValue is not None and len(sidValue) > 0:
					# daidai出力						# CSV出力
					if sidValue == '4'					: sidValue = '1'		# 積極的支援
					elif sidValue == '3'				: sidValue = '2'		# 動機づけ支援
					elif sidValue in ['1','2']			: sidValue = '3'		# なし
					elif sidValue == '5'				: sidValue = '4'		# 判定不能
					else: # TODO: 一致なしはデータを空にする
						sidValue = None

				# TODO: 定性値(入力)を数値(出力)に変換した後じゃないと、文字列長が不一致になる可能性がある
				# 文字列チェック変換と長さ調整
				if sidValue is not None:
					sidValue = mojiCheckConvAndCut(sidValue, keyData)

				# 生活習慣
				if conf.form_code_subType['20030201'] is not None:
					# 眼底の選択肢の値に「0」を付与する
					if keyData['@physicalName'] in ['GNTEI-KW', 'GNTEI-SCH', 'GNTEI-SCS', 'GNTEI-SCT', 'GNTEI-WM', 'GNTEI-DAS']:
						if str(int(sidValue)) in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
							sidValue = '00000' + str(int(sidValue)) + '00'
						# 眼底（SCOTT）の提出データ定義に分類(0度)は存在しないため、(？)設定不能を入れる
						elif int(sidValue) == 0 and keyData['@physicalName'] == 'GNTEI-SCT':
								sidValue = '?'

				# 事業者健診
				if conf.form_code_subType['20030202'] is not None:
					# 眼底の選択肢の値から「0」を削除する
					if keyData['@physicalName'] in ['GNTEI-KW', 'GNTEI-SCH', 'GNTEI-SCS', 'GNTEI-SCT', 'GNTEI-WM', 'GNTEI-DAS']:
						sidValue = re.sub(r'[0]+', '', sidValue)

				# {名前: 項目入力データ}
				value = {keyData['@physicalName']: sidValue}

			except Exception as err:
				# 検査結果が存在しない。（基準が組まれていない可能性大）
				log('data not found [{}:{}], [type:{}]'.format(keyData['@sid'], ''.join([k['#text'] for k in inspecitonElement if k['@sid'] == keyData['@sid']]), err.__class__.__name__), LOG_WARN)
				continue
		else:
			log('@xmlTag is None, @sid is None', LOG_WARN)
			continue

		if value is not None:
			data.update(value)
			# もろもろの処理を行う際にsidを使用するので｛name:sid｝の辞書を作成しておく
			nameDictSidData.update({keyData['@physicalName']:keyData['@sid']})

	if len(data) < 1: return None

	# 生活習慣予防だけかな？
	# 健診区分
	if 'KNSN-KBN' in data:
		data['KNSN-KBN'] = kenshinKubunFlag
	# 検査区分
	if 'KENSA-KBN' in data:
		data['KENSA-KBN'] = '1'					# デフォ
		if kenshinKubunFlag in ['1','2']:
			data['KENSA-KBN'] = '1'
		elif kenshinKubunFlag in ['3']:
			data['KENSA-KBN'] = '1'
	# 支部コードは健診機関コードから抽出
	if 'SHIBU-CD' in data:
		data['SHIBU-CD'] = data['KENKG-NO'][2:4]

	# TODO: 個別処理（基本的に生活習慣予防と事業者健診では共通になるはず。違う場合は処理を分けること）
	# データ作成後、改めて各項目毎に必要な判定があれば。。。

	# 生活習慣と事業者健診で値の意味が逆
	if conf.form_code_subType['20030201'] is not None:			# 生活習慣予防
		umu_nashi	= '1'		# 特記すべきこと"なし"
		umu_ari		= '2'		# 特記すべきこと"あり"
		umu_unknown	= '?'		# 設定不能
	elif conf.form_code_subType['20030202'] is not None:		# 事業者健診
		umu_nashi	= '2'		# 特記すべきこと"なし"
		umu_ari		= '1'		# 特記すべきこと"あり"
		umu_unknown	= ''
	else:
		umu_nashi = None
		umu_ari = None
		umu_unknown	= None

	# 生活習慣と事業者健診
	# 所見の有無
	shokenUmuList = ['SDZ-SHO-UM', 'SNSTT-KIOU-UM', 'SNSTT-JKKSJ-UM', 'SNSTT-TKSJ-UM']
	for keyName in shokenUmuList:
		if keyName in data:
			inspKeyName = umuString.sub('', keyName)	# shokenUmuListに登録された名前から「-UM」を除いた名前を抽出
			# 既往歴／自覚症状／他覚症状の文字列チェック
			if keyName in ['SNSTT-KIOU-UM', 'SNSTT-JKKSJ-UM', 'SNSTT-TKSJ-UM'] and inspKeyName in data:
				data[keyName] = umu_nashi
				if data[inspKeyName] is not None and len(data[inspKeyName]) > 0:		# 入力データあり
					data[keyName] = umu_ari
					if shokenNashiMoji.search(data[inspKeyName]) is not None:			# 入力データが「異常がない」旨の文字列に一致する
						data[keyName] = umu_nashi
			# 心電図
			if 'SDZ-SHO-UM' == keyName and inspKeyName in data and cmn.get_inspection_status_check(elementSid=nameDictSidData[inspKeyName]):		# 受診してるかも合わせてチェック
				# 医師判定が「異常なし」は所見なしと扱う
				if data[keyName] in ['1','90001']:
					data[keyName] = umu_nashi
				else:
					# 医師判定が「異常なし」"以外"が選択されている場合は、所見有無ありと扱う
					data[keyName] = umu_ari
					# 所見入力なしは「所見有無なし」とする
					if data[inspKeyName] is None or len(data[inspKeyName]) < 1:
						data[keyName] = umu_nashi
					# 所見にデータ入力されている場合は「異常がない」旨の所見文字列が入力されているかチェックを行い該当したら「所見有無なし」とする
					elif data[inspKeyName] is not None and len(data[inspKeyName]) > 0 and shokenNashiMoji.search(data[inspKeyName]) is not None:
						data[keyName] = umu_nashi

			del inspKeyName			# 念のためクリア

	# 生活習慣
	if conf.form_code_subType['20030201'] is not None:
		# 検査の有無
		kensa_umu_nashi		= '0'
		kensa_umu_ari		= '1'
		for keyName in kensaUmuList:
			if keyName in shokenUmuList: continue
			inspKeyName = umuString.sub('', keyName)
			# 要素sidから項目sidを検索
			try:
				eitemSid = [k for k in conf.inspStdOptData['elementSid'] if inspKeyName in nameDictSidData and nameDictSidData[inspKeyName] in conf.inspStdOptData['elementSid'][k]][0]
			except:
				eitemSid = None
			if eitemSid is None:
				data[keyName] = None
				data[inspKeyName] = None
			# 検査法毎に枠があるが、使用しないものは未入力扱い
			elif inspKeyName in ignoreInspMethodName:
				data[keyName] = None
				data[inspKeyName] = None
			# 未受診である
			elif conf.inspStdOptData['eitem'][eitemSid] in ['1','2']:
				# 一般健診
				if kenshinKubunFlag == '1':
					# 未受診項目は「0:測定なし（検査なし）」を設定かつ、データも念のためクリア
					if eitemSid in inspTypeNormal:
						data[keyName] = kensa_umu_nashi
						#if data[inspKeyName] is None or len(data[inspKeyName]) < 1:
						#	data[keyName] = None
						data[inspKeyName] = None
					# 付加項目／子宮頸がんリストに含まれるものは、データクリア
					elif eitemSid in inspTypeHuka or eitemSid in inspTypeCervicalCancer:
						data[keyName] = None
						data[inspKeyName] = None
				# 付加健診
				elif kenshinKubunFlag == '2':
					# 一般と付加に含まれるもの
					if eitemSid in inspTypeNormal or eitemSid in inspTypeHuka:
						data[keyName] = kensa_umu_nashi
						#if data[inspKeyName] is None or len(data[inspKeyName]) < 1:
						#	data[keyName] = None
						data[inspKeyName] = None
					# 子宮頸がんリストに含まれる場合、データなし
					elif eitemSid in inspTypeCervicalCancer:
						data[keyName] = None
						data[inspKeyName] = None
				# 子宮頸がん単独受診
				elif kenshinKubunFlag == '3':
					# 健診区分が単独に含まれる場合
					if eitemSid in inspTypeCervicalCancer:
						data[keyName] = kensa_umu_nashi
						data[inspKeyName] = None
					# 一般項目／付加に含まれる場合、データなし
					elif eitemSid in inspTypeNormal or eitemSid in inspTypeHuka:
						data[keyName] = None
						data[inspKeyName] = None
			# 受診している
			elif conf.inspStdOptData['eitem'][eitemSid] in ['3','4']:
				data[keyName] = kensa_umu_ari
				# 検査結果が空
				if data[inspKeyName] is None or len(data[inspKeyName]) < 1:
					data[keyName] = kensa_umu_nashi
				# 「結果なし」、「未実施」、「測定不能」はXMLME解析時に「?」に加工済みのため、データを空にして測定有無に「?」をセットする
				elif data[inspKeyName] in ['?']:
					data[inspKeyName] = ''
					data[keyName] = umu_unknown

			log('sid:{}, key:{}, umu:{}, value:{}'.format(eitemSid, keyName, data[keyName], data[inspKeyName]), LOG_DBG)
			del inspKeyName			# 念のためクリア

		# HCV抗体とHCV拡散増幅検査の関係
		if data['KEC-KANEN-HCV-KOUTAI'] is not None and len(data['KEC-KANEN-HCV-KOUTAI']) > 0:
			# qualitativeCodeで変換された後のデータが格納されているため、そこと比較チェックする必要がある
			if data['KEC-KANEN-HCV-KOUTAI'] in [qualitativeCode['-']]:
				data['KEC-KANEN-HCV-KOUTAI'] = '1'					# 1:Ｃ型肝炎ウイルスに感染して"いない"可能性が極めて高い
			elif data['KEC-KANEN-HCV-KOUTAI'] in [qualitativeCode['+-'], qualitativeCode['1+'], qualitativeCode['2+'], qualitativeCode['3+'], qualitativeCode['4+']]:
				data['KEC-KANEN-HCV-KOUTAI'] = '2'					# 2:Ｃ型肝炎ウイルスに感染して"いる"可能性が極めて高い
			elif re.match(r'[0-9\?]', data['KEC-KANEN-HCV-KOUTAI']) is not None:
				# 定性値から協会けんぽツール用の値に変換済みの場合何もしない
				pass
			else:
				data['KEC-KANEN-HCV-KOUTAI'] = '?'					# 一致しないものは「？」をいれる

			if data['KEC-KANEN-HCV-KSZF-KS'] is not None and len(data['KEC-KANEN-HCV-KSZF-KS']) > 0:
				data['KEC-KANEN-HCV-KOUTAI'] = '3'					# 3:要HCV核酸増幅検査。このルートに落ちてきている＝HCV核酸増幅検査を受けていることになるため、HCV抗体の値変更を行う
				if data['KEC-KANEN-HCV-KSZF-KS'] in [qualitativeCode['-']]:
					data['KEC-KANEN-HCV-KSZF-KS'] = '1'				# 1:Ｃ型肝炎ウイルスに感染して"いない"可能性が極めて高い
				elif data['KEC-KANEN-HCV-KSZF-KS'] in [qualitativeCode['+-'], qualitativeCode['1+'], qualitativeCode['2+'], qualitativeCode['3+'], qualitativeCode['4+']]:
					data['KEC-KANEN-HCV-KSZF-KS'] = '2'				# 2:Ｃ型肝炎ウイルスに感染して"いる"可能性が極めて高い
				elif re.match(r'[0-9\?]', data['KEC-KANEN-HCV-KSZF-KS']) is not None:
					# 定性値から協会けんぽツール用の値に変換済みの場合何もしない
					pass
				else:
					data['KEC-KANEN-HCV-KSZF-KS'] = '?'				# 一致しないものは「？」をいれる

		# 判定ランク
		if len(kensaRankDict) > 0:
			# ランク判定するのに使用するデータ
			groupCheck2Eitem = {k['@physicalName'] : {'sid':k['@sid'].split(','),'gsid':k['@gsid'].split(',')} for k in outsourceColumnsEitem if '@gsid' in k and '@sid' in k}
			# 治療中のランクが1個でもあればON
			rankChiryoutyuuFlag = False
			# グループ（項目の判定結果から算出）
			for keyName,sidList in kensaRankDict.items():
				# 上部消化器X線と上部消化器内視鏡はどちらか1個しか作成しない
				if keyName in ['IBXSN-SDKBN', 'ISKYO-SDKBN'] and len(sidList) > 0:
					# 未受診の場合スキップ。両方受けていたら。。。とりあえず出力して協会けんぽツール側で修正させる？
					if sidList[0] in conf.inspStdOptData['eitem'] and conf.inspStdOptData['eitem'][sidList[0]] in ['1','2']:
						continue
					# TODO: eitemに含まれていないパターンが存在する。含まれていなければスキップ
					elif sidList[0] not in conf.inspStdOptData['eitem'] :
						continue

				if keyName in data and not(re.search(r'SGSKN-SDKBN-[1-9]$', keyName)):
					eItemRank = {k : conf.m_opinion_rankset['group'][result['eitem'][k]['code']]['name'] for k in sidList if k in result['eitem'] and 'code' in result['eitem'][k] and result['eitem'][k]['code'] not in ['90001', '90099']}
					groupRank = None
					gRankManual = None
					if keyName in groupCheck2Eitem and 'gsid' in groupCheck2Eitem[keyName]:
						tmp = list(set(groupCheck2Eitem[keyName]['gsid']) & set(result['group']['rankManualFlag'].keys()))
						if tmp is not None and len(tmp) > 0:
							# グループランクに手動入力されていた場合はここ、対象の項目はm_outsourceで事前設定を行う
							gRankManual = result['group']['rankManualFlag'][tmp[0]]
							# ランク文字以外が直接含まれる場合、スキップする
							if gRankManual not in rankConvert.keys():
								log('find group rank code is {}, proc skip'.format(gRankManual), LOG_WARN)
								continue
							data[keyName] = rankConvert[gRankManual]
							continue
					if len(eItemRank) > 0:
						rankCheck = [rankConvert[eItemRank[k]] for k in eItemRank]
						# グループランクの抽出（A～F以外の文字は除外）
						rankList = {k:v for k,v in result['group']['rank'].items() if v in rankConvert.keys()}
						if keyName in groupCheck2Eitem and len(list(set(sidList) & set(groupCheck2Eitem[keyName]['sid']))) > 0:
							# 問診の治療中が存在していたので、頑張ってグループランクを集める
							groupRank = [rankConvert[rankList[k+'_rank']] for k in groupCheck2Eitem[keyName]['gsid'] if k+'_rank' in rankList]
							rankCheck.extend(groupRank)
						data[keyName] = max(rankCheck)
						if rankConvert['F'] in rankCheck:
							rankChiryoutyuuFlag = True
			# 総合
			totalRankMoji = result['general'][conf.outsource_config['root']['outsource']['columns']['general_item']['code']]
			if totalRankMoji is not None and len(totalRankMoji) > 0 and totalRankMoji in rankConvert.keys():
				totalRank = rankConvert[totalRankMoji]
				tRankPhysicalName = 'SGSKN-SDKBN-{}'.format(totalRank)
				if totalRank == rankConvert['F']:
					totalRank = None
				data[tRankPhysicalName] = totalRank
				if rankChiryoutyuuFlag == True:
					tRankChiryoutyuu = 'SGSKN-SDKBN-{}'.format(rankConvert['F'])
					data[tRankChiryoutyuu] = rankConvert['F']

	# 生活習慣予防
	if conf.form_code_subType['20030201'] is not None:
		# 子宮単独時の場合に出力したくないデータを空にする
		if kenshinKubunFlag in ['1','3']:
			data = dataClear(data, kenshinKubunFlag)

	return data

def create_kyoukaikenpo(xml_outsource):
	global config_data
	global csvHeaderItemDict
	global csvDataItemDict
	global langList

	tmp_file = None
	sid = None
	sid_examinee = None
	err_sid_list = []

	csv_data = []
	#csv_header_dict = {'LineNo':1}		# 固定
	csv_header = []						#
	total_cnt = 1						# データ件数のカウント用

	# 出力ファイル名の部品
	out_file_prefix = config_data['out_file_prefix']
	out_file_suffix = config_data['out_file_suffix']

	# 協会けんぽ用
	csvHeaderItemDict = conf.outsource_config['root']['outsource']['columns']['csvHeader_item']
	csvDataItemDict = conf.outsource_config['root']['outsource']['columns']['csvData_item']
	houbetsuNumber = conf.outsource_config['root']['outsource']['houbetsuNumber'].split(',')

	# 内部処理切り分け用の何かを格納
	if 'form_code_subType' in conf.outsource_config['root']['outsource']['condition']:
		formSubType = conf.outsource_config['root']['outsource']['condition']['form_code_subType']['subCode']
		if formSubType in conf.form_code_subType:
			conf.form_code_subType[formSubType] = '1'
	else:
		log('[m_outsouce] check formSubType')
		cmn._exit('xml_error', '[m_outsource] formSubType not found')

	try:

		# MySQL
		sql.open()

		if xml_outsource is not None or xml_outsource == '':
			# CSV形式
			csv_option = cmn.outsource_dict('condition')
			# 変換オプション、最低限の初期値(keyが存在しなければ入れる)
			if 'f_birthday2age' not in conf.convert_option: conf.convert_option['f_birthday2age'] = '0'
			if 'f_kana_sort' not in conf.convert_option: conf.convert_option['f_kana_sort'] = '0'
			# 受診者情報
			examinee_item = cmn.outsource_dict('columns/examinee_item')
			# 予約情報
			appoint_item = cmn.outsource_dict('columns/appoint_item')
			# 検査項目情報
			inspection_item = cmn.outsource_dict('resultItems/element')
			# 総合判定／所見
			general_item = cmn.outsource_dict('columns/general_item')
			# グループ判定
			groupRank_item = cmn.outsource_dict('resultItems/group')
			# 団体情報
			org_item = cmn.outsource_dict('columns/org_item')
			if 'insurer_number' not in org_item:		# org_itemに保険者番号がないので終わり
				cmn._exit('xml_error', '[m_outsource] org_item Fault (insurer_number not found)')
			# 受診対象項目
			#acceptance_item = cmn.outsource_dict('columns/acceptance_item')

			# ソートで使用するためにコンフィグ内のデータを変更しておく
			if sort_code['date'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['date']]['key'] = appoint_item['dt_appoint']						# 受信日
			if sort_code['course'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['course']]['key'] = appoint_item['title_me']					# コース
			if sort_code['number'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['number']]['key'] = appoint_item['appoint_number']				# 受診番号
			if sort_code['examinee'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['examinee']]['key'] = examinee_item['name']					# 健診者氏名
			if sort_code['org_agreement'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['org_agreement']]['key'] = org_item['insurance_name']	# 契約団体
			if sort_code['org_affiliation'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['org_affiliation']]['key'] = org_item['org_name']		# 所属団体


		else:
			cmn._exit('xml_error', '[m_outsource] xml get failed')		# m_outsourceのXML取得失敗

		del xml_outsource

		# 抽出条件
		cond_contract = cmn.search_abst_sort_cond(abst_code['org_agreement'])		# 契約団体
		cond_course = cmn.search_abst_sort_cond(abst_code['course'])				# 受診コース
		cond_org = cmn.search_abst_sort_cond(abst_code['org_affiliation'])			# 所属団体
		cond_examinee = cmn.search_abst_sort_cond(abst_code['examinee'])			# 健診者
		cond_appo = cmn.search_abst_sort_cond(abst_code['status'])					# 受付ステータス

		# ソート条件
		priority_appo = cmn.search_abst_sort_cond(sort_code['date'])					# 受診日
		priority_org = cmn.search_abst_sort_cond(sort_code['course'])					# 受診コース
		priority_course = cmn.search_abst_sort_cond(sort_code['org_agreement'])			# 契約団体
		priority_contact = cmn.search_abst_sort_cond(sort_code['org_affiliation'])		# 所属団体
		priority_aponum = cmn.search_abst_sort_cond(sort_code['number'])				# 受診番号
		priority_examinee = cmn.search_abst_sort_cond(sort_code['examinee'])			# 健診者

		sort_cond = []
		sort_cond.append(priority_appo) if priority_appo is not None else None
		sort_cond.append(priority_org) if priority_org is not None else None
		sort_cond.append(priority_course) if priority_course is not None else None
		sort_cond.append(priority_contact) if priority_contact is not None else None
		sort_cond.append(priority_aponum) if priority_aponum is not None else None
		sort_cond.append(priority_examinee) if priority_examinee is not None else None

		# 予約者情報の取得
		sql_query = 'call p_appoint_noxml(?,0,?,?,?,null,null,null,null,null,null,null);'
		param = (config_data['sid_morg'], max(cond_appo), config_data['date_start'], config_data['date_end'])
		log(' \"{}\", \"{}\"'.format(sql_query, param), LOG_INFO)

		# TODO: fetchallで全件取得を行い、データ数のカウントを行う。件数が多いときに制限として使うかな・・・？
		#       ただし、XMLが返るような検索で使用するのは禁止。メモリ食いすぎる。
		rows = sql.once2noexit(sql_query, param)
		# 0件データチェック
		if rows is None or len(rows) < 1: cmn._exit('info', 'no data')
		log('sql row data count: {}'.format(len(rows)), LOG_INFO)
		#成田用変換
		if config_data['sid_morg'] == '90007':
			# 変換言語は日本語で出力(固定)
			sid_locale = '140001'
			# 言語マスタ取得
			langList = geti18ndictionary(sid_locale)

		# 組み立て
		# TODO: skipする場合は必ずSQLのカーソルを進めること
		#       row = cur.fetchone() <- これを入れる
		for row in rows:
			# ループ開始時にクリアしておかないと処理途中でエラー抜けした場合、ログに無関係なIDと受信日が表示される
			conf.examInfo['appoint_day'] = None
			conf.examInfo['id'] = None

			# 絞り込み
			sid = conf.examInfo['sid'] = str(row['sid']) if row['sid'] is not None else None				# p_appointが返却するレコードに含まれるsid
			sid_examinee = conf.examInfo['sid_examinee'] = str(row['sid_examinee']) if row['sid_examinee'] is not None else None
			appo_sts = conf.examInfo['appo_sts'] = str(row['status']) if row['status'] is not None else None
			course_sid = conf.examInfo['course_sid'] = str(row['sid_me']) if row['sid_me'] is not None else None
			sid_cntracot = conf.examInfo['sid_cntracot'] = str(row['sid_contract']) if row['sid_contract'] is not None else None

			if (cmn.check_abst_sts(appo_sts, cond_appo) == False):						# 受付ステータス
				log(' *** reject status', LOG_DBG)
				continue

			if (cmn.check_abst_sts(sid_examinee, cond_examinee) == False):				# 受診者
				log(' *** reject examinee', LOG_DBG)
				continue

			if (cmn.check_abst_sts(course_sid, cond_course) == False):					# コース
				log(' *** reject course', LOG_DBG)
				continue

			if (cmn.check_abst_sts(sid_cntracot, cond_contract) == False):				# 契約
				log(' *** reject cntracot', LOG_DBG)
				continue

			# 絞り込みここまで、ただし団体はこの時点では不明なので下の方

			# 受診者
			# 予約時点の情報を取得するため、t_appointを参照する
			#t_appoint = sql.once('SELECT * FROM t_appoint where sid_morg = '+ config_data['sid_morg'] +' and sid = ' + sid + ';')
			t_appoint = cmn.get_t_appoint(sid)
			if t_appoint is None: continue
			examData = getXmlSid.analyzeXmlExaminee(cmn.getRow2Xml(t_appoint[0]['xml_examinee']))['examinee']
			result_examinee = {}
			dt_appoint_base = row['dt_appoint'].split()
			dt_appoint_day = dt_appoint_base[0]							# 予約日

			conf.examInfo['appoint_day'] = dt_appoint_day
			conf.examInfo['id'] = examData[sid_examinee]['id']

			result_examinee[sid] = {}
			result_examinee[sid] = cmn.get_examinee_data(examData[sid_examinee], examinee_item)
			# 協会けんぽの生年月日（日付）フォーマットに変換 # YYYYMMDD(区切り文字の記号なし)
			result_examinee[sid][examinee_item['birthday']] = re.sub(r'[/-]', '', result_examinee[sid][examinee_item['birthday']])
			# 協会けんぽ用に数字に変換（生年月日の元号）
			if 'birthdayGengo' in examinee_item:
				result_examinee[sid][examinee_item['birthdayGengo']] = warekiGengo2num(result_examinee[sid][examinee_item['birthdayGengo']])

			log('apoDay:{}, age:{}'.format(conf.examInfo['appoint_day'], conf.examInfo['age']), LOG_DBG)
			#del key_list, key, tmp_list1, tmp_list2, item, xml_examinee

			# コース名、予約日(受診日)
			result_appoint = {}
			result_appoint[sid] = {}
			result_appoint[sid] = cmn.get_appo_info(row, appoint_item)
			# 協会けんぽの受診日（日付）フォーマットに変換 # YYYYMMDD(区切り文字の記号なし)
			result_appoint[sid][appoint_item['dt_appoint']] = re.sub(r'[/-]', '', result_appoint[sid][appoint_item['dt_appoint']])
			# 協会けんぽ用に数字に変換（受診日の元号）
			if 'appointGengo' in appoint_item:
				result_appoint[sid][appoint_item['appointGengo']] = warekiGengo2num(result_appoint[sid][appoint_item['appointGengo']])
				# 生活習慣予防ツールの動作に合わせて、"年"の桁を2桁で調整
				result_appoint[sid][appoint_item['appointGengoY']] = '{:0>2}'.format(result_appoint[sid][appoint_item['appointGengoY']])

			# XMLツリー
			sid_appoint = str(row['sid'])
			#t_appo_me = sql.once('SELECT * FROM t_appoint_me where sid_morg = '+ config_data['sid_morg'] +' and sid_appoint = ' + sid_appoint + ';')
			t_appo_me = cmn.get_t_appoint_me(sid_appoint)
			if t_appo_me is None: continue

			try:	# TODO: xml_meに特殊記号(<>&など)が直接挿入されてXML解析失敗するパターンが存在する。その場合はスキップを行う
				xml_me = cmn.getRow2Xml(t_appo_me[0]['xml_me'])
			except Exception as err:
				log('xmlme err:{}'.format(err), LOG_ERR)
				err_sid_list.append({sid: {'sid_examinee': sid_examinee, 'msg': 'xml_me:'+str(err)}})
				continue
			#t_appo = sql.once('SELECT * FROM t_appoint where sid_morg = '+ config_data['sid_morg'] +' and sid = ' + sid_appoint + ';')
			t_appo = cmn.get_t_appoint(sid_appoint)
			if t_appo is None: continue
			xml_xorg = cmn.getRow2Xml(t_appo[0]['xml_xorg'])

			# 協会けんぽCSV出力のため、団体紐づけなしは強制スキップ
			if xml_xorg is None:
				log(' *** skip: xml_xorg is None', LOG_DBG)
				continue

			# 団体
			result_org = {}
			result_org[sid] = {}
			result_org_sid = None

			#result_org[sid], result_org_sid = get_org_data(xml_xorg, org_item)
			xmlOrgSid = getXmlSid.analyzeXmlOrgIndex(xml_xorg)
			result_org[sid] = cmn.get_org_data(xmlOrgSid)
			result_org_sid = result_org[sid]['org_sid'] if 'org_sid' in result_org[sid] else None

			if 'org_sid' in result_org[sid]: del result_org[sid]['org_sid']		# org_sidは団体絞り込みでしか使用しないため、ここで削除する
			if (cmn.check_abst_sts(result_org_sid, cond_org) == False):			# 団体情報が読めるのがこのタイミングなので、ここで絞り込み
				log(' *** reject org', LOG_DBG)
				continue

			# 協会けんぽツールで事業者記号は８桁で入力しないとエラーになるので、頭０埋めを行う
			if org_item['insurance_symbol'] in result_org[sid] and len(result_org[sid][org_item['insurance_symbol']]) < 8:
				result_org[sid][org_item['insurance_symbol']] = '{:0>8}'.format(result_org[sid][org_item['insurance_symbol']])

			# 保険者番号なしと、桁数がおかしいものはスキップ
			if org_item['insurer_number'] not in result_org[sid] or result_org[sid][org_item['insurer_number']] is None or len(result_org[sid][org_item['insurer_number']]) != 8:
				continue
			# 法別番号のチェック（契約団体番号の頭2文字が法別番号）
			if result_org[sid][org_item['insurer_number']][0:2] not in houbetsuNumber:
				continue
			# TODO: 生活習慣予防と事業者健診の判定が必要になるかもしれない。

			# 被保険者・被扶養者番号の変換
			if org_item['f_examinee'] in result_org[sid]:
				if result_org[sid][org_item['f_examinee']] == '0':			# 0：家族
					result_org[sid][org_item['f_examinee']] = '{:0>2}'.format('1')		# 0padding
				elif result_org[sid][org_item['f_examinee']] == '1':		# 1：本人
					result_org[sid][org_item['f_examinee']] = '{:0>2}'.format('0')
				elif result_org[sid][org_item['f_examinee']] == '2':		# 2：任意
					result_org[sid][org_item['f_examinee']] = '{:0>2}'.format('2')

			# xmlmeを参照したい人向けにXMLを解析してごにょごにょしたものを返す
			xmlmeConvList = [
				form_code['kyoukaikenpo']
				]
			# 参照する必要はあるけど、結果をごにょる必要がないのはここ
			xmlmeNoConvList = [
				#form_code['kyoukaikenpo']
			]

			# FIXME: 将来的にMEの解析／取得処理を変更したいので仮置き
			# 基準を取得するためのsidをXMLME内から漁る
			me2criterionSid = m_me.getXMLMEcriterion(t_appo_me[0]['xml_me'])
			# 基準の取得
			conf.m_criterion = m_criterion.getCriterionCourse(config_data['sid_morg'], meCriterionData=me2criterionSid)

			# xmlMeの解析／取得
			xmlMeSid = None
			xmlMeConvFlag = True if config_data['s_print'] in xmlmeConvList else False
			if config_data['s_print'] in xmlmeConvList or config_data['s_print'] in xmlmeNoConvList:
				xmlMeSid = kk.convXmlMeEelementKyoukaiKenpo(xml_me)
				#xmlMeSid = getXmlSid.analyzeXmlMeIndex(xml_me, resultConv=xmlMeConvFlag, f_elementsType='kyoukaikenpo') if xml_me is not None else None

			# 検査項目（標準／オプション）の受診状態の取得
			if xmlMeSid is not None:
				# conf.inspStdOptDataに格納される。戻り値を受け取ってもおｋ
				cmn.get_inspection_stdOpt_data(xmlMeSid)

			# 検査項目
			result_eitem = {}
			result_inspection = {}
			result_general = {}
			result_medi_cure = {}
			result_group_rank = {}
			inspection_sprint_list = [form_code['kyoukaikenpo']]
			if config_data['s_print'] in inspection_sprint_list:		# 検査結果
				result_eitem[sid] = {}
				result_inspection[sid] = {}
				result_general[sid] = {}
				result_medi_cure[sid] = {}
				result_group_rank[sid] = {}
				if xmlMeSid is not None:
					result_eitem[sid] = {k:xmlMeSid['eitems'][k]['result']['opinion'][kk] for k in xmlMeSid['eitems'] for kk in xmlMeSid['eitems'][k]['result']['opinion']}
					result_inspection[sid] = cmn.get_inspection_data(xmlMeSid, inspection_item, retSid=True)	# ここは「sid:結果」で貰う
					# データ取得失敗時に空になる
					if len(result_inspection[sid]) < 1:
						log('result_inspection data is None', LOG_ERR)
					# 治療中の取得
					#result_medi_cure[sid] = get_medi_cure_data(xmlMeSid, medi_cure_item)
					# 総合所見／判定の取得
					if int(appo_sts) > 1:	# 受付ステータスが判定済み以上を対象(予約／受付の場合は対象外)
						result_general[sid] = cmn.get_general_data(xmlMeSid, general_item, course_sid)
					# グループ判定／所見
					if int(appo_sts) > 0:	# 予約以上
						result_group_rank[sid] = cmn.get_groupRank_data(xmlMeSid, groupRank_item, retSid=True)

			del xml_me, xml_xorg, xmlMeSid			# 重たいxmlはここで捨てる

			# ここから下でデータの組み立て
			kk_data_dict = {
				'appoint':result_appoint[sid],
				'examinee':result_examinee[sid],
				'org':result_org[sid],
				'general':result_general[sid],
				'group':result_group_rank[sid],
				'eitem':result_eitem[sid],
				'inspection':result_inspection[sid],
				'inspectionItem': inspection_item,
				}

			# CSVへ出力するためのデータ
			csv_data_dict = {}
			try:
				csv_data_dict.update(getKKcsvDataItemVale(kk_data_dict))
			except Exception as err:
				log('data create error, errMsg: [{}], proc skip'.format(err), LOG_ERR)
				continue

			## 辞書に必要なものを追加
			## 予約情報(受診日)
			#if result_appoint is not None and sid in result_appoint and result_appoint[sid] is not None:
			#	csv_data_dict.update(result_appoint[sid])
			# 受診者情報
			#if result_examinee is not None and sid in result_examinee and result_examinee[sid] is not None:
			#	csv_data_dict.update(result_examinee[sid])
			## 総合判定／所見
			#if result_general is not None and sid in result_general and result_general[sid] is not None:
			#	csv_data_dict.update(result_general[sid])
			## グループ判定／所見
			#if result_group_rank is not None and sid in result_group_rank and result_group_rank[sid] is not None:
			#	if 'rank' in result_group_rank[sid] and result_group_rank[sid]['rank'] is not None: csv_data_dict.update(result_group_rank[sid]['rank'])
			#	# グループ判定所見
			#	if 'finding' in result_group_rank[sid] and result_group_rank[sid]['finding'] is not None: csv_data_dict.update(result_group_rank[sid]['finding'])
			#	if 'summary' in result_group_rank[sid] and result_group_rank[sid]['summary'] is not None: csv_data_dict.update(result_group_rank[sid]['summary'])
			## 治療中
			##if result_medi_cure is not None and sid in result_medi_cure and result_medi_cure[sid] is not None:
			##	csv_data_dict.update(result_medi_cure[sid])
			## 団体情報
			#if result_org is not None and sid in result_org and result_org[sid] is not None:
			#	csv_data_dict.update(result_org[sid])

			## 出力対象の帳票に合わせる
			## 検査結果
			#if config_data['s_print'] in inspection_sprint_list and result_inspection[sid] is not None:
			#	csv_data_dict.update(result_inspection[sid])
			## 問診
			##if config_data['s_print'] in interview_sprint_list and result_interview[sid] is not None:
			##	csv_data_dict.update(result_interview[sid])

			csv_data.append(csv_data_dict)

			total_cnt += 1

			del csv_data_dict	# ループ用に削除

		# 受診者データ取得/解析終了
		conf.examInfo['sid'] = None
		conf.examInfo['sid_examinee'] = None

		# 処理件数0件はCSV出力を行わないので、終わり
		if total_cnt == 1:	# 1-origin
			msg = 'no proc data'
			if len(err_sid_list) > 0: msg += ', msg: {}'.format(err_sid_list)	# もしエラーがあればメッセージに結合
			cmn._exit('success', '{}'.format(msg))

		# ここからCSV出力用の処理
		csv_config = cmn.get_csv_format(csv_option)
		csv.register_dialect('daidai', delimiter=csv_config['delimiter'], doublequote=csv_config['doublequote'], lineterminator=csv_config['terminated'], quoting=csv_config['quoting'])

		# CSVデータ部のヘッダ作成
		csv_header = [k['@physicalName'] for k in csvDataItemDict['item']]
		#csv_header = cmn.head_add(list(examinee_item.values()), csv_header)				# 受診者情報は固定出力
		#csv_header = cmn.head_add(list(appoint_item.values()), csv_header)				# 予約情報は固定出力
		#csv_header = cmn.head_add(list(org_item.values()), csv_header)					# 団体が登録されていると必ず出力されるので、固定
		# 検査結果リスト
		#if config_data['s_print'] in inspection_sprint_list:
		#	if inspection_item is not None: csv_header = cmn.head_add(list(inspection_item.values()), csv_header)		# 検査項目
		#	if general_item is not None: csv_header = cmn.head_add(list(general_item.values()), csv_header)				# 総合判定／総合所見／確定医師名
		#	if groupRank_item is not None:	# グループ判定
		#		csv_header = cmn.head_add(list({k:groupRank_item[k]+'_rank' for k in groupRank_item}.values()), csv_header)				# ランク
		#		csv_header = cmn.head_add(list({k:groupRank_item[k]+'_finding' for k in groupRank_item}.values()), csv_header)			# 所見
		#		csv_header = cmn.head_add('groupRankSummary', csv_header)						# TODO: グループ所見まとめ用のCSVヘッダ名称はソース固定。直すときは検索忘れずに

		# 漢字のソートはアレなので、カナでソートをかける。ただし、未入力者のデータはNoneであることに注意。（ソート時に先頭になるのか、末尾になるのか。。。）
		# ただし、ソートしたいデータにkanaがいない場合はnameのまま
		if conf.convert_option['f_kana_sort'] == '1' and sort_code['examinee'] in config_data['sort_condition'] and examinee_item['name-kana'] in csv_data:
			config_data['sort_condition'][sort_code['examinee']]['key'] = examinee_item['name-kana']

		# CSVデータのソートを行う
		sort_data = cmn.get_csv_sort_data(csv_data, csv_config, sort_cond)

		# tempfile.mkstemp(suffix=None, prefix=None, dir=None, text=False)			# これで作成した一時ファイルは自動で削除されない
		fobj = tempfile.mkstemp(suffix=out_file_suffix, prefix=out_file_prefix, text=False)		# tmpdirはシステムお任せ。ゴミが残ってもOSのポリシーに基づいて削除して貰う
		tmp_file_path = pl.PurePath(fobj[1])
		tmp_file = pl.Path(tmp_file_path)

		# 辞書型のデータを書き込む。ヘッダを参照して該当ヘッダの列に対応するデータを入れてくれるので位置が確定できる
		# 文字化けは？にしてみるテスト
		codecs.register_error('hoge', lambda e: ('?', e.end))
		#with open(tmp_file.resolve(), mode='r+', newline='', encoding=csv_config['encoding'], errors='hoge') as f:
		with open(tmp_file.resolve(), mode='r+', newline='', encoding='UTF-8', errors='hoge') as f:
			# 生活習慣予防の場合、頭に１行必要

			if conf.form_code_subType['20030201'] is not None:
				fp = csv.writer(f, dialect='daidai')
				fp.writerow(['','','','',''])

			# CSVのフォーマットにヘッダ指定
			# TODO: ヘッダに無いデータはエラーにせず無視する(出力しない)(extrasaction='ignore')
			fp = csv.DictWriter(f, dialect='daidai', fieldnames=csv_header, extrasaction='ignore')

			# ヘッダの書き込み
			if 'f_csvHeader' in conf.outsource_config['root']['outsource']['condition'] and conf.outsource_config['root']['outsource']['condition']['f_csvHeader'] == '1':
				fp.writeheader()

			# ソート済みデータを書き込む
			for line in sort_data:
				try:
					fp.writerow(line)
				except Exception as err:
					log('write error : {}'.format(err))

		csv_file_name = tmp_file.name

		log('Number of data: {0}'.format(total_cnt - 1))
		if total_cnt == 1:				# 絞り込みを行った結果、対象者０なら終わり(カウンタの初期は１)
			cmn.file_del(tmp_file)		# 一時ファイルが存在するなら削除
			cmn._exit('success', 'no data')

		# javascript側でこのキーワードを検索してファイル名を特定する
		msg2js('{0}{1}'.format(config_data['output_search_word'], csv_file_name))

	except Exception as err:
		cmn.file_del(tmp_file)	# こけたときにtmpfileが存在したら削除を試みる
		cmn.traceback_log(err)

	finally:
		# MySqlセッション終了
		sql.close()

def main():
	xml_outsource = None

	# sm_morgを取得
	row = cmn.get_sm_morg()
	if row is None: cmn._exit('sql_error', '[sm_morg] sid not found')
	if len(row) < 1: cmn._exit('sql_error', '[sm_morg] get failed')
	if len(row) > 1: cmn._exit('sql_error', '[sm_morg] duplicate: {}'.format(len(row)))
	try:
		ret = cmn.getXmlCstmInfo(row[0]['xml_cstminfo'])
		if ret == False: raise ValueError()
	except Exception as err:
		log('xml_cstminfo error:{}'.format(err))
		cmn._exit('xml_error', '[xml_cstminfo] xml convert failed')
	del row

	# 医療機関個別のm_outsourceを取得
	row = cmn.get_m_outsource(sid_section=config_data['sid_section'], sid=config_data['outsouceSid'])
	if row is None:
		# m_outsourceが見つからない
		cmn._exit('sql_error', '[m_outsource] sid_section not found')
	if len(row) != 1:
		# m_outsourceの取得失敗。返却されるのは1個を期待している
		cmn._exit('sql_error', '[m_outsource] get failed: SQL return rows Len:{}'.format(len(row)))
	try:
		xml_outsource = cmn.getXmlOutsource(row[0]['xml_outsource'])
	except Exception as err:
		log('m_outsoucr error:{}'.format(err))
		cmn._exit('xml_error', '[m_outsource] xml convert failed')




	# ベースとなるm_outsourceを特定して取得
	if 'form_code_subType' in conf.outsource_config['root']['outsource']['condition']:
		subFormCode = None
		if 'subCode' in conf.outsource_config['root']['outsource']['condition']['form_code_subType']:
			subFormCode = conf.outsource_config['root']['outsource']['condition']['form_code_subType']['subCode']
		else:
			subFormCode = conf.outsource_config['root']['outsource']['condition']['form_code_subType']

		if subFormCode == '20030204':
			kyoukaikenpo_shikakusya_list.outputcsv(config_data)
		else:

			row = cmn.get_m_outsource(sid_section=config_data['sid_section'], sid=None, sid_morg='0', subFormCode=subFormCode)
			if row is None:
				# m_outsourceが見つからない
				cmn._exit('sql_error', '[m_outsource base] sid_section not found')
			if len(row) != 1:
				# m_outsourceの取得失敗。返却されるのは1個を期待している
				cmn._exit('sql_error', '[m_outsource base] get failed: SQL return rows Len:{}'.format(len(row)))
			try:
				xml_outsource = cmn.getXmlOutsource(row[0]['xml_outsource'])
			except Exception as err:
				log('m_outsoucr error:{}'.format(err))
				cmn._exit('xml_error', '[m_outsource base] xml convert failed')
			del row
			if xml_outsource is None: cmn._exit('sql_error', '[m_outsource] get failed')		# m_outsourceの取得失敗

			create_kyoukaikenpo(xml_outsource)

if __name__ == '__main__':
	#### デバッグ専用：使うときにコメント解除 ####
	## VSCode ver1.27.1がサポートしているptvsdのバージョンは「4.1.1」
	#import ptvsd
	#log('!!!! enable ptvsd !!!!')
	#ptvsd.enable_attach(address=('0.0.0.0', 3000), redirect_output=True)
	#ptvsd.wait_for_attach()
	#### ここまでデバッグ専用：未使用時はコメントアウト ####


	# 引数の解析
	config_data = cmn.args2config(sys.argv)

	if len(config_data) > 0:
		start = time.time()
		main()
		elapsed_time = time.time() - start
		log('elapsed_time: {:.3f} sec'.format(elapsed_time))	# 実行時間表示
		cmn._exit('success')		# 終わり


	else:
		cmn._exit('error')		# エラー

	cmn._exit('exit')				# 終わり

