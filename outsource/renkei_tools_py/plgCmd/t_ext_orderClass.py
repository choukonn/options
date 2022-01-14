#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_ext_order
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql



class TextOrder(mySql.Exceute):
	def __init__(self, sidMorg, *, loggerChild=None, config=None, sidUpd=systemUserSid):
		try:
			self.sidMorg = sidMorg
			# 受診ステータス（ex_status）
			self.examSts = {
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

			if loggerChild is not None:
				self.logger = loggerChild
			else:
				self.logger = logger
			super().__init__(config=None)

			# 更新者IDの指定
			if not hasattr(self, 'sidUpd'):
				if sidUpd is not None:
					self.sidUpd = int(sidUpd)
				else:
					self.sidUpd = int(systemUserSid)
			# システムのデフォルト以外が渡された場合
			elif sidUpd is not None and int(sidUpd) != int(systemUserSid) and self.sidUpd != int(sidUpd):
				self.sidUpd = int(sidUpd)

		except Exception as err:
			self.logger.error(err)

	# t_ext_order
	def searchOrders(self, sidMorg, *, sidAppoint, seqNo, sts):
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
			rows = self.once(query, param)
			if rows is None:
				self.logger.warning('[{sidMorg}] [t_ext_order] sidAppoint not found'.format(sidMorg=sidMorg,))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	def getAppoint(self, sidMorg, *, getType):
		if sidMorg is None:
			return None
		try:
			# getType = 'KPLUS' or 'LSC'
			param = (sidMorg, getType)
			query = 'CALL p_ext_get_appoint(?, ?);'
			rows = self.once(query, param)
			if rows is None:
				# TODO: 処理対象データが存在しない場合、ストアドの戻りは0件になるため、ログをコメントアウト
				#self.logger.warning('[{sidMorg}] [t_ext_order] p_ext_get_appoint faild'.format(sidMorg=sidMorg,))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	def getOrderSeqNo(self, sidMorg, sidAppoint):
		if sidMorg is None:
			return None
		seqNo = None
		try:
			# orderNoの取得
			param = (sidMorg, sidAppoint)
			query = 'SELECT IFNULL((MAX(no) + 1), 1) AS "seqNo" FROM t_ext_order WHERE sid_morg = ? and sid_appoint = ?;'
			rows = self.once(query, param)
			seqNo = rows[0]['seqNo']
		except Exception as err:
			self.logger.debug(err)
			raise
		return seqNo


	def setAppointOrder(self, sidMorg, *, sidAppoint, dtAppoint, seqNo, orderStatus, order_flg=1, reception_flg=0):
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
			#IN	IN_kplus_order		INT UNSIGNED,			# (7) K+オーダ出力フラグ
			#IN	IN_lsc_order		INT UNSIGNED,			# (8) LSCオーダ出力フラグ
			#IN	IN_socket_order		INT UNSIGNED,			# (9) 電カルオーダ出力フラグ(電カルは別途オーダ送るので1固定で設定)
			#IN	IN_order_flg		INT UNSIGNED,			# (10) オーダ発行フラグ 0 発行しない、1 発行する
			#IN	IN_reception_flg	INT UNSIGNED,			# (11) 受付済みフラグ   0 受付前、1 受付後

			# orderStatus = 1: 新規、2: 更新、3: 予約キャンセル、4:受付、5:受付キャンセル
			#                                 1  2  3  4  5  6  7  8  9 10 11
			query = 'CALL p_ext_appoint_order(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'
			param = (sidMorg, systemUserSid, sidAppoint, dtAppoint, seqNo, orderStatus, 0, 0, 1, order_flg, reception_flg)
			rows = self.once(query, param)
			if rows is None:
				self.logger.warning('[{sidMorg}] [t_ext_order] p_ext_appoint_order faild'.format(sidMorg=sidMorg,))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows
