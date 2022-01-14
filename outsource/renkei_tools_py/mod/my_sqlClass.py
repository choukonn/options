#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import mysql.connector
import re
import urllib.parse
from datetime import datetime, date
from collections import namedtuple

# myapp
from .mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
config_data = {}

regPT1Tab = re.compile(r'[\t]+')

# SQL文で直接INSERT/UPDATEを記述した場合の区別用
_QueryModeType = namedtuple('modeType', [
	'other',
	'update',
	'insert',
	'delete'
])
queryModeType = _QueryModeType(0, 1, 2, 3)

# 通常／バルクインサートの区別用
_ExecuteModeType = namedtuple('executeModeType', [
	'execute',
	'executemany'
])
executeMode = _ExecuteModeType(0, 1)


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


class Connecter(object):
	def __init__(self, config):
		self._config = config
		#self._cnx = None
		#self._cur = None

	def _createSession(self,):
		conn = None
		try:
			#url = urllib.parse.quote(config_data['mysql'], safe=':@/')					# 特殊文字を%xx形式にエスケープ（safeで指定した文字は対象外、文字、数字、および '_.-' も対象外）
			#url = urllib.parse.urlparse(url, scheme='mysql', allow_fragments=False)		# 分解
			#urlname = urllib.parse.unquote(url.username)								# エスケープしていた文字を戻す
			#urlpass = urllib.parse.unquote(url.password)


			#Log().dbg_log(url)
			conn = mysql.connector.connect(
				host = self._config['host'],
				user = self._config['user'],
				password = self._config['pass'],
				database = self._config['dbName'],
				# 暫定
				#host = 'localhost',
				#user = 'ddadmin',
				#password = '1anNw7j$',
				#database = 'dd_data_90007',		# /が含まれているため、2文字目から取得

				buffered = False,
				use_pure = True,				# prepaerd=TrueでのNotImplementedError対応
				charset = 'utf8mb4',
				collation = 'utf8mb4_general_ci',
				connection_timeout = 300
			)
		except Exception as err:
			logger.exception(err)
			raise

		return conn

	def _open(self,):
		try:
			cnx = self._createSession()
			if cnx.is_connected() is None:
				raise Exception('mysql connect error [{h}, {p}, {u}, {s}]'.format(h=self._config['host'], p=self._config['port'], u=self._config['user'], s=self._config['dbName']))
			cur = cnx.cursor(prepared=True)
		except Exception as err:
			logger.exception(err)
			raise
		return (cur, cnx)

	def _close(self, cur, cnx):
		try:
			if cur is not None:
				cur.close()
			if cnx is not None:
				cnx.close()
		except Exception as err:
			logger.exception(err)
			raise

	def _commit(self, cur, cnx, query, param):
		try:
			cnx.commit()
			# 実行前のrowcountは「-1」、UPDATE後は1行変更で「0」かも、ログ表示用に＋１する
			self.logger.debug('update row count: {rc}, query[{q}], param[{p}]'.format(rc=cur.rowcount, q=query, p=','.join(map(str, param))))
		except Exception as err:
			logger.exception(err)
			raise

	## preparedオプションを使うために、dictionaryオプションが無効となっている、そのためここでdict型に変換する
	def _ret2dict(self, cur, query, param, result):
		ret = None
		if result is None or len(result) < 1:
			return ret

		cLen = cur.rowcount
		if cLen > 0:
			tmp = None
			# ストアド内部でエラーになるとコードが返却されるので終わり
			if len(cur.column_names) == 1 and cur.column_names[0] == 'code':
				raise Exception('code:[{}], query:[{}], param:[{}]'.format(result, query, param))
			if type(result) == list:
				tmp = [dict(zip(cur.column_names, row)) for row in result]
				# DB上本来はdatetime型のカラムのはずが「00:00:00」のときだけpython側で受け取るとdate型に変換？されているため、date型は一律datetime型へと変換したものを格納する
				tmp2 = [{k: ensure_datetime(v) for k, v in item.items()} for item in tmp]
			elif type(result) == tuple:
				tmp = dict(zip(cur.column_names, result))
				tmp2 = {v: ensure_datetime(v) for k, v in tmp.items()}
			else:
				raise Exception('unknown sql data [{}]'.format(result))
			ret = tmp2

		return ret

	def _execute(self, queryMode, query, param):
		data = None
		result = None
		cur = None
		cnx = None
		try:
			cur, cnx = self._open()
			if param is not None and len(param) > 0:
				cur.execute(query, param)
			else:
				cur.execute(query)

			# UPDATE/INSERT
			if queryMode in [queryModeType.update, queryModeType.insert, queryModeType.delete]:
				self._commit(cur, cnx, query, param)
			# それ以外
			else:
				result = cur.fetchall()

			if result is not None and len(result) > 0:
				data = self._ret2dict(cur, query, param, result)
		except Exception as err:
			logger.exception(err)
			raise
		finally:
			self._close(cur, cnx)

		return data

	def _executeMany(self, queryMode, query, param):
		data = None
		result = None
		try:
			cur, cnx = self._open()
			# バルクインサート／アップデートは直接記述した場合のみ、ストアドは除外
			if queryMode not in [queryModeType.update, queryModeType.insert, queryModeType.delete]:
				self.logger.error('bulk inserts are for INSERT and UPDATE only')
			elif param is not None and len(param) > 0:
				cur.executemany(self.query, self.param)
			else:
				cur.executemany(self.query)

			# UPDATE/INSERT
			if queryMode in [queryModeType.update, queryModeType.insert, queryModeType.delete]:
				self._commit(cur, cnx, query, param)
			# それ以外
			else:
				result = cur.fetchall()

			if result is not None and len(result) > 0:
				data = self._ret2dict(cur, query, param, result)
		except Exception as err:
			logger.exception(err)
			raise
		finally:
			self._close(cur, cnx)

		return data



class Exceute(Connecter):
	def __init__(self, *, loggerChild=None, config=mycnf['useDBconf'], sidMorg=None, sidUpd=systemUserSid):
		if sidMorg is not None:
			self.sidMorg = sidMorg

		#self._query = None
		#self._param = None
		#self._result = None
		#self._execMode = None

		try:
			_config = mycnf['useDBconf']
			if config is not None:
				_config = config
				mycnf['useDBconf'] = config
			if loggerChild is not None:
				self.logger = loggerChild
			super().__init__(config=_config)

			# 更新者IDの指定
			if not hasattr(self, 'sidUpd'):
				if sidUpd is not None:
					self.sidUpd = int(sidUpd)
				else:
					self.sidUpd = int(systemUserSid)
			# システムのデフォルト以外が渡された場合
			elif sidUpd is not None and int(sidUpd) != int(systemUserSid) and self.sidUpd != int(sidUpd):
				self.sidUpd = int(sidUpd)

		except:
			raise

	def _qStringCheck(self, query):
		if query is None or len(query) < 1:
			raise Exception('Exceute error query string is None')

	def _qModeCheck(self, query):
		mode = None
		try:
			self._qStringCheck(query)
			# 0:その他、1:UPDATE、2:INSERT
			mode = queryModeType.other
			if re.search(r'^UPDATE ', query.upper()) is not None:
				mode = queryModeType.update
			elif re.search(r'^INSERT ', query.upper()) is not None:
				mode = queryModeType.insert
			elif re.search(r'^DELETE ', query.upper()) is not None:
				mode = queryModeType.delete
		except:
			raise
		return mode

	def _checkQ(self, query, param, execMode):
		# 長文クエリを直接記述した際、ログ表示すると鬱陶しいのでトリム
		_q = regPT1Tab.sub('\x20 ', query).strip()

		if execMode == executeMode.execute:
			_p = ','.join(map(str, param))
		elif execMode == executeMode.executemany:
			# TODO: （仮）バルクインサートする場合、パラメータ部が配列、かつ、最低1個は必要
			if param is None or not((type(param) == list or type(param) == tuple) and len(param) > 0):
				raise Exception('executemany requires parameter options')
			_p = ','.join(map(str, param[0]))
		else:
			raise Exception('unknwon execMode option, mode:[{}]'.format(execMode))
		msg = 'query:[{q}], param:[{p}]'.format(q=_q, p=_p)

		# バルクインサートの場合、件数表示を追加
		if execMode == executeMode.executemany:
			msg += ', data-len:[{}]'.format(len(param))
		self.logger.debug(msg)

		return _q

	def _exec(self, execMode, query, param):
		try:
			data = None
			_query = self._checkQ(query, param, execMode)
			queryMode = self._qModeCheck(_query)

			# 区別
			if execMode == executeMode.execute:
				data = self._execute(queryMode, _query, param)
			elif execMode == executeMode.executemany:
				data = self._executeMany(queryMode, _query, param)

		except Exception as err:
			# TODO: productionの時だけ
			if mycnf['envMode'] == 'production':
				self.logger.error('query:{q}, param:{p}', query, p=','.join(map(str, param)))
			self.logger.exception(err)
			raise

		return data

	def once(self, query, param):
		data = None
		execMode = executeMode.execute

		data = self._exec(execMode, query, param)
		return data

	def onceMany(self, query, param):
		data = None
		execMode = executeMode.executemany

		data = self._exec(execMode, query, param)

		return data
