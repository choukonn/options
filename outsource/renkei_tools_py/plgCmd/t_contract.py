#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_contract

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)
import datetime

# myapp
from ..mod.mycfg import conf as mycnf
from ..mod import common as cmn
from ..mod import my_sql as mySql


# 受診者団体に紐づく契約SIDを取得
def getSidContract(sidMorg, *, sidExaminee, dtAppoint, sOrg):
	try:
		query = (" select sid from t_contract where sid_morg = ? and s_upd <> 3 "
				"	and ? between dfr_contract and dto_contract "
				"	and sid_corg in "
				"	(   select o.sid from m_org o inner join m_xorg xo "
				"		on o.sid_morg = xo.sid_morg and o.sid = xo.sid_org "
				"		where o.sid_morg = ? and extractvalue(o.xml_org, '/root/org/s_org') = ? "
				"		and xo.sid_examinee = ? and xo.s_upd <> 3 and xo.f_current = 1);")

		param = (sidMorg, dtAppoint, sidMorg, sOrg, sidExaminee)
		rows = mySql.once(query, param)

	except Exception as err:
		logger.debug(err, exc_info=True)
		raise
	return rows


