#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_examinee
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import re
import jaconv

# myapp
from mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
import mod.common as cmn
import mod.my_sqlClass as mySql
import plugins.plgCommon as plgCmn



class Mexaminee(mySql.Exceute):
	def __init__(self, sidMorg, *, loggerChild=None, config=None, sidUpd=systemUserSid):
		try:
			# 郵便番号チェック用
			self.zipCheck1 = re.compile(r'^([0-9]{3}[\-]?[0-9]{4}[\x20\u3000]+)')
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


	# 郵便番号っぽいものと住所を分割するやつ
	def splitZipCodeAddress(self, *, moji):
		ret = {'zip' : None, 'addr' : None}
		try:
			if moji is None or type(moji) != str: return ret
			tmp = moji.strip()
			if len(tmp) < 1: return ret
			tmp = jaconv.normalize(tmp, 'NFKC')
			tmp = jaconv.z2h(tmp, digit=True)

			regObj = self.zipCheck1.search(tmp)
			if regObj is None:
				return ret

			if len(regObj.group(1)) > 0:
				tmpZip = regObj.group(1).strip()
				# TODO: 区切り文字（半角マイナス）が含まれない場合は入れる
				if tmpZip.find('-') < 0:
					tmpZip = "{}-{}".format(tmpZip[:3], tmpZip[3:])
				ret['zip'] = tmpZip.strip()

				# TODO: 郵便番号らしきものの抽出に成功した場合、残りを住所として扱う
				addr = self.zipCheck1.sub('', tmp)
				if addr is not None and len(addr) > 0:
					addr = addr.strip()
					if len(addr) > 0:
						ret['addr'] = jaconv.h2z(addr, digit=True, ascii=True)

		except Exception as err:
			logger.debug(err)
			raise

		return ret


	# 受診者検索（カルテID）
	def searchExaminee(self, *, sidMorg, examId):
		try:
			query = 'SELECT * FROM m_examinee WHERE sid_morg = ? AND EXTRACTVALUE(xml_examinee, \'//examinee/id\')="{cid}";'.format(cid=examId)
			param = (sidMorg,)
			rows = self.once(query, param)
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# 受診者XMLの登録
	def setExamineeXml(self, sidMorg, *, xml, sid, sid_upd=0):
		# IN	IN_mode			VARCHAR(255),		1: PUT=新規　POST=更新
		# IN	IN_sid_morg		INT UNSIGNED,		2: 医療機関番号
		# IN	IN_sid_upd		INT UNSIGNED,		3: 更新した人のsid、システムで固定
		# IN	IN_sid			INT UNSIGNED,		4: 新規はNULL。更新時はsid指定
		# IN	IN_s_upd		INT UNSIGNED,		5: 1:新規、2:更新
		# IN	IN_xml_examinee	MEDIUMTEXT,			6: XMLの文字列（notオブジェクト）
		# IN	IN_condition	MEDIUMTEXT			7: 謎引数

		try:
			if sidMorg is None:
				raise Exception('sidMorg is None')
			if xml is None or type(xml) != str:
				raise Exception('xml is None or not type(str)')

			if sid is None:
				mode = 'PUT'	# 新規登録
				s_upd = '1'
			# 対象IDのデータが存在した場合、更新扱い
			else:
				mode = 'POST'	# 更新登録
				s_upd = '2'

			# 更新時、xml_examineeが同じかどうかをチェックする
			if mode == 'POST':
				xmlObj = plgCmn.xml2Obj(xml)
				cid = plgCmn.customNormalize(xmlObj.find('examinee/id').text)
				query = 'CALL p_examinee("GET", ?, ?, null, null, null, ?);'
				param = (sidMorg, sid_upd, cid)
				rows = self.once(query, param)

				if rows is not None:
					if xml == rows[0]['xml_examinee']:
						# xml_examineeが同一の場合、何もしない
						self.logger.info('xml file match, do not update')
						return {'sid': sid}

			query = 'CALL p_examinee(?, ?, ?, ?, ?, ?, null);'
			param = (mode, sidMorg, sid_upd, sid, s_upd, xml)
			rows = self.once(query, param)
			if rows is not None:
				# 登録／更新に更新するとsidが返却されるので、それが存在するのかチェック
				if 'sid' in rows[0] and rows[0]['sid'] is not None and len(str(rows[0]['sid'])) > 0:
					return rows[0]
		except Exception as err:
			self.logger.debug(err)
			raise

		return None
