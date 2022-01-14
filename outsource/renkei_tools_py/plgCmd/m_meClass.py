#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_me
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql



class Mme(mySql.Exceute):
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


	# m_meの取得
	def getMe(self, sidMorg, *, sid_criterion=None, sUpd=2, sts=1, sidMe=None, inCourseID=None):
		if sidMorg is None:
			return None
		try:
			query = 'SELECT * FROM m_me WHERE sid_morg = ? AND status = ? AND s_upd <= ?'
			if inCourseID is not None:
				query += ' AND inCourseID = ?'
				param = (sidMorg, sts, sUpd, inCourseID)
			elif sid_criterion is not None and sidMe is not None:
				query += ' AND sid_criterion = ? AND sid = ?'
				param = (sidMorg, sts, sUpd, sid_criterion, sidMe)
			else:
				param = (sidMorg, sts, sUpd)
			query += ';'
			rows = self.once(query, param)
			if rows is None:
				self.logger.warning('[{sidMorg}] [m_me] Course not found, courseSid:{courseSid}, sidMe:{sidMe}'.format(sidMorg=sidMorg, courseSid=sid_criterion, sidMe=sidMe))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows
