#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# 一括結果インポート

from logging import getLogger
plgLog = getLogger(__name__)

import csv
import os
import sys
import re
import pathlib
import xml.etree.ElementTree as ET
import datetime
import xmltodict
import traceback
from time import sleep, time
from collections import defaultdict, namedtuple

# myapp
# from mod import common as cmn
# from mod import my_fileClass as myFile
# from mod import my_sqlClass as mySql
# import plugins.plgCommon as plgCmn
# from plugins.plgCmd import m_examineeClass, m_criterionClass, t_appointClass, m_eorgClass, m_meClass, m_outsourceClass, t_appoint_meClass, t_ext_orderClass, m_me_attributeClass, m_orgClass, t_ext_infoClass, t_contract_me_attributeClass
# import plugins.extFileCtrlClass as extFileCtrl


import form_tools_py.conf as conf
import form_tools_py.common as form_cmn
from renkei_tools_py.mod import mycfg as mycfg

# DB設定
mycfg.setDbConfig('90007', 'development')

from renkei_tools_py.mod import common as cmn
from renkei_tools_py.mod import my_fileClass as myFile
from renkei_tools_py.mod import my_sqlClass as mySql

from renkei_tools_py import plgCommon as plgCmn
# from renkei_tools_py.plgCmd import m_examinee, m_criterion, t_appointClass, m_eorg, m_me, m_outsource, t_appoint_meClass, t_ext_order, m_me_attribute, m_org, t_ext_info, t_contract, t_contract_me_attributeClass
from renkei_tools_py.plgCmd import m_examinee, m_criterion, t_appoint, m_eorg, m_me, m_outsource, t_appoint_me, t_ext_order, m_me_attribute, m_org, t_ext_info, t_contract, t_contract_me_attributeClass
from renkei_tools_py import extFileCtrlClass as extFileCtrl



# インポートファイル解析用
from renkei_tools_py import analysisFile

# コンフィグの代わり
# from . import csv2xml_mapping
from renkei_tools_py import csv2xml_mapping

msg2js = form_cmn.Log().msg2js
log = form_cmn.Log().log
dbg_log = form_cmn.Log().dbg_log

try:
	# 医療機関番号をmodule名から取得（暫定）
	# sidMorg = __name__.split('.')[2]
	sidMorg = '90007'
	cmn.baseConf = mycfg.conf

	# 設定ファイルは起動時しか読み込まない
	examineeMap = csv2xml_mapping.examineeMapGet(sidMorg)
	appointMap = csv2xml_mapping.appointMapGet(sidMorg)
	requiredMap = csv2xml_mapping.requiredMapGet(sidMorg)
	optionMap = csv2xml_mapping.optionMapGet(sidMorg)
	orgMap = csv2xml_mapping.orgMapGet(sidMorg)
	dataNameMap = csv2xml_mapping.dataItemMapGet(sidMorg)
	# t_appoint = t_appointClass.Tappoint(sidMorg=sidMorg, loggerChild=plgLog)
	# t_appoint_me = t_appoint_meClass.TappointMe(sidMorg=sidMorg, loggerChild=plgLog)

except Exception as err:
	plgLog.error(err, exc_info=True)
	msg2js('コンフィグの初期設定でエラーが発生しました。err:[{err}]'.format(err=err))
	traceLog(err)

# インスタンス生成
# try:
# 	# インスタンスの作成
# 	sql = mySql.Exceute(loggerChild=plgLog, config=dbconfig, sidMorg=sidMorg, sidUpd=optionMap['sid_upd'])
# 	extFile = extFileCtrl.ExtFileCtrl(sidMorg=sidMorg, loggerChild=plgLog)
# 	fileCtrl = myFile.FileCtrl(sidMorg=sidMorg, loggerChild=plgLog)
# 	t_contract_me_attribute = t_contract_me_attributeClass.T_contract_me_attribute(sidMorg=sidMorg, loggerChild=plgLog)

# 	# sql = mySql.Exceute(loggerChild=plgLog)
# 	# extFile = extFileCtrl.ExtFileCtrl(sidMorg=sidMorg, loggerChild=plgLog)
# 	# fileCtrl = myFile.FileCtrl(sidMorg=sidMorg, loggerChild=plgLog)
# 	# m_outsource = m_outsourceClass.Moutsource(sidMorg=sidMorg, loggerChild=plgLog)
# 	# m_criterion = m_criterionClass.Mcriterion(sidMorg=sidMorg, loggerChild=plgLog)
# 	# m_eorg = m_eorgClass.Meorg(sidMorg=sidMorg, loggerChild=plgLog)
# 	# m_examinee = m_examineeClass.Mexaminee(sidMorg=sidMorg, loggerChild=plgLog)
# 	# m_org = m_orgClass.Morg(sidMorg=sidMorg, loggerChild=plgLog)
# 	# m_me = m_meClass.Mme(sidMorg=sidMorg, loggerChild=plgLog)
# 	# m_me_attribute = m_me_attributeClass.MmeAttributeClass(sidMorg=sidMorg, loggerChild=plgLog)
# 	# t_appoint = t_appointClass.Tappoint(sidMorg=sidMorg, loggerChild=plgLog)
# 	# t_appoint_me = t_appoint_meClass.TappointMe(sidMorg=sidMorg, loggerChild=plgLog)
# 	# t_ext_info = t_ext_infoClass.TextInfo(sidMorg=sidMorg, loggerChild=plgLog)
# 	# t_ext_order = t_ext_orderClass.TextOrder(sidMorg=sidMorg, loggerChild=plgLog)
# 	# t_contract_me_attribute = t_contract_me_attributeClass.T_contract_me_attribute(sidMorg=sidMorg, loggerChild=plgLog)
# except Exception as err:
# 	plgLog.error(err, exc_info=True)

plgConfig = None

success = cmn.success
warning = cmn.warning
error = cmn.error

# ファイル出力したいエラーメッセージ格納用
errMsg = []

systemUserSid = mySql.systemUserSid

pConfig = None
pDir = None
courseMap = None
contractData = None

# TODO: コース毎に基準を格納する（1回のループ処理中だけ保持する。大量データの一括処理時に毎度DBアクセスするのを回避する）
meCriterionData = {}
criterionSid = {}
outsourcingInspectionMap = {}
mMeXMLData = {}
# ここまで

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

#	----------------------------------------
#		予約ステータス(AppointStatus):
#			|- 1:新規　2:変更　3:キャンセル
#	----------------------------------------
AppointAct_konosu = namedtuple('AppointAct_konosu',[
	'new_register',		# 1
	'change',			# 2
	'cancel'			# 3
])
appointAct_konosu = AppointAct_konosu(1, 2, 3)
#appointAct = {
# 'new_register': 1,
# 'change': 2,
# 'cancel': 3
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
# tAppointSts = t_appointClass.tAppointSts
# reAppointSts = t_appointClass.sReApo
tAppointSts = t_appoint.tAppointSts
reAppointSts = t_appoint.sReApo

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
			log("K-Plus order registration faild")
			#log('[{sidMorg}] K-Plus order registration faild: seqNo:{a}, orderStatus:{b}, tAppoint:{c}'.format(sidMorg=sidMorg, a=seqNo, b=orderSts, c=tAppointData))
		else:
			log("K-Plus order registration success")
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

# トレースログ出力
def traceLog(message):
	type_, value, traceback_ = sys.exc_info()
	log('message: {message}, traceback: {err}'.format(message=message, err=traceback.format_exception(type_, value, traceback_)))

# テンプレ取得
def getXMLTemplate(filePath):
	try:
		return fileCtrl.xmlRead(filePath)
	except Exception as err:
		plgLog.error(err, exc_info=True)
		return None


# テンプレ取得
def getXMLTemplate2text(filePath):
	try:
		return fileCtrl.textRead(filePath)
	except Exception as err:
		plgLog.error(err, exc_info=True)
		return None

# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: 受診者属性情報の登録
#	|- DB操作：m_examinee.setExamineeXml(ストアド・プロシージャ)
#		|- *注意：更新時、xml_examineeが同じかどうかをチェックする
# |- Param:
#	|- examData(元のCSVデータ: row['dataItem'])
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def setExaminee(sidMorg, sid_examinee, xmlData, examData):
	# 日付の形式のリフォーム
	regDateFormat1 = re.compile(r'([0-9]{4})([0-9]{2})([0-9]{2})')					# TODO: 区切り文字なし（19990101）
	regDateFormat2 = re.compile(r'([0-9]{4})/([0-9]{1,2})/([0-9]{1,2})')			# TODO: 区切り文字あり（1999/01/01 or 1999/1/1）など
	regDateFormat3 = re.compile(r'([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})')			# TODO: 区切り文字なし（1999-01-01 or 1999-1-1）など		
	
	xml = None
	if xmlData is not None and type(xmlData) == str:
		xml = plgCmn.xml2Obj(xmlData)

	try:
		xmlObj_examinee = xml
		#for examData in data:
		# 受診者情報のXML当て込み
		for xmlKey,csvKey in examineeMap.items():
			if csvKey in examData and examData[csvKey] is not None:
				textData = examData[csvKey]
				if xmlKey == 'examinee/birthday':
					# 元のソースは問題あり(正規表現：r'')
					if regDateFormat1.match(textData):			# 区切り文字なし（19990101）
						textData = regDateFormat1.sub(r'\1/\2/\3', textData)
					elif regDateFormat2.match(textData):		# 区切り文字あり（1999/01/01 or 1999/1/1）
						textData = regDateFormat2.sub(r'\1/\2/\3', textData)
					elif regDateFormat3.match(textData):		# 区切り文字あり（1999-01-01 or 1999-1-1）
						textData = regDateFormat3.sub(r'\1/\2/\3', textData)
					if plgCmn.dateFormatCheck(textData) == False:
						plgLog.error('[{sidMorg}] date format check faild, csvText:[{orgDay}]'.format(sidMorg=sidMorg, orgDay=textData))
						return None
					textData = datetime.date.strftime(datetime.datetime.strptime(textData, '%Y/%m/%d'), '%Y/%m/%d')		# FIXME: 日付フォーマットの変換が必要かも
				try:
					xmlObj_examinee.findall(xmlKey)[0].text = textData
				except Exception as err:
					plgLog.warning('[{sidMorg}] xmlKey: {xmlKey}, csvKey: {csvKey}, textData: {textData}, msg:{eMsg}'.format(sidMorg=sidMorg, xmlKey=xmlKey, csvKey=csvKey, textData=textData, eMsg=err))
	except Exception as err:
		plgLog.error(err, exc_info=True)
		return None

	# DBへの登録
	try:
		# 受診者の新規登録の場合、sidタグが不要なので削除を行うこと
		if sid_examinee is None:
			[elm_exam.remove(elm) for elm_exam in xmlObj_examinee.iter('examinee') for elm in elm_exam.iter() if elm.tag == 'sid']
		else:
			xmlObj_examinee.find('examinee/sid').text = sid_examinee

		xmlStr = ET.tostring(xmlObj_examinee, encoding='UTF-8').decode('UTF-8')

		rows = m_examinee.setExamineeXml(sidMorg=sidMorg, xml=xmlStr, sid=sid_examinee)
		if rows is not None and 'sid' in rows and rows['sid'] is not None:
			sid_examinee = str(rows['sid'])
		else:
			return None
	except Exception as err:
		plgLog.exception('[{}]'.format(err))
		return None

	return sid_examinee


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: sid_appointとXMLの取得
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def getSidExaminee(sidMorg, cid):
	try:
		plgLog.info('[{sidMorg}] search m_examinee, karuteID:{cid}'.format(sidMorg=sidMorg, cid=cid))

		row = m_examinee.searchExaminee(sidMorg=sidMorg, examId=plgCmn.customNormalize(cid))
		xml = None
		sid_examinee = None
		if row is not None:
			sid_examinee = str(row[0]['sid'])
			xml = plgCmn.xml2Obj(row[0]['xml_examinee'])
		else:
			# 人テンプレXML
			xml = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['examinee']['1']))
	except Exception as err:
		plgLog.error(err, exc_info=True)

	return (sid_examinee, ET.tostring(xml, encoding='UTF-8').decode('UTF-8'))


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: 予約の取り消し
#	|- f_allDataNullisAppointCancel(1): 
#		|- 受付⇒予約⇒キャンセル(二段階操作 - t_appoint.status: 1=>0; t_appoint.s_upd: 3)
#	|- f_allDataNullisAppointCancel(0):
#		|- *注意：受付⇒予約(t_appoint.status: 1=>0; t_appoint.s_upd: 2)
#		|- 予約⇒キャンセル(t_appoint.status: 0; t_appoint.s_upd: 3)
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def delTappoint(sidMorg, tAppoint):
	ret = None
	appoSts = None
	# 強制フラグがONの場合
	if 'f_allDataNullisAppointCancel' in optionMap and optionMap['f_allDataNullisAppointCancel'] == 1:
		if tAppoint['status'] == tAppointSts['checkin']:
			# 受付⇒予約とステータス変化させた上で予約の削除
			appoSts = [reAppointSts['cancelReg'], reAppointSts['canselApo']]
		else:
			appoSts = reAppointSts['canselApo']
	else:
		if tAppoint['status'] == tAppointSts['checkin']:
			# appoSts = reAppointSts['cancelReg']
			# 受付⇒予約⇒キャンセル(二段階操作)
			appoSts = [reAppointSts['cancelReg'], reAppointSts['canselApo']]
		else:
			appoSts = reAppointSts['canselApo']

	try:
		ret = t_appoint.cancelTappoint(sidMorg=sidMorg, tAppointRow=tAppoint, appoSts=appoSts)
	except Exception as err:
		plgLog.error(err)
	return ret


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: 更新（t_appoint_me.xml_me検査や問診結果更新のみ）
#	|- DB操作：t_appoint_me.eresultPost(ストアド・プロシージャ)
#		|- *注意：t_appoint_me.xml_me検査や問診結果更新のみ
# |- Param:
#	|- data: list(dict) type of "retData" returned from setTappointMe fun
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def setTappointUpdate(sidMorg, data):
	try:
		# xmlme更新のチャレンジ回数と待ち時間
		givupCnt = 20
		givupWait = 0.5
		givupFlag = True
		retryFlag = False

		vid = data['visitId']
		cid = data['examineeItem']['karuteId']
		apoDt = data['examineeItem']['apoDt']
		sid_examinee = data['examineeItem']['sid_examinee']
		sid_appoint = data['appointItem']['tAppoint']['sid_appoint']
		xmlCcard = data['appointItem']['tAppoint']['xml_ccard']
		xmlAppoint = data['appointItem']['tAppoint']['xml_appoint']
		apoStatus = data['apoStatus']
		# t_appoint.s_reappoint
		reApoSts = data['appointItem']['reApoSts']
		if apoStatus is not None:
			_apoStatus = data['appointItem']['tAppoint']['status']
		courseId = data['courseMapInfo']['courseId']
		sidMe = data['courseMapInfo']['sidMe']
		xmlMe = data['appointItem']['xmlMe']
		xmlMeTime = data['appointItem']['xmlMeTime']
		remarks = data['appointItem']['remarks']
	except Exception as err:
		plgLog.error(err)

	try:
		# TODO: タイムスタンプをチェックして必要なら再生成
		while True:
			if givupCnt < 0:
				break
			nowTappoint = t_appoint.getTappoint(sidMorg=sidMorg, vid=vid, cid=cid, apoDay=apoDt.date(), sidExaminee=sid_examinee)
			# TODO: 同日別コースが存在する可能性を考慮してコースIDが一致するデータの取得を行う
			try:
				tAppoint = [k for k in nowTappoint if k['inCourseID'] == courseId][0]
			except Exception as err:
				plgLog.error('new t_appoint data get failed')
				break

			# t_appoint_meの更新時間
			if 'me_dt_upd' in tAppoint:
				if tAppoint['me_dt_upd'] > xmlMeTime:
					retryFlag = True
			# t_appointの更新時間
			elif 'dt_upd' in tAppoint:
				if tAppoint['dt_upd'] > xmlMeTime:
					retryFlag = True
			else:
				plgLog.error('t_appoint and t_appoint_me timestamp check failed')
				break

			# 再生成
			if retryFlag:
				plgLog.warning('re-Create XMLME')
				# 新しいXMLMEを渡したうえで再生成
				data['appointItem']['xmlMeInfo'] = plgCmn.xml2Obj(tAppoint['xml_me'])
				xmlMe, xmlMeTime = createXmlMe(sidMorg, vid, cid, apoDt, sidMe, data['courseMapInfo']['sid'], sid_examinee, data['dataItem'], data['appointItem']['xmlMeInfo'])
			else:
				givupFlag = False
				break
			givupCnt -= 1
			sleep(givupWait)
	except Exception as err:
		plgLog.error(err)

	# XMLMEの再生成回数の上限到達で諦める
	try:
		if givupFlag:
			plgLog.error('Give up on XMLME updates. Target of re-creation')
			# TODO: 諦めた場合のファイルをどうするか・・・inフォルダに書き戻すか？エラー扱いで終わる？
			fname = pConfig['givupFileName'] + str(datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')) + '.csv'
			outPath = pDir.joinpath(pConfig['path']['in'], fname)
			tmpH = list(data['dataItem'].keys())
			tmpD = [data['dataItem']]
			fileCtrl.csvWrite(outPath, tmpD, tmpH)
			return None
	except Exception as err:
		plgLog.error('giveup process failed')
		return

	try:
		# 結果XML更新(t_appoint_meのみ)
		#                   eresultPost(sidMorg, *, sidAppoint, sUpd, nAppoint1, xml1, nAppoint2=None, xml2=None, dtUpd=None):
		rows = t_appoint_me.eresultPost(sidMorg, sidAppoint=sid_appoint, sUpd=2, nAppoint1=1, xml1=xmlMe)
		if rows is not None and rows[0]['OUT_sid_appoint'] != 0:
			# t_appoint_me.sid_appoint
			sid_appoint = rows[0]['OUT_sid_appoint']

		# 問題FIX必要（*注意：apoStatus ==> reApoSts, 予約/受付ステータスではなく、t_appoint.s_reappointです）
		#				 setTappointPost(sidMorg, *, sidAppoint, apoStatus, sidMe=None, xmlMe=None, xmlCcard=None, xmlAppoint=None, remarks="", sidContract=None):
		# rows = t_appoint.setTappointPost(sidMorg, sidAppoint=sid_appoint, apoStatus=reApoSts, apoDate=apoDt, sidMe=sidMe, xmlMe=xmlMe, xmlCcard=xmlCcard, xmlAppoint=xmlAppoint, remarks=remarks)
		# if rows is not None and rows[0]['sid'] != 0:
		# 	# t_appoint_me.sid_appoint
		# 	sid_appoint = rows[0]['sid']

		plgLog.info('[{sidMorg}] eresultPost [row: {row}]'.format(sidMorg=sidMorg, row=rows[0]))
		log('[{sidMorg}] eresultPost [row: {row}]'.format(sidMorg=sidMorg, row=rows[0]))
	except Exception as err:
		plgLog.error(err, exc_info=True)
		traceLog(err)

	return sid_appoint


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: 予約新規登録（*注意：「t_appoint予約情報」&&「t_appoint_me検査結果」 両方新規登録）
#	|- DB操作：t_appoint.setTappointPut(ストアド・プロシージャ)
# |- Param:
#	|- remarks: 備考欄(t_appoint.remarks)
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def setTappointNew(sidMorg, vid, apoDt, sid_examinee, sidMe, xmlMe, remarks):
	try:
		sid_appoint = None
		# XMLテンプレ(ccard)読み込み
		xmlCcard = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['ccard']['1']))
		if xmlCcard is not None:
			xmlCcard = ET.tostring(xmlCcard, encoding='UTF-8').decode('UTF-8')

		# ~~必須（ないとK+連携のmlg_data.mlg_t_orders.txt_orderの情報マッピング出来ない）~~
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
		# こうのすやらなくてもいい??
		#xmlAppoint = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['appoint']['1']))
		#if xmlAppoint is not None:
		#	xmlAppoint = ET.tostring(xmlAppoint, encoding='UTF-8').decode('UTF-8')

		# TODO：団体登録が必要なら処理を作成する
		#t_XmlObj_org = getXMLTemplate(pathlib.Path(cmn.baseConf['templateXML']['org']['1']))

		# t_appoint && t_appoint_me 両方新規登録
		# def setTappointPut(self, sidMorg, *, vid, apoDt, sidExaminee, sidMe, xmlMe, xmlCcard, xmlAppoint=None, remarks="", sidContract=None):
		rows = t_appoint.setTappointPut(sidMorg, vid=vid, apoDt=apoDt, sidExaminee=sid_examinee, sidMe=sidMe, xmlMe=xmlMe, xmlCcard=xmlCcard, xmlAppoint=xmlAppoint, remarks=remarks)
		if rows is not None and rows[0]['sid'] != 0:
			sid_appoint = rows[0]['sid']

		plgLog.info('[{sidMorg}] setTappointNew [row: {row}]'.format(sidMorg=sidMorg, row=rows))
	except Exception as err:
		plgLog.error(err, exc_info=True)

	return sid_appoint


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: XMLMEや基準やマッピングコードのみ取得（*注意：結果はまだマッピングしてない）
#	|- 更新：tAppointが存在する場合、既存な結果情報(t_appoint_me.xml_me)取得
#	|- 新規：tAppointがない場合、m_meからXMLMEを取得する
# |- Param
#	|- data: インポートしたCSVからpython Dictに変換されたjson型データ
# |- Return
#	|- retData: xmlMeInfo
#		|- ['meXmlObj']: xml_me obj
#		|- ['criterionSid']: 基準（コースID毎にキャッシュする）
#		|- ['inspCodeMap']: 全項目コード情報(ex. {'179': ['M00101'], ...} - 身長)
#		|- ['inspDataPickUp']: csvデータとマッピングできたコード(ex. ['M00101', ...])
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def getXmlMeInfo(sidMorg, tAppoint, courseMapInfo, data):
	global meCriterionData, criterionSid, outsourcingInspectionMap, mMeXMLData
	retData = {}
	meXmlObj = None
	inspCodeMap = None
	inspDataPickUp = []
	courseSid = courseMapInfo['sid']
	meCriterionDataDiscoveredFlag = False

	# キャッシュされた（courseSid対応する基準情報obj）
	if meCriterionData is not None and courseSid in meCriterionData and meCriterionData[courseSid] is not None:
		if len(meCriterionData[courseSid]) > 0:
			meCriterionDataDiscoveredFlag = True

	if meCriterionDataDiscoveredFlag == False:
		meCriterionData[courseSid] = None
		outsourcingInspectionMap[courseSid] = None
		criterionSid[courseSid] = None
		mMeXMLData[courseSid] = None

	try:
		# tAppointが存在する
		if tAppoint is not None:
			# 既存な結果情報(t_appoint_me.xml_me)
			tmpXmlme = tAppoint['xml_me']
		# tAppointがない場合、m_meからXMLMEを取得する
		else:
			# 新規xml_me
			rows = m_me.getMe(sidMorg, sidMe=courseMapInfo['sidMe'], sid_criterion=courseSid)
			if rows is not None and len(rows[0]['xml_me']) > 0:
				if courseSid in mMeXMLData and mMeXMLData[courseSid] is not None:
					# TODO: 気持ちタイムスタンプのチェック
					if mMeXMLData[courseSid]['dt_upd'] < rows[0]['dt_upd']:
						mMeXMLData[courseSid] = rows[0]
				else:
					mMeXMLData[courseSid] = rows[0]
				tmpXmlme = mMeXMLData[courseSid]['xml_me']
			else:
				# TODO: このルートには普通落ちない
				plgLog.error('XML does not exist in m_me')
				return None

		if meCriterionDataDiscoveredFlag == False:
			meCriterionData[courseSid] = m_criterion.getXMLMEcriterion(tmpXmlme)

		meXmlObj = plgCmn.xml2Obj(tmpXmlme)
		if meCriterionDataDiscoveredFlag == False:
			# 基準の取得
			criterionSid.update(m_criterion.getCriterionCourse(sidMorg, meCriterionData=meCriterionData[courseSid]))
	except Exception as err:
		plgLog.error('[{}] get xmlme or m_criterion faild, {}'.format(sidMorg, err), exc_info=True)

	if criterionSid is not None and criterionSid[courseSid] is not None and len(criterionSid[courseSid]) > 0:
		try:
			# 外注マッピングの取得(コース：全項目コード)
			inspCodeMap = None
			courseXMLObj = plgCmn.xml2Obj(criterionSid[courseSid]['course'][courseMapInfo['sidMe']]['xml_criterion'])
			if meCriterionDataDiscoveredFlag == False:
				outsourcingInspectionMap[courseSid] = m_eorg.getOutsourcingMap(sidMorg, courseXMLObj=courseXMLObj)
			# 要素コードだけ欲しい
			if outsourcingInspectionMap[courseSid]['eie'] is not None:
				inspCodeMap = {k: v['res'] for k, v in outsourcingInspectionMap[courseSid]['eie'].items() if v['res'] is not None}
			if inspCodeMap is None:
				plgLog.error('[{}] get inspcode faild'.format(sidMorg))
				return None

			log("##############{}:各種類の問診含む全項目コード情報###############".format(courseSid))
			log(inspCodeMap)
			# データ内に含まれるマッピングコードと一致するアイテムのみ抽出（取り込みのデータあるかどうか問わず）
			for key in inspCodeMap.values():
				checkItem = list(set(key) & set(data.keys()))
				if len(checkItem) < 1: continue
				for key2 in checkItem:
					# TODO: 空データの場合も抽出対象とする。その代わり、XMLMEの構築個所でf_intendedの操作を行うこととする
					#if data[key2] is None and len(data[key2]) < 1: continue
					inspDataPickUp.append(key2)

			log("##############{}:マッピングできた項目コード###############".format(courseSid))
			log(inspDataPickUp)
		except Exception as err:
			plgLog.error('[{}] get inspcode faild, {}'.format(sidMorg, err), exc_info=True)

	retData['meXmlObj'] = meXmlObj
	retData['criterionSid'] = {courseSid: criterionSid[courseSid]}
	retData['inspCodeMap'] = inspCodeMap
	retData['inspDataPickUp'] = inspDataPickUp

	return retData


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: 実際の検査結果マッピング操作（*注意：新規や更新共通やる）
# 	|- matchingEleSid: **設定対象**の項目コード集合(ex. {'179': ['M00101'], ...})
# |- Param
#	|- xmlMeInfo: returned by getXmlMeInfo func
#	|- row: インポートcsvデータ
# |- Return
#	|- xmlMe: 検査や問診結果マッピングしたxml_me obj
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def createXmlMe(sidMorg, visitId, cid, apoDt, sidMe, courseSid, sid_examinee, row, xmlMeInfo):
	# ログ出力用ベース情報
	logExamInfo = 'visitId: {vid}, karuteId: {cid}, apoDay: {apoDay}, sid_examinee: {sidExam}, courseSid: {courseSid}, sidMe: {sidMe}'.format(vid=visitId, cid=cid, apoDay=apoDt.date(), sidExam=sid_examinee, courseSid=courseSid, sidMe=sidMe)

	sid_appoint = None
	plgLog.info('[{sidMorg}] create new {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
	# meの取得
	meXmlObj = xmlMeInfo['meXmlObj']
	# 基準の取得
	criterionSid = xmlMeInfo['criterionSid']

	# 外注マッピングの取得（各種類問診含む全項目コード- たくさん）
	inspCodeMap = {k:v for k,v in xmlMeInfo['inspCodeMap'].items() if v is not None}
	if inspCodeMap == xmlMeInfo['inspCodeMap']:
		log("!!!!!!!!!!!!!!!!inspCodeMapとxmlMeInfo['inspCodeMap']同じです!!!!!!!!!!!!!!!!!!!!!!")

	# csvデータと検査項目のピックアップ（利用しなかった??）
	inspDataPickUp = xmlMeInfo['inspDataPickUp']

	# 設定対象のelementと一致するものをマッピングリストから抽出（??検査結果のみかも-適応問診コードのみ）
	matchingEleSid = {k : inspCodeMap[k] for k in set(inspCodeMap) & set(criterionSid[courseSid]['ele2eitem'].keys())}
	# 同じじゃない、matchingEleSidは最適化問診含む全項目コード（少ない）
	if matchingEleSid == xmlMeInfo['inspCodeMap']:
		log("!!!!!!!!!!!!!!!!matchingEleSidとxmlMeInfo['inspCodeMap']同じです!!!!!!!!!!!!!!!!!!!!!!")
	log("#############このコース問診含む全項目コードobj##############")
	log(matchingEleSid)

	# TODO: 最初に全ての「f_intended」フラグを落とす
	for ei in meXmlObj.findall('./eitems/eitem'):
		if ei.find('./f_intended') is None:
			ei = ET.SubElement(ei, 'f_intended')
			ei.text = '0'
		else:
			ei.find('./f_intended').text = '0'

	# 結果あてこみ（eSid: 項目コード; csvKey: 項目対応するcsvファイルのヘッダ）
	for eSid, csvKey in matchingEleSid.items():
		getValue = None
		valueData = None
		valueCode = None
		valueForm = None
		if csvKey is None or len(csvKey) < 1: continue
		if eSid not in criterionSid[courseSid]['element']:
			plgLog.warning('[{sidMorg}] unknown eSid: {eSid}, criterionMap not in'.format(sidMorg=sidMorg, eSid=eSid))
			continue

		# マッピングコードが複数登録されている場合、データ内に一致するものがあるのかを検索する
		try:
			mapCode = None
			matchKeyData = list(set(csvKey) & set(row.keys()))
			if len(matchKeyData) == 1:
				mapCode = matchKeyData[0]
			elif len(matchKeyData) > 1:
				plgLog.error('[{sidMorg}] multiple mapping code, eSid:{esid}, data: {d}'.format(sidMorg=sidMorg, esid=eSid, d=matchKeyData))
				continue
			else:
				plgLog.warning('[{sidMorg}] mapping code not in data, eSid:{esid}'.format(sidMorg=sidMorg, esid=eSid))
		except Exception as err:
			plgLog.error('search mapping code failed: {e}'.format(e=err))
			continue

		if mapCode in row and row[mapCode] is not None:
			try:
				# 結果を格納するXMLのtree検索
				obj = meXmlObj.find('elements/element/[sid="{}"]'.format(eSid)).find('result')
				# f_intendedの差し込むためのitemのsidを特定
				isid = criterionSid[courseSid]['ele2eitem'][eSid]
			except Exception as err:
				plgLog.warning('[{sidMorg}] item sid get faild, eSid: {eSid}, mapCode: {mapCode}'.format(sidMorg=sidMorg, eSid=eSid, mapCode=mapCode))
				continue
			# 結果値
			getValue = plgCmn.data2CodeFromCriterion(sidMorg, eSid=eSid, criterion=criterionSid[courseSid]['element'][eSid]['raw'], inValue=row[mapCode])
			if getValue['inType'] in ['2', '3']:
				valueData = getValue['value']
				valueForm = getValue['value-form']
				valueCode = getValue['code']
			# 未該当
			else:
				# 入力が単文、出力が文字だとこのルートかも？
				valueData = getValue['value']
				# TODO: 文字＋単文を組んだ上で数字＋不等号のデータを入れるパターンがある
				if getValue['value-form'] is not None and plgCmn.formValueStringCheck(getValue['value-form']) is not None:
					valueForm = getValue['value-form']
			# str型の場合は、前後の空白を落とす
			if type(valueData) == str:
				valueData = valueData.strip()

			# result/status/examタグ
			# TODO: XML仕様書を見ても記載がないが、画面で入力して登録ボタンを押下すると「９」が入っているのでそのまま真似する
			if obj.find('status/exam') is not None:
				obj.find('status/exam').text = '9'

			# valueタグ
			if obj.find('value') is not None:
				obj.find('value').text = valueData
			else:
				try:
					ET.SubElement(obj, 'value').text = valueData
				except:
					plgLog.error('[{sidMorg}] [XMLME] add xml value tag failed [sid:{sid}]'.format(sidMorg=sidMorg, sid=eSid))

			# value-fromタグ
			if obj.find('value-form') is not None:
				obj.find('value-form').text = valueForm
			else:
				try:
					if valueForm is not None:
						ET.SubElement(obj, 'value-form').text = valueForm
				except:
					plgLog.error('[{sidMorg}] [XMLME] add xml value-form tag failed [sid:{sid}]'.format(sidMorg=sidMorg, sid=eSid))

			# codeタグのチェック、存在しなければ作成
			if obj.find('code') is not None:
				# 存在する、かつ、結果値として取り込む必要がある場合（医師判定など）
				if valueCode is not None:
					obj.find('code').text = valueCode
			else:
				if valueCode is not None:
					try:
						ET.SubElement(obj, 'code').text = valueCode
					except:
						plgLog.error('[{sidMorg}] [XMLME] add xml code tag failed [sid:{sid}, code:{c}]'.format(sidMorg=sidMorg, sid=eSid, c=valueCode))

			f_Intended = fIntendedFlag.ON
			# オプションをみて、valueが空のデータ受信時は「受診フラグ」をOFFにする
			if 'valueIsNull2fIntendedFlagOFF' in optionMap and optionMap['valueIsNull2fIntendedFlagOFF']:
				if valueData is None or len(valueData) < 1:
					f_Intended = fIntendedFlag.OFF

			try:
				# f_intended操作対象の特定
				fobj = meXmlObj.find('eitems/eitem/[sid="{}"]'.format(isid))
				# タグがなければ作成して格納
				if fobj.find('f_intended') is None:
					fobj = ET.SubElement(fobj, 'f_intended')
					fobj.text = f_Intended
				# タグがあれば値の変更だけ
				else:
					fobj.find('f_intended').text = f_Intended

				# codeが存在するときだけ、eitemのタグをさらに変更する
				if valueCode is not None:
					# result/status/opinionに謎の「９」をいれる
					if fobj.find('result/status/opinion') is not None:
						fobj.find('result/status/opinion').text = '9'
					# result/opinions/opinion/codeにインポート対象の戻り値にcodeがあれば
					if fobj.find('result/opinions/opinion/code') is not None:
						_xmlCode = fobj.find('result/opinions/opinion/code').text
						# XML内のcode値よりインポート側の値が大きい場合のみ
						if _xmlCode is not None and int(_xmlCode) <= int(valueCode):
							fobj.find('result/opinions/opinion/code').text = valueCode
			except:
				plgLog.debug('[{sidMorg}] [XMLME] tag not found [sid:{sid}, name:{name}]'.format(sidMorg=sidMorg, sid=eSid, name=mapCode))
				continue

	try:
		xmlMe = ET.tostring(meXmlObj, encoding='UTF-8').decode('UTF-8')
	except Exception as err:
		plgLog.error('[{sidMorg}] xmlobj2string msg:{e}'.format(sidMorg=sidMorg, e=err))
		return (None, None)

	return (xmlMe, datetime.datetime.now())


# 必須情報のチェック
def checkRequiredData(sidMorg, data):
	ret = False
	errcnt = 0
	# 属性情報のチェック
	for k in requiredMap['examinee']:
		try:
			if data[examineeMap[k]] is None or len(data[examineeMap[k]]) < 1:
				errcnt += 1
				plgLog.warning('[{sidMorg}] examineeMap is no data: {examMap}'.format(sidMorg=sidMorg, examMap=examineeMap[k]))
		except:
			errcnt += 1
			plgLog.warning('[{sidMorg}] examineeMap is no key: {examMap}'.format(sidMorg=sidMorg, examMap=examineeMap[k]))
		continue
	# 予約情報のチェック
	for k in requiredMap['appoint']:
		try:
			# コースID強制指定フラグがONの場合、かつ、デフォルトコースIDが指定されていたらエラーチェック対象外とする
			if 'courseId' == k and 'force_courseId' in optionMap and optionMap['force_courseId'] is not None and len(optionMap['force_courseId']) > 0:
				continue
			elif data[appointMap[k]] is None or len(data[appointMap[k]]) < 1:
				errcnt += 1
				plgLog.warning('[{sidMorg}] appointMap is no data: {apoMap}'.format(sidMorg=sidMorg, apoMap=appointMap[k]))
		except:
			errcnt += 1
			plgLog.warning('[{sidMorg}] appointMap is no key: {apoMapKey}'.format(sidMorg=sidMorg, apoMapKey=k))
		continue

	if errcnt == 0:
		ret = True

	return ret


# コース情報取得
def getCourseInfo(sidMorg, row):
	courseMapInfo = None
	mapCourseID = None

	# コースIDからコース情報の特定
	if appointMap['courseId'] in row and row[appointMap['courseId']] is not None:
		mapCourseID = row[appointMap['courseId']]

	# コースIDが取得できない（含まれていない）
	if mapCourseID is None or len(mapCourseID) < 1:
		# オプションでコースIDが強制されている場合はそれを採用する
		if 'force_courseId' in optionMap and optionMap['force_courseId'] is not None and len(optionMap['force_courseId']) > 0:
			mapCourseID = optionMap['force_courseId']
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


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |- TODO: 一括取り込み用全てののデータを揃い
#	|- 受診者属性情報取り込み用:
#	|- 予約情報取り込み用:
#	|- 結果取り込み用:
# |- Param:
#	|- data: インポートしたCSVからpython Dictに変換されたjson型データ
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def setTappointMe(sidMorg, data):
	if data is None: return None
	global courseMap, errMsg
	# インポートのCSVレコード数
	dataCount = len(data)
	procCount = 0
	retStatus = error
	errRowData = []
	# 各種取り込み用必須情報
	retData = []

	# コース情報取得
	courseMap = csv2xml_mapping.courseMapGet(sidMorg)
	# 取り込みレコード（CSVの行）ごとに必須情報を揃う
	for row in data:
		tmpData = {
			'visitId'		: None,		# 受診番号
			'examineeItem'	: None,		# 受診者属性情報
			'appointItem'	: None,		# 予約情報と検査結果(xml_me)
			'apoStatus'		: None,		# 予約ステータス（予約/受付）
			'apoAction'		: None,		# 予約アクションステータス(1:新規　2:更新　3:キャンセル 4:エクスポート送信)
			'dataItem'		: row,		# 元のデータ（csv）
			'courseMapInfo' : None,		# コース情報
			'dataCount'		: dataCount,# インポートのCSVレコード数
		}

		reApoSts = None
		sid_appoint = None
		courseMapInfo = None
		vid = None
		xmlMe = None
		xmlMeTime = None
		xmlMeInfo = None

		# validation-1: 必須項目のチェック
		retCheck = checkRequiredData(sidMorg, row)
		if retCheck == False:
			plgLog.warning('[{sidMorg}] no required data, row data: {row}'.format(sidMorg=sidMorg, row=row))
			errRowData.append(row)
			continue

		# visitIDの取得
		if 'visitId' in appointMap and appointMap['visitId'] in row:
			vid = row[appointMap['visitId']]

		tmpData['visitId'] = vid

		# カルテID取得
		cid = row[examineeMap['examinee/id']]

		# 受診日取得
		tmpDateTime = row[appointMap['appointDay']].split(' ')
		# 日付のみ - ○：2021-12-08; ×:2021-12-8
		examDate = re.sub(r'([0-9]{4})[/\-]?([0-9]{2})[/\-]?([0-9]{2})', r'\1/\2/\3', tmpDateTime[0])
		if 'appointTime' in appointMap and appointMap['appointTime'] in row:
			examDateTime = None
			_examDateTime = row[appointMap['appointTime']].split(':')
			if len(_examDateTime) == 2:
				examDateTime = re.sub(r'([0-9]{1,2})[:]?([0-9]{1,2})', r'\1:\2:00', row[appointMap['appointTime']])
			elif len(_examDateTime) == 3:
				examDateTime = re.sub(r'([0-9]{1,2})[:]?([0-9]{1,2})[:]?([0-9]{1,2})', r'\1:\2:\3', row[appointMap['appointTime']])
			else:
				plgLog.info('unknwon time format, data:[{}], default time set'.format(row[appointMap['appointTime']]))

			if examDateTime is None or len(examDateTime) < 1:
				# みつからない場合はデフォルトを入れる
				examDateTime = '00:00:00'
		else:
			# 時刻のみ - 分割チェック
			# if len(tmpDateTime) == 2 and tmpDateTime[1] is not None and len(tmpDateTime[1]) > 0 and re.match(r'[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}', tmpDateTime[1]) is not None:
			# 	examDateTime = tmpDateTime[1]
			if len(tmpDateTime) == 2 and tmpDateTime[1] is not None and len(tmpDateTime[1]) > 0:
					# hh:mm
					if re.match(r'[0-9]{1,2}:[0-9]{1,2}', tmpDateTime[1]) is not None:
						examDateTime = tmpDateTime[1] + ':00'
					# hh:mm:ss
					elif re.match(r'[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}', tmpDateTime[1]) is not None:
						examDateTime = tmpDateTime[1]
			else:
				# 予約時間不明／ない
				examDateTime = '00:00:00'

		if plgCmn.dateFormatCheck(examDate) == False:
			# あり得ない日付の場合はスキップ
			plgLog.info('[{sidMorg}] appointDay format error, convDay:[{day}], csvText:[{dayOrg}]'.format(sidMorg=sidMorg, day=examDate, dayOrg=row[appointMap['appointDay']]))
			errRowData.append(row)
			continue
		# 完全な日時
		examDtObj = plgCmn.text2datetime(examDate + ' ' + examDateTime)

		# ログ出力用ベース情報
		logExamInfo = 'visitId: {vid}, karuteId: {cid}, apoDay: {apoDay}'.format(vid=vid, cid=cid, apoDay=examDate)


		# 予約ステータス取得（"登録"ステータスで初期化する）
		apoStatus = tAppointSts['reservation']
		# アクションステータス(1:新規　2:更新　3:キャンセル)
		apoAct = None
		# 何もしてない
		apoActSts = None
		if 'f_force_checkin' in optionMap and optionMap['f_force_checkin'] == 1:
			# 強制チェックイン
			apoStatus = tAppointSts['checkin']
			apoAct = appointAct.register
			apoActSts = appointSts.checkin
		else:
			# 予約/受付ステータス(こうのすではなし) - こうのすなし
			if 'apoStatus' in appointMap and appointMap['apoStatus'] in row:
				try:
					if int(row[appointMap['apoStatus']]) == appointSts.reservation:
						apoActSts = appointSts.reservation
					elif int(row[appointMap['apoStatus']]) == appointSts.checkin:
						apoActSts = appointSts.checkin
				except:
					plgLog.error('[{sidMorg}] appoint action status unknown type: {sts}, {logExamInfo}'.format(sidMorg=sidMorg, sts=row[appointMap['apoStatus']], logExamInfo=logExamInfo))
					continue

			# アクション取得(1:新規　2:更新　3:キャンセル)
			if 'apoAction' in appointMap and appointMap['apoAction'] in row:
				try:
					if int(row[appointMap['apoAction']]) == appointAct_konosu.new_register:
						apoAct = appointAct_konosu.new_register
					elif int(row[appointMap['apoAction']]) == appointAct_konosu.change:
						apoAct = appointAct_konosu.change
					elif int(row[appointMap['apoAction']]) == appointAct_konosu.cancel:
						apoAct = appointAct_konosu.cancel
				except:
					plgLog.error('[{sidMorg}] appoint action unknown type: {sts}, {logExamInfo}'.format(sidMorg=sidMorg, sts=row[appointMap['apoAction']], logExamInfo=logExamInfo))
					continue

		# 受診者検索＆xml_examineeの取得
		sid_examinee, examineeXML = getSidExaminee(sidMorg, cid)

		tmpData['examineeItem'] = {'sid_examinee': sid_examinee, 'karuteId': cid, 'examDate': examDate,'apoDt': examDtObj, 'examineeXML': examineeXML}
		tmpData['apoStatus'] = apoStatus
		tmpData['apoAction'] = apoAct
		tmpData['apoActionStatus'] = apoActSts

		# ログ出力用ベース情報
		logExamInfo = 'karuteId: {cid}, apoDay: {apoDay}, sid_examinee: {sidExam}'.format(cid=cid, apoDay=examDate, sidExam=sid_examinee)

		# コース情報取得
		courseMapInfo = getCourseInfo(sidMorg, row)
		if courseMapInfo is None:
			plgLog.info('[{sidMorg}] courseId is None, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			errRowData.append(row)
			continue
		elif courseMapInfo == -1:
			plgLog.info('[{sidMorg}] courseId is get faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			errRowData.append(row)
			continue
		elif courseMapInfo == -2:
			plgLog.info('[{sidMorg}] courseMapInfo is None, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			errRowData.append(row)
			continue
		elif courseMapInfo == -3:
			plgLog.info('[{sidMorg}] courseSid is None or sidMe is None, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			errRowData.append(row)
			continue

		# ログ出力用ベース情報
		logExamInfo = 'karuteId: {cid}, apoDay: {apoDay}, sid_examinee: {sidExam}, courseSid: {courseSid}'.format(cid=cid, apoDay=examDate, sidExam=sid_examinee, courseSid=courseMapInfo['sid'])

		# 備考欄（こうのすなし--暫定：問診結果取り込みの時あるかも）
		# t_appoint.remarks
		remarks = None
		if 'remarks' in appointMap and appointMap['remarks'] in row and row[appointMap['remarks']]:
			remarks = row[appointMap['remarks']]

		# t_appointを検索（予約情報検索：t_appoint && t_appoint_me.xml_me）
		tAppoint = t_appoint.getTappoint(sidMorg=sidMorg, vid=vid, cid=cid, apoDay=examDate, sidExaminee=sid_examinee)
		# 検索結果が複数の場合
		if tAppoint is not None:
			if len(tAppoint) > 1:
				plgLog.warning('[{sidMorg}] examinee check return Multiple'.format(sidMorg=sidMorg))
			tAppoint = tAppoint[0]

			# コースIDの取得に失敗
			if 'inCourseID' not in tAppoint:
				plgLog.warning('[{sidMorg}] inCourseID get faild, data:[{logExamInfo}]'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				continue

			# 予約:0／受付:1以外は処理しない（判定済み:2, 確定済み:3）
			if tAppoint['status'] not in [tAppointSts['reservation'], tAppointSts['checkin']]:
				plgLog.warning('[{sidMorg}] t_appoint status proc 0-1, t_appoint status is {sts}'.format(sidMorg=sidMorg, sts=tAppoint['status']))
				if tAppoint['status'] == tAppointSts['judgment']:
					msg2js('第{columnCount}行,カルテID:{cid}, {msg}'.format(columnCount=procCount+1, cid=cid, msg='受診者は判定済みの為、スキップします'))
				elif tAppoint['status'] == tAppointSts['confirm']:
					msg2js('第{columnCount}行,カルテID:{cid}, {msg}'.format(columnCount=procCount+1, cid=cid, msg='受診者は確定済みの為、スキップします'))
				continue

			# visitidが存在する、かつ、t_appointの検索結果と一致（TODO: カルテIDのみだと同日複数コースのチェックができないため、visitIdは必須）
			if vid is not None and tAppoint['visitid'] == vid:
				# 登録データと同一コースではない場合、処理フラグのチェック
				if tAppoint['inCourseID'] != row[appointMap['courseId']]:
					plgLog.warning('[{sidMorg}] t_appoint check CourseID unmatch'.format(sidMorg=sidMorg))
					# 強制キャンセルフラグが無効の場合、データ異常扱いでスキップ
					if 'f_unmatchIdAppointForceCancel' in optionMap and optionMap['f_unmatchIdAppointForceCancel'] != 1:
						plgLog.warning('[{sidMorg}] skip registration process'.format(sidMorg=sidMorg))
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
				plgLog.warning('[{sidMorg}] {msg}, data:[{logExamInfo}]'.format(sidMorg=sidMorg, msg=_msg, logExamInfo=logExamInfo))
				del _msg
				continue

		# キャンセル(t_appoint_me.xml_me関連の基準値などの操作要らない)
		if apoAct == appointAct_konosu.cancel:
				pass
		else:
			# XMLMEや基準の取得（予約情報あるないでもやる- 新規や更新の場合）
			xmlMeInfo = getXmlMeInfo(sidMorg, tAppoint, courseMapInfo, row)
			if xmlMeInfo is None:
				continue
			if 'meXmlObj' not in xmlMeInfo or xmlMeInfo['meXmlObj'] is None:
				plgLog.error('[{sidMorg}] get XMLME faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				continue
			if 'criterionSid' not in xmlMeInfo or xmlMeInfo['criterionSid'] is None:
				plgLog.error('[{sidMorg}] get criterionSid faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				continue
			if 'inspCodeMap' not in xmlMeInfo or xmlMeInfo['inspCodeMap'] is None:
				plgLog.error('[{sidMorg}] get inspCodeMap faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				continue
			if 'inspDataPickUp' not in xmlMeInfo or xmlMeInfo['inspDataPickUp'] is None:
				plgLog.error('[{sidMorg}] get inspDataPickUp faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				errRowData.append(row)
				continue
			tmpData['courseMapInfo'] = courseMapInfo

			# TODO: 強制予約削除フラグチェック、検査項目が全て空の場合、予約キャンセル扱いとしてデータの論理削除(t_appoint.status=0、 t_appoint.s_reappoint=4)
			if 'f_allDataNullisAppointCancel' in optionMap and optionMap['f_allDataNullisAppointCancel'] == 1:
				if len(xmlMeInfo['inspDataPickUp']) < 1:
					tmpData['apoStatus'] = tAppointSts['reservation']
					tmpData['apoAction'] = appointAct.cancel
					tmpData['apoActionStatus'] = appointSts.reservation

			# XMLMEの作成(新規と更新両方でもやる)
			# このxmlMeが結果マッピング終わった
			xmlMe, xmlMeTime = createXmlMe(sidMorg, vid, cid, examDtObj, courseMapInfo['sidMe'], courseMapInfo['sid'], sid_examinee, row, xmlMeInfo)
			if xmlMe is None:
				plgLog.error('create XMLME failed')
				continue
			else:
				if tAppoint is None:
					pass
				# ステータスが予約／受付済みのみXML更新
				elif 0 <= tAppoint['status'] <= 1:
					# 日付変更しました
					if tAppoint['dt_appoint'].date() != examDtObj.date():
						reApoSts = reAppointSts['day']
					# 健診内容更新しました
					else:
						reApoSts = reAppointSts['change']

		tmpData['appointItem'] = {'reApoSts': reApoSts, 'xmlMe': xmlMe, 'xmlMeInfo': xmlMeInfo, 'tAppoint': tAppoint, 'remarks': remarks, 'xmlMeTime': xmlMeTime}

		retData.append(tmpData)
		del tmpData
		procCount += 1

	plgLog.info('[{sidMorg}] create data procCount/dataCount: {pCnt}/{dCnt}'.format(sidMorg=sidMorg, dCnt=dataCount, pCnt=procCount))

	return retData


# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
#
# |-TODO: DBへの一括登録処理
#	|- 受診者属性情報取り込み
#	|- 予約情報取り込み
#	|- 検査結果と問診結果取り込み
# |- Param:
#	|- rows: list(dict) type of "retData" returned from setTappointMe fun
#
# -*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
def registerDatabase(sidMorg, rows):
	if rows is None:
		return

	global errMsg
	procCount = 0
	columnCount = 0
	# statusは予約・受付ではないと含まないで
	dataCount = len(rows)
	for row in rows:
		# 総件数(定義所おかしいけど)
		dataCount = row['dataCount']
		dataUpdTime = None
		# オーダー連携用（ステータス）
		ordSts = None
		appointRegSkip = False
		sid_appoint = None
		vid = row['visitId']
		cid = row['examineeItem']['karuteId']
		apoDt = row['examineeItem']['apoDt']
		examDate = row['examineeItem']['examDate']
		tAppoint = row['appointItem']['tAppoint']

		sid_examinee =  row['examineeItem']['sid_examinee']

		reApoSts = row['appointItem']['reApoSts']

		# ログ出力用ベース情報
		logExamInfo = 'visitId: {vid}, karuteId: {cid}, apoDay: {apoDay}'.format(vid=row['visitId'], cid=cid, apoDay=apoDt)
		
		# 予約処理時、受診者未登録の場合はスキップ
		if sid_examinee is None:
			columnCount += 1
			msg = 'examiee not register. skip appoint regster'
			errMsg.append(msg)
			log('[{sidMorg}] {m}, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo, m=msg))
			msg2js('第{columnCount}行,カルテID:{cid}, {msg}'.format(columnCount=columnCount, cid=cid, msg='受診者未登録のため、予約登録をスキップします'))
			continue
		
		# 受診者登録（新規／更新）
		sid_examinee = setExaminee(sidMorg, row['examineeItem']['sid_examinee'], row['examineeItem']['examineeXML'], row['dataItem'])
		if sid_examinee is None:
			msg = 'examiee register failed'
			errMsg.append('karuteId:[{}] {}'.format(cid, msg))
			plgLog.info('[{sidMorg}] {msg}, {logExamInfo}'.format(sidMorg=sidMorg, msg=msg, logExamInfo=logExamInfo))
			continue
		
		# 予約情報がありましたら、appointAct_konosu.new_register(1)でも、何もしない
		if tAppoint is not None:
			# 予約キャンセル
			if row['apoAction'] == appointAct_konosu.cancel:
				retSts = delTappoint(sidMorg=sidMorg, tAppoint=tAppoint)
				msg = 't_appoint cancel'

				# TODO: daidaiのキャンセルに成功した場合に、Kプラス連携の処理を行う
				if retSts == True:
					msg += ' success'
					# # K+オーダー連携
					# t_ext_order.status(予約キャンセル)
					ordSts = examSts['appointDel']
					# K+予約／受付連携の実施
					# K+側はオーダーキーさえ変わらないならコース変更はアップデートで対応できるが、daidai側の仕様でXMLMEの作り直しが発生するためキャンセルを行う方針
					procOrder(sidMorg, tAppoint, vid, cid, sid_examinee, tAppoint['dt_appoint'], ordSts, row['dataItem'], tAppoint['dt_appoint'])
					# t_ext_infoのレコードを論理削除
					xmlExtLink = createExtLinkXML(sidMorg, tAppoint, dataUpdTime)
					# def extInfoPost(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None, sUpd=2):
					t_ext_info.extInfoPost(sidMorg, pName=pConfig['plgName'], sidAppoint=tAppoint['sid'], sidExaminee=sid_examinee, cid=cid, updateTime=xmlExtLink['updTime'], xmlInfo=xmlExtLink['xml'], sUpd=3)
				else:
					msg += ' faild'
				errMsg.append(msg)
				plgLog.info('[{sidMorg}] {msg}, {logExamInfo}'.format(sidMorg=sidMorg, msg=msg, logExamInfo=logExamInfo))
			# 更新
			elif row['apoAction'] == appointAct_konosu.change:
				ordSts = examSts['update']
				# t_appoint_me table更新したのみ
				sid_appoint = setTappointUpdate(sidMorg, row)
				if sid_appoint is None:
					plgLog.error('[{sidMorg}] t_appoint update faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				else:
					# t_appointのステータス変更（更新の場合のみやります）
					# stsCode=row['apoStatus']
					t_appoint.setTappointStatus(sidMorg, sid_appoint=sid_appoint, stsCode=tAppoint['status'], sReappoint=row['appointItem']['reApoSts'], apoDate=row['examineeItem']['apoDt'])
					# t_appoint.setTappointStatus(sidMorg, sid_appoint=sid_appoint, stsCode='1', sReappoint=row['appointItem']['reApoSts'], apoDate=row['examineeItem']['apoDt'])
					# 予約日の変更？
					if reApoSts == reAppointSts['day']:
						# # K+オーダー連携
						# 予約日変更の場合はキャンセルオーダを先に出す
						# dd_data.t_ext_order.status:
							# |- 1レコード：　3:予約キャンセル
							# |- 2レコード：　1:予約
						ordSts = examSts['appointDel']
						# まず、論理キャンセル(t_ext_order)
						procOrder(sidMorg, tAppoint, vid, cid, sid_examinee, tAppoint['dt_appoint'], ordSts, row['dataItem'], tAppoint['dt_appoint'])
						# 3 ==> 1(新規)
						ordSts = examSts['appoint']
					else:
						# コース更新や予約時刻変更？
						ordSts = examSts['update']

					plgLog.info('[{sidMorg}] t_appoint update success, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
					log('[{sidMorg}] t_appoint update success, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			elif row['apoAction'] == appointAct_konosu.new_register:
				columnCount += 1
				log('[{sidMorg}] new register action, but skip because t_appoint have existed'.format(sidMorg=sidMorg))
				msg2js('第{columnCount}行,カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(columnCount=columnCount, cid=cid, courseName=row['dataItem']['CourseName'], examDate=examDate, msg='予約情報がありましたため、新規予約をスキップします。'))
				continue					
		# 新規予約(appointAct_konosu.new_register(1))
		else:
			# 何の為は謎(とりあえずコメントする)???
			# 強制予約削除フラグON、かつ、取り込み対象検査項目が存在しない場合、登録処理スキップフラグON
			if 'f_allDataNullisAppointCancel' in optionMap and optionMap['f_allDataNullisAppointCancel'] == 1:
				if len(row['appointItem']['xmlMeInfo']['inspDataPickUp']) < 1:
					appointRegSkip = True

			# こうのす- キャンセルアクションだが、該当するt_appointが存在しない場合は終わり
			if row['apoAction'] == appointAct_konosu.cancel:
				columnCount += 1
				log('[{sidMorg}] Cancel action, but skip because t_appoint does not exist'.format(sidMorg=sidMorg))
				msg2js('第{columnCount}行,カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(columnCount=columnCount, cid=cid, courseName=row['dataItem']['CourseName'], examDate=examDate, msg='予約情報が見つからないため、予約キャンセルをスキップします。'))
				continue
			elif row['apoAction'] == appointAct_konosu.change:
				log('[{sidMorg}] Change action, but do new register because t_appoint does not exist'.format(sidMorg=sidMorg))
				msg2js('第{columnCount}行,カルテID:{cid}, コース名:{courseName}, 受診日：{examDate}, {msg}'.format(columnCount=columnCount+1, cid=cid, courseName=row['dataItem']['CourseName'], examDate=examDate, msg='予約情報が見つからないため、更新アクションなのに、新規予約登録します。'))
			
			# 新規予約登録
			if not appointRegSkip:
				# 新規(setTappointPutでt_appoint && t_appoint_me両方新規登録)
				sid_appoint = setTappointNew(sidMorg, vid, apoDt, sid_examinee, row['courseMapInfo']['sidMe'], row['appointItem']['xmlMe'], row['appointItem']['remarks'])
				if sid_appoint is None:
					plgLog.error('[{sidMorg}] t_appoint add faild, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				else:
					# t_ext_order.status(新規予約)
					ordSts = examSts['appoint']
					# t_appointを検索（予約情報検索：t_appoint && t_appoint_me.xml_me）
					tAppoint = t_appoint.getTappoint(sidMorg=sidMorg, vid=vid, cid=cid, apoDay=examDate, sidExaminee=sid_examinee)[0]
					plgLog.info('[{sidMorg}] t_appoint add success, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
					log('[{sidMorg}] t_appoint add success, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
			else:
				plgLog.info('[{sidMorg}] t_appoint register skip, Data to be imported does not exist, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
				log('[{sidMorg}] t_appoint register skip, Data to be imported does not exist, {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo))
		
		# K+オーダー連携(更新や新規予約オーダー共通処理)
		if row['apoAction'] != appointAct_konosu.cancel:
			# xml_externalLinkageの作成／更新
			try:
				xmlExtLink = createExtLinkXML(sidMorg, tAppoint, dataUpdTime, courseId=row['dataItem'][appointMap['courseId']])
				# 連携情報の新規登録
				if xmlExtLink['raw'] is None:
					# def extInfoPut(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None):
					t_ext_info.extInfoPut(sidMorg, pName=pConfig['plgName'], sidAppoint=tAppoint['sid'], sidExaminee=sid_examinee, vid=vid, cid=cid, dtAppoint=apoDt, updateTime=xmlExtLink['updTime'], xmlInfo=xmlExtLink['xml'])
				# 更新
				else:
					# def extInfoPost(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None, sUpd=2):
					t_ext_info.extInfoPost(sidMorg, pName=pConfig['plgName'], sidAppoint=tAppoint['sid'], sidExaminee=sid_examinee, vid=vid, cid=cid, dtAppoint=apoDt, updateTime=xmlExtLink['updTime'], xmlInfo=xmlExtLink['xml'])
			except Exception as err:
				msg2js('連携情報の更新処理でエラーが発生しました。err:[{err}]'.format(err=err))
				log('[{sidMorg}] externalLikageXML get faild:{e} {logExamInfo}'.format(sidMorg=sidMorg, logExamInfo=logExamInfo, e=err))
				traceLog(err)
				continue
			
			# K+二オーダー情報送り
			procOrder(sidMorg, tAppoint, vid, cid, sid_examinee, examDate, ordSts, row['dataItem'], apoDt)
		
		# TODO: sid_appointが存在しない場合、登録に失敗している想定
		# if sid_appoint is not None:
		# 	# t_appointのステータス変更
		# 	t_appoint.setTappointStatus(sidMorg, sid_appoint=sid_appoint, stsCode=row['apoStatus'], sReappoint=row['appointItem']['reApoSts'], apoDate=row['examineeItem']['apoDt'])

		procCount += 1
		columnCount += 1
	plgLog.info('[{sidMorg}] register data procCount/dataCount: {pCnt}/{dCnt}'.format(sidMorg=sidMorg, dCnt=dataCount, pCnt=procCount))
	log('総件数:{total_cnt}, 登録/更新件数:{regist_cnt}'.format(total_cnt=dataCount, regist_cnt=procCount))
	msg2js('総件数:{total_cnt}, 登録/更新件数:{regist_cnt}'.format(total_cnt=dataCount, regist_cnt=procCount))
	return


# workファイルが存在したらリネームする
def workFileCheck(plgDir):
	targetDir = pDir
	if plgDir is not None:
		targetDir = plgDir

	fileList = list(targetDir.glob('*.WORK'))
	for targetFile in fileList:
		mvPath = targetFile.parent
		newName = re.sub(r'\.WORK$', '', targetFile.name)
		targetFile.rename(mvPath.joinpath(newName))


# CSVファイルの読み書き
def csvFileOpen(mode, fp, enc='UTF-8', data=None, flagHeader=True):
	data = None
	try:
		if mode == 'read':
			data = fileCtrl.csvRead(fp, encoding=enc, flagHeader=flagHeader)
		elif mode == 'write' and data is not None:
			fileCtrl.csvWrite(fp, data, data[0].keys(), encoding=enc)
			return
		else:
			return None
	except:
		raise
	return data


# TODO: リストをN分割する
# https://www.python.ambitious-engineer.com/archives/1843
def split_list(l, n):
	"""
	リストをサブリストに分割する
	:param l: リスト
	:param n: サブリストの要素数
	:return:
	"""
	for idx in range(0, len(l), n):
		yield l[idx:idx + n]


# インポート対象ファイルを開く
def fileOpen(sidMorg, fp):
	data = None
	errData = None
	ret = None
	newfp = None
	try:
		# fp = pathlib.Path(fp)
		# oldFile = str(fp)
		# workFile = pathlib.Path(str(fp) + '.WORK')		# 実ファイル名の末尾に「.WORK」を付与
		# fp.rename(workFile)								# 処理を行う対象のファイル名を変更する
		# newfp = pathlib.Path(workFile)					# 変更後のPATHを再取得
		# plgLog.info('[{sidMorg}] * call item: {fname}'.format(sidMorg=sidMorg, fname=str(newfp)))
		
		# # ＊ファイルオープン(default: flagHeader=True)：
		# #	|- ヘッダありCSVファイル:	dict type(json ==> python dict: [{:}, {:}, ...])
		# #	|- ヘッダなしCSVファイル:	list type(全部はマッピングデータ: [[,], [,], ...])	
		# fileData = csvFileOpen('read', newfp, pConfig['encoding'])
		# kounosuインポート・サンプル(csv with headers)

		# create a dictionary List
		fileData = []
		dataJson = ""
		headers = []
		# len = 20
		# headers = ["AppointDate","AppointNumber","AppointStatus","CourseName","CourseId","Id","Name","Kana","Sex","Dob","Age","Zip","Address","Company","CompanyId", "GMJ0101", "GMF0101", "M00101", "M00201", "M00401"]
		# len = 139
		# headers = ['AppointDate', 'AppointNumber', 'AppointStatus', 'CourseName', 'CourseId', 'Id', 'Name', 'Kana', 'Sex', 'Dob', 'Age', 'Zip', 'Address', 'Company', 'CompanyId', 'GMJ0101', 'GMF0101', 'M00101', 'M00201', 'M00401', 'GMJ0801', 'GMF0801', 'M00301', 'GMJ0201', 'GMF0201', 'M00601', 'M00602', 'M00603', 'M00604', 'GMJ0301', 'GMF0301', 'M00701', 'M00702', 'M00703', 'M00704', 'GMJ0401', 'GMF0401', 'M00801', 'M00802', 'M00803', 'M00804', 'M00805', 'M00806', 'GMJ0202', 'GMF0202', 'M00913', 'M00914', 'M00915', 'M00916', 'M00917', 'M00918', 'GBJ0101', 'GBF0101', 'B00101', 'B00201', 'B00301', 'B00401', 'B00403', 'B00501', 'GBJ0201', 'GBF0201', 'B00601', 'B00701', 'B00801', 'B00901', 'B01001', 'B01101', 'B01201', 'GBJ0401', 'GBF0401', 'B01501', 'B01502', 'B01601', 'B01602', 'B01603', 'B01701', 'GBJ0501', 'GBF0501', 'B01901', 'GBJ1601', 'GBF1601', 'B02001', 'B02101', 'B02201', 'GUJ0301', 'GUF0301', 'U00301', 'GUJ0401', 'GUF0401', 'U00101', 'GUJ0201', 'GUF0201', 'U00201', 'GSJ0101', 'GSF0101', 'S00101', 'S00102', 'GQJ0101', 'GQF0101', 'Q00101', 'Q00201', 'Q00301', 'Q00401', 'Q00501', 'Q00601', 'Q00701', 'Q00801', 'Q00901', 'Q01001', 'Q01101', 'Q01201', 'Q01301', 'Q01401', 'Q01501', 'Q01601', 'Q01701', 'Q01801', 'Q01901', 'Q02001', 'Q02701', 'Q02801', 'GIJ0201', 'GIF0201', 'I00201', 'I00202', 'I00203', 'I00204', 'I00214', 'GIJ0101', 'GIF0101', 'I00101', 'I00111', 'GDJ0101', 'GDF0101', 'D00401', 'D00402', 'D00403', 'TJ0101', 'TF0101']
		encoding = "shift-jis"
		# encoding = "utf-8"
		

		with open(fp, 'r', encoding=encoding) as csvf:
			# ------
			# headあり　&& headなし
			# ------
			csvReader = csv.reader(csvf)

			# # head list
			head_row = next(csvReader)
			# log(head_row)
			# log(len(head_row))

			# ------
			# 特定カラム数処理
			# ------
			# if head_row[0] == "AppointDate":
			# 	# 第一行目はヘッダ
			# 	headers = head_row[:19]
			# else:
			# 	headers = ["AppointDate","AppointNumber","AppointStatus","CourseName","CourseId","Id","Name","Kana","Sex","Dob","Age","Zip","Address","Company","CompanyId",  "GMJ0101", "GMF0101", "M00101", "M00201", "M00401"]
			# 	# ヘッダなし、第一行目も予約情報
			# 	dict_row = dict(zip(headers, head_row[:19]))
			# 	fileData.append(dict_row)
			# #convert each csv row into python dict(第二行目から)
			# for row in csvReader: 
			# 	dict_row = dict(zip(headers, row[:19]))
			# 	fileData.append(dict_row)

			# ------
			# 全カラム数処理
			# ------
			if head_row[0] == "AppointDate":
				# 第一行目はヘッダ
				headers = head_row
			else:
				headers = ['AppointDate', 'AppointNumber', 'AppointStatus', 'CourseName', 'CourseId', 'Id', 'Name', 'Kana', 'Sex', 'Dob', 'Age', 'Zip', 'Address', 'Company', 'CompanyId', 'GMJ0101', 'GMF0101', 'M00101', 'M00201', 'M00401', 'GMJ0801', 'GMF0801', 'M00301', 'GMJ0201', 'GMF0201', 'M00601', 'M00602', 'M00603', 'M00604', 'GMJ0301', 'GMF0301', 'M00701', 'M00702', 'M00703', 'M00704', 'GMJ0401', 'GMF0401', 'M00801', 'M00802', 'M00803', 'M00804', 'M00805', 'M00806', 'GMJ0202', 'GMF0202', 'M00913', 'M00914', 'M00915', 'M00916', 'M00917', 'M00918', 'GBJ0101', 'GBF0101', 'B00101', 'B00201', 'B00301', 'B00401', 'B00403', 'B00501', 'GBJ0201', 'GBF0201', 'B00601', 'B00701', 'B00801', 'B00901', 'B01001', 'B01101', 'B01201', 'GBJ0401', 'GBF0401', 'B01501', 'B01502', 'B01601', 'B01602', 'B01603', 'B01701', 'GBJ0501', 'GBF0501', 'B01901', 'GBJ1601', 'GBF1601', 'B02001', 'B02101', 'B02201', 'GUJ0301', 'GUF0301', 'U00301', 'GUJ0401', 'GUF0401', 'U00101', 'GUJ0201', 'GUF0201', 'U00201', 'GSJ0101', 'GSF0101', 'S00101', 'S00102', 'GQJ0101', 'GQF0101', 'Q00101', 'Q00201', 'Q00301', 'Q00401', 'Q00501', 'Q00601', 'Q00701', 'Q00801', 'Q00901', 'Q01001', 'Q01101', 'Q01201', 'Q01301', 'Q01401', 'Q01501', 'Q01601', 'Q01701', 'Q01801', 'Q01901', 'Q02001', 'Q02701', 'Q02801', 'GIJ0201', 'GIF0201', 'I00201', 'I00202', 'I00203', 'I00204', 'I00214', 'GIJ0101', 'GIF0101', 'I00101', 'I00111', 'GDJ0101', 'GDF0101', 'D00401', 'D00402', 'D00403', 'TJ0101', 'TF0101', 'QB007', 'Email', 'Remarks', 'Memo']
				# ヘッダなし、第一行目も予約情報
				dict_row = dict(zip(headers, head_row))
				fileData.append(dict_row)
			#convert each csv row into python dict(第二行目から)
			for row in csvReader: 
				dict_row = dict(zip(headers, row))
				fileData.append(dict_row)

			# ------
			# head あり
			# ------
			# csvreader = csv.DictReader(csvf)
			# fileData = [row for row in csvreader]

		log(fileData)

		if len(fileData) < 500:
			tmp = fileData
			# データ作成
			data = setTappointMe(sidMorg, tmp)
			# 登録
			retSts = registerDatabase(sidMorg, data)
			if errData is not None and len(errData) > 0:
				eFilePath = pDir.joinpath(pConfig['path']['err'], fp.name+'.errData')
				csvFileOpen('write', eFilePath, errData)
				ret = ret + error if ret is not None else error
			else:
				ret = ret + success if ret is not None else success
			del fileData, tmp, data, errData
		else:
			# TODO: 3000件投入して500件ずつ処理を行うと、メモリ4GB搭載で約25～60％の使用量（TOPコマンドで目視確認）
			#       XMLMEのサイズで大分変化すると考えられる
			fileDataN = list(split_list(fileData, 500))
			del fileData
			for cnt in range(len(fileDataN)):
				tmp = fileDataN.pop()
				# データ作成
				data = setTappointMe(sidMorg, tmp)
				# 登録
				retSts = registerDatabase(sidMorg, data)
				if errData is not None and len(errData) > 0:
					eFilePath = pDir.joinpath(pConfig['path']['err'], fp.name+'.errData')
					csvFileOpen('write', eFilePath, errData)
					ret = ret + error if ret is not None else error
				else:
					ret = ret + success if ret is not None else success
			del fileDataN, tmp, data, errData

	except PermissionError as err:
		ret = error
		errFile = pathlib.Path(str(oldFile)+'.PERMERR')
		newfp.rename(errFile)
		newfp = errFile
		plgLog.error('[{sidMorg}] {eMsg}'.format(sidMorg=sidMorg, eMsg=err))
	except Exception as err:
		ret = error
		plgLog.exception(err)
	finally:
		# ファイル移動
		if newfp is not None:
			mvfp = newfp
		else:
			mvfp = fp
		# extFile.endproc(sidMorg, plConfig=pConfig, sts=ret, fp=mvfp)
	return


# トリガーファイルの出力
def outputTriggerFile(sidMorg,):
	pass


# main process
def plg(sidMorg, config, plgName, plgDir):
	if sidMorg is None or config is None or plgName is None or plgDir is None:
		return

	# 1ループ中に保持したいもの
	global meCriterionData, criterionSid, outsourcingInspectionMap, mMeXMLData

	global contractData
	plgLog.info('[{sidMorg}] **** plg start ****'.format(sidMorg=sidMorg))

	global errMsg, pConfig, pDir
	# pConfig = config
	pConfig = config.plg['p021']
	pConfig['plgName'] = plgName
	pDir = plgDir

	# triggerTime = None
	# if 'triggerFile' in pConfig and 'waitTime' in pConfig['triggerFile']:
	# 	triggerTime = time() + pConfig['triggerFile']['waitTime']

	# # プラグイン起動時にWORKファイルの救済を行う
	# workFileCheck(pDir.joinpath(pConfig['path']['in']))

	if examineeMap is None or appointMap is None:
		eMsg = 'error Object: '
		if examineeMap is None: eMsg += 'examineeMap'
		if appointMap is None: eMsg += 'appointMap'
		raise Exception('[{sidMorg}] create config error, {plgName} up faild, msg: {logMsg}'.format(sidMorg=sidMorg, plgName=plgName, logMsg=eMsg))

	# while cmn.flagThreadLoop:
	try:
		startTime = time()
		# fileList = extFile.getFileList(sidMorg=sidMorg, plgName=plgName, plgDir=pDir, plConfig=pConfig)
		# if fileList is not None and len(fileList) > 0:
		# 	# 契約情報の取得
		# 	contractData = t_contract_me_attribute.getT_contract_me_attribute(sidMorg)
		# 	cnt = 0
		# 	startTime = time()
		# 	for fp in fileList:
		# 		cnt += 1
		# 		try:
		# 			if extFile.isFileOpen(fp) == False:
		# 				fileOpen(sidMorg, fp)
		# 		except Exception as err:
		# 			pass

		# 		finally:
		# 			# エラーメッセージをファイルへ出力
		# 			_errMsg = [k for k in errMsg if len(k) > 0]
		# 			if _errMsg is not None and len(_errMsg) > 0:
		# 				eFilePath = pDir.joinpath(pConfig['path']['err'], fp.name+'.errMsg')
		# 				fileCtrl.textWrite(filePath=eFilePath, data=_errMsg, encoding='UTF-8')
		# 				errMsg = []

		fileOpen(sidMorg, config_data['file_path'])
		# 実行時間表示
		# plgLog.info('[{sidMorg}] fileCount:{cnt}, elapsed_time: {eltime:.3f} sec'.format(sidMorg=sidMorg, cnt=cnt, eltime=time() - startTime))
		plgLog.info('[{sidMorg}] elapsed_time: {eltime:.3f} sec'.format(sidMorg=sidMorg, eltime=time() - startTime))
		# # トリガーファイルの出力処理
		# if triggerTime is not None:
		# 	if triggerTime < time():
		# 		outputTriggerFile(sidMorg)
		# 		triggerTime = time() + pConfig['triggerFile']['waitTime']

	except Exception as err:
		# plgLog.error(err, exc_info=True)
		msg2js('予約登録処理でエラーが発生しました。')
		traceLog(err)
	finally:
		# 処理後はクリア
		meCriterionData = {}
		criterionSid = {}
		outsourcingInspectionMap = {}
		mMeXMLData = {}

		plgLog.debug('[CHECK] sidMorg:{}, plgName:{}, plgDir:{}, waitTime:{}'.format(sidMorg, plgName, plgDir, cmn.baseConf['workersDelay']))
		sleep(cmn.baseConf['workersDelay'])

	plgLog.info('[{sidMorg}] plg exit'.format(sidMorg=sidMorg))
	return

# main
def main():

	config = cmn.plgConfigGet()
	plgDir = os.getcwd()
	plgName = '予約インポート'

	plg(sidMorg, config, plgName, plgDir)

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

	log('ImportForAll.py start')
	msg2js('一括インポートを開始します')

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
		
		start_time = time()
		# メイン処理呼び出し
		main()
		# 実行時間表示
		log('[{sidMorg}] 一括インポート処理時間: {eltime:.3f} sec'.format(sidMorg=sidMorg, eltime=time() - start_time))

		msg2js('一括インポートインポートを終了します')

		form_cmn._exit('success')		# 処理成功

	except Exception as err:
		msg2js('一括インポートインポートのメイン処理でエラーが発生しました。err:[{err}]'.format(err=err))
		traceLog(err)
		form_cmn._exit('error')		# エラー
	log('ImportForAll.py end')
	form_cmn._exit('exit')				# 終わり