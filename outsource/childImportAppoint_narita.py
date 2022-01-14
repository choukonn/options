#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# 受診者／予約インポート
# 流用元はp020の一括結果インポート

from logging import getLogger
plgLog = getLogger(__name__)

import os
import sys
import re
import json
import csv
import pathlib
import xml.etree.ElementTree as ET
import datetime
import xmltodict
import traceback
from time import sleep, time
from collections import defaultdict, namedtuple
from operator import itemgetter

# myapp
import form_tools_py.conf as conf
import form_tools_py.common as form_cmn
from renkei_tools_py.mod import mycfg as mycfg

# DB設定
# mycfg.setDbConfig('90007', 'development')
mycfg.setDbConfig('90007', 'production')
#mycfg.setDbConfig(ENV_DB_CODE, ENV_MODE)

from renkei_tools_py.mod import common as cmn
from renkei_tools_py.mod import my_fileClass as myFile
from renkei_tools_py.mod import my_sqlClass as mySql
from renkei_tools_py import plgCommon as plgCmn
from renkei_tools_py.plgCmd import m_examinee, m_criterion, t_appoint, m_eorg, m_me, m_outsource, t_appoint_me, t_ext_order, m_me_attribute, m_org, t_ext_info, t_contract, t_contract_me_attributeClass
from renkei_tools_py import extFileCtrlClass as extFileCtrl


# インポートファイル解析用
from renkei_tools_py import analysisFile

# コンフィグの代わり
from renkei_tools_py import csv2xml_mapping

msg2js = form_cmn.Log().msg2js
log = form_cmn.Log().log
dbg_log = form_cmn.Log().dbg_log


try:
	# 医療機関番号をmodule名から取得（暫定）
	sidMorg = '90007'
	cmn.baseConf = mycfg.conf
	examineeMap = csv2xml_mapping.examineeMapGet(sidMorg)
	appointMap = csv2xml_mapping.appointMapGet(sidMorg)
	requiredMap = csv2xml_mapping.requiredMapGet(sidMorg)
	optionMap = csv2xml_mapping.optionMapGet(sidMorg)
	orgMap = csv2xml_mapping.orgMapGet(sidMorg)
	dataNameMap = csv2xml_mapping.dataItemMapGet(sidMorg)
except Exception as err:
	msg2js('コンフィグの初期設定でエラーが発生しました。err:[{err}]'.format(err=err))
	traceLog(err)

# ファイル出力したいエラーメッセージ格納用
errMsg = []

dbconfig = {}
sql = None
extFile = None
fileCtrl = None
t_contract_me_attribute = None

# 処理モード
procMode = None
modeAppoint = analysisFile.modeAppoint
modeExam = analysisFile.modeExam
plgConfig = None

success = cmn.success
warning = cmn.warning
error = cmn.error

pConfig = None
pDir = None
courseMap = None
mapDataAll = None
contractData = None
orderMoutSourceSid = None

resultMsg = ""

# 受診ステータス（ex_status）
examSts = t_ext_order.examSts


# 変更対象ステータス
ChangeSts = namedtuple('changeSts', [
	# 初回の予約
	'initAppoint',	# 0
	# コース変更
	'course',		# 1
	# 日付変更
	'apoDay',		# 2
	# 時間変更
	'apoTime',		# 3
	#ステータス変更（予約⇔受付）
	'chgStatus'		# 4
])
changeSts = ChangeSts(0, 1, 2, 3, 4)
#changeSts = {
#	# 初回の予約
#	'initAppoint': 0,
#	# コース変更
#	'course': 1,
#	# 日付変更
#	'apoDay': 2,
#	# 時間変更
#	'apoTime': 3,
#}

# 予約ステータス
AppointSts = namedtuple('appointSts', [
	'reservation',		# 1
	'checkin'		# 2
])
appointSts = AppointSts(1, 2)
#appointSts = {
#	'appoint': 1,
#	'checkin': 2,
#}

AppointAct = namedtuple('appointAct', [
	'register',		# 1
	'cancel'		# 2
])
appointAct = AppointAct(1, 2)
#appointAct = {
#	'register': 1,
#	'cancel': 2,
#}

FIntendedFlag = namedtuple('fIntendedFlag', [
	'ON',		# 1
	'OFF' 		# 0
])
fIntendedFlag = FIntendedFlag('1', '0')
#fIntendedFlag = {
#	'ON': '1',
#	'OFF': '0'
#}

# 属性情報で国コードしか送ってこれない場合、以下のべた書き対応表からm_examineeのXMLを埋める
countryAndLang = {
	# 国		nationality		locale
	'VN':		 {'VNM':		'vi-VN'},
	'JP':		 {'JPN':		'ja-JP'},
	'US':		 {'US':			'en-US'},
	# デフォルトは以下とする
	'OTHER':	 {'OTHER':		'en-US'}
}

# データ内のupdateTimeのチェックステータス
UpdateTimeStatus = namedtuple('updateTimeStatus', [
	# 新規
	'new',			# 1
	# 更新あり
	'update',		# 2
	# 無視
	'ignore'		# 3
	])
updateTimeStatus = UpdateTimeStatus(1, 2, 3)
#updateTimeStatus = {
#	# 新規？
#	'new': 1,
#	# 更新あり
#	'update': 2,
#	# 無視
#	'ignore': 3,
#}

# t_appointステータス
tAppointSts = t_appoint.tAppointSts
reAppointSts = t_appoint.sReApo


# トレースログ出力
def traceLog(message):
	type_, value, traceback_ = sys.exc_info()
	log('message: {message}, traceback: {err}'.format(message=message, err=traceback.format_exception(type_, value, traceback_)))

# テンプレ取得
def getXMLTemplate(filePath):
	try:
		return fileCtrl.xmlRead(filePath)
	except Exception as err:
		msg2js('テンプレートの取得でエラーが発生しました。getXMLTemplate　err:[{err}]'.format(err=err))
		traceLog(err)
		return None


# テンプレ取得
def getXMLTemplate2text(filePath):
	try:
		return fileCtrl.textRead(filePath)
	except Exception as err:
		msg2js('テンプレートの取得でエラーが発生しました。getXMLTemplate2text　err:[{err}]'.format(err=err))
		traceLog(err)
		return None


# m_outsourceの設定ファイルを取得
def getOrderOutSourceXML(sidMorg,):
	global orderMoutSourceSid
	daidaiClass = None

	rows = m_outsource.getOutource(sidMorg, sid=orderMoutSourceSid, sid_section=135014)

	if orderMoutSourceSid is None:
		for row in rows:
			xmlObj = plgCmn.xml2Obj(row['xml_outsource'])
			daidaiClass = xmlObj.find('./outsource/condition/plugins/plugin/class').text
			# LSCのオーダー設定と区別できないので、無理やりこれ
			if daidaiClass == 'Bit.nw.external.plugin.KPlusMultiOrder':
				orderMoutSourceSid = row['sid']
				break
		# m_outsourceが取得出来ない場合、終わり
		if daidaiClass is None:
			log('[{sidMorg}] K+ config(m_outsource) get faild')
			return None
	elif len(rows) == 1:
		xmlObj = plgCmn.xml2Obj(rows[0]['xml_outsource'])
	else:
		log('[{sidMorg}] K+ config(m_outsource) get faild')
		return None

	# 未使用のためとりあえずコメントアウト
	# eorgSid = xmlObj.find('./outsource/condition/db_info/sid_eorg').text
	# ssidFrom = xmlObj.find('./outsource/condition/db_info/ssid_from').text
	# ssidTo = xmlObj.find('./outsource/condition/db_info/ssid_to').text
	# ssidProduct = xmlObj.find('./outsource/condition/db_info/ssid_product').text
	# ssidFileKind = xmlObj.find('./outsource/condition/db_info/ssid_file_kind').text


# オーダー用テーブルへの登録
def sendAppointOrder(sidMorg, tAppointData, orderSts, xml, row, dtAppoint):
	ret = False
	# オーダ送信フラグ 0:未送信、1:送信済み  ※オーダを送信しない場合は1で登録する
	kplusOrder = 0
	lscOrder = 0
	socketOrder = 0
	# オーダ発行フラグ
	order_flg = 1
	# 受付済みフラグ
	reception_flg = 0

	try:
		# シーケンス番号取得
		seqNo = t_ext_order.getOrderSeqNo(sidMorg, tAppointData['sid'])

		# def setAppointOrder(sidMorg, *, sidAppoint, dtAppoint, seqNo, orderStatus, kplusOrder=0, lscOrder=0, socketOrder=0, order_flg=1, reception_flg=0):
		rows = t_ext_order.setAppointOrder(sidMorg, sidAppoint=tAppointData['sid'], dtAppoint=dtAppoint, seqNo=seqNo, orderStatus=orderSts, kplusOrder=kplusOrder, lscOrder=lscOrder, socketOrder=socketOrder, order_flg=order_flg, reception_flg=reception_flg)
		if rows is None or len(rows) < 1 or (rows is not None and rows[0]['status'] != 1):
			# ストアドを見る限り、status = 0が失敗、成功で1が返る
			log('[{sidMorg}] K-Plus order registration faild: seqNo:{a}, orderStatus:{b}, tAppoint:{c}'.format(sidMorg=sidMorg, a=seqNo, b=orderSts, c=tAppointData))
		else:
			ret = True

	except Exception as err:
		msg2js('オーダテーブルへの登録でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] msg: {e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)

	return ret


# オーダーテーブルへ登録する際のXML作成
def createAppointOrderXML(sidMorg, kpFlag=0, lscFlag=0):
	orderXmlObj = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['extOrder']['1']))
	#kpOrderFlag = 0
	#lscOrderFlag = 0
	xmlStr = None

	try:
		# 0固定
		orderXmlObj.find('.//kplus_out_flg').text = str(kpFlag)
		orderXmlObj.find('.//lsc_out_flg').text = str(lscFlag)

		xmlStr = ET.tostring(orderXmlObj, encoding='UTF-8').decode('UTF-8')
	except Exception as err:
		msg2js('オーダテーブルのXML作成でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] [extOrder] xml create faild: {msg}'.format(sidMorg=sidMorg, msg=err))
		traceLog(err)
		return None

	return xmlStr


# オーダ発行処理
def procOrder(sidMorg, tAppoint, vid, cid, sid_examinee, examDate, ordSts, row, examDtObj):
	tAppointData = tAppoint

	# f_appoint_onlyがON:1のとき、連携すべき項目をもっていないので処理させない
	if 'f_appoint_only' in optionMap and optionMap['f_appoint_only'] == 1:
		return

	# K+予約／受付連携が有効な場合の処理
	if 'useKpAppointLink' in pConfig and sidMorg in pConfig['useKpAppointLink']:
		if 'f_kp_appoint_link' in optionMap and optionMap['f_kp_appoint_link'] == 1:
			orderXml = createAppointOrderXML(sidMorg)
			if orderXml is not None:
				# 新規登録処理時は、登録されたt_appointの取得を行う
				if tAppoint is None:
					tAppointNew = t_appoint.getTappoint(sidMorg=sidMorg, vid=vid, cid=cid, apoDay=examDate, sidExaminee=sid_examinee)
					if tAppointNew is not None and len(tAppointNew) > 0:
						tAppointData = tAppointNew[0]
					else:
						log('[{sidMorg}] new register t_appoint get faild, k-puls order is skip'.format(sidMorg=sidMorg))
						return

				sendAppointOrder(sidMorg, orderSts=ordSts, tAppointData=tAppointData, xml=orderXml, row=row, dtAppoint=examDtObj)

			log('[{sidMorg}] k-plus proc complete'.format(sidMorg=sidMorg))

	return


# xml_orgの作成
def createOrgXML(sidMorg, orgData, row, orgType):
	xmlStr = None

	try:
		if orgData is None:
			xmlObj = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['org']['1']))
			xmlObj.find('./org/s_org').text = orgType
			# 新規登録はsidタグが不要
			# FIXME: xml_examineeからコピペだけど、なんかいまいちに思える。要素の削除簡単な方法ないのかな？
			[elm_exam.remove(elm) for elm_exam in xmlObj.iter('org') for elm in elm_exam.iter() if elm.tag == 'sid']

		else:
			xmlObj = plgCmn.xml2Obj(orgData['xml_org'])

	except Exception as err:
		msg2js('団体XMLの取得でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] xml_org get faild, msg:{e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
		return None

	# 団体用データの抽出
	orgMapData = {k: str(row[v]) for k, v in orgMap.items() if v in row}

	try:
		# XML作成
		for key, val in orgMapData.items():
			tagSet = xmlObj.find(key)
			if tagSet is not None:
				tagSet.text = val if val is not None and len(val) > 0 else None

		xmlStr = ET.tostring(xmlObj, encoding='UTF-8').decode('UTF-8')

	except Exception as err:
		msg2js('団体XMLの作成でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] xml_org create faild: {e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
		return None

	return xmlStr


# 団体紐づけ
def procXinorg(sidMorg, orgSid, orgType, examDataObj, cid, orgName, row, s_org):

	def setXinOrgXml(row, s_org):
		xinObj = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['org']['2']))

		if s_org == m_org.orgTypeCode['company']: # 所属団体の場合
			# 学籍番号 or 社員番号
			xinObj.find('./xinorg/n_examinee').text = row['EmployeeNo']
		else: # 上記以外の団体の場合
			# 保険証の記号
			xinObj.find('./xinorg/s_examinee').text = row['InsSymbol']
			# 保険証の番号
			xinObj.find('./xinorg/n_examinee').text = row['InsNo']

		xin = ET.tostring(xinObj, encoding='UTF-8').decode('UTF-8')
		m_org.setXorgAdd(sidMorg, sidExaminee=examDataObj['sid_examinee'], sidOrg=orgSid, fCurrent=1, xml=xin)

	# 紐づけリストが存在する
	if examDataObj['xOrg'] is not None:
		checkOrg = [k for k in examDataObj['xOrg'] if k['sid_org'] == orgSid]
		# リスト内に含まれない
		if len(checkOrg) < 1:
			# xinorgの設定
			setXinOrgXml(row, s_org)
			log('カルテID:{cid}, 団体名:{orgName}, {msg}'.format(cid=cid, orgName=orgName, msg='団体情報を受診者に紐づけました'))
	else:
		setXinOrgXml(row, s_org)
		log('カルテID:{cid}, 団体名:{orgName}, {msg}'.format(cid=cid, orgName=orgName, msg='団体情報を受診者に紐づけました'))

	xOrgList = m_org.searchXorgId(sidMorg, sidExaminee=examDataObj['sid_examinee'])
	# 種別チェック用に紐づけリストに該当する団体のXMLから種別を抜き出す
	orgTypeList = {}
	for key in xOrgList:
		rows = m_org.searchOrgId(sidMorg, sid=key['sid_org'])
		tmp = plgCmn.xml2Obj(rows[0]['xml_org'])
		orgTypeList[str(key['sid_org'])] = tmp.find('./org/s_org').text
		del tmp

	# 紐づけリスト更新用
	# 空のXMLオブジェクトを用意して、それに各xinorgを格納、作成したものをストアドに渡す
	baseObj = plgCmn.xml2Obj('<root><xorg><sid_examinee /><xinorgs /></xorg></root>')
	baseObj.find('./xorg/sid_examinee').text = examDataObj['sid_examinee']
	childObj = baseObj.find('./xorg/xinorgs')

	for item in xOrgList:
		tmpBase = plgCmn.xml2Obj('<xinorg><sid_org /><f_current /></xinorg>')
		tmpXinorg = plgCmn.xml2Obj(item['xml_xinorg']).find('xinorg')
		tmpCurrent = item['f_current']
		# 種別一致、sid不一致、有効、設定されているものは無効にする
		if int(orgType) == int(orgTypeList[str(item['sid_org'])]) and orgSid != item['sid_org'] and tmpCurrent == 1:
			tmpCurrent = 0
		elif orgSid == item['sid_org']:
			tmpCurrent = 1
		tmpBase.find('f_current').text = str(tmpCurrent)
		tmpBase.find('sid_org').text = str(item['sid_org'])
		if orgSid == item['sid_org']:
			if s_org == m_org.orgTypeCode['company']: # 所属団体の場合
				# 取込データの設定値が空の場合はエラーメッセージだけ出して更新しない
				if row['EmployeeNo'].strip() == "" and tmpXinorg.find('n_examinee').text is not None and tmpXinorg.find('n_examinee').text.strip() != "":
					msg2js('カルテID:{cid}, 団体名：{orgName} {msg}'.format(cid=cid, orgName=orgName, msg='設定値が空のため、社員番号(学籍番号)の更新をスキップします。'))
				else:
					# 設定済み、かつ値が変わるときはメッセージを出す
					if tmpXinorg.find('n_examinee').text is not None and tmpXinorg.find('n_examinee').text.strip() != "" \
					and row['EmployeeNo'].strip() != "" \
					and tmpXinorg.find('n_examinee').text.strip() != row['EmployeeNo'].strip():
						msg2js('カルテID:{cid}, 団体名：{orgName}, 更新前：{before}, 更新後:{after} {msg}'\
							.format(cid=cid, orgName=orgName, before=tmpXinorg.find('n_examinee').text.strip(), \
								after=row['EmployeeNo'].strip(), msg='社員番号(学籍番号)を更新しました。'))

					# 学籍番号 or 社員番号
					tmpXinorg.find('n_examinee').text = row['EmployeeNo']
			else: # 上記以外の団体の場合
				if row['InsSymbol'].strip() == "" and tmpXinorg.find('s_examinee').text is not None:
					msg2js('カルテID:{cid}, 団体名：{orgName} {msg}'.format(cid=cid, orgName=orgName, msg='設定値が空のため、被保険者証の記号の更新をスキップします。'))
				else:
					# 設定済み、かつ値が変わるときはメッセージを出す
					if tmpXinorg.find('s_examinee').text is not None and tmpXinorg.find('s_examinee').text.strip() != "" \
					and row['InsSymbol'].strip() != "" \
					and tmpXinorg.find('s_examinee').text.strip() != row['InsSymbol'].strip():
						msg2js('カルテID:{cid}, 団体名：{orgName}, 更新前：{before}, 更新後:{after} {msg}'\
							.format(cid=cid, orgName=orgName, before=tmpXinorg.find('s_examinee').text.strip(), \
								after=row['InsSymbol'].strip(), msg='被保険者証の記号を更新しました。'))

					# 保険証の記号
					tmpXinorg.find('s_examinee').text = row['InsSymbol']

				if row['InsNo'].strip() == "" and tmpXinorg.find('n_examinee').text is not None:
					msg2js('カルテID:{cid}, 団体名：{orgName} {msg}'.format(cid=cid, orgName=orgName, msg='設定値が空のため、被保険者証の番号の更新をスキップします。'))
				else:
					# 設定済み、かつ値が変わるときはメッセージを出す
					if tmpXinorg.find('n_examinee').text is not None and tmpXinorg.find('n_examinee').text.strip() != "" \
					and row['InsNo'].strip() != "" \
					and tmpXinorg.find('n_examinee').text.strip() != row['InsNo'].strip():
						msg2js('カルテID:{cid}, 団体名：{orgName}, 更新前：{before}, 更新後:{after} {msg}'\
							.format(cid=cid, orgName=orgName, before=tmpXinorg.find('n_examinee').text.strip(), \
								after=row['InsNo'].strip(), msg='被保険者証の番号を更新しました。'))

					# 保険証の番号
					tmpXinorg.find('n_examinee').text = row['InsNo']
		tmpBase.extend(tmpXinorg.findall('*'))
		childObj.append(tmpBase)
		del tmpBase, tmpXinorg, tmpCurrent

	xOrgListStr = ET.tostring(baseObj, encoding='UTF-8').decode('UTF-8')

	m_org.setXorgUpdate(sidMorg, xml=xOrgListStr)

	return


# 団体処理
def procOrg(sidMorg, row, examDataObj, orgType, orgSid=None, cid=None):
	retOrgSid = None
	orgName = None
	n_org = None
	s_org = None

	# 団体番号をセット
	if row['OrgNo'] != '': # 受診者所属団体
		n_org = row['OrgNo']
		s_org = m_org.orgTypeCode['company']
		orgName = row['OrgName']
	elif row['InsOrgNo'] != '': # 健保
		n_org = row['InsOrgNo']
		s_org = m_org.orgTypeCode['insurance']
		orgName = row['InsOrgName']
	elif row['AreaOrgNo'] != '': # 地域
		n_org = row['AreaOrgNo']
		s_org = m_org.orgTypeCode['region']
		orgName = row['AreaOrgName']
	elif row['OtherOrgNo'] != '': # その他
		n_org = row['OtherOrgNo']
		s_org = m_org.orgTypeCode['other']
		orgName = row['OtherOrgName']

	# TODO: 団体番号が存在するときだけ処理を行う
	if n_org is not None:
		# 団体番号で該当する団体の検索
		orgRows = m_org.searchOrgId(sidMorg, sid=orgSid, orgId=n_org, sOrgId=s_org)
		log(orgRows)
		# 複数ヒットしたら処理しない
		if orgRows is not None and len(orgRows) > 1:
			for orgRow in orgRows:
				orgName += orgRow['name'] + ' '
			msg2js('カルテID:{cid}, 団体番号:{norg}, 団体名：{orgName} {msg}'.format(cid=cid, norg=n_org, orgName=orgName, msg='団体番号が重複しているので団体紐づけ処理をスキップしました'))
			log('[{sidMorg}] duplicate org id, orgData:{org}'.format(sidMorg=sidMorg, org=orgRows))
		# 登録
		elif orgRows is not None:
			orgRow = orgRows[0] if orgRows is not None else None
			orgSid = orgRows[0]['sid'] if orgRow is not None else None

			# 受診者団体登録
			if orgSid is not None and orgSid != 0:
				procXinorg(sidMorg, orgSid, orgType, examDataObj, cid, orgName, row, s_org)
		else:
			msg2js('カルテID:{cid}, 団体番号:{norg}, 団体名：{orgName} {msg}'.format(cid=cid, norg=n_org, orgName=orgName, msg='団体番号に紐づく団体がないため団体紐づけ処理をスキップしました'))

	return retOrgSid


# xml_externalLinkageの取得
def getExternalLinkageXML(sidMorg, sidAppoint, sidExaminee):
	data = None
	try:
		# def extInfoGet2(sidMorg, *, plgName=None, sidAppoint=None, sidExaminee=None):
		tmp = t_ext_info.extInfoGet2(sidMorg, plgName=pConfig['plgName'], sidAppoint=sidAppoint, sidExaminee=sidExaminee)
		if tmp is not None and len(tmp) > 0:
			data = tmp[0]
	except Exception as err:
		msg2js('連携情報テーブルの取得でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] t_ext_info get faild, msg:{e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
	return data


# xml_externalLinkageの作成
def createExtLinkXML(sidMorg, tAppoint, dtObj, courseId=None):
	data = {
		'newFlag': False,
		'raw': None,
		'updTime': None,
		'xml': None
	}

	xmlStr = None
	nowTime = datetime.datetime.now()

	data['raw'] = getExternalLinkageXML(sidMorg, tAppoint['sid_appoint'], tAppoint['sid_examinee'])

	try:
		if data['raw'] is not None and data['raw']['xml_info'] is not None and len(data['raw']['xml_info']) > 0:
			xmlObj = plgCmn.xml2Obj(data['raw']['xml_info'])
		else:
			xmlObj = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['extLink']['1']))
			data['newFlag'] = True
	except Exception as err:
		msg2js('連携情報XMLの取得でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] xml_externalLinkage get faild, msg:{e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
		return None

	try:
		# 連携情報格納用のタグチェック
		elObj = xmlObj.find('.//external_linkage')
		# タグがなければ作成する
		if elObj is None: elObj = ET.SubElement(xmlObj, 'external_linkage')
		courseObj = elObj.find('./courseInfo')
		if courseObj is None: courseObj = ET.SubElement(elObj, 'courseInfo')
		courseUpdObj = courseObj.find('./updateTime')
		if courseUpdObj is None: courseUpdObj = ET.SubElement(courseObj, 'updateTime')
		courseIdObj = courseObj.find('./courseId')
		if courseIdObj is None: courseIdObj = ET.SubElement(courseObj, 'courseId')
		# 時刻情報の格納
		if data['newFlag'] == True:
			if dtObj is not None:
				courseUpdObj.text = datetime.datetime.strftime(dtObj, '%Y/%m/%d %H:%M:%S')
			else:
				courseUpdObj.text = datetime.datetime.strftime(nowTime, '%Y/%m/%d %H:%M:%S')
		elif data['newFlag'] == False and dtObj is not None:
			courseUpdObj.text = datetime.datetime.strftime(dtObj, '%Y/%m/%d %H:%M:%S')

		# コースIDの格納
		if courseId is not None:
			courseIdObj.text = courseId

		xmlStr = ET.tostring(xmlObj, encoding='UTF-8').decode('UTF-8')

	except Exception as err:
		msg2js('連携情報XMLの作成でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] xml_externalLinkage create faild: {e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
		return None

	data['updTime'] = courseUpdObj.text
	data['xml'] = xmlStr

	return data


# 新規登録用のXMLMEを取得
def getXmlMeTemplate(sidMorg, sidMe, cSidcriterion):
	try:
		query = 'SELECT * FROM m_me WHERE sid_morg = ? AND sid = ? AND sid_criterion = ? AND status = 1;'
		param = (sidMorg, sidMe, cSidcriterion)
		rows = sql(query, param)
		if rows is None:
			log('[{sidMorg}] [m_me] Course not found, courseSid:{courseSid}, sidMe:{sidMe}'.format(sidMorg=sidMorg, courseSid=cSidcriterion, sidMe=sidMe))
			return None

	except Exception as err:
		msg2js('コース情報の取得でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)

	return rows[0]


# 受診者の登録
def setExaminee(sidMorg, examDataObj, examData):
	regDateFormat1 = re.compile(r'([0-9]{4})([0-9]{2})([0-9]{2})')					# TODO: 区切り文字なし（19990101）
	regDateFormat2 = re.compile(r'([0-9]{4})/([0-9]{1,2})/([0-9]{1,2})')			# TODO: 区切り文字あり（1999/01/01 or 1999/1/1）など

	regPtTag1 = re.compile(r'^examinee/status/emphasis_information$')
	regPtTag2 = re.compile(r'^examinee/status/medical_information$')
	regPtTag3 = re.compile(r'^examinee/status/personal_information$')

	sid_examinee = None
	if examDataObj is not None and examDataObj['sid_examinee'] is not None:
		sid_examinee = examDataObj['sid_examinee']

	try:
		# sid_examineeがない場合、新規登録扱いで処理を継続
		if sid_examinee is None:
			log('[{sidMorg}] examinee data is new registration'.format(sidMorg=sidMorg))
		# sid_examineeがある（登録済み）、更新日時情報がない場合、更新しない
		elif sid_examinee is not None and examData['UpdateTime'] is None:
			log('[{sidMorg}] examinee data is no update, UpdateTime is nothing'.format(sidMorg=sidMorg))
			return str(examDataObj['raw']['sid'])
		# DB上の日付より、受け取ったデータの日時が古い場合は処理しない
		elif examData['UpdateTime'] is not None and examDataObj['raw']['dt_upd'] > plgCmn.text2datetime(examData['UpdateTime']):
			log('[{sidMorg}] examinee data update date is old, DB is new, Registration skip'.format(sidMorg=sidMorg))
			return str(examDataObj['raw']['sid'])
		# DB上の日付より、受け取ったデータの日時が新しい場合、処理継続
		elif examData['UpdateTime'] is not None and examDataObj['raw']['dt_upd'] < plgCmn.text2datetime(examData['UpdateTime']):
			log('[{sidMorg}] examinee data is new, next proc'.format(sidMorg=sidMorg))
		else:
			log('[{sidMorg}] examinee data condition mismatch, do not register'.format(sidMorg=sidMorg))
			return None
	except Exception as err:
		msg2js('受診者登録のチェック処理でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] msg:{e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
		return None


	try:
		xmlObj = examDataObj['xmlObj']
		#for examData in data:
		# 受診者情報のXML当て込み
		for xmlKey,csvKey in examineeMap.items():
			if csvKey in examData and examData[csvKey] is not None:
				textData = examData[csvKey]
				if xmlKey == 'examinee/birthday':
					if regDateFormat1.match(textData):			# 区切り文字なし
						textData = regDateFormat1.sub('\1/\2/\3', textData)
					elif regDateFormat2.match(textData):		# 区切り文字あり
						textData = regDateFormat1.sub('\1/\2/\3', textData)
					if plgCmn.dateFormatCheck(textData) == False:
						log('[{sidMorg}] date format check faild, csvText:[{orgDay}]'.format(sidMorg=sidMorg, orgDay=textData))
						return None
					textData = datetime.date.strftime(datetime.datetime.strptime(textData, '%Y/%m/%d'), '%Y/%m/%d')		# FIXME: 日付フォーマットの変換が必要かも

				# 国コード／言語コード対応
				elif xmlKey == 'examinee/nationality':
					if examData[csvKey] in countryAndLang:
						if optionMap['f_CountryCode2langCode'] == 1:
							xmlObj.find('examinee/locale').text = list(countryAndLang[examData[csvKey]].values())[0]
							xmlObj.find('examinee/nationality').text = list(countryAndLang[examData[csvKey]].keys())[0]
							continue
					else:
						continue
				elif xmlKey == 'examinee/locale':
					# 強制フラグが無効以外は場合はスキップ
					if optionMap['f_CountryCode2langCode'] != 0:
						continue

				# 特定タグに一致した場合の個別処理
				# emphasis_information / medical_information / personal_information
				elif regPtTag1.match(xmlKey) is not None or regPtTag2.match(xmlKey) is not None or regPtTag3.match(xmlKey) is not None:
					if textData is not None:
						# 空白
						if len(textData) < 1:
							textData = None
						# 有効
						elif int(textData) == 1:
							textData = '1'
						# 無効
						elif int(textData) == 2:
							textData = '0'
						else:
							textData = None

				try:
					xmlObj.find(xmlKey).text = textData
				except Exception as err:
					traceLog(err)
					log('[{sidMorg}] xmlKey: {xmlKey}, csvKey: {csvKey}, textData: {textData}, msg:{eMsg}'.format(sidMorg=sidMorg, xmlKey=xmlKey, csvKey=csvKey, textData=textData, eMsg=err))
	except Exception as err:
		msg2js('受診者XMLの作成でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)
		return None

	# 標準送付先住所の扱い
	try:
		addressDstTag = 'examinee/contact/destination'
		# TODO: 値が未設定の場合のみ、初期値として最初に値が存在する枠を選択する
		if xmlObj.find(addressDstTag).text is None:
			addressCheckTag = ('examinee/contact/address1', 'examinee/contact/address2', 'examinee/contact/address3')
			for n, key in enumerate(addressCheckTag):
				if xmlObj.find(key).text is not None and len(xmlObj.find(key).text) > 0:
					xmlObj.find(addressDstTag).text = str(n + 1)
					break

	except Exception as err:
		msg2js('受診者住所の設定でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] msg: {e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)

	# DBへの登録
	try:
		# 受診者の新規登録の場合、sidタグが不要なので削除を行うこと
		if sid_examinee is None:
			[elm_exam.remove(elm) for elm_exam in xmlObj.iter('examinee') for elm in elm_exam.iter() if elm.tag == 'sid']
		else:
			xmlObj.find('examinee/sid').text = sid_examinee

		xmlStr = ET.tostring(xmlObj, encoding='UTF-8').decode('UTF-8')

		rows = m_examinee.setExamineeXml(sidMorg=sidMorg, xml=xmlStr, sid=sid_examinee)
		if rows is not None and 'sid' in rows and rows['sid'] is not None:
			sid_examinee = str(rows['sid'])
		else:
			return None
	except Exception as err:
		msg2js('受診者登録でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] msg:{e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
		return None

	return sid_examinee


# sid_appointとXMLの取得
def getSidExaminee(sidMorg, cid):
	data = {
		'karuteId': None,
		'sid_examinee': None,
		'xmlObj': None,
		'raw': None,
		'xOrg': None,
	}

	try:
		log('[{sidMorg}] search m_examinee, karuteID:{cid}'.format(sidMorg=sidMorg, cid=cid))

		row = m_examinee.searchExaminee(sidMorg=sidMorg, examId=plgCmn.customNormalize(cid))
		if row is not None:
			data['sid_examinee'] = str(row[0]['sid'])
			data['xmlObj'] = plgCmn.xml2Obj(row[0]['xml_examinee'])
			data['karuteId'] = data['xmlObj'].find('./examinee/id').text
			data['raw'] = row[0]
		else:
			# 人テンプレXML
			data['xmlObj'] = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['examinee']['1']))
	except Exception as err:
		msg2js('受診者情報の取得でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)

	try:
		# 紐づけ団体の検索
		rows = m_org.searchXorgId(sidMorg, sidExaminee=data['sid_examinee'])
		data['xOrg'] = rows
	except Exception as err:
		msg2js('紐づけ団体の取得でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)

	return data


# XMLMEから要素／項目／グループのsidとsid_criterionを抽出
def getXMLMEcriterion(tAppointRow):
	try:
		meCriterion = defaultdict(lambda: defaultdict(set))
		xmlObj = plgCmn.xml2Obj(tAppointRow['xml_me'])

		meCriterion['equipment'] = {xobj.find('s_equipment').text:xobj.find('count').text for xobj in xmlObj.findall('.//equipment')}
		meCriterion['ecourse'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//ecourse')}
		meCriterion['egroup'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//egroup')}
		meCriterion['eitem'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//eitem')}
		meCriterion['element'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//element')}
	except Exception as err:
		msg2js('コース情報の抽出処理でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)

	return meCriterion


# 予約新規登録
def setTappointNew(sidMorg, vid, apoDt, sid_examinee, sidMe, xmlMe, data, remarks, contractInfo):
	try:
		sid_appoint = None
		sid_contract = None
		SOrg = None
		contractRows = None
		# XMLテンプレ(ccard)読み込み
		xmlCcard = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['ccard']['1']))
		if xmlCcard is not None:
			xmlCcard = ET.tostring(xmlCcard, encoding='UTF-8').decode('UTF-8')
		# XMLテンプレ(appoint)読み込み
		xmlAppoint = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['appoint']['1']))
		if xmlAppoint is not None:
			if 'psid_appoint' in appointMap and appointMap['psid_appoint'] in data:
				xmlAppoint.find('./appoint/appoint_info/psid_appoint').text = str(data[appointMap['psid_appoint']])
			if 'psid_me' in appointMap and appointMap['psid_me'] in data:
				xmlAppoint.find('./appoint/appoint_info/psid_me').text = str(data[appointMap['psid_me']])
			if 'inspection_date' in appointMap and appointMap['inspection_date'] in data:
				xmlAppoint.find('./appoint/appoint_info/inspection_date').text = str(data[appointMap['inspection_date']])
			xmlAppoint = ET.tostring(xmlAppoint, encoding='UTF-8').decode('UTF-8')

		# TODO：団体登録が必要なら処理を作成する
		#t_XmlObj_org = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['org']['1']))

		if 'SOrg' in appointMap and appointMap['SOrg'] in data:
			SOrg = str(data[appointMap['SOrg']])
		# 契約情報取得
		if SOrg is not None:
			contractRows = t_contract.getSidContract(sidMorg, sidExaminee=sid_examinee, dtAppoint=apoDt, sOrg=SOrg)

		# 契約SIDセット
		if contractRows is not None:
			if len(contractRows) > 0:
				sid_contract = contractRows[0]['sid']

		if sid_contract is None:
			if contractInfo is not None and 't_contract_me_sid_contract' in contractInfo and contractInfo['t_contract_me_sid_contract'] is not None:
				sid_contract = contractInfo['t_contract_me_sid_contract']

		# 予約がある場合
		rows = t_appoint.setTappointPut(sidMorg, vid=vid, apoDt=apoDt, sidExaminee=sid_examinee, sidMe=sidMe, xmlMe=xmlMe, xmlCcard=xmlCcard, xmlAppoint=xmlAppoint, sidContract=sid_contract)
		if rows is not None and rows[0]['sid'] != 0:
			sid_appoint = rows[0]['sid']

		log('[{sidMorg}] setTappointNew [row: {row}]'.format(sidMorg=sidMorg, row=rows))
	except Exception as err:
		msg2js('予約登録処理でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)

	return sid_appoint


# XMLMEや基準やマッピングコード
def getXmlMeInfo(sidMorg, tAppoint, courseMapInfo, data, useContractInfo):
	retData = {}
	meXmlObj = None
	meCriterionData = None
	criterionSid = None
	inspCodeMap = None
	inspDataPickUp = []
	contractAttribExam = None
	try:
		# tAppointが存在する
		if tAppoint is not None:
			meXmlObj = plgCmn.xml2Obj(tAppoint['xml_me'])
			# me内を漁る
			meCriterionData = getXMLMEcriterion(tAppoint)
		# tAppointがない場合、m_meからXMLMEを取得する
		else:
			rows = m_me.getMe(sidMorg, sidMe=courseMapInfo['sidMe'], sid_criterion=courseMapInfo['sid'])
			if rows is not None and len(rows[0]['xml_me']) > 0:
				meXmlObj = plgCmn.xml2Obj(rows[0]['xml_me'])
				meCriterionData = m_criterion.getXMLMEcriterion(rows[0]['xml_me'])
		if meCriterionData is not None:
			# 基準の取得
			criterionSid = m_criterion.getCriterionCourse(sidMorg, meCriterionData=meCriterionData)
	except Exception as err:
		msg2js('コースXMLの取得でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)

	try:
		if courseMapInfo['sid'] not in criterionSid:
			log('[{}] does not match XMLME courseSid, courseSid:{}, criterionSid:{}'.format(sidMorg, courseMapInfo['sidMe'], criterionSid))
			return None
	except Exception as err:
		msg2js('コースSIDの比較でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)
		return None

	try:
		# 標準／オプションの取得
		meAttrib = m_me_attribute.getMeAttributeData(sidMorg, sidMe=courseMapInfo['sidMe'], courseSid=courseMapInfo['sid'])
		meAttribExam = {sid: {k: v for k, v in item.items()} for sid,item in meAttrib['eitem'].items()}

		if useContractInfo is not None:
			contractXmlObj = plgCmn.xml2Obj(useContractInfo['t_contract_me_xml_attribute'])
			_tmp = {}
			for x in contractXmlObj.findall('.//consultation'):
				_f_exam = None
				_f_intended = None
				_sid = x.find('./sid').text
				if x.find('./s_exam').text != '1004': continue
				elif x.find('./f_exam') is None and x.find('./f_intended') is None: continue
				# 契約のXML内にタグがない場合はm_me(meAttribExam)から値を取り込む
				# f_exam
				if x.find('./f_exam') is not None:
					_f_exam = x.find('./f_exam').text
				# データがないのでm_meを継承
				if _f_exam is None:
					_f_exam = meAttribExam[_sid]['f_exam']

				# f_intended
				if x.find('./f_intended') is not None:
					_f_intended = x.find('./f_intended').text
				# データがないのでm_meを継承
				if _f_intended is None:
					_f_intended = meAttribExam[_sid]['f_intended']

				_tmp[_sid] = {'f_exam': _f_exam, 'f_intended': _f_intended}
			if len(_tmp) > 0:
				contractAttribExam = _tmp

		# 契約情報でフラグ上書き
		if contractAttribExam is not None and len(contractAttribExam) > 0:
			meAttribExam.update(contractAttribExam)
	except Exception as err:
		msg2js('標準、オプションの設定処理でエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{}] get inspcode faild, {}'.format(sidMorg, err))
		traceLog(err)

	if criterionSid is not None:
		# 予約専用フラグONの場合、マッピングコードの取得はしない
		if 'f_appoint_only' in optionMap and optionMap['f_appoint_only'] == 1:
			inspCodeMap = {}
			inspDataPickUp = {}
		else:
			try:
				# 外注マッピングの取得
				inspCodeMap = None
				courseXMLObj = plgCmn.xml2Obj(criterionSid[courseMapInfo['sid']]['course'][courseMapInfo['sidMe']]['xml_criterion'])
				outsourcingInspectionMap = m_eorg.getOutsourcingMap(sidMorg, courseXMLObj=courseXMLObj)
				if outsourcingInspectionMap is None:
					log('[{}] erog code not found, target:[{}]'.format(sidMorg, courseMapInfo))
					return None
				# 項目コードだけ欲しい
				if outsourcingInspectionMap['ei'] is not None:
					inspCodeMap = {k: v['req'] for k, v in outsourcingInspectionMap['ei'].items()}
				if inspCodeMap is None:
					log('[{}] get inspcode faild'.format(sidMorg))
					return None
				# データ内に含まれるマッピングコードと一致するアイテムのみ抽出
				for key in inspCodeMap.values():
					checkItem = list(set(key) & set(data.keys()))
					if len(checkItem) < 1: continue
					for key2 in checkItem:
						if data[key2] is None and len(data[key2]) < 1: continue
						inspDataPickUp.append(key2)

			except Exception as err:
				msg2js('外注マッピングの取得でエラーが発生しました。err:[{err}]'.format(err=err))
				traceLog(err)

	retData['meXmlObj'] = meXmlObj
	retData['criterionSid'] = criterionSid
	retData['inspCodeMap'] = inspCodeMap
	retData['inspDataPickUp'] = inspDataPickUp
	retData['meAttribExam'] = meAttribExam
	retData['contractAttribExam'] = contractAttribExam

	return retData


# 新規作成
def createXmlMe(sidMorg, visitId, cid, apoDt, sidMe, courseSid, sid_examinee, row, xmlMeInfo, remarks, contractInfo):
	global errMsg
	if apoDt is not None:
		_apoDt = apoDt.date()
	else:
		_apoDt = None

	# ログ出力用ベース情報
	logExamInfo = 'visitId: {vid}, karuteId: {cid}, apoDay: {apoDay}, sid_examinee: {sidExam}, courseSid: {courseSid}, sidMe: {sidMe}'.format(vid=visitId, cid=cid, apoDay=_apoDt, sidExam=sid_examinee, courseSid=courseSid, sidMe=sidMe)

	if contractInfo is not None and _apoDt is not None:
		_dfrDt = contractInfo['dfr_contract'].date()
		_dtoDt = contractInfo['dto_contract'].date()
		if not (_dfrDt <= _apoDt and _apoDt <= _dtoDt):
			log('Since the consultation date is outside the contract period, reservation registration will be skipped, dt_appoint:[{}], dfr_contract:[{}], dto_contract:[{}]'.format(_apoDt, _dfrDt, _dtoDt))
			msg2js('カルテID:{cid}, {msg}'.format(cid=cid, msg='受診日が契約期間外のため、予約登録をスキップします'))
			msg = 't_contract Information is not valid, karuteId:[{}]'.format(cid)
			errMsg.append(msg)
			return None

	sid_appoint = None
	log('[{sidMorg}] create new {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
	# meの取得
	meXmlObj = xmlMeInfo['meXmlObj']
	# 基準の取得
	criterionSid = xmlMeInfo['criterionSid']
	# 外注マッピングの取得
	inspCodeMapAll = xmlMeInfo['inspCodeMap']
	# 検査項目のピックアップ
	# inspDataPickUp = list(set(xmlMeInfo['inspDataPickUp']))
	# マッピング登録されている要素のみを抽出
	inspEieSid = {k:v for k,v in inspCodeMapAll.items() if v is not None}
	# eitemのリスト
	ele2eitem = criterionSid[courseSid]['ele2eitem']
	# 設定対象のelementと一致するものをマッピングリストから抽出
	matchingEieSid = {k : inspEieSid[k] for k in set(inspEieSid.keys()) & set(ele2eitem.values())}
	# XMLMEに組まれているeitemのリスト
	eItemList = set(ele2eitem.values())
	# オプション扱いの項目のみ抽出
	# f_exam=1（オプション）、2（標準）
	eItemOptionList = [sid for sid, item in xmlMeInfo['meAttribExam'].items() if item['f_exam'] == '1']

	checkOptItem = None
	if eItemList is not None and len(eItemList) > 0:
		checkOptItem = set(eItemList) & set(eItemOptionList)

	# f_intendedタグを全てONで作成
	for iSid in eItemList:
		# オプションの場合、f_intendedはデフォルトOFFで作成
		if iSid in checkOptItem:
			deffIntendedFlag = fIntendedFlag.OFF
			if iSid in xmlMeInfo['meAttribExam'] and 'f_intended' in xmlMeInfo['meAttribExam'][iSid]:
				# オプション、かつ、受診対象というパターンが存在する
				if xmlMeInfo['meAttribExam'][iSid]['f_intended'] == fIntendedFlag.ON:
					deffIntendedFlag = fIntendedFlag.ON
			else:
				log('Failed to get f_intended(option), item sid: {iSid}, set default value'.format(iSid=iSid))
		else:
			deffIntendedFlag = fIntendedFlag.ON
			if iSid in xmlMeInfo['meAttribExam'] and 'f_intended' in xmlMeInfo['meAttribExam'][iSid]:
				# 必須、かつ、対象外のパターンもあり得る
				if xmlMeInfo['meAttribExam'][iSid]['f_intended'] == fIntendedFlag.OFF:
					deffIntendedFlag = fIntendedFlag.OFF
			else:
				log('Failed to get f_intended(required), item sid: {iSid}, set default value'.format(iSid=iSid))

		try:
			fobj = meXmlObj.find('eitems/eitem/[sid="{}"]'.format(iSid))
			# タグが存在しない場合は作成
			if fobj.find('f_intended') is None:
				f_intendedObj = ET.SubElement(fobj, 'f_intended')
				f_intendedObj.text = deffIntendedFlag
			# 存在する場合は値を格納
			else:
				fobj.find('f_intended').text = deffIntendedFlag
		except Exception as err:
			msg2js('検査項目の受診チェック処理でエラーが発生しました。err:[{err}]'.format(err=err))
			log('[{sidMorg}] f_intended tag create faild, item sid: {iSid}'.format(sidMorg=sidMorg, iSid=iSid))
			traceLog(err)

	# f_intendedの中身を変更するためのデータ収集
	flagCheckDataTmp = defaultdict(list)
	for eSid,iSid in ele2eitem.items():
		# 受け取ったファイルにデータが存在したら、格納
		if iSid in matchingEieSid:
			try:
				matchKeyData = list(set(matchingEieSid[iSid]) & set(row.keys()))
				if len(matchKeyData) == 1:
					matchKey = matchKeyData[0]
					if row[matchKey] is not None and len(row[matchKey]) > 0:
						flagCheckDataTmp[iSid].append(int(row[matchKey]))
				elif len(matchKeyData) > 1:
					log('[{sidMorg}] multiple key, eSid:{esid}, iSid:{isid}, data: {d}'.format(sidMorg=sidMorg, esid=eSid, isid=iSid, d=matchKeyData))
				else:
					log('[{sidMorg}] mapping code not found, eSid:{esid}, iSid:{isid}'.format(sidMorg=sidMorg, esid=eSid, isid=iSid))
			except Exception as err:
				msg2js('検査項目のデータ収集処理でエラーが発生しました。err:[{err}]'.format(err=err))
				traceLog(err)

	flagCheckData = {k: set(v) for k,v in flagCheckDataTmp.items() if v is not None}

	# f_intendedの中身を変更する
	for iSid,flag in flagCheckData.items():
		if iSid not in criterionSid[courseSid]['eitem']:
			log('[{sidMorg}] unknown iSid: {iSid}, criterionMap not in'.format(sidMorg=sidMorg, iSid=iSid))
			continue
		try:
			fobj = meXmlObj.find('eitems/eitem/[sid="{}"]'.format(iSid))
			# ON優先
			if appointAct.register in flag:
				fobj.find('f_intended').text = fIntendedFlag.ON
			else:
				fobj.find('f_intended').text = fIntendedFlag.OFF

		except:
			msg2js('検査項目の受診チェックの変更でエラーが発生しました。err:[{err}]'.format(err=err))
			log('[{sidMorg}] f_intended changed faild, itemSid: {isid}, msg: {e}'.format(sidMorg=sidMorg, e=err, isid=iSid))
			traceLog(err)
			continue

	xmlStr = ET.tostring(meXmlObj, encoding='UTF-8').decode('UTF-8')



	# meの登録
	sid_appoint = setTappointNew(sidMorg, visitId, apoDt, sid_examinee, sidMe, xmlStr, row, remarks, contractInfo)
	if sid_appoint is None:
		log('[{sidMorg}] t_appoint add faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
	else:
		log('[{sidMorg}] t_appoint add success, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))

	return sid_appoint


# XMLMEの更新
def updateXmlMe(sidMorg, cid, tAppoint, courseSid, data, xmlMeInfo):
	# ログ出力用ベース情報
	logExamInfo = 'visitId: {vid}, karuteId: {cid}, apoDay: {apoDay}, sid_examinee: {sidExam}, courseSid: {courseSid}, sidMe: {sidMe}'.format(
		vid=tAppoint['visitid'], cid=cid, apoDay=tAppoint['dt_appoint'], sidExam=tAppoint['sid_examinee'], courseSid=courseSid, sidMe=tAppoint['sid_me']
		)

	dtUpd1stFlag = False
	ret = None
	sid_appoint = tAppoint['sid']

	# インポート用データに検査項目が含まれない場合XMLMEの更新は行わない
	if len(xmlMeInfo['inspDataPickUp']) < 1:
		log('[{sidMorg}] no insp operation, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
		return sid_appoint

	log('[{sidMorg}] [XMLME] start update, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))

	# meの取得
	meXmlObj = xmlMeInfo['meXmlObj']
	# 基準の取得
	criterionSid = xmlMeInfo['criterionSid']
	# 外注マッピングの取得
	inspCodeMapAll = xmlMeInfo['inspCodeMap']
	# 検査項目のピックアップ
	inspDataPickUp = list(set(xmlMeInfo['inspDataPickUp']))
	# マッピング登録されている項目のみを抽出
	inspEieSid = {k: v for k,v in inspCodeMapAll.items() if v is not None}
	# eitemのリスト
	ele2eitem = criterionSid[courseSid]['ele2eitem']
	# 設定対象のitemと一致するものをマッピングリストから抽出
	matchingEieSid = {k : inspEieSid[k] for k in set(inspEieSid.keys()) & set(ele2eitem.values())}
	# XMLMEに組まれているeitemのリスト
	eItemList = set(ele2eitem.values())
	# オプション扱いの項目のみ抽出
	# f_exam=1（オプション）、2（標準）
	eItemOptionList = [sid for sid, item in xmlMeInfo['meAttribExam'].items() if item['f_exam'] == '1']
	# 項目コードに対応するマッピングコードの抽出
	targetFintendedItem = {k: list(set(v) & set(inspDataPickUp))[0] for k, v in matchingEieSid.items() if len(set(v) & set(inspDataPickUp)) > 0}

	checkOptItem = None
	targetOptItem = None
	if eItemList is not None and len(eItemList) > 0:
		checkOptItem = set(eItemList) & set(eItemOptionList)
		targetOptItem = set(checkOptItem) ^ set(targetFintendedItem)

	# マッピング済みデータが1件以上存在
	if len(matchingEieSid) > 0:
		flagCheckData = None
		# f_intendedの操作のみを行う
		for iSid, mapCodeList in matchingEieSid.items():
			f_intendedFlag = None
			iSidCriterion = None

			# マッピングコードが複数登録されている場合、データ内に一致するものがあるのかを検索する
			try:
				mapCode = None
				matchKeyData = list(set(mapCodeList) & set(data.keys()))
				if len(matchKeyData) == 1:
					mapCode = matchKeyData[0]
					if data[mapCode] is not None and len(data[mapCode]) > 0:
						flagCheckData = str(int(data[mapCode]))
				elif len(matchKeyData) > 1:
					log('[{sidMorg}] multiple mapping code, iSid:{isid}, data: {d}'.format(sidMorg=sidMorg, isid=iSid, d=matchKeyData))
					continue
				else:
					log('[{sidMorg}] mapping code not in data, iSid:{isid}'.format(sidMorg=sidMorg, isid=iSid))
			except Exception as err:
				traceLog(err)
				continue

			try:
				# オプション項目のチェック
				if iSid in checkOptItem:
					fobj = meXmlObj.find('.//eitem/[sid="{}"]'.format(iSid))
					# XMLMEに検査項目が存在しない
					if fobj is None:
						log('[{sidMorg}] optional inspection not in XMLME [eItemSidExam: {isid}, name:{name}]'.format(sidMorg=sidMorg, isid=iSid, name=mapCode))
						continue

					iSidCriterion = fobj.find('sid_criterion').text
					f_intendedObj = fobj.find('f_intended')
					# データ内に値が存在した
					if iSid in targetFintendedItem:
						# 値が同じなら何もしない
						if f_intendedObj.text == flagCheckData:
							log('[{sidMorg}] optional inspection f_intended no changed, isid:{isid}, xml:{a}, data:{b}, code:{c}'.format(sidMorg=sidMorg, a=f_intendedObj.text, b=flagCheckData, isid=iSid, c=matchKeyData))
							continue
						else:
							f_intendedFlag = flagCheckData

					# データ内にオプション項目がない、かつ、存在しないオプション項目を未実施扱いにする場合
					elif 'f_inspOptNotExistForceDisable' in optionMap and optionMap['f_inspOptNotExistForceDisable'] == 1:
						if f_intendedObj is not None and f_intendedObj.text == '1':
							log('[{sidMorg}] optional inspection f_intended no changed, isid:{isid}, xml:{a}, data:{b}'.format(sidMorg=sidMorg, a=f_intendedObj.text, b=flagCheckData, isid=iSid))
							f_intendedFlag = '0'

					# 処理対象の項目
					elif iSid in targetOptItem:
						# OFFなら何もしない
						if f_intendedObj is not None and f_intendedObj.text == '0':
							continue
						f_intendedFlag = 0
						log('[{sidMorg}] optional inspection f_intended off [eItemSidExam: {isid}, name:{name}]'.format(sidMorg=sidMorg, isid=iSid, name=mapCode))

					# 何もしない
					else:
						log('[{sidMorg}] optional inspection f_intended no changed, not in item list [eItemSidExam: {isid}, name:{name}]'.format(sidMorg=sidMorg, isid=iSid, name=mapCode))
						continue

				# 標準項目
				else:
					if mapCode is not None and mapCode in data:
						f_intendedFlag = int(data[mapCode]) if data[mapCode] is not None and len(data[mapCode]) > 0 else None

			except Exception as err:
				msg2js('オプションの受診チェック処理でエラーが発生しました。err:[{err}]'.format(err=err))
				traceLog(err)

			# なにかしらの理由で、OFF/ONフラグの指定がされていない
			if f_intendedFlag is None:
				log('[{sidMorg}] isid: {isid}, name: {name}, f_intendedFlag is None, proc skip'.format(sidMorg=sidMorg, isid=iSid, name=mapCodeList))
				continue

			try:
				# 履歴作成のためにdt_updだけを初回のみ更新かける
				if dtUpd1stFlag == False:
					t_appoint.setTappointDtUpd(sidMorg, sidAppoint=sid_appoint)
					dtUpd1stFlag = True

				ret = sid_appoint
				# とりあえず予約取込時はxml_meを更新しない
				#rows = t_appoint_me.setUpdateXMLME(sidMorg, sidAppoint=sid_appoint, elementSidExam=None, elementVal=None, eitemSidExam=iSidCriterion, valueForm=None, f_intendedOnly=f_intendedFlag)
				#if ret is None and rows is not None and rows[0]['sid'] is not None and rows[0]['sid'] == int(sid_appoint):
				#	ret = rows[0]['sid']
				#log('[{sidMorg}] [XMLME] update return row: {row}'.format(sidMorg=sidMorg, row=rows))

			except Exception as err:
				msg2js('更新日時の更新でエラーが発生しました。err:[{err}]'.format(err=err))
				log('[{sidMorg}] [XMLME] update failed found [eItemSidExam: {isid}, name:{name}], msg:{e}'.format(sidMorg=sidMorg, isid=iSid, name=mapCode, e=err))
				traceLog(err)
				continue

		# 1件も更新できなかった
		if ret is None:
			log('[{sidMorg}] no data update, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			ret = int(sid_appoint)

	else:
		# 更新データ0件の場合
		log('[{sidMorg}] no data, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
		ret = int(sid_appoint)

	return ret


# 必須情報のチェック
def checkRequiredData(sidMorg, data):
	global errMsg
	ret = False
	errcnt = 0

	# 予約情報のチェック
	if procMode == modeAppoint:
		for k in requiredMap['appoint']:
			try:
				if data[appointMap[k]] is None or (type(data[appointMap[k]]) == str and len(data[appointMap[k]].strip()) < 1):
					errcnt += 1
					log('[{sidMorg}] appointMap is no data: {apoMap}'.format(sidMorg=sidMorg, apoMap=appointMap[k]))
					msg = 'required key check faild, keyName:{k}, data:[{d}]'.format(k=k, d=','.join(data.values()))
					msg2js('項目名:{k}, {msg}'.format(k=k, msg='必須項目が未設定ため、予約登録をスキップします'))
					errMsg.append(msg)
			except Exception as err:
				errcnt += 1
				log('[{sidMorg}] appointMap is no key: {apoMapKey} {err}'.format(sidMorg=sidMorg, apoMapKey=k, err=err))
				traceLog(err)
				msg = 'required key setting check faild, keyName:{k}'.format(k=k)
				errMsg.append(msg)
			continue

		if errcnt == 0:
			ret = True

	elif procMode == modeExam:
		# 属性情報のチェック
		for k in requiredMap['examinee']:
			try:
				if data[examineeMap[k]] is None or data[examineeMap[k]].strip() > 0 and len(data[examineeMap[k]].strip()) < 1:
					errcnt += 1
					log('[{sidMorg}] examineeMap is no data: {examMap}'.format(sidMorg=sidMorg, examMap=examineeMap[k]))
			except Exception as err:
				errcnt += 1
				log('[{sidMorg}] examineeMap is no key: {examMapKey}'.format(sidMorg=sidMorg, examMapKey=k))
				traceLog(err)
			continue

		if errcnt == 0:
			ret = True

	else:
		log('[{sidMorg}] unknwon proc mode: {p}'.format(sidMorg=sidMorg, p=procMode))

	return ret


# updateTimeの比較
def checkUpdateTime(sidMorg, row, tAppoint, logExamInfo):
	ret = updateTimeStatus.ignore

	if optionMap['f_courseUpdateTimeCheck'] != 1:
		return None

	log('[{sidMorg}] f_courseUpdateTimeCheck is enabled, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))

	# フラグが有効だが、keyがないのでエラー
	if dataNameMap['updateTime'] not in row:
		log('[{sidMorg}] {key} is not found, there is no updateime, {logExamInfo}'.format(sidMorg=sidMorg, key=dataNameMap['updateTime'], logExamInfo=logExamInfo))
		return ret
	# keyは存在するけどvalueがなければエラー
	if row[dataNameMap['updateTime']] is None or len(row[dataNameMap['updateTime']]) < 1:
		log('[{sidMorg}] {val} is not found, there is no updateime, {logExamInfo}'.format(sidMorg=sidMorg, val=row[dataNameMap['updateTime']], logExamInfo=logExamInfo))
		return ret

	try:
		# コース情報更新時刻の比較
		xmlEx = createExtLinkXML(sidMorg, tAppoint, plgCmn.text2datetime(row[dataNameMap['updateTime']]))
		tmp = None
		tmpCourseInfo = None
		if xmlEx['raw'] is not None and xmlEx['raw']['xml_info'] is not None:
			tmp = plgCmn.xml2Obj(xmlEx['raw']['xml_info'])
			tmpCourseInfo = tmp.find('./external_linkage/courseInfo')
		oldUpdTime = None
		if tmpCourseInfo is not None:
			oldUpdTime = tmpCourseInfo.find('updateTime').text if tmpCourseInfo.find('updateTime') is not None else None

		oldUpdObj = None
		if oldUpdTime is not None:
			oldUpdObj = plgCmn.text2datetime(oldUpdTime)

		newUpdObj = plgCmn.text2datetime(row[dataNameMap['updateTime']])
		# 新規作成データ
		if xmlEx['newFlag'] == True:
			ret = updateTimeStatus.new
		# DB上の更新時刻より、データ内の時刻が古い場合は処理しない
		elif oldUpdObj is not None and oldUpdObj >= newUpdObj:
			log('[{sidMorg}] the DB time is new and the data is old so do not process it, old:{o}, new:{n}, {logExamInfo}'.format(sidMorg=sidMorg, o=oldUpdObj, n=newUpdObj, logExamInfo=logExamInfo))
			return ret
		# データ内の時刻が新しい場合に処理継続
		elif oldUpdObj is not None and oldUpdObj < newUpdObj:
			ret = updateTimeStatus.update
		else:
			log('[{sidMorg}] appoint date is unknown, oldUpd:{o}, newUpd:{n}, {logExamInfo}'.format(sidMorg=sidMorg, o=oldUpdObj, n=newUpdObj, logExamInfo=logExamInfo))
			return ret

	except Exception as err:
		msg2js('コース情報の更新チェックでエラーが発生しました。err:[{err}]'.format(err=err))
		log('[{sidMorg}] datetime check error: {e}'.format(sidMorg=sidMorg, e=err))
		traceLog(err)
		raise

	return ret


# コース情報取得
def getCourseInfo(sidMorg, row):
	courseMapInfo = None

	# コースIDからコース情報の特定
	if appointMap['courseId'] in row and row[appointMap['courseId']] is not None:
		mapCourseID = row[appointMap['courseId']]
		if mapCourseID is None or len(mapCourseID) < 1:
			return -1
	else:
		return -1
	# コース情報から諸々取得
	for k in courseMap:
		if 'courseId' in k:
			if k['courseId'] is None:
				continue
			elif k['courseId'] == mapCourseID:
				courseMapInfo = k
	if courseMapInfo is None:
		return -2
	else:
		sidMe = courseMapInfo['sidMe']
		courseSidCriterion = courseMapInfo['sid']
	if sidMe is None or courseSidCriterion is None:
		return -3

	return courseMapInfo


# t_apo作成
# mode = 1:受診者登録, 2:予約登録
def setTappointMe(sidMorg, data):
	if data is None: return None
	global errMsg, courseMap
	dataCount = len(data)
	procCount = 0
	retStatus = error
	errRowData = []

	# コース情報取得
	courseMap = csv2xml_mapping.courseMapGet(sidMorg)

	for row in data:
		appointUpdFlag = None
		sidAppoint = None
		reApoSts = None
		courseMapInfo = None
		vid = None
		ordSts = None
		dataUpdTime = None
		cancelSts = None
		contractInfo = None
		useContractInfo = None

		# 必須項目のチェック
		retCheck = checkRequiredData(sidMorg, row)
		if retCheck == False:
			log('[{sidMorg}] no required data, row data: {row}'.format(sidMorg=sidMorg, row=row))
			errRowData.append(row)
			continue

		# カルテID取得
		cid = row[examineeMap['examinee/id']]
		if cid is None:
			log('[{sidMorg}] not examiee id data, row data: {row}'.format(sidMorg=sidMorg, row=row))
			msg2js('{msg}'.format(msg='カルテIDが未設定のため、予約登録をスキップします'))
			continue

		# 受診者検索＆xml_examineeの取得
		examDataObj = getSidExaminee(sidMorg, cid)
		sid_examinee = examDataObj['sid_examinee']

		# ログ出力用ベース情報
		logExamInfo = 'karuteId: {cid}, sid_examinee: {sidExam}'.format(cid=cid, sidExam=sid_examinee)

		# 処理モードが未定義は終わり
		if procMode not in [modeExam, modeAppoint]:
			log('[{sidMorg}] unknown data, Not an appointment / examination: {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			continue

		# 受診者処理モード
		if procMode == modeExam:
			# 受診者登録（新規／更新）
			sid_examinee = setExaminee(sidMorg, examDataObj, row)
			if sid_examinee is None:
				log('[{sidMorg}] examiee register failed, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				continue

			# 登録後の情報を再取得する
			examDataObj = getSidExaminee(sidMorg, cid)
			# 団体登録処理
			orgSid = procOrg(sidMorg, row, examDataObj, m_org.orgTypeCode['company'], None, cid)

			log('[{sidMorg}] org register successed, {orgSid}'.format(sidMorg=sidMorg, orgSid=orgSid))

		# 予約処理モード
		elif procMode == modeAppoint:
			# 予約処理時、受診者未登録の場合はスキップ
			if sid_examinee is None:
				msg = 'examiee not register. skip appoint regster'
				errMsg.append(msg)
				log('[{sidMorg}] {m}, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo, m=msg))
				msg2js('カルテID:{cid}, {msg}'.format(cid=cid, msg='受診者未登録のため、予約登録をスキップします'))
				continue

			# 団体登録処理
			orgSid = procOrg(sidMorg, row, examDataObj, m_org.orgTypeCode['company'], None, cid)

			# 登録後の情報を再取得する
			examDataObj = getSidExaminee(sidMorg, cid)

			# コース情報取得
			courseMapInfo = getCourseInfo(sidMorg, row)
			if courseMapInfo is None:
				msg = 'courseId is None'
				errMsg.append(msg)
				log('[{sidMorg}] {m}, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo, m=msg))
				errRowData.append(row)
				msg2js('カルテID:{cid}, コースID:{courseID}, {msg}'.format(cid=cid, courseID=row[appointMap['courseId']], msg='コース情報の取得に失敗したため、予約登録をスキップします'))
				continue
			elif courseMapInfo == -1:
				log('[{sidMorg}] courseId is get faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				msg2js('カルテID:{cid}, コースID:{courseID}, {msg}'.format(cid=cid, courseID=row[appointMap['courseId']], msg='取込ファイルにコースIDが未設定のため、予約登録をスキップします'))
				continue
			elif courseMapInfo == -2:
				log('[{sidMorg}] courseMapInfo is None, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				msg2js('カルテID:{cid}, コースID:{courseID}, {msg}'.format(cid=cid, courseID=row[appointMap['courseId']], msg='コースIDが未登録のため、予約登録をスキップします'))
				continue
			elif courseMapInfo == -3:
				log('[{sidMorg}] courseSid is None or sidMe is None, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				msg2js('カルテID:{cid}, コースID:{courseID}, {msg}'.format(cid=cid, courseID=row[appointMap['courseId']], msg='コースSIDの取得に失敗したため、予約登録をスキップします'))
				continue

			# 受付通し番号
			if 'f_force_visitId' in optionMap and int(optionMap['f_force_visitId']) == 1:
				try:
					vid = row[appointMap['visitId']]
				except:
					log('[{sidMorg}] visitId is not found, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
					msg2js('カルテID:{cid}, コース名:{courseName}, {msg}'.format(cid=cid, courseName=row['CourseName'], msg='受付通し番号が未設定のため、予約登録をスキップします'))
					continue

			logExamInfo += ', visitid: {vid}'.format(vid=vid)

			# 受診日取得
			tmpDateTime = row[appointMap['appointDay']].split(' ')
			examDate = re.sub(r'([0-9]{4})[/\-]?([0-9]{2})[/\-]?([0-9]{2})', r'\1/\2/\3', tmpDateTime[0])
			if appointMap['appointTime'] in row:
				examDateTime = None
				_examDateTime = row[appointMap['appointTime']].split(':')
				if len(_examDateTime) == 2:
					examDateTime = re.sub(r'([0-9]{1,2})[:]?([0-9]{1,2})', r'\1:\2:00', row[appointMap['appointTime']])
				elif len(_examDateTime) == 3:
					examDateTime = re.sub(r'([0-9]{1,2})[:]?([0-9]{1,2})[:]?([0-9]{1,2})', r'\1:\2:\3', row[appointMap['appointTime']])
				else:
					log('unknwon time format, data:[{}], default time set'.format(row[appointMap['appointTime']]))

				if examDateTime is None or len(examDateTime) < 1:
					# みつからない場合はデフォルトを入れる
					examDateTime = '00:00:00'
			else:
				# 分割チェック
				if len(tmpDateTime) == 2 and tmpDateTime[1] is not None and len(tmpDateTime[1]) > 0 and re.match(r'[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}', tmpDateTime[1]) is not None:
					examDateTime = tmpDateTime[1]
				else:
					# 予約時間不明／ない
					examDateTime = '00:00:00'

			if plgCmn.dateFormatCheck(examDate) == False:
				# あり得ない日付の場合はスキップ
				log('[{sidMorg}] appointDay format error, convDay:[{day}], csvText:[{dayOrg}]'.format(sidMorg=sidMorg, day=examDate, dayOrg=row[appointMap['appointDay']]))
				msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='受診日に不正な日付が設定されているため、予約登録をスキップします。'))
				errRowData.append(row)
				continue
			examDtObj = plgCmn.text2datetime(examDate + ' ' + examDateTime)


			# 設定コース情報が団体専用の場合
			if courseMapInfo['psid'] is not None and int(courseMapInfo['psid']) != 0:
				# TODO: 受診者に団体紐づけがなければスキップ
				if examDataObj['xOrg'] is None:
					f_orgCheck = True

					if optionMap['f_force_not_org_regist'] == 1:
						me_type = m_criterion.getMeType(sidMorg, courseMapInfo['sid'])

						if me_type is not None:
							force_not_org_regist = csv2xml_mapping.force_not_org_regist
							# 宿泊コースの2～3日目などは団体がなくても登録する
							if str(sidMorg) in force_not_org_regist and str(me_type) in force_not_org_regist[str(sidMorg)]:
								f_orgCheck = False

					if f_orgCheck:
						msg = 'group-only course. do not associate with the examinee'
						msg2js('カルテID:{cid}, コース名:{courseName}, {msg}'.format(cid=cid, courseName=row['CourseName'], msg='団体専用コースで受診者団体が未設定のため、予約登録をスキップします'))
						log('[{sidMorg}] {m}, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo, m=msg))
						errMsg.append(msg)
						continue
				# TODO: 契約の紐づけが存在する場合、該当契約情報で予約を取る。という処理を作成する必要がある。。。
				elif contractData is not None and len(contractData) > 0:
					try:
						contractInfo = [k for k in contractData if k['inCourseID'] is not None and k['inCourseID'] == courseMapInfo['courseId'] and k['s_upd'] < 3 and k['dfr_contract'].date() <= examDtObj.date() <= k['dto_contract'].date()]
						plgLog.debug('contract info found, data[{}]'.format(map(str, contractInfo)))
					except Exception as err:
						msg = 'Reservation processing skipped because acquisition of t_contract information failed, karuteId:[{}], courseId:[{}]'.format(cid, courseMapInfo['courseId'])
						msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDtObj.date(), msg='契約期間の判定に失敗したため、予約登録をスキップします'))
						errMsg.append(msg)
						del msg
						log('failed to get t_contract information')
						continue

					if contractInfo is not None and len(contractInfo) > 0 and examDataObj['xOrg'] is not None:
						try:
							# 有効な「所属団体　＞　地域　＞　社保／国保　＞　その他」を抽出してそーっと
							_orgList = [k for k in examDataObj['xOrg'] if k['f_current'] == 1 and k['s_upd'] < 3 and k['s_org'] in ['1', '10', '11', '12']]
							_orgSort = sorted(_orgList, key=lambda x: x['s_org'])
							# 優先順に団体sid、コースIDが一致するデータを契約情報ないから検索
							for _org in _orgSort:
								useContractInfo = [k for k in contractInfo if k['sid_corg'] == _org['sid_org']]
								if len(useContractInfo) > 0:
									useContractInfo = useContractInfo[0]
									break

							if len(useContractInfo) == 0:
								msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDtObj.date(), msg='指定した受診日、コース、団体で有効な契約が見つからないため、予約登録をスキップします'))
								continue

						except Exception as err:
							log('The contract organization and attribute information are not linked')
							msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='契約情報の取得に失敗したため、予約登録をスキップします。'))
							traceLog(err)
							continue
					else:
						msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDtObj.date(), msg='指定した受診日、コースで有効な契約が見つからないため、予約登録をスキップします'))
						continue

			# 備考欄
			remarks = None
			if 'remarks' in appointMap and appointMap['remarks'] in row and row[appointMap['remarks']]:
				remarks = row[appointMap['remarks']]

			# データ内に更新日時情報を持っている
			#if dataNameMap['updateTime'] in row and row[dataNameMap['updateTime']] is not None:
			#	dataUpdTime = plgCmn.text2datetime(row[dataNameMap['updateTime']])

			# ログ出力用ベース情報
			logExamInfo += ', apoDay: {apoDay}, courseSid: {courseSid}, courseId: {courseId}'.format(apoDay=examDate, courseSid=courseMapInfo['sid'], courseId=courseMapInfo['courseId'])

			# t_appointを検索
			tAppoint = t_appoint.getTappoint(sidMorg=sidMorg, vid=vid, cid=cid, apoDay=examDate, sidExaminee=sid_examinee)

			if tAppoint is None: # 見つからない場合は手動登録している場合があるのでvisit_idを外して再検索
				tAppoint = t_appoint.getTappoint(sidMorg=sidMorg, vid=None, cid=cid, apoDay=examDate, sidExaminee=sid_examinee)

			# コース連携情報格納用データを取得して最新レコードの更新ステータスが削除（s_upd=3）の場合、処理しない
			#if 'f_force_courseUpdLastStsCancelSkip' in optionMap and optionMap['f_force_courseUpdLastStsCancelSkip'] == 1:
			#	if tAppoint is not None and len(tAppoint) > 0:
			#		sidAppoint = tAppoint[0]['sid']
			#	# def extInfoGet(sidMorg, *, plgName=None, sidAppoint=None, vid=None):
			#	tmpData = t_ext_info.extInfoGet(sidMorg, plgName=pConfig['plgName'], sidAppoint=sidAppoint, vid=vid)
			#	if tmpData is not None and len(tmpData) > 0:
			#		tmpExtLinkData = [k for k in tmpData if k['dt_appoint'] == examDtObj]
			#		if len(tmpExtLinkData) > 0:
			#			# 最新1件のみ取得する
			#			tmpExtLinkDataSort = sorted(tmpExtLinkData, key=lambda x: x['dt_upd'], reverse=True)[0]
			#			del tmpData, tmpExtLinkData
			#			# 更新ステータスとコースIDのチェック
			#			extLinkXmlObj = plgCmn.xml2Obj(tmpExtLinkDataSort['xml_info'])
			#			tmpCourseId = None
			#			try:
			#				tmpCourseId = extLinkXmlObj.find('./external_linkage/courseInfo/courseId').text
			#			# XMLタグが存在しない場合は何もしない
			#			except:
			#				pass
			#			if tmpCourseId is not None and tmpExtLinkDataSort['visit_id'] == vid and tmpCourseId == courseMapInfo['courseId'] and dataUpdTime <= tmpExtLinkDataSort['update_time'] and tmpExtLinkDataSort['s_upd'] == 3:
			#				log('[{sidMorg}] t_ext_info table check, vid and courseId is match and s_upd == 3, proc skip [{logExamInfo}]'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			#				log('[{sidMorg}] If you want to register, set s_upd = 2 or change vid [{logExamInfo}]'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			#				continue

			# キャンセルアクションだが、該当するt_appointが存在しない場合は終わり
			if appointMap['apoAction'] in row and int(row[appointMap['apoAction']]) == appointAct.cancel and tAppoint is None:
				log('[{sidMorg}] Cancel action, but skip because t_appoint does not exist'.format(sidMorg=sidMorg))
				msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='予約情報が見つからないため、予約キャンセルをスキップします。'))
				continue

			# 検索結果が存在する
			if tAppoint is not None:
				# 検索結果が複数の場合
				# if len(tAppoint) > 1:
				#	log('[{sidMorg}] t_appoint check return Multiple, use row[0]'.format(sidMorg=sidMorg))

				tmpApp = None

				for app in tAppoint:
					if 'inCourseID' not in app:
						continue
					else:
						# コースIDが一致するものを設定
						if app['inCourseID'] == courseMapInfo['courseId']:
							tmpApp = app
							break

				if tmpApp is None:
					plgLog.warning('[{sidMorg}] t_appoint check CourseID unmatch, data:[{logExamInfo}]'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
					# コースが合わないものは使えないのでリセット
					tAppoint = None
				else:
					tAppoint = tmpApp

					# コースIDの取得に失敗
					if 'inCourseID' not in tAppoint:
						log('[{sidMorg}] inCourseID get faild, data:[{logExamInfo}]'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
						msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='コースIDの取得に失敗したため、予約登録をスキップします。'))
						continue

					# 予約／受付以外は処理しない
					if tAppoint['status'] not in [tAppointSts['reservation'], tAppointSts['checkin']]:
						log('[{sidMorg}] t_appoint status proc 0-1, t_appoint status is {sts}'.format(sidMorg=sidMorg, sts=tAppoint['status']))
						if tAppoint['status'] == tAppointSts['judgment']:
							msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='判定済みのため、予約更新をスキップします。'))
						else:
							msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='確定済みのため、予約更新をスキップします。'))

						continue

					# TODO: 予約専用フラグがON
					if 'f_appoint_only' in optionMap and optionMap['f_appoint_only'] == 1:
						# 登録アクションかつ、ファイルステータスとt_appointのステータスが同一の場合、すきっぷ
						if int(row[appointMap['apoAction']]) == appointAct.register:
							# TODO: 見直しが必要
							try:
								tmpStsKey = [k for k, v in tAppointSts.items() if v == tAppoint['status']][0]
							except:
								log('[{sidMorg}] t_appoint status check failed, data:[{logExamInfo}]'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
								msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='予約ステータスのチェックに失敗したため、予約登録をスキップします。'))
								traceLog(err)
								continue
							if (tmpStsKey == 'reservation' and int(row[appointMap['apoStatus']]) == appointSts.reservation) or (tmpStsKey == 'checkin' and int(row[appointMap['apoStatus']]) == appointSts.checkin):
								log('[{sidMorg}] file status and t_appoint status match, skip proc'.format(sidMorg=sidMorg))
								msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='予約ステータスが変わらないため、予約登録をスキップします。'))
								continue

					# visitidが存在する、かつ、t_appointの検索結果と一致（TODO: カルテIDのみだと同日複数コースのチェックができないため、visitIdは必須）
					if vid is not None and tAppoint['visitid'] == vid:
						# 登録データと同一コースではない場合、処理フラグのチェック
						if tAppoint['inCourseID'] != row[appointMap['courseId']]:
							log('[{sidMorg}] t_appoint check CourseID unmatch'.format(sidMorg=sidMorg))
							# 強制キャンセルフラグが無効の場合、データ異常扱いでスキップ
							if 'f_unmatchIdAppointForceCancel' in optionMap and optionMap['f_unmatchIdAppointForceCancel'] != 1:
								log('[{sidMorg}] skip registration process'.format(sidMorg=sidMorg))
								msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='受付通し番号が同じで登録済みの予約とコースが異なるため、予約登録をスキップします。'))
								continue

					# TODO: visitidが存在しなくて、同日別コースのチェックができないためスキップする？
					# 発見されたt_appointの予約コースと、操作対象のコースIDが不一致
					elif vid is None and (tAppoint['inCourseID'] != courseMapInfo['courseId']):
						tmpFindC = [k for k in courseMap if k['courseId'] == tAppoint['inCourseID']][0]
						_msg = 'Mismatch with the reserved course. Multiple registration not possible, find courseName:{oldN}({oldC}), new courseName:{newN}({newC}), data:[{d}]'.format(
							newN=courseMapInfo['courseName'],
							newC=courseMapInfo['courseId'],
							oldN=tmpFindC['courseName'],
							oldC=tmpFindC['courseId'],
							d=','.join(row.values())
							)
						errMsg.append(_msg)
						log('[{sidMorg}] {msg}, data:[{logExamInfo}]'.format(sidMorg=sidMorg, msg=_msg, logExamInfo=logExamInfo))
						msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='受付通し番号が未設定で更新対象のコースが不一致のため、予約登録をスキップします。'))
						del _msg
						continue

					# データの更新日時情報のチェック
					updCheck = checkUpdateTime(sidMorg, row, tAppoint, logExamInfo)
					# 無視対象の場合はスキップ
					if updCheck == updateTimeStatus.ignore:
						log('[{sidMorg}] 更新日時のチェックに失敗したため、予約登録をスキップします, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
						continue

					# 予約キャンセルする？
					if appointMap['apoAction'] in row and int(row[appointMap['apoAction']]) == appointAct.cancel:
						appointUpdFlag = changeSts.course
						# 強制チェックインフラグがONの場合、削除する際も一気に消すために、「３：受付、４：取り消し」をまとめて渡す
						if 'f_fourceCheckInOn' in optionMap and optionMap['f_fourceCheckInOn']:
							apoSts = (reAppointSts['cancelReg'], reAppointSts['canselApo'])
							ordSts = examSts['appointDel']
						# 強制チェックインではない場合、データ内の操作ステータスとアクションを参照
						elif appointMap['apoStatus'] in row and row[appointMap['apoStatus']] is not None and len(row[appointMap['apoStatus']]) > 0:
							# 予約のキャンセル
							if int(row[appointMap['apoStatus']]) == appointSts.reservation:
								apoSts = reAppointSts['canselApo']
								ordSts = examSts['appointDel']
							# 受付のキャンセル
							elif int(row[appointMap['apoStatus']]) == appointSts.checkin:
								apoSts = reAppointSts['cancelReg']
								ordSts = examSts['checkinDel']
								appointUpdFlag = changeSts.chgStatus
							else:
								log('[{sidMorg}] appoint operation unknwon option:[{v}], {logExamInfo}'.format(sidMorg=sidMorg, v=row[appointMap['apoStatus']], logExamInfo=logExamInfo))
								msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, 予約ステータス：{apoStatus}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, apoStatus=row[appointMap['apoStatus']], msg='apoStatusに不正なステータスが設定されているため、予約登録をスキップします。'))
								continue
						else:
							log('[{sidMorg}] appoint operation status not in data, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
							msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='apoStatusが未設定のため、予約登録をスキップします。'))
							continue

						cancelSts = t_appoint.cancelTappoint(sidMorg=sidMorg, tAppointRow=tAppoint, appoSts=apoSts)
						if cancelSts == True:
							msg = 'success'
							procCount += 1
						else:
							msg = 'faild'
						log('[{sidMorg}] t_appoint cancel {msg}, {logExamInfo}'.format(sidMorg=sidMorg, msg=msg, logExamInfo=logExamInfo))

						# TODO: daidaiのキャンセルに成功した場合に、Kプラス連携の処理を行う
						if cancelSts:
							# K+予約／受付連携の実施
							# K+側はオーダーキーさえ変わらないならコース変更はアップデートで対応できるが、daidai側の仕様でXMLMEの作り直しが発生するためキャンセルを行う方針
							procOrder(sidMorg, tAppoint, vid, cid, sid_examinee, examDate, ordSts, row, examDtObj)

							# t_ext_infoのレコードを論理削除
							xmlExtLink = createExtLinkXML(sidMorg, tAppoint, dataUpdTime)
							# def extInfoPost(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None, sUpd=2):
							t_ext_info.extInfoPost(sidMorg, pName=pConfig['plgName'], sidAppoint=tAppoint['sid'], sidExaminee=sid_examinee, cid=cid, updateTime=xmlExtLink['updTime'], xmlInfo=xmlExtLink['xml'], sUpd=3)

						continue

					# コース変更？
					elif tAppoint['inCourseID'] != row[appointMap['courseId']]:
						appointUpdFlag = changeSts.course
						ordSts = examSts['update']
					# 予約日の変更？
					elif tAppoint['dt_appoint'].date() != examDtObj.date():
						appointUpdFlag = changeSts.apoDay
						# 予約日変更の場合はキャンセルオーダを先に出す
						ordSts = examSts['appointDel']
						procOrder(sidMorg, tAppoint, vid, cid, sid_examinee, tAppoint['dt_appoint'], ordSts, row, tAppoint['dt_appoint'])
					# 予約時間の変更？
					elif tAppoint['dt_appoint'].time() != examDtObj.time():
						appointUpdFlag = changeSts.apoTime
						ordSts = examSts['update']

			# XMLMEや基準の取得
			xmlMeInfo = getXmlMeInfo(sidMorg, tAppoint, courseMapInfo, row, useContractInfo)
			if xmlMeInfo is None:
				log('[{sidMorg}] get xmlMeInfo faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='コース情報の取得に失敗したため、予約登録をスキップします。'))
				errRowData.append(row)
				continue
			if 'meXmlObj' not in xmlMeInfo or xmlMeInfo['meXmlObj'] is None:
				log('[{sidMorg}] get XMLME faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='コース情報の取得に失敗したため、予約登録をスキップします。'))
				errRowData.append(row)
				continue
			if 'criterionSid' not in xmlMeInfo or xmlMeInfo['criterionSid'] is None:
				log('[{sidMorg}] get criterionSid faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='基準情報の取得に失敗したため、予約登録をスキップします。'))
				errRowData.append(row)
				continue
			if 'inspCodeMap' not in xmlMeInfo or xmlMeInfo['inspCodeMap'] is None:
				log('[{sidMorg}] get inspCodeMap faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='マッピング情報(inspCodeMap)の取得に失敗したため、予約登録をスキップします。'))
				errRowData.append(row)
				continue
			if 'inspDataPickUp' not in xmlMeInfo or xmlMeInfo['inspDataPickUp'] is None:
				log('[{sidMorg}] get inspDataPickUp faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				msg2js('カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(cid=cid, courseName=row['CourseName'], examDate=examDate, msg='マッピング情報(inspDataPickUp)の取得に失敗したため、予約登録をスキップします。'))
				errRowData.append(row)
				continue

			if tAppoint is None:
				# 新規登録
				appointUpdFlag = changeSts.initAppoint
				log('[{sidMorg}] t_appoint can not find, next register proc, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				sidAppoint = createXmlMe(sidMorg, vid, cid, examDtObj, courseMapInfo['sidMe'], courseMapInfo['sid'], sid_examinee, row, xmlMeInfo, remarks, useContractInfo)
				if sidAppoint is None:
					log('[{sidMorg}] sidAppoint is None, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
					msg2js('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='予約登録に失敗しました'))
					continue
				# 登録検査項目が0件は-2
				elif sidAppoint == -2:
					log('[{sidMorg}] regist count 0, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
					msg2js('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='予約登録に失敗しました'))
					continue
				ordSts = examSts['appoint']
				tAppoint = t_appoint.getTappoint(sidMorg=sidMorg, vid=vid, cid=cid, apoDay=examDate, sidExaminee=sid_examinee)[0]

				log('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='予約登録に成功しました'))

			else:
				# ステータスが予約／受付済みのみXML更新
				if 0 <= tAppoint['status'] <= 1:
					# 更新
					sidAppoint = updateXmlMe(sidMorg, cid, tAppoint, courseMapInfo['sid'], row, xmlMeInfo)
					# データ削除は-1
					if sidAppoint == -1:
						msg2js('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='予約更新に失敗しました'))
						continue

					msg = ''
					if tAppoint['status'] == 1 and int(row[appointMap['apoStatus']]) == appointSts.reservation: # 受付キャンセル
						ordSts = examSts['checkinDel']
						msg = '受付キャンセルしました'
					elif  tAppoint['status'] == 0 and int(row[appointMap['apoStatus']]) == appointSts.checkin: # 受付
						ordSts = examSts['checkin']
						msg = '受付しました'
					elif appointUpdFlag == changeSts.apoDay: # 日付変更
						ordSts = examSts['appoint']
						msg = '日付変更しました'
					else:
						ordSts = examSts['update']
						msg = '更新しました'
					reApoSts = examSts['update']
					log('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg=msg))
				else:
					msg2js('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='予約更新失敗しました'))
					log('[{sidMorg}] Do not apply, t_appoint.status: {tApoSts}, {logExamInfo}'.format(sidMorg=sidMorg, tApoSts=tAppoint['status'], logExamInfo=logExamInfo))

			# xml_externalLinkageの作成／更新
			try:
				xmlExtLink = createExtLinkXML(sidMorg, tAppoint, dataUpdTime, courseId=row[appointMap['courseId']])
				# 連携情報の新規登録
				if xmlExtLink['raw'] is None:
					# def extInfoPut(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None):
					t_ext_info.extInfoPut(sidMorg, pName=pConfig['plgName'], sidAppoint=tAppoint['sid'], sidExaminee=sid_examinee, vid=vid, cid=cid, dtAppoint=examDtObj, updateTime=xmlExtLink['updTime'], xmlInfo=xmlExtLink['xml'])
				# 更新
				else:
					# def extInfoPost(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None, sUpd=2):
					t_ext_info.extInfoPost(sidMorg, pName=pConfig['plgName'], sidAppoint=tAppoint['sid'], sidExaminee=sid_examinee, vid=vid, cid=cid, dtAppoint=examDtObj, updateTime=xmlExtLink['updTime'], xmlInfo=xmlExtLink['xml'])
			except Exception as err:
				msg2js('連携情報の更新処理でエラーが発生しました。err:[{err}]'.format(err=err))
				log('[{sidMorg}] externalLikageXML get faild:{e} {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo, e=err))
				traceLog(err)
				continue

			if sidAppoint is None:
				log('[{sidMorg}] create t_appoint faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				continue

			# 新規登録時のt_appointのステータスは予約
			if appointUpdFlag is not None and appointUpdFlag == changeSts.initAppoint:
				tApoStsCode = tAppointSts['reservation']
			# それ以外はt_appointレコードそのまんま
			else:
				tApoStsCode = tAppoint['status']
				# ステータスとアクションが含まれている時だけ、ステータス変更をかける
				if appointMap['apoStatus'] in row and row[appointMap['apoStatus']] is not None and appointMap['apoAction'] in row and row[appointMap['apoAction']] is not None:
					# 予約
					if int(row[appointMap['apoStatus']]) == appointSts.reservation:
						tApoStsCode = tAppointSts['reservation']
					# 受付
					elif int(row[appointMap['apoStatus']]) == appointSts.checkin:
						tApoStsCode = tAppointSts['checkin']
						appointUpdFlag = changeSts.chgStatus
					else:
						msg2js('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='ステータス変更に失敗しました'))
						log('[{sidMorg}] unknown status flag, data=[{d}]'.format(sidMorg=sidMorg, d=','.join(row)))
						continue

			# t_appoint&t_appoint_meのレコード更新
			t_appoint.setTappointStatus(sidMorg, sid_appoint=sidAppoint, stsCode=tApoStsCode, sReappoint=reApoSts, apoDate=examDtObj)

			# チェックイン処理のストアド実行
			if 'f_fourceCheckInOn' in optionMap and optionMap['f_fourceCheckInOn'] == 1:
				# 新規登録時のみ、チェックイン処理
				if appointUpdFlag is not None and appointUpdFlag == changeSts.initAppoint:
					checkInSts = t_appoint.checkinPost(sidMorg, visitId=vid)
					if checkInSts is not None and len(checkInSts) > 0 and checkInSts[0]['sid'] == sidAppoint:
						log('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='受付しました'))
						log('[{sidMorg}] checkin complete'.format(sidMorg=sidMorg))
					else:
						msg2js('カルテID:{cid}, 受診日：{examDate}, {msg}'.format(cid=cid, examDate=examDate, msg='受付に失敗しました'))
						log('[{sidMorg}] checkin faild: {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
						continue

			# オーダ連携処理の実施
			procOrder(sidMorg, tAppoint, vid, cid, sid_examinee, examDate, ordSts, row, examDtObj)


		procCount += 1

	if dataCount == procCount:
		retStatus = success
	elif procCount < 1:
		retStatus = error
	else:
		retStatus = warning

	log('[{sidMorg}] procCount/dataCount: {pCnt}/{dCnt}'.format(sidMorg=sidMorg, dCnt=dataCount, pCnt=procCount))
	msg2js('総件数:{total_cnt}, 登録/更新件数:{regist_cnt}'.format(total_cnt=dataCount, regist_cnt=procCount))

	return retStatus, errRowData





# main
def main():

	global contractData
	global procMode
	config = cmn.plgConfigGet()
	plgDir = os.getcwd()
	plgName = '予約インポート'
	errData = None
	ret = None
	procMode = 1 # 予約モード

	log('[{sidMorg}] **** plg start ****'.format(sidMorg=sidMorg))

	global errMsg, pConfig, pDir, mapDataAll
	pConfig = config.plg['p021']
	pConfig['plgName'] = plgName
	log('**** plgName: {} ****'.format(plgName))
	log('{}'.format(pConfig))
	pDir = plgDir
	log('{}'.format(pDir))

	try:
		mapDataAll = {
			'examineeMap': examineeMap,
			'appointMap': appointMap,
			'requiredMap': requiredMap,
			'optionMap': optionMap,
			'orgMap': orgMap,
			'dataNameMap': dataNameMap,
		}

	except Exception as err:
		msg2js('マッピング用のオブジェクト設定でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)
		return

	if examineeMap is None or appointMap is None:
		eMsg = 'error Object: '
		if examineeMap is None: eMsg += 'examineeMap'
		if appointMap is None: eMsg += 'appointMap'
		raise Exception('[{sidMorg}] create config error, {plgName} up faild, msg: {logMsg}'.format(sidMorg=sidMorg, plgName=plgName, logMsg=eMsg))

	try:

		# 契約情報の取得
		contractData = t_contract_me_attribute.getT_contract_me_attribute(sidMorg)

	except Exception as err:
		msg2js('契約情報の取得でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)
		return

	try:
		log('^^^^^^^^^^^dataJson^^^^^^^^^^^^')
		startTime_csvRead = time()

		# 成田予約受付インポート・サンプル(json)
		encoding = "UTF-8"
		# "file_path": "/tmp/upload_3cf4b19e19c5350537e1790006f44cb7"
		tmpfile = open(config_data['file_path'], 'r', encoding=encoding)

		jsonString = tmpfile.read()
		tmpfile.close()
		
		log(jsonString)

	except Exception as err:
		msg2js('取込ファイルの読込でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)
		return

	try:

		if jsonString is not None and len(jsonString) > 0:
			data = None

			try:
				data = json.loads(jsonString)

				endTime_csvRead = time()
				log('time cost of csvread: {}'.format(endTime_csvRead - startTime_csvRead))

			except Exception as err:
				msg2js('取込ファイルの解析に失敗しました。ファイル内に不正な文字列が含まれている可能性があります。')
				traceLog(err)
				raise

			log(data)
			cnt = 0
			startTime = time()
			ret, errData = setTappointMe(sidMorg, data['PackageList']['Package'])
			# ret, errData = setTappointMe(sidMorg, data)

			# 実行時間表示
			log('[{sidMorg}] fileCount:{cnt}, elapsed_time: {eltime:.3f} sec'.format(sidMorg=sidMorg, cnt=cnt, eltime=time() - startTime))

	except Exception as err:
		msg2js('予約登録処理でエラーが発生しました。')
		traceLog(err)

	log('[{sidMorg}] plg exit'.format(sidMorg=sidMorg))
	return

if __name__ == '__main__':
	#### デバッグ専用：使うときにコメント解除 ####
	## VSCode ver1.27.1がサポートしているptvsdのバージョンは「4.1.1」
	# 本体からデバッグするときはこちらのdebugモードtrueにしてremort Attach
	debug_mode = False

	if debug_mode:
		import ptvsd
		print('!!!! enable ptvsd !!!!')
		ptvsd.enable_attach(address=('0.0.0.0', 3000), redirect_output=True)
		ptvsd.wait_for_attach()

	# ローカルでpython単体で動かすときは以下のモジュールで動かす・・・
	#import debugpy
	#debugpy.listen(5678)
	#### ここまでデバッグ専用：未使用時はコメントアウト ####

	global config_data		# グローバルに突っ込む必要あり

	log('childImportAppoint.py start')
	msg2js('予約インポートを開始します')

	try:
		# コンフィグ設定をjs側から受取
		config_data = form_cmn.args2config(sys.argv)
		# DB接続情報の受渡し
		dbconfig = {'host':config_data['host'], 'port':config_data['port'], 'dbName':config_data['dbName'], 'user':config_data['user'], 'pass':config_data['pass'], 'timeOut': config_data['timeout']}
		# インスタンスの作成
		sql = mySql.Exceute(loggerChild=plgLog, config=dbconfig, sidMorg=sidMorg, sidUpd=optionMap['sid_upd'])
		extFile = extFileCtrl.ExtFileCtrl(sidMorg=sidMorg, loggerChild=plgLog)
		fileCtrl = myFile.FileCtrl(sidMorg=sidMorg, loggerChild=plgLog)
		t_contract_me_attribute = t_contract_me_attributeClass.T_contract_me_attribute(sidMorg=sidMorg, loggerChild=plgLog)

		# メイン処理呼び出し
		main()

		msg2js('予約インポートを終了します')

		form_cmn._exit('success')		# 処理成功

	except Exception as err:
		msg2js('予約インポートのメイン処理でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)
		form_cmn._exit('error')		# エラー

	log('childImportAppoint.py end')
	form_cmn._exit('exit')				# 終わり