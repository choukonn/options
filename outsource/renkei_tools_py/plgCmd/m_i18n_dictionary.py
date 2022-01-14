#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# m_i18n_dictionary

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

from collections import defaultdict

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sql as mySql
from .. import plgCommon as plgCmn

i18nMapLocale = plgCmn.i18nMapLocale
i18nCode = plgCmn.i18nCode


# i18n
def geti18nCodeMap(sidMorg, *, useLocale=None):
	i18nMapLocale[sidMorg] = {}
	i18nCode[sidMorg] = {}
	data = None

	def i18nMap(rows):
		if i18nMapLocale[sidMorg] is not None and len(i18nMapLocale[sidMorg]) < 1:
			data = defaultdict(lambda: defaultdict(set))
			# {locale:{code1:text1,code2:text2}}
			{data[k['locale_id']].update({k['code']:k['text']}) for k in rows}
			i18nMapLocale[sidMorg] = data

		if i18nCode[sidMorg] is not None and len(i18nCode[sidMorg]) < 1:
			data = defaultdict(list)
			# {code:[text1,text2,text3]}
			if useLocale is None:
				{data[k['code']].append(k['text']) for k in rows}
				i18nCode[sidMorg] = data
			else:
				{data[k['code']].append(k['text']) for k in rows if rows['locale_id'] == useLocale}
				i18nCode[sidMorg] = data

	try:
		query = 'call p_i18ndictionary("GET", ?, null);'
		param = (sidMorg,)
		rows = mySql.once(query, param)
		if rows is None:
			return None

		i18nMap(rows)

	except Exception as err:
		logger.debug(err)
		raise
	return
