#!/usr/bin/python3

# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4
#
# getXmlSid.pyから分割。

import re
import jaconv

import form_tools_py.conf as conf
import form_tools_py.common as cmn
import form_tools_py.read_i18n_translation as ri18n

################################
log = cmn.Log().log
dbg_log = cmn.Log().dbg_log
sql = cmn.Sql()
################################
LOG_NOTICE = cmn.LOG_NOTICE
LOG_INFO = cmn.LOG_INFO
LOG_WARN = cmn.LOG_WARN
LOG_ERR = cmn.LOG_ERR
LOG_DBG = cmn.LOG_DBG

## nodeコマンドでjsをワンライナー実行して結果取得後に処理を分ける
def procRun(cmd):
	ret = None
	if cmd is None or len(cmd)<1: return None
	import subprocess

	ptTrue = re.compile(r'[tT][rR][uU][eE]')
	ptFalse = re.compile(r'[fF][aA][lL][sS][eE]')

	try:
		proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		log('outside cmd execution: [cmd={}], [code={}], [stdout={}]'.format(cmd, proc.returncode, proc.stdout), LOG_DBG)
		if proc.returncode != 0:
			log('outside cmd return error: {}'.format(proc.stderr.decode('UTF-8')), LOG_ERR)
		procRet = proc.stdout.decode('UTF-8')
		if ptTrue.search(procRet):
			ret = '1'
		elif ptFalse.search(procRet):
			ret = '0'
		else:
			ret = procRet
	except Exception as err:
		log('outside cmd failed: [{}], [msg={}]'.format(err.__class__.__name__, err), LOG_ERR)

	return ret

# 特定健診向けの変換
def convXmlMeEelementTokuteiKenshin(rdata, courseSid):
	if rdata is None or courseSid is None: return None

	import form_tools_py.getXmlSid as getXmlSid

	# 日本語で出力(固定)
	sid_locale = '140001'
	global langList
	# 言語マスタ取得
	langList = geti18ndictionary(sid_locale)

	# 改行置換用
	convbreak = re.compile(r"\n+")

	# 定性値(Qualitative value)チェック用
	ptQv1 = re.compile(r"[-]")
	ptQv2 = re.compile(r"(\+-|±)")
	ptQv3 = re.compile(r"([+]{1}|1\+)")
	ptQv4 = re.compile(r"([+]{2}|2\+)")
	ptQv5 = re.compile(r"([+]{3}|3\+)")
	ptQv6 = re.compile(r"([+]{4,6}|4\+|5\+|6|\+)")

	# 「**:結果なし」、「***:未実施」、「****:測定不能」を意味する記号を入力された場合のチェック用
	ptNoKekka = re.compile(r"^[*]{2}$|^[\-]{2}$")
	ptMiJissi = re.compile(r"^[*]{3}$|^[\-]{3}$")
	ptSokuHunou =  re.compile(r"^[*]{4}$|^[\-]{4}$")

	m_criterion = {}
	data = {}
	# 単選択で値を表示するもの
	tandata = ['726','5','695','1332401','7061001','1390501','2390701','200603','200703','200803']
	# 既往歴　脳血管
	noudata = ['30001511','30001512','30001513','30001514']
	# 既往歴　心血管
	sindata = ['30001529','30001530','30001531','30001532','30001533']
	# 既往歴　腎不全
	jindata = ['30001574']
	# 所見系まとめ
	shokenlist = {
	'頭部MRI・MRA所見'		:'90111',
	'心電図所見'					: '549',
	'ホルター心電図所見'		: '921',
	'負荷心電図所見'		: '1390801',
	'腹部超音波所見'		: '750',
	'胸部Ｘ線所見'				:'557',
	'胸部CT所見'			:'941',
	'大腸内視鏡所見'		:'664',
	'腹部CT所見'			:'1440101',
	'マンモグラフィー所見'		:'672',
	'Carotid ultrasonograph'	:'90161'	#頸動脈超音波
	}

	# valueを持つsidをリストアップ
	m_criterion['criterion'] = {rdata[k]['sid']:rdata[k]['sid_criterion'] for k in rdata if 'value' in rdata[k]['result']}
	for sid in m_criterion['criterion']:
		data[sid] = getXmlSid.getXmlCriterion(m_criterion['criterion'][sid], s_exam='1005')	# s_exam=1005は項目要素

	for sid in m_criterion['criterion']:
		dataCriterion = data[sid]['criterion'][m_criterion['criterion'][sid]]
		val = rdata[sid]['result']['value']
		if val is None or len(val.strip()) < 1: continue
		# 出力が数値
		if dataCriterion['output-format'] == '1':
			decDigit = dataCriterion['number-value']['dec-digit']
			val = cmn.numeric2conv(val, decDigit)	#数値判定で数値じゃない場合は値がそのまま帰ってくるので、"測定不能""未実施処理"を行う
			# 「**:結果なし」が入力されていたらvalを"測定不能"にする
			if ptNoKekka.match(val) or val == '結果なし':
				val = '測定不能'
			#	「****:未実施」が入力されていたらvalを"未実施"にする
			elif ptMiJissi.match(val) or val == '未実施':
				val = '未実施'
			#	「****:測定不能」が入力されていたらvalを"測定不能"にする
			elif ptSokuHunou.match(val) or val == '測定不能':
				val = '測定不能'

			rdata[sid]['result']['value'] = str(val)

		# 出力が定性
		elif dataCriterion['output-format'] == '2':
			if val in ['91070']:		# 「91070:検出せず」はvalを"測定不能"にする
				val = '測定不能'
			elif val in ['91080']:		# 「91080:結果なし」はvalを"未実施"にする
				val = '未実施'
			elif val in ['91090']:		# 「91090:未検査」はvalを"未実施"にする(追加)
				val = '未実施'
			elif val in ['normal']:		#	成田では定性のところに文字がくる場合があるので、空白に変換(一時対応)
				val = '測定不能'
			elif val in ['abnormal']:	#	成田では定性のところに文字がくる場合があるので、空白に変換(一時対応)
				val = '測定不能'
			elif val in ['キャンセル']:	#	成田では定性のところに文字がくる場合があるので、未実施に変換(一時対応)
				val = '未実施'
			elif val in ['検査中']:		#	成田では定性のところに文字がくる場合があるので、未実施に変換(一時対応)
				val = '未実施'
			elif val in ['未到着']:		#	成田では定性のところに文字がくる場合があるので、未実施に変換(一時対応)
				val = '未実施'

			else:
				qsid = dataCriterion['qualitative']['sid']
				if qsid not in conf.m_qualitative or conf.m_qualitative[qsid] is None:	# 定性値のリストをチェック、存在しなければ追加していく
					tmp = getXmlSid.getXmlQualitative(qsid)
					conf.m_qualitative[qsid] = tmp['qualitative'][qsid]
					conf.m_qualitative[qsid] = {conf.m_qualitative[qsid][k]['value']: conf.m_qualitative[qsid][k]['caption'] for k in conf.m_qualitative[qsid] if k.isdigit()}
				val = re.sub(r"[\(\)]", '', cmn.Zenkaku2Hankaku().zen2han(conf.m_qualitative[qsid][val]))	# Unicodeの正規化を行っておく
				if ptQv1.match(val): val = '-'			# 1:-
				elif ptQv2.match(val): val = '+-'		# 2:+-
				elif ptQv3.match(val): val = '1+'		# 3:1+
				elif ptQv4.match(val): val = '2+'		# 4:2+
				elif ptQv5.match(val): val = '3+'		# 5:3+
				elif ptQv6.match(val):					# 6:3+を超えるもの
					if sid == '473':	# 尿潜血は4+まである
						val = '4+'
					else:				# 上記以外は3+にまるめる
						val = '3+'

			rdata[sid]['result']['value'] = val
		# 出力が文字
		elif dataCriterion['output-format'] == '3':
			#言語変換を入れる所
			if checkComment(val):
				val = convComment(val)
			if checkComment(dataCriterion['name']):
				name = convComment(dataCriterion['name'])
				name =  jaconv.h2z(name, kana=True, ascii=True, digit=True)	# 半角は全て全角へ変換
			# 入力が 1:単文、2:複文
			if dataCriterion['input-style'] in ['1', '2']:
				#言語変換を入れる所
				if checkComment(val):
					val = convComment(val)
				val = convbreak.sub(r"　", val.strip())						# 改行文字は全角スペースに置換

				val = jaconv.h2z(val, kana=True, ascii=True, digit=True)	# 半角は全て全角へ変換

				#成田用　心電図所見2～10が来た場合は所見1にまとめる
		#		if '心電図所見' in dataCriterion['name'] and sid != '549':
		#			rdata['549']['result']['value'] = rdata['549']['result']['value'] + '　' + val
		#		else:
		#			rdata[sid]['result']['value'] = val
				shoken_name = dataCriterion['name'][:-1]

				if shoken_name in shokenlist.keys():
					try:
						if sid != shokenlist[shoken_name]:
							shokensid = shokenlist[shoken_name]
							rdata[shokensid]['result']['value'] = rdata[shokensid]['result']['value'] + '　' + val
						else:
							rdata[sid]['result']['value'] = val
					except Exception as err:
							log('create value list: esid: {}, msg: {}'.format(sid, err), LOG_ERR)

			# 入力が 3:単選択、4:複選択、6:論理
			elif dataCriterion['input-style'] in ['3', '4', '5', '6']:
				if 'char-value' not in dataCriterion:
					log('esid: {}, intput: {}, output: {}, char-value tag nothing'.format(sid, dataCriterion['input-style'], dataCriterion['output-format']), LOG_WARN)
				else:
					try:
						valItem = {dataCriterion['char-value'][k]['value']:dataCriterion['char-value'][k]['caption'] for k in dataCriterion['char-value']}
					except Exception as err:
						log('create value list: esid: {}, msg: {}'.format(sid, err), LOG_ERR)
					# 3:単選択、4:複選択
					# TODO: 複選択はないものと扱う
					if dataCriterion['input-style'] in ['3', '4', '6']:
						try:
							if '::' in val:
								conv_val = None
								sep_list = val.split('::')
								for k in range(len(sep_list)):
									if conv_val is None or conv_val < sep_list[k]:
										conv_val = sep_list[k]

								val =conv_val
							if val in valItem and dataCriterion['s_exam'] in ['1005']:		# 1005:要素
								if '92001' == val or '001' == val: val = '1'
								elif '92002' == val or '002' == val: val = '2'
								elif '92003' == val or '003' == val: val = '3'
								elif '92004' == val or '004' == val: val = '4'
								elif '92005' == val or '005' == val: val = '5'
								elif '92006' == val or '006' == val: val = '6'
								#選択した値をそのまま出すものもある
								elif sid in tandata:
									val = valItem[val]

							#成田用　各既往歴が分かれているのでまとめる 一つでもあれば値に１を設定
							#既往歴30001512　に選択肢の文言をまとめる。
							if sid in noudata and val is not None:
								if val == '4':
									rdata['30001511']['result']['value'] = '1'
									if 'value' in rdata['30001512']['result']:
										rdata['30001512']['result']['value'] = rdata['30001512']['result']['value'] + '　' + name
									else:
										rdata['30001512']['result']['value'] = name
							elif sid in sindata and val is not None:
								if val == '4':
									rdata['30001529']['result']['value'] = '1'
									if 'value' in rdata['30001512']['result']:
										rdata['30001512']['result']['value'] = rdata['30001512']['result']['value'] + '　' + name
									else:
										rdata['30001512']['result']['value'] = name
							elif sid in jindata and val is not None:
								if val == '4':
									rdata['30001570']['result']['value'] = '1'
									if 'value' in rdata['30001512']['result']:
										rdata['30001512']['result']['value'] = rdata['30001512']['result']['value'] + '　' + name
									else:
										rdata['30001512']['result']['value'] = name
							elif '300013' in sid and val is not None and val == '1':
								if 'value' in rdata['30001301']['result']:
									rdata['30001301']['result']['value'] = rdata['30001301']['result']['value'] + '　' + name
								else:
									rdata['30001301']['result']['value'] = name

							else:
								rdata[sid]['result']['value'] = val
						except Exception as err:
							log('create value list: esid: {}, msg: {}'.format(sid, err), LOG_ERR)
					# 入力が 5:演算
					elif dataCriterion['input-style'] == '5':
						# captionを出力
						val = val #searchTransCode(valItem, val, mode=dataCriterion['input-style'])
						rdata[sid]['result']['value'] = val

			else:
				# TODO: 検討が必要かも
				log('sid_criterion: {}, input-style undefined: {}'.format(sid, dataCriterion['input-style']), LOG_DBG)

		else:
			log('output-format undefined: {}'.format(dataCriterion['output-format']), LOG_WARN)

	# 成田用　眼底は項目ごとに１枠にまとめる
	if '2390302' in rdata and 'value' in rdata['2390302']['result'] and rdata['2390302']['result']['value'] is not None:
		if '2390301' in rdata and 'value' in rdata['2390301']['result'] and rdata['2390301']['result']['value'] < rdata['2390302']['result']['value']:
			rdata['2390301']['result']['value'] = rdata['2390302']['result']['value']
	if '2390402' in rdata and 'value' in rdata['2390402']['result'] and rdata['2390402']['result']['value'] is not None:
		if '2390401' in rdata and 'value' in rdata['2390401']['result'] and rdata['2390401']['result']['value'] < rdata['2390402']['result']['value']:
			rdata['2390401']['result']['value'] = rdata['2390402']['result']['value']

	return rdata


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

	try:
		# 改行で分割
		arr = target.splitlines()

		for i in range(len(arr)):
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

# 言語マスタ取得
def geti18ndictionary(sid_locale):
	try:
		query = 'SELECT * FROM m_i18n_dictionary where sid_morg = 0 and sid_locale = ' + sid_locale + ';'
		rows = cmn.get_sql_query(query)

	except Exception as err:
		log('error', '{}'.format(err))
		raise

	return rows

