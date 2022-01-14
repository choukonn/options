#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_ext_info

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)
from collections import defaultdict

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql


# t_ext_infoのデータを検索
def extInfoGet(sidMorg, *, plgName=None, sidAppoint=None, vid=None):
	if sidMorg is None or plgName is None:
		return None
	if sidAppoint is None and vid is None:
		return None

	# ストアド引数
	# IN sid_morg INT UNSIGNED,			-- (1): 医療機関番号
	# IN plugin_id VARCHAR(30),			-- (2): pluginの名前
	# IN sid_appoint INT UNSIGNED		-- (3): t_appointのsid
	# IN visit_id VARCHAR(30),			-- (4): visitId

	try:
		#                            1  2  3  4
		query = 'CALL p_ext_info_get(?, ?, ?, ?);'
		param = (sidMorg, plgName, sidAppoint, vid)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise

	return rows


# t_ext_infoのデータを検索(受診者連携用)
def extInfoGet2(sidMorg, *, plgName=None, sidAppoint=None, sidExaminee=None):
	if sidMorg is None or plgName is None:
		return None
	if sidExaminee is None:
		return None

	# ストアド引数
	# IN sid_morg INT UNSIGNED,			-- (1): 医療機関番号
	# IN plugin_id VARCHAR(30),			-- (2): pluginの名前
	# IN sidExaminee INT UNSIGNED		-- (3): 受診者SID

	try:
		#                            1  2  3  4
		query = 'CALL p_ext_info_get2(?, ?, ?, ?);'
		param = (sidMorg, plgName, sidAppoint, sidExaminee)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise

	return rows


# t_ext_infoに新規登録
def extInfoPut(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None):
	if sidMorg is None or pName is None or sidAppoint is None:
		return None

	# ストアド引数
	# IN sid_morg INT UNSIGNED,			-- (1): 医療機関番号
	# IN sid_upd INT UNSIGNED,			-- (2): 更新ユーザのsid
	# IN plugin_id VARCHAR(30),			-- (3): プラグイン名
	# IN visit_id VARCHAR(30),			-- (4): 受付通し番号
	# IN examinee_id VARCHAR(20),		-- (5): カルテID
	# IN sid_appoint INT UNSIGNED,		-- (6): t_appointのsid
	# IN sid_examinee INT UNSIGNED,		-- (7): m_examineeのsid
	# IN dt_appoint DATETIME,			-- (8): 予約日時
	# IN update_time DATETIME,			-- (9): 更新日時
	# IN xml_info MEDIUMTEXT,			-- (10): 情報

	try:
		#                            1  2  3  4  5  6  7  8  9 10
		query = 'CALL p_ext_info_put(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'
		param = (sidMorg, systemUserSid, pName, vid, cid, sidAppoint, sidExaminee, dtAppoint, updateTime, xmlInfo)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise

	return rows


# t_ext_infoの更新
def extInfoPost(sidMorg, *, pName, sidAppoint, sidExaminee=None, vid=None, cid=None, dtAppoint=None, updateTime=None, xmlInfo=None, sUpd=2):
	if sidMorg is None or pName is None or sidAppoint is None:
		return None

	# ストアド引数
	# IN sid_morg INT UNSIGNED,			-- (1): 医療機関番号
	# IN sid_upd INT UNSIGNED,			-- (2): 更新ユーザのsid
	# IN s_upd INT UNSIGNED,			-- (3): 更新ステータス（１：新規、２：更新、３：論理削除）
	# IN plugin_id VARCHAR(30),			-- (4): プラグイン名
	# IN visit_id VARCHAR(30),			-- (5): 受付通し番号
	# IN examinee_id VARCHAR(20),		-- (6): カルテID
	# IN sid_appoint INT UNSIGNED,		-- (7): t_appointのsid
	# IN sid_examinee INT UNSIGNED,		-- (8): m_examineeのsid
	# IN dt_appoint DATETIME,			-- (9): 予約日時
	# IN update_time DATETIME,			-- (10): 更新日時
	# IN xml_info MEDIUMTEXT,			-- (11): 情報

	try:
		#                             1  2  3  4  5  6  7  8  9 10 11
		query = 'CALL p_ext_info_post(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'
		param = (sidMorg, systemUserSid, sUpd, pName, vid, cid, sidAppoint, sidExaminee, dtAppoint, updateTime, xmlInfo)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise

	return rows

