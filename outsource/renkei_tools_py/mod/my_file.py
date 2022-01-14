#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import codecs
import re
import csv
import json
import xml.etree.ElementTree as ET


# URLエンコード（XMLタグ内に特殊文字がいる場合のエスケープ処理）が必要な可能性


# ASCIIコード表参照
regPt1CtrlCode = re.compile('[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]')	# 改行なし(\r\n)
regPt2CtrlCode = re.compile('[\x00-\x1F\x7F]')						# 改行含む
# 改行のみ
regPt3CtrlCode = re.compile(r'^[\r\n]+$')
# 先頭が＃ではない
regPt1comment = re.compile(r'^[^#]')
regPt1dataStart = re.compile(r'^"')
regPt1dataEnd = re.compile(r'.+"$')

def utf8bomcheck(filePath):
	ret = False
	BOMLEN = len(codecs.BOM_UTF8)
	try:
		with open(filePath, mode='r+b') as fp:
			chunk = fp.read(BOMLEN)
			if chunk == codecs.BOM_UTF8:
				ret = True
	except Exception as err:
		logger.debug(err)
		raise
	return ret


def csvRead(filePath, encoding='UTF-8', flagHeader=True):
	if filePath is None:
		eMsg = 'args error filePath'
		logger.debug(eMsg)
		raise Exception(eMsg)

	# コメント行の判定をやろうとしたけどむりっぽ
	def commentSkip(obj):
		for n1,d1 in enumerate(obj):
			if n1 == 0:
				yield d1
			elif regPt3CtrlCode.match(d1) is None and len(d1) > 0:
				spd1 = d1.split(',')
				for n2,d2 in enumerate(spd1):
					flagYield = True
					if n2 == 0:
						if regPt1dataStart.match(d2) is not None and regPt1dataEnd.match(d2) is not None:
							if regPt1comment.match(d2) is None:
								break
						else:
							flagYield = False
							break
					else:
						break
				if flagYield == True:
					yield d1


	try:
		if encoding.upper() in ['UTF-8', 'utf8']:
			utf8Bomflag = utf8bomcheck(filePath)
			if utf8Bomflag == True: encoding = 'UTF-8-SIG'

		with open(filePath, mode='r', encoding=encoding, newline=None) as fr:
			# 制御コードっぽいものは削除。コメント行っぽいのも無視（TODO: ヘッダ行の先頭が＃だとヘッダが無視される
			# ヘッダありファイル
			if flagHeader:
				obj = csv.DictReader(regPt1CtrlCode.sub('', k) for k in fr)
				#obj = csv.DictReader(commentSkip(fr))
			# ヘッダなしファイル
			else:
				obj = csv.reader((regPt1CtrlCode.sub('', k) for k in fr))
			data = [k for k in obj]

	except UnicodeDecodeError as err:
		logger.error('csv file encoding error, {}'.format(err))
		return

	except Exception as err:
		logger.debug('{}'.format(err))
		raise

	return data


# 気に入らないから保留
#def csvReadNoHeader(filePath, encoding=None):
#	if filePath is None:
#		return
#
#	try:
#		with open(filePath, mode='r', encoding=encoding, newline=None) as fr:
#			rows = [regPt1CtrlCode.sub('', k).strip() for k in fr]
#			maxLen = len(max([k.split(',') for k in rows], key=lambda x:len(x)))		# 全データ内のうち、最大のカラム数を取得
#			header = ['col'+str(k) for k in range(maxLen)]		# 「colxxx」という名前のヘッダを作成
#
#			# 再格納のついでに、行頭が「＃」で始まらないものだけ抽出。
#			raw = [k for k in rows if pt1comment.match(k) and len(k) > 0]
#			if raw is None or len(raw) < 1:
#				return None
#
#			obj = csv.DictReader(raw, fieldnames=header)
#
#			data = [k for k in obj]
#
#	except Exception as err:
#		logger.warning('{}'.format(err))
#		pass
#
#	return data


def csvWrite(filePath, data, header, encoding=None):
	if filePath is None:
		return
	if header is None:
		return

	try:
		with open(filePath, mode='w', encoding=encoding, newline='\n') as fw:
				fpw = csv.DictWriter(fw, fieldnames=header, extrasaction='ignore')
				# ヘッダ書き込み
				fpw.writeheader()
				# データ書き込み
				for row in data:
					fpw.writerow(row)

	except Exception as err:
		logger.debug('{}'.format(err))
		raise


def xmlRead(filePath, encoding=None):
	if filePath is None:
		return

	try:
		with open(filePath, mode='r', encoding=encoding, newline=None) as fr:
			xmlRaw = ''.join([regPt2CtrlCode.sub('', k).strip() for k in fr])
			if xmlRaw is None or len(xmlRaw) < 1:
				return None

	except UnicodeDecodeError as err:
		logger.error('xml file encoding error, {}'.format(err))
		return

	except Exception as err:
		logger.debug('{}'.format(err))
		raise

	xmlObj = ET.fromstring(xmlRaw)

	return xmlObj

# xml.etree.ElementTreeのオブジェクトからファイルを作成
def xmlWrite(filePath, xmlObj):
	if filePath is None:
		return
	if xmlObj is None:
		return
	if type(xmlObj) != type(ET):
		return

	try:
		xmlObj.write(filePath)

	except Exception as err:
		logger.debug('{}'.format(err))
		raise


def textRead(filePath, encoding=None):
	if filePath is None:
		logger.debug('args error filePath')
		raise

	try:
		with open(filePath, mode='r', encoding=encoding, newline=None) as fr:
			# 制御コードっぽいものは削除。＃で始まる行はスキップ
			obj = (regPt1CtrlCode.sub('', k) for k in fr.readlines() if len(k) > 0 if regPt1comment.match(k))
			data = ''.join([k for k in obj])

	except UnicodeDecodeError as err:
		logger.error('text file encoding error, {}'.format(err))
		return

	except Exception as err:
		logger.debug('{}'.format(err))
		raise

	return data


def textWrite(filePath, data, encoding=None):
	if filePath is None:
		eMsg = 'args error filePath'
		logger.debug(eMsg)
		raise Exception(eMsg)

	try:
		wType = 'w'
		if type(data) == bytes:
			wType = 'wb'
		with open(filePath, mode=wType, encoding=encoding, newline=None) as fw:
			if type(data) == list:
				_data = '\n'.join(data)
				fw.writelines(_data)
			elif type(data) == str:
				fw.write(data)
			else:
				logger.warning('unknown type, text write failed')

	except Exception as err:
		logger.debug('{}'.format(err))
		raise

	return


def jsonRead(filePath, encoding=None):
	if filePath is None:
		logger.debug('args error filePath')
		raise

	try:
		with open(filePath, 'r', encoding=encoding, newline=None) as fr:
			data = json.load(fr)

	except UnicodeDecodeError as err:
		logger.error('json file encoding error, {}'.format(err))
		return

	except Exception as err:
		logger.debug('{}'.format(err))
		raise

	return data
