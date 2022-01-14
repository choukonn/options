#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_me_attribute
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import xml.etree.ElementTree as ET
from collections import defaultdict

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql



class MmeAttributeClass(mySql.Exceute):
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


	# m_me_attributeの取得
	def getMeAttribute(self, sidMorg, *, courseSid, sidMe):
		if sidMorg is None or courseSid is None:
			return None
		try:
			# コース基準XMLのgroupに含まれるグループのsidを抽出し、カンマ区切りにしたデータを返却する
			query = 'SELECT * FROM m_me_attribute WHERE sid_morg = ? AND sid_criterion = ? AND sid_me = ?;'
			param = (sidMorg, courseSid, sidMe)
			rows = self.once(query, param)
			if rows is None:
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows[0]


	# m_me_attributeを取得して抽出したものをDict型にして返す
	def getMeAttributeData(self, sidMorg, *, courseSid, sidMe):
		try:
			raw = self.getMeAttribute(sidMorg, courseSid=courseSid, sidMe=sidMe)
			attrib = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
			xmlObj = ET.fromstring(raw['xml_attribute'])
			# 1004（項目）の抽出
			xobj = xmlObj.findall('.//consultation/[s_exam="1004"]')
			for obj in xobj:
				attrib['eitem'][obj.find('sid').text]['f_intended'] = obj.find('f_intended').text
				attrib['eitem'][obj.find('sid').text]['f_exam'] = obj.find('f_exam').text
		except Exception as err:
			self.logger.debug(err)
			raise

		return attrib
