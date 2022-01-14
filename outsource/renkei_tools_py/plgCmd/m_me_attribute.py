#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_me_attribute

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import xml.etree.ElementTree as ET
from collections import defaultdict

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql


# m_me_attributeの取得
def getMeAttribute(sidMorg, *, courseSid, sidMe):
	if sidMorg is None or courseSid is None:
		return None
	try:
		# コース基準XMLのgroupに含まれるグループのsidを抽出し、カンマ区切りにしたデータを返却する
		query = 'SELECT * FROM m_me_attribute WHERE sid_morg = ? AND sid_criterion = ? AND sid_me = ?;'
		param = (sidMorg, courseSid, sidMe)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows[0]


# m_me_attributeを取得して抽出したものをDict型にして返す
def getMeAttributeData(sidMorg, *, courseSid, sidMe):
	try:
		raw = getMeAttribute(sidMorg, courseSid=courseSid, sidMe=sidMe)
		attrib = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
		xmlObj = ET.fromstring(raw['xml_attribute'])
		# 1004（項目）の抽出
		xobj = xmlObj.findall('.//consultation/[s_exam="1004"]')
		for obj in xobj:
			attrib['eitem'][obj.find('sid').text]['f_intended'] = obj.find('f_intended').text
			attrib['eitem'][obj.find('sid').text]['f_exam'] = obj.find('f_exam').text
	except Exception as err:
		logger.debug(err)
		raise

	return attrib
