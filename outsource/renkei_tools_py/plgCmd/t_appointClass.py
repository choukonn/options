#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# t_appoint
# クラス化してみたい

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)
import datetime

# myapp
from ..mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from ..mod import common as cmn
from ..mod import my_sqlClass as mySql

# t_appointステータス
tAppointSts = {
	# 予約
	'reservation': 0,
	# 受付
	'checkin': 1,
	# 判定
	'judgment': 2,
	# 確定
	'confirm': 3,
}

tAppointAct = {
	# 登録
	'register': 1,
	# 取り消し
	'cancel': 2,
}

# 予約変更区分
sReApo = {
	'day':			1,		# 日付変更
	'change':		2,		# 健診（内容）変更
	'cancelReg':	3,		# 受付キャンセル
	'canselApo':	4,		# 予約キャンセル
}



class Tappoint(mySql.Exceute):
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

	# t_appointとt_appoint_meの更新時刻だけを変更する
	def setTappointDtUpd(self, sidMorg, *, sidAppoint):
		try:
			dt_upd = datetime.datetime.strftime(datetime.datetime.now(), '%Y/%m/%d %H:%M:%S.%f')
			# t_appoint_me
			query = 'UPDATE t_appoint_me SET dt_upd = ? WHERE sid_morg = ? AND sid_appoint = ?;'
			param = (dt_upd, sidMorg, sidAppoint)
			rows = self.once(query, param)
			# t_appoint
			query = 'UPDATE t_appoint SET dt_upd = ? WHERE sid_morg = ? AND sid = ? AND (s_reappoint IS NULL OR s_reappoint < 4);'
			param = (dt_upd, sidMorg, sidAppoint)
			rows = self.once(query, param)
		except Exception as err:
			self.logger.debug(err, exc_info=True)
			raise
		return rows


	# t_appointとt_appoint_meのステータスを変更
	def setTappointStatus(self, sidMorg, *, sid_appoint, stsCode, sReappoint, apoDate):
		try:
			dt_upd = datetime.datetime.strftime(datetime.datetime.now(), '%Y/%m/%d %H:%M:%S.%f')
			# t_appoint_me
			query = 'UPDATE t_appoint_me SET s_upd = 2, dt_upd = ? WHERE sid_morg = ? AND sid_appoint = ?;'
			param = (dt_upd, sidMorg, sid_appoint)
			rows = self.once(query, param)
			# t_appoint
			query = 'UPDATE t_appoint SET s_upd = 2, status = ?, dt_appoint = ?, dt_upd = ?, s_reappoint = ? WHERE sid_morg = ? AND sid = ? AND (s_reappoint IS NULL OR s_reappoint < 4);'
			param = (stsCode, apoDate, dt_upd, sReappoint, sidMorg, sid_appoint)
			rows = self.once(query, param)
		except Exception as err:
			self.logger.debug(err, exc_info=True)
			raise
		return rows


	# 更新
	def setTappointPost(self, sidMorg, *, sidAppoint, apoStatus, sidMe=None, xmlMe=None, xmlCcard=None, xmlAppoint=None, remarks="", sidContract=None):

		try:
			# 引数                       1  2  3  4   5    6  7  8  9  10    11    12   13 14  15    16    17    18
			query = 'CALL p_appoint_post(?, ?, ?, ?, null, ?, ?, ?, ?, null, null, null, ?, ?, null, null, null, null);'
			param = (sidMorg, systemUserSid, sidAppoint, apoStatus, remarks, sidContract, sidMe, xmlMe, xmlCcard, xmlAppoint)
			rows = self.once(query, param)
		# FIXME: 国際版と国内版で引数の数が違う、国内版へのマージ＆テストする期間がたりないので仮対処
		#except mySql.mysql.connector.errors.ProgrammingError:
		# TODO: mysql5.5？5.6？だと上記例外が出ないので、全て対象にする。
		except Exception:
			self.logger.info(' **** retry query ****')
			try:
				# 引数                       1  2  3  4   5    6  7   8     9     10    11    12  13  14     15    16
				query = 'CALL p_appoint_post(?, ?, ?, ?, null, ?, ?, null, null, null, null, null, ?, null, null, null);'
				param = (sidMorg, systemUserSid, sidAppoint, apoStatus, remarks, sidContract, xmlCcard)
				rows = self.once(query, param)
			except Exception as err:
				self.logger.debug(err)
				raise
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# 新規
	def setTappointPut(self, sidMorg, *, vid, apoDt, sidExaminee, sidMe, xmlMe, xmlCcard, xmlAppoint=None, remarks="", sidContract=None):
		try:
			
			# query = 'CALL p_appoint_put(?, 1, ?, ?, ?, ?, ?, ?, null, null, null, ?, ?, null, null, null, null, ?);'
			# param = (sidMorg, apoDt, sidExaminee, remarks, sidMe, xmlMe, xmlCcard, vid)

			# 引数                      1  2  3  4  5   6  7  8   9     10    11  12 13  14    15    16    17   18
			query = 'CALL p_appoint_put(?, 1, null, null, "", null, null, null, null, null, null, null, null, null, null, null, null, ?);'
			param = (sidMorg, vid)
			# param = (sidMorg, apoDt, sidExaminee, remarks, sidContract, sidMe, xmlMe, xmlCcard, xmlAppoint, vid)
			rows = self.once(query, param)
		# FIXME: 国際版と国内版で引数の数が違う、国内版へのマージ＆テストする期間がたりないので仮対処
		#except mySql.mysql.connector.errors.ProgrammingError:
		# TODO: mysql5.5？5.6？だと上記例外が出ないので、全て対象にする。
		except Exception:
			self.logger.info(' **** retry query ****')
			# 引数                      1  2  3  4  5  6  7  8   9     10    11  12   13   14    15    16
			query = 'CALL p_appoint_put(?, 1, ?, ?, ?, ?, ?, ?, null, null, null, ?, null, null, null, null);'
			param = (sidMorg, apoDt, sidExaminee, remarks, sidContract, sidMe, xmlMe, xmlCcard)
			rows = self.once(query, param)
		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# チェックイン時に送信するストアド
	def checkinPost(self, sidMorg, *, visitId, apoDay=None, sidExaminee=None):

		# ストアド引数
		# IN	IN_sid_morg			INT UNSIGNED,	1
		# IN	IN_sid_upd			INT UNSIGNED,	2
		# IN	IN_sid_appoint		INT UNSIGNED,	3
		# IN	IN_remarks			VARCHAR(255),	4
		# IN	IN_xml_ccard		MEDIUMTEXT,		5
		# IN	IN_xml_appoint		MEDIUMTEXT		6

		try:
			rows = self.getTappoint(sidMorg, vid=visitId, cid=None, apoDay=apoDay, refDate=None, sidExaminee=sidExaminee)
			# TODO: visitId以外で検索すると複数ヒットする可能性があるが、無視して1件目を強制採用
			tAppoint = rows[0]
		except:
			raise

		try:
			sidAppoint = tAppoint['sid']
			reMarks = tAppoint['remarks']
			xmlCcard = tAppoint['xml_ccard']
			xmlAppoint = tAppoint['xml_appoint']

			# 引数                       1  2  3  4  5  6
			query = 'CALL p_checkin_post(?, ?, ?, ?, ?, ?);'
			param = (sidMorg, systemUserSid, sidAppoint, reMarks, xmlCcard, xmlAppoint)
			rows = self.once(query, param)

		# FIXME: 国際版と国内版で引数の数が違う、国内版へのマージ＆テストする期間がたりないので仮対処
		#except mySql.mysql.connector.errors.ProgrammingError:
		# TODO: mysql5.5？5.6？だと上記例外が出ないので、全て対象にする。
		except Exception:
			self.logger.info(' **** retry query ****')
			# 引数                       1  2  3  4  5
			query = 'CALL p_checkin_post(?, ?, ?, ?, ?);'
			param = (sidMorg, systemUserSid, sidAppoint, reMarks, xmlCcard)
			rows = self.once(query, param)

		except Exception as err:
			self.logger.debug(err)
			raise
		return rows


	# t_appointに登録済みなのかチェックし、存在したらSELECTの結果を返却
	# getTappoint(sidMorg=sidMorg, vid=visitid, cid=karuteid, apoDay=examDate, refDate=refDate, sidExaminee=sid_examinee)
	def getTappoint(self, sidMorg, *, vid=None, cid, apoDay, refDate=None, sidExaminee):
		# visitidがない場合はカルテIDと予約日で検索する
		# 基準日(refDate)を指定した場合、その日を含め、未来を検索する

		# ストアド引数
		# IN sidMorg INT UNSIGNED,				-- (1): 医療機関番号
		# IN vid VARCHAR(30),					-- (2): visitId
		# IN cid VARCHAR(20),					-- (3): カルテID
		# IN apoDay VARCHAR(10),				-- (4): 予約日(YYYY/MM/DD)、基準日と同時指定された場合は予約日最優先
		# IN refDay VARCHAR(10),				-- (5): 基準日(YYYY/MM/DD)、この日を含めて、未来を検索対象とする
		# IN apoSidExaminee INT UNSIGNED		-- (6): sid_examinee

		try:
			query = 'CALL p_searchTappoint(?, ?, ?, ?, ?, ?);'
			param = (sidMorg, vid, cid, apoDay, refDate, sidExaminee)
			rows = self.once(query, param)
			if rows is None:
				# 検索にヒットしない
				return None
		except Exception as err:
			self.logger.debug(err)
			raise

		return rows

	# t_appointの予約SIDを返却
	# getSidAppoint(sidMorg=sidMorg, vid=visitid, cid=karuteid, apoDay=examDate)
	def getSidAppoint(self, sidMorg, vid=None, cid=None, apoDay=None, refDate=None, yoyakuFlg=0):
		# visitidがない場合はカルテIDと予約日で検索する
		# 基準日(refDate)を指定した場合、指定日の前後1ヶ月で検索

		# ストアド引数
		# IN sidMorg INT UNSIGNED,				-- (1): 医療機関番号
		# IN vid VARCHAR(30),					-- (2): visitId
		# IN cid VARCHAR(20),					-- (3): カルテID
		# IN apoDay date,						-- (4): 予約日(YYYY-MM-DD)、基準日と同時指定された場合は予約日最優先
		# IN refDay date,						-- (5): 基準日(YYYY-MM-DD)、指定日の前後1ヶ月を取得
		# IN yoyaku_flg INT,					-- (6): 予約フラグ(YYYY-MM-DD)、予約フラグ(予約ステータスを検索対象に含む1、含まない0)

		try:
			sid_appoint = 0
			# 2020/4/7時点は成田病院限定で、前後1カ月の近い日付を持ってくる
			# 検索した結果、親のsid情報を持っている場合はそちらの結果を返却する
			if sidMorg == '90007':
				query = 'SELECT f_get_appoint_sid3(?, ?, ?, ?, ?, ?) as sid_appoint;'
			# 成田以外は説明文通り
			else:
				query = 'SELECT f_get_appoint_sid2(?, ?, ?, ?, ?, ?) as sid_appoint;'
			param = (sidMorg, vid, cid, apoDay, refDate, yoyakuFlg)
			rows = self.once(query, param)
			if rows is None:
				# 検索にヒットしない
				return None

			sid_appoint = rows[0]["sid_appoint"]
		except Exception as err:
			self.logger.debug(err)
			raise

		return sid_appoint


	# 予約取り消し
	def cancelTappoint(self, sidMorg, *, tAppointRow, appoSts=None):
		retSts = False
		retFlag = 0
		changeSts = []

		if type(appoSts) != list and type(appoSts) != tuple:
			changeSts.append(appoSts)
		else:
			changeSts = appoSts

		if changeSts is None or len(changeSts) < 1:
			# ステータス未指定
			return None

		try:
			xmlCcard = tAppointRow['xml_ccard']
			for sts in changeSts:
				# 受付－＞予約－＞取り消し（削除）とやらないと、p_appoint_postのストアドでキャンセルできない。受付－＞取り消し(削除)と一気に飛ばすことは無理
				rows = self.setTappointPost(sidMorg=sidMorg, sidAppoint=tAppointRow['sid'], apoStatus=sts, xmlCcard=xmlCcard, remarks=tAppointRow['remarks'])
				if rows[0]['sid'] == tAppointRow['sid']:
					retFlag += 1
			if retFlag == len(changeSts):
				retSts = True
		except Exception as err:
			self.logger.debug(err)
			raise

		return retSts


	# カルテIDと期間を指定した検索
	def serachAppointPeriod(self, sidMorg, *, karuteId=None, refDate=None, dayAfter=60, dayAgo=10, stsFlagStart=0, stsFlagEnd=1, ignoreCourse=[]):
		if sidMorg is None or karuteId is None or refDate is None: return None
		# ステータス３以上のものは・・・
		if stsFlagStart >= tAppointSts['confirm'] or stsFlagEnd >= tAppointSts['confirm']: return None

		data = []

		# 無視リスト
		ignoreSidMe = None
		if ignoreCourse is not None and type(ignoreCourse) == list and len(ignoreCourse) > 0:
			ignoreSidMe = ','.join(map(str, ignoreCourse))

		# 検索開始日：終了日
		_after = refDate - datetime.timedelta(days=dayAfter)
		_ago = refDate + datetime.timedelta(days=dayAgo)
		after = _after.strftime('%Y-%m-%d 00:00:00')
		ago = _ago.strftime('%Y-%m-%d 23:59:59')

		query = 'SELECT \
				ta.sid_morg, \
				ta.sid_upd, \
				ta.dt_upd, \
				ta.s_upd, \
				ta.sid, \
				ta.status, \
				ta.dt_appoint, \
				ta.sid_examinee, \
				ta.n_appoint, \
				ta.s_reappoint, \
				ta.xml_examinee, \
				ta.xml_xorg, \
				ta.xml_ccard, \
				ta.xml_appoint, \
				ta.visitid, \
				EXTRACTVALUE(ta.xml_examinee, "//id") AS karuteId, \
				apome.sid_contract, \
				apome.sid_me, \
				apome.xml_me, \
				apome.name_me \
			FROM t_appoint ta \
				JOIN t_appoint_me apome ON ta.sid_morg = apome.sid_morg AND ta.sid = apome.sid_appoint AND ta.s_upd < 3 AND (ta.s_reappoint < 4 OR ta.s_reappoint IS NULL) AND ta.dt_appoint BETWEEN ? AND ? \
			WHERE ta.sid_morg = ? AND EXTRACTVALUE(ta.xml_examinee, "//id") = ?'
		param = (after, ago, sidMorg, karuteId)

		# 無視したいsidmeを指定
		if ignoreSidMe is not None:
			query += ' AND NOT FIND_IN_SET(apome.sid_me, ?)'
			param += (ignoreSidMe,)

		try:
			rows = self.once(query, param)
			if rows is None:
				# 検索にヒットしない
				self.logger.info('[{sidMorg}] karuteID: {id} not found in t_appoint, day range: "{d1} - {d2}", status range: "{s1} - {s2}"'.format(sidMorg=sidMorg, id=karuteId, d1=str(after), d2=str(ago), s1=stsFlagStart, s2=stsFlagEnd))
				return None

			# TODO: ステータス（予約／受付／判定済み／確定）チェックはプログラムで行って、対象外がわかりやすいようにログ出力を行う
			for row in rows:
				_status = row['status']
				_visitid = row['visitid']
				_karuteId = row['karuteId']
				_sidAppont = row['sid']
				_sidExaminee = row['sid_examinee']
				_dtAppoint = str(row['dt_appoint'])
				if stsFlagStart <= _status <= stsFlagEnd:
					data.append(row)
				else:
					self.logger.info('not applicable because status is out of range, status: {sts}, dtAppoint: {apoDay}, karuteId: {id}, sidAppoint: {sid}, visitid: {visitid}, sidExaminee: {sidExam}'.format(
						sts = _status,
						apoDay = _dtAppoint,
						id = _karuteId,
						sid = _sidAppont,
						visitid = _visitid,
						sidExam = _sidExaminee
						)
					)
					continue

		except Exception as err:
			self.logger.debug(err)
			raise

		return data
