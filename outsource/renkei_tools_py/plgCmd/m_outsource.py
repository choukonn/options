#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_outsource

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql


# m_outsourceの取得
def getOutource(sidMorg, sid=None, sid_section=None):
	if sidMorg is None or len(sidMorg) < 1:
		return None

	query = 'SELECT * FROM m_outsource WHERE sid_morg = ?'
	param = (sidMorg,)
	if sid is not None:
		query += ' AND sid = ?'
		param = param + (sid,)
	elif sid_section is not None:
		query += ' AND sid_section = ?'
		param = param + (sid_section,)

	query += ';'

	rows = mySql.once(query, param)
	if rows is None or len(rows) < 1:
		return None

	return rows
