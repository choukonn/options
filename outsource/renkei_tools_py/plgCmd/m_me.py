#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_me

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql


# m_meの取得
def getMe(sidMorg, *, sid_criterion=None, sUpd=2, sts=1, sidMe=None, inCourseID=None):
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
		rows = mySql.once(query, param)
		if rows is None:
			logger.warning('[{sidMorg}] [m_me] Course not found, courseSid:{courseSid}, sidMe:{sidMe}'.format(sidMorg=sidMorg, courseSid=sid_criterion, sidMe=sidMe))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows
