#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_outsource
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql



class Moutsource(mySql.Exceute):
	def __init__(self, sidMorg, *, loggerChild=None, config=None, sidUpd=systemUserSid):
		if sidMorg is None or len(sidMorg) < 1:
			raise Exception('sid_morg is not found')

		self.sidMorg = sidMorg

		try:
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


	def getOutource(self, *, sidMorg=None, sid=None, sid_section=None):
		try:
			query = 'SELECT * FROM m_outsource WHERE sid_morg = ?'
			param = (self.sidMorg,)

			if sid is not None:
				query += ' AND sid = ?'
				param = param + (sid,)
			elif sid_section is not None:
				query += ' AND sid_section = ?'
				param = param + (sid_section,)

			query += ';'

			rows = self.once(query, param)

		except Exception as err:
			self.logger.debug(err)
			raise

		if rows is None or len(rows) < 1:
			return None

		return rows
