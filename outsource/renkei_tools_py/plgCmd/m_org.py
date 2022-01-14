#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_org

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql
from .. import plgCommon as plgCmn


# 団体種別番号
orgTypeCode = {
	# 所属団体
	'company'		: '1',
	# 代行機関
	'agent'			: '5',
	# 地域
	'region'		: '10',
	# 社保／国保
	'insurance'		: '11',
	# その他
	'other'			: '12',
}


# 紐づけ団体の検索
def searchXorgId(sidMorg, *, sidExaminee):

		try:
			#query = 'SELECT * FROM m_xorg WHERE sid_morg = ? AND sid_examinee = ?;'
			query = ' \
				SELECT \
					mxorg.sid_morg, \
					mxorg.sid_upd, \
					mxorg.dt_upd, \
					mxorg.s_upd, \
					mxorg.sid_examinee, \
					mxorg.sid_org, \
					mxorg.f_current, \
					mxorg.xml_xinorg, \
					EXTRACTVALUE(mxorg.xml_xinorg, "//n_examinee") AS n_examinee, \
					EXTRACTVALUE(mxorg.xml_xinorg, "//s_examinee") AS s_examinee, \
					EXTRACTVALUE(mxorg.xml_xinorg, "//f_examinee") AS f_examinee, \
					EXTRACTVALUE(morg.xml_org, "//s_org") AS s_org, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=1]/../name") AS org_1_name, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=1]/../n_org") AS org_1_n_org, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=1]/../sid") AS org_1_sid, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=5]/../name") AS org_5_name, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=5]/../n_org") AS org_5_n_org, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=5]/../sid") AS org_5_sid, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=10]/../name") AS org_10_name, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=10]/../n_org") AS org_10_n_org, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=10]/../sid") AS org_10_sid, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=11]/../name") AS org_11_name, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=11]/../n_org") AS org_11_n_org, \
					EXTRACTVALUE(morg.xml_org, "//s_org[text()=11]/../sid") AS org_11_sid, \
					morg.xml_org \
				FROM m_xorg mxorg \
					LEFT JOIN m_org morg ON mxorg.sid_morg = morg.sid_morg AND mxorg.sid_org = morg.sid \
				WHERE mxorg.sid_morg = ? AND mxorg.sid_examinee = ? AND mxorg.s_upd <> 3; \
			'
			param = (sidMorg, sidExaminee)
			rows = mySql.once(query, param)
		except Exception as err:
			logger.debug(err)
			raise
		return rows


# 団体登録情報更新
def setXorgUpdate(sidMorg, *, xml):
	# ストアド引数
	# IN	IN_sid_morg		INT UNSIGNED,		1: 医療機関番号
	# IN 	IN_sid_upd		INT UNSIGNED,		2: 更新した人のsid、システムで固定
	# IN 	IN_xorg			MEDIUMTEXT			3: xinorgのXML（紐づけされているものを全て格納したやつ）

	try:
		query = 'call p_xorg_post(?, ?, ?);'
		param = (sidMorg, 1, xml)
		rows = mySql.once(query, param)
	except Exception as err:
		logger.debug(err)
		raise
	return rows


# 団体紐づけ
def setXorgAdd(sidMorg, *, sidExaminee, sidOrg, fCurrent, xml):
	# ストアド引数
	# IN	IN_sid_morg		INT UNSIGNED,		1: 医療機関番号
	# IN 	IN_sid_upd		INT UNSIGNED,		2: 更新した人のsid、システムで固定
	# IN 	IN_sid_examinee	INT UNSIGNED,		3: 受診者のsid
	# IN 	IN_sid_org		INT UNSIGNED,		4: 団体のsid
	# IN 	IN_f_current	INT UNSIGNED,		5: 有効：1、無効：0
	# IN 	IN_xml_xinorg	MEDIUMTEXT			6: xinorgのXML

	try:
		query = 'call p_xorg_put(?, ?, ?, ?, ?, ?);'
		# sid_upd=0がストアド内で許されていないので、1固定
		param = (sidMorg, 1, sidExaminee, sidOrg, fCurrent, xml)
		rows = mySql.once(query, param)
	except Exception as err:
		logger.debug(err)
		raise
	return rows


# 団体ID検索
def searchOrgId(sidMorg, *, sid, orgId=None, sOrgId=None):
	# sOrgId = 1:所属, 10: 地域, 11:社保・国保, 12:その他保険団体
	try:
		query = None
		param = None
		rows = None
		if sid is not None:
			query = 'SELECT * FROM m_org WHERE sid_morg = ? AND sid = ?;'
			param = (sidMorg, sid)
		elif sOrgId is not None:
			query = 'SELECT * FROM m_org WHERE sid_morg = ? AND EXTRACTVALUE(xml_org, \'//org[s_org[text()="{sOrgId}"]]/n_org\') = "{orgId}";'.format(sOrgId=sOrgId, orgId=orgId)
			param = (sidMorg,)
		else:
			query = 'SELECT * FROM m_org WHERE sid_morg = ? AND EXTRACTVALUE(xml_org, "//org/n_org") = "{orgId}";'.format(orgId=orgId)
			param = (sidMorg,)
		rows = mySql.once(query, param)
	except Exception as err:
		logger.debug(err)
		raise
	return rows


# 団体XMLの登録
def setOrgXml(sidMorg, *, xml, sid):
	# ストアド引数
	# IN	IN_mode			VARCHAR(255),			1: PUT=新規　POST=更新
	# IN	IN_sid_morg		INT UNSIGNED,			2: 医療機関番号
	# IN 	IN_sid_upd		INT UNSIGNED,			3: 更新した人のsid、システムで固定
	# IN	IN_s_upd		INT UNSIGNED,			4: 1:新規、2:更新
	# IN 	IN_sid			MEDIUMTEXT,				5: 新規はNULL。更新時はsid指定
	# IN	IN_xml_org		MEDIUMTEXT,				6: XMLの文字列（notオブジェクト）
	# IN	IN_condition	VARCHAR(255)			7: 謎引数

	try:
		if sidMorg is None:
			raise Exception('sidMorg is None')
		if xml is None or type(xml) != str:
			raise Exception('xml is None or not type(str)')

		if sid is None:
			mode = 'PUT'	# 新規登録
			sUpd = '1'
		# 対象IDのデータが存在した場合、更新扱い
		else:
			mode = 'POST'	# 更新登録
			sUpd = '2'

		# 更新時、xml_orgが同じかどうかをチェックする
		if mode == 'POST':
			# 更新はsidが必須、未指定は何もしない
			if sid is None:
				return None

			# 団体検索
			rows = searchOrgId(sidMorg, sid=sid)
			# 0件は何もしない
			if len(rows) < 1:
				return None
			# 複数ヒットしたら何もしない
			elif len(rows) > 1:
				raise Exception('multiple return item, [sid:{}], [rows:{}]'.format(sid, rows))

			row = rows[0]
			# xml_orgが同一の場合、何もしない
			if xml == row['xml_org']:
				return {'sid' : row['sid']}
			# 設定対象のsidと、引数で渡されたsidが不一致は何もしない
			elif sid != row['sid']:
				raise Exception('sid unmatch, args[sid:{}], target[sid:{}]'.format(sid, row['sid']))

		#                   1  2  3  4  5  6  7
		query = 'CALL p_org(?, ?, ?, ?, ?, ?, null);'
		# sid_upd=0がストアド内で許されていないので、1固定
		param = (mode, sidMorg, 1, sUpd, sid, xml)
		rows = mySql.once(query, param)
		if rows is not None:
			# 登録／更新するとsidが返却されるので、それが存在するのかチェック
			if 'sid' in rows[0] and rows[0]['sid'] is not None and len(str(rows[0]['sid'])) > 0:
				return rows[0]

	except Exception as err:
		logger.debug(err)
		raise
	return None
