#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_appoint_order

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)
from datetime import datetime

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql


# t_appoint_me
# XMLMEの部分更新用ストアド
def setUpdateXMLME(sidMorg, *, sidAppoint, elementSidExam, elementVal=None, eitemSidExam=None, valueForm=None, f_intendedOnly=None):
	if sidMorg is None:
		return None

	# TODO：引数
	# IN sidMorg INT UNSIGNED,				-- 1:医療機関番号
	# IN sidUpd INT UNSIGNED,				-- 2:更新者のSID
	# IN sidAppoint INT UNSIGNED,			-- 3:予約者SID
	# IN elementSidExam INT UNSIGNED,		-- 4:要素のsidExam
	# IN elementVal MEDIUMTEXT,				-- 5:要素に入れる結果値
	# IN eitemSidExam INT UNSIGNED,			-- 6:f_intendedを作成したい項目のsidExam
	# IN valueForm VARCHAR(20),				-- 7:要素の数値入力で使用する結果形態値（不要な場合はNULL固定）
	# IN f_intendedOnly TINYINT(1)			-- 8:valueタグの操作を行わず、f_intendedのみを操作したい場合（NULL=操作しない|0=フラグOFF|1=フラグON）

	try:
		#                                     1  2  3  4  5  6  7  8
		query = 'CALL p_updateXmlMeElementVal2(?, ?, ?, ?, ?, ?, ?, ?);'
		param = (sidMorg, systemUserSid, sidAppoint, elementSidExam, elementVal, eitemSidExam, valueForm, f_intendedOnly)
		rows = mySql.once(query, param)
		if rows is None:
			logger.debug('[{sidMorg}] [XMLME] update failed found [sidAppoint: {sidApo}, elementSidExam: {esid}, value: {v}, eitemSidExam:{isid}]'.format(sidMorg=sidMorg, sidApo=sidAppoint, isid=elementSidExam, v=elementVal, esid=eitemSidExam))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows

# 結果XML更新
def eresultPost(sidMorg, *, sidAppoint, sUpd, nAppoint1, xml1, nAppoint2=None, xml2=None, dtUpd=None):
	if sidMorg is None:
		return None
	# IN	IN_sid_morg				INT UNSIGNED,		-- 1
	# IN	IN_sid_upd				INT UNSIGNED,		-- 2
	# IN	IN_sid_appoint			INT UNSIGNED,		-- 3
	# IN	IN_status				INT UNSIGNED,		-- 4
	# IN	IN_n_appoint_me_1		INT UNSIGNED,		-- 5 枝番、たぶん使われていないので1固定にする
	# IN	IN_xml_me_1				MEDIUMTEXT,			-- 6
	# IN	IN_n_appoint_me_2		INT UNSIGNED,		-- 7 ??
	# IN	IN_xml_me_2				MEDIUMTEXT,			-- 8 ??
	# IN	IN_dt_upd				VARCHAR(255)		-- 9

	if dtUpd is None:
		_dtUpd = datetime.now()
	else:
		_dtUpd = dtUpd

	try:
		#                            1  2  3  4  5  6  7  8  9
		query = 'CALL p_eresult_post(?, ?, ?, ?, ?, ?, ?, ?, ?, null);'
		param = (sidMorg, 1, sidAppoint, sUpd, nAppoint1, xml1, nAppoint2, xml2, _dtUpd)
		rows = mySql.once(query, param)
		if rows is None:
			logger.debug('[{sidMorg}] [XMLME] update failed found [sidAppoint: {sidApo}]'.format(sidMorg=sidMorg, sidApo=sidAppoint))
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows
