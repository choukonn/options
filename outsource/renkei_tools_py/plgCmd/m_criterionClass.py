#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_criterion
# クラス化してみたい
import xml.etree.ElementTree as ET

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

from collections import defaultdict, namedtuple

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql
import plugins.plgCommon as plgCmn

# 定義情報
_itemNumber = namedtuple('itemNumber', (
	'ecourse',
	'epack',
	'egroup',
	'eitem',
	'element'
))
itemType = _itemNumber(1001, 1002, 1003, 1004, 1005)


class Mcriterion(mySql.Exceute):
	def __init__(self, sidMorg, *, loggerChild=None, config=None, sidUpd=systemUserSid):
		try:
			self.sidMorg = sidMorg
			if loggerChild is not None:
				self.logger = loggerChild
			else:
				self.logger = logger
			super().__init__(config=None)

			# 更新者IDの指定
			if not hasattr(self, 'sidUpd'):
				if sidUpd is not None:
					self.sidUpd = int(sidUpd)
				else:
					self.sidUpd = int(systemUserSid)
			# システムのデフォルト以外が渡された場合
			elif sidUpd is not None and int(sidUpd) != int(systemUserSid) and self.sidUpd != int(sidUpd):
				self.sidUpd = int(sidUpd)

			self.itemType = itemType

		except Exception as err:
			self.logger.error(err)


	# 基準取得（一括）
	def getCriterionsAll(self, sidMorg, *, courseSid, mode=None):
		if sidMorg is None:
			return None

		try:
			# 医療機関番号とコースSIDを指定
			query = 'CALL p_ext_getCriterions(?, ?, ?);'
			param = (sidMorg, courseSid, mode)
			rows = self.once(query, param)
			if rows is None:
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# 基準検索（たくさん）
	def getCriterion(self, sidMorg, *, s_exam, sidList):
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
			self.logger.debug(err)
			raise

		try:
			# カンマ区切りのsidで絞り込む
			# query = 'SELECT * FROM m_criterion WHERE sid_morg = ? AND s_exam = ? AND s_upd < 3 AND FIND_IN_SET(sid, ?);'
			query = 'CALL p_getCriterionSidAndSidCriterion(?, ?, ?);'
			param = (sidMorg, s_exam, targetList)
			rows = self.once(query, param)
			if rows is None:
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# 基準検索（パック）
	def getCriterionCoursePacks(self, sidMorg, *, sidList):
		if sidMorg is None or sidList is None:
			return None
		try:
			# コース基準XMLのpackに含まれるグループのsidを抽出し、カンマ区切りにしたデータを返却する
			query = 'SELECT *,REPLACE(extractvalue(xml_criterion, "//epack/sid_criterion"), " ", ",") AS psid FROM m_criterion WHERE sid_morg = ? AND s_exam = 1001 AND sid = ?;'
			param = (sidMorg, sidList)
			rows = self.once(query, param)
			if rows is None:
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows[0]


	# 基準検索（パック項目）
	def getCriterionPackItems(self, sidMorg, *, sidList):
		if sidMorg is None or sidList is None:
			return None
		try:
			# パック基準に含まれる項目sidを抽出、カンマ区切りにしたデータを返却する
			query = 'SELECT *,REPLACE(extractvalue(xml_criterion, "//eitem/sid_criterion"), " ", ",") AS isid FROM m_criterion WHERE sid_morg = ? AND s_exam = 1002 AND FIND_IN_SET(sid, ?);'
			param = (sidMorg, sidList)
			rows = self.once(query, param)
			if rows is None:
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# コース基準を元に一括で取得した基準情報を解析／返却
	def getCriterionCourseAll(self, sidMorg, *, meCriterionData, mode=None):
		try:
			# 返却用のデータ格納
			criterionData = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

			courseSid = list(meCriterionData['ecourse'].values())[0]
		except Exception as err:
			raise

		try:
			# TODO: 項目が属するグループ、または要素が属する項目の紐づけデータの生成を行う
			def item2val(itemKey1, itemKey2):
				sidList = {}
				for sidExam, val1 in itemKey1.items():
					if 'raw' not in val1 or val1['raw'] is None or len(val1['raw']) < 1: continue
					xmlObj = plgCmn.xml2Obj(val1['raw']['xml_criterion'])
					_sid = [k.text for k in xmlObj.findall('.//sid') if k.text is not None]
					_item2Sid = list(filter(lambda x : x in _sid, itemKey2))
					for _itemSid in _item2Sid:
						sidList[_itemSid] = sidExam
				return sidList

		except Exception as err:
			raise

		try:
			# 一括取得
			rows = self.getCriterionsAll(sidMorg, courseSid=courseSid, mode=mode)
			if rows is None:
				raise Exception ('course criterion get faild')
			# コース基準
			tmp = list(filter(lambda x : x['sid'] == int(courseSid), rows))
			if tmp is None or len(tmp) < 1:
				raise Exception ('course criterion get failed')
			criterionData[courseSid]['course'] = tmp[0]

			# パックはコース基準から抽出する
			xmlObj = plgCmn.xml2Obj(criterionData[courseSid]['course']['xml_criterion'])
			psidEitem = [obj.find('.//sid_criterion').text for obj in xmlObj.findall('.//epack') if obj.find('.//sid_criterion') is not None and obj.find('.//sid_criterion').text is not None]
			# パック基準
			tmp = list(filter(lambda x : x['s_exam'] == self.itemType.epack, rows))
			criterionData[courseSid]['epack'] = None
			if tmp is not None or len(tmp) > 0:
				criterionData[courseSid]['epack'] = {str(k['sid_exam']) : {'sid': str(k['sid']), 'raw': k} for k in tmp}

			# グループ基準
			tmp = list(filter(lambda x : x['s_exam'] == self.itemType.egroup, rows))
			if tmp is None or len(tmp) < 1:
				raise Exception ('group criterion get faild')
			criterionData[courseSid]['egroup'] = {str(k['sid_exam']) : {'sid': str(k['sid']), 'eorgCode': {'eorgSid': k['eorgSid'], 'egReqCode': k['egReqCode']}, 'raw': k} for k in tmp}

			# 項目基準
			tmp = list(filter(lambda x : x['s_exam'] == self.itemType.eitem, rows))
			if tmp is None or len(tmp) < 1:
				raise Exception ('item criterion get faild')
			criterionData[courseSid]['eitem'] = {str(k['sid_exam']) : {'sid': str(k['sid']), 'eorgCode': {'eorgSid': k['eorgSid'], 'eiReqCode': k['eiReqCode']}, 'raw': k} for k in tmp}

			# 要素基準
			tmp = list(filter(lambda x : x['s_exam'] == self.itemType.element, rows))
			if tmp is None or len(tmp) < 1:
				raise Exception ('element criterion get faild')
			criterionData[courseSid]['element'] = {str(k['sid_exam']) : {'sid': str(k['sid']), 'eorgCode': {'eorgSid': k['eorgSid'], 'eieReqCode': k['eieReqCode'], 'eieResCode': k['eieResCode']}, 'raw': k} for k in tmp}

			# 項目に紐づくグループ
			criterionData[courseSid]['eitem2group'] = item2val(criterionData[courseSid]['egroup'], criterionData[courseSid]['eitem'])
			# 要素に紐づく項目
			criterionData[courseSid]['ele2eitem'] = item2val(criterionData[courseSid]['eitem'], criterionData[courseSid]['element'])

		except Exception as err:
			self.logger.debug(err)
			raise

		return criterionData


	# XMLMEに格納されているsidを元に基準取得
	def getCriterionCourse(self, sidMorg, *, meCriterionData):
		try:
			# 返却用のデータ格納
			criterionData = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

			courseSid = list(meCriterionData['ecourse'].values())[0]
			courseSidMe = list(meCriterionData['ecourse'].keys())[0]
			meCriterionDataGroupList = list(meCriterionData['egroup'].values())
			meCriterionDataEitemList = list(meCriterionData['eitem'].values())
			meCriterionDataElementList = list(meCriterionData['element'].values())

			# コース基準
			rows = self.getCriterion(sidMorg, s_exam=self.itemType.ecourse, sidList=courseSid)
			if rows is None:
				raise Exception ('course criterion get faild')
			criterionData[courseSid]['course'] = {str(row['sid_exam']) : row for row in rows}
			# パックはコース基準から抽出する
			xmlObj = plgCmn.xml2Obj(criterionData[courseSid]['course'][courseSidMe]['xml_criterion'])
			psid = [obj.find('.//sid_criterion').text for obj in xmlObj.findall('.//epack')]
			rows = self.getCriterion(sidMorg, s_exam=self.itemType.epack, sidList=psid)
			if rows is not None:
				criterionData[courseSid]['epack'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}

			# グループ基準
			rows = self.getCriterion(sidMorg, s_exam=self.itemType.egroup, sidList=meCriterionDataGroupList)
			if rows is None:
				raise Exception ('group criterion get faild')
			criterionData[courseSid]['egroup'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}
			# 項目に紐づくグループ
			criterionData[courseSid]['eitem2group'] = {isid:gsid for gsid in criterionData[courseSid]['egroup'] for isid in criterionData[courseSid]['egroup'][gsid]['sidList'].keys()}
			# 項目基準
			rows = self.getCriterion(sidMorg, s_exam=self.itemType.eitem, sidList=meCriterionDataEitemList)
			if rows is None:
				raise Exception ('item criterion get faild')
			criterionData[courseSid]['eitem'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}
			# 要素に紐づく項目
			criterionData[courseSid]['ele2eitem'] = {esid:isid for isid in criterionData[courseSid]['eitem'] for esid in criterionData[courseSid]['eitem'][isid]['sidList'].keys()}
			# 要素基準
			rows = self.getCriterion(sidMorg, s_exam=self.itemType.element, sidList=meCriterionDataElementList)
			if rows is None:
				raise Exception ('element criterion get faild')
			criterionData[courseSid]['element'] = {str(row['sid_exam']) : {'sid':str(row['sid']), 'sidList':dict(k.split(':') for k in row['sidList'].split(',') if len(row['sidList']) > 0), 'raw':row} for row in rows}

		except Exception as err:
			self.logger.debug(err)
			raise

		return criterionData


	# XMLMEから要素／項目／グループのsidとsid_criterionを抽出
	def getXMLMEcriterion(self, xml):
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
			self.logger.debug(err)
			raise

		return meCriterion
