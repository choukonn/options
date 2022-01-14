#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_eorg
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)
from collections import defaultdict

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql



class Meorg(mySql.Exceute):
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

		except Exception as err:
			self.logger.error(err)


	# eieのみ取得
	def getEorgCodeEie(self, sidMorg, *, eOrgSid):
		if sidMorg is None or eOrgSid is None:
			return None
		eOrgCode = {}
		eOrgCode['eie'] = {}
		codeMap = defaultdict(set)

		try:
			query = 'SELECT * FROM m_eorg_eie WHERE sid_morg = ? AND sid_eorg = ? AND (res_code != "" OR req_code != "");'
			param = (sidMorg, eOrgSid)
			rows = self.once(query, param)
			if rows is None:
				return None
		except Exception as err:
			self.logger.debug(err)
			raise

		try:
			for row in rows:
				# TODO: マッピングコードがないやつは無視
				if (row['req_code'] is not None and len(row['req_code']) > 0) or (row['res_code'] is not None and len(row['res_code']) > 0):
					eOrgCode['eie'][row['sid']] = {'req': row['req_code'] if len(row['req_code']) > 0 else None, 'res':row['res_code'] if len(row['res_code']) > 0 else None}

				codeMap['eie'] = defaultdict(lambda: defaultdict(set))
				for key, val in eOrgCode['eie'].items():
					if val['req'] is None and val['res'] is None: continue
					codeMap['eie'][str(key)]['req'] = list(set(val['req'].split(','))) if val['req'] is not None else None
					codeMap['eie'][str(key)]['res'] = list(set(val['res'].split(','))) if val['res'] is not None else None
				if len(codeMap['eie']) < 1: codeMap['eie'] = None

		except Exception as err:
			self.logger.debug(err)
			raise

		return codeMap


	# 外部検査機関のコード一覧を取得
	def getEorgCodeBase(self, sidMorg, *, eOrgSid):
		if sidMorg is None or eOrgSid is None:
			return None
		try:
			query = 'CALL p_getEorgCodeBase(?, ?);'
			param = (sidMorg, eOrgSid)
			rows = self.once(query, param)
			if rows is None:
				return None
		except Exception as err:
			self.logger.debug(err)
			raise

		return rows


	# 外部検査機関のマッピング設定を取得
	def getEorgCodeList(self, sidMorg, *, eOrgSid):
		if sidMorg is None or eOrgSid is None:
			return None
		try:
			rows = self.getEorgCodeBase(sidMorg, eOrgSid=eOrgSid)
			if rows is None:
				return None
			eOrgCode = {}
			eOrgCode['eie'] = {}
			eOrgCode['ei'] = {}
			eOrgCode['eg'] = {}
			for row in rows:
				# TODO: マッピングコードがないやつは無視
				if (row['eieReqCode'] is not None and len(row['eieReqCode']) > 0) or (row['eieResCode'] is not None and len(row['eieResCode']) > 0):
					eOrgCode['eie'][row['sid_eie']] = {'req': row['eieReqCode'] if len(row['eieReqCode']) > 0 else None, 'res':row['eieResCode'] if len(row['eieResCode']) > 0 else None}
				if row['eiReqCode'] is not None and len(row['eiReqCode']) > 0:
					eOrgCode['ei'][row['sid_ei']] = {'req': row['eiReqCode'] if len(row['eiReqCode']) > 0 else None}
				if row['egReqCode'] is not None and len(row['egReqCode']) > 0:
					eOrgCode['eg'][row['sid_deg']] = {'req': row['egReqCode'] if len(row['egReqCode']) > 0 else None}
		except Exception as err:
			self.logger.debug(err)
			raise

		return eOrgCode


	# XMLMEのecourseに設定されているsidEorgを元に外注マッピングの取得（グループ／項目／要素に値が設定されているものだけ）
	def getOutsourcingMap(self, sidMorg, *, courseXMLObj):
		codeMap = defaultdict(set)
		eOrgSid = None
		if sidMorg is None or courseXMLObj is None: return None
		try:
			eOrgSid = courseXMLObj.find('.//eorg/sid').text if courseXMLObj.find('.//eorg/sid') is not None else None
			if eOrgSid is None:
				self.logger.debug('[{}] eOrgSid is None, mapcode search faild, default use'.format(sidMorg))
				return None
			codeMappingInfo = self.getEorgCodeList(sidMorg, eOrgSid=eOrgSid)
			codeMap['eg'] = defaultdict(lambda: defaultdict(set))
			codeMap['ei'] = defaultdict(lambda: defaultdict(set))
			codeMap['eie'] = defaultdict(lambda: defaultdict(set))
			# 値が存在するものだけ格納
			for key, val in codeMappingInfo['eg'].items():
				if val['req'] is None: continue
				codeMap['eg'][str(key)]['req'] = list(set(val['req'].split(','))) if val['req'] is not None else None
			if len(codeMap['eg']) < 1: codeMap['eg'] = None

			for key, val in codeMappingInfo['ei'].items():
				if val['req'] is None: continue
				codeMap['ei'][str(key)]['req'] = list(set(val['req'].split(','))) if val['req'] is not None else None
			if len(codeMap['ei']) < 1: codeMap['ei'] = None

			for key, val in codeMappingInfo['eie'].items():
				if val['req'] is None and val['res'] is None: continue
				codeMap['eie'][str(key)]['req'] = list(set(val['req'].split(','))) if val['req'] is not None else None
				codeMap['eie'][str(key)]['res'] = list(set(val['res'].split(','))) if val['res'] is not None else None
			if len(codeMap['eie']) < 1: codeMap['eie'] = None

		except Exception as err:
			self.logger.debug(err)
			raise

		try:
			mapListCheck = [k for k in codeMap.values() if k != None]
			if len(mapListCheck) < 1:
				self.logger.debug('[{}] mapping code is all None, default use'.format(sidMorg))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise

		return codeMap
