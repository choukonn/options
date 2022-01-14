#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# sm_morg
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql



class SmMorg(mySql.Exceute):
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

	# sm_morgの取得
	def getSmMorg(self, sidMorg):
		if sidMorg is None or len(sidMorg) < 1:
			return None

		query = 'SELECT * FROM sm_morg WHERE sid = ?;'
		param = (sidMorg,)
		rows = self.once(query, param)
		if rows is None or len(rows) < 1:
			return None
		return rows[0]
