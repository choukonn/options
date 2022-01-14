#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
import re
from datetime import datetime, date
import unicodedata


# myapp
from .mod.mycfg import conf as mycnf
systemUserSid = mycnf['systemUserSid']
from .mod import common as cmn
from .mod import my_sql as mySql

i18nMapLocale = {}
i18nCode = {}

# ASCIIコード表参照
pt1CtrlCode = re.compile('[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]')	# 改行なし

# 言語コードチェック用正規表現
regi18nCheck = re.compile(r'^##([A-Z]{1,}[0-9]{2,})##$')

# 正規化時の1文字変換テーブル
customNormalizeCharTable = str.maketrans({
	'‐'		: '-',		# 全角ハイフン(0x815D)を半角マイナスへ
	'ー'	: '-',		# 全角長音「ー」(0x815B)を半角マイナスへ
})


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
		raise TypeError('{} is neither a date nor a datetime'.format(d))


def datetime2text(d, fmt=None):
	if isinstance(d, datetime):
		raise TypeError('not datetime object')
	if fmt is None:
		f = r'%Y/%m/%d %H:%M:%S'
	else:
		f = fmt

	tmp = datetime.strftime(d, f)
	return tmp


def text2datetime(d, fmt=None):
	try:
		if fmt is None:
			f = r'%Y/%m/%d %H:%M:%S'
		else:
			f = fmt

		tmp = datetime.strptime(d, f)
		return tmp
	except ValueError:
		return None


# Unicodeの正規化
# 参考：　https://docs.python.org/ja/3/library/unicodedata.html
def customNormalize(moji):
	if moji is None:
		return None
	tmp = moji.strip()						# 文字列前後の空白や改行を落とす
	tmp = tmp.translate(customNormalizeCharTable)
	ret = unicodedata.normalize('NFKC', tmp)

	return ret

# 文字変換その１
xmlEscapeCharTable1 = str.maketrans({
	'<'		: '&lt;',
	'>'		: '&gt;',
	'&'		: '&amp;',
	#'"'	: '&quot;',
	#"'"	: '&apos;',
})


# 文字変換その２
def xmlEscapeChar1(char):
	# 参考：https://www.ipentec.com/document/xml-character-escape
	#     エスケープ表記 元の文字 説明
	# (1) &#x20;				スペース
	# (2) &#xA0;				スペース (UTF-8)
	# (3) &#x0A;				改行
	# (4) &#x08;				タブ
	# (5) &#x0D;				ラインフィード
	# (6) &lt;		<
	# (7) &gt;		>
	# (8) &amp;		&			アンパサンド
	# (9) &quot;	"			ダブルクォーテーション
	# (10) &apos;	'			シングルクォーテーション
	char1 = re.compile('<')
	char2 = re.compile('>')
	char3 = re.compile('&')
	#char4 = re.compile('"')
	#char5 = re.compile("'")

	try:
		if char is not None and len(char) > 0:
			if char1.search(char): char = char1.sub('&lt;', char)
			if char2.search(char): char = char2.sub('&gt;', char)
			if char3.search(char): char = char3.sub('&amp;', char)
			#if char4.search(char): char = char4.sub('&quot;', char)
			#if char5.search(char): char = char5.sub('&apos;', char)
	except Exception as err:
		logger.debug(err)
		raise
	return char


# 数字と小数部の桁数を与えて、小数部を丸めた数字を返却
# TODO: マイナスの値は考慮されていない
def numeric2conv(val, ndigit):
	num = 0
	if type(val) == str:
		# 全て数字かチェック
		if val.replace('.', '').isnumeric():
			try:
				# floatに変換(100なら100.0になる)
				num = float(val)
			except:
				# floatの変換失敗したら元データを返す。（例）「x..x」みたいに小数点が多く入力されている
				return val
		else:
			# 数字じゃない場合は元データ返却
			return val
	elif type(val) == int or type(val) == float:
		try:
			num = float(val)
		except:
			return val
	else:
		# TODO: 保険。このルートには落ちないはず
		return val

	# 桁に合わせて処理を変更
	if int(ndigit) > 0:
		# 丸める(四捨五入)
		tmp_num = float(round(num, int(ndigit)))
		# 四捨五入の結果小数部が.0になると、0が消えてしまうので桁調整を行う
		ret_mum = '{:.{digit}f}'.format(tmp_num, digit=int(ndigit))
		return ret_mum

	# 数字の欄は画面上見えないが小数点が入力できるため、画面の動きに合わせる
	elif int(ndigit) == 0:
		# 丸める(四捨五入))
		return str(int(round(num, 0)))

	# TODO: 保険。このルートには落ちないはず
	return val


# テキストのXMLをElementTreeオブジェクトへ
def xml2Obj(xml):
	if xml is None or len(xml) < 1: return None
	obj = None
	try:
		# 念のための制御コード削除
		xml = pt1CtrlCode.sub('', xml)
		obj = ET.fromstring(xml)
	except Exception as err:
		logger.debug(err)
		raise
	return obj


# y/m/d形式のテキストを与えて、date型へのオブジェクト変換を試みる
# 戻り値： 成功=True、失敗=False
def dateFormatCheck(dateStr):
	dateObj = None
	# TODO: YYYY-MM-DD
	regDateFormat1 = re.compile(r'^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})$')
	# TODO: YYYY/MM/DD
	regDateFormat2 = re.compile(r'^([0-9]{4})/([0-9]{1,2})/([0-9]{1,2})$')

	if type(dateStr) != str:
		return False

	try:
		# 区切り文字「-」
		if regDateFormat1.match(dateStr):
			dateObj = datetime.strptime(dateStr,"%Y-%m-%d")
		# 区切り文字「/」
		elif regDateFormat2.match(dateStr):
			dateObj = datetime.strptime(dateStr,"%Y/%m/%d")
		# 区切り文字なし
		else:
			dateObj = datetime.strptime(dateStr,"%Y%m%d")
	except ValueError:
		return None
	except Exception:
		raise
	return dateObj


# 言語コードに対応する文字列を取得
def i18nCode2Val(sidMorg, *, data, langMode='en-US'):
	moji = None
	lang = langMode
	if langMode is None:
		lang = 'en-US'

	check = regi18nCheck.match(data)
	if check is None:
		return data

	try:
		check2 = check.group(1)
		if check2 in i18nCode[sidMorg]:
			moji = i18nMapLocale[sidMorg][lang][check2]
	except:
		return data

	return moji


# 結果形態値のチェック
def formValueStringCheck(val):
	ret = None
	if val in ['未満', 'L', '<']:
		ret = 'L'
	elif val in ['以下', 'E', '<=']:
		ret = 'E'
	elif val in ['以上', 'U', '>=']:
		ret = 'U'
	elif val in ['超える', '超', 'O', '>']:
		ret = 'O'
	elif val in ['結果なし', 'B']:
		ret = 'B'
	elif val in ['未実施', 'N']:
		ret = 'N'
	elif val in ['測定不能', 'M']:
		ret = 'M'
	elif val in ['測定不可', 'NOT ANALYSIS', 'NA']:
		ret = 'NA'
	elif val in ['計算不可', 'NOT CALC', 'NC']:
		ret = 'NC'
	elif val in ['検体不足', 'SHORT SAMPLE', 'SS']:
		ret = 'SS'
	elif val in ['検査中止', 'CANCEL', 'C']:
		ret = 'C'
	elif val in ['空白', 'BLANK', 'BL']:
		ret = 'BL'

	return ret


# CSV上の文字列を基準値にあるやつを参照して変換したものを返却する
# 引数criterionにはあらかじめxml_qualitativeを持たせておくこと
def data2CodeFromCriterion(sidMorg, *, eSid, criterion, inValue, numericConvFlag=False):
	if sidMorg is None or eSid is None or criterion is None:
		return None

	# TODO: 基本的にはt_appoint_meのresultタグが作成できるような値をセット
	retData = {
		'value'			: None,
		'value-form'	: None,
		'code'			: None,
		'caption'		: None,		# こいつはm_criterionにいる。使う？
		'bool'			: None,		# こいつはm_criterionにいる。使う？
	}

	# 戻り値格納用。初期値は貰った値
	retVal = inValue
	# TODO: 前後に空白がある場合も考慮して剥がしておく
	value = inValue.strip() if inValue is not None and type(inValue) == str else inValue

	regCtl1 = re.compile(r'[\r\n]+')

	regQl1 = re.compile(r'[()]+')
	regQl2 = re.compile(r'^([+][-]|[-][+]|±)$')			# ＋－
	regQl3 = re.compile(r'^[-]{1}$')					# ー
	regQl4 = re.compile(r'^([+]{1}|1[+])$')				# １＋
	regQl5 = re.compile(r'^([+]{2}|2[+])$')				# ２＋
	regQl6 = re.compile(r'^([+]{3}|3[+])$')				# ３＋
	regQl7 = re.compile(r'^([+]{4}|4[+])$')				# ４＋
	regQl8 = re.compile(r'^([+]{5}|5[+])$')				# ５＋
	regQl9 = re.compile(r'^([+]{6,}|[6-9][+])$')		# ６＋～９＋
	# TODO: 以下の文字チェックはdaidai本体に合わせてメンテが必要
	# 文字チェック1
	regQl101 = re.compile(r'^(陰性|ｲﾝｾｲ)$')
	# 文字チェック2
	regQl102 = re.compile(r'^(陽性|ﾖｳｾｲ)$')
	# 文字チェック3
	regQl201 = re.compile(r'^(結果なし|結果無|けっかなし|ｹｯｶﾅｼ)$')
	# 文字チェック4
	regQl202 = re.compile(r'^(検出せず|ｹﾝｼｭﾂｾｽﾞ)$')

	regInequalitySign = re.compile(r'^[\-]*[0-9.]*?(<=|>=|<|>)[\-]*[0-9.]*?$')

	# 定性値を１～ｎ＋に寄せるための変換
	def qualitativeValueConv(val):
		moji = regQl1.sub('', customNormalize(val))
		if regQl2.match(moji): return regQl2.sub('+-', moji)
		elif regQl3.match(moji): return regQl3.sub('-', moji)
		elif regQl4.match(moji): return regQl4.sub('1+', moji)
		elif regQl5.match(moji): return regQl5.sub('2+', moji)
		elif regQl6.match(moji): return regQl6.sub('3+', moji)
		elif regQl7.match(moji): return regQl7.sub('4+', moji)
		elif regQl8.match(moji): return regQl8.sub('5+', moji)
		elif regQl9.match(moji): return regQl9.sub('6+', moji)
		# 文字列チェック
		elif regQl101.match(moji): return regQl3.sub('-', moji)
		elif regQl102.match(moji): return regQl3.sub('1+', moji)
		elif regQl201.match(moji): return regQl3.sub('結果なし', moji)
		elif regQl202.match(moji): return regQl3.sub('検出せず', moji)
		elif regi18nCheck.match(moji):
			retMoji = moji
			try:
				retMoji = i18nMapLocale['en-US'][moji]
			except:
				pass
			return retMoji
		else: return moji

	# 出力が数値
	def val2out1(val, ndigit, numericConvFlag=False):
		if val is None: return None
		if val.find('::') > 0: sepStr = '::'
		elif val.find('/') > 0: sepStr = '/'
		else: sepStr = ','
		sepVal = val.split(sepStr)
		valForm = None
		retVal = None
		escapeVal = None
		if len(sepVal) != 2:
			normalizeVal = customNormalize(sepVal[0])
			# 不等号の存在チェック
			tmp = regInequalitySign.search(normalizeVal)
			if tmp is None:
				# 検索にヒットしなければ、正規化を行ったデータを返却
				tmpVal = normalizeVal
			# 区切り文字による分割はないが、数字＋不等号なパターンがあり得る
			else:
				tmpSymbol = tmp.group(1)
				tmpFVal = formValueStringCheck(tmpSymbol)
				if tmpFVal is not None:
					valForm = tmpFVal
				tmpVal = normalizeVal.replace(tmpSymbol, '')
		else:
			for n, v in enumerate(sepVal):
				# 分割個数が2個を超える場合、無視
				if n > 2: continue
				# 値がない場合、無視
				if v is None: continue

				normalizeVal = customNormalize(v)

				# 結果形態値のチェック、戻り値がNone以外で該当したと扱う
				tmpFVal = formValueStringCheck(normalizeVal)
				if tmpFVal is not None:
					valForm = tmpFVal

				# 数値部分のチェック
				else:
					# 全て数字ではない場合、数字＋文字の結果として扱うため、元データを返却するので初期値にいれる
					tmpVal = val
					# 小数点やマイナスを除外した上で全て数字なのか判定
					if normalizeVal.replace('.', '').replace('-', '').isnumeric():
						tmpVal = normalizeVal

		try:
			retVal = tmpVal
			if numericConvFlag == True:
				retVal = numeric2conv(tmpVal, ndigit)

			# XMLに直接格納できない文字のエスケープ処理
			escapeVal = retVal.translate(xmlEscapeCharTable1)
		except Exception as err:
			logger.debug('[{}] {}'.format(sidMorg, err))
		finally:
			retData['value'] = escapeVal
			retData['value-form'] = valForm
		return retData

	# 出力が定性
	def val2out2(val, xmlObj):
		if val is None or xmlObj is None:
			retData['value'] = val
			return retData
		retVal = val
		retCap = None
		retCode = None
		val = qualitativeValueConv(val)
		objList = xmlObj.findall('.//qualitative-value')
		# XML内のcaptionを正規化してから比較する必要があるため、ループを回す
		for capObj in objList:
			qlCap = capObj.find('./caption').text if capObj.find('./caption') is not None else None
			qlVal = capObj.find('./value').text if capObj.find('./value') is not None else None
			qlCode = capObj.find('./code').text if capObj.find('./code') is not None else None
			if qlCap is None or qlVal is None: continue
			qlCapConv = qualitativeValueConv(qlCap)
			# captionと比較
			if qlCapConv.upper() == val.upper():
				retVal = qlVal
				retCap = qlCap
				retCode = qlCode
				break

		retData['value'] = retVal
		retData['caption'] = retCap
		retData['code'] = retCode if retCode is not None else '90001'

		return retData

	# 出力が文字
	def val2out3(val, inType, xmlObj):
		if val is None:
			retData['value'] = None
			return retData
		escapeVal = None
		retVal = val
		retCode = None
		retCap = None
		retBool = None

		def checkBool(qlBool):
			# boolを格納
			if qlBool is not None and len(qlBool) > 0:
				if int(qlBool) == 1:
					return True
				elif int(qlBool) == 0:
					return False

		# 単文
		if inType == '1':
			# 改行を削除
			regCtl1.sub('', val)
			retVal = val

		# 複文
		elif inType == '2':
			retVal = val

		# 単選択、または論理
		elif inType == '3' or inType == '6':
			val = regQl1.sub('', customNormalize(val))
			objList = xmlObj.findall('.//char-value')
			for capObj in objList:
				qlCap = capObj.find('./caption').text if capObj.find('./caption') is not None else None
				qlVal = capObj.find('./value').text if capObj.find('./value') is not None else None
				qlCode = capObj.find('./code').text if capObj.find('./code') is not None else None
				qlBool = capObj.find('./bool').text if capObj.find('./bool') is not None else None

				if qlCap is None or qlVal is None: continue
				qlVal = regQl1.sub('', customNormalize(qlVal))
				qlCapConv = i18nCode2Val(sidMorg, data=qlCap)
				# valueと比較
				if val.upper() == qlVal.upper():
					retVal = qlVal
					retCode = qlCode
					retCap = qlCapConv
					retBool = checkBool(qlBool)
					break
				# captionと比較
				elif val.upper() == qlCapConv.upper():
					retVal = qlVal
					retCode = qlCode
					retCap = qlCapConv
					retBool = checkBool(qlBool)
					break

		# 複選択
		elif inType == '4':
			if val.find('::') > 0: sepStr = '::'
			else: sepStr = ','
			retVal = val
			retCap = None
			retCode = None
			sepVal = val.split(sepStr)
			val = regQl1.sub('', customNormalize(val))
			objList = xmlObj.findall('.//char-value')
			valList = []
			for capObj in objList:
				qlCap = capObj.find('./caption').text if capObj.find('./caption') is not None else None
				qlVal = capObj.find('./value').text if capObj.find('./value') is not None else None
				qlCode = capObj.find('./code').text if capObj.find('./code') is not None else None
				if qlCap is None or qlVal is None: continue
				qlVal = regQl1.sub('', customNormalize(qlVal))
				qlCapConv = i18nCode2Val(sidMorg, data=qlCap)
				for v in sepVal:
					v2 = customNormalize(v)
					# valueと比較
					if v2.upper() == qlVal.upper():
						# 複選択なので値をList型に突っ込む
						valList.append(qlVal)
					# captionと比較
					elif v2.upper() == qlCapConv.upper():
						# 複選択なので値をList型に突っ込む
						valList.append(qlVal)
			# 出力時の区切り文字列は国際版で「::」を使用する取り決めになった
			if len(valList) > 0:
				retVal = '{}'.format('::').join(valList)
				retVal = retVal.strip('::')
			retCode = qlCode
			retCap = qlCap

		# 自動演算
		elif inType == '5':
			# TODO: 何をしていいのか不明、daidai側にこの機能があったとしてもjavascript前提で動作するものだから悩む。なので未実装
			pass
		else:
			pass

		# XMLに直接格納できない文字のエスケープ処理を最後に
		escapeVal = retVal.translate(xmlEscapeCharTable1)

		retData['value'] = escapeVal
		retData['caption'] = retCap
		retData['code'] = retCode if retCode is not None else '90001'
		retData['bool'] = retBool

		return retData


	# 出力が論理
	def val2out4(val):
		# TODO: 使用機会がなさそうなので、未実装
		retData['value'] = val
		return retData

	# 基準のXMLを取得
	xmlCriObj = xml2Obj(criterion['xml_criterion'])
	# 定性値コードのXMLが存在したら取得
	xmlQlObj = None
	if 'xml_qualitative' in criterion and criterion['xml_qualitative'] is not None and len(criterion['xml_qualitative']) > 0:
		xmlQlObj = xml2Obj(criterion['xml_qualitative'])

	# 入力　1:単文、2:複文、3:単選択、4:複選択、5:自動演算、6:論理
	inType = xmlCriObj.find('.//input-style').text
	# 出力　1:数値、2:定性、3:文字、4:論理
	outType = xmlCriObj.find('.//output-format').text

	# 出力が数値
	if outType == '1':
		decDigit = xmlCriObj.find('.//number-value/dec-digit').text		# 小数部桁数
		retVal = val2out1(value, decDigit)
	# 出力が定性
	elif outType == '2':
		retVal = val2out2(value, xmlQlObj)
	# 出力が文字
	elif outType == '3':
		retVal = val2out3(value, inType, xmlCriObj)
	elif outType == '4':
		retVal = val2out4(value)

	# TODO: 使うかもなので入れておく
	retVal['inType'] = inType
	retVal['outType'] = outType

	return retVal
