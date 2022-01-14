#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_i18n_dictionary
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

i18nMapLocale = plgCmn.i18nMapLocale
i18nCode = plgCmn.i18nCode



class Mi18ndictionary(mySql.Exceute):
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


	# i18n
	def geti18nCodeMap(self, sidMorg, *, useLocale=None):
		i18nMapLocale[sidMorg] = {}
		i18nCode[sidMorg] = {}
		data = None

		def i18nMap(rows):
			if i18nMapLocale[sidMorg] is not None and len(i18nMapLocale[sidMorg]) < 1:
				data = defaultdict(lambda: defaultdict(set))
				# {locale:{code1:text1,code2:text2}}
				{data[k['locale_id']].update({k['code']:k['text']}) for k in rows}
				i18nMapLocale[sidMorg] = data

			if i18nCode[sidMorg] is not None and len(i18nCode[sidMorg]) < 1:
				data = defaultdict(list)
				# {code:[text1,text2,text3]}
				if useLocale is None:
					{data[k['code']].append(k['text']) for k in rows}
					i18nCode[sidMorg] = data
				else:
					{data[k['code']].append(k['text']) for k in rows if rows['locale_id'] == useLocale}
					i18nCode[sidMorg] = data

		try:
			query = 'call p_i18ndictionary("GET", ?, null);'
			param = (sidMorg,)
			rows = self.once(query, param)
			if rows is None:
				return None

			i18nMap(rows)

		except Exception as err:
			logger.debug(err)
			raise
		return
