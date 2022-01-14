#!/usr/bin/python3

# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

import os
import sys
import xml.etree.ElementTree as ET
import pathlib
import re

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


################################

# くそーす
# XMLの中身を抽出して、辞書型にする。
# その際、配列になっているものはindexも入れておく
# 返却するデータはXMLそのものではないことに注意する
# ※ 返却データは呼び出し元で内包表記を利用することを意識して作成すること ※

# xmlオブジェクト内のlistで指定されたtagを「tag:text」にしたdict型で返却
# サブツリーの中までは解析しない
def xmlTagText2dict(xmlchild, tagList):
	data = {}
	if xmlchild is not None and tagList is not None:
		data = {xmlchild.find(k).tag:xmlchild.find(k).text for k in tagList if xmlchild.find(k) is not None}
		# eitemにf_intendedが存在しない場合、データ上「f_intended=None」を挿入する。元のXMLはいじらない
		if xmlchild.tag == 'eitem' and 'f_intended' not in data: data['f_intended'] = None

	return data

# xml_rankset(XML内)の検査項目／要素のindexを取得するのが目的
# sid(index)を元にXML内のデータを引くのに使う予定
def getXmlQualitativeSid(xmlobj):
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}

	child = list(xmlobj)
	cLen = len(child) if child is not None else 0

	itemList = ['sid', 'name']

	sid = xmlobj.find('sid').text if xmlobj.find('sid') is not None else None
	data[parent][sid] = xmlTagText2dict(xmlobj, itemList)

	tagIdx = {}
	for i in range(cLen):
		tagIdx[xmlobj[i].tag] = i

	if 'qualitative-values' in tagIdx and len(child[tagIdx['qualitative-values']]) > 0:
		qualitative = child[tagIdx['qualitative-values']].findall('qualitative-value')
		itemList = ['sid', 'value', 'caption', 'code']
		for i in range(len(qualitative)):
			key = qualitative[i].find('key').text if qualitative[i].find('key') is not None else None
			data[parent][sid][key] = {'idx': i}
			data[parent][sid][key].update(xmlTagText2dict(qualitative[i], itemList))

	return data

# xml_rankset(XML内)の検査項目／要素のindexを取得するのが目的
# sid(index)を元にXML内のデータを引くのに使う予定
def getXmlRanksetSid(xmlobj):
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}

	child = list(xmlobj)
	cLen = len(child) if child is not None else 0

	itemList = ['sid', 'tag', 'f_total']

	sid = xmlobj.find('sid').text if xmlobj.find('sid') is not None else None
	data[parent][sid] = xmlTagText2dict(xmlobj, itemList)

	tagIdx = {}
	for i in range(cLen):
		tagIdx[xmlobj[i].tag] = i

	if 'opinions' in tagIdx and len(child[tagIdx['opinions']]) > 0:
		opinions = child[tagIdx['opinions']].findall('opinion')
		itemList = ['code', 'order', 'name', 'exp', 'hi_key', 'lo_key']
		for i in range(len(opinions)):
			code = opinions[i].find('code').text if opinions[i].find('code') is not None else None
			data[parent][sid][code] = {'idx':i}
			data[parent][sid][code].update(xmlTagText2dict(opinions[i], itemList))

	return data

# m_criterion(XML内)の検査項目／要素のindexを取得するのが目的
# sid(index)を元にXML内のデータを引くのに使う予定
#@cmn.measure	# デバッグ専用
def getXmlCriterionSid(xmlobj):
	m_criterion = {}
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}

	child = list(xmlobj)
	cLen = len(child) if child is not None else 0

	itemList = ['sid', 's_criterion', 's_exam', 'name', 'title', 'abbr', 'output-format', 'input-style', 'price', 'rank-output-key']

	sid = xmlobj.find('sid').text if xmlobj.find('sid') is not None else None
	s_exam = xmlobj.find('s_exam').text if xmlobj.find('s_exam') is not None else None
	data[parent][sid] = xmlTagText2dict(xmlobj, itemList)

	tagIdx = {}
	for i in range(cLen):
		tagIdx[xmlobj[i].tag] = i

	# 総合判定
	if 'total-rankset' in tagIdx and len(child[tagIdx['total-rankset']]) > 0:
		ranksid = child[tagIdx['total-rankset']].find('sid').text if child[tagIdx['total-rankset']].find('sid') is not None else None
		data[parent][sid]['total-rankset'] = {'sid': ranksid}
	# グループ判定
	if 'group-rankset' in tagIdx and len(child[tagIdx['group-rankset']]) > 0:
		ranksid = child[tagIdx['group-rankset']].find('sid').text if child[tagIdx['group-rankset']].find('sid') is not None else None
		data[parent][sid]['group-rankset'] = {'sid': ranksid}
	# HiLowマーク
	if 'abnormal-marks' in tagIdx and len(child[tagIdx['abnormal-marks']]) > 0:
		mark = child[tagIdx['abnormal-marks']].findall('abnormal-mark')
		if mark is not None:
			data[parent][sid]['abnormal-mark'] = {}
			itemList = ['key', 'rank', 'finding']
			for i in range(len(mark)):
				key = mark[i].find('key').text if mark[i].find('key').tag == 'key' else None
				data[parent][sid]['abnormal-mark'][key] = xmlTagText2dict(mark[i], itemList)

	# opinions内の検索(グループ)
	if 'opinions' in tagIdx and len(child[tagIdx['opinions']]) > 0:
		opinions = child[tagIdx['opinions']].findall('opinion')
		itemList = ['key', 'target_code', 'code', 'rank-output-key', 'finding', 'exp']
		for i in range(len(opinions)):
			data[parent][sid] = xmlTagText2dict(opinions[i], itemList)

	# JLAC10コード
	if 'government-code' in tagIdx and len(child[tagIdx['government-code']]) > 0:
		governmentCode = child[tagIdx['government-code']]
		itemList = ['value', 'name']
		data[parent][sid]['government-code'] = xmlTagText2dict(governmentCode, itemList)

	# opinion-conditions(項目)
	if 'opinion-conditions' in tagIdx and len(child[tagIdx['opinion-conditions']]) > 0:
		conditions = child[tagIdx['opinion-conditions']].findall('opinion-condition')
		data[parent][sid]['opinion-condition'] = {}
		itemList = ['age-exp', 'key', 'sex']
		for i in range(len(conditions)):
			opinions = conditions[i].findall('opinions/opinion')
			key = conditions[i].find('key').text if conditions[i].find('key') is not None else None
			data[parent][sid]['opinion-condition'] = xmlTagText2dict(conditions[i], itemList)
			data[parent][sid]['opinion-condition'][key] = {}
			data[parent][sid]['opinion-condition'][key]['opinion'] = {}
			itemList = ['key', 'target_code', 'code', 'rank-output-key', 'finding', 'exp']
			for ii in range(len(opinions)):
				key2 = opinions[ii].find('key').text if opinions[ii].find('key') is not None else None
				data[parent][sid]['opinion-condition'][key]['opinion'][key2] = xmlTagText2dict(opinions[ii], itemList)

	# structures内の検索
	# FIXME: 改善したい
	if 'structures' in tagIdx and len(child[tagIdx['structures']]) > 0:
		elements = child[tagIdx['structures']].findall('structure/elements/element')
		eitems = child[tagIdx['structures']].findall('structure/eitems/eitem')
		egroups = child[tagIdx['structures']].findall('structure/egroups/egroup')
		epacks = child[tagIdx['structures']].findall('structure/epacks/epack')
		searchList = [elements, eitems, egroups, epacks]
		searchList = [x for x in searchList if x is not None and len(x)>0]		# XMLの要素なし(Noneとかtagなし)を排除してlist作り直し
		itemList = ['sid', 'sid_criterion']
		for searchItem in searchList:
			searchLen = len(searchItem)
			for i in range(searchLen):
				eparent = searchItem[i].tag
				if eparent not in data[parent][sid]:
					data[parent][sid][eparent] = {}
				esid = searchItem[i].find('sid').text if searchItem[i].find('sid') is not None else None
				data[parent][sid][eparent][esid] = xmlTagText2dict(searchItem[i], itemList)
				ei_criterion = searchItem[i].findall('criterions/criterion')
				eiLen = len(ei_criterion) if ei_criterion is not None else 0
				for ii in range(eiLen):
					c_sid = ei_criterion[ii].find('sid').text if ei_criterion[ii].find('sid') is not None else None
					data[parent][sid][eparent][esid][c_sid] = {'idx': ii, 'sid': c_sid}
					if s_exam in ['1001', '1003']:							# コースとグループの時だけ追加検索して、結合する
						if s_exam == '1001': target_s_exam = '1003'			# コースの場合は、グループを対象
						elif s_exam == '1003': target_s_exam = '1004'		# グループの場合は、項目を対象
						else: continue
						if eparent == 'epack': target_s_exam = '1002'		# パック。。。
						m_criterion = getXmlCriterion(c_sid, s_exam=target_s_exam, sid_exam=esid)
						if m_criterion is None:
							log('[{}(m_criterion sid:{})] get failed, structures[{}] esid[{}] criterionSid[{}]'.format(data[parent][sid]['name'], sid, eparent, esid, c_sid), LOG_WARN)
							continue
						data[parent][sid][eparent][esid][c_sid].update(m_criterion['criterion'][c_sid])

	# equipments内の検索
	if 'equipments' in tagIdx and len(child[tagIdx['equipments']]) > 0:
		equipments = child[tagIdx['equipments']].findall('equipments/equipment')
		itemList = ['s_equipment', 'count']
		for i in range(len(equipments)):
			data[parent][sid]['s_equipment'] = {'idx': i}
			data[parent][sid]['s_equipment'].update(xmlTagText2dict(equipments[i], itemList))

	# eorg内の検索
	if 'eorg' in tagIdx and len(child[tagIdx['eorg']]) > 0:
		eorgsid = child[tagIdx['eorg']].find('sid').text if child[tagIdx['eorg']].find('sid') is not None else None
		data[parent][sid]['eorg'] = {'sid': eorgsid}

	# number-value
	if 'number-value' in tagIdx and len(child[tagIdx['number-value']]) > 0:
		numberValue = child[tagIdx['number-value']]
		itemList = ['unit', 'int-digit', 'dec-digit', 'prescribed-value', 'lolimit-value', 'uplimit-value']
		if numberValue is not None:
			data[parent][sid]['number-value'] = xmlTagText2dict(numberValue, itemList)

	# char-values
	if 'char-values' in tagIdx and len(child[tagIdx['char-values']]) > 0:
		charValues = child[tagIdx['char-values']].findall('char-value')
		if charValues is not None:
			chaLen = len(charValues)
			data[parent][sid]['char-value'] = {}
			itemList = ['key', 'tag', 'value', 'caption', 'tags', 'asmkey', 'asmvalue']
			for i in range(chaLen):
				key = charValues[i].find('key').text if charValues[i].find('key') is not None else None
				data[parent][sid]['char-value'][key] = {'idx':i}
				data[parent][sid]['char-value'][key].update(xmlTagText2dict(charValues[i], itemList))

	# qualitative
	if 'qualitative' in tagIdx and len(child[tagIdx['qualitative']]) > 0:
		qsid = child[tagIdx['qualitative']].find('sid').text if child[tagIdx['qualitative']].find('sid').tag == 'sid' else None
		data[parent][sid]['qualitative'] = {'sid': qsid}

	return data

# 項目のxml_criterion(s_exam:1005)
def getXmlCriterionElement(xmlobj):
	data = {}
	if xmlobj is None: return None
	if xmlobj.find('s_exam').text != '1005': return None
	data = getXmlCriterionSid(xmlobj)
	return data

# 項目のxml_criterion(s_exam:1004)
def getXmlCriterionItem(xmlobj):
	data = {}
	if xmlobj is None: return None
	if xmlobj.find('s_exam').text != '1004': return None
	data = getXmlCriterionSid(xmlobj)
	return data

# グループのxml_criterion(s_exam:1003)
def getXmlCriterionGroup(xmlobj):
	data = {}
	if xmlobj is None: return None
	if xmlobj.find('s_exam').text != '1003': return None
	data = getXmlCriterionSid(xmlobj)
	return data

# パックのxml_criterion(s_exam:1002)
def getXmlCriterionPack(xmlobj):
	data = {}
	if xmlobj is None: return None
	if xmlobj.find('s_exam').text != '1002': return None
	data = getXmlCriterionSid(xmlobj)
	return data

# コースのxml_criterion(s_exam:1001)
def getXmlCriterionCource(xmlobj):
	data = {}
	if xmlobj is None: return None
	if xmlobj.find('s_exam').text != '1001': return None
	data = getXmlCriterionSid(xmlobj)
	return data

# xml_me(XML)内のresultタグの中身を抽出
#@cmn.measure	# デバッグ専用
def getXmlMeAnalyzeResult(result):
	data = {}

	if result is None:
		return None

	resultLen = len(result)
	if resultLen < 1:
		return None

	for i in range(resultLen):
		if result[i].tag == 'status':
			itemList = ['exam', 'opinion', 'finding']
			data['status'] = xmlTagText2dict(result[i], itemList)

		elif result[i].tag == 'opinions':
			opinion = result[i].findall('opinion') if result[i].findall('opinion') is not None else None
			opinionLen = len(opinion)
			data['opinion'] = {}
			itemList = ['rank-output-key', 'code', 'finding', 'manual', 'f_rank-output', 'exp', 'f_hilo', 'sid_doctor']
			for ii in range(opinionLen):
				val = xmlTagText2dict(opinion[ii], itemList)
				data['opinion'][val['rank-output-key']] = val

		elif result[i].tag == 'value':
			retVal = ''
			if result[i].text is not None: retVal = result[i].text.strip()
			data['value'] = retVal
		elif result[i].tag == 'code':
			retVal = ''
			if result[i].text is not None: retVal = result[i].text.strip()
			data['code'] = retVal

	return data

def getXmlExamineeSid(xmlobj):
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}

	itemList = [
		'sid',
		'f_examinee',
		'id',
		'name',
		'name-kana',
		'birthday',
		'sex',
		'bloodtype',
		'age-whenapo',
		'remarks',
		'my_number',
		'locale',
		'nationality',
		]
	sid = xmlobj.find('sid').text if xmlobj.find('sid') is not None else None
	data[parent][sid] = xmlTagText2dict(xmlobj, itemList)

	if xmlobj.find('contact') is not None:
		# contact
		contactList = [
			'contact/send_addr',
			'contact/tel',
			'contact/tel2',
			'contact/tel3',
			'contact/fax',
			'contact/email',
			'contact/zip1',
			'contact/address1',
			'contact/zip2',
			'contact/address2',
			'contact/zip3',
			'contact/address3',
			'contact/destination',
			]
		data[parent][sid]['contact'] = xmlTagText2dict(xmlobj, contactList)
		# contact/address
		if xmlobj.find('contact/address') is not None:
			addressList = [
				'contact/address/zip',
				'contact/address/adr1',
				'contact/address/adr2',
				'contact/address/adr3',
				'contact/address/adr4',
				]
			data[parent][sid]['contact']['address'] = xmlTagText2dict(xmlobj, addressList)

	return data

def getXmlAttributeSid(xmlobj):
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}

	child = list(xmlobj)
	cLen = len(child) if child is not None else 0

	# m_me_attribute
	# 補足：m_me_attributeは更新分のみが格納されている。このXMLの中にいない検査項目は必須扱いとなる
	#### XMLタグの意味
	#f_exam			# 必須／オプション項目 (1 = オプション、2 = 必須)
	#f_intended 	# 受診対象項目 (0 = 対象外、1 = 対象)

	itemList = ['sid', 'sid_criterion', 'f_intended', 's_exam', 'f_exam']
	for i in range(cLen):
		sid = child[i].find('sid').text if child[i].find('sid') is not None else None
		data[parent][sid] = {'idx':i}
		data[parent][sid].update(xmlTagText2dict(child[i], itemList))

	return data


def getXmlOrgSid(xmlobj):
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}

	child = list(xmlobj)
	cLen = len(child) if child is not None else 0

	baseList = [
		'sid',
		's_org',
		's_org',
		'n_org',
		'sid_aorg',
		'sid_dorg',
		'name',
		'name-kana',
		'abbr',
		'zip1',
		'address1',
		'zip2',
		'address2',
		'tel',
		'fax',
		'remarks'
		]
	for i in range(cLen):
		sid = child[i].find('sid').text if child[i].find('sid') is not None else None
		data[parent][sid] = {'idx':i}
		data[parent][sid].update(xmlTagText2dict(child[i], baseList))

		if child[i].find('xinorg') is not None:
			xinorgList = [
				'xinorg/n_examinee',
				'xinorg/s_examinee',
				'xinorg/sid_industry',
				'xinorg/sid_jobtype',
				'xinorg/sid_post',
				'xinorg/d_hired',
				'xinorg/remarks',
				'xinorg/f_examinee',
				'xinorg/n_department',
				'xinorg/s_department'
				]
			data[parent][sid]['xinorg'] = xmlTagText2dict(child[i], xinorgList)
		if child[i].find('address') is not None:
			addrList = [
				'address/zip',
				'address/adr1',
				'address/adr2',
				'address/adr3',
				'address/adr4'
				]
			data[parent][sid]['address'] = xmlTagText2dict(child[i], addrList)

	return data

# 特定健診用にxml_ccardの情報を取得する。
def getXmlCcardSid(xmlobj):
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}
	data[parent]['no'] = None
	data[parent]['d_valid'] = None

	no = xmlobj.find('no').text if xmlobj.find('no') is not None else None
	d_valid = xmlobj.find('d_valid').text if xmlobj.find('d_valid') is not None else None
	data[parent]['no'] = no
	data[parent]['d_valid'] = d_valid

	s_medexamObj = xmlobj.findall('s_medexams/s_medexam')
	for k in s_medexamObj:
		s_class = k.find('s_class').text if k.find('s_class') is not None else None
		examine_rate = k.find('charge/examinee/rate').text if k.find('charge/examinee/rate') is not None else None
		examine_value = k.find('charge/examinee/value').text if k.find('charge/examinee/value') is not None else None
		insurer_rate = k.find('charge/insurer/rate').text if k.find('charge/insurer/rate') is not None else None
		insurer_value = k.find('charge/insurer/value').text if k.find('charge/insurer/value') is not None else None
		insurer_limit = k.find('charge/insurer/value_limit').text if k.find('charge/insurer/value_limit') is not None else None


		data[parent][s_class] = {}
		data[parent][s_class]['examine_rate'] = {}
		data[parent][s_class]['examine_value'] = {}
		data[parent][s_class]['insurer_rate'] = {}
		data[parent][s_class]['insurer_value'] = {}
		data[parent][s_class]['insurer_limit'] = {}

		data[parent][s_class]['examine_rate'] = examine_rate
		data[parent][s_class]['examine_value'] = examine_value
		data[parent][s_class]['insurer_rate'] = insurer_rate
		data[parent][s_class]['insurer_value'] = insurer_value
		data[parent][s_class]['insurer_limit'] = insurer_limit

	return data

# 特定健診用にt_contract_me_attribute xml_attributeの情報を取得する。
def getContractXmlAttributeSid(xmlobj):
	data = {}

	if xmlobj is None:
		return None

	parent = xmlobj.tag
	data[parent] = {}

	child = list(xmlobj)
	cLen = len(child) if child is not None else 0

	# t_contract_me_attribute
	#### XMLタグの意味
	#sid			# 設定項目名
	#sid_criterion 	# 受診項目名

	consultationList = ['sid', 'sid_criterion','s_exam']
	for i in range(cLen):
		sid = child[i].find('sid').text if child[i].find('sid') is not None else None
		data[parent][sid] = {'idx':i}
		data[parent][sid].update(xmlTagText2dict(child[i], consultationList))

		if child[i].find('attribute') is not None:
			attribList = [
				'attribute/price',
				'attribute/tokken/s_class',
				]
			data[parent][sid]['attribute'] = xmlTagText2dict(child[i], attribList)

	return data

# xml_me(XML内)の検査項目／要素のindexを取得するのが目的
# sid(とindex)を元にXML内のデータを引くのに使う予定
#@cmn.measure	# デバッグ専用
def getXmlMeSid(xmlobj):
	#global m_section
	data = {}

	if xmlobj is None:
		return None

	# m_sectionは差分がある場合のみ取得を行う
	old_psid = conf.m_section['psid'] if 'psid' in conf.m_section else (0,)	# 取得できない時はダミーを入れる
	m_section_psid = (20000, 90000, 91000, 92000)

	if old_psid is not None and (len(list(set(old_psid) ^ set(m_section_psid))) != 0):	# 差分チェック
		row = cmn.get_m_section_psid(m_section_psid)
		conf.m_section.update({str(item['sid']):item['name'] for item in row if row is not None})

	parent = xmlobj.tag
	data[parent] = {}

	child = list(xmlobj)
	cLen = len(child) if child is not None else 0

	if parent == 'ecourse':
		itemList = ['sid','sid_criterion']
		if xmlobj.find('sid') is None: return None		# sidが取得できない場合、XMLが壊れている可能性あり
		sid = xmlobj.find('sid').text
		#sid_criterion = xmlobj.find('sid_criterion').text
		#data[parent][sid] = {'sid': sid, 'sid_criterion': sid_criterion}
		data[parent][sid] = xmlTagText2dict(xmlobj, itemList)
		result = xmlobj.find('result') if xmlobj.find('result') is not None else None
		if result is not None:
			data[parent][sid]['result'] = getXmlMeAnalyzeResult(result)

		# コースの基準をconfへ
		sid_criterion = data[parent][sid]['sid_criterion']
		if sid_criterion not in conf.m_criterion:
			conf.m_criterion[sid_criterion] = getXmlCriterion(sid_criterion, s_exam='1001')['criterion'][sid_criterion]

		return data

	if parent == 'equipments':
		itemList = ['s_equipment','sid_crcountiterion']
		for i in range(cLen):
			s_equipment = child[i].find('s_equipment').text if child[i].find('s_equipment') is not None else None
			#count = child[i].find('count').text if child[i].find('count') is not None else None
			#data[parent][s_equipment] = {'idx':i, 's_equipment': s_equipment, 'count': count}
			data[parent][s_equipment] = {'idx':i}
			data[parent][s_equipment].update(xmlTagText2dict(child[i], itemList))
	else:
		# egroups/eitems/elements
		itemList = ['sid','sid_criterion','f_intended']
		for i in range(cLen):
			sid = child[i].find('sid').text if child[i].find('sid') is not None else None
			#sid_criterion = child[i].find('sid_criterion').text if child[i].find('sid_criterion') is not None else None
			#f_intended = child[i].find('f_intended').text if child[i].find('f_intended') is not None else None
			data[parent][sid] = {'idx':i}
			data[parent][sid].update(xmlTagText2dict(child[i], itemList))
			result = child[i].find('result') if child[i].find('result') is not None else None
			if result is not None:
				data[parent][sid]['result'] = getXmlMeAnalyzeResult(result)

	return data

# xml_meのcourseをいじる
#@cmn.measure	# デバッグ専用
def convXmlMeCourse(rdata):
	m_criterion = {}
	data = {}
	if rdata is None:
		return None

	conf.m_opinion_rankset['total'] = None
	conf.m_opinion_rankset['group'] = None

	courseSid = ''.join(rdata.keys())		# コースSIDは常に1個という前提

	if 'opinion' in rdata[courseSid]['result'] is None or len(rdata[courseSid]['result']['opinion']) < 1:
		return rdata

	m_criterion['criterion'] = {rdata[k]['sid']:rdata[k]['sid_criterion'] for k in rdata if k is not None}
	for sid in m_criterion['criterion']:
		data[sid] = getXmlCriterion(m_criterion['criterion'][sid], s_exam='1001', sid_exam=sid)				# s_exam=1001はコース
		if data[sid] is None: return rdata
		totalRanksetSid = data[sid]['criterion'][m_criterion['criterion'][sid]]['total-rankset']['sid']		# 総合判定用
		if totalRanksetSid not in conf.m_opinion_rankset or conf.m_opinion_rankset[totalRanksetSid] is None:
			try:
				conf.m_opinion_rankset['total'] = getXmlRankset(totalRanksetSid)['rankset'][totalRanksetSid]
			except Exception as err:
				log('total rankset get faild: {}'.format(err), LOG_ERR)
		groupRanksetSid = data[sid]['criterion'][m_criterion['criterion'][sid]]['group-rankset']['sid']		# グループ判定用
		if groupRanksetSid not in conf.m_opinion_rankset or conf.m_opinion_rankset[groupRanksetSid] is None:
			try:
				conf.m_opinion_rankset['group'] = getXmlRankset(groupRanksetSid)['rankset'][groupRanksetSid]
			except Exception as err:
				log('group rankset get faild: {}'.format(err), LOG_ERR)

	# opinionも常に1個だよね・・・？
	val = None
	try:
		if 'f_course_rank2moji' in conf.convert_option and conf.convert_option['f_course_rank2moji'] == '1':
			# 文字を返したい場合、m_sectionのnameを返却する
			val = conf.m_section[rdata[courseSid]['result']['opinion']['1']['code']]	# TODO: コースの出力先Noは１固定
		else:
			# codeにname（A～F）を入れる
			val = conf.m_opinion_rankset['total'][rdata[courseSid]['result']['opinion']['1']['code']]['name']
	except KeyError:
		log('unknown rankset: courseSid: {}, opinion: {}'.format(courseSid, rdata[courseSid]['result']['opinion']), LOG_DBG)
	if val is not None:
		rdata[courseSid]['result']['opinion']['1']['code'] = val

	# 総合所見の改行を置換
	val = rdata[courseSid]['result']['opinion']['1']['finding']
	if val is not None and len(val) > 0:
		# ＜総合所見＞の文字列を削除
		val = val.replace(u'＜総合所見＞','').strip()
		val = re.sub(r"\n+", '\n', val)
		# TODO: 暫定版。識別用の改行文字を入れる。Excelマクロ側で識別文字列をチェックして改行コードを挿入する
		if 'f_totalRankFindingBreak' in conf.convert_option and (conf.convert_option['f_totalRankFindingBreak'] == '1' or ('#text' in conf.convert_option['f_totalRankFindingBreak'] and conf.convert_option['f_totalRankFindingBreak']['#text'] == '1')):

			if '@replaceStr' in conf.convert_option['f_totalRankFindingBreak']:	# 任意の改行置換用文字
				val = val.strip().replace('\n', conf.convert_option['f_totalRankFindingBreak']['@replaceStr'])
			else:
				val = val.strip().replace('\n','\\r\\n')
		else:
			val = val.strip().replace('\n',', ')
		rdata[courseSid]['result']['opinion']['1']['finding'] = val

	# 確定を行った医師名
	# その他入力の健康診断を実施した医師にしてくれ。だとかなーり面倒かも。というかこのコードじゃ無理
	if 'sid_doctor' in rdata[courseSid]['result']['opinion']['1'] and rdata[courseSid]['result']['opinion']['1']['sid_doctor'] is not None:
		sid_doctor = rdata[courseSid]['result']['opinion']['1']['sid_doctor']
		row = cmn.get_m_user(sid_doctor) if int(sid_doctor) > 1 else None	# １は健診アカウントなので無視
		rdata[courseSid]['result']['opinion']['1']['sid_doctor'] = row[0]['name'] if row is not None else None

	return rdata

# xml_meのgroupをいじる
#@cmn.measure	# デバッグ専用
def convXmlMeGroup(rdata):
	if rdata is None: return None

	# 改行置換用
	pattern1 = r"\n+"
	convbreak = re.compile(pattern1)

	m_criterion = {}
	data = {}

	m_criterion['criterion'] = {rdata[k]['sid']:rdata[k]['sid_criterion'] for k in rdata if k is not None}
	for sid in m_criterion['criterion']:
		if 'f_intended' not in rdata[sid] or rdata[sid]['f_intended'] != '1': continue
		# opinionが複数ある場合、rank-output-keyに項目名を入れる。そのためにm_criterionの検索／取得を行う
		opinionLen = len(rdata[sid]['result']['opinion'])
		if opinionLen > 1:
			sid_criterion = m_criterion['criterion'][sid]
			data[sid] = getXmlCriterion(sid_criterion, s_exam='1003', sid_exam=sid)				# s_exam=1003はグループ
			eData = {k:data[sid]['criterion'][sid_criterion]['eitem'][k][v] for k in data[sid]['criterion'][sid_criterion]['eitem'] for v in data[sid]['criterion'][sid_criterion]['eitem'][k]}

		# グループのopinionは沢山いる可能性あり
		val = None
		for key in rdata[sid]['result']['opinion'].keys():
			try:
				val = conf.m_opinion_rankset['group'][rdata[sid]['result']['opinion'][key]['code']]['name'] if rdata[sid]['result']['opinion'][key]['code'] != '90001' else None
			except KeyError:
				log('unknown rankset: groupSid: {}, opinion: {}'.format(sid, rdata[sid]['result']['opinion'][key]), LOG_DBG)
			if val is not None:
				rdata[sid]['result']['opinion'][key]['code'] = val
			if opinionLen > 1:
				outKey = rdata[sid]['result']['opinion'][key]['rank-output-key']
				tmpName = ''
				for fsid in eData:
					if 'rank-output-key' in eData[fsid] and eData[fsid]['rank-output-key'] == outKey:
						# 省略名＞出力名＞内部名称の順で採用
						if eData[fsid]['abbr'] is not None and len(eData[fsid]['abbr'].strip()) > 0: tmpName += eData[fsid]['abbr']
						elif eData[fsid]['title'] is not None and len(eData[fsid]['title'].strip()) > 0: tmpName += eData[fsid]['title']
						else: tmpName += eData[fsid]['name']
						tmpName += '\n'		# 区切り文字
				if len(tmpName) > 0: rdata[sid]['result']['opinion'][key]['rank-output-key'] = tmpName.strip().replace('\n',',')	# 区切り文字を置換して格納

			# 所見の改行を置換
			val = rdata[sid]['result']['opinion'][key]['finding']
			if val is not None and len(val) > 0:
				# TODO: 所見欄の改行をどうにかしたいならここ
				val = convbreak.sub(r"\n", val.strip())
				# TODO: 暫定版。識別用の改行文字を入れる。Excelマクロ側で識別文字列をチェックして改行コードを挿入する
				if 'f_groupRankFindingBreak' in conf.convert_option and (conf.convert_option['f_groupRankFindingBreak'] == '1' or ('#text' in conf.convert_option['f_groupRankFindingBreak'] and conf.convert_option['f_groupRankFindingBreak']['#text'] == '1')):
					if '@replaceStr' in conf.convert_option['f_groupRankFindingBreak']:	# 任意の改行置換用文字
						val = val.strip().replace('\n', conf.convert_option['f_groupRankFindingBreak']['@replaceStr'])
					else:
						val = val.strip().replace('\n','\\r\\n')
				else:
					val = convbreak.sub(r", ", val.strip())
				rdata[sid]['result']['opinion'][key]['finding'] = val

	return rdata

# xml_meのelementをいじる
#@cmn.measure	# デバッグ専用
def convXmlMeEelement(rdata):
	if rdata is None: return None
	#global m_qualitative

	#if 'f_translation' in conf.convert_option and conf.convert_option['f_translation'] == '1' and len(conf.i18n_list) > 0: useTransCode = True		# 多言語対応なら、翻訳文を検索する
	#else: useTransCode = False

	# 言語コードを抽出するための正規表現
	pattern1 = r"##([A-Z]+[0-9]+)##"
	transCode = re.compile(pattern1)
	# 改行置換用
	pattern2 = r"\n+"
	convbreak = re.compile(pattern2)

	m_criterion = {}
	data = {}

	##
	# 翻訳対象だけど、翻訳文が見つからない(or m_outsourceに記載した文言を強制したい)時のために突っ込んでおく
	def searchTransCode(sValItem, sVal, mode=None):
		retVal = sVal	# 全部こけたときは入力を戻す
		i18n = None
		if mode == '3' or mode == '6':
			try:
				# 読み込んだファイル(例:i18n_list=en-US.js)に対象となるkeyが存在したら、対象の翻訳文で取得する
				i18n = conf.i18n_list[list(dict(conf.i18n_list).keys()).index(conf.i18n_item[sid][sVal])][1]
				if i18n is not None and len(i18n) > 0: retVal = i18n
			# m_outsourceで定義されていない場合、captionを採用
			except KeyError:
				try:
					# captionに言語コードが入っている場合、それを検索して出力
					if sVal in sValItem: retVal = conf.i18n_list[list(dict(conf.i18n_list).keys()).index(transCode.sub(r"\1", sValItem[sVal]))][1]
				except Exception:
					# captionを出力
					if sVal in sValItem: retVal = sValItem[sVal]
			except ValueError:
				try:
					# 言語コードが入っていない（見つからない）場合、m_outsourceの定義から出力を試みる
					retVal = conf.i18n_item[sid][sVal]
				except Exception:
					# captionを出力
					if retVal in sValItem: retVal = sValItem[sVal]
			except Exception as err:
				log('i18n check: esid:{}, valItem:{}, msg:{}'.format(sid, sValItem, err), LOG_ERR)

		elif mode == '4':
			# 複選択対応を考慮。区切り文字を追加する場合はここ
			if sVal.find(',') > 0: sepStr = ','
			elif sVal.find('::') > 0: sepStr = '::'
			else: sepStr = u' ' # デフォは空白
			sepVal = sVal.split(sepStr)
			try:	# TODO: 多言語対応
				retVal = ','.join([conf.i18n_list[list(dict(conf.i18n_list).keys()).index(conf.i18n_item[sid][v])][1] for v in sepVal])
			except KeyError: retVal = ''.join([sValItem[v] for v in sepVal])
			except ValueError: retVal = ''.join([sValItem[v] for v in sepVal])
			except Exception as err:
				log('inputStyle=4, i18n check: esid:{}, valItem:{}, msg:{}'.format(sid, err, sValItem), LOG_ERR)

		elif mode == '5':
			# TODO: 翻訳未対応
			if sVal in sValItem: retVal = sValItem[val]

		return retVal

	# valueを持つsidをリストアップ
	m_criterion['criterion'] = {rdata[k]['sid']:rdata[k]['sid_criterion'] for k in rdata if 'value' in rdata[k]['result']}
	for sid in m_criterion['criterion']:
		data[sid] = getXmlCriterion(m_criterion['criterion'][sid], s_exam='1005')	# s_exam=1005は項目要素

	for sid in m_criterion['criterion']:
		# 取得した基準データ内に該当するものが含まれていない場合はスキップ
		if sid not in data or data[sid] is None:
			log('esid:{}, is criterionData not found'.format(sid), LOG_WARN)
			continue
		# 結果データ内に該当する基準データが含まれない場合スキップ
		try:
			dataCriterion = data[sid]['criterion'][m_criterion['criterion'][sid]]
		except Exception as err:
			log('examlist_sid:{}, m_criterion_sid:{} is criterionData not found'.format(sid, m_criterion['criterion'][sid]), LOG_WARN)
			continue
		val = rdata[sid]['result']['value']
		if val is None or len(val.strip()) < 1: continue
		# 出力が数値
		if dataCriterion['output-format'] == '1':
			decDigit = dataCriterion['number-value']['dec-digit']
			rdata[sid]['result']['value'] = cmn.numeric2conv(val, decDigit)
		# 出力が定性
		elif dataCriterion['output-format'] == '2':
			qsid = dataCriterion['qualitative']['sid']
			if qsid not in conf.m_qualitative or conf.m_qualitative[qsid] is None:	# 定性値のリストをチェック、存在しなければ追加していく
				tmp = getXmlQualitative(qsid)
				conf.m_qualitative[qsid] = tmp['qualitative'][qsid]
				conf.m_qualitative[qsid] = {conf.m_qualitative[qsid][k]['value']: conf.m_qualitative[qsid][k]['caption'] for k in conf.m_qualitative[qsid] if k.isdigit()}
			rdata[sid]['result']['value'] = conf.m_qualitative[qsid][val] if val in conf.m_qualitative[qsid] else val
		# 出力が文字
		elif dataCriterion['output-format'] == '3':
			# 入力が 1:単文、2:複文
			if dataCriterion['input-style'] == '1' or dataCriterion['input-style'] == '2':
				val = convbreak.sub(r"\n", val.strip())
				# TODO: 暫定版。識別用の改行文字を入れる。Excelマクロ側で識別文字列をチェックして改行コードを挿入する
				if 'f_elementValueBreak' in conf.convert_option and (conf.convert_option['f_elementValueBreak'] == '1' or ('#text' in conf.convert_option['f_elementValueBreak'] and conf.convert_option['f_elementValueBreak']['#text'] == '1')):
					if '@replaceStr' in conf.convert_option['f_elementValueBreak']:	# 任意の改行置換用文字
						val = val.strip().replace('\n', conf.convert_option['f_elementValueBreak']['@replaceStr'])
					else:
						val = val.strip().replace('\n','\\r\\n')
				else:
					val = convbreak.sub(r", ", val.strip())
				rdata[sid]['result']['value'] = val

			# 入力が 3:単選択、4:複選択、6:論理
			# FIXME: 要検証、翻訳の有無で言語コードを引く引かない含めて再設計が必要かも。
			elif dataCriterion['input-style'] == '3' or dataCriterion['input-style'] == '4' or dataCriterion['input-style'] == '5' or dataCriterion['input-style'] == '6':
				if 'char-value' not in dataCriterion:
					log('esid: {}, intput: {}, output: {}, char-value tag nothing'.format(sid, dataCriterion['input-style'], dataCriterion['output-format']), LOG_WARN)
				else:
					try:
						valItem = {dataCriterion['char-value'][k]['value']:dataCriterion['char-value'][k]['caption'] for k in dataCriterion['char-value']}
					except Exception as err:
						log('create value list: esid: {}, msg: {}'.format(sid, err), LOG_ERR)
					# 3:単選択、4:複選択
					if dataCriterion['input-style'] == '3' or dataCriterion['input-style'] == '4' or dataCriterion['input-style'] == '6':
						#if 'f_translation' in convert_option and convert_option['f_translation'] == '1' and len(conf.i18n_list) > 0:	# 多言語対応なら、翻訳文を検索する
						if dataCriterion['input-style'] == '3' or dataCriterion['input-style'] == '6':
							val = searchTransCode(valItem, val, mode=dataCriterion['input-style'])
						if dataCriterion['input-style'] == '4':
							val = searchTransCode(valItem, val, mode=dataCriterion['input-style'])
						rdata[sid]['result']['value'] = val
					# 入力が 6:論理(bool)
					# FIXME: 色々考える必要があるかも。1(True)｜0(False)なのか、valを見てcaptionを出力するのか
					# と、思ったけど。出力が文字ならcaptionだよなぁ？なのでコメントアウトして3,4,6に統合
					#elif dataCriterion['input-style'] == '6':
					#	log('input-style 6, sid: {}, val: {}, char-value: {}'.format(sid, val, dataCriterion['char-value'].values()), LOG_DBG)
					#	boolList = [dataCriterion['char-value'][k]['bool'] for k in dataCriterion['char-value'] if 'bool' in dataCriterion['char-value'][k]]
					#	if len(boolList) > 0:
					#		log('bool, sid: {}, val: {}, bool: {}'.format(sid, val, boolList), LOG_WARN)

					# 入力が 5:演算
					elif dataCriterion['input-style'] == '5':
						# captionを出力
						val = searchTransCode(valItem, val, mode=dataCriterion['input-style'])
						rdata[sid]['result']['value'] = val

			else:
				# TODO: 検討が必要かも
				log('sid_criterion: {}, input-style undefined: {}'.format(sid, dataCriterion['input-style']), LOG_DBG)

		else:
			log('output-format undefined: {}'.format(dataCriterion['output-format']), LOG_WARN)

	return rdata


# コースのxml_criterion(s_exam:1001)のstructuresをごにょっと解析
#@cmn.measure	# デバッグ専用
def analyzeXmlCriterionCource_fIntended_fExam(xmlMeSid):
	if xmlMeSid is None or len(xmlMeSid) < 1: return None
	data = {}
	data['xmlMe'] = {}
	data['xmlMe']['egroup'] = {}
	data['xmlMe']['eitem'] = {}
	data['meAttrib'] = {}
	data['meAttrib']['eitem'] = {}
	data['contMeAttrib'] = {}
	data['contMeAttrib']['attribute'] = {}

	# まずはコースID取得
	course_sid = list(xmlMeSid['ecourse'].keys())[0]		# xmlMeにコース情報が存在するのは1個の前提に取得
	course_sid_criterion = xmlMeSid['ecourse'][course_sid]['sid_criterion']
	# 何故かコースのsid_criterionが変な人がいる場合あり
	if course_sid_criterion is None or course_sid_criterion == '0' or len(course_sid_criterion) < 1:
		log('course sid_criterion unknown : sid={}, sid_criterion={}'.format(course_sid, course_sid_criterion), LOG_WARN)
		return None

	# コースの基準を取得
	criterion_course = getXmlCriterion(course_sid_criterion, s_exam='1001')['criterion']

	# グループ抽出（分解）
	#groupList = {}
	#for sid in criterion_course[course_sid_criterion]['egroup']:
	#	groupList[sid] = {}
	#	sid_criterion = criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']
	#	groupList[sid] = criterion_course[course_sid_criterion]['egroup'][sid][sid_criterion]['eitem']
	# 内包表記に変更して速度を稼ぐ
	# [抽出結果] {'groupSid':{'eitemSid':eitemList}}
	#groupList = {sid:criterion_course[course_sid_criterion]['egroup'][sid][criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']]['eitem'] for sid in criterion_course[course_sid_criterion]['egroup']}

	# 項目抽出（上のグループアイテムから抽出分解）
	#eitemList = {}
	#for sid in groupList:
	#	eitemList[sid] = {}
	#	for esid in groupList[sid]:
	#		eitemList[sid][esid] = {}
	#		eitemList[sid][esid] = groupList[sid][esid][groupList[sid][esid]['sid_criterion']]['element']
	# 内包表記に変更して速度を稼ぐ
	# [抽出結果] {'groupSid':{'eitemSid':{'elementSid':element}}}
	#eitemList = {sid:{esid:groupList[sid][esid][groupList[sid][esid]['sid_criterion']]['element'] for esid in groupList[sid] if 'element' in groupList[sid][esid][groupList[sid][esid]['sid_criterion']]} for sid in groupList}

	# 内包表記の実験（変数groupListにつっこんでいたけど、性能向上狙いでワンライナーに変更）
	eitemList = {sid:{esid:{sid:criterion_course[course_sid_criterion]['egroup'][sid][criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']]['eitem'] for sid in criterion_course[course_sid_criterion]['egroup']}[sid][esid][{sid:criterion_course[course_sid_criterion]['egroup'][sid][criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']]['eitem'] for sid in criterion_course[course_sid_criterion]['egroup']}[sid][esid]['sid_criterion']]['element'] for esid in {sid:criterion_course[course_sid_criterion]['egroup'][sid][criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']]['eitem'] for sid in criterion_course[course_sid_criterion]['egroup']}[sid] if 'element' in {sid:criterion_course[course_sid_criterion]['egroup'][sid][criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']]['eitem'] for sid in criterion_course[course_sid_criterion]['egroup']}[sid][esid][{sid:criterion_course[course_sid_criterion]['egroup'][sid][criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']]['eitem'] for sid in criterion_course[course_sid_criterion]['egroup']}[sid][esid]['sid_criterion']]} for sid in {sid:criterion_course[course_sid_criterion]['egroup'][sid][criterion_course[course_sid_criterion]['egroup'][sid]['sid_criterion']]['eitem'] for sid in criterion_course[course_sid_criterion]['egroup']}}

	# 要素抽出（上の項目アイテムから抽出分解）
	#elementList = {}
	#for sid in eitemList:
	#	elementList[sid] = {}
	#	for esid in eitemList[sid]:
	#		elementList[sid][esid] = {}
	#		elementList[sid][esid] = list(eitemList[sid][esid].keys())
	# 内包表記に変更して速度を稼ぐ
	# [抽出結果] {'groupSid':{'eitemSid':[elementSid]}
	elementList = {sid:{esid:list(eitemList[sid][esid].keys()) for esid in eitemList[sid]} for sid in eitemList}

	# 項目のSIDのみ抽出: [抽出結果] {'groupSid':[eitem]}
	eitemSidList = {k: list(eitemList[k].keys()) for k in eitemList}
	# 要素のSIDのみ抽出: [抽出結果] {'eitemSid':[element]}
	elementSidList = {kk: elementList[k][kk] for k in elementList for kk in elementList[k]}

	# xmlMeのgroupのf_intendedを抽出。tagが存在しなければ（1）受診対象扱いにする
	xmlMe_egroup_fInteded = {k : xmlMeSid['egroups'][k].get('f_intended') if k in xmlMeSid['egroups'].keys() else '1' for k in eitemSidList.keys()}
	data['xmlMe']['egroup']['f_intended'] = xmlMe_egroup_fInteded
	# xmlMeのeitemのf_intendedを抽出。tagが存在しなければ（1）受診対象扱いにする
	xmlMe_eitem_fInteded = {k : xmlMeSid['eitems'][k].get('f_intended') if k in xmlMeSid['eitems'].keys() else '1' for k in elementSidList.keys()}
	data['xmlMe']['eitem']['f_intended'] = xmlMe_eitem_fInteded

	# m_me_attribute
	#### XMLタグの意味
	#f_exam			# 1:オプション、2:必須
	#f_intended 	# 0:対象外、1:受診対象

	#### ここからコース基準のお話
	#（１）f_intended=0 && f_exam = 1 # オプションかつ、受診対象外
	#（２）f_intended=0 && f_exam = 2 # 必須。かつ、受診対象外
	#（３）f_intended=1 && f_exam = 1 # オプション、かつ、受診対象
	#（４）f_intended=1 && f_exam = 2 # 必須。かつ。受診対象
	# 標準／オプションはコースのcriterionをベースに、m_me_attributeで上書き、（contractがあるならさらに上書き。）となる
	#### ここまで

	# f_exam(必須／オプション)のチェック
	# 補足：m_me_attributeは更新分のみが格納されている。このXMLの中にいない検査項目は必須扱いとなる
	attrib_data = getXmlAttribute(course_sid, course_sid_criterion)['consultations']
	if attrib_data is None or len(attrib_data) < 1:	# タグが取得できない場合、警告ログだけ表示
		data['meAttrib']['eitem']['f_exam'] = None
		data['meAttrib']['eitem']['f_intended'] = None
		log('m_me_attribute not found : sid_me={} and sid_criterion={}'.format(course_sid, course_sid_criterion), LOG_WARN)
	else:	# 存在したら処理する
		# m_me_attributeのf_examを抽出する
		me_attrib_f_exam = {k:attrib_data[k].get('f_exam') for k in attrib_data if 'f_exam' in attrib_data[k]}
		# m_me_attributeのf_intendedを抽出する
		me_attrib_f_intended = {k:attrib_data[k].get('f_intended') for k in attrib_data if 'f_intended' in attrib_data[k]}

		# me_attrib_f_examにいないが、eitemSidList(コース基準)に存在しているものをまとめる
		f_examMergeSidList = list(me_attrib_f_exam.keys())			# List化
		f_examMergeSidList.extend(list(elementSidList.keys()))		# me_attrib_f_examと、elementSidList(コース基準)を結合
		f_examMergeSidList = set(f_examMergeSidList)				# 重複排除
		# 基準の項目の標準／オプションを確定させる
		# me_attrib_f_exam内に存在しない場合は(2)必須扱い（xmlMeはf_examをもっていないので、そちらの参照は行わない）
		#f_examMergeList = {}
		#for sid in f_examMergeSidList:
		#	statusData = me_attrib_f_exam[sid] if sid in me_attrib_f_exam else '2'
		#	f_examMergeList.update({sid: statusData})
		data['meAttrib']['eitem']['f_exam'] = {sid: me_attrib_f_exam[sid] if sid in me_attrib_f_exam else '2' for sid in f_examMergeSidList}

		# 基準の受診対象／対象外を確定させる
		# やってることは上と同じ
		f_intendedMergeSidList = list(me_attrib_f_intended.keys())
		f_intendedMergeSidList.extend(list(elementSidList.keys()))
		f_intendedMergeSidList = set(f_intendedMergeSidList)
		data['meAttrib']['eitem']['f_intended'] = {sid: me_attrib_f_intended[sid] if sid in me_attrib_f_intended else '1' for sid in f_intendedMergeSidList}

	# FIXME: このCSV出力機能ではcontractでの上書きは未対応。将来機能かもね
	# m_me_attributeをベースに、t_contract_me_attributeでさらに上書き(特定健診用)
	#### ここから 作成途中だが、コース情報からしかとらないのでここでの紐づけは必要ないかも仲里
#		t_attrib_data = getContractXmlAttribute(course_sid, course_sid_criterion)['consultations']
#		data['contMeAttrib']['attribute'] = None
#		log('t_contract_me_attribute not found : sid_me={} and sid_criterion={}'.format(course_sid, course_sid_criterion), LOG_WARN)
#		else: #存在したら処理する
#			#t_contract_me_attributeのattributeを抽出する
#			t_cont_attrib = {t:t_attrib_data[t].get('attribute') for t in t_attrib_data if 'attribute' in t_attrib_data[t]}
#			#
#			t_contattribSidList = list(t_connt_attrib.keys())			# List化
#			t_contattribSidList.extend(list(elementsidList.keys()))		# コース基準を統合
#			t_contattribSidList = set(f_examMergeSidList)				# 重複排除
#
#			data['contMeAttrib']['attribute'] = {sid: t_cont_attrib[sid] if sid in t_cont_attrib else '2' for sid in t_contattribSidList}



	#### ここまで

	# TODO: f_intended 目視チェック用にログ出力
	#from operator import itemgetter
	#sort_attrib = {int(k):data['meAttrib']['eitem']['f_intended'][k] for k in data['meAttrib']['eitem']['f_intended']}
	#sort_data = sorted(sort_attrib.items(), key=itemgetter(0))
	#log('f_intended meAttrib:{}'.format(sort_data), LOG_WARN)
	#sort_xmlMe = {int(k):data['xmlMe']['eitem']['f_intended'][k] for k in data['xmlMe']['eitem']['f_intended']}
	#sort_data = sorted(sort_xmlMe.items(), key=itemgetter(0))
	#log('f_intended xmlMe:{}'.format(sort_data), LOG_WARN)

	# 要素のsidを格納しておく
	data['xmlMe']['eitem']['elementSid'] = elementSidList

	return data


#@cmn.measure	# デバッグ専用
def analyzeXmlQualitativeIndex(xml):
	data = {}

	sidQualitative = getXmlQualitativeSid(xml.find('qualitative'))
	data.update(sidQualitative)

	return data

#@cmn.measure	# デバッグ専用
def analyzeXmlRanksetIndex(xml):
	data = {}

	sidRankset = getXmlRanksetSid(xml.find('rankset'))
	data.update(sidRankset)

	return data

#@cmn.measure	# デバッグ専用
def analyzeXmlCriterionIndex(xml):
	data = {}
	sidCriterion = None
	s_exam = None
	try:
		s_exam = xml.find('criterion/s_exam').text
	except:
		return None

	if s_exam == '1001': sidCriterion = getXmlCriterionCource(xml.find('criterion'))			# コース
	elif s_exam == '1002': sidCriterion = getXmlCriterionPack(xml.find('criterion'))			# パック
	elif s_exam == '1003': sidCriterion = getXmlCriterionGroup(xml.find('criterion'))			# グループ
	elif s_exam == '1004': sidCriterion = getXmlCriterionItem(xml.find('criterion'))			# 項目
	elif s_exam == '1005': sidCriterion = getXmlCriterionElement(xml.find('criterion'))			# 要素
	else: return None

	if sidCriterion is None or len(sidCriterion) < 1: return None

	data.update(sidCriterion)

	return data

#@cmn.measure	# デバッグ専用
def analyzeXmlAttributeIndex(xml):
	data = {}

	sidConsultations = getXmlAttributeSid(xml.find('attribute/consultations'))
	data.update(sidConsultations)

	return data

#@cmn.measure	# デバッグ専用
def analyzeXmlOrgIndex(xml):
	data = {}

	sidOrgs = getXmlOrgSid(xml.find('orgs'))
	data.update(sidOrgs)

	return data

#@cmn.measure	# デバッグ専用
# 特定健診用
def analyzeXmlCcardIndex(xml):
	data = {}

	xmlCcard = getXmlCcardSid(xml.find('ccard'))
	data.update(xmlCcard)

	return data

#@cmn.measure	# デバッグ専用
def analyzeXmlMeIndex(xml, resultConv=False, f_elementsType=None):

	data = {}

	sidEquipments = getXmlMeSid(xml.find('equipments'))
	sidEcourse = getXmlMeSid(xml.find('ecourse'))
	sidEgroups = getXmlMeSid(xml.find('egroups'))
	sidEitems = getXmlMeSid(xml.find('eitems'))
	sidElements = getXmlMeSid(xml.find('elements'))

	# xmlmeのデータをcsv出力用に修正
	if sidElements is not None and resultConv == True:
		#協会けんぽ
		if f_elementsType == 'kyoukaikenpo':
			import form_tools_py.getXmlSid_kk as kk
			courseSid = ''.join(sidEcourse['ecourse'].keys())
			sid_criterion = sidEcourse['ecourse'][courseSid]['sid_criterion']
			sidElements['elements'] = kk.convXmlMeEelementKyoukaiKenpo(sidElements['elements'], sid_criterion)
		#特定健診
		elif f_elementsType == 'tokuteikenshin':
			import form_tools_py.getXmlSid_tk as tk
			courseSid = ''.join(sidEcourse['ecourse'].keys())
			sid_criterion = sidEcourse['ecourse'][courseSid]['sid_criterion']
			sidElements['elements'] = tk.convXmlMeEelementTokuteiKenshin(sidElements['elements'], sid_criterion)

		else:
			sidElements['elements'] = convXmlMeEelement(sidElements['elements'])
	if sidEcourse is not None and resultConv == True:
		sidEcourse['ecourse'] = convXmlMeCourse(sidEcourse['ecourse'])
	if sidEgroups is not None and resultConv == True:
		sidEgroups['egroups'] = convXmlMeGroup(sidEgroups['egroups'])

	# 返却データの作成
	data.update(sidEquipments)
	data.update(sidEcourse)
	data.update(sidEgroups)
	data.update(sidEitems)
	data.update(sidElements)

	return data

#@cmn.measure	# デバッグ専用
def analyzeContractXmlAttributeIndex(xml):
	data = {}
	exam_class = xml.find('attribute/tokken/exam_class').text if xml.find('attribute/tokken/exam_class') is not None else None
	course_price = xml.find('attribute/price').text if xml.find('attribute/price') is not None else None
	data['exam_class'] = exam_class
	data['course_price'] = course_price

	sidConsultations = getContractXmlAttributeSid(xml.find('attribute/consultations'))

	data.update(sidConsultations)

	return data

def analyzeXmlExaminee(xml):
	data = {}
	data = getXmlExamineeSid(xml.find('examinee'))
	return data

# m_qualitativeのxml_qualitative
def getXmlQualitative(sid):
	row = cmn.get_m_qualitative(sid)
	xml = cmn.getRow2Xml(row[0]['xml_qualitative'])
	data = analyzeXmlQualitativeIndex(xml)
	return data
# m_opinion_ranksetのxml_rankset
def getXmlRankset(sid):
	row = cmn.get_m_opinion_rankset(sid)
	xml = cmn.getRow2Xml(row[0]['xml_rankset'])
	data = analyzeXmlRanksetIndex(xml)
	return data
# m_criterionのxml_criterion
def getXmlCriterion(sid, s_exam=None, sid_exam=None):
	and_query = ''
	if s_exam is not None:
		and_query += ' AND s_exam=' + str(s_exam) + ' '
	if sid_exam is not None:
		and_query += ' AND sid_exam=' + str(sid_exam) + ' '
	row = cmn.get_m_criterion_plus(sid, and_query)
	if row is None: return None
	xml = cmn.getRow2Xml(row[0]['xml_criterion'])		# 最初の1個目しか採用しない
	data = analyzeXmlCriterionIndex(xml)
	return data
# m_me_attributeのxml_attribute
def getXmlAttribute(sid_me, sid_criterion):
	row = cmn.get_m_me_attribute(sid_me, sid_criterion)
	xml = cmn.getRow2Xml(row[0]['xml_attribute'])
	data = analyzeXmlAttributeIndex(xml)
	return data
# t_appointのxml_xorg
def getXmlOrg(sid):
	row = cmn.get_t_appoint(sid)
	xml = cmn.getRow2Xml(row[0]['xml_xorg'])
	data = analyzeXmlOrgIndex(xml)
	return data
# t_appoint_meのxml_me
def getXmlMe(sid_appoint):
	row = cmn.get_t_appoint_me(sid_appoint)
	xml = cmn.getRow2Xml(row[0]['xml_me'])
	data = analyzeXmlMeIndex(xml)
	return data
# t_appointのxml_examinee
def getXmlExaminee(sid_examinee=None, exam_id=None):
	row = cmn.get_t_appoint(sid=sid_examinee, exam_id=exam_id)
	xml = cmn.getRow2Xml(row[0]['xml_examinee'])
	data = analyzeXmlExaminee(xml)
	return data
# t_appointのxml_ccard 特定健診用
def getXmlCcard(sid):
	row = cmn.get_t_appoint(sid)
	xml = cmn.getRow2Xml(row[0]['xml_ccard'])
	data = analyzeXmlCcardIndex(xml)
	return data
# t_contract_me_attributeのxml_attribute
def getContractXmlAttribute(sid_me, sid_contract):
	row = cmn.get_t_contract_me_attribute(sid_me, sid_contract)
	xml = cmn.getRow2Xml(row[0]['xml_attribute'])
	data = analyzeContractXmlAttributeIndex(xml)
	return data

