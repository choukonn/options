#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_contract_me_attribute
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sqlClass as mySql



class T_contract_me_attribute(mySql.Exceute):
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

	# t_contract_me_attributeの取得
	def getT_contract_me_attribute(self, sidMorg):
		if sidMorg is None or len(sidMorg) < 1:
			return None

		query = ' \
			SELECT \
				tcm.sid_morg, \
				tcm.sid_upd, \
				tcm.dt_upd, \
				tcm.s_upd, \
				tcm.sid_contract AS t_contract_me_sid_contract, \
				tcm.sid_me AS t_contract_me_sid_me, \
				tcm.sid_criterion AS t_contract_me_sid_criterion, \
				tcm.sid_exam AS t_contract_me_sid_exam, \
				extractvalue(tcm.xml_attribute, "/root/attribute/name") AS t_contract_me_name, \
				tcm.xml_attribute AS t_contract_me_xml_attribute, \
				mme.sid AS m_me_sid, \
				mme.psid AS m_me_psid, \
				mme.name AS m_me_name, \
				mme.inCourseID AS inCourseID, \
				mme.outCourseID AS outCourseID, \
				tc.status AS t_contract_status, \
				tc.s_contract AS t_contract_s_contract, \
				tc.sid_corg, \
				tc.sid_dorg, \
				tc.sid_aorg, \
				tc.dfr_contract, \
				tc.dto_contract, \
				extractvalue(mo_c.xml_org, "//sid") AS corg_sid, \
				extractvalue(mo_c.xml_org, "//s_org") AS s_corg, \
				extractvalue(mo_c.xml_org, "//name") AS corg_name, \
				extractvalue(mo_c.xml_org, "//n_org") AS corg_nunber, \
				extractvalue(mo_d.xml_org, "//sid") AS dorg_sid, \
				extractvalue(mo_d.xml_org, "//s_org") AS s_dorg, \
				extractvalue(mo_d.xml_org, "//name") AS dorg_name, \
				extractvalue(mo_d.xml_org, "//n_org") AS dorg_number, \
				tc.name AS tc_name \
			FROM t_contract_me_attribute tcm \
				LEFT JOIN t_contract tc ON tcm.sid_morg = tc.sid_morg AND tc.sid = tcm.sid_contract \
				LEFT JOIN m_me mme ON tcm.sid_morg = mme.sid_morg AND tcm.sid_me = mme.sid \
				LEFT JOIN m_org mo_c ON tc.sid_morg = mo_c.sid_morg AND tc.sid_corg = mo_c.sid \
				LEFT JOIN m_org mo_d ON tc.sid_morg = mo_d.sid_morg AND tc.sid_dorg = mo_d.sid \
			WHERE tcm.sid_morg = ? AND tcm.s_upd < 3 AND tc.s_upd < 3 AND (mme.s_upd < 3 AND mme.status > 0); \
		'

		param = (sidMorg,)
		rows = self.once(query, param)
		if rows is None or len(rows) < 1:
			return None
		return rows
