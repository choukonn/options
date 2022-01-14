#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# sm_morg

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sql as mySql


# sm_morgの取得
def getSmMorg(sidMorg):
	if sidMorg is None or len(sidMorg) < 1:
		return None

	query = 'SELECT * FROM sm_morg WHERE sid = ?;'
	param = (sidMorg,)
	rows = mySql.once(query, param)
	if rows is None or len(rows) < 1:
		return None
	return rows[0]
