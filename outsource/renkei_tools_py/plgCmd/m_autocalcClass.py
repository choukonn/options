#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_autocalc
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

from collections import defaultdict

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql
import plugins.plgCommon as plgCmn



class MautocalcClass(mySql.Exceute):
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


	# 自動計算処理
	def setAutoCalc(self, sidMorg, sid_upd, sid_appoint, item_id, value, sid_section):
		array = {}

		try:
			array['calc_flg'] = False

			# 自動計算結果を取得
			query = 'call p_autocalc(?, null, ?, ?, ?);'
			param = (sidMorg, item_id, value, sid_section)
			rows = self.once(query, param)
			if rows is not None:
				if rows[0]['calc_flg'] == 1:
					# 自動計算結果を登録
					query = 'call p_updateXmlMeElementVal(?, ?, ?, ?, ?, null, null, null);'
					param = (sidMorg, sid_upd, sid_appoint, rows[0]['eie_out'], rows[0]['value'])
					rows2 = self.once(query, param)
					if rows2 is not None:
						array['calc_flg'] = True
						array['eie_out'] = rows[0]['eie_out']
						array['value'] = rows[0]['value']
		except Exception as err:
			self.logger.debug(err)
			raise

		return array
