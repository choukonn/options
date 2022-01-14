#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_appoint_order
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)
from datetime import datetime

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sqlClass as mySql



class TappointMe(mySql.Exceute):
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


	# t_appoint_me
	# XMLMEの部分更新用ストアド
	def setUpdateXMLME(self, sidMorg, *, sidAppoint, elementSidExam, elementVal=None, eitemSidExam=None, valueForm=None, f_intendedOnly=None):
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
			query = 'CALL p_updateXmlMeElementVal(?, ?, ?, ?, ?, ?, ?, ?);'
			param = (sidMorg, systemUserSid, sidAppoint, elementSidExam, elementVal, eitemSidExam, valueForm, f_intendedOnly)
			rows = self.once(query, param)
			if rows is None:
				self.logger.debug('[{sidMorg}] [XMLME] update failed found [sidAppoint: {sidApo}, elementSidExam: {esid}, value: {v}, eitemSidExam:{isid}]'.format(sidMorg=sidMorg, sidApo=sidAppoint, isid=elementSidExam, v=elementVal, esid=eitemSidExam))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# 結果XML更新
	def eresultPost(self, sidMorg, *, sidAppoint, sUpd, nAppoint1, xml1, nAppoint2=None, xml2=None, dtUpd=None):
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
			rows = self.once(query, param)
			if rows is None:
				self.logger.debug('[{sidMorg}] [XMLME] update failed found [sidAppoint: {sidApo}]'.format(sidMorg=sidMorg, sidApo=sidAppoint))
				return None
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# t_appoint_meの取得
	def getTappointMe(self, sidMorg, *, sidAppoint):
		if sidMorg is None or sidAppoint is None:
			return None
		query = 'SELECT * FROM t_appoint_me WHERE sid_morg = ? AND sid_appoint = ?;'
		param = (sidMorg, sidAppoint)
		row = None

		try:
			rows = self.once(query, param)
			if rows is None:
				self.logger.debug('[{sidMorg}] t_appoint_me get failed [sidAppoint: {sidApo}]'.format(sidMorg=sidMorg, sidApo=sidAppoint))
				return None
			else:
				if len(rows) > 0:
					row = rows[0]
		except Exception as err:
			self.logger.debug(err)
			raise
		return row

	# XMLMEの登録
	def createUpdateXmlMeElementResult(self, *, sidMorg=None, sidAppoint=None, data=None):
		if sidAppoint is None or data is None or len(data) < 1: return None
		if sidMorg is None: sidMorg = self.sidMorg
		ret = False
		queryList = []
		tmp = None

		try:
			# TODO: UPDATEに指定するelement/result文字列を作成
			for eSid, xml in data.items():
				if xml is None or len(xml) < 1: continue
				tmp = 'xml_me = UPDATEXML(xml_me, \'//element[sid[text()="{eSid}"]]/result\', "{xml}")'.format(eSid=eSid, xml=xml)
				queryList.append(tmp)
		except Exception as err:
			self.logger.debug(err)
			raise

		if queryList is None or len(queryList) < 1:
			return ret

		try:
			# TODO: list型をstr型にしたうえで全結合
			qItem = ','.join(map(str, queryList))
			del tmp, queryList, data
		except Exception as err:
			self.logger.debug(err)
			raise

		try:
			dtUpd = datetime.now()
			apome = 'UPDATE t_appoint_me SET \
					{xml}, \
					sid_upd = ?, s_upd = 2, dt_upd = ? \
					WHERE sid_morg = ? AND sid_appoint = ? AND s_upd < 3;'.format(xml=qItem)
			param = (self.sidUpd, dtUpd, sidMorg, sidAppoint)

			# 先にt_appointのdt_updの更新をかける。そうしないと画面操作時の同時更新制御チェックにひっかかからない
			apo = 'UPDATE t_appoint SET sid_upd = ?, s_upd = 2, dt_upd = ? WHERE sid_morg = ? AND sid = ? AND s_upd < 3 AND status < 3;'
			# パラメータは同じものを使用する
			self.once(apo, param)
			self.once(apome, param)
			ret = True
		except Exception as err:
			self.logger.debug(err)
			raise

		return ret
