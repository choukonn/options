#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_autocalc

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

from collections import defaultdict

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sql as mySql
import plugins.plgCommon as plgCmn


# 自動計算処理
def setAutoCalc(sidMorg, sid_upd, sid_appoint, item_id, value, sid_section):
	array = {}

	try:
		array['calc_flg'] = False

		# 自動計算結果を取得
		query = 'call p_autocalc(?, null, ?, ?, ?);'
		param = (sidMorg, item_id, value, sid_section)
		rows = mySql.once(query, param)
		if rows is not None:
			if rows[0]['calc_flg'] == 1:
				# 自動計算結果を登録
				query = 'call p_updateXmlMeElementVal(?, ?, ?, ?, ?, null, null, null);'
				param = (sidMorg, sid_upd, sid_appoint, rows[0]['eie_out'], rows[0]['value'])
				rows2 = mySql.once(query, param)
				if rows2 is not None:
					array['calc_flg'] = True
					array['eie_out'] = rows[0]['eie_out']
					array['value'] = rows[0]['value']
	except Exception as err:
		logger.debug(err)
		raise

	return array


