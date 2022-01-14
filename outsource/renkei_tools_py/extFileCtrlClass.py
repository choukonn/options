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

success = cmn.success
warning = cmn.warning
error = cmn.error

threadCheckItem = {}


class _Container():
	pass




class ExtFileCtrl():
	def __init__(self, sidMorg, *, loggerChild=None, config=None):
		try:
			self.sidMorg = sidMorg
			self.procStatus = _Container()
			self.procStatus.success = 'OK'
			self.procStatus.warning = 'WARNING'
			self.procStatus.error = 'NG'
			self.procStatus.unknown = 'UNKNOWN'

			if loggerChild is not None:
				self.logger = loggerChild
			else:
				self.logger = logger
		except Exception as err:
			self.logger.error(err)

	# 終了処理
	def endproc(self, sidMorg, *, plConfig, fp, sts=None, errMsg=None):
		#self.logger.debug(' * start func:{}'.format(sys._getframe().f_code.co_name))
		plgName = plConfig['plgName'] if 'plgName' in plConfig else None
		retStatus = self.procStatus.error

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
				self.logger.error('[{}][{}] move faild: file not found, {}'.format(sidMorg, plgName, fp))
				return
		if sts is not None:
			retStatus = sts
		if retStatus == success: status = self.procStatus.success
		elif retStatus == warning: status = self.procStatus.warning
		elif retStatus == error: status = self.procStatus.error
		else: status = self.procStatus.unknown
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
			self.logger.error(err)
			raise

		try:
			if errMsg is not None and len(errMsg) > 0:
				if 'err' in plConfig['path'].keys():
					errFilePath = pathlib.Path(cmn.baseConf['basePath']).joinpath(plConfig['path']['err'], tmpNewName + '.log')
					cmn.modFile.textWrite(errFilePath, errMsg, encoding='UTF-8')
		except Exception as err:
			self.logger.error('[{}][{}] create error file faild: {}'.format(sidMorg, plgName, str(fp.name)))
			pass

		try:
			# rename & move
			if plConfig['procEndFile'] == '1':
				self.logger.info('[{}][{}] file move: {} => {}'.format(sidMorg, plgName, oldPath, newPath))
				shutil.move(oldPath, newPath)
			# 削除
			else:
				self.logger.info('[{}][{}] file delete: {}'.format(sidMorg, plgName, str(fp.name)))
				fp.unlink()
		except:
			self.logger.error(err)
			pass


	# ファイルサイズ取得
	def getFileSize(self, fp):
		_ret = None
		# pathlibオブジェクトを渡すこと
		if fp is None:
			return _ret
		try:
			_ret = fp.stat().st_size
		except:
			raise
		return _ret

	# 処理対象ファイルの上限サイズチェック（サーバメモリを超えるファイルを食わされたら困る）
	# サイズOK: True
	# サイズNG: False
	def checkFileSize(self, fp, maxsize=None):
		_ret = False
		try:
			_defaultSize = 10 * 1024 * 1024
			if maxsize is None or type(maxsize) != int or maxsize == 0:
				_maxFileSize = _defaultSize

			_fileSize = self.getFileSize(fp)

			if _fileSize is None:
				pass
			elif _fileSize <= _maxFileSize:
				_ret = True
			elif _fileSize > _maxFileSize:
				self.logger.error('file size over, size:{} > max-size:{}'.format(_fileSize, _maxFileSize))
		except:
			raise

		return _ret

	# ファイルオープンチェック
	def isFileOpen(self, fp):
		#self.logger.debug(' * start func:{}'.format(sys._getframe().f_code.co_name))
		pinfo = None
		pinfoCmd = None
		ret = False

		# FIXME: 次のような環境の場合のファイルオープンチェック処理を強化する必要がある
		#        環境メモ： Linux-1 <-> NAS <-> Linux-2
		#        開いているプロセスがリモート側になる場合、書き込み完了前に巻き取ってしまう可能性がある
		#        書き込み完了後にリネームをかけてる方式の場合、上手いこと動く可能性があるが、要検証

		try:
			fileSize = self.getFileSize(fp)
			if fileSize is None:
				self.logger.debug('unknwon file path')
				return None
			elif fileSize < 1:
				self.logger.debug('file size [{}] byte, name:[{}]'.format(fileSize, fp.name))
				return None
		except:
			raise

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
		except Exception:
			raise

		return ret


	# ファイルリスト作成
	def getFileList(self, sidMorg, plgName, plgDir, plConfig, ignoreList=[]):
		#self.logger.debug(' * start func:{}'.format(sys._getframe().f_code.co_name))
		_suffixPath = cmn.baseConf['plgConfig'].plgTargetSuffixPath[plgName][sidMorg]
		suffixPath = _suffixPath.split(',')
		fileList = []
		regPt = None
		regPt2 = None
		if 'fileName' in plConfig and plConfig['fileName'] is not None and len(plConfig['fileName']) > 0:
			regPt = re.compile('{reg}'.format(reg=plConfig['fileName']))
		if 'givupFileName' in plConfig and plConfig['givupFileName'] is not None and type(plConfig['givupFileName']) == str and len(plConfig['givupFileName']) > 0:
			regPt2 = re.compile(r'^{reg}.+'.format(reg=plConfig['givupFileName']))

		# ファイル名チェック
		def nameCheck(fpath, plConfig):
			flag = False
			suffix = fpath.suffix

			# ファイル名の厳密チェック（正規表現）
			if regPt is not None:
				if regPt.match(fpath.name) is not None:
					flag = True
				# ギブアップファイルのチェック
				elif regPt2 is not None:
					if regPt2.search(fpath.name) is not None:
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
			self.logger.debug('find file: {}'.format(', '.join(map(lambda x: str(x.name), searchObj))))

		fileList = [pathlib.Path(k) for k in searchObj if pathlib.Path(k).is_file() and nameCheck(pathlib.Path(k), plConfig) and self.isFileOpen(k) == False and k not in ignoreList]
		if fileList is not None and len(fileList) > 0:
			fileList = sorted(fileList, key=lambda x: x.stat().st_mtime)		# 更新日時でソート
		return fileList
