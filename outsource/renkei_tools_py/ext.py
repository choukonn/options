#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import os
import sys
import shutil
import datetime
import pathlib
import glob
import psutil
from time import sleep
import re

# myapp
from .mod import common as cmn
from .mod import loggingConfig as myLog
from .plgCmd.m_i18n_dictionary import geti18nCodeMap

success = cmn.success
warning = cmn.warning
error = cmn.error

threadCheckItem = {}


class _Container():
	pass

procStatus = _Container()
procStatus.success = 'OK'
procStatus.warning = 'WARNING'
procStatus.error = 'NG'
procStatus.unknown = 'UNKNOWN'


# 終了処理
def endproc(sidMorg, *, plConfig, fp, sts=None, errMsg=None):
	logger.debug(' * start func:{}'.format(sys._getframe().f_code.co_name))
	plgName = plConfig['plgName'] if 'plgName' in plConfig else None
	retStatus = procStatus.error

	def isFileExists(fp):
		try:
			with open(fp, mode='r') as fp:
				return True
		except:
			return False

	if fp is None:
		# ファイルが無ければ何もしない
		return
	else:
		if isFileExists(fp) != True:
			logger.error('[{}][{}] move faild: file not found, {}'.format(sidMorg, plgName, fp))
			return
	if sts is not None:
		retStatus = sts
	if retStatus == success: status = procStatus.success
	elif retStatus == warning: status = procStatus.warning
	elif retStatus == error: status = procStatus.error
	else: status = procStatus.unknown
	nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
	try:
		if 'done' in plConfig['path'].keys():
			mvPath = plConfig['path']['done']
		else:
			mvPath = 'done'

		ymdName = datetime.date.today().strftime('%Y/%m/%d')
		mvPath = cmn.baseConf['basePath'] + '/' + sidMorg + '/' + mvPath
		donePath = pathlib.Path(mvPath).joinpath(ymdName)
		if donePath is not None:
			donePath.mkdir(parents=True, exist_ok=True)			# 移動先ディレクトリの作成
		oldPath = str(fp)
		tmpNewName = re.sub('.WORK$', '', fp.name)				# 末尾に付与されていたら削除する
		newPath = str(donePath.joinpath('{}.{}_{}'.format(tmpNewName, status, nowTime)))
	except Exception as err:
		logger.error(err)
		raise

	try:
		if errMsg is not None and len(errMsg) > 0:
			if 'err' in plConfig['path'].keys():
				errFilePath = pathlib.Path(cmn.baseConf['basePath']).joinpath(plConfig['path']['err'], tmpNewName + '.log')
				cmn.modFile.textWrite(errFilePath, errMsg, encoding='UTF-8')
	except Exception as err:
		logger.error('[{}][{}] create error file faild: {}'.format(sidMorg, plgName, str(fp.name)))
		pass

	try:
		# rename & move
		if plConfig['procEndFile'] == '1':
			logger.info('[{}][{}] file move: {} => {}'.format(sidMorg, plgName, oldPath, newPath))
			shutil.move(oldPath, newPath)
		# 削除
		else:
			logger.info('[{}][{}] file delete: {}'.format(sidMorg, plgName, str(fp.name)))
			fp.unlink()
	except:
		logger.error(err)
		pass


# ファイルサイズ取得
def getFileSize(fp):
	# pathlibオブジェクトを渡すこと
	if fp is None:
		return None
	return fp.stat().st_size


# ファイルオープンチェック
def isFileOpen(fp):
	logger.debug(' * start func:{}'.format(sys._getframe().f_code.co_name))
	pinfo = None
	pinfoCmd = None
	ret = False

	fileSize = getFileSize(fp)
	if fileSize is None and fileSize < 1:
		return ret

	try:
		# プロセスリストの取得
		#pinfo = pl.as_dict(attrs=['pid', 'name', 'username', 'cmdline'])
		# cmdlineが空のプロセスは除外した上で取得
		pinfo = [k.as_dict(attrs=['pid', 'cmdline']) for k in psutil.process_iter() if len(k.as_dict(attrs=['cmdline'])['cmdline']) > 0]
		#_pinfoCmd = [k for k in _pinfo['cmdline'] if k == str(self.fp)]
		pinfoCmd = list(filter(lambda x : str(fp) in x['cmdline'] or fp.name in x['cmdline'], pinfo))
		# 一致するファイルPATHが存在したらファイルオープンされていると判定
		if pinfoCmd is not None and len(pinfoCmd) > 0:
			ret = True
	except psutil.NoSuchProcess:
		pass

	return ret


# ファイルリスト作成
def getFileList(sidMorg, plgName, plgDir, plConfig, ignoreList=[]):
	#logger.debug(' * start func:{}'.format(sys._getframe().f_code.co_name))
	_suffixPath = cmn.baseConf['plgConfig'].plgTargetSuffixPath[plgName][sidMorg]
	suffixPath = _suffixPath.split(',')
	fileList = []
	regPt = None
	if 'fileName' in plConfig and plConfig['fileName'] is not None and len(plConfig['fileName']) > 0:
		regPt = re.compile('{reg}'.format(reg=plConfig['fileName']))

	# ファイル名チェック
	def nameCheck(fpath, plConfig):
		flag = False
		suffix = fpath.suffix

		# ファイル名の厳密チェック（正規表現）
		if regPt is not None:
			if regPt.match(fpath.name) is not None:
				flag = True
		# 単純な拡張子の一致
		elif 'suffix' in plConfig and suffix in plConfig['suffix'] and len(plConfig['suffix']) > 0:
			flag = True
		# ドットファイルは強制で無視
		if re.search(r"^\.", str(fpath)) is not None:
			flag = False

		return flag

	searchObj = []
	for _target in suffixPath:
		# 絶対PATHで記述されている時は、basePATHと結合しない（windowsは一切考慮しない）
		if _target[0] == '/':
			searchPath = str(pathlib.Path(_target))
		else:
			searchPath = str(plgDir.joinpath(_target))
		# list型の結合
		searchObj.extend([pathlib.Path(k) for k in glob.glob(searchPath) if pathlib.Path(k).is_file()])
		if searchObj is not None and len(searchObj) > 0:
			logger.debug('[{p}] find file: {f}'.format(p=plgName, f=','.join([str(pathlib.Path(k)) for k in searchObj])))

	fileList = [pathlib.Path(k) for k in searchObj if pathlib.Path(k).is_file() and nameCheck(pathlib.Path(k), plConfig) and isFileOpen(k) == False and k not in ignoreList]
	if fileList is not None and len(fileList) > 0:
		fileList = sorted(fileList, key=lambda x: x.stat().st_mtime)		# 更新日時でソート
	return fileList


# プラグインコンフィグ
def plgConfigDefaultSet(sidMorg, config, plgName):
	# プラグイン側で医療機関番号を指定するのがめんどくさいので、ここで入れ替え
	plgConfMorg = {}

	for key,val in config.items():
		plgConfMorg[key] = {}
		if type(val) == dict:
			if sidMorg in val:
				plgConfMorg[key] = val[sidMorg]
			elif 'default' in val:
				plgConfMorg[key] = val['default']
			else:
				plgConfMorg[key] = None
				logger.error('[{sidMorg}] Missing "default" parameter, name:{name} key:{key}'.format(sidMorg=sidMorg, key=key, name=plgName))
		else:
			plgConfMorg[key] = val

	return plgConfMorg


# プラグイン呼び出し関数
def plgRun(**kwargs):
	"""
	sidMorg : 医療機関番号\n
	plgName : プラグイン名\n
	plgDir : プラグインが使用するディレクトリ情報（pathオブジェクト）\n
	plgconf : プラグインコンフィグ
	"""

	# 動的インポート用
	# TODO: https://www.366service.com/jp/qa/cd9d75e39cb2af1e1adb29e4f9ec5d80
	#       https://docs.python.org/ja/3/library/importlib.html
	from importlib import import_module
	from importlib.abc import Loader, MetaPathFinder
	from importlib.util import module_from_spec, spec_from_file_location

	global threadCheckItem

	logger.debug(' * start func:{}'.format(sys._getframe().f_code.co_name))

	try:
		sidMorg = kwargs['sidMorg']
		plgName = kwargs['plgName']
		plgDir = kwargs['plgDir']
		plgConf = cmn.baseConf['plgConfig'].plg[plgName]
	except Exception as err:
		logger.error(err)


	# TODO: https://qiita.com/kzm4269/items/e7e67ab6c1dd278c3d16
	def import_module_from_file_location(name, location):
		class Finder(MetaPathFinder):
			@staticmethod
			def find_spec(fullname, *_):
				if fullname == name:
					return spec_from_file_location(name, location)

		finder = Finder()
		sys.meta_path.insert(0, finder)
		try:
			return import_module(name)
		finally:
			sys.meta_path.remove(finder)


	# 呼び出し処理
	def callPlg(sidMorg, plgName, plgDir, plgConf):
		from threading import get_ident, current_thread
		module = None

		# プラグインコンフィグ
		tmp = plgConfigDefaultSet(sidMorg, plgConf, plgName)
		plgConfMorg = {k: v for k,v in tmp.items()}
		del tmp
		plgConfMorg['plgName'] = plgName

		# 解析補助用エラーデータ書き込みディレクトリが指定されているかつ、存在しなければ作成を試みる
		try:
			eFileDirPath = plgDir.joinpath(plgConfMorg['path']['err'])
			if eFileDirPath.is_dir() == False:
				eFileDirPath.mkdir(parents=True, exist_ok=True)
		except:
			pass

		threadIdent = get_ident()
		logger.info('NOTICE: {}, sidMorg: {:>6}, plgName: {}, plgDir: {}'.format(current_thread(), sidMorg, plgName, plgConfMorg['path']))
		threadCheckItem.update({str(threadIdent) : { 'info' : current_thread(), 'sidMorg' : sidMorg, 'plgName' : plgName}})

		# プラグインの動的インポート＆実行
		# FIXME: class化を完了したらインスタンスを作成して、mainスレッドからプラグインのインスタンスを呼び出すだけ。にするべきである。と今更気づいたので時間があれば修正すべし
		try:
			curDir = str(pathlib.Path(__file__).parent.resolve())
			plgMorgPath = '{}/{}'.format(curDir, plgName)
			srcFile = '{}/plg.py'.format(plgMorgPath)
			plgMorgName = '{}.{}.{}'.format(__package__, plgName, sidMorg)
			module = import_module_from_file_location(plgMorgName, srcFile)

			# ロガーへ登録
			myLog.setPlgLogger(plgMorgName)

			try:
				# 言語コードの取得
				geti18nCodeMap(sidMorg)
			except:
				pass

			# モジュール実行
			module.plg(sidMorg=sidMorg, config=plgConfMorg, plgName=plgName, plgDir=plgDir)

		except Exception as err:
			logger.exception(err)
		finally:
			logger.info('thread stop, sidMorg:[{}], plgName:[{}], threadIdent:[{}]'.format(sidMorg, plgName, threadIdent))
			if str(threadIdent) in threadCheckItem:
				del threadCheckItem[str(threadIdent)]
		return

	# 実行
	try:
		callPlg(sidMorg, plgName, plgDir, plgConf)
	except Exception as err:
		logger.exception(err)
