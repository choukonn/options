#!/usr/bin/python3

# -*- coding: utf-8 -*-
# 文字コードはUTF-8で
# ネストが深いので４タブね。
# vim: ts=4 sts=4 sw=4

# 参考サイト
# https://dev.mysql.com/doc/connector-python/en/connector-python-example-connecting.html


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

# デバッグ用
#from memory_profiler import profile

import form_tools_py.conf as conf
import form_tools_py.common as cmn
import form_tools_py.read_i18n_translation as ri18n
import form_tools_py.getXmlSid as getXmlSid

# signalハンドラの登録(CTRL+Cとkill)
signal.signal(signal.SIGINT, cmn.handler_exit)
signal.signal(signal.SIGTERM, cmn.handler_exit)

# コンフィグ
config_data = conf.config_data
# フィルタ情報
filter_item_tag = {}
filter_item_name = collections.OrderedDict()

# スクリプトのPATH
#script_file = pl.Path(__file__).resolve()
#script_dir = script_file.parents[0]
# TEMPディレクトリのPATH
#tmp_dir = script_dir.joinpath(pl.PurePath('..', '..', '..', 'temp'))
# カレント
#cur_dir = os.getcwd()

# 出力ファイル名
csv_file_name = ""

# DD用ヘッダに出力する識別用文字列
# 1:'DD'固定
dd_header_prefix = 'DD'


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



################################################################################
# FIXME: （仮）やっつけバージョンです。
# 検査項目の料金探索
#@cmn.measure	# デバッグ専用
def search_xml_criterion(xmlMeSid, search_item):

	tmp_list1 = []
	tmp_list2 = []
	tmp_course_price = None		# コース料金
	tmp_option_price = None		# オプション料金の計算用
	total_opt = 0				# オプション合計を格納
	total_amount = 0			# コース＋オプション

	# まずはコースID取得
	course_sid = list(xmlMeSid['ecourse'].keys())[0]		# xmlMeにコース情報が存在するのは1個の前提に取得
	course_sid_criterion = xmlMeSid['ecourse'][course_sid]['sid_criterion']
	# 何故かコースのsid_criterionが変な人がいる場合あり
	if course_sid_criterion == '0' or course_sid_criterion is None:
		log('course sid_criterion unknown : sid={}, sid_criterion={}'.format(course_sid, course_sid_criterion), LOG_WARN)
		return None

	# m_me_attribute
	#### XMLタグの意味
	#f_exam			# 必須／オプション項目 (1 = オプション、2 = 必須)
	#f_intended 	# 受診対象項目 (0 = 対象外、1 = 対象)
	#### ここからコース基準のお話
	#（１）f_intended=0 && f_exam = 1 # オプションかつ、受診対象外
	#（２）f_intended=0 && f_exam = 2 # 必須。かつ、受診対象外
	#（３）f_intended=1 && f_exam = 1 # オプション、かつ、受診対象
	#（４）f_intended=1 && f_exam = 2 # 必須。かつ。受診対象
	#### ここまで
	# オプション項目かつ、それを受診する場合に項目料金をCSVに出力する。なので、受診対象／対象外なのかf_examをチェックする必要がある
	# (必須項目はコース料金に含まれるので出力しない。また受診しない場合でも減額は行わない)

	# f_exam(必須／オプション)のチェック
	# 補足：m_me_attributeは更新分のみが格納されている。このXMLの中にいない検査項目は必須扱いとなる
	attrib_data = getXmlSid.getXmlAttribute(course_sid, course_sid_criterion)['consultations']
	if attrib_data is None:	# 見つからなかったら終わり
		log('m_me_attribute not found : sid_me={} and sid_criterion={}'.format(course_sid, course_sid_criterion), LOG_WARN)
		return None
	me_attrib_item = {k:attrib_data[k]['f_exam'] for k in attrib_data if 'f_exam' in attrib_data[k]}

	# コース料金取得
	criterion_data = getXmlSid.getXmlCriterion(course_sid_criterion, s_exam='1001')['criterion']
	if criterion_data is None:
		return None
	course_data = criterion_data[course_sid_criterion]
	tmp_course_price = course_data['price'] if 'price' in course_data else None
	tmp_list1.append(search_item['course'])							# CSVに出力するコース料金用ヘッダ名
	tmp_list2.append(tmp_course_price)								# コース料金

	# パック情報を全て取得
	# パック名はexamlistのsidで管理されないので、名前は画面で登録したものを取得する
	packPrice = {}
	packItemList = {}
	if 'epack' in course_data:
		for packItem in course_data['epack']:
			packData = getXmlSid.getXmlCriterion(course_data['epack'][packItem]['sid_criterion'], s_exam='1002')['criterion']
			for item in packData:
				priceVal = None
				if 'price' in packData[item]:
					priceVal = packData[item]['price']
				packPrice.update({item: {'name': packData[item]['name'], 'title': packData[item]['title'], 'abbr': packData[item]['abbr'], 'price': priceVal}})
				packItemList[item] = list(packData[item]['eitem'].keys())

	# 受診対象項目のlistを作成
	f_intended_data = {k : xmlMeSid['eitems'][k].get('f_intended') for k in search_item if k in xmlMeSid['eitems']}

	# パックに含まれるsidを除外
	pesid_xor_pack = []
	packSidActive = []
	if len(packItemList) > 0:
		for psid in packItemList:
			maeLen = len(packItemList[psid])
			f_intended_and_pack = list(set(packItemList[psid]) & set(list(f_intended_data.keys())))		# andで一致するsidを抽出
			atoLen = len(f_intended_and_pack)
			if maeLen == atoLen:
				# 一致したらパックを有効とみなして除外リストを作成
				pesid_xor_pack.append(f_intended_and_pack)
				packSidActive.append(psid)							# 有効なパックのsidを残す
		pesid_xor_pack = [k for k in pesid_xor_pack for k in pesid_xor_pack[0]]
		# パックに含まれる項目SIDを除外したリスト
		#f_intended_xor_pack = [i for i in pesid_xor_pack + list(f_intended_data.keys()) if i not in pesid_xor_pack or i not in list(f_intended_data.keys())]

	# 受診対象の検査項目が、search_itemとme_attrib_itemに含まれる、かつ、「f_exam=1（オプション）」のみを抽出
	# search_item(m_outsourceで定義されているリスト)に含まれているかチェックは、csvのヘッダ出力する関係で無条件抽出が不可のために以下リストを作成する
	f_intended_data_check = [k for k in f_intended_data if k in search_item and k in me_attrib_item and me_attrib_item[k] == '1']

	sql.open()	# ループで回すから接続したまま、終了時に閉じる
	for itemSid in f_intended_data_check:										# 受診対象項目検索
		if len(pesid_xor_pack) > 0 and item in pesid_xor_pack: continue		# パックに含まれていたらスキップ
		item_f_intended = f_intended_data[itemSid]							# 受診フラグ
		tmp_option_price = None												# 常にクリアしておく
		if item_f_intended == '1':
			tmp_list1.append(search_item[itemSid])							# CSVヘッダ名
			sid_criterion = xmlMeSid['eitems'][itemSid]['sid_criterion']	# 検索用
			query = 'SELECT xml_criterion FROM m_criterion WHERE sid_morg = ? AND sid = ?;'
			param = [config_data['sid_morg'], sid_criterion]
			row = sql.once2noexit(query, param)
			#row = cmn.get_m_criterion(sid_criterion)
			if row is not None:
				xml = row[0]['xml_criterion']
				xml_criterion = ET.fromstring(xml)
				# TODO: 項目料金が設定されていないものは強制0円
				tmp_option_price = xml_criterion.findtext('criterion/price')
				if tmp_option_price is None and 'f_force_price_0en' in conf.convert_option and conf.convert_option['f_force_price_0en'] != '0':
					tmp_option_price = 0

			else:
				log('sid={} of m_criterion not found'.format(sid_criterion), LOG_WARN)
			if tmp_option_price is not None:
				total_opt += int(tmp_option_price)			# オプション合計計算
			tmp_list2.append(tmp_option_price)				# 項目別オプション料金
	sql.close()	# セッション終了
	# コース料金＋オプションがNoneではない
	if tmp_course_price is not None and total_opt is not None:
		total_amount = int(tmp_course_price) + int(total_opt)
	# コース料金None、オプションがNoneではない
	elif tmp_course_price is None and total_opt is not None:
		total_amount = int(total_opt)
	# オプションがNoneなのでコースだけ入れる。その際コース料金がNoneであるということはシステムにコース料金が未登録ということになるので気にしない
	else:
		total_amount = tmp_course_price
	# パック料金を加算
	tmp_packItem = []
	if total_amount is not None and type(total_amount) == int and len(packSidActive) > 0:
		# TODO: 呼び出し元でパック名を抽出するのに使う。またパック名は内部名称「name」を採用する
		tmp_packItem = [packPrice[k]['name'] for k in packPrice]
		for psid in packSidActive:
			priceVal = packPrice[psid]['price']
			priceName = packPrice[psid]['name']
			tmp_list1.append(priceName)
			tmp_list2.append(priceVal)
			total_amount += int(priceVal) if priceVal is not None else 0

	tmp_list1.append(search_item['amount'])
	tmp_list2.append(total_amount)
	tmp_list1.append(search_item['options'])
	tmp_list2.append(total_opt)

	item_price = dict(zip(tmp_list1,tmp_list2))
	if len(tmp_packItem) > 0: item_price.update({'packName':tmp_packItem})

	return item_price

# 支払フラグ検索
def search_xml_appoint(xml_tree, search_target, search_item):
	tmp_list1 = []
	tmp_list2 = []

	# FIXME: 汚いからいつか直したい
	base = xml_tree.find(search_target['tree'])
	if base is not None and 'items' not in search_target:
		return None
	base_len = len(base)
	for i in range(base_len):
		if len(base[i]) > 0:
			for ii in range(len(base[i])):
				if len(base[i][ii]) > 0:
					for iii in range(len(base[i][ii])):
						if base[i][ii][iii].tag == 'f_payment':
							tmp_list1.append(search_item['status'])						# TODO: 支払フラグピンポイントで検索しているのでべた書き。他にもあれば適宜修正
							tmp_list2.append(base[i][ii][iii].text)
						elif base[i][ii][iii].tag == 'payment_info':
							if 'method_of_payment' in search_item:
								tmp_list1.append(search_item['method_of_payment'])		# TODO: 支払方法
								tmp_list2.append(base[i][ii][iii].text)
						elif base[i][ii][iii].tag == 'discount':
							if 'discount' in search_item:
								tmp_list1.append(search_item['discount'])				# TODO: 割引金額
								tmp_list2.append(base[i][ii][iii].text)
						else:
							tmp_list1.append(base[i][ii][iii].tag)
							tmp_list2.append(base[i][ii][iii].text)
				else:
					if base[i][ii].tag == 'exam_type':
						if 'payType' in search_item:
							tmp_list1.append(search_item['payType'])					# TODO: 支払う人
							tmp_list2.append(base[i][ii].text)

	item_payment = dict(zip(tmp_list1,tmp_list2))

	return item_payment

# 過去歴
#@cmn.measure	# デバッグ専用
def get_past_history_data(sid_examinee, appoint_day, past_history_item_list, sid_me=None):
	rdata = {}
	tmp_list = []
	# 過去歴取得のクエリ
	sid_morg = str(config_data['sid_morg']) if 'sid_morg' in config_data else None
	base_day = str(appoint_day)
	history_limit_num = past_history_item_list['convert_option']['f_past_history']
	query = '\
		SELECT \
		t_apo_me.*, \
		t_apo.status, \
		t_apo.dt_appoint, \
		f_make_n_appoint(t_apo.sid_morg,t_apo.sid,t_apo.status) AS n_appoint, \
		t_apo.s_reappoint, \
		t_apo.sid_examinee, \
		ExtractValue(t_apo.xml_examinee, "/root/examinee/id") AS exam_id, \
		t_apo.xml_examinee, \
		t_apo.xml_xorg, \
		ExtractValue(m_cri.xml_criterion, "/root/criterion/name") AS name_me, \
		ExtractValue(m_cri.xml_criterion, "/root/criterion/title") AS title_me, \
		ExtractValue(m_cri.xml_criterion, "/root/criterion/abbr") AS abbr_me \
		FROM \
			t_appoint_me t_apo_me \
			INNER JOIN t_appoint t_apo ON t_apo_me.sid_morg = t_apo.sid_morg AND t_apo_me.sid_appoint = t_apo.sid \
			INNER JOIN m_criterion m_cri ON t_apo_me.sid_morg = m_cri.sid_morg AND t_apo_me.sid_me = m_cri.sid_exam AND m_cri.s_exam = 1001 AND m_cri.sid = ExtractValue(t_apo_me.xml_me, "/root/ecourse/sid_criterion") \
		WHERE \
			t_apo.sid_morg = ? \
			AND t_apo.sid_examinee = ? \
			AND t_apo.status = 3 \
			AND t_apo.dt_appoint < ? \
			AND \
			CASE WHEN ? IS NOT NULL THEN t_apo_me.sid_me = ? \
			ELSE True \
			END \
		ORDER BY t_apo.dt_appoint DESC LIMIT ?;'
	param = (sid_morg, sid_examinee, base_day, sid_me, sid_me, history_limit_num)
	#dbg_log('info sql: {}, param: {}'.format(query, param))
	rows = sql.once(query, param)
	if rows is None:
		return {}
	row_num = len(rows)
	for i in range(row_num):
		tmp_history = {}
		course_sid = str(rows[i]['sid_me'])
		# 受診者情報
		examData = getXmlSid.analyzeXmlExaminee(cmn.getRow2Xml(rows[i]['xml_examinee']))['examinee'][sid_examinee]
		result_examinee = cmn.get_examinee_data(examData, past_history_item_list['examinee_item'])
		tmp_history.update(result_examinee)
		# 受診日(予約日)
		result_appoint = cmn.get_appo_info(rows[i], past_history_item_list['appoint_item'])
		tmp_history.update(result_appoint)
		# 検査結果
		xmlobj = cmn.getRow2Xml(rows[i]['xml_me'])
		xmlMeSid = getXmlSid.analyzeXmlMeIndex(xmlobj, resultConv=True)
		result_inspection = cmn.get_inspection_data(xmlMeSid, past_history_item_list['inspection_item'])
		tmp_history.update(result_inspection)
		# 問診
		if 'interview_item' in past_history_item_list:
			result_interview = cmn.get_inspection_data(xmlMeSid, past_history_item_list['interview_item'])
			tmp_history.update(result_interview)

		# 総合判定／所見
		result_general = {past_history_item_list['general_item'][k] : xmlMeSid['ecourse'][course_sid]['result']['opinion']['1'][k] for k in xmlMeSid['ecourse'][course_sid]['result']['opinion']['1'] if k in past_history_item_list['general_item']}
		tmp_history.update(result_general)
		# グループランク／所見
		result_group_rank = cmn.get_groupRank_data(xmlMeSid, past_history_item_list['groupRank_item'])
		if result_group_rank is not None:
			if 'rank' in result_group_rank: tmp_history.update(result_group_rank['rank'])
			if 'finding' in result_group_rank: tmp_history.update(result_group_rank['finding'])
			if 'summary' in result_group_rank: tmp_history.update(result_group_rank['summary'])
		# 団体
		if rows[i]['xml_xorg'] is not None:
			#xml_xorg = ET.fromstring(rows[i]['xml_xorg'])
			xmlobj = cmn.getRow2Xml(rows[i]['xml_xorg'])
			#result_org, result_org_sid = get_org_data(xmlobj, past_history_item_list['org_item'])
			xmlOrgSid = getXmlSid.analyzeXmlOrgIndex(xmlobj)
			result_org = cmn.get_org_data(xmlOrgSid)
			if 'org_sid' in result_org: del result_org['org_sid']	# 不要なので削除
			#result_org = {past_history_item_list['org_item'][k] : xmlOrgSid['orgs'][k]['name'].get('value') for k in past_history_item_list['org_item'] if k in xmlOrgSid['orgs']}

			tmp_history.update(result_org)

		tmp_list.append({'A'+str(i+1): tmp_history})

	#key_list = []
	#val_list = []
	#for i in range(len(tmp_list)):
	#	for item in tmp_list[i][list(tmp_list[i].keys())[0]].keys():
	#		key = list(tmp_list[i].keys())[0] + '_' + item
	#		val = tmp_list[i][list(tmp_list[i].keys())[0]][item]
	#		key_list.append(key)
	#		val_list.append(val)

	#return dict(zip(key_list, val_list))
	rdata = {list(tmp_list[i].keys())[0] + '_' + item:tmp_list[i][list(tmp_list[i].keys())[0]][item] for i in range(len(tmp_list)) for item in tmp_list[i][list(tmp_list[i].keys())[0]].keys()}

	return rdata


# 治療中項目
def get_medi_cure_data(xmlMeSid, itemList):
	if len(xmlMeSid) < 1: return None
	data = {itemList['title']: ','.join([itemList[k] for k in itemList if k in xmlMeSid['elements'] and 'value' in xmlMeSid['elements'][k]['result'] and xmlMeSid['elements'][k]['result']['value'] is not None])}
	return data

# 受診対象検査項目
def get_acceptance_data(xmlMeSid, itemList):
	if len(xmlMeSid) < 1: return None
	data = {itemList[k] : xmlMeSid['eitems'][k].get('f_intended') for k in itemList if k in xmlMeSid['eitems']}
	return data

# 問診項目
def get_interview_data(xmlMeSid, itemList):
	if len(xmlMeSid) < 1: return None
	data = {itemList[k] : xmlMeSid['elements'][k]['result'].get('value') for k in itemList if k in xmlMeSid['elements']}
	return data

# 検査項目料金
def get_inspection_price_data(xmlMeSid, itemList):
	if len(xmlMeSid) < 1: return None
	data = search_xml_criterion(xmlMeSid, itemList)
	return data

# 支払フラグ
def get_payment_data(xml_appoint, search_item):
	search_target = {'tree':'appoint', 'items': {'f_menstruation':'f_menstruation', 'f_aftermeal':'f_aftermeal', 'payFlag':'f_payment', 'payInfo':'payment_info', 'exam_type':'exam_type'} }
	payment_dict = search_xml_appoint(xml_appoint, search_target, search_item)
	return payment_dict

# 簡易報告書
def get_simple_report_data(xmlMeSid, itemList):
	if len(xmlMeSid) < 1: return None
	data = {itemList[k] : xmlMeSid['elements'][k]['result'].get('value') for k in itemList if k in xmlMeSid['elements']}
	return data


# ----------------------------------------
# データ作成
#@profile	# デバッグ専用
def create_renpyou(xml_outsource):
	global config_data
	global csv_file_name
	global filter_item_tag		# フィルタ情報もグローバル
	global filter_item_name		# フィルタ情報もグローバル

	tmp_file = None
	sid = None
	sid_examinee = None
	err_sid_list = []

	csv_data = []
	#csv_header_dict = {'LineNo':1}		# 固定
	csv_header = ['LineNo', 'Number']	# LineNoはマクロ側で使用するため、Numberに受診者の数をインクリメントで入れる
	total_cnt = 1						# データ件数のカウント用

	# 出力ファイル名の部品
	out_file_prefix = config_data['out_file_prefix']
	out_file_suffix = config_data['out_file_suffix']

	# 統計（日別）の結果格納で使用する
	result_statistics_day = {}
	# パック料金を出力する際のヘッダ名で使用する。
	packName = ''

	try:

		# MySQL
		sql.open()

		if xml_outsource is not None or xml_outsource == '':
			# CSV形式
			csv_option = cmn.outsource_dict('condition')
			# 変換オプション、最低限の初期値(keyが存在しなければ入れる)
			if 'f_birthday2age' not in conf.convert_option: conf.convert_option['f_birthday2age'] = '0'
			if 'f_kana_sort' not in conf.convert_option: conf.convert_option['f_kana_sort'] = '0'
			if 'f_translation' not in conf.convert_option: conf.convert_option['f_translation'] = '0'
			if 'f_past_history' not in conf.convert_option: conf.convert_option['f_past_history'] = '0'
			# 過去歴(データはずーっと下のほうで作成するので、枠だけ用意)
			result_past_history_item = []
			# 受診者情報
			examinee_item = cmn.outsource_dict('columns/examinee_item')
			# 予約情報
			appoint_item = cmn.outsource_dict('columns/appoint_item')
			# 検査項目情報
			inspection_item = cmn.outsource_dict('columns/inspection_item')
			if inspection_item is not None and 'i18n' in inspection_item: conf.i18n_item.update(inspection_item['i18n']); del inspection_item['i18n']		# 翻訳リストを配列から切り出し、別変数へ格納
			# 治療中項目
			medi_cure_item = cmn.outsource_dict('columns/medi_cure_item')
			# 総合判定／所見
			general_item = cmn.outsource_dict('columns/general_item')
			# グループ判定
			groupRank_item = cmn.outsource_dict('columns/groupRank_item')
			# 団体情報
			org_item = cmn.outsource_dict('columns/org_item')
			# 受診対象項目
			acceptance_item = cmn.outsource_dict('columns/acceptance_item')
			if acceptance_item is not None and 'i18n' in acceptance_item: conf.i18n_item.update(acceptance_item['i18n']); del acceptance_item['i18n']		# 翻訳リストを配列から切り出し、別変数へ格納
			# 問診
			interview_item = cmn.outsource_dict('columns/interview_item')
			if interview_item is not None and 'i18n' in interview_item: conf.i18n_item.update(interview_item['i18n']); del interview_item['i18n']			# 翻訳リストを配列から切り出し、別変数へ格納
			# 検査項目料金
			acceptance_rate_item = cmn.outsource_dict('columns/acceptance_item')	# 受診対象項目の料金を探す
			price_item = cmn.outsource_dict('columns/price_item')					# コース料金その他用
			#price_itemName = list(price_item.values())
			if acceptance_rate_item is not None and price_item is not None: price_item.update(acceptance_rate_item)			# 項目料金＋コース料金の検索用データを結合
			# 簡易報告書
			simple_report_item = cmn.outsource_dict('columns/simple_report_item')
			# 会計（統計）情報
			#statistics_item = cmn.outsource_dict(xml_outsource, 'outsource/columns/statistics_item', None)

			# ヘッダフラグがあれば初期値を上書きする
			header_status = cmn.outsource_dict('condition/header/{}{}'.format(conf.form_num_prefix, config_data['s_print']))
			if header_status is not None and 'f_use' in header_status and header_status['f_use'] is not None:
				config_data['dd_header_flag'] = header_status['f_use']

			# Excelマクロ向け用CSV向けの設定
			xls_break_status = cmn.outsource_dict('condition/excel_break/{}{}'.format(conf.form_num_prefix, config_data['s_print']), 'xls_csv_flag')
			config_data['xls_break_flag'] = xls_break_status['xls_break_use'] if xls_break_status is not None and 'xls_break_use' in xls_break_status else '0'
			if config_data['xls_break_flag'] == '1':
				config_data['xls_break_line'] = xls_break_status['xls_break_line'] if 'xls_break_line' in xls_break_status else '0'
				config_data['xls_break_str'] = xls_break_status['xls_break_str'] if 'xls_break_str' in xls_break_status else ''

			# ソートで使用するためにコンフィグ内のデータを変更しておく
			if sort_code['date'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['date']]['key'] = appoint_item['dt_appoint']						# 受信日
			if sort_code['course'] in config_data['sort_condition']:
				# コース名の優先度（name > title > abbr）
				courseName = None
				if 'name_me' in appoint_item: courseName = appoint_item['name_me']
				elif 'title_me' in appoint_item: courseName = appoint_item['title_me']
				elif 'abbr_me' in appoint_item: courseName = appoint_item['abbr_me']
				if courseName is not None: config_data['sort_condition'][sort_code['course']]['key'] = courseName
			if sort_code['number'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['number']]['key'] = appoint_item['appoint_number']				# 受診番号
			if sort_code['examinee'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['examinee']]['key'] = examinee_item['name']					# 健診者氏名
			if sort_code['org_agreement'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['org_agreement']]['key'] = org_item['insurance_name']	# 契約団体
			if sort_code['org_affiliation'] in config_data['sort_condition']: config_data['sort_condition'][sort_code['org_affiliation']]['key'] = org_item['org_name']		# 所属団体

			#### フィルタ情報 ####
			# 色々かき集めた情報を、フィルタに登録したもの以外出力しないように抑制する
			# また、フィルタに存在するが、かき集めた情報内に存在しないものはダミーデータとしてCSVにヘッダのみ出力を行う
			# フィルタ設定がない帳票の場合、Noneになる
			filter_item_tag, filter_item_name = cmn.outsource_filter_dict(xml_outsource, 'outsource/filters', config_data['s_print'])

		else:
			cmn._exit('xml_error', '[m_outsource] xml get failed')		# m_outsourceのXML取得失敗

		del xml_outsource

		# 言語ファイルの読み込みおぷそん
		#if conf.convert_option['f_translation'] == '1' and 'translation_lang' in config_data:
		#	conf.i18n_list = ri18n.read_file(config_data['translation_lang']+'.js')
		# DBの言語マスタからログインユーザの言語で引っ張る
		ri18n.getDBlist(user=True)

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

		# 組み立て
		# TODO: skipする場合は必ずSQLのカーソルを進めること
		#       row = cur.fetchone() <- これを入れる
		for row in rows:
			# ループ開始時にクリアしておかないと処理途中でエラー抜けした場合、ログに無関係なIDと受信日が表示される
			conf.examInfo['appoint_day'] = None
			conf.examInfo['id'] = None
			conf.examInfo['locale'] = None

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
			#dt_appoint_time = dt_appoint_base[1].split(':')				# 予約時刻、秒は捨て
			#appoint_time = None
			#if int(dt_appoint_time[0]+dt_appoint_time[1]) > 0:			# 00:00は予約時間なし扱い
			#	appoint_time = dt_appoint_time[0] + ':' + dt_appoint_time[1]

			conf.examInfo['appoint_day'] = dt_appoint_day
			conf.examInfo['id'] = examData[sid_examinee]['id']
			conf.examInfo['locale'] = examData[sid_examinee]['locale']
			# DBの言語マスタから受診者の言語で引っ張る
			ri18n.getDBlist(exam=True)

			# 絞り込みその２：婦人科問診の場合は、女性のみ出力とする
			if config_data['s_print'] == form_code['interview_gynecology']:
				if examData[sid_examinee]['sex'] is not None and examData[sid_examinee]['sex'] != "2":	# 1:男性、2:女性
					continue
			# 絞り込み２：終わり

			result_examinee[sid] = {}
			result_examinee[sid] = cmn.get_examinee_data(examData[sid_examinee], examinee_item)

			#del key_list, key, tmp_list1, tmp_list2, item, xml_examinee

			# コース名、予約日(受診日)
			result_appoint = {}
			result_appoint[sid] = {}
			result_appoint[sid] = cmn.get_appo_info(row, appoint_item)

			# XMLツリー
			sid_appoint = str(row['sid'])
			#t_appo_me = sql.once('SELECT * FROM t_appoint_me where sid_morg = '+ config_data['sid_morg'] +' and sid_appoint = ' + sid_appoint + ';')
			t_appo_me = cmn.get_t_appoint_me(sid_appoint)
			if t_appo_me is None: continue

			try:	# TODO: xml_meに特殊記号(<>&など)が直接挿入されてXML解析失敗するパターンが存在する。その場合はスキップを行う
				xml_me = cmn.getRow2Xml(t_appo_me[0]['xml_me'])
				xml_me_elementsLen = len([k for k in xml_me.find('elements')])
				xml_me_eitemsLen = len([k for k in xml_me.find('eitems')])
				xml_me_egroupsLen = len([k for k in xml_me.find('egroups')])
				if xml_me_elementsLen < 1 or xml_me_eitemsLen < 1 or xml_me_egroupsLen < 1:
					log('xmlme format error (eitemsLen:{}, eitemsLen:{}, egroupsLen:{}]'.format(xml_me_elementsLen, xml_me_eitemsLen, xml_me_egroupsLen), LOG_ERR)
					continue

			except Exception as err:
				log('xmlme err:{}'.format(err), LOG_ERR)
				err_sid_list.append({sid: {'sid_examinee': sid_examinee, 'msg': 'xml_me:'+str(err)}})
				continue
			#t_appo = sql.once('SELECT * FROM t_appoint where sid_morg = '+ config_data['sid_morg'] +' and sid = ' + sid_appoint + ';')
			t_appo = cmn.get_t_appoint(sid_appoint)
			if t_appo is None: continue
			xml_xorg = cmn.getRow2Xml(t_appo[0]['xml_xorg'])

			# 団体
			result_org = {}
			result_org[sid] = {}
			result_org_sid = None
			if xml_xorg is None and cond_org is not None: continue	# 団体紐づけなし、かつ、団体絞り込みありの場合、スキップ

			if xml_xorg is not None:
				#result_org[sid], result_org_sid = get_org_data(xml_xorg, org_item)
				xmlOrgSid = getXmlSid.analyzeXmlOrgIndex(xml_xorg)
				result_org[sid] = cmn.get_org_data(xmlOrgSid)
				result_org_sid = result_org[sid]['org_sid'] if 'org_sid' in result_org[sid] else None
				if 'org_sid' in result_org[sid]: del result_org[sid]['org_sid']		# org_sidは団体絞り込みでしか使用しないため、ここで削除する
				if (cmn.check_abst_sts(result_org_sid, cond_org) == False):			# 団体情報が読めるのがこのタイミングなので、ここで絞り込み
					log(' *** reject org', LOG_DBG)
					continue

			# xmlmeを参照したい人向けにXMLを解析してごにょごにょしたものを返す
			xmlmeConvList = [
				form_code['inspection'],
				form_code['interview'],
				form_code['interview_2nd'],
				form_code['interview_gynecology'],
				form_code['denri_kojin'],
				form_code['tokkabutu_kojin'],
				form_code['yuuki_kojin'],
				]
			# 参照する必要はあるけど、結果をごにょる必要がないのはここ
			xmlmeNoConvList = [
				form_code['reservation'],
				form_code['escort_sheet'],
				form_code['price'],
				form_code['invoice'],
				form_code['Receipt'],
				form_code['statistics_individual'],
				form_code['statistics_daily'],
				form_code['statistics_optionList'],
			]
			xmlMeSid = None
			xmlMeConvFlag = True if config_data['s_print'] in xmlmeConvList else False
			if config_data['s_print'] in xmlmeConvList or config_data['s_print'] in xmlmeNoConvList:
				xmlMeSid = getXmlSid.analyzeXmlMeIndex(xml_me, resultConv=xmlMeConvFlag) if xml_me is not None else None
			# 検査項目（標準／オプション）の受診状態
			if xmlMeSid is not None:
				conf.inspStdOptData = cmn.get_inspection_stdOpt_data(xmlMeSid)

			# 検査項目
			result_inspection = {}
			result_general = {}
			result_medi_cure = {}
			result_group_rank = {}
			inspection_sprint_list = [
				form_code['inspection'],
				form_code['interview_2nd'],
				form_code['denri_kojin'],
				form_code['tokkabutu_kojin'],
				form_code['yuuki_kojin'],
				]
			if config_data['s_print'] in inspection_sprint_list:		# 検査結果
				result_inspection[sid] = {}
				result_general[sid] = {}
				result_medi_cure[sid] = {}
				result_group_rank[sid] = {}
				if xmlMeSid is not None:
					result_inspection[sid] = cmn.get_inspection_data(xmlMeSid, inspection_item)
					# データ取得失敗時に空になる
					if len(result_inspection[sid]) == 0:
						log('result_inspection data is None', LOG_ERR)
					# 治療中の取得
					result_medi_cure[sid] = get_medi_cure_data(xmlMeSid, medi_cure_item)
					# 総合所見／判定の取得
					if int(appo_sts) > 1:	# 受付ステータスが判定済み以上を対象(予約／受付の場合は対象外)
						result_general[sid] = cmn.get_general_data(xmlMeSid, general_item, course_sid)
					# グループ判定／所見
					if int(appo_sts) > 0:	# 予約以上
						result_group_rank[sid] = cmn.get_groupRank_data(xmlMeSid, groupRank_item)

			# 過去歴の取得
			result_past_history = {}
			if config_data['s_print'] in inspection_sprint_list:		# 検査結果
				past_history = conf.convert_option['f_past_history']		# 過去歴取得フラグ兼何回分取得するかの数字
				if past_history is not None and int(past_history) > 0:
					past_history_item_list = {
						'convert_option':conf.convert_option, 'examinee_item':examinee_item, 'appoint_item':appoint_item, 'org_item':org_item,
						'inspection_item':inspection_item, 'medi_cure_item':medi_cure_item, 'general_item':general_item,
						'acceptance_item':acceptance_item, 'interview_item':interview_item, 'groupRank_item':groupRank_item,
					}

					tokusyu_list = [  			#特殊健診リスト
						form_code['denri_kojin'],
						form_code['tokkabutu_kojin'],
						form_code['yuuki_kojin'],
						]

					sid_me = None
					if config_data['s_print'] in tokusyu_list:			#コースIDがあるかチェック　あったらsid_meに入れる
						if '201003' in config_data['abst_condition']:	#特殊健診以外のコースを取得しないように
							sid_me = config_data['abst_condition']['201003']

					result_past_history[sid] = get_past_history_data(sid_examinee, dt_appoint_day, past_history_item_list, sid_me)
					# CSV出力用ヘッダになる元データを作成
					if len(result_past_history[sid]) > 0 and len(result_past_history_item) < len(result_past_history[sid]):
						result_past_history_item = list(result_past_history[sid].keys())

					# データ取得失敗とか、取得すべき過去歴がない場合
					if len(result_past_history[sid]) <= 0:
						log('sid={}, sid_examinee={}: result_past_history data is nothing'.format(sid, sid_examinee), LOG_INFO)

			# 受診対象検査項目
			result_acceptance = {}
			acceptance_sprint_list = [form_code['reservation'], form_code['escort_sheet']]
			if config_data['s_print'] in acceptance_sprint_list:
				result_acceptance[sid] = {}
				if xmlMeSid is not None:
					result_acceptance[sid] = get_acceptance_data(xmlMeSid, acceptance_item)

			# 問診項目
			result_interview = {}
			interview_sprint_list = [form_code['interview'], form_code['interview_2nd'], form_code['interview_gynecology']]
			if config_data['s_print'] in interview_sprint_list:
				result_interview[sid] = {}
				if xmlMeSid is not None:
					result_interview[sid] = get_interview_data(xmlMeSid, interview_item)

			# 検査項目料金(仮)
			result_inspection_rate = {}
			inspection_rate_sprint_list = [form_code['price'], form_code['invoice'], form_code['Receipt'], form_code['statistics_individual'], form_code['statistics_daily']]
			if config_data['s_print'] in inspection_rate_sprint_list:
				result_inspection_rate[sid] = {}
				if xmlMeSid is not None:
					# 支払フラグと支払方法等(xml_appoint)を取得する
					xml_appoint = ET.fromstring(t_appo[0]['xml_appoint']) if t_appo[0]['xml_appoint'] is not None else None
					if xml_appoint is not None and xml_appoint.find('appoint/payments') is not None:
						payment_dict = get_payment_data(xml_appoint, price_item)
						price_dict = get_inspection_price_data(xmlMeSid, price_item)
						# xml_meからコース情報（sid_criterion）が取得できなかった場合、料金情報が取得できないためNoneが返る、よってスキップする
						if price_dict is None:
							#row = sql.ret2dict(cur, cur.fetchone())
							continue
						if 'packName' in price_dict:
							packName += ',' + ','.join(list(price_dict['packName']))	# ヘッダ名でしか使用しない。文字列で結合していく
							del price_dict['packName']
						payment_dict.update(price_dict)
						result_inspection_rate[sid] = payment_dict
					else:
						# xml_appoint内から必要な情報の取得に失敗
						log('payments tag not found in xml_appoint', LOG_WARN)
						payment_dict = None
						price_dict = None

			# 会計（統計）情報
			result_statistics = {}
			statistics_rate_sprint_list = [form_code['statistics_individual'], form_code['statistics_daily']]
			if config_data['s_print'] in statistics_rate_sprint_list:
				result_statistics[sid] = {}
				if dt_appoint_day not in result_statistics_day: result_statistics_day[dt_appoint_day] = {}	# 日別のデータ格納変数、該当日がなければ初期化
				total_amount = 0
				if price_dict is not None and price_item['amount'] in price_dict:	# amountにはコース＋オプションが入っている
					total_amount = int(price_dict[price_item['amount']])

				# FIXME: ミャンマー専用処理としてべた書き作成したもの。よそで使いまわす場合は修正いれる必要ある
				# 統計の内容は各機関で変わると思う。なので、増えるようならモジュールにして別途処理させるほうがいいな？
				# 日別データ格納用
				if 'cash' not in result_statistics_day[dt_appoint_day]: result_statistics_day[dt_appoint_day]['cash'] = 0
				if 'card' not in result_statistics_day[dt_appoint_day]: result_statistics_day[dt_appoint_day]['card'] = 0
				if 'company' not in result_statistics_day[dt_appoint_day]: result_statistics_day[dt_appoint_day]['company'] = 0
				if price_item['amount'] not in result_statistics_day[dt_appoint_day]: result_statistics_day[dt_appoint_day][price_item['amount']] = 0	# 合計(TODO: price_itemにいる名前を引かないと他に影響あり・・・)
				if 'unpaid' not in result_statistics_day[dt_appoint_day]: result_statistics_day[dt_appoint_day]['unpaid'] = 0				# 未払い
				if 'grandTotal' not in result_statistics_day[dt_appoint_day]: result_statistics_day[dt_appoint_day]['grandTotal'] = 0		# 全体の合計

				payment_type = payment_dict[price_item['method_of_payment']] if payment_dict is not None and price_item['method_of_payment'] in payment_dict and payment_dict[price_item['method_of_payment']] else None
				payment_flag = payment_dict[price_item['status']] if payment_dict is not None and payment_dict[price_item['status']] else None	# 未払いフラグ
				# 個人／団体（会社）の区別＋出力用文字列の入れ替え
				if result_org[sid] is not None:
					if org_item['org_name'] in result_org[sid] and result_org[sid][org_item['org_name']] is not None:
						# あれば会社
						result_org[sid][org_item['org_name']] = 'Corporation'
					else:
						# 団体名が無ければ個人
						result_org[sid][org_item['org_name']] = 'Individual'
				# 支払情報の振り分け
				if payment_type is not None:
					# 橙には支払いを行った料金情報は入力されないので、コース＋オプションの料金を設定する
					if payment_flag == '1':
						if payment_type == '0':
							pass
						elif payment_type == '1':	# 現金
							result_statistics[sid]['cash'] = total_amount
							result_statistics_day[dt_appoint_day]['cash'] = int(result_statistics_day[dt_appoint_day]['cash']) + total_amount
						elif payment_type == '2':	# カード
							result_statistics[sid]['card'] = total_amount
							result_statistics_day[dt_appoint_day]['card'] = int(result_statistics_day[dt_appoint_day]['card']) + total_amount
						elif payment_type == '3':	# 会社
							result_statistics[sid]['company'] = total_amount
							result_statistics_day[dt_appoint_day]['company'] = int(result_statistics_day[dt_appoint_day]['company']) + total_amount
					else:
						# 支払済みフラグが未チェックの場合はここに入れる
						result_statistics[sid]['unpaid'] = total_amount
						result_statistics_day[dt_appoint_day]['unpaid'] = int(result_statistics_day[dt_appoint_day]['unpaid']) + total_amount

				# TODO: コース＋オプションの合計を格納する
				pay_cash = result_statistics[sid]['cash'] if 'cash' in result_statistics[sid] and result_statistics[sid]['cash'] is not None else 0
				pay_card = result_statistics[sid]['card'] if 'card' in result_statistics[sid] and result_statistics[sid]['card'] is not None else 0
				pay_company = result_statistics[sid]['company'] if 'company' in result_statistics[sid] and result_statistics[sid]['company'] is not None else 0

				total_fee = pay_cash + pay_card + pay_company
				result_inspection_rate[sid][price_item['amount']] = total_fee
				result_statistics_day[dt_appoint_day][price_item['amount']] = int(result_statistics_day[dt_appoint_day][price_item['amount']]) + total_fee

				# 全体のトータル
				result_statistics[sid]['grandTotal'] = total_amount
				result_statistics_day[dt_appoint_day]['grandTotal'] = int(result_statistics_day[dt_appoint_day]['grandTotal']) + total_amount

			# 簡易報告書
			# TODO: 健康診断を実施した医師名は基準に含まれるため、xmlMeを見る必要がある
			result_simple_report = {}
			if config_data['s_print'] == form_code['simple_report']:
				result_simple_report[sid] = {}
				if xmlMeSid is not None:
					result_simple_report[sid] = get_simple_report_data(xmlMeSid, simple_report_item)

			# TODO: (仮)標準／オプション項目を統計用に出力
			result_isnp_std_opt_report = {}
			if config_data['s_print'] == form_code['statistics_optionList']:
				result_isnp_std_opt_report[sid] = {}
				if xmlMeSid is not None:
					result_isnp_std_opt_report[sid] = cmn.get_inspection_stdOpt_data(xmlMeSid, acceptance_item)

			del xml_me, xml_xorg, xmlMeSid			# 重たいxmlはここで捨てる

			# ここから下でデータの組み立て
			csv_data_dict = {'LineNo' : total_cnt, 'Number': total_cnt}

			# 辞書に必要なものを追加
			data_type_daily_list = [form_code['statistics_daily']]	# 出力データが日別
			# 予約情報(受診日)
			if result_appoint is not None and sid in result_appoint and result_appoint[sid] is not None:
				csv_data_dict.update(result_appoint[sid])
			# 人でまとめる場合
			if config_data['s_print'] not in data_type_daily_list:
				# 受診者情報
				if result_examinee is not None and sid in result_examinee and result_examinee[sid] is not None:
					csv_data_dict.update(result_examinee[sid])
				# 総合判定／所見
				if result_general is not None and sid in result_general and result_general[sid] is not None:
					csv_data_dict.update(result_general[sid])
				# グループ判定／所見
				if result_group_rank is not None and sid in result_group_rank and result_group_rank[sid] is not None:
					if 'rank' in result_group_rank[sid] and result_group_rank[sid]['rank'] is not None: csv_data_dict.update(result_group_rank[sid]['rank'])
					# グループ判定所見
					if 'finding' in result_group_rank[sid] and result_group_rank[sid]['finding'] is not None: csv_data_dict.update(result_group_rank[sid]['finding'])
					if 'summary' in result_group_rank[sid] and result_group_rank[sid]['summary'] is not None: csv_data_dict.update(result_group_rank[sid]['summary'])
				# 治療中
				if result_medi_cure is not None and sid in result_medi_cure and result_medi_cure[sid] is not None:
					csv_data_dict.update(result_medi_cure[sid])
				# 団体情報
				if result_org is not None and sid in result_org and result_org[sid] is not None:
					csv_data_dict.update(result_org[sid])
				# 簡易報告書
				if result_simple_report is not None and sid in result_simple_report and result_simple_report[sid] is not None:
					csv_data_dict.update(result_simple_report[sid])
				# TODO: (仮)標準／オプション項目の受診リスト
				if result_isnp_std_opt_report is not None and sid in result_isnp_std_opt_report and result_isnp_std_opt_report[sid] is not None:
					csv_data_dict.update(result_isnp_std_opt_report[sid])

			# 出力対象の帳票に合わせる
			# 検査結果
			if config_data['s_print'] in inspection_sprint_list and result_inspection[sid] is not None:
				csv_data_dict.update(result_inspection[sid])
				if len(result_past_history) > 0 and sid in result_past_history and result_past_history[sid] is not None:
					csv_data_dict.update(result_past_history[sid])
			# 受診対象検査項目
			if config_data['s_print'] in acceptance_sprint_list and result_acceptance[sid] is not None:
				csv_data_dict.update(result_acceptance[sid])
			# 問診
			if config_data['s_print'] in interview_sprint_list and result_interview[sid] is not None:
				csv_data_dict.update(result_interview[sid])
			# 検査項目料金(料金リスト／請求書／領収書)
			if config_data['s_print'] in inspection_rate_sprint_list and result_inspection_rate[sid] is not None:
				csv_data_dict.update(result_inspection_rate[sid])
			# 会計（統計）情報
			if config_data['s_print'] == form_code['statistics_individual'] and result_statistics[sid] is not None:
				csv_data_dict.update(result_statistics[sid])
			elif config_data['s_print'] == form_code['statistics_daily'] and result_statistics_day[dt_appoint_day] is not None:
				csv_data_dict.update(result_statistics_day[dt_appoint_day])

			# フィルタにマッチしないデータは削除
			if filter_item_name is not None:
				fil_csv_data_dict = {}
				for fitem in filter_item_name.values():
					if fitem not in csv_data_dict:	# 収集したデータに含まれないフィルタのアイテムは空（None）で出力を行う
						fitem_key = [k for k, v in filter_item_name.items() if v == fitem][0] if fitem in filter_item_name.values() else fitem
						default_ret_val = None
						if config_data['s_print'] in statistics_rate_sprint_list:
							default_ret_val = 0
						fil_csv_data_dict[fitem_key] = default_ret_val
					else:
						# valueからkeyを抽出。なんて小難しい。。。
						# https://note.nkmk.me/python-dict-get-key-from-value/
						fil_csv_data_dict[[k for k, v in filter_item_name.items() if v == fitem][0]] = csv_data_dict.pop(fitem)
					# ソート条件用のヘッダ名もフィルタ対象になっている可能性
					for i in range(len(sort_cond)):
						if sort_cond[i]['key'] == fitem:
							sort_cond[i]['key'] = [k for k, v in filter_item_name.items() if v == fitem][0]
							break
				# 日別の場合
				if config_data['s_print'] in data_type_daily_list:
					if len(csv_data) > 0:
						dt_appoint_day_find = False
						for idx in range(len(csv_data)):	# 日付検索
							if csv_data[idx][filter_item_tag['dt_appoint']] == dt_appoint_day:	# 日付が存在する場合はデータ入れ替え
								csv_data[idx] = fil_csv_data_dict
								dt_appoint_day_find = True
						if dt_appoint_day_find == False:
							csv_data.append(fil_csv_data_dict)	# 日付がない場合も追加
					else:
						csv_data.append(fil_csv_data_dict)	# 初回は追加するのでこのルート
				else:
					csv_data.append(fil_csv_data_dict)
			else:
				# 日別の場合
				if config_data['s_print'] in data_type_daily_list:
					csv_data[dt_appoint_day] = csv_data_dict
				else:
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
			cmn._exit('warning', '{}'.format(msg))

		# ここからCSV出力用の処理
		csv_config = cmn.get_csv_format(csv_option)
		csv.register_dialect('daidai', delimiter=csv_config['delimiter'], doublequote=csv_config['doublequote'], lineterminator=csv_config['terminated'], quoting=csv_config['quoting'])

		# CSVデータ部のヘッダ作成
		csv_header = cmn.head_add(list(examinee_item.values()), csv_header)				# 受診者情報は固定出力
		csv_header = cmn.head_add(list(appoint_item.values()), csv_header)				# 予約情報は固定出力
		csv_header = cmn.head_add(list(org_item.values()), csv_header)					# 団体が登録されていると必ず出力されるので、固定
		# 検査結果リスト
		if config_data['s_print'] in inspection_sprint_list:
			if medi_cure_item['title'] is not None: csv_header.append(medi_cure_item['title'])							# ヘッダに出力する治療中の文字列
			if inspection_item is not None: csv_header = cmn.head_add(list(inspection_item.values()), csv_header)		# 検査項目
			if general_item is not None: csv_header = cmn.head_add(list(general_item.values()), csv_header)				# 総合判定／総合所見／確定医師名
			if groupRank_item is not None:	# グループ判定
				csv_header = cmn.head_add(list({k:groupRank_item[k]+'_rank' for k in groupRank_item}.values()), csv_header)				# ランク
				csv_header = cmn.head_add(list({k:groupRank_item[k]+'_finding' for k in groupRank_item}.values()), csv_header)			# 所見
				csv_header = cmn.head_add('groupRankSummary', csv_header)						# TODO: グループ所見まとめ用のCSVヘッダ名称はソース固定。直すときは検索忘れずに
			if len(result_past_history_item) > 0: csv_header = cmn.head_add(result_past_history_item, csv_header)		# 過去歴 (TODO:枠だけ用意してるので、lenで判定)
		# 受診対象検査項目リスト
		if config_data['s_print'] in acceptance_sprint_list:
			if acceptance_item is not None: csv_header = cmn.head_add(list(acceptance_item.values()), csv_header)
		# 問診項目リスト
		if config_data['s_print'] in interview_sprint_list:
			if interview_item is not None: csv_header = cmn.head_add(list(interview_item.values()), csv_header)
		# 検査項目料金リスト
		if config_data['s_print'] in inspection_rate_sprint_list:
			if price_item is not None: csv_header = cmn.head_add(list(price_item.values()), csv_header)
			if len(packName) > 0:
				packNameList = list(set(packName.split(',')))	# 重複しているパック名をここで削除
				if len(packNameList) > 0: csv_header = cmn.head_add(packNameList, csv_header)
		# 簡易報告書
		if config_data['s_print'] == form_code['simple_report']:
			if simple_report_item is not None: csv_header = cmn.head_add(list(simple_report_item.values()), csv_header)
		# 標準／オプション項目の受診リスト(TODO:仮)
		if config_data['s_print'] == form_code['statistics_optionList']:
			if inspection_item is not None: csv_header = cmn.head_add(list(acceptance_item.values()), csv_header)

		# フィルタが存在する場合、その情報からヘッダの再作成を行う
		if filter_item_name is not None:	# FIXME: INDEXを作って、さらにそれ見てソートをかけるべき
			del csv_header
			csv_header = filter_item_name


		csv_header_len = len(csv_header)			# CSVデータのカラム数として使う

		#dbg_log("len:{0}, {1}".format(csv_header_len,csv_header))

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
		with open(tmp_file.resolve(), mode='r+', newline='', encoding=csv_config['encoding']) as f:
			# 帳票＋単票用のヘッダとデータを書き込む
			if config_data['dd_header_flag'] != '0':
				fp = csv.writer(f, dialect='daidai')
				# 帳票用のヘッダ作成
				head_date = str(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
				dd_header = [dd_header_prefix, head_date, config_data['form_name']]

				form_header = [None for i in range(csv_header_len)]		# 帳票ヘッダ用の配列作成
				for key in dd_header:
					form_header[dd_header.index(key)] = key
				# 帳票用ヘッダ書き込み
				fp.writerow(form_header)
				del form_header, dd_header

				# 単票用のヘッダ部、データ部を固定で出力する(連票には不要なため)
				# FIXME: やっつけばーじょん。単票の処理を作っていないので仮対応とする。
				#		複数人数出力するファイルは連票扱いとして、固定データを除き、単票ヘッダ、空データ部を出力とする
				# total_cntの初期値は「１」のため、1人の場合は「２」となる
				renpyou_list = [
					form_code['inspection'],
					form_code['reservation'],
					form_code['price'],
					form_code['denri_kojin'],
					form_code['tokkabutu_kojin'],
					form_code['yuuki_kojin'],
					]
				if total_cnt != 2 or (config_data['s_print'] in renpyou_list):
					form_header = [None for i in range(csv_header_len)]
					form_header[0] = 'LineNo'			# 固定
					form_header[1] = 'period_from'		# 固定(仮)
					form_header[2] = 'period_to'		# 固定(仮)
					fp.writerow(form_header)
					form_data = [None for i in range(csv_header_len)]
					form_data[0] = '1'			# 固定
					form_data[1] = config_data['date_start']		# 固定(仮)
					form_data[2] = config_data['date_end']			# 固定(仮)
					fp.writerow(form_data)
					del form_header, form_data

				#f.seek(0)		# 先頭に戻す

			# CSVのフォーマットにヘッダ指定
			# TODO: ヘッダに無いデータはエラーにせず無視する(出力しない)(extrasaction='ignore')
			fp = csv.DictWriter(f, dialect='daidai', fieldnames=csv_header, extrasaction='ignore')
			#fp = csv.writer(f, dialect='daidai')
			# ヘッダの書き込み
			fp.writeheader()

			# ソート済みデータを書き込む
			line_cnt = 1
			br_num = int(config_data['xls_break_line']) if 'xls_break_line' in config_data else None
			br_cnt = 0
			for line in sort_data:
				# LineNoが存在する場合、降り直しを行う
				if 'LineNo' in line:	# TODO: LineNoはマクロ側で使用する値。改行オプションを仕込んでいる
					# かつ、改行オプションが有効ならLineNoのデータ部に仕込む
					# TODO: OrderedDictを使用しているデータの場合、未確認。こけるかも
					br_str = ''
					if 'xls_break_flag' in config_data and config_data['xls_break_flag'] == '1' and 'xls_break_line' in config_data and br_num is not None and br_cnt == br_num:
						br_cnt = 0
						br_str = config_data['xls_break_str']
					line['LineNo'] = br_str + str(line_cnt)
					if 'Number' in line:	# これに実人数が入る
						line['Number'] = line_cnt
					br_cnt += 1
				fp.writerow(line)
				line_cnt += 1

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

#@profile	# デバッグ専用
def main():

	# m_outsourceを取得
	row = cmn.get_m_outsource(config_data['sid_section'])
	if row is None:
		# m_outsourceが見つからない
		cmn._exit('sql_error', '[m_outsource] sid_section not found')
	if len(row) < 1:
		# m_outsourceの取得失敗
		cmn._exit('sql_error', '[m_outsource] get failed')
	try:
		xml_outsource = cmn.getXmlOutsource(row[0]['xml_outsource'])
	except Exception as err:
		log('m_outsoucr error:{}'.format(err))
		cmn._exit('xml_error', '[m_outsource] xml convert failed')

	del row

	# TODO: 吐き出すのは連票用
	# 単票を出力する場合は、処理を新規に作ること
	#cmn.memory_log()		# デバッグ用：実行前にメモリ状態を表示
	create_renpyou(xml_outsource)
	#cmn.memory_log()		# デバッグ用：実行後にメモリ状態を表示

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

