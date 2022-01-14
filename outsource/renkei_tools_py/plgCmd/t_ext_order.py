#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_ext_order

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql

# 受診ステータス（ex_status）
examSts = {
	# 1:予約
	'appoint' : 1,
	# 2:更新
	'update': 2,
	# 3:予約キャンセル
	'appointDel' : 3,
	# 4:受付
	'checkin' : 4,
	# 5:受付キャンセル
	'checkinDel' : 5,
}

# t_ext_order
def searchOrders(sidMorg, *, sidAppoint, seqNo, sts):
	if sidMorg is None:
		return None
	try:
		param = (sidMorg,)
		query = 'SELECT * FROM t_ext_order WHERE sid_morg = ? AND status = ? AND s_upd <= ?'
		if sidAppoint is not None:
			query += ' AND sid_appoint = ?'
			param += (sidAppoint,)
		if seqNo is not None:
			query += ' AND no = ?'
			param += (seqNo,)

		query += ';'
		rows = mySql.once(query, param)
		if rows is None:
			logger.warning('[{sidMorg}] [t_ext_order] sidAppoint not found'.format(sidMorg=sidMorg,))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows


def getAppoint(sidMorg, *, getType):
	if sidMorg is None:
		return None
	try:
		# getType = 'KPLUS' or 'LSC'
		param = (sidMorg, getType)
		query = 'CALL p_ext_get_appoint(?, ?);'
		rows = mySql.once(query, param)
		if rows is None:
			logger.warning('[{sidMorg}] [t_ext_order] p_ext_get_appoint faild'.format(sidMorg=sidMorg,))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows


def getOrderSeqNo(sidMorg, sidAppoint):
	if sidMorg is None:
		return None
	seqNo = None
	try:
		# orderNoの取得
		param = (sidMorg, sidAppoint)
		query = 'SELECT IFNULL((MAX(no) + 1), 1) AS "seqNo" FROM t_ext_order WHERE sid_morg = ? and sid_appoint = ?;'
		rows = mySql.once(query, param)
		seqNo = rows[0]['seqNo']
	except Exception as err:
		logger.debug(err)
		raise
	return seqNo


def setAppointOrder(sidMorg, *, sidAppoint, dtAppoint, seqNo, orderStatus, kplusOrder=0, lscOrder=0, socketOrder=0, order_flg=1, reception_flg=0):
	if sidMorg is None:
		return None
	try:

		# ストアド引数
		#IN	IN_sid_morg			INT UNSIGNED,			# (1) 医療機関番号
		#IN	IN_sid_upd			INT UNSIGNED,			# (2) システムユーザのsid
		#IN	IN_sid_appoint		INT UNSIGNED,			# (3) t_appointのsid
		#IN	IN_dt_appoint		DATETIME,				# (4) 予約日
		#IN	IN_no				INT UNSIGNED,			# (5) シーケンス番号
		#IN	IN_status			INT UNSIGNED,			# (6) オーダーステータス
		#IN	IN_kplus_order		INT UNSIGNED,			# (7) K+オーダ出力フラグ 0 未出力、1 出力済み　　※オーダ出力しない場合は1で設定する
		#IN	IN_lsc_order		INT UNSIGNED,			# (8) LSCオーダ出力フラグ 0 未出力、1 出力済み　　※オーダ出力しない場合は1で設定する
		#IN	IN_socket_order		INT UNSIGNED,			# (9) 電カルオーダ出力フラグ 0 未出力、1 出力済み　　※オーダ出力しない場合は1で設定する
		#IN	IN_order_flg		INT UNSIGNED,			# (10) オーダ発行フラグ 0 発行しない、1 発行する
		#IN	IN_reception_flg	INT UNSIGNED,			# (11) 受付済みフラグ   0 受付前、1 受付後

		# orderStatus = 1: 新規、2: 更新、3: 予約キャンセル、4:受付、5:受付キャンセル
		#                                 1  2  3  4  5  6  7  8  9 10 11
		query = 'CALL p_ext_appoint_order(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'
		param = (sidMorg, systemUserSid, sidAppoint, dtAppoint, seqNo, orderStatus, kplusOrder, lscOrder, socketOrder, order_flg, reception_flg)
		rows = mySql.once(query, param)
		if rows is None:
			logger.warning('[{sidMorg}] [t_ext_order] p_ext_appoint_order faild'.format(sidMorg=sidMorg,))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows
