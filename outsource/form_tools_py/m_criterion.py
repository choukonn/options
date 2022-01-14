#!/usr/bin/python3

# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

import re
from collections import defaultdict
import xml.etree.ElementTree as ET

# myapp
import form_tools_py.common as cmn

################################
log = cmn.Log().log
dbg_log = cmn.Log().dbg_log
mySql = cmn.Sql()
################################
LOG_NOTICE = cmn.LOG_NOTICE
LOG_INFO = cmn.LOG_INFO
LOG_WARN = cmn.LOG_WARN
LOG_ERR = cmn.LOG_ERR
LOG_DBG = cmn.LOG_DBG


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
		log('{}'.format(err), LOG_ERR)
		return None

	try:
		# カンマ区切りのsidで絞り込む
		# query = 'SELECT * FROM m_criterion WHERE sid_morg = ? AND s_exam = ? AND s_upd < 3 AND FIND_IN_SET(sid, ?);'
		query = 'CALL p_getCriterionSidAndSidCriterion(?, ?, ?);'
		param = (sidMorg, s_exam, targetList)
		rows = mySql.once(query, param)
		if rows is None:
			return None
	except Exception as err:
		log('{}'.format(err), LOG_ERR)
		return None
	return rows


# XMLMEに格納されているsidを元に基準取得
def getCriterionCourse(sidMorg, *, meCriterionData):
	try:
		# 返却用のデータ格納
		criterionData = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
		data = {}

		courseSid = list(meCriterionData['ecourse'].values())[0]
		courseSidMe = list(meCriterionData['ecourse'].keys())[0]
		meCriterionDataGroupList = sorted(list(meCriterionData['egroup'].values()))
		meCriterionDataEitemList = sorted(list(meCriterionData['eitem'].values()))
		meCriterionDataElementList = sorted(list(meCriterionData['element'].values()))

		data[courseSid] = {}

		# コース基準
		rows = getCriterion(sidMorg, s_exam=1001, sidList=courseSid)
		if rows is None:
			raise Exception ('course criterion get faild')
		criterionData[courseSid]['course'] = {str(row['sid_exam']) : row for row in rows}
		# パックはコース基準から抽出する
		xmlObj = cmn.getRow2Xml(criterionData[courseSid]['course'][courseSidMe]['xml_criterion'])
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
		log('{}'.format(err), LOG_ERR)
		return None

	data[courseSid] = {k:v for k,v in criterionData[courseSid].items()}

	return data
