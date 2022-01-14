#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_appoint_order
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql



class TappointOrder(mySql.Exceute):
	def __init__(self, sidMorg, *, loggerChild=None, config=None, sidUpd=systemUserSid):
		try:
			self.sidMorg = sidMorg
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

	# t_appoint_order
	def searchMlgTOrders(self, sidMorg, *, sidAppoint, num, sidMe, cid, seqNo):
		if sidMorg is None:
			return None
		try:
			param = (sidMorg,)
			query = 'SELECT * FROM t_appoint_order WHERE sid_morg = ? AND status = ? AND s_upd <= ?'
			if sidAppoint is not None:
				query += ' AND sid_appoint = ?'
				param += (sidAppoint,)
			if num is not None:
				query += ' AND no = ?'
				param += (num,)

			query += ';'
			rows = self.once(query, param)
			if rows is None:
				self.logger.warning('[{sidMorg}] [t_appoint_order] sidAppoint not found, sid_appoint:{sidAppoint}'.format(sidMorg=sidMorg, sidAppoint=sidAppoint))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows
