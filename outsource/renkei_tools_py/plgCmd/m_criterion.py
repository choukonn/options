#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_criterion

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

from collections import defaultdict

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql
from .. import plgCommon as plgCmn


# 基準検索（たくさん）
def getCriterion(sidMorg, *, s_exam, sidList):
	if sidMorg is None or sidList is None:
		return None
	try:
		targetList = sidList
		if type(sidList) == list:
			if len(sidList) == 1:
				targetList = sidList[0]
			else:
				targetList = ','.join(sidList)

	except Exception as err:
		logger.debug(err)
		raise

	try:
		# カンマ区切りのsidで絞り込む
		# query = 'SELECT * FROM m_criterion WHERE sid_morg = ? AND s_exam = ? AND s_upd < 3 AND FIND_IN_SET(sid, ?);'
		query = 'CALL p_getCriterionSidAndSidCriterion(?, ?, ?);'
		param = (sidMorg, s_exam, targetList)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows


# 基準検索（パック）
def getCriterionCoursePacks(sidMorg, *, sidList):
	if sidMorg is None or sidList is None:
		return None
	try:
		# コース基準XMLのpackに含まれるグループのsidを抽出し、カンマ区切りにしたデータを返却する
		query = 'SELECT *,REPLACE(extractvalue(xml_criterion, "//epack/sid_criterion"), " ", ",") AS psid FROM m_criterion WHERE sid_morg = ? AND s_exam = 1001 AND sid = ?;'
		param = (sidMorg, sidList)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows[0]


# 基準検索（パック項目）
def getCriterionPackItems(sidMorg, *, sidList):
	if sidMorg is None or sidList is None:
		return None
	try:
		# パック基準に含まれる項目sidを抽出、カンマ区切りにしたデータを返却する
		query = 'SELECT *,REPLACE(extractvalue(xml_criterion, "//eitem/sid_criterion"), " ", ",") AS isid FROM m_criterion WHERE sid_morg = ? AND s_exam = 1002 AND FIND_IN_SET(sid, ?);'
		param = (sidMorg, sidList)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		logger.debug(err)
		raise
	return rows


# XMLMEに格納されているsidを元に基準取得
def getCriterionCourse(sidMorg, *, meCriterionData):
	try:
		# 返却用のデータ格納
		criterionData = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

		courseSid = list(meCriterionData['ecourse'].values())[0]
		courseSidMe = list(meCriterionData['ecourse'].keys())[0]
		meCriterionDataGroupList = list(meCriterionData['egroup'].values())
		meCriterionDataEitemList = list(meCriterionData['eitem'].values())
		meCriterionDataElementList = list(meCriterionData['element'].values())

		# コース基準
		rows = getCriterion(sidMorg, s_exam=1001, sidList=courseSid)
		if rows is None:
			raise Exception ('course criterion get faild')
		criterionData[courseSid]['course'] = {str(row['sid_exam']) : row for row in rows}
		# パックはコース基準から抽出する
		xmlObj = plgCmn.xml2Obj(criterionData[courseSid]['course'][courseSidMe]['xml_criterion'])
		psid = [obj.find('.//sid_criterion').text for obj in xmlObj.findall('.//epack')]
		rows = getCriterion(sidMorg, s_exam=1002, sidList=psid)
		if rows is not None:
			criterionData[courseSid]['epack'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}

		# グループ基準
		rows = getCriterion(sidMorg, s_exam=1003, sidList=meCriterionDataGroupList)
		if rows is None:
			raise Exception ('group criterion get faild')
		criterionData[courseSid]['egroup'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}
		# 項目に紐づくグループ
		criterionData[courseSid]['eitem2group'] = {isid:gsid for gsid in criterionData[courseSid]['egroup'] for isid in criterionData[courseSid]['egroup'][gsid]['sidList'].keys()}
		# 項目基準
		rows = getCriterion(sidMorg, s_exam=1004, sidList=meCriterionDataEitemList)
		if rows is None:
			raise Exception ('item criterion get faild')
		criterionData[courseSid]['eitem'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}
		# 要素に紐づく項目
		criterionData[courseSid]['ele2eitem'] = {esid:isid for isid in criterionData[courseSid]['eitem'] for esid in criterionData[courseSid]['eitem'][isid]['sidList'].keys()}
		# 要素基準
		rows = getCriterion(sidMorg, s_exam=1005, sidList=meCriterionDataElementList)
		if rows is None:
			raise Exception ('element criterion get faild')
		criterionData[courseSid]['element'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}

	except Exception as err:
		logger.debug(err)
		raise

	return criterionData


# XMLMEから要素／項目／グループのsidとsid_criterionを抽出
def getXMLMEcriterion(xml):
	if xml is None or len(xml) < 1: return None
	try:
		meCriterion = defaultdict(lambda: defaultdict(set))
		if type(xml) == str:
			xmlObj = plgCmn.xml2Obj(xml)
		else:
			xmlObj = xml

		meCriterion['equipment'] = {xobj.find('s_equipment').text:xobj.find('count').text for xobj in xmlObj.findall('.//equipment')}
		meCriterion['ecourse'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//ecourse')}
		meCriterion['egroup'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//egroup')}
		meCriterion['eitem'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//eitem')}
		meCriterion['element'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//element')}
	except Exception as err:
		logger.debug(err, exc_info=True)
		raise

	return meCriterion

# 基準レコードを取得
def getCriterionRow(sidMorg, sidCriterion):
	res = None

	if sidMorg is None or sidCriterion is None:
		return None
	try:
		query = 'select * from m_criterion where sid_morg = ? and sid = ?;'
		param = (sidMorg, sidCriterion)
		rows = mySql.once(query, param)
		if rows is None:
			return None

		if len(rows) > 0:
			res = rows
	except Exception as err:
		logger.debug(err)
		raise

	return res

# コース系統を取得
def getMeType(sidMorg, sidCriterion):
	meType = None

	if sidMorg is None or sidCriterion is None:
		return None
	try:
		row = getCriterionRow(sidMorg, sidCriterion)

		if row is not None and len(row) > 0 and 'xml_criterion' in row[0]:
			courseXMLObj = plgCmn.xml2Obj(row[0]['xml_criterion'])
			meType = courseXMLObj.find('./criterion/s_metype').text
	except Exception as err:
		logger.debug(err)
		raise

	return meType
