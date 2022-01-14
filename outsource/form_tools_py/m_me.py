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

# XMLMEから要素／項目／グループのsidとsid_criterionを抽出
def getXMLMEcriterion(xml):
	data = None
	try:
		meCriterion = defaultdict(lambda: defaultdict(set))
		xmlObj = cmn.getRow2Xml(xml)

		meCriterion['equipment'] = {xobj.find('s_equipment').text:xobj.find('count').text for xobj in xmlObj.findall('.//equipment')}
		meCriterion['ecourse'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//ecourse')}
		meCriterion['egroup'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//egroup')}
		meCriterion['eitem'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//eitem')}
		meCriterion['element'] = {xobj.find('sid').text:xobj.find('sid_criterion').text for xobj in xmlObj.findall('.//element')}
	except Exception as err:
		log('{}'.format(err), LOG_ERR)
		return None

	if len(meCriterion) > 0:
		data = {k:v for k,v in meCriterion.items()}

	return data
