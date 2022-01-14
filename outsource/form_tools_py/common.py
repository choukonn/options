#!/usr/bin/python3

# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

import os
import io
import sys
import traceback
import signal
import tempfile
import inspect

import csv
import pathlib as pl
import mysql.connector
import urllib.parse
import json
import collections
import base64
import unicodedata
import argparse
from operator import itemgetter, attrgetter
import xml.etree.ElementTree as ET
import xmltodict
import math
import datetime
import re

import form_tools_py.conf as conf
config_data = {}

sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# デバッグ専用: 関数の単純な実行時間を計測
# 1: http://nihaoshijie.hatenadiary.jp/entry/2017/10/21/231616
# 2: http://st-hakky.hatenablog.com/entry/2018/01/26/214255
from functools import wraps
import time
def measure(func):
	@wraps(func)
	def wrapper(*args, **kargs):
		start = time.time()
		result = func(*args,**kargs)
		execution_time =  time.time() - start
		Log().log(f'{func.__name__}: {execution_time:.3f}', LOG_INFO)
		return result
	return wrapper

# 和暦確認用
wareki = {
	20190501: {'gengo': '令和',},
	19890108: {'gengo': '平成',},
	19261225: {'gengo': '昭和',},
	19120730: {'gengo': '大正',},
	18680125: {'gengo': '明治',}
}

####
LOG_NOTICE = conf.LOG_NOTICE
LOG_INFO = conf.LOG_INFO
LOG_WARN = conf.LOG_WARN
LOG_ERR = conf.LOG_ERR
LOG_DBG = conf.LOG_DBG
LOG_ALL = conf.LOG_ALL
LOG_DEF = conf.LOG_DEF

abst_code = conf.abst_code
sort_code = conf.sort_code
form_code = conf.form_code
ret_code = conf.ret_code
####

class Log:
	def __init__(self,):
		self.examData = ''
		self.msg = ''
		self.out_msg = ''
		self.title = {
			LOG_ALL:'[dev]:',
			LOG_DBG:'[debug]:',
			LOG_ERR:'[error]:',
			LOG_WARN:'[warning]:',
			LOG_INFO:'[info]:',
			LOG_NOTICE:'[notice]:'
			}
		self.level = conf.LOG_DEF
		if os.getenv('NODE_ENV') != 'production':	# とりあえず出したいなら適当な判定にする
			self.level = conf.LOG_DBG

	def examinee(self,):
		self.exam = 'sid: {}, sid_examinee: {}, id: {}, day: {}'.format(conf.examInfo['sid'], conf.examInfo['sid_examinee'], conf.examInfo['id'], conf.examInfo['appoint_day'])
		log =  '[' + self.exam + ']: '
		return log

	def msg2str(self, in_msg, lv=LOG_NOTICE):
		if lv >= LOG_WARN:
			self.examData = self.examinee()
		else:
			self.examData = ''

		if type(in_msg) == str:
			self.out_msg = in_msg
		else:
			self.out_msg = str(in_msg)

		log = self.examData + self.out_msg.strip()

		return log

	# jsの標準入力にいれたいときだけ使う
	def msg2js(self, log_msg):
		self.msg = self.msg2str(log_msg)

		if len(self.msg) > 1:
			sys.stdout.write(self.msg + '\n')
			sys.stdout.flush()

	# 通常ログは標準エラー出力に流す
	def log(self, log_msg='', lv=LOG_NOTICE):
		if lv <= self.level:	# デフォルト以下であれば出力
			self.msg = self.msg2str(log_msg, lv)
			title = self.title[lv]
			if len(self.msg) > 1:
				sys.stderr.write(title + ' ' + self.msg + '\n')
				sys.stderr.flush()

	# デバッグログは標準エラーに流し込む
	# printデバッグ用。とにかく出力する
	def dbg_log(self, log_msg='', lv=LOG_ALL):
		if lv <= LOG_ALL:
			funcName = str(inspect.stack()[1][3])		# 呼び出し元の関数名
			funcLine = str(inspect.stack()[1].lineno)
			dbg_msg = self.title[LOG_DBG] + ' (' + funcName + ':' + funcLine + '): '
			self.msg = self.msg2str(log_msg, lv)
			if len(self.msg) > 1:
				sys.stderr.write(dbg_msg + self.msg + '\n')
				sys.stderr.flush()

# ファイルのフルPATHを渡す
def file_del(tmp_path):
	file_path = None

	if tmp_path is None:
		# 何もしない
		return

	# 文字列はpathlibのオブジェクトに変換
	if type(tmp_path) == str:
		tmp_file_path = pl.PurePath(tmp_path)
		file_path = pl.Path(tmp_file_path)
	# pathlibの名前を変えてるので、「pl」になっているtype()で確認するとpathlib.PosixPathである
	elif type(tmp_path) == pl.PosixPath:
		file_path = tmp_path
	else:
		Log().log('file path is unkown type, check path=[{}]'.format(tmp_path))

	if file_path is not None and file_path.exists() and file_path.is_file:	# 存在チェック
		file_path.unlink()

#
# ret = ['status': int, 'msg': str, 'cnx': mysql.conn~]
#		1: status: ret_codeで定義されているKEYの名称を渡す
#		2: msg: 出力したいテキスト
#		3: cnx: MySQLのセッション情報
def _exit(*args):
	ret = {'status': ret_code['die'], 'msg': "die", 'cnx': None}

	if len(args) == 1:
		ret = {'status': ret_code[args[0]],'msg': None, 'cnx': None}
	elif len(args) == 2:
		ret = {'status': ret_code[args[0]],'msg': args[1], 'cnx': None}
	elif len(args) == 3:
		ret = {'status': ret_code[args[0]],'msg': args[1], 'cnx': args[2]}

	# mysqlのセッション閉じる
	if ret['cnx'] is not None and type(ret['cnx']) == mysql.connector.connection_cext.CMySQLConnection:
		ret['cnx'].close()

	# メッセージ出力
	if ret['msg'] is not None:
		# js側で標準出力を解析しているので、渡すのは本当に必要なものだけ
		if conf.examInfo['sid'] is not None and len(conf.examInfo['sid']) > 0:
			exam_info = 'sid: {}, sid_examinee: {}, id: {}, day: {}'.format(conf.examInfo['sid'], conf.examInfo['sid_examinee'], conf.examInfo['id'], conf.examInfo['appoint_day'])
		else:
			# sidがなければデータなし
			exam_info = 'no exam data'
		if ret['status'] == 0:
			ret_msg = "[PY-INFO] " + ret['msg'] + "\n"
			sys.stdout.write(ret_msg)
			sys.stdout.flush()
		elif ret['status'] > 0 and ret['status'] < 100:
			ret_msg = "[PY-WARNING] " + '[' + exam_info + ']: '
			ret_msg += ret['msg'] + "\n"
			sys.stderr.write(ret_msg)
			sys.stderr.flush()
		else:
			ret_msg = "[PY-ERROR] " + '[' + exam_info + ']: '
			ret_msg += ret['msg'] + "\n"
			sys.stderr.write(ret_msg)
			sys.stderr.flush()

	# sys.exitは必ず例外を吐いて終了する。デバッガを使うとここで止まるが気にするな
	# ステータスコードを返すために使用する必要がある
	sys.exit(ret['status'])
	#exit(ret['status'])


def handler_exit(signal, frame):
	Log().log('signal: {}'.format(str(signal)), LOG_WARN)
	_exit('signal')


def traceback_log(err):
	sys_info = sys.exc_info()
	tb_info = traceback.format_tb(sys_info[2])
	msg = '"tracebak: {}'.format(tb_info)
	msg += '\nmsg: [{}]"'.format(err)
	_exit('die', msg.replace('\\n','\n'))


# デバッグ用
# pythonが使用したメモリ情報ではなく、この関数が実行された時点のOSのメモリ情報を取得
def memory_log():
	if os.getenv('NODE_ENV') != 'production':
		import psutil		# これのインストールが別途必要
		memory = psutil.virtual_memory()
		Log().log('memory info: {0}'.format(memory))


# base64でエンコードされた文字列データをデコードしてjson形式で返す
def b64dec2json(b64enc):
	if b64enc is None or type(b64enc) != str:
		return None

	try:
		b64dec = base64.b64decode(b64enc)
	except Exception as err:
		_exit('error', 'b64decode error: {}'.format(err))
	try:
		data = json.loads(b64dec)
	except Exception as err:
		_exit('error', 'json load error: {}'.format(err))

	return data

# jsから渡される引数の再構築
# デバッグ用に引数を渡せば単独で動かせるように引数解析のモジュールを使用する
def args2config(argv):
	dbg_log = Log().dbg_log
	log = Log().log

	global config_data		# グローバルに突っ込む必要あり

	log(__name__ + ': Analysis of arguments')

	# パーサーを作る
	parser = argparse.ArgumentParser(
		prog = 'export_form_data',			# プログラム名
		usage = 'output csv file',			# プログラムの利用方法
		description = 'description',		# 引数のヘルプの前に表示
		epilog = 'end',						# 引数のヘルプの後で表示
		add_help = False,					# -h/–help オプションの追加
	)
	# 引数追加
	parser.add_argument('-J', action='store')		# base64でエンコードした文字列を渡す(中身はJSON形式)
	parser.add_argument('-j')		# json形式
	parser.add_argument('-l')		# list形式(テキスト形式)
	parser.add_argument('-f')		# json形式のテキストファイルを渡す
	parser.add_argument('-F')		# base64でエンコードされた文字列のテキストファイルを渡す（中身はjson形式）

	# 引数を解析する
	#dbg_log('args: ' + str(argv))
	args = parser.parse_args()

	config = None

	if args.J:
		# base64でエンコードされている前提でデコードする
		log(__name__ + ' :base64enc:' + args.J, LOG_DBG)	# デコード前の文字列を表示
		config = b64dec2json(args.J)
	elif args.j:
		config = json.loads(args.j)
	# FIXME: list型を変換したい場合とか、手動でどうにかしたい場合ここを修正／再利用する
	elif args.l:
		if type(args.l) == list:
			config = {}
			tmp1 = []
			tmp2 = []
			tmp_word = args[0].replace('"','')
			word = tmp_word.split(',')
			for item in word:
				tmp = item.split(':', 1)
				tmp1.append(tmp[0])
				tmp2.append(tmp[1])

			config = dict(zip(tmp1,tmp2))
		else:
			_exit('error', 'error args: type[{0}]'.format(type(args.l)))
	elif args.f is not None or args.F is not None:	# ファイルで受け取る必要があればここに
		tmp_file = None
		if args.f is not None: tmp_file = pl.PurePath(args.f)
		elif args.F is not None: tmp_file = pl.PurePath(args.F)
		if tmp_file is None: _exit('error', 'args.F or args.f')
		config_path = pl.Path(tmp_file)
		dbg_log(config_path)
		if config_path is not None and config_path.exists() and config_path.is_file:	# 存在チェック
			try:
				with open(config_path.resolve(), mode='r', encoding='UTF-8') as f:
					line = f.read()
					if args.f is not None: config = json.loads(line)
					elif args.F is not None: config = b64dec2json(line)
			except Exception as err:
				_exit('error', 'config file error, name: {}, msg:{}'.format(str(config_path.resolve()), err))
		else:
			_exit('error', 'config file not found')

	else:
		_exit('error', 'error args: unregistered option')

	config['NODE_ENV'] = os.getenv('NODE_ENV', 'dev')	# ローカル環境はNODE_ENVが設定されていないのが多いためPYTHON内で使うように適当な初期値を入れておく

	# 帳票用のヘッダ作成フラグ
	config['dd_header_flag'] = '1'

	# m_userがない場合、初期値をいれておく
	if 'm_user' not in config:
		config['m_user'] = '0'		# 0:存在しない、あくまでも判定用のための初期値、 健診アカウントは「1」である

	if len(config['sort_condition']) == 0:		# ソート条件が空の場合、日付ソートをデフォで行う
		config['sort_condition'][sort_code['date']] = {'key':'Date', 'direction':1, 'priority':1}

	conf.config_data = config_data = config

	# デバッグ用にログ表示するコンフィグからパスワードを隠す
	printConfig = json.loads(json.dumps(config, ensure_ascii=False))
	printConfig['mysql'] = 'mysql://USER:PASSWD@HOST/SCHEMA'
	log('config: {0}'.format(json.dumps(printConfig, ensure_ascii=False)))

	# 解析用に抽出条件とソート条件は常にログに出力
	log('form number: {}'.format(config['s_print']))
	log('Extraction condition: {}'.format(config['abst_condition']))			# 抽出条件
	log('Sort condition: {}'.format(config['sort_condition']))					# ソート条件

	return config_data

# 和暦チェック用
# 引数はYYYYMMDD
# 戻り値は「元号」,「年」
def warekiCheck(dateYmd):
	if dateYmd is None or len(dateYmd) < 1: return None, None
	gengo = None
	gengoY = None
	for ymd in sorted(wareki.keys(), reverse=True):
		if gengo is None and int(dateYmd) >= ymd:
			gengo = wareki[ymd]['gengo']
			gengoY = str(int(dateYmd[:4]) - (int(str(ymd)[:4]) - 1))

	return gengo, gengoY

# SQLで取得したsm_morgのXMLをdict変換してconfに突っ込んでおく
# 戻り値はbool
def getXmlCstmInfo(row):
	ret = False
	xml = getRow2Xml(row)
	if xml is None or len(xml) < 1: return False
	try:
		xmldict = xmltodict.parse(row)
		#outsource_config = json.dumps(xmldict, ensure_ascii=False)
		conf.xml_cstminfo = xmldict
		ret = True
	except Exception as err:
		Log().log(err, LOG_ERR)

	return ret

# SQLで取得したm_outsourceのXMLを変換してグローバル変数に突っ込んでおく
# 返却するのはXML
def getXmlOutsource(row):

	xml = getRow2Xml(row)
	overWriteFlag = False

	try:
		xmldict = xmltodict.parse(row)
		#outsource_config = json.dumps(xmldict, ensure_ascii=False)
		if conf.outsource_config is None or len(conf.outsource_config) > 0:
			overWriteFlag = True
			confOld = conf.outsource_config['root']['outsource']
			confNew = xmldict['root']['outsource']
			# TODO: 複数回この関数を呼んだ場合都度マージを行う。ただし、完全に差分更新される訳ではないことに注意。
			for key1 in confNew.keys():
				key1List = list(confNew[key1].keys()) if type(confNew[key1]) == collections.OrderedDict else [key1]
				for key2 in key1List:
					if key1 in confOld and type(confOld[key1]) != type(None) and key1 != key2 and key2 not in confOld[key1]:
						try:
							confOld[key1][key2] = {**confOld[key1][key2], **confNew[key1][key2]}
						except:
							confOld[key1][key2] = confNew[key1][key2]
					elif key1 in confOld and type(confOld[key1]) != type(None) and key2 in confOld[key1]:
						key2List = list(confNew[key1][key2].keys()) if type(confNew[key1][key2]) == collections.OrderedDict else [key2]
						for key3 in key2List:
							if key2 in confOld[key1] and type(confOld[key1][key2]) != type(None) and key2 != key3 and key3 not in confOld[key1][key2]:
								try:
									confOld[key1][key2][key3] = {**confOld[key1][key2][key3], **confNew[key1][key2][key3]}
								except:
									confOld[key1][key2][key3] = confNew[key1][key2][key3]
							elif key2 == key3:
								confOld[key1][key2] = confNew[key1][key2]
					elif key1 in confOld and confOld[key1] is None and confNew[key1] is not None:
						try:
							confOld[key1] = confNew[key1]
						except:
							pass
					elif key1 not in confOld:
						try:
							confOld[key1] = {**confOld[key1], **confNew[key1]}
						except:
							confOld[key1] = confNew[key1]
					elif key1 == key2:
						confOld[key1] = confNew[key1]
					else:
						Log().log('outsurce not merge [key1:{}][key2:{}]'.format(key1, key2), LOG_ERR)

		if overWriteFlag == False:
			conf.outsource_config = xmldict

	except Exception as err:
		Log().log(err, LOG_ERR)

	# 性別／年齢等の変換情報は直接持たせておく
	conf.convert_option = outsource_dict('condition/convert_option')

	return xml

# 取得済みのm_outsourceのdictをごにょっとする
# かつ、ソートで使用するデータのkeyに検索で使用する名前を入れる
def outsource_dict(searchKey, searchType=None):
	data = {}
	# 多言語フラグ
	f_translation = None
	if 'convert_option' in conf.outsource_config['root']['outsource']['condition'] and 'f_translation' in conf.outsource_config['root']['outsource']['condition']['convert_option']:
		f_translation = conf.outsource_config['root']['outsource']['condition']['convert_option']['f_translation']

	# m_outsourceの辞書から引くデータを確定させる
	# data = {itemList[k] : xmlMeSid['elements'][k]['result'].get('value') for k in itemList if k in xmlMeSid['elements']}
	keyList = searchKey.split('/')
	try:
		outsource = conf.outsource_config['root']['outsource']
		for key in keyList:
			outsource = outsource[key]
	except Exception:
		return None


	if searchType is not None:
		# エクセルマクロ向けCSV用のフラグ色々
		if 'xls_csv_flag' == searchType:
			if 'f_use' in outsource:
				data = {'xls_break_use':outsource['f_use']['#text'], 'xls_break_line':outsource['f_use']['@line'], 'xls_break_str':outsource['f_use']['@br_str']}

	# 検査項目、問診、治療中、受診対象項目とか、名前空間を使ってるものを解析、抽出
	elif 'item' in outsource:
		if type(outsource['item']) == list:
			# list化されている
			data = {k['@sid']:k['#text'] for k in outsource['item']}
		else:
			# 1個の場合
			data = {outsource['item']['@sid']:outsource['item']['#text']}
		if '#text' in outsource and outsource['#text'] is not None:
			data.update({'title':outsource['#text']})
		# 多言語対応用
		if f_translation is not None and f_translation != '0':
			i18n_data = {}
			for k in outsource['item']:
				if 'trans' in k:
					if type(k['trans']) == list:
						# list化されている
						i18n = {k['@sid']:{kk['@val']:kk['#text'] for kk in k['trans']}}
					else:
						i18n = {k['@sid']:{k['trans']['@val']:k['trans']['#text']}}
					i18n_data.update(i18n)
			if len(i18n_data) > 0:
				data.update({'i18n':i18n_data})

	# それ以外
	else:
		#data = {k:outsource[k] for k in outsource if type(outsource[k]) == str}
		for key in outsource:
			if type(outsource[key]) == str:
				data.update({key:outsource[key]})
			elif type(outsource[key]) == collections.OrderedDict:
				data[key] = dict(outsource[key])

	return data


# フィルタアイテムの取得
def outsource_filter_dict(xml, search_path, sprint_code):

	od_dict_item_tag = collections.OrderedDict()
	od_dict_item_name = collections.OrderedDict()

	tmp_name1 = None
	tmp_name2 = None

	# xmlの仕様として、要素名の頭に数字や記号が使えないので、f200319(例)という形で登録している
	# (例)outsource/filters/f200319 というXMLを解析する
	search_path = search_path + '/' + conf.form_num_prefix + sprint_code

	search_item = xml.findall(search_path)
	if search_item is None or len(search_item) == 0:			# 検索対象のXMLが見つからない
		#func_exit('xml_error', "{0} not found".format(search_path))
		return None, None

	item_num = len(search_item[0])

	tmp_tag1 = [None for i in range(item_num)]
	tmp_tag2 = [None for i in range(item_num)]

	# TODO: XMLの構造は固定と仮定して順番通りに取得すると並びが固定できるかも？
	# ダメならindex貼ってソートかけるとかしないとだめかもしれない
	for i in range(item_num):	# 0-index
		num = i
		# key/valを格納
		if search_item[0][num].tag == 'item':
			tmp_tag1[num] = search_item[0][num].attrib['sid']
		else:
			tmp_tag1[num] = search_item[0][num].tag
		if 'name' in search_item[0][num].attrib:	# 変換後の名前
			tmp_name1 = search_item[0][num].attrib['name']
		else:
			tmp_name1 = search_item[0][num].text

		tmp_name2 = search_item[0][num].text
		tmp_tag2[num] = search_item[0][num].text

		od_dict_item_tag[tmp_tag1[num]] = tmp_tag2[num]
		od_dict_item_name[tmp_name2] = tmp_name1

	dict_item_tag = dict(zip(tmp_tag1, tmp_tag2))		# データ取得時のフィルタチェックで使用する
	#dict_item_name = dict(zip(tmp_name1, tmp_name2))	# 最終のデータ出力チェックで使用する

	return dict_item_tag, od_dict_item_name



# list型に追加(連結)して、連結後のlistを返す
# FIXME: 考慮不足
def head_add(src, dst):
	if src is None or len(src) < 1: return dst			# srcが無ければ何もせずにdst(元データ)を返却
	tmp = []
	tmp_list = []
	cnt = len(dst)
	if type(src) == dict:
		d = {}
		for word in src:
			#Log().dbg_log(' ** LOG: {0}'.format(s))
			cnt += 1
			d.update({src[word]:cnt})
			dst.update(d)
			#tmp.append(word)
		return dst
	elif type(src) == list:
		tmp.extend(src)
	elif type(src) == str:
		sp_src = src.split(',')
		tmp.extend(sp_src)
	else:
		tmp.append(src)

	tmp_list.extend(dst)
	tmp_list.extend(tmp)

	return tmp_list

# 年齢の計算
# 戻り値: 年齢
# 参考：https://teratail.com/questions/138394
def age_calculation(appoint_day, birthday):
	nendomatsuFlag = False
	# 協会けんぽは（４月１日）時点での年齢が求められるので調整が必要
	if config_data['s_print'] in [conf.form_code['kyoukaikenpo']]: nendomatsuFlag = True

	try:
		appoint_day = appoint_day.replace('-','/')
		birthday = birthday.replace('-','/')
		appo_day = datetime.datetime.strptime(appoint_day, '%Y/%m/%d').date()
		birth_day = datetime.datetime.strptime(birthday, '%Y/%m/%d').date()
		nendoYear = appo_day.year
		if nendomatsuFlag == True:
			# 誕生日が１月１日～４月２日未満の間は年度を加算しない
			if (1, 1) <= (birth_day.month, birth_day.day) < (4, 2):
				nendoYear += 1
		age = nendoYear - birth_day.year
		if nendomatsuFlag == False:
			# 予約日 > 誕生日：誕生日はまだ迎えていない
			# 予約日 <= 誕生日：迎えている
			if (appo_day.month, appo_day.day) <= (birth_day.month, birth_day.day):
				age -= 1
		elif nendomatsuFlag == True:
			# 予約日が１月１日～４月２日未満の間は年齢を減算する
			if (1, 1) <= (appo_day.month, appo_day.day) < (4, 2):
				age -= 1

	except Exception as err:
		Log().log('age calc faild, msg:{}'.format(err), LOG_ERR)
		return None

	return age

# dictから一致するものだけlistに追加
# TODO: listの中の順番は保証されない。没案かも
def dictval2list(csv_header, dict_name, list_name):
	if dict_name is not None:
		for key in dict_name:
			if key in csv_header:
				idx = csv_header.index(key)
				list_name[idx] = dict_name[key]

# 抽出条件、ソート条件をコンフィグから検索
# 戻り値はkeyに対応するvalue、かつ、文字列ならlist化を行って返却する
def search_abst_sort_cond(key):
	ret = None

	if key in config_data['abst_condition']:
		# 抽出条件は文字列で返すように明示的に指定
		ret = str(config_data['abst_condition'][key]) if len(str(config_data['abst_condition'][key])) > 0 else None
	elif  key in config_data['sort_condition']:
		# 数値でソートを行うので、文字列化しないこと
		ret = config_data['sort_condition'][key] if len(str(config_data['sort_condition'][key])) > 0 else None

	if ret is not None and type(ret) != dict and type(ret) == str and len(ret) > 0:
		ret = ret.split(',')

	return ret

# 絞り込み条件と取得結果のチェック
# 戻り値はbool
def check_abst_sts(row, cond):
	ret = False
	#dbg_log(' ** row: {}, cond: {}'.format(row, cond))
	if cond is None:
		# 絞り込み条件がない場合、何もしない
		ret = True
	elif row is not None and cond is not None:	# Nullチェック
		if type(row) == list and type(cond) == list:
			if len(list(set(row) & set(cond))) > 0:	# list内の同値を出力（bit演算のANDを想像）
				ret = True
			#else:
			#	cmn._exit('warning', 'abst check: type not list')
		elif type(row) == str and type(cond) == list:
			if row in cond:						# 取得値が、画面からの絞り込み条件に含まれていない
				ret = True
		elif type(row) == str:
			if type(cond) == int:
				if int(row) == cond:
					ret = True
			elif type(cond) == str:
				if row == cond:
					ret = True
		elif type(row) == int:
			if type(cond) == int:
				if row == cond:
					ret = True
			elif type(cond) == str:
				if str(row) == cond:
					ret = True

		else:
			_exit('warning', 'abst check: type unmatch, row[{0}], cond[{1}]'.format(row, cond))
	else:
		#cmn._exit('warning', 'abst check: None Data')
		pass	# 団体とか契約がないとかあり得るので、何もしない

	return ret

# 団体情報
def get_org_data(orgSid):
	if orgSid is None:
		return {}

	zen2han = Zenkaku2Hankaku().zen2han

	def get_orgZip(orgData=None):
		val = ''
		if orgData is None: return None
		# 送付先
		if 'zip1' in orgData: val = orgData['zip1']
		# 住所枠の入力欄
		if 'address' in orgData and orgData['zip1'] is None:
			if 'zip' in orgData['address'] and orgData['address']['zip'] is not None and len(orgData['address']['zip']) > 0: val = orgData['address']['zip']
		return val
	def get_orgAddress(orgData=None):
		val = ''
		t_addr = ''
		if orgData is None: return None
		# 送付先
		if 'address1' in orgData and orgData['address1'] is not None and len(orgData['address1']) > 0:
			t_addr = orgData['address1']
			t_addr = re.sub(r"\n", u' ', t_addr.strip())				# 改行を半角スペースに置換
			t_addr = re.sub(r"[\s|　]+", u' ', t_addr.strip())		# 連続する空白っぽいのを半角スペースにまとめる
			val = t_addr
		# 住所枠の入力欄
		if 'address' in orgData:
			if 'adr1' in orgData['address'] and orgData['address']['adr1'] is not None and len(orgData['address']['adr1']) > 0: val += orgData['address']['adr1'].strip()
			if 'adr2' in orgData['address'] and orgData['address']['adr2'] is not None and len(orgData['address']['adr2']) > 0: val += orgData['address']['adr2'].strip()
			if 'adr3' in orgData['address'] and orgData['address']['adr3'] is not None and len(orgData['address']['adr3']) > 0: val += orgData['address']['adr3'].strip()
			if 'adr4' in orgData['address'] and orgData['address']['adr4'] is not None and len(orgData['address']['adr4']) > 0: val += orgData['address']['adr4'].strip()
		return val

	tmp_list = {}
	org_sid = []
	oth_org_cnt = 0			# その他団体は複数つけられるためカウントする
	outsource_org_item = conf.outsource_config['root']['outsource']['columns']['org_item']		# m_outsourceのツリー
	org_num_sep_moji = ','
	for i,k in enumerate(list(orgSid['orgs'])):
		i=i	# lint対策。意味はない
		org_sid.append(orgSid['orgs'][k]['sid'])
		s_org = orgSid['orgs'][k]['s_org']

		if 'f_org_num_conv' in conf.convert_option and conf.convert_option['f_org_num_conv'] == '1':
			# 記号／番号(社員番号)の全角=>半角変換とは名ばかりのUnicode正規化
			s_examinee = zen2han(orgSid['orgs'][k]['xinorg']['s_examinee']) if orgSid['orgs'][k]['xinorg']['s_examinee'] is not None else ''	# 記号: s_examinee
			n_examinee = zen2han(orgSid['orgs'][k]['xinorg']['n_examinee']) if orgSid['orgs'][k]['xinorg']['n_examinee'] is not None else ''	# 番号: n_examinee
			d_hired = zen2han(orgSid['orgs'][k]['xinorg']['d_hired']) if orgSid['orgs'][k]['xinorg']['d_hired'] is not None else ''				# 入社日: d_hired
			n_org = zen2han(orgSid['orgs'][k]['n_org']) if 'n_org' in orgSid['orgs'][k] and orgSid['orgs'][k]['n_org'] is not None else ''		# 保険者番号: n_org
		else:
			# 変換しないが、前後の空白は落とす
			s_examinee = orgSid['orgs'][k]['xinorg']['s_examinee'].strip() if orgSid['orgs'][k]['xinorg']['s_examinee'] is not None else ''
			n_examinee = orgSid['orgs'][k]['xinorg']['n_examinee'].strip() if orgSid['orgs'][k]['xinorg']['n_examinee'] is not None else ''
			d_hired = zen2han(orgSid['orgs'][k]['xinorg']['d_hired']) if orgSid['orgs'][k]['xinorg']['d_hired'] is not None else ''
			n_org = orgSid['orgs'][k]['n_org'].strip() if 'n_org' in orgSid['orgs'][k] and orgSid['orgs'][k]['n_org'] is not None else ''

		org_name = orgSid['orgs'][k]['name'].strip()
		if s_org == '1' and 'org_name':
			# 所属団体
			if 'org_name' in outsource_org_item:
				key = outsource_org_item['org_name']		# 団体名
				val = org_name
				tmp_list.update({key:val})
			if 'org_number' in outsource_org_item:
				key = outsource_org_item['org_number']		# 記号／番号(社員番号)
				val = n_examinee
				tmp_list.update({key:val})
			if 'org_zip' in outsource_org_item:
				key = outsource_org_item['org_zip']			# 郵便番号
				val = get_orgZip(orgSid['orgs'][k])
				tmp_list.update({key:val})
			if 'org_addr' in outsource_org_item:
				key = outsource_org_item['org_addr']		# 住所
				val = get_orgAddress(orgSid['orgs'][k])
				tmp_list.update({key:val})
			if 'org_hiredate' in outsource_org_item:
				key = outsource_org_item['org_hiredate']	# 入社日
				val = d_hired
				tmp_list.update({key:val})
		elif s_org == '10' or s_org == '11' or s_org == '12':
			# 10: 地域, 11:社保・国保, 12:その他保険団体
			if 'insurance_name' in outsource_org_item:
				key = outsource_org_item['insurance_name']
				val = org_name
				tmp_list.update({key:val})
			if 'insurance_symbol' in outsource_org_item:
				key = outsource_org_item['insurance_symbol']
				val = s_examinee
				tmp_list.update({key:val})
			if 'insurance_number' in outsource_org_item:
				key = outsource_org_item['insurance_number']
				val = n_examinee
				tmp_list.update({key:val})
			if 'insurer_number' in outsource_org_item:		# 保険者番号
				key = outsource_org_item['insurer_number']
				val = n_org
				tmp_list.update({key:val})
			if 'insurance_zip' in outsource_org_item:
				key = outsource_org_item['org_zip']			# 郵便番号
				val = get_orgZip(orgSid['orgs'][k])
				tmp_list.update({key:val})
			if 'insurance_addr' in outsource_org_item:
				key = outsource_org_item['org_addr']		# 住所
				val = get_orgAddress(orgSid['orgs'][k])
				tmp_list.update({key:val})
			if 'f_examinee' in outsource_org_item:
				key = outsource_org_item['f_examinee']		# 被保険者・被扶養者番号チェック用
				val = orgSid['orgs'][k]['xinorg']['f_examinee'].strip() if 'f_examinee' in orgSid['orgs'][k]['xinorg'] and orgSid['orgs'][k]['xinorg']['f_examinee'] is not None else None
				tmp_list.update({key:val})
		else:
			# その他
			if 'other_name' in outsource_org_item:
				oth_org_cnt += 1
				key = outsource_org_item['other_name'] + '_{}'.format(oth_org_cnt)
				val = org_name
				tmp_list.update({key:val})
			if 'other_number' in outsource_org_item:
				key = outsource_org_item['other_number'] + '_{}'.format(oth_org_cnt)
				if len(s_examinee) > 0 and len(n_examinee) > 0:
					val = '{}{}{}'.format(s_examinee, org_num_sep_moji, n_examinee)
				else:
					val = '{}{}'.format(s_examinee, n_examinee)
				tmp_list.update({key:val})
			if 'other_zip' in outsource_org_item:
				key = outsource_org_item['org_zip']			# 郵便番号
				val = get_orgZip(orgSid['orgs'][k])
				tmp_list.update({key:val})
			if 'other_addr' in outsource_org_item:
				key = outsource_org_item['org_addr']		# 住所
				val = get_orgAddress(orgSid['orgs'][k])
				tmp_list.update({key:val})

	# 絞り込みで団体番号が必要なので、合わせて返却する。
	# TODO: org_sidが不要な場合、受け取った先で削除を行うこと
	tmp_list.update({'org_sid':org_sid})

	return tmp_list

# 受診券情報
def get_ccard_data(xmlCcard):
	if xmlCcard is None:
		return {}

	ccard_list = {}
#	xml_ccard = []
	outsource_ccard_item = conf.outsource_config['root']['outsource']['columns']['ccard_item']		# m_outsourceのツリー

	if 'no' in outsource_ccard_item:
		key = outsource_ccard_item['no']
		val = xmlCcard['ccard']['no'] if 'no' in xmlCcard['ccard'] else None
		ccard_list.update({key:val})
	if 'd_valid' in outsource_ccard_item:
		key = outsource_ccard_item['d_valid']
		val = xmlCcard['ccard']['d_valid'] if 'd_valid' in xmlCcard['ccard'] else None
		ccard_list.update({key:val})

#	for k,v in xmlCcard['ccard'].items():
#		xml_ccard.append(v)
#		ccard_list[k] = {}
#		#if k in enumerate(list(xmlCcard['ccard']) =
#		if 's_class' in outsource_ccard_item:
#			key = outsource_ccard_item['s_class']
#			val = k
#			ccard_list[k].update({key:val})
#		if 'examine_rate' in outsource_ccard_item:
#			key = outsource_ccard_item['examine_rate']
#			val = v['examine_rate'] if 'examine_rate' in v and v['examine_rate'] is not None else None
#			ccard_list[k].update({key:val})
#		if 'examine_value' in outsource_ccard_item:
#			key = outsource_ccard_item['examine_value']
#			val = v['examine_value'] if 'examine_value' in v and v['examine_value'] is not None else None
#			ccard_list[k].update({key:val})
#		if 'insurer_rate' in outsource_ccard_item:
#			key = outsource_ccard_item['insurer_rate']
#			val = v['insurer_rate'] if 'insurer_rate' in v and v['insurer_rate'] is not None else None
#			ccard_list[k].update({key:val})
#		if 'insurer_value' in outsource_ccard_item:
#			key = outsource_ccard_item['insurer_value']
#			val = v['insurer_value'] if 'insurer_value' in v and v['insurer_value'] is not None else None
#			ccard_list[k].update({key:val})

	return ccard_list

#attribe情報
def get_contract_me_attribute_data(xmlAttribute):
	if xmlAttribute is None:
		return{}

	attribute_List = {}
	xml_attribute = []
	outsource_attribute_item = conf.outsource_config['root']['outsource']['columns']['attribute_item']		# m_outsourceのツリー

	if 'course_price' in outsource_attribute_item:
		key = outsource_attribute_item['course_price']
		val = xmlAttribute['course_price'] if 'course_price' in xmlAttribute else None
		attribute_List.update({key:val})

	for k,v in xmlAttribute['consultations'].items():
		xml_attribute.append(v)
		attribute_List[k] = {}

		if 'sid_criterion' in outsource_attribute_item:
			key = outsource_attribute_item['sid_criterion']
			val = v['sid_criterion'] if 'sid_criterion' in v else None
			attribute_List[k].update({key:val})
		if 'tokken_price' in outsource_attribute_item:
			key = outsource_attribute_item['tokken_price']
			val = v['attribute']['price'] if 'price' in v['attribute'] else None
			attribute_List[k].update({key:val})
		if 's_class' in outsource_attribute_item:
			key = outsource_attribute_item['s_class']
			val = v['attribute']['s_class'] if 's_class' in v['attribute'] else None
			attribute_List[k].update({key:val})

	return attribute_List

#kekka1データ作成
def get_price_data1(examineeKekka1Header,kekkadata):

	kekka1_hederitem = examineeKekka1Header		# 定義しておいたヘッダ
	kekka1_data = {k:None for k in kekka1_hederitem.values()}
	for cnt in range(1,5):					#詳細健診用の4か所を埋める
		kk = str(cnt)
		#区分
		if kk == '1' and 'mkSec' in kekka1_hederitem:
			key = kekka1_hederitem['mkSec']
		elif kk == '2' and 'msSec' in kekka1_hederitem:
			key = kekka1_hederitem['msSec']
		elif kk == '3' and 'mtSec' in kekka1_hederitem:
			key = kekka1_hederitem['mtSec']
		elif kk == '4' and 'mnSec' in kekka1_hederitem:
			key = kekka1_hederitem['mnSec']
		val = kekkadata[kk]['section'] if 'section' in kekkadata[kk] else None
		kekka1_data.update({key:val})
		#金額
		if kk == '1' and 'mkMoney' in kekka1_hederitem:
			key = kekka1_hederitem['mkMoney']
		elif kk == '2' and 'msMoney' in kekka1_hederitem:
			key = kekka1_hederitem['msMoney']
		elif kk == '3' and 'mtMoney' in kekka1_hederitem:
			key = kekka1_hederitem['mtMoney']
		elif kk == '4' and 'mnMoney' in kekka1_hederitem:
			key = kekka1_hederitem['mnMoney']
		val = kekkadata[kk]['value'] if 'value' in kekkadata[kk] and kekkadata[kk]['value'] != '0' else None
		kekka1_data.update({key:val})
		#負担率
		if kk == '1' and 'mkRate' in kekka1_hederitem:
			key = kekka1_hederitem['mkRate']
		elif kk == '2' and 'msRate' in kekka1_hederitem:
			key = kekka1_hederitem['msRate']
		elif kk == '3' and 'mtRate' in kekka1_hederitem:
			key = kekka1_hederitem['mtRate']
		elif kk == '4' and 'mnRate' in kekka1_hederitem:
			key = kekka1_hederitem['mnRate']
		val = kekkadata[kk]['rate'] if 'rate' in kekkadata[kk] else None
		kekka1_data.update({key:val})
		#詳細健診単価
		if kk == '1' and 'syousaiUnitPrice1' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiUnitPrice1']
		elif kk == '2' and 'syousaiUnitPrice2' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiUnitPrice2']
		elif kk == '3' and 'syousaiUnitPrice3' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiUnitPrice3']
		elif kk == '4' and 'syousaiUnitPrice4' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiUnitPrice4']
		val = kekkadata['syousai'][kk]['price'] if 'price' in kekkadata['syousai'][kk] else None
		kekka1_data.update({key:val})
		#詳細健診コード
		if kk == '1' and 'syousaiCode1' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiCode1']
		elif kk == '2' and 'syousaiCode2' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiCode2']
		elif kk == '3' and 'syousaiCode3' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiCode3']
		elif kk == '4' and 'syousaiCode4' in kekka1_hederitem:
			key = kekka1_hederitem['syousaiCode4']
		val = kekkadata['syousai'][kk]['code'] if 'code' in kekkadata['syousai'][kk] else None
		kekka1_data.update({key:val})
		#窓口負担金
		if kk == '1' and 'mkMoneyCalc' in kekka1_hederitem:
			key = kekka1_hederitem['mkMoneyCalc']
		elif kk == '2' and 'msMoneyCalc' in kekka1_hederitem:
			key = kekka1_hederitem['msMoneyCalc']
		elif kk == '3' and 'mtMoneyCalc' in kekka1_hederitem:
			key = kekka1_hederitem['mtMoneyCalc']
		else:
			continue
		val = kekkadata[kk]['Calc'] if 'Calc' in kekkadata[kk] else None
		kekka1_data.update({key:val})

	#請求区分
	if 'seiSec' in kekka1_hederitem:
		key = kekka1_hederitem['seiSec']
		val = kekkadata['seiSec'] if 'seiSec' in kekkadata else None
		kekka1_data.update({key:val})
	#委託料単価区分
	if 'itakuUnitPriceSec' in kekka1_hederitem:
		key = kekka1_hederitem['itakuUnitPriceSec']
		val = kekkadata['itakuUnitPriceSec'] if 'itakuUnitPriceSec' in kekkadata else None
		kekka1_data.update({key:val})
	#基本的な健診単価
	if 'kihonUnitPrice' in kekka1_hederitem:
		key = kekka1_hederitem['kihonUnitPrice']
		val = kekkadata['kihonUnitPrice'] if 'kihonUnitPrice' in kekkadata else None
		kekka1_data.update({key:val})
	#単価(合計）
	if 'UnitPriceCalc' in kekka1_hederitem:
		key = kekka1_hederitem['UnitPriceCalc']
		val = kekkadata['UnitPriceCalc'] if 'UnitPriceCalc' in kekkadata else None
		kekka1_data.update({key:val})
	#窓口負担金額（合計）
	if 'mdAllCalc' in kekka1_hederitem:
		key = kekka1_hederitem['mdAllCalc']
		val = kekkadata['mdAllCalc'] if 'mdAllCalc' in kekkadata else None
		kekka1_data.update({key:val})
	#他健診負担金額
	if 'taAllCalc' in kekka1_hederitem:
		key = kekka1_hederitem['taAllCalc']
		val = kekkadata['taAllCalc'] if 'taAllCalc' in kekkadata else None
		kekka1_data.update({key:val})
	#請求金額
	if 'billingAmount' in kekka1_hederitem:
		key = kekka1_hederitem['billingAmount']
		val = kekkadata['billingAmount'] if 'billingAmount' in kekkadata else None
		kekka1_data.update({key:val})
	#受診者ID
	kekka1_data[kekka1_hederitem['id']] = conf.examInfo['id']

	return kekka1_data

# examineeのXML
def get_examinee_data(examData, examinee_item):
	zen2han = Zenkaku2Hankaku().zen2han
	data = {}

	if 'name' in examData: data['name'] = examData['name']
	if 'name-kana' in examData: data['name-kana'] = examData['name-kana']
	if 'my_number' in examData: data['my_number'] = examData['my_number']
	if 'id' in examData: data['id'] = examData['id']
	if 'birthday' in examData:
		data['birthday'] = examData['birthday']
		birDay = re.sub('[/-]+', '', examData['birthday'])
		gengo, gengoY = warekiCheck(birDay)		# 和暦の元号と年を取得

	if 'sex' in examData:
		# m_outsourceの定義そのまま
		sex_male = conf.convert_option['sex_male'] if 'sex_male' in conf.convert_option else None
		sex_female = conf.convert_option['sex_female'] if 'sex_female' in conf.convert_option else None
		sex_unknown = conf.convert_option['sex_unknown'] if 'sex_unknown' in conf.convert_option else None
		data['sex'] = examData['sex']
		if sex_male is not None and examData['sex'] == '1': data['sex'] = sex_male				# 男性
		elif sex_female is not None and examData['sex'] == '2':  data['sex'] = sex_female		# 女性
		elif sex_unknown is not None: data['sex'] = sex_unknown									# 不明
		conf.examInfo['sex'] = examData['sex']

	# 予約日から計算した年齢。属性情報連携等で、画面以外から登録を行った場合、XMLタグが存在しないことがあるので外だし
	conf.examInfo['age'] = age_calculation(conf.examInfo['appoint_day'], examData['birthday'])
	if 'age-whenapo' in examData:
		if conf.convert_option['f_birthday2age'] == '1': data['age-whenapo'] = conf.examInfo['age']

	# 和暦を格納
	if 'birthdayGengo' in conf.outsource_config['root']['outsource']['columns']['examinee_item']: data['birthdayGengo'] = gengo
	if 'birthdayGengoY' in conf.outsource_config['root']['outsource']['columns']['examinee_item']: data['birthdayGengoY'] = '{:0>2}'.format(gengoY)		# 二桁にする
	if 'birthdayGengoM' in conf.outsource_config['root']['outsource']['columns']['examinee_item']: data['birthdayGengoM'] = birDay[4:6]
	if 'birthdayGengoD' in conf.outsource_config['root']['outsource']['columns']['examinee_item']: data['birthdayGengoD'] = birDay[6:8]

	if 'bloodtype' in examData:
		if examData['bloodtype'] is not None:
			bld = examData['bloodtype'].split() 			# 空白で分解
			data['bloodtype'] = bld[0]						# 血液型
			#data['bloodRHtype']	= bld[1]				# RH型
		else:
			data['bloodtype'] = None
			#data['bloodRHtype']	= None

	if 'contact' in examData:
		t_zip = ''
		t_addr = ''
		zipData = None
		addressData = None
		# 複数住所入力枠が存在する場合
		if 'destination' in examData['contact'] and examData['contact']['destination'] is not None:
			if examData['contact']['destination'] == '0':
				examData['contact']['destination'] = '1'
			zipNum = 'zip' + str(examData['contact']['destination'])
			addrNum = 'address' + str(examData['contact']['destination'])
			try:
				s_addr = examData['contact'][addrNum]
				# 郵便番号かもしれない個所を狙い撃ちでチェック
				reobj = re.match(r".*[0-9]{3}-[0-9]{4}", zen2han(s_addr[:9]))
				if reobj is not None:
					# 数字かチェックするために、郵便番号に「マイナス」がいたら消す
					if reobj.string[0].strip().replace('-','').isnumeric():
						t_zip = s_addr[0:8]			# 全て数値なら郵便番号っぽい
						t_addr = s_addr[9:]
					else:
						t_zip = s_addr[1:9]			# 郵便マークがいる可能性
						t_addr = s_addr[10:]
				else:
					# 送付先住所に郵便番号がないっぽいが、個別入力枠に存在する場合はそっちを入れる
					if t_zip is not None and re.match(r".*[0-9]{3}-[0-9]{4}", zen2han(t_zip)) is not None:
						pass
					else:
						t_zip = examData['contact'][zipNum]
					t_addr = s_addr
			except Exception as err:
				Log().log('unknwon zip/address, zipNum: {}, addrNum: {}, msg: {}'.format(zipNum, addrNum, err), LOG_WARN)

		# 住所の入力枠
		if 'address' in examData['contact'] and examData['contact']['address'] is not None:
			if 'zip' in examData['contact']['address']: t_zip = examData['contact']['address']['zip']
			addrList = ['adr1', 'adr2', 'adr3', 'adr4']
			for key in addrList:
				if key in examData['contact']['address']:
					t_addr += examData['contact']['address'][key] if examData['contact']['address'][key] is not None else ''

		# 送付先住所
		if 'send_addr' in examData['contact'] and examData['contact']['send_addr'] is not None and len(examData['contact']['send_addr']) > 0:
			s_addr = examData['contact']['send_addr']
			# 郵便番号かもしれない個所を狙い撃ちでチェック
			reobj = re.match(r".*[0-9]{3}-[0-9]{4}", zen2han(s_addr[:9]))
			if reobj is not None:
				# 数字かチェックするために、郵便番号に「マイナス」がいたら消す
				if reobj.string[0].strip().replace('-','').isnumeric():
					t_zip = s_addr[0:8]			# 全て数値なら郵便番号っぽい
					t_addr = s_addr[9:]
				else:
					t_zip = s_addr[1:9]			# 郵便マークがいる可能性
					t_addr = s_addr[10:]
			else:
				# 送付先住所に郵便番号がないっぽいが、個別入力枠に存在する場合はなにもしない
				if t_zip is not None and re.match(r".*[0-9]{3}-[0-9]{4}", zen2han(t_zip)) is not None:
					pass
				else:
					t_zip = None
				t_addr = s_addr

		# 郵便番号と住所のトリミング
		if t_zip is not None and len(t_zip) > 0: zipData = t_zip.strip()
		if t_addr is not None and len(t_addr) > 0:
			t_addr = re.sub(r"\n", u' ', t_addr.strip())				# 改行を半角スペースに置換
			addressData = re.sub(r"[\s|　]+", u' ', t_addr.strip())		# 連続する空白っぽいのを半角スペースにまとめる

		data['zip'] = zipData
		data['address'] = addressData

	# 出力データの抽出
	data = {examinee_item[key]:data[key] for key in examinee_item if key in data}
	# 加工したデータ（data）に入っていないが、引数で貰ったデータ（examData）に含まれているものはマージ
	data.update({examinee_item[key]:examData[key] for key in examinee_item if examinee_item[key] not in data and key in examData})

	return data


# 数字と小数部の桁数を与えて、小数部を丸めた数字を返却
# TODO: マイナスの値は考慮されていない
def numeric2conv(val, ndigit):
	num = 0
	if type(val) == str:
		if val.replace('.', '').isnumeric():		# 全て数字かチェック
			try:
				num = float(val)					# floatに変換(100なら100.0になる)
			except:
				# 入力ミスでfloatの変換失敗したら元データを返す。（例）「x..x」みたいに小数点が多く入力されている
				return val
		else:
			return val							# 数字じゃない場合は元データ返却。出力されないという文句を言われないために入力されたものを返す
	elif type(val) == int or type(val) == float:
		try:
			num = float(val)
		except:
			return val
	else:
		return val		# TODO: 保険。このルートには落ちないはず

	#if num.is_integer():						# 小数部が.0ならTrue
	#	return str(int(num))					# .0をカット
	#else:
	if int(ndigit) > 0:
		tmp_num = float(round(num, int(ndigit)))	# 丸める(四捨五入)
		ret_mum = '{:.{digit}f}'.format(tmp_num, digit=int(ndigit))	# 四捨五入の結果小数部が.0になると、0が消えてしまうので桁調整を行う
		return ret_mum

	elif int(ndigit) == 0:	# 数字の欄は画面上見えないが小数点が入力できるため、画面の動きに合わせる
		return str(int(round(num, 0)))		# 丸める(四捨五入))

	return val		# TODO: 保険。このルートには落ちないはず

# コース名、受診日の取得
#@measure	# デバッグ専用
def get_appo_info(row, appoint_item):
	appo_info = appoint_item.keys()
	tmp_list1 = []
	tmp_list2 = []
	dt_appoint_day = None
	appoint_time = None
	dt_appo = None

	if b'dt_appoint' in row:
		dt_appo = str(row[b'dt_appoint'])
	elif 'dt_appoint' in row:
		dt_appo = row['dt_appoint']

	if type(dt_appo) == datetime.datetime or type(dt_appo) == datetime.date:
		dt_appo = datetime.datetime.strftime(dt_appo, '%Y/%m/%d %H:%M:%S')

	if dt_appo is not None:
		dt_appoint_base = dt_appo.split()
		dt_appoint_day = dt_appoint_base[0]							# 予約日
		dt_appoint_ymd = re.sub(r'[/-]', '', dt_appoint_day)		# 年月日の区切り文字[/-]っぽいのを削除
		dt_appoint_time = dt_appoint_base[1].split(':')				# 予約時刻、秒は捨て
		if int(dt_appoint_time[0]+dt_appoint_time[1]) > 0:			# 00:00は予約時間なし扱い
			appoint_time = dt_appoint_time[0] + ':' + dt_appoint_time[1]

		# 和暦の元号と年を取得
		gengo, gengoY = warekiCheck(dt_appoint_ymd)

	for key in appo_info:
		tmp_list1.append(appoint_item[key])
		if key == 'appoint_number':			# 受診番号
			val = row['n_appoint'] if 'n_appoint' in row else None
			#tmp_list2.append(item.findtext('ccard/no'))			# これじゃない
			tmp_list2.append(val)						# 現状使っているところはないらしい
		elif key == 'dt_appoint':			# 受診日（予約日）
			tmp_list2.append(dt_appoint_day)
		elif key == 'appoint_time':			# 受診時刻（予約時刻）
			tmp_list2.append(appoint_time)
		elif key == 'appointGengo':
			tmp_list2.append(gengo)
		elif key == 'appointGengoY':
			tmp_list2.append(gengoY)
		elif key == 'appointGengoM':
			tmp_list2.append(dt_appoint_ymd[4:6])
		elif key == 'appointGengoD':
			tmp_list2.append(dt_appoint_ymd[6:8])
		else:
			val = row[key] if key in row else None
			tmp_list2.append(val)

	return dict(zip(tmp_list1,tmp_list2))


# 検査項目
def get_inspection_data(xmlMeSid, itemList, retSid=False):
	if len(xmlMeSid) < 1: return None
	if retSid == True:
		# 「sid:結果」で返却
		data = {k : xmlMeSid['elements'][k]['result'].get('value') for k in itemList if k in xmlMeSid['elements']}
	else:
		# 「項目名：結果」で返却
		data = {itemList[k] : xmlMeSid['elements'][k]['result'].get('value') for k in itemList if k in xmlMeSid['elements']}
	return data

## f_intendedとf_examの取得
def getFintendedFexam(xmlMeSid):
	if xmlMeSid is None or len(xmlMeSid) < 1: return None
	import form_tools_py.getXmlSid as getXmlSid
	data = {}
	data = getXmlSid.analyzeXmlCriterionCource_fIntended_fExam(xmlMeSid)
	if data is None or len(data) < 1: return None

	return data

## 検査項目の標準／オプション取得／実施／未実施
# 以下の内容で出力データを作成する
# 1：標準、未実施
# 2：オプション、未実施
# 3：標準、実施
# 4：オプション、実施
def search_xml_criterion_inspOption(xmlMeSid):
	if xmlMeSid is None or len(xmlMeSid) < 1: return None
	data = None
	courseInfo = getFintendedFexam(xmlMeSid)

	# f_exam=1（オプション）、2（標準）
	# f_intended: 0=未実施(OFF) 1=実施(ON)
	# 受診対象の検査項目「xmlMeのf_intended=1」かつ「me_attrib_itemのf_exam=1 or 2」に該当するものを抽出
	f_intended_data_check = {}
	for sid,val in courseInfo['xmlMe']['eitem']['f_intended'].items():
		attrb_f_examVal = courseInfo['meAttrib']['eitem']['f_exam'][sid] if courseInfo['meAttrib']['eitem']['f_exam'] is not None and sid in courseInfo['meAttrib']['eitem']['f_exam'] else None
		f_intended_data_check.update({sid: val})											# 初期値はxmlMeのf_intended(標準、実施扱い)
		if val == '0':																		# f_intended=0になっている場合、予約時に「受診しない」と明示されているので何もしない
			pass
		elif courseInfo['meAttrib']['eitem']['f_intended'] is None:							# meAttribに必要な情報が無い
			pass
		elif sid in courseInfo['meAttrib']['eitem']['f_intended']:							# meAttribに含まれる場合は、meAttribで上書きする
			if val is None:																	# NoneはXMLME解析時に、f_intendedタグが存在しなかった項目
				val = courseInfo['meAttrib']['eitem']['f_intended'][sid]
		# リスト作成
		if attrb_f_examVal is None and val is None: f_intended_data_check[sid] = '3'		# m_me_attribもxmlmeのf_intendedもなければ強制で標準、実施扱い
		elif attrb_f_examVal == '2' and val == '0': f_intended_data_check[sid] = '1'		# 標準、未実施
		elif attrb_f_examVal == '1' and val == '0': f_intended_data_check[sid] = '2'		# オプション、未実施
		elif attrb_f_examVal == '2' and val == '1': f_intended_data_check[sid] = '3'		# 標準、実施
		elif attrb_f_examVal == '1' and val == '1': f_intended_data_check[sid] = '4'		# オプション、実施

	# xmlMeに格納されている全検査項目の受診状態をconfに格納する
	if f_intended_data_check is not None or len(f_intended_data_check) > 0:
		conf.inspStdOptData['eitem'] = f_intended_data_check
		# 要素のsidを格納する
		conf.inspStdOptData['elementSid'] = courseInfo['xmlMe']['eitem']['elementSid']

	data = f_intended_data_check

	return data

## 標準／オプション項目の抽出
# itemListが指定された場合、このlistで指定された項目のみを返却する
#@measure	# デバッグ専用
def get_inspection_stdOpt_data(xmlMeSid, itemList=None):
	if len(xmlMeSid) < 1: return None
	getItemList = search_xml_criterion_inspOption(xmlMeSid)

	# 検査項目が指定されている場合、さらに抽出した内容を戻り値で返す
	if itemList is not None: data = {itemList[k] : getItemList[k] for k in getItemList['eitem'] if k in itemList}
	else: data = getItemList

	return data

## 特定の検査項目／項目要素を受診しているか確認
# 戻り値
# None: 検査項目が見つからない
# False: 受診対象外
# True: 受診対象
def get_inspection_status_check(eitemSid=None, elementSid=None):
	ret = None
	if conf.inspStdOptData is None and eitemSid is None and elementSid is None: return ret
	if len(conf.inspStdOptData) < 1 or ((eitemSid is not None and len(eitemSid) < 1) or (elementSid is not None and len(elementSid) < 1)): return ret
	sid = None
	# 項目
	if eitemSid is not None:
		#sid = [k for k in conf.inspStdOptData['eitem'] if eitemSid == k][0]
		sid = eitemSid
	# 要素sidを指定された場合、項目sidを取得しなおす
	elif elementSid is not None:
		sid = [k for k,v in conf.inspStdOptData['elementSid'].items() if elementSid in v]
	if sid is None or len(sid) < 1: return ret
	else: sid = sid[0]

	if conf.inspStdOptData['eitem'][sid] in ['3','4']:
		ret = True
	else:
		ret = False

	return ret

# グループ判定／所見の取得
def get_groupRank_data(xmlMeSid, itemList, retSid=False):
	if itemList is None or len(itemList) < 1: return None			# m_outsourceにgroupRankが未設定

	if len(xmlMeSid) < 1: return None

	# 改行置換用
	pattern1 = r"\n+"
	convbreak = re.compile(pattern1)

	sepStr = ': '	# 所見を繋げる際の区切り文字

	data = {}

	## グループに複数ランクが存在する場合、重いものを抽出する
	# xmlMeSid['egroups']['1000']
	# TODO: [A-Z|0-9]以外の場合、要調査（例：C6, C12などの複数文字の場合）
	def getRank(obj):
		rankSort = {obj['result']['opinion'][k]['code']:k for k in obj['result']['opinion'] if obj['result']['opinion'][k]['code'] and obj['result']['opinion'][k]['code'] != '90001'}
		if len(rankSort) < 1: return None	# 強制
		ranking = rankSort[sorted(rankSort, key=itemgetter(0), reverse=True)[0]]

		return ranking

	## グループ内に存在する複数項目の判定所見の取得／結合
	def getFinding(obj):
		ret = ''
		findData = {obj['result']['opinion'][k]['rank-output-key']:obj['result']['opinion'][k]['finding'] for k in obj['result']['opinion'] if obj['result']['opinion'][k]['finding'] is not None}
		findDataLen = len(findData)
		if findDataLen == 1:
			for key in findData:
				if key.isdecimal(): ret = findData[key]
				else: ret = key + sepStr + ''.join(findData.values())		# 項目名： 所見～～～　となる
		elif findDataLen > 1:
			finding = ''
			for key in findData:
				if len(key.strip()) < 1: continue						# 改行だけの場合はスキップ
				finding += key + sepStr + findData[key].strip() + '\n'
			finding = convbreak.sub(r"\n", finding.strip())
			# TODO: 暫定版。識別用の改行文字を入れる。Excelマクロ側で識別文字列をチェックして改行コードを挿入する
			if 'f_groupRankFindingBreak' in conf.convert_option and conf.convert_option['f_groupRankFindingBreak'] == '1':
				ret = convbreak.sub(r"\\r\\n", finding.strip())
			else:
				ret = convbreak.sub(r", ", finding.strip())

		return [ret]

	try:
		if retSid == True:
			# old
			#rankData = {k : xmlMeSid['egroups'][k]['result']['opinion'][kk]['code'] for k in xmlMeSid['egroups'] for kk in getRank(xmlMeSid['egroups'][k]) if k in itemList and xmlMeSid['egroups'][k]['f_intended'] == '1' and xmlMeSid['egroups'][k]['result']['opinion'][kk]['code'] !='90001'}

			# new
			#for k1,v1 in xmlMeSid['egroups'].items():
			#	if k1 in itemList and v1['f_intended'] == '1':
			#		if getRank(v1) is not None:
			#			for k2 in getRank(v1):
			#				v1['result']['opinion'][k2]['code']
			rankData = {k1 : v1['result']['opinion'][k2]['code'] for k1,v1 in xmlMeSid['egroups'].items() if k1 in itemList and v1['f_intended'] == '1' and getRank(v1) is not None for k2 in getRank(v1)}
			rankManualFlag = {k1 : v1['result']['opinion'][k2]['code'] for k1,v1 in xmlMeSid['egroups'].items() if k1 in itemList and v1['f_intended'] == '1' and getRank(v1) is not None for k2 in getRank(v1) if v1['result']['opinion'][k2]['manual'] != '0'}

			findingData = {k : kk for k in xmlMeSid['egroups'] for kk in getFinding(xmlMeSid['egroups'][k]) if k in itemList and xmlMeSid['egroups'][k]['f_intended'] == '1' and len(kk) > 0}
			# sidで返却する場合は所見サマリの作成は行わない。
		else:
			#rankData = {itemList[k] : xmlMeSid['egroups'][k]['result']['opinion'][kk]['code'] for k in xmlMeSid['egroups'] for kk in getRank(xmlMeSid['egroups'][k]) if k in itemList and xmlMeSid['egroups'][k]['f_intended'] == '1' and xmlMeSid['egroups'][k]['result']['opinion'][kk]['code'] !='90001'}
			rankData = {}
			for k in xmlMeSid['egroups']:
				if k in itemList and xmlMeSid['egroups'][k]['f_intended'] == '1':
					opIdx = getRank(xmlMeSid['egroups'][k])
					if opIdx is not None and len(opIdx) > 0:
						rankData = {**rankData, **{itemList[k] : xmlMeSid['egroups'][k]['result']['opinion'][opIdx]['code']}}
			findingData = {itemList[k] : kk for k in xmlMeSid['egroups'] for kk in getFinding(xmlMeSid['egroups'][k]) if k in itemList and xmlMeSid['egroups'][k]['f_intended'] == '1' and len(kk) > 0}

			# 所見サマリ。「グループ名：所見」で所見部分は各項目所見を結合したデータを突っ込む
			if len(findingData) > 0:
				summaryData = ''.join([k + sepStr + findingData[k] + '\n' for k in findingData])
				if 'f_groupRankFindingBreak' in conf.convert_option and conf.convert_option['f_groupRankFindingBreak'] == '1':
					data['summary'] = {'groupRankSummary':convbreak.sub(r"\\r\\n", summaryData.strip())}
				else:
					data['summary'] = {'groupRankSummary':convbreak.sub(r", ", summaryData.strip())}

		data['rank'] = {k+'_rank':rankData[k] for k in rankData}
		data['finding'] = {k+'_finding':findingData[k] for k in findingData}		# ランク名称に所見用文字列「_finding」を付与
		data['rankManualFlag'] = rankManualFlag

	except Exception as err:
		Log().log('group rank get faild: {}'.format(err), LOG_ERR)

	return data

# 項目ランクの取得
# 戻り値＝sid：ランクコード
def get_itemRank_data(xmlMeSid, itemList):
	if itemList is None or len(itemList) < 1: return None			# m_outsourceにgroupRankが未設定

	if len(xmlMeSid) < 1: return None

	data = {}

	## itemに複数ランクが存在する場合、重いものを抽出する
	# TODO: [A-Z|0-9]以外の場合、要調査（例：C6, C12などの複数文字の場合）
	def getRank(obj):
		rankSort = {obj['result']['opinion'][k]['code']:k for k in obj['result']['opinion'] if obj['result']['opinion'][k]['code']}
		if len(rankSort) < 1: return '1'	# 強制
		ranking = rankSort[sorted(rankSort, key=itemgetter(0), reverse=True)[0]]

		return ranking

	try:
		data = {k : v['result']['opinion'][kk]['code'] for k,v in xmlMeSid.items() for kk in getRank(v) if k in itemList and v['result']['opinion'][kk]['code'] not in ['90001', '90099'] }

	except Exception as err:
		Log().log('item rank get faild: {}'.format(err), LOG_ERR)

	return data


# 総合判定とか、確定を行った医師名の取得
def get_general_data(xmlMeSid, itemList, course_sid):
	if len(xmlMeSid) < 1: return None
	data = None
	# 総合判定のrank-output-keyは１固定
	try:
		data = {itemList[k] : xmlMeSid['ecourse'][course_sid]['result']['opinion']['1'][k] for k in xmlMeSid['ecourse'][course_sid]['result']['opinion']['1'] if k in itemList}
	except Exception as err:
		Log().log('xmlme ecourse.result.opinion get faild:({}:{})'.format(err.__class__.__name__, err), LOG_WARN)
	return data

# kekka1データ作成
def get_price_data(xmlCcard,xmlAttribute,detail,additional,detail_item,tk_calc_data):
	zen2han = Zenkaku2Hankaku().zen2han

	data = {}
	calc_data = 0
	detail_calc_data = 0

	#基本的な健診単価
	data['kihonUnitPrice'] = xmlAttribute['course_price'] if 'course_price' in xmlAttribute and xmlAttribute['course_price'] is not None else 0
	#基本的な健診単価計算用
	unitPrice = int(data['kihonUnitPrice']) if data['kihonUnitPrice'] is not None else 0

	#詳細な単価が入っていれば、コード1から順に格納していく
	data['syousai'] = {}
	for key in range(1,5):					#詳細健診用の4か所を埋める
		kk = str(key)
		data['syousai'][kk] = {}
		data['syousai'][kk]['price'] = {}
		data['syousai'][kk]['code'] = {}

		#初期値と見つからない場合はNoneを入れておく
		data['syousai'][kk]['price'] = None
		data['syousai'][kk]['code'] = None

		if 'annual_price' in detail_item and detail_item['annual_price'] is not None and data['syousai'][kk]['price'] == None and data['syousai'][kk]['code'] == None:
			data['syousai'][kk]['price'] = detail_item['annual_price']
			data['syousai'][kk]['code'] = detail_item['annual_code']
			detail_item['annual_price'] = None
			detail_item['annual_code'] = None
		elif 'cardiogram_price' in detail_item and detail_item['cardiogram_price'] is not None and data['syousai'][kk]['price'] == None and data['syousai'][kk]['code'] == None:
			data['syousai'][kk]['price'] = detail_item['cardiogram_price']
			data['syousai'][kk]['code'] = detail_item['cardiogram_code']
			detail_item['cardiogram_price'] = None
			detail_item['cardiogram_price'] = None
		elif 'funduscopy_price' in detail_item and detail_item['funduscopy_price'] is not None and data['syousai'][kk]['price'] == None and data['syousai'][kk]['code'] == None:
			data['syousai'][kk]['price'] = detail_item['funduscopy_price']
			data['syousai'][kk]['code'] = detail_item['funduscopy_code']
			detail_item['funduscopy_price'] = None
			detail_item['funduscopy_price'] = None
		elif 'creatinine_price' in detail_item and detail_item['creatinine_price'] is not None and data['syousai'][kk]['price'] == None and data['syousai'][kk]['code'] == None:
			data['syousai'][kk]['price'] = detail_item['creatinine_price']
			data['syousai'][kk]['code'] = detail_item['creatinine_code']
			detail_item['creatinine_price'] = None
			detail_item['creatinine_price'] = None

		if data['syousai'][kk]['price'] is not None:
			detail_calc_data = int(detail_calc_data) + int(data['syousai'][kk]['price'])

	# 1:基本的な健診,2:詳細な健診,3:追加健診,4:人間ドック
	for pricedata in range(1,5):					#詳細健診用の4か所を埋める
		k = str(pricedata)

		data[k] = {}
		data[k]['section'] = {}
		data[k]['value'] = {}
		data[k]['rate'] = {}
		data[k]['limit'] = {}
		data[k]['Calc'] = {}
		ex_rate = int(zen2han(xmlCcard['ccard'][k]['examine_rate'])) if k in xmlCcard['ccard'] and 'examine_rate' in xmlCcard['ccard'][k] and xmlCcard['ccard'][k]['examine_rate'] is not None and len(xmlCcard['ccard'][k]['examine_rate']) > 0 else None
		ex_value = int(zen2han(xmlCcard['ccard'][k]['examine_value'])) if k in xmlCcard['ccard'] and 'examine_value' in xmlCcard['ccard'][k] and xmlCcard['ccard'][k]['examine_value'] is not None and len(xmlCcard['ccard'][k]['examine_value']) > 0 else None
		in_limit = int(zen2han(xmlCcard['ccard'][k]['insurer_limit'])) if k in xmlCcard['ccard'] and 'insurer_limit' in xmlCcard['ccard'][k] and xmlCcard['ccard'][k]['insurer_limit'] is not None and len(xmlCcard['ccard'][k]['insurer_limit']) > 0 else None

		#各窓口負担データ
		if ex_rate == None and ex_value == None:
			data[k]['section'] = '1'
			data[k]['value'] = '0'
			data[k]['rate'] = None
			data[k]['Calc'] = 0
		elif ex_rate is not None and ex_rate > 0:
			data[k]['section'] = '3'
			data[k]['value'] = '0'
			data[k]['rate'] = str(ex_rate * 100)			#t_appoint.xml_ccardの負担率は小数点表記のため、パーセントに変換
			if k == '2':
				data[k]['Calc'] = int(round(detail_calc_data * ex_rate / 100,0))
			elif k == '3':
				data[k]['Calc'] = int(round(tk_calc_data * ex_rate / 100,0))
			else:
				data[k]['Calc'] = int(round(unitPrice * ex_rate / 100,0))
		elif ex_value is not None and ex_value > 0:
			data[k]['section'] = '2'
			data[k]['value'] = str(ex_value)
			data[k]['rate'] = None
			if k == '2':
				if detail_calc_data > ex_value:
					data[k]['Calc'] = ex_value
				else:
					data[k]['Calc'] = detail_calc_data
			elif k == '3':
				if tk_calc_data > ex_value:
					data[k]['Calc'] = ex_value
				else:
					data[k]['Calc'] = tk_calc_data
			else:
				if unitPrice > ex_value:
					data[k]['Calc'] = ex_value
				else:
					data[k]['Calc'] = unitPrice
		else:
			data[k]['section'] = '1'
			data[k]['value'] = '0'
			data[k]['rate'] = None
			data[k]['Calc'] = 0

		#保険者負担上限がある場合はその内容を表示する
		if in_limit is not None:
			data[k]['section'] = '4'
			data[k]['value'] = in_limit
			data[k]['rate'] = None
			data[k]['limit'] = in_limit
			if k == '2':
				data[k]['Calc'] = detail_calc_data - in_limit if detail_calc_data > in_limit else 0
			elif k == '3':
				data[k]['Calc'] = tk_calc_data - in_limit if tk_calc_data > in_limit else 0
			else:
				data[k]['Calc'] = unitPrice - in_limit if unitPrice > in_limit else 0

		calc_data += data[k]['Calc']


	#請求区分データ作成
	if detail == '2' and additional == '2':
		#基本的な健診
		data['seiSec'] = '1'
	elif detail == '1' and additional == '2':
		#基本的な健診＋詳細な健診
		data['seiSec'] = '2'
	elif detail == '2' and additional == '1':
		#基本的な健診+追加健診
		data['seiSec'] = '3'
	else:
		#基本的な健診+詳細な健診+追加健診
		data['seiSec'] = '4'

	#委託料単価区分
	data['itakuUnitPriceSec'] = xmlAttribute['exam_class'] if 'exam_class' in xmlAttribute and xmlAttribute['exam_class'] is not None else 1

	#人間ドックコースを受信していた場合は、基本的な健診単価を0にする
	if conf.examInfo['courseName'] is not None and '人間ドック' in conf.examInfo.values():
		data['kihonUnitPrice'] = 0


	#単価(合計）
	data['UnitPriceCalc'] = str(int(unitPrice + detail_calc_data + tk_calc_data))

	#窓口負担額(合計)
	data['mdAllCalc'] = str(calc_data)

	#他健診負担金額		//他健診がないのでベース(js)の処理も0で返している。今後必要になったら計算を入れる
	data['taAllCalc'] = '0'

	#請求金額(単価合計-窓口負担金額合計)
	data['billingAmount'] = str(int(data['UnitPriceCalc']) - calc_data)

	return data

# （特定健診）決済情報ファイル２
def get_price_data2(headerData, reAttribute, xmlMeSidEitem, mCriterionData):
	# reAttributeの種別
	# 0：無効
	# 1：特健基本
	# 2：特健詳細
	# 3：その他追加
	# 4：その他ドック
	jyushinKoumoku = [k for k,v in conf.inspStdOptData['eitem'].items() if v in ['3','4']]
	kubunTypeName = conf.outsource_config['root']['outsource']['columns']['attribute_item']['s_class']
	coursePriceName = conf.outsource_config['root']['outsource']['columns']['attribute_item']['course_price']
	priceTagName = conf.outsource_config['root']['outsource']['columns']['attribute_item']['tokken_price']
	t_price_calc = 0

	# 不要な要素は削除
	del reAttribute[coursePriceName]
	# 追加項目のデータ集め
	kubunAddSid = sorted([k for k,v in reAttribute.items() if v[kubunTypeName] == '3' and v[priceTagName] is not None])
	targetSid = list(set(jyushinKoumoku) & set(kubunAddSid))
	governmentCode = {}
	dataJlac10 = None
	data = {k:None for k in headerData.values()}

	for s1,k1 in mCriterionData.items():
		gSidCri = k1['sid_criterion']
		gCri = mCriterionData[s1][gSidCri]
		if 'eitem' not in gCri: continue
		for s2,k2 in gCri['eitem'].items():
			eiSid = k2['sid']
			eiSidCri = k2['sid_criterion']
			eiCri = gCri['eitem'][s2][eiSidCri]
			if 'government-code' not in eiCri: continue
			governmentCode[eiSid] = {}
			governmentCode[eiSid] = {**eiCri['government-code'], **{}}

	if governmentCode is not None or len(governmentCode) > 0:
		dataJlac10 = {k:v for k,v in governmentCode.items() if k in targetSid}

	data[headerData['id']] = conf.examInfo['id']
	for n,k in enumerate(kubunAddSid):
		try:
			idx = '{:0>2}'.format(n + 1)
			headerCode = 'unit{}Code'.format(idx)
			headerprice = 'unit{}Price'.format(idx)
			data[headerData[headerCode]] = dataJlac10[k]['value']
			data[headerData[headerprice]] = reAttribute[k][priceTagName]
			t_price_calc += int(reAttribute[k][priceTagName])	#追加健診単価合計(kekka1計算用)
		except Exception as err:
			msg = 'xml error: {}'.format(err)
			Log().log(msg, LOG_ERR)
	return data,t_price_calc

# CSVの出力フォーマットを作成
# 詳細は(https://docs.python.org/ja/3/library/csv.html)
def get_csv_format(csv_option):
	config = {			# 初期値
		'quoting'		: csv.QUOTE_MINIMAL,	# QUOTE_ALL:1, QUOTE_MINIMAL:0, QUOTE_NONNUMERIC:2, QUOTE_NONE:3
		'doublequote'	: False,
		'terminated'	: '\n',
		'delimiter'		: ',',
		'encoding'		: 'UTF-8'
	}

	if 'quoting' in csv_option:
		if csv_option['quoting'] == 'QUOTE_ALL':
			config['quoting'] = csv.QUOTE_ALL
		elif csv_option['quoting'] == 'QUOTE_MINIMAL':
			config['quoting'] = csv.QUOTE_MINIMAL
		elif csv_option['quoting'] == 'QUOTE_NONNUMERIC':
			config['quoting'] = csv.QUOTE_NONNUMERIC
	if 'enclosed' in csv_option:
		if csv_option['enclosed'] == 'DOUBLE_QUOTE':
			config['doublequote'] = True
	if 'terminated' in csv_option:
		if csv_option['terminated'] == 'CRLF':
			config['terminated'] = '\r\n'
	if 'delimiter' in csv_option:
		if re.match(r'\\t', csv_option['delimiter']):
			config['delimiter'] = '\t'
		else:
			config['delimiter'] = csv_option['delimiter']
	if 'encoding' in csv_option:
		config['encoding'] = csv_option['encoding']

	return config

# CSVに出力するデータをソートする
def get_csv_sort_data(csv_data, csv_config, sort_cond):

	# データ件数が1件以下ならソートしない
	if len(csv_data) <= 1:
		return csv_data

	sort_data = []
	for row in csv_data:
		sort_data.append(collections.OrderedDict(row))

	# 取得しているデータは全て同じものなので、listの1個目からkeyを用意する
	key_list = csv_data[0].keys()

	# ソートに使用するデータをソートする（TODO: 優先度:低->高の順にソートしたい）
	s_sort_cond = sorted(sort_cond, key=lambda x: -x['priority'])
	for cond in s_sort_cond:			# priorityでソートしたデータを順繰り回してCSVデータのソートを行う
		rev_flag = False
		if cond['key'] in key_list:		# keyが含まれている場合
			idx = cond['key']	# dictはkeyでソートをかける
			if cond['direction'] == '2':
				rev_flag = True

			#sort_data = sorted(sort_data, key=itemgetter(idx), reverse=rev_flag)	# Noneがいるとこける。。。
			#sort_data = sorted(sort_data, key=lambda x:(x[idx] is not None, x[idx]), reverse=rev_flag)	# keyが存在しないとこける
			sort_data = sorted(sort_data, key=lambda x:(x.get(idx) is not None, x.get(idx)), reverse=rev_flag)

	return sort_data

# SQLのクエリ結果（ROW）のXMLが格納されているカラムの中身（XMLデータ）を丸ごと渡す
# ElementTreeのXMLオブジェクトを返す
def getRow2Xml(row):
	# ASCIIコード表参照
	pt1CtrlCode = re.compile('[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]')	# 改行なし
	if row is None or len(row) < 1 or type(row) != str:
		return None

	try:
		xml = pt1CtrlCode.sub('', row)
		xmlObj = ET.fromstring(xml)
	except Exception as err:
		msg = 'xml error: {}'.format(err)
		Log().log(msg, LOG_ERR)

	return xmlObj

def sql_row_check(row):
	ret = False

	if row is None:
		msg = 'row is None'
	elif len(row) < 1:
		msg = 'row is len=0'
	elif b'code' in row:
		msg = 'sql return code: ' + str(row[b'code'])
	else:
		ret = True

	if ret == False:
		func = str(inspect.stack()[1][3])		# 呼び出し元の関数名
		Log().dbg_log(func + ' : ' + msg, LOG_WARN)

	return ret

# FIXME: クラス。。。オブジェクト。。。うーん。。。
def get_sql_query(query, param=None):
	row = Sql().once(query, param)
	if sql_row_check(row) == False:
		msg = '[sql query] {}'.format(query)
		msg = '{}, param={}'.format(msg, param) if param is not None else ''
		Log().log(msg)
		return None
	return row
def get_sql_query2(query, param=None):
	row = Sql().once2noexit(query, param)
	if sql_row_check(row) == False:
		msg = '[sql query] {}'.format(query)
		msg = '{}, param={}'.format(msg, param) if param is not None else ''
		Log().log(msg)
		return None
	return row
####
def get_sm_morg():
	query = 'SELECT * FROM sm_morg WHERE sid = ?;'
	param = (config_data['sid_morg'],)
	row = get_sql_query(query, param)
	return row
####
def get_m_outsource(sid_section=None, sid=None, sid_morg=None, subFormCode=None):
	if sid_section is None: return None
	if sid_morg is None: sid_morg = config_data['sid_morg']
	query = 'SELECT * FROM m_outsource WHERE sid_morg = ? AND sid_section = ? '
	if sid is not None:
		query += ' AND sid = ?'
		param = (sid_morg, sid_section, sid)
	# 協会けんぽ用に仕込んだもの（医療機関個別＋ベースのm_outsource）を区別して取得するためのクエリ
	elif subFormCode is not None and len(subFormCode) > 0:
		query += ' AND ExtractValue(xml_outsource, \'/root/outsource/condition/form_code_subType\')=?'
		param = (sid_morg, sid_section, subFormCode)
	else:
		query += ';'
		param = (sid_morg, sid_section)
	row = get_sql_query(query, param)
	return row
####
def get_t_appoint(sid=None, sid_examinee=None, exam_id=None):
	if sid is not None:
		add_query = 'AND sid = ?'
		param = (config_data['sid_morg'], sid)
	elif sid_examinee is not None:
		add_query = 'AND sid_examinee = ?'
		param = (config_data['sid_morg'], sid_examinee)
	elif exam_id is not None:
		add_query = 'AND ExtractValue(xml_examinee, "/root/examinee/id") = ?'
		param = (config_data['sid_morg'], exam_id)
	else:
		return None
	query = 'SELECT * FROM t_appoint where sid_morg = ? ' + add_query + ';'
	row = get_sql_query(query, param)
	return row
####
def get_m_examinee(sid_examinee=None, exam_id=None):
	if sid_examinee is not None:
		add_query = 'sid = ?'
		param = (config_data['sid_morg'], sid_examinee)
	elif exam_id is not None:
		add_query = 'ExtractValue(xml_examinee, "/root/examinee/id") = ?'
		param = (config_data['sid_morg'], exam_id)
	else:
		return None
	query = 'SELECT *,ExtractValue(xml_examinee, "/root/examinee/id") as exam_id FROM m_examinee where sid_morg = ? ' + add_query + ';'
	row = get_sql_query(query, param)
	return row
####
def get_t_appoint_me(sid_appoint):
	query = 'SELECT * FROM t_appoint_me where sid_morg = ? AND sid_appoint = ?;'
	param = (config_data['sid_morg'], sid_appoint)
	row = get_sql_query(query, param)
	return row
####
def get_m_criterion(sid, s_exam=None, sid_exam=None):
	add = ''
	query = 'SELECT * FROM m_criterion WHERE sid_morg = ? '
	if sid is not None:
		add += ' AND sid = ? '
		param = (config_data['sid_morg'], sid)
	elif s_exam is not None and sid_exam is not None:
		add += ' AND s_exam = ? AND sid_exam = ? '
		param = (config_data['sid_morg'], s_exam, sid_exam)
	else:
		return None
	query += add + ' ;'
	row = get_sql_query(query, param)
	return row
####
# s_examとかsid_exam等他でも絞り込みこみたい場合に、絞り込み条件を渡して使用する
def get_m_criterion_plus(sid, add_query=None):
	query = 'SELECT * FROM m_criterion WHERE sid_morg = ? AND sid = ?'
	if add_query is not None:
		query += ' ' + add_query
	query += ';'	# 閉じる
	param = (config_data['sid_morg'], sid)
	row = get_sql_query(query, param)
	return row
####
def get_m_me_attribute(sid_me, sid_criterion):
	query = 'SELECT * FROM m_me_attribute WHERE sid_morg = ? AND sid_me = ? AND sid_criterion = ?;'
	param = (config_data['sid_morg'], sid_me, sid_criterion)
	row = get_sql_query(query, param)
	return row
####
def get_m_qualitative(sid):
	query = 'SELECT * FROM m_qualitative WHERE sid_morg = ? AND sid = ?;'
	param = (config_data['sid_morg'], sid)
	row = get_sql_query(query, param)
	return row
####
def get_m_opinion_rankset(sid):
	query = 'SELECT * FROM m_opinion_rankset WHERE sid_morg = ? AND sid = ?;'
	param = (config_data['sid_morg'], sid)
	row = get_sql_query(query, param)
	return row
####
# 1個の場合でもtuple形式で渡すこと
def get_m_section_psid(psid):
	if psid is not None and (type(psid) != tuple):
		return None
	psid_query = 'AND ('
	for item in psid:
		if str(item).isdigit() and int(item) > 0:
			#psid_query += ' psid=' + item + ' \n '
			psid_query += ' psid=? \n '	# 区切り文字。最後にstrip()で剥がしてORに置換する
		else:
			return None
	psid_query = psid_query.strip().replace('\n',' OR ')
	psid_query += ' )'
	query = 'SELECT * FROM m_section WHERE sid_morg = {} {};'.format(config_data['sid_morg'], psid_query)
	row = get_sql_query(query, psid)
	conf.m_section['psid'] = psid
	return row
####
def get_m_user(sid):
	query = 'SELECT * FROM m_user WHERE sid_morg = ? AND sid = ?;'
	param = (config_data['sid_morg'], sid)
	row = get_sql_query(query, param)
	return row
####
#受診券チェックフラグを拾うためにテーブル追加
def get_t_contract(sid_cntracot):
	query = 'SELECT * FROM t_contract WHERE sid_morg = ? AND sid = ?;'
	param = (config_data['sid_morg'],sid_cntracot)
	row = get_sql_query(query,param)
	f_check = row[0]['f_check']
	return f_check
####
#特定健診用の情報を拾うために追加
def get_t_contract_me_attribute(sid_me, sid_contract):
	query = 'SELECT * FROM t_contract_me_attribute WHERE sid_morg = ? AND sid_me = ? AND sid_contract = ?;'
	param = (config_data['sid_morg'], sid_me, sid_contract)
	row = get_sql_query(query, param)
	return row
####
# 特定健診の団体絞り込みで使う
# カルテIDと、団体のsid
# 保険団体の団体番号と、代行機関の番号を検索した結果を返す
def search_t_apo2morg(sid, orgSid):
	query = 'SELECT \
		t_apo.sid, \
		t_apo.sid_examinee, \
		EXTRACTVALUE(t_apo.xml_examinee, "/root/examinee/id") AS "examieeId", \
		EXTRACTVALUE(t_apo.xml_xorg, "//org[s_org[text()=11]]/n_org") AS "orgId", \
		EXTRACTVALUE(morg.xml_org, "//org/n_org") AS "dorgId" \
	FROM t_appoint t_apo \
		JOIN m_org morg ON t_apo.sid_morg = morg.sid_morg AND morg.sid = ? \
	WHERE t_apo.sid_morg = ? AND t_apo.sid = ?;'
	param = (orgSid, config_data['sid_morg'], sid)
	row = get_sql_query(query, param)
	return row

# SQL接続用のObj作成
# TODO: classに統合してもいいんじゃない？でもclassがよくわかってないから放置しちゃう
# TODO: ユーザ名とパスワードに特殊文字（例：＃）が含まれていた場合、意図しない分解がされてしまうのを対処しているが、'/'含め、一部対処が難しいのも存在する
# どうしても標準モジュールでダメなら最後は自前パースになる。。。
def sql_session():
	url = urllib.parse.quote(config_data['mysql'], safe=':@/')					# 特殊文字を%xx形式にエスケープ（safeで指定した文字は対象外、文字、数字、および '_.-' も対象外）
	url = urllib.parse.urlparse(url, scheme='mysql', allow_fragments=False)		# 分解
	urlname = urllib.parse.unquote(url.username)								# エスケープしていた文字を戻す
	urlpass = urllib.parse.unquote(url.password)

	#Log().dbg_log(url)
	conn = mysql.connector.connect(
		host = url.hostname,
		#port = url.port,
		user = urlname,
		password = urlpass,
		database = url.path[1:],		# /が含まれているため、2文字目から取得
		#buffered = True,
		buffered = False,
		use_pure = True,				# prepaerd=TrueでのNotImplementedError対応
		charset = 'utf8mb4',
		collation = 'utf8mb4_general_ci',
		connection_timeout = 300
	)

	return conn

# 全角英数記号を半角にする
# TODO: 全角ハイフンとマイナスは別物のため、unicodeの正規化では変換されない
# そのため、個別対応として全角ハイフンを半角マイナスに置換している
class Zenkaku2Hankaku:
	# 参考：　https://docs.python.org/ja/3/library/unicodedata.html		# Unicodeの正規化というらしい

	def __init__(self,):
		self.ret = None
		self.tmp = None

	def zen2han(self, moji):
		if moji is None:
			return None
		self.tmp = moji.strip()						# 文字列前後の空白や改行を落とす
		self.tmp = self.tmp.replace('‐','-')		# 全角ハイフン(0x815D)を半角マイナスへ置換。
		self.tmp = self.tmp.replace('ー','-')		# 全角長音「ー」(0x815B)が紛れている。。。パッと見マイナスに見えるからなぁ。
		self.tmp = self.tmp.replace('－','-')		# 0x817C
		self.ret = unicodedata.normalize('NFKC', self.tmp)

		return self.ret


#### MySQL接続用
# FIXME: 考慮不足、知識不足、もうちょっとどうにかしたい
# objectをコンフィグに突っ込んで、1セッション内でQuery実行できるようにしたい
# fetchoneにも対応させたい
class Sql:
	def __init__(self,):
		self.cnx = None
		self.cur = None
		self.result = None

	def connect_session(self,):
		try:
			self.cnx = sql_session()
			self.cnx.is_connected()
		except Exception as err:
			traceback_log(err)

	def create_cursor(self,):
		# https://bugs.mysql.com/bug.php?id=92700
		# dictionaryとpreparedの両方Trueは未サポート(2018/10/30)
		#self.cur = self.cnx.cursor(dictionary=True, prepared=prepared_opt)
		self.cur = self.cnx.cursor(prepared=True)
		#self.cur = self.cnx.cursor(cursor_class=mysql.connector.cursor.MySQLCursorPrepared)

	def open(self,):
		self.connect_session()
		self.create_cursor()

	def session_close(self,):
		self.cnx.close()

	def cursor_close(self,):
		self.cur.close()

	def close(self,):
		self.cursor_close()
		self.session_close()

	def ret2dict(self, cur=None, data=None):
		# preparedオプションを使うために、dictionaryオプションが無効となっている、そのためここでdict型に変換する
		ret = None
		if cur is None and data is None:
			data = self.result
			cur = self.cur
		elif cur is not None and data is None:
			return ret
		cLen = cur.rowcount
		if cLen > 0:
			tmp = None
			# ストアド内部でエラーになるとコードが返却されるので終わり
			if len(cur.column_names) == 1 and cur.column_names[0] == 'code':
				_exit('info', 'sql return code: ' + str(data[0]))
			if type(data) == list:
				tmp = [dict(zip(cur.column_names, row)) for row in data]
			elif type(data) == tuple:
				tmp = dict(zip(cur.column_names, data))
			else:
				Log().log('unknown sql data', LOG_ERR)
				return data
			ret = tmp
		return ret

	# 使い切り
	# fetchall
	def once(self, query=None, param=None):
		#dbg_log = Log().dbg_log
		ret = None
		if query is None:
			return ret
		prepared_opt = True if param is not None else False
		self.open()
		try:
			#dbg_log(query)
			if prepared_opt:
				self.cur.execute(query, param)
			else:
				self.cur.execute(query)
			self.result = self.cur.fetchall()
			ret = self.ret2dict()
		except Exception as err:
			func = str(inspect.stack()[1][3])		# 呼び出し元の関数名
			#msg = '{}:"{}":"{}"'.format(func, query, param)
			msg = '{}:"{}"'.format(func, self.cur.statement)
			Log().log(msg)
			traceback_log(err)

		self.cur.close()

		return ret

	# 接続は自分で閉じること
	def once2noexit(self, query=None, param=None):
		#dbg_log = Log().dbg_log
		ret = None
		if query is None:
			return ret
		prepared_opt = True if param is not None else False
		try:
			#dbg_log(query)
			self.create_cursor()
			if prepared_opt:
				self.cur.execute(query, param)
			else:
				self.cur.execute(query)
			self.result = self.cur.fetchall()
			ret = self.ret2dict()
		except Exception as err:
			func = str(inspect.stack()[1][3])		# 呼び出し元の関数名
			msg = '{}:"{}":"{}"'.format(func, query, param)
			Log().log(msg, LOG_ERR)
			traceback_log(err)

		self.cursor_close()

		return ret


