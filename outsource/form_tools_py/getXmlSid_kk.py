#!/usr/bin/python3

# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4
#
# getXmlSid.pyから分割。
# そろそろimport時の循環参照で混乱してきそう。クラス型プログラムにしてかつパッケージ化の勉強もした方がいいのだろうか。
# コードの量が増える前にどこかで対策を考えたほうがいいんだろな。

import re
import jaconv

import form_tools_py.conf as conf
import form_tools_py.common as cmn

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

## m_criterionの判定式をごにょる。現状、聴力でしか確認していないのでこのまま使い回しは不可
def getCriterionEitemResult(result, fsid_exam, esid_exam):
	import shlex
	import form_tools_py.getXmlSid as getXmlSid

	ret = None
	convAmp = re.compile(r'&amp;')		# &
	convLt = re.compile(r'&lt;')		# <
	convGt = re.compile(r'&gt;')		# >
	delStr = re.compile(r'\$')			# delete

	courseSid = list(conf.m_criterion.keys(),)[0]

	# エスケープ文字列を変換
	def convertSymbol(expJs):
		ret = expJs
		ret = convAmp.sub(r'&', ret)
		ret = convLt.sub(r'<', ret)
		ret = convGt.sub(r'>', ret)
		return ret

	# TODO: 判定式に完全対応はしてない。要素に合致する式を１個だけ抽出して判定を行う
	def convertStr2JsVariable(result, exp, fsid_exam, esid_exam):
		if result is None or exp is None or len(result) < 1 or len(exp) < 1 or result in ['?']: return None
		data = {}
		sidExp = ''
		ret = ''
		ptEsid = re.compile(r'\$E[0-9]+\.value[\x20]+([<>=]+)[\x20]+([0-9]+)')		# 「$E194.value <= 30」みたいな条件で検索する
		ptEsid2 = re.compile(r'E[0-9]+')
		ptSid = re.compile(r'(E)([0-9]+)')
		delSymbol = re.compile(r'\$|\.value')
		cnvSymbol1 = re.compile(r'&&')
		cnvSymbol2 = re.compile(r'\|\|')

		# この形で作成して返却する
		# 'var E194={value:30}, E195={value:30}, E196={value:30}, E197={value:30};'
		expSub = cnvSymbol2.sub(' or ', cnvSymbol1.sub(' and ', delSymbol.sub('', exp)))
		items = ptEsid2.findall(expSub)
		for item in items:
			item2 = ptSid.search(item)
			if 'E' == item2.group(1):
				try:
					sid = item2.group(2)

					#data[sid] = result[sid]['result']['value']
					# 変数の動的定義
					# https://qiita.com/kammultica/items/3201f43eec53e3e56f54
					itemVal = result.find('.//element[sid="{}"]/result/value'.format(sid)).text
					exec('{} = {}'.format(item2.string, itemVal))

				except:
					return None

		# 下みたいな形になるように変更する
		# ($E194.value <= 30 && $E195.value <= 30) || ($E196.value <= 30 && $E197.value <= 30)
		# (E194 <= 30 and $E195 <= 30) or (E196 <= 30 and E197 <= 30)

		# 「(式１) or (式２)」とか「(式１) and (式２)」 の単純な式になっている前提で処理する
		# TODO: 複雑な条件式が設定されている場合、期待通りに動作しません
		retSp = None
		for sp in re.split(r'\)', expSub):
			if esid_exam in sp:
				# 次の判定式の開始「(」までを削除
				expSubSp = re.sub(r'.*\(', '', sp)
				# esid_examが含まれる判定式でチェックを行う
				try:
					retSp = eval(expSubSp)
				except Exception as err:
					log('proc exp error: [{}], [msg={}]'.format(err.__class__.__name__, err), LOG_ERR)
		if retSp is not None:
			ret = retSp
		else:
			ret = eval(expSub)

		return ret

	# OLD
	#m_criterion = [conf.m_criterion[k]['egroup'] for k in conf.m_criterion][0]
	#m_criterionEitem = {gsid:{fsid:m_criterion[gsid][kk]['eitem'][fsid][kkk]} for gsid in m_criterion for kk in m_criterion[gsid] if 'eitem' in m_criterion[gsid][kk] for fsid in m_criterion[gsid][kk]['eitem'] if fsid==fsid_exam for kkk in m_criterion[gsid][kk]['eitem'][fsid]}
	#opinion = {keyId:m_criterionEitem[gsid][fsid][key][keyId] for gsid in m_criterionEitem for fsid in m_criterionEitem[gsid] for key in m_criterionEitem[gsid][fsid] if key=='opinion-condition' for keyId in m_criterionEitem[gsid][fsid][key] if type(m_criterionEitem[gsid][fsid][key][keyId])!=type(None) and 'opinion' in m_criterionEitem[gsid][fsid][key][keyId]}

	# NEW
	#m_criterionEitem = conf.m_criterion[courseSid]['eitem'][fsid_exam]
	m_criterion = conf.m_criterion[courseSid]['eitem'][fsid_exam]['raw']['xml_criterion']
	#m_criterionEitem = {sid:getXmlSid.getXmlCriterionSid(cmn.getRow2Xml(item['raw']['xml_criterion']).find('./criterion')) for sid,item in m_criterion.items()}
	m_criterionEitem = getXmlSid.getXmlCriterionSid(cmn.getRow2Xml(m_criterion).find('./criterion'))['criterion']
	m_criterionEitem = [k for k in m_criterionEitem.values()][0]
	outputKey = result.find('.//element[sid="{}"]/result/opinions/opinion/rank-output-key'.format(esid_exam)).text

	opinion = m_criterionEitem['opinion-condition'][outputKey]['opinion']
	for key,val in opinion.items():
		if 'code' in val and val['code'] == '90002':
			exp = convertSymbol(val['exp'])
			ret = convertStr2JsVariable(result, exp, fsid_exam, esid_exam)
			#convVar = 'var E194={value:30}, E195={value:30}, E196={value:30}, E197={value:30};'
			#cmdNode = shlex.split('env node -p "{} {}"'.format(convVar, delStr.sub('',convExp)))
			#ret = procRun(cmdNode)

	return ret

# 協会けんぽ向けの変換
def convXmlMeEelementKyoukaiKenpo(xmlObj):
	if xmlObj is None: return None

	import form_tools_py.getXmlSid as getXmlSid

	# コースSID
	courseSid = xmlObj.find('./ecourse/sid_criterion').text
	sieMd = xmlObj.find('./ecourse/sid').text

	# 総合判定用に格納
	totalRanksetSid = cmn.getRow2Xml(conf.m_criterion[courseSid]['course'][sieMd]['xml_criterion']).find('./criterion/total-rankset/sid').text
	conf.m_opinion_rankset['total'] = getXmlSid.getXmlRankset(totalRanksetSid)['rankset'][totalRanksetSid]
	# グループ判定用に格納
	groupRanksetSid = cmn.getRow2Xml(conf.m_criterion[courseSid]['course'][sieMd]['xml_criterion']).find('./criterion/group-rankset/sid').text
	conf.m_opinion_rankset['group'] = getXmlSid.getXmlRankset(groupRanksetSid)['rankset'][groupRanksetSid]

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
	ptNoKekka = re.compile(r"^[*]{2,4}$|^[\-]{2,4}$")

	# 白血球の基準に入力されている単位の文字を削除する用
	ptWbcUnit1 = re.compile(r"[／/]*[μｕＵuU][ｌＬlL]")			# ul | /ul

	m_criterion = {}
	data = {}
	retData = {}

	# valueを持つsidをリストアップ
	#m_criterion['criterion'] = {rdata[k]['sid']:rdata[k]['sid_criterion'] for k in rdata if 'value' in rdata[k]['result']}
	# XMLME内の検索
	m_criterion['criterion'] = {k.find('./sid').text:k.find('./sid_criterion').text for k in xmlObj.findall('.//element') if k.find('./result/value') is not None}
	# 基準取得
	for sid in m_criterion['criterion']:
		#data[sid] = getXmlSid.getXmlCriterion(m_criterion['criterion'][sid], s_exam='1005')	# s_exam=1005は項目要素
		if sid not in conf.m_criterion[courseSid]['element']:
			log('unknown sid_criterion: {}, Not obtained with m_criterion'.format(sid), LOG_ERR)
			continue
		data[sid] = getXmlSid.getXmlCriterionSid(cmn.getRow2Xml(conf.m_criterion[courseSid]['element'][sid]['raw']['xml_criterion']).find('./criterion'))

	for sid,sidCriterion in m_criterion['criterion'].items():
		if sid not in data:
			log('unknown sid: {}, Not obtained with data'.format(sid), LOG_WARN)
			continue
		if sidCriterion not in data[sid]['criterion']:
			log('unknown sidCriterion: {}, Not obtained with data[{}]'.format(sid, sidCriterion), LOG_WARN)
			continue
		dataCriterion = data[sid]['criterion'][sidCriterion]
		#val = rdata[sid]['result']['value']
		val = xmlObj.find('.//element[sid="{}"]/result/value'.format(sid)).text
		if val is None or len(val.strip()) < 1: continue
		# 出力が数値
		if dataCriterion['output-format'] == '1':
			decDigit = dataCriterion['number-value']['dec-digit']
			val = cmn.numeric2conv(val, decDigit)
			# 「**:結果なし」「***:未実施」「****:測定不能」が入力されていたらvalを"?"にする
			if ptNoKekka.match(val):
				val = '?'
			# TODO: 白血球(sid:377)は単位変換が必要になる場合もあるので、ここで個別対応を行う
			elif sid == '377':
				if val.replace('.', '').isnumeric():			# 全て数字かチェック。
					try:
						val = float(re.sub(r'[.]+', '.', val))		# 小数点の入力ミスチェック（連続は丸める）。そのあとfloatへ
					except:
						log('unit convert check failed [sid:{}]'.format(sid), LOG_ERR)
						pass
					unitStr = ptWbcUnit1.sub('', dataCriterion['number-value']['unit'])		# 単位の文字削除
					if len(unitStr) < 1:					# 「1/ul」=>「100/mm3」
						val = cmn.numeric2conv(val * 0.01, '2')
					elif unitStr in ['10**2', '10^2']:		# 「100/ul」=>「100/mm3」で協会けんぽツールと同じ単位なので何もしない
						pass
					elif unitStr in ['10**3', '10^3']:		# 「1000/ul」=>「100/mm3」
						val = cmn.numeric2conv(val * 10, '2')
					elif unitStr in ['10**4', '10^4']:		# 「10000/ul」=>「100/mm3」
						val = cmn.numeric2conv(val * 100, '2')
			# 聴力は数値ではなく、所見あり／なしで出す必要がある
			# この対応は念のため対応。本当はやりたくない。協会けんぽのコース基準作成時点で「所見あり／なし」で組んでおくべき
			elif sid in ['194','195','196','197']:
				jsExpChk = getCriterionEitemResult(xmlObj, fsid_exam='193', esid_exam=sid)
				# 判定結果（true）
				if jsExpChk == True or jsExpChk == '1':
					val = '1'				# "所見なし"に対応する文字を入れる
				# 判定結果（false）
				elif jsExpChk == False or jsExpChk == '0':
					val = '2'				# "所見あり"に対応する文字を入れる
				else:
					val = '?'				# 設定不能

			#rdata[sid]['result']['value'] = str(val)
			xmlObj.find('.//element[sid="{}"]/result/value'.format(sid)).text = str(val)

		# 出力が定性
		elif dataCriterion['output-format'] == '2':
			if val in ['91070', '91080']:		# 「91070:検出せず」と「91080:結果なし」はvalを"?"にする
				val = '?'
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

			#rdata[sid]['result']['value'] = val
			xmlObj.find('.//element[sid="{}"]/result/value'.format(sid)).text = str(val)
		# 出力が文字
		elif dataCriterion['output-format'] == '3':
			# 入力が 1:単文、2:複文
			if dataCriterion['input-style'] in ['1', '2']:
				val = convbreak.sub(r"　", val.strip())						# 改行文字は全角スペースに置換
				val = jaconv.h2z(val, kana=True, ascii=True, digit=True)	# 半角は全て全角へ変換
				#rdata[sid]['result']['value'] = val
				xmlObj.find('.//element[sid="{}"]/result/value'.format(sid)).text = str(val)

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
						if val in valItem and dataCriterion['s_exam'] in ['1005']:		# 1005:要素
							if '92001' == val: val = '1'
							elif '92002' == val: val = '2'
							elif '92003' == val: val = '3'
							elif '92004' == val: val = '4'
							elif '92005' == val: val = '5'
							elif '92006' == val: val = '6'
						#rdata[sid]['result']['value'] = val
						xmlObj.find('.//element[sid="{}"]/result/value'.format(sid)).text = str(val)
					# 入力が 5:演算
					elif dataCriterion['input-style'] == '5':
						# captionを出力
						#val = val #searchTransCode(valItem, val, mode=dataCriterion['input-style'])
						#rdata[sid]['result']['value'] = val
						pass

			else:
				# TODO: 検討が必要かも
				log('sid_criterion: {}, input-style undefined: {}'.format(sid, dataCriterion['input-style']), LOG_DBG)

		else:
			log('output-format undefined: {}'.format(dataCriterion['output-format']), LOG_WARN)

	retData.update(getXmlSid.getXmlMeSid(xmlObj.find('equipments')))

	convData = getXmlSid.getXmlMeSid(xmlObj.find('ecourse'))
	retData.update({'ecourse': getXmlSid.convXmlMeCourse(convData['ecourse'])})

	convData = getXmlSid.getXmlMeSid(xmlObj.find('egroups'))
	retData.update({'egroups': getXmlSid.convXmlMeGroup(convData['egroups'])})

	retData.update(getXmlSid.getXmlMeSid(xmlObj.find('eitems')))
	retData.update(getXmlSid.getXmlMeSid(xmlObj.find('elements')))

	return retData

