#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import mysql.connector
import re
from datetime import datetime, date

# myapp
from .mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']

regPT1Tab = re.compile(r'[\t]+')

# TODO: https://codeday.me/jp/qa/20190420/655917.html
# Thanks to https://stackoverflow.com/a/1937636/2482744
def date_to_datetime(d):
	return datetime.combine(d, datetime.min.time())


def ensure_datetime(d):
	if isinstance(d, datetime):
		return d
	elif isinstance(d, date):
		return date_to_datetime(d)
	else:
		#raise TypeError('{} is neither a date nor a datetime'.format(d))
		return d


## SQL接続用のObj作成（仮）
def sql_session(dbConf):
	try:
		conn = mysql.connector.connect(
			host = dbConf['host'],
			port = dbConf['port'],
			user = dbConf['user'],
			password = dbConf['pass'],
			database = dbConf['dbName'],
			buffered = False,
			use_pure = True,				# prepaerd=TrueでのNotImplementedError対応
			charset = 'utf8mb4',
			collation = 'utf8mb4_general_ci',
			connection_timeout = int(dbConf['timeOut']),
		)
	except Exception as err:
		logger.debug(err)
		raise
	return conn

## fetchall
def once(query, param, **kwargs):
	cnx = None
	cur = None
	data = None
	result = None
	if query is None or len(query) < 1:
		eMsg = 'query is None'
		raise Exception(eMsg)
	query = regPT1Tab.sub(' ', query).strip()

	# 0:その他、1:UPDATE、2:INSERT
	mode = 0
	if re.search(r'^UPDATE ', query.upper()) is not None: mode = 1
	elif re.search(r'^INSERT ', query.upper()) is not None: mode = 2

	# datetime型を文字列にしようかと思ったけど。。。
	def convData(row):
		ret = None
		if type(row) == list:
			ret = []
			for line in row:
				data = tuple()
				for c in line:
					if type(c) == type(None):
						data = data + (None,)
					elif type(c) == str:
						data = data + ('{}'.format(c),)
					elif type(c) == datetime:
						data = data + ('{}'.format(c.strftime('%Y/%m/%d %H:%M:%S')),)
					elif type(c) == date:
						data = data + ('{}'.format(c.strftime('%Y/%m/%d')),)
					else:
						data = data + (c,)
				ret.append(data)
		elif type(row) == tuple:
			data = tuple()
			for c in row:
				if type(c) == type(None):
					data = data + (None,)
				elif type(c) == str:
					data = data + ('{}'.format(c),)
				elif type(c) == datetime:
					data = data + ('{}'.format(c.strftime('%Y/%m/%d %H:%M:%S')),)
				elif type(c) == date:
					data = data + ('{}'.format(c.strftime('%Y/%m/%d')),)
				else:
					data = data + (c,)
			ret = data
		return ret

	## preparedオプションを使うために、dictionaryオプションが無効となっている、そのためここでdict型に変換する
	def ret2dict(cur, result):
		ret = None
		if result is None or len(result) < 1: return ret
		#data = convData(result)
		data = result
		cLen = cur.rowcount
		if cLen > 0:
			tmp = None
			# ストアド内部でエラーになるとコードが返却されるので終わり
			if len(cur.column_names) == 1 and cur.column_names[0] == 'code':
				raise Exception('code:[{}], query:[{}], param:[{}]'.format(result, query, param))
			if type(data) == list:
				tmp = [dict(zip(cur.column_names, row)) for row in data]
				# DB上本来はdatetime型のカラムのはずが「00:00:00」のときだけpython側で受け取るとdate型に変換？されているため、date型は一律datetime型へと変換したものを格納する
				tmp2 = [{k: ensure_datetime(v) for k,v in item.items()} for item in tmp]
			elif type(data) == tuple:
				tmp = dict(zip(cur.column_names, data))
				tmp2 = {v: ensure_datetime(v) for k,v in tmp.items()}
			else:
				raise Exception('unknown sql data [{}]'.format(result))
			ret = tmp2
		return ret

	try:
		cnx = sql_session(mycnf['useDBconf'])
		if cnx.is_connected() is None:
			raise Exception('mysql connect error [{q}, {p}]'.format(q=query, p=param))
		cur = cnx.cursor(prepared=True)
	except Exception as err:
		logger.debug(err)
		raise

	try:
		if query is None:
			return result
		logger.debug('query:[{q}], param[{p}]'.format(q=query, p=param))
		if param is not None and len(param) > 0:
			cur.execute(query, param)
		else:
			cur.execute(query)

		# 1:UPDATE、2:INSERT
		if 1 <= mode <= 2:
			cnx.commit()
			# 実行前のrowcountは「-1」、UPDATE後は1行変更で「0」かも、ログ表示用に＋１する
			logger.debug('update row count: {rc}, query[{q}], param[{p}]'.format(rc=cur.rowcount, q=query, p=param))
		# 上記以外の場合、結果の取得を試みる
		else:
			result = cur.fetchall()
			data = ret2dict(cur, result)

	except mysql.connector.errors.DatabaseError as err:
		logger.debug('[{}], [{}], [{}]'.format(err, query, param))
		raise
	except Exception as err:
		logger.debug('[{}], [{}], [{}]'.format(err, query, param))
		raise
	finally:
		cur.close()

	try:
		if cnx.is_connected() is not None:
			cnx.close()
	except Exception as err:
		logger.debug(err)
		raise

	return data


class MySql(object):
	def __init__(self, url):
		self.url = url
		self.cnx = None
		self.cur = None

	def _open(self,):
		self.cnx = sql_session(mycnf.conf['useDBconf'])

	def _close(self,):
		pass

	def _execute(self,):
		pass

	def _executemany(self,):
		pass

	def _commit(self,):
		pass

