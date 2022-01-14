#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_appoint_order

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sql as mySql


# t_appoint_order
def searchMlgTOrders(sidMorg, *, sidAppoint, num, sidMe, cid, seqNo):
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
		rows = mySql.once(query, param)
		if rows is None:
			logger.warning('[{sidMorg}] [t_appoint_order] sidAppoint not found, sid_appoint:{sidAppoint}'.format(sidMorg=sidMorg, sidAppoint=sidAppoint))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows
