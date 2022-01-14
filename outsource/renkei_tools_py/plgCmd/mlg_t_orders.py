#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# mlg_t_orders

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sql as mySql


# mlg_t_orders
def setMlgPostOrder(sidMorg, *, sidAppoint, ssidLinkageProduct, ssidFileKind, xml, orderNo, ssidFrom, fileName, orderKey, seqNo, targetName):
	if sidMorg is None:
		return None

	# ストアドの引数メモ
	# IN		IN_mode						VARCHAR(10)				-- 1 未使用
	#,IN		IN_sid_morg					INT UNSIGNED			-- 2 医療機関番号
	#,IN		IN_st_upd					INT UNSIGNED			-- 3 「1」固定
	#,IN		IN_int_order				INT UNSIGNED			-- 4 「1」固定
	#,IN		IN_int_upd_sid_usr			INT	UNSIGNED			-- 5 システムユーザのsid
	#,IN		IN_ssid_linkage_product		INT	UNSIGNED			-- 6 m_outsourceの「ssid_to」
	#,IN		IN_ssid_file_kind			INT UNSIGNED			-- 7 m_outsourceの「ssid_file_kind」
	#,IN		IN_txt_order				MEDIUMTEXT				-- 8 オーダＸＭＬ
	#,IN		IN_sid_appoint				INT UNSIGNED			-- 9 daidaiのsid_appoint
	#,IN		IN_order_no					VARCHAR(32)				-- 10 オーダー番号
	#,IN		IN_DB_PATH					varchar(255)			-- 11 MLGの接続情報
	#,IN		IN_ssid_data_acquisition	INT UNSIGNED			-- 12 m_outsourceの「ssid_from」
	#,IN		IN_vc_file_name				VARCHAR(255)			-- 13 ファイル名
	#,IN		IN_xml_order				mediumtext				-- 14 null固定
	#,IN		IN_order_key				VARCHAR(255)			-- 15 yyyymmdd_カルテID
	#,IN		IN_IndexFile				VARCHAR(255)			-- 16 null固定
	#,IN		IN_no						INT UNSIGNED			-- 17 オーダー通し番号
	#,IN		IN_target					VARCHAR(10)				-- 18 'KPLUS'の文字列固定

	try:
		# TODO: mysql://testUser:testPass@localhost:3306/mlg_data/
		mlgPath = 'mysql://' + mycnf['useMLGconf']['user'] + ':' + mycnf['useMLGconf']['pass'] + '@' + mycnf['useMLGconf']['host'] + ':' + str(mycnf['useMLGconf']['port']) + '/' + mycnf['useMLGconf']['dbName'] + '/'

		#                              1     2  3  4  5  6  7  8  9  10 11 12 13 14    15 16    17 18
		query = 'CALL p_mlg_post_order(null, ?, 1, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, null, ?, null, ?, ?);'
		param = (sidMorg, systemUserSid, ssidLinkageProduct, ssidFileKind, xml, sidAppoint, orderNo, mlgPath, ssidFrom, fileName, orderKey, seqNo, targetName)
		rows = mySql.once(query, param)
		if rows is None:
			logger.warning('[{sidMorg}] [p_mlg_post_order] post faild, sidAppoint: {sidAppoint}, orderKey: {orderkey}'.format(sidMorg=sidMorg, sidAppoint=sidAppoint, orderkey=orderKey))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows


# 受診者情報の更新
def setMlgPostExam(sidMorg, *, ssidLinkageProduct, ssidFileKind, xml, orderNo, ssidFrom, fileName, orderKey):
	if sidMorg is None:
		return None

	# ストアド引数メモ
	# IN		IN_sid_morg					INT UNSIGNED		-- 1 医療機関番号
	#,IN		IN_st_upd					INT UNSIGNED		-- 2 「1」固定
	#,IN		IN_int_order				INT UNSIGNED		-- 3 「1」固定
	#,IN		IN_int_upd_sid_usr			INT	UNSIGNED		-- 4 システムユーザのsid
	#,IN		IN_ssid_linkage_product		INT	UNSIGNED		-- 5 m_outsourceの「ssid_to」
	#,IN		IN_ssid_file_kind			INT UNSIGNED		-- 6 m_outsourceの「ssid_file_kind」
	#,IN		IN_txt_order				MEDIUMTEXT			-- 7 オーダＸＭＬ
	#,IN		IN_order_no					VARCHAR(32)			-- 8 オーダー番号
	#,IN		IN_DB_PATH					varchar(255)		-- 9 MLGの接続情報
	#,IN		IN_ssid_data_acquisition	INT UNSIGNED		-- 10 m_outsourceの「ssid_from」
	#,IN		IN_vc_file_name				VARCHAR(255)		-- 11 ファイル名
	#,IN		IN_order_key				VARCHAR(255)		-- 12 yyyymmdd_カルテID

	try:
		# TODO: mysql://testUser:testPass@localhost:3306/mlg_data/
		mlgPath = 'mysql://' + mycnf['useMLGconf']['user'] + ':' + mycnf['useMLGconf']['pass'] + '@' + mycnf['useMLGconf']['host'] + ':' + str(mycnf['useMLGconf']['port']) + '/' + mycnf['useMLGconf']['dbName'] + '/'

		#                             1  2  3  4  5  6  7  8  9 10 11 12
		query = 'CALL p_mlg_post_exam(?, 1, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?);'
		param = (sidMorg, systemUserSid, ssidLinkageProduct, ssidFileKind, xml, orderNo, mlgPath, ssidFrom, fileName, orderKey)
		rows = mySql.once(query, param)
		if rows is None:
			logger.warning('[{sidMorg}] [p_mlg_post_exam] post faild'.format(sidMorg=sidMorg,))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows
