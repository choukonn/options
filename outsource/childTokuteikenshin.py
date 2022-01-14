#!/usr/bin/python3

# -*- coding: utf-8 -*-
# 文字コードはUTF-8で
# ネストが深いので４タブね。
# vim: ts=4 sts=4 sw=4

# 特定健診のCSV出力
# ベースのm_outsourceはsid_morg=0に作成
# 検査法等の医療機関個別情報は今まで通り

# 以下のツールに合わせて作成
#CC2Xシリーズ 第3期対応正式版2019.03.02

#import os
import sys
import signal
import tempfile
import xml.etree.ElementTree as ET
import csv
import datetime
import pathlib as pl
import collections
from operator import itemgetter, attrgetter
import re
import time
import zipfile
import codecs

# https://github.com/ikegami-yukino/jaconv/blob/master/README_JP.rst
import jaconv

import form_tools_py.conf as conf
import form_tools_py.common as cmn
import form_tools_py.read_i18n_translation as ri18n
import form_tools_py.getXmlSid as getXmlSid

# signalハンドラの登録(CTRL+Cとkill)
signal.signal(signal.SIGINT, cmn.handler_exit)
signal.signal(signal.SIGTERM, cmn.handler_exit)

# コンフィグ
config_data = {}

# 特定健診データ作成用
csvHeaderItemDict = {}
csvDataItemDict = {}
# 受診項目のsid一覧を格納するもの
jyushinEitemList = {}
#KEKKA1(負担金)出力用データのヘッダ名
#examineeKekka1Header = {'id':'#健診者ID', 'mkSec':'窓口負担区分（基本的な健診）', 'mkMoney':'窓口負担額（基本的な健診）', 'mkRate':'窓口負担率（基本的な健診）', 'msSec':'窓口負担区分（詳細な健診）', 'msMoney':'窓口負担額（詳細な健診）', 'msRate':'窓口負担率（詳細な健診）', 'mtSec':'窓口負担区分(追加健診）', 'mtMoney':'窓口負担額(追加健診）', 'mtRate':'窓口負担率(追加健診）', 'mnSec':'窓口負担区分(人間ドック）', 'mnMoney':'窓口負担額(人間ドック）', 'mnRate':'窓口負担率(人間ドック）', 'mnMaxMoney':'窓口負担上限額(人間ドック）', 'seiSec':'請求区分', 'itakuUnitPriceSec':'委託料単価区分', 'kihonUnitPrice':'基本的な健診単価', 'syousaiUnitPrice1':'詳細な健診単価', 'syousaiCode1':'詳細健診コード', 'syousaiUnitPrice2':'詳細な健診単価', 'syousaiCode2':'詳細健診コード', 'syousaiUnitPrice3':'詳細な健診単価', 'syousaiCode3':'詳細健診コード', 'syousaiUnitPrice4':'詳細な健診単価', 'syousaiCode4':'詳細健診コード', 'mkMoneyCalc':'窓口負担金額（基本的な健診）', 'msMoneyCalc':'窓口負担金額（詳細な健診）', 'mtMoneyCalc':'窓口負担金額（追加健診）', 'UnitPriceCalc':'単価(合計）', 'mdAllCalc':'窓口負担金額（合計）', 'taAllCalc':'他健診負担金額', 'billingAmount':'請求金額'}
examineeKekka1Header = {}
examineeKekka1Header.update({'id':'#健診者ID'})
examineeKekka1Header.update({'mkSec':'窓口負担区分（基本的な健診）'})
examineeKekka1Header.update({'mkMoney':'窓口負担額（基本的な健診）'})
examineeKekka1Header.update({'mkRate':'窓口負担率（基本的な健診）'})
examineeKekka1Header.update({'msSec':'窓口負担区分（詳細な健診）'})
examineeKekka1Header.update({'msMoney':'窓口負担額（詳細な健診）'})
examineeKekka1Header.update({'msRate':'窓口負担率（詳細な健診）'})
examineeKekka1Header.update({'mtSec':'窓口負担区分(追加健診）'})
examineeKekka1Header.update({'mtMoney':'窓口負担額(追加健診）'})
examineeKekka1Header.update({'mtRate':'窓口負担率(追加健診）'})
examineeKekka1Header.update({'mnSec':'窓口負担区分(人間ドック）'})
examineeKekka1Header.update({'mnMoney':'窓口負担額(人間ドック）'})
examineeKekka1Header.update({'mnRate':'窓口負担率(人間ドック）'})
examineeKekka1Header.update({'mnMaxMoney':'窓口負担上限額(人間ドック）'})
examineeKekka1Header.update({'seiSec':'請求区分'})
examineeKekka1Header.update({'itakuUnitPriceSec':'委託料単価区分'})
examineeKekka1Header.update({'kihonUnitPrice':'基本的な健診単価'})
examineeKekka1Header.update({'syousaiUnitPrice1':'詳細な健診単価1'})
examineeKekka1Header.update({'syousaiCode1':'詳細健診コード1'})
examineeKekka1Header.update({'syousaiUnitPrice2':'詳細な健診単価2'})
examineeKekka1Header.update({'syousaiCode2':'詳細健診コード2'})
examineeKekka1Header.update({'syousaiUnitPrice3':'詳細な健診単価3'})
examineeKekka1Header.update({'syousaiCode3':'詳細健診コード3'})
examineeKekka1Header.update({'syousaiUnitPrice4':'詳細な健診単価4'})
examineeKekka1Header.update({'syousaiCode4':'詳細健診コード4'})
examineeKekka1Header.update({'mkMoneyCalc':'窓口負担金額（基本的な健診）'})
examineeKekka1Header.update({'msMoneyCalc':'窓口負担金額（詳細な健診）'})
examineeKekka1Header.update({'mtMoneyCalc':'窓口負担金額（追加健診）'})
examineeKekka1Header.update({'UnitPriceCalc':'単価(合計）'})
examineeKekka1Header.update({'mdAllCalc':'窓口負担金額（合計）'})
examineeKekka1Header.update({'taAllCalc':'他健診負担金額'})
examineeKekka1Header.update({'billingAmount':'請求金額'})

#KEKKA1出力するデータを格納するもの
examineeKekka1Data = {}
#KEKKA2(追加健診)出力用データのヘッダ名
examineeKekka2Header = {
	'id':'健診者ID',
	'unit01Price':'追加健診単価１',  'unit01Code':'追加健診コード１',
	'unit02Price':'追加健診単価２',  'unit02Code':'追加健診コード２',
	'unit03Price':'追加健診単価３',  'unit03Code':'追加健診コード３',
	'unit04Price':'追加健診単価４',  'unit04Code':'追加健診コード４',
	'unit05Price':'追加健診単価５',  'unit05Code':'追加健診コード５',
	'unit06Price':'追加健診単価６',  'unit06Code':'追加健診コード６',
	'unit07Price':'追加健診単価７',  'unit07Code':'追加健診コード７',
	'unit08Price':'追加健診単価８',  'unit08Code':'追加健診コード８',
	'unit09Price':'追加健診単価９',  'unit09Code':'追加健診コード９',
	'unit10Price':'追加健診単価１０', 'unit10Code':'追加健診コード１０'
	}

#KEKKA2出力するデータを格納するもの
examineeKekka2Data = {}
# ファイル出力対象者データのヘッダ名
resultSuccessHeader = {'apoDay':'受診日','id':'受診者ID'}
examineeResultHeader = {**resultSuccessHeader, **{'item':'対象項目'}}
# エラー出力用データのヘッダ名
examineeErrHeader = {**examineeResultHeader, **{'content':'内容'}}
# エラー出力するデータを格納するもの
examineeErrData = []

# 既往歴　脳血管
noulist = ['30001511','30001512','30001513','30001514']
# 既往歴　心血管
sinlist = ['30001529','30001530','30001531','30001532','30001533']
# 既往歴　腎不全
jinlist = ['30001574']
# 頭部MRI
tobulist = ['901103','901104','901115','901116','901117','901118','901119','901120','901121']
#所見２～10は定義しないと拾ってこれない
# 心電図所見
shindenlist = ['550','1390403','1390404','1390514','1390537','1390538','1390539','1390540','1390541']
# ホルスター心電図
holslist = ['1390703','1390704','1390705','1390706','1390707','1390708','1390709','1390710','1390711']
# 負荷心電図
hukalist = ['1390802','1390803','1390804','1390806','1390807','1390808','1390809','1390810','1390811']
# 腹部超音波所見
hukubulist = ['1440907','1440908','1440937','1440938','1440980','1440983','1440986','1440999','14409100']
# 胸部Ｘ線所見
kyobuxplist = ['558','1410103','1410114','1410115','1410148','1410149','1410150','1410151','1410152']
# 胸部CT所見
kyobuctlist = ['1410202','1410203','1410215','1410216','1410244','1410245','1410246','1410247','1410248']
# 大腸内視鏡所見
daityoulist = ['665','6660103','6660115','6660116','6660145','6660146','6660147','6660148','6660149']
# 腹部CT所見
hykubuctlist = ['1440103','1440104','1440116','1440117','1440145','1440146','1440147','1440148','1440149']
# マンモグラフィー所見
mmglist = ['7090274','7090275','7090276','7090277','7090278','7090279','7090280','7090281']
# Carotid ultrasonograph
carotidlist = ['901603','901604','901616','901617','901639','901655','901656','901657','901658']
# 胃内視鏡
stomachlist = ['656','657','7530323','7530324','7530325','7530326','7530327','7530370','7530371']

# 文字列結合を行う結果の修正用
StringChecklist = {
	'attribType':'N',
	'dataSize':128

}
################################################################################
msg2js = cmn.Log().msg2js
log = cmn.Log().log
dbg_log = cmn.Log().dbg_log
sql = cmn.Sql()
sql2 = cmn.Sql()
sql3 = cmn.Sql()
zen2han = cmn.Zenkaku2Hankaku().zen2han

# 変数も参照したいよね
abst_code = conf.abst_code
sort_code = conf.sort_code
form_code = conf.form_code
m_section = conf.m_section

LOG_NOTICE = conf.LOG_NOTICE
LOG_INFO = conf.LOG_INFO
LOG_WARN = conf.LOG_WARN
LOG_ERR = conf.LOG_ERR
LOG_DBG = conf.LOG_DBG

# 改行置換用
convbreak = re.compile(r"[\r\n]+")
################################################################################
## 文字列チェック
# '9'		: # 半角数値・半角ピリオド(半角ピリオドを除く半角英字記号、全角文字が設定された場合、エラー。)
# '9a'		:
# 'X'		: # 半角英数記号・半角カナ(全角文字が設定された場合、エラー)
# 'Xa'		: # 半角数字のみ
# 'Xb'		: # 半角英数記号のみ
# 'N'		: # 全角文字のみ
# 'N/X'		: # 半角英数記号・半角カナ・全角文字・スペースは削除
# 'kana'	: # 半角カタカナのみ
# 'KANA'	: # 全角カタカナのみ
def chkStrType(strWord, chkType):
	if (strWord is None or len(strWord) < 1) or (chkType is None or len(chkType) < 1): return False
	chkStrFlag = False
	pos = None
	#chkWord = strWord.encode('UTF-8')
	chkWord = strWord

	attribType9 = re.compile(r'[0-9.ｧ-ﾝﾞﾟ]+')
	attribType9a = re.compile(r'[0-9]+')
	attribTypeX = re.compile(r'[!\"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~0-9a-zA-Zｧ-ﾝﾞﾟ]+')
	attribTypeXa = re.compile(r'[!\"#$%&\'()*+,-－./:;<=>?@\[\\\]^_`{|}~0-9a-zA-Z]+')

	chkHanKana = re.compile(r'[ｧ-ﾝﾞﾟｰ\u3000\x20]+')
	chkZenKana = re.compile(r'[ァ-ンー\u3000\x20]+')
	chkHira = re.compile(r'[ぁ-んー\u3000\x20]+')

	if chkType == '9':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = attribType9.sub('', chkWord)
		if pos is not None and pos != '':
			chkWord = chkWord.replace(pos, '')
			# 変換後に再チェック
			pos = len(attribType9a.sub('', chkWord))
			if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == '9a':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = len(attribType9a.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'X':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = len(attribTypeX.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'Xa':
		# 指定の文字を削除して余計な文字が残っているかチェック
		pos = len(attribTypeXa.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'N':
		# 半角英数記号半角カナに一致する文字が存在するかチェック
		pos = attribTypeX.search(chkWord)
		# 不一致はNoneが返る
		if pos is None: chkStrFlag = True
	elif chkType == 'Na':
		# 半角カナを削除して余計な文字がいるかチェック
		pos = len(chkHanKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'Nb':
		# 全角カナを削除して余計な文字がいるかチェック
		pos = len(chkZenKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'N/X':
		# 何もしない。。。
		chkStrFlag = True
	elif chkType == 'hira':
		# ひらがなチェック
		pos = len(chkHira.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'kana':
		# 半角カタカナチェック
		pos = len(chkHanKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	elif chkType == 'KANA':
		# 全角カタカナチェック
		pos = len(chkZenKana.sub('', chkWord))
		if pos is not None and pos < 1: chkStrFlag = True
	else:
		log('unkwon string check type:{}'.format(chkType))

	return chkStrFlag,chkWord

## 文字列が指定された長さを超えた場合にまるめる
def mojiCheckConvAndCut(val, keyData):
	try:
		# m_outsource（csvData_item）にdataSizeが設定されていない、または数値に変換できない場合はエラー
		keyData['dataSize'] = int(keyData['dataSize'])
		moji = str(val)
	except Exception as err:
		log('[keyData check] dataSize is error: [msg:{}], [data:{}]'.format(err, keyData['dataSize']), LOG_ERR)
		return moji
	chf = True
	if moji is not None and len(moji) > 0:
		# 日本語変換をかける
		# jaconvモジュールでは変換対象外の文字は何もせず返すので、ひらがなとカタカナどちらで入力されていて問題ないように変換しておく
		if keyData['attribType'] == 'N':
			moji = jaconv.normalize(moji, 'NFKC')								# Unicode正規化
			moji = re.sub(r"[-－―－]","ー",moji)									# 伸ばし棒で環境依存文字が含まれている場合は一律で「－」に変換
			moji = re.sub(r"[]","□",moji)
			moji = jaconv.h2z(moji, kana=True, ascii=True, digit=True)			# 半角=>全角へ一律変換
			moji = convbreak.sub(r"　", moji.strip())
			moji = moji.strip()
		elif keyData['attribType'] == 'Na':		# 半角カタカナにする
			moji = jaconv.normalize(moji, 'NFKC')								# Unicode正規化
			moji = jaconv.hira2hkata(moji)										# ひらがな=>（半）カタカナ
			moji = jaconv.z2h(moji, kana=True, ascii=True, digit=True)			# （全）カタカナ=>（半）カタカナ
			moji = convbreak.sub(r"　", moji.strip())
			moji = moji.strip()
		elif keyData['attribType'] == 'Nb':		# 全角カタカナにする
			moji = jaconv.normalize(moji, 'NFKC')								# Unicode正規化
			moji = moji.replace(' ', '')										#スペースがあれば削除
			moji = jaconv.hira2kata(moji)										# ひらがな=>（全）カタカナ
			moji = jaconv.h2z(moji, kana=True, ascii=True, digit=True)			# （半）カタカナ=>（全）カタカナ
			moji = convbreak.sub(r"　", moji.strip())
			moji = moji.strip()

		#住所用に使用するN/Xでもスペースは削除する
		if keyData['attribType'] == 'N/X':
			moji = moji.replace(' ', '')										#スペースがあれば削除
			moji = jaconv.normalize(moji, 'NFKC')								# Unicode正規化
			moji = convbreak.sub(r"　", moji.strip())
			moji = moji.strip()
		if moji is not None and moji != '':
			# 文字列チェック
			chf,moji = chkStrType(moji, keyData['attribType'])
		if chf == False:
			log('[string check] type:{}, physicalName:{}, data:\"{}\"'.format(keyData['attribType'], keyData['item_id'], moji), LOG_WARN)
		#数字のみの場合の'-'が消えてないのでここで削除
		if keyData['attribType'] == '9a':
			moji = moji.replace('-', '')
		if keyData['attribType'] == 'Xa':
			moji = re.sub(r"[-－―]","-",moji)									# 伸ばし棒で環境依存文字が含まれている場合は一律で「－」に変換
			moji = convbreak.sub(r"　", moji.strip())
			moji = moji.strip()
		# 文字列長チェック
		if len(moji) > keyData['dataSize']:
			# 文字列の長さ調整
			if 'f_deleteString_sizeOver' in conf.convert_option and conf.convert_option['f_deleteString_sizeOver'] == '1':
				#（数字のみは除外とする）
				if keyData['attribType'] not in ['9', '9a']:
					moji = moji[:keyData['dataSize']]
			else:
				# 超えてるけど、調整フラグOFFの場合はログ出力だけで何もしない
				log('[string length check] [{}:\"{}\", len:{}][max:{}]'.format(keyData['caption'], moji, len(moji), keyData['dataSize']), LOG_WARN)
	else:
		# 値がNone
		#log('[string check] text:{}, val:{}'.format(keyData['#text'], moji), LOG_WARN)
		pass

	return moji

#エラー表示用の名前変換(一括変換をかける前に個別で対応)
def namaehenkan(kanamoji):
	#エラーチェックは一括処理で行うためここでチェックしない。変換のみ
	kanamoji = jaconv.normalize(kanamoji, 'NFKC')								# Unicode正規化
	kanamoji = kanamoji.replace(' ', '')										#スペースがあれば削除
	kanamoji = jaconv.hira2kata(kanamoji)										# ひらがな=>（全）カタカナ
	kanamoji = jaconv.h2z(kanamoji, kana=True, ascii=True, digit=True)			# （半）カタカナ=>（全）カタカナ

	return kanamoji

# 入力項目漏れがあるときのエラーメッセージ作成
def inputDataCheck2errMsg(result):
	# 項目情報
	csvDataItem = conf.outsource_config['root']['outsource']['columns']['csvData_item']['item']
	# 受診項目の取得
	jyushinEitemList = [k for k in conf.inspStdOptData['eitem'] if conf.inspStdOptData['eitem'][k] in ['3','4']]
	# 入力チェック対象の抽出
	checkTargetList = {}
	blankMsg = []
	# TODO: 血圧2回法を採用しているといいつつ、1回しか入力されていない場合があるため、個別処理が必要
	# 血圧データチェック用（その他 > 2回目 > 1回目）
	ketuatsu3H = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '1380105'}		# 血圧最高その他
	ketuatsu3L = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '1380106'}		# 血圧最低その他
	ketuatsu2H = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '269'}			# 血圧最高2回目
	ketuatsu2L = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '270'}			# 血圧最低2回目
	ketuatsu1H = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '267'}			# 血圧最高1回目
	ketuatsu1L = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '268'}			# 血圧最低1回目
	ketuatsuHflag = None
	ketuatsuLflag = None
	ketuatsuHall = {}
	ketuatsuHall.update(ketuatsu3H)
	ketuatsuHall.update(ketuatsu2H)
	ketuatsuHall.update(ketuatsu1H)
	ketuatsuLall = {}
	ketuatsuLall.update(ketuatsu3L)
	ketuatsuLall.update(ketuatsu2L)
	ketuatsuLall.update(ketuatsu1L)
	# 血糖の検査
	kettou1 = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '464'}			# 空腹時血糖
	kettou2 = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '1057'}			# HbA1c
	kettou3 = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '1351101'}		# 随時血糖
	kettouFlag = None
	kettouAll = {}
	kettouAll.update(kettou1)
	kettouAll.update(kettou2)
	kettouAll.update(kettou3)
	# 眼底グループの検査
	ganteikw = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '233' and 'GNTEI-KW' in result} 			# 眼底検査KW
	ganteisch = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '241' and 'GNTEI-SCH' in result}			# 眼底検査Scheie H
	ganteiscs = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '244' and 'GNTEI-SCS' in result}			# 眼底検査Scheie S
	ganteisct = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '255' and 'GNTEI-SCT' in result}			# 眼底検査SCOTT
	ganteiwm = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '2390801' 'GNTEI-WM' in result}		# 眼底検査Wong-Mitchell
	ganteida = {k['@sid']: k['@physicalName'] for k in csvDataItem if k['@sid'] == '2390901' 'GNTEI-DAS' in result}		# 眼底検査Davis
	ganteiFlag = None
	ganteiALL = {}
	ganteiALL.update(ganteikw)
	ganteiALL.update(ganteisch)
	ganteiALL.update(ganteiscs)
	ganteiALL.update(ganteisct)
	ganteiALL.update(ganteiwm)
	ganteiALL.update(ganteida)

	errMsgBase = {examineeErrHeader['apoDay']:conf.examInfo['appoint_day'], examineeErrHeader['kana']:result['JSS-NM-KN'], examineeErrHeader['id']:conf.examInfo['id'], examineeErrHeader['course']:conf.examInfo['courseName']}

	for key in csvDataItemDict['item']:
		if '@sid' not in key or key['@sid'] is None: continue
		jyushinElement2eItemSid = [k for k,v in conf.inspStdOptData['elementSid'].items() if key['@sid'] in v]
		if '@required' not in key or key['@required'] is None or len(key['@required']) < 1: continue
		# 1:受診者属性情報系
		if key['@required'] == '1':
			checkTargetList[key['@physicalName']] = key['#text']
		# 2:検査項目系
		elif key['@required'] == '2':
			# 受診している項目のみ対象とする
			if len(list(set(jyushinElement2eItemSid) & set(jyushinEitemList))) > 0:
				# 複数存在する項目のうち、いずれか一つあればいい場合のチェックを行う
				# 血糖チェック
				if kettouFlag is None and key['@physicalName'] in (list(kettou1.values()) + list(kettou2.values()) + list(kettou3.values())):
					# 空腹時血糖
					if key['@physicalName'] in list(kettou1.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: kettouFlag = list(kettou1.keys())[0]
					# HbA1c
					elif key['@physicalName'] in list(kettou2.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: kettouFlag = list(kettou2.keys())[0]
					# 随時血糖
					elif key['@physicalName'] in list(kettou3.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: kettouFlag = list(kettou3.keys())[0]

				# 血圧その他
				elif key['@physicalName'] in list(ketuatsu3H.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ketuatsuHflag = list(ketuatsu3H.keys())[0]
				elif key['@physicalName'] in list(ketuatsu3L.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ketuatsuLflag = list(ketuatsu3L.keys())[0]
				# 血圧2回目
				elif key['@physicalName'] in list(ketuatsu2H.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ketuatsuHflag = list(ketuatsu2H.keys())[0]
				elif key['@physicalName'] in list(ketuatsu2L.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ketuatsuLflag = list(ketuatsu2L.keys())[0]
				# 血圧1回目
				elif key['@physicalName'] in list(ketuatsu1H.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ketuatsuHflag = list(ketuatsu1H.keys())[0]
				elif key['@physicalName'] in list(ketuatsu1L.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ketuatsuLflag = list(ketuatsu1L.keys())[0]

				#眼底グループチェック
				elif key['@physicalName'] in list(ganteikw.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ganteiFlag = list(ganteikw.keys())[0]
				elif key['@physicalName'] in list(ganteisch.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ganteiFlag = list(ganteisch.keys())[0]
				elif key['@physicalName'] in list(ganteiscs.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ganteiFlag = list(ganteiscs.keys())[0]
				elif key['@physicalName'] in list(ganteisct.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ganteiFlag = list(ganteisct.keys())[0]
				elif key['@physicalName'] in list(ganteiwm.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ganteiFlag = list(ganteiwm.keys())[0]
				elif key['@physicalName'] in list(ganteida.values()) and result[key['@physicalName']] is not None and len(result[key['@physicalName']]) > 0: ganteiFlag = list(ganteida.keys())[0]


				# 特定の者以外は基本ここ
				else:
					checkTargetList[key['@physicalName']] = key['#text']

	# データ最終チェック
	# 血圧（最高）データ最終チェック
	delKetsuatuH = [k for k in (list(ketuatsu3H.keys()) + list(ketuatsu2H.keys()) + list(ketuatsu1H.keys())) if ketuatsuHflag != k]
	for k in delKetsuatuH:
		if ketuatsuHall[k] in checkTargetList:
			del checkTargetList[ketuatsuHall[k]]
	if len(delKetsuatuH) == len(ketuatsuHall):
		msgObj = {**errMsgBase, **{examineeErrHeader['item']: '収縮期血圧（最高）', examineeErrHeader['content']:'未入力'}}
		blankMsg.append(msgObj)

	# 血圧（最低）チェック
	delKetsuatuL = [k for k in (list(ketuatsu3L.keys()) + list(ketuatsu2L.keys()) + list(ketuatsu1L.keys())) if ketuatsuLflag != k]
	for k in delKetsuatuL:
		if ketuatsuLall[k] in checkTargetList:
			del checkTargetList[ketuatsuLall[k]]
	if len(delKetsuatuH) == len(ketuatsuHall):
		msgObj = {**errMsgBase, **{examineeErrHeader['item']: '拡張期血圧（最低）', examineeErrHeader['content']:'未入力'}}
		blankMsg.append(msgObj)

	# 腹囲(実測)チェック
	if 'SNSTT-FKI-JSK' in result and (result['SNSTT-FKI-JSK'] is None or len(result['SNSTT-FKI-JSK']) < 1):
		# 内臓脂肪面積を実施している場合、腹囲は省略可能なためエラーメッセージに含まれる場合は除外する
		naizoushibouSid = [k['@sid'] for k in csvDataItemDict['item'] if k['@physicalName'] == 'SNSTT-NZSB-MNSK']
		if len(naizoushibouSid) > 0 and len(list(set(naizoushibouSid) & set(jyushinEitemList))) == 1 and 'SNSTT-NZSB-MNSK' in result and result['SNSTT-NZSB-MNSK'] is not None and len(result['SNSTT-NZSB-MNSK']) > 0:
			del checkTargetList['SNSTT-FKI-JSK']

	# 血糖チェック
	delKettou = [k for k in (list(kettou1.keys()) + list(kettou2.keys()) + list(kettou3.keys())) if kettouFlag != k]
	for k in delKettou:
		if kettouAll[k] in checkTargetList:
			del checkTargetList[kettouAll[k]]
	if len(delKettou) == len(kettouAll):
		msgObj = {**errMsgBase, **{examineeErrHeader['item']: '血糖', examineeErrHeader['content']:'未入力'}}
		blankMsg.append(msgObj)

	# 眼底チェック
	if '232' in jyushinEitemList:
		delgantei = [k for k in (list(ganteikw.keys()) + list(ganteisch.keys()) + list(ganteiscs.keys()) + list(ganteisct.keys()) + list(ganteiwm.keys()) + list(ganteida.keys())) if ganteiFlag != k]
		for k in delgantei:
			if ganteiALL[k] in checkTargetList:
				del checkTargetList[ganteiALL[k]]
		if len(delgantei) == len(ganteiALL):
			msgObj = {**errMsgBase, **{examineeErrHeader['item']: '眼底', examineeErrHeader['content']:'未入力'}}
			blankMsg.append(msgObj)

	# エラーメッセージ作成
	# examineeErrHeader = {'apoDay':'受診日', 'kana':'氏名かな', 'id':'受診者ID', 'item':'対象項目', 'content':'内容'}
	for key,val in checkTargetList.items():
		msgObj = None
		# 未入力系のメッセージ
		if key in result:
			if result[key] is None or len(result[key]) < 1:
				msgObj = {**errMsgBase, **{examineeErrHeader['item']: val, examineeErrHeader['content']:'未入力'}}
				blankMsg.append(msgObj)

	return blankMsg


## 特定健診用のフォーマットチェック及び変換
def getTKcsvDataItemVale(result,keyData):
	if result is None: return None
	# まずは結果データを取得。
	# TODO: 個別処理が必要な場合、適宜加工を行うこと
	try:
		sidValue = result['value']

		# 定性値コード変換
		ignoreTeisei2Num = ['B03602', 'B02901','B02903','B03004','S00101','S00102','I00908']
		if sidValue is not None and re.search(r'[+\-]+', sidValue):
			if keyData['item_id'] in ignoreTeisei2Num:
				if sidValue == '-' or sidValue == '(-)': sidValue = '2'
				elif sidValue == '+' or sidValue == '(+)': sidValue = '1'
				elif sidValue == '+-' or sidValue == '(+-)': sidValue = '1'
				elif sidValue == '2+' or sidValue == '(2+)': sidValue = '1'
				elif sidValue == '3+' or sidValue == '(3+)': sidValue = '1'
				elif sidValue == '4+' or sidValue == '(4+)': sidValue = '1'
				else: sidValue = '2'
			#尿糖は4+が来た場合'5'にまるめる
			elif keyData['item_id'] in 'U00201':
			# 数字チェック
				if sidValue == '-' or sidValue == '(-)': sidValue = '1'
				elif sidValue == '+-' or sidValue == '(+-)': sidValue = '2'
				elif sidValue == '1+' or sidValue == '(1+)' or sidValue == '(+)': sidValue = '3'
				elif sidValue == '2+' or sidValue == '(2+)': sidValue = '4'
				elif sidValue == '3+' or sidValue == '(3+)': sidValue = '5'
				elif sidValue == '4+' or sidValue == '(4+)': sidValue = '5'
				else: sidValue = None
			else:
			# 数字チェック
				if sidValue == '-' or sidValue == '(-)': sidValue = '1'
				elif sidValue == '+-' or sidValue == '(+-)': sidValue = '2'
				elif sidValue == '1+' or sidValue == '(1+)' or sidValue == '(+)': sidValue = '3'
				elif sidValue == '2+' or sidValue == '(2+)': sidValue = '4'
				elif sidValue == '3+' or sidValue == '(3+)': sidValue = '5'
				elif sidValue == '4+' or sidValue == '(4+)': sidValue = '6'


		if sidValue is not None and keyData['attribType'] != 'N':
			if sidValue in ['91070']:		# 「91070:検出せず」はvalを"測定不能"にする
				sidValue = '測定不能'
			elif sidValue in ['91080']:		# 「91080:結果なし」はvalを"未実施"にする
				sidValue = '未実施'
			elif sidValue in ['91090']:		# 「91090:未検査」はvalを"未実施"にする(追加)
				sidValue = '未実施'
			elif sidValue in ['normal']:		#	成田では定性のところに文字がくる場合があるので、空白に変換(一時対応)
				sidValue = '測定不能'
			elif sidValue in ['abnormal']:	#	成田では定性のところに文字がくる場合があるので、空白に変換(一時対応)
				sidValue = '測定不能'
			elif sidValue in ['キャンセル']:	#	成田では定性のところに文字がくる場合があるので、未実施に変換(一時対応)
				sidValue = '未実施'
			elif sidValue in ['検査中']:		#	成田では定性のところに文字がくる場合があるので、未実施に変換(一時対応)
				sidValue = '未実施'
			elif sidValue in ['未到着']:		#	成田では定性のところに文字がくる場合があるので、未実施に変換(一時対応)
				sidValue = '未実施'
			elif sidValue in ['実施せず']:		#	成田では定性のところに文字がくる場合があるので、未実施に変換(一時対応)
				sidValue = '未実施'

		if keyData['item_id'] in ['P00202'] and sidValue is not None and len(sidValue) > 0:
			# daidai出力						# CSV出力
			if sidValue == 'NILM'					: sidValue = '1'
			elif sidValue == 'ASC-US'				: sidValue = '2'
			elif sidValue == 'ASC-H'				: sidValue = '3'
			elif sidValue == 'LSIL'					: sidValue = '4'
			elif sidValue == 'HSIL'					: sidValue = '5'
			elif sidValue == 'SCC'					: sidValue = '6'
			elif sidValue == 'AGC'					: sidValue = '7'
			elif sidValue == 'AIS'					: sidValue = '8'
			elif sidValue == 'Adenocarcinoma'		: sidValue = '9'
			elif sidValue == 'Other malig.'				: sidValue = '10'

		# TODO: 定性値(入力)を数値(出力)に変換した後じゃないと、文字列長が不一致になる可能性がある
		# 文字列チェック変換と長さ調整
		if sidValue is not None:
			sidValue = mojiCheckConvAndCut(sidValue, keyData)

		# メタボ判定の値を変換(国内)
		if keyData['item_id'] == 'D00501' and sidValue is not None and len(sidValue) > 0:
			# daidai出力						# CSV出力
			if sidValue == '3' or sidValue == '003'					: sidValue = '1'		# 基準該当
			elif sidValue == '2' or sidValue == '002'				: sidValue = '2'		# 予備群該当
			elif sidValue == '1' or sidValue == '001'				: sidValue = '3'		# 非該当
			elif sidValue == '4' or sidValue == '004'				: sidValue = '4'		# 判定不能
			else: # TODO: 一致なしはデータを空にする
				sidValue = None
	#	# メタボ判定の値を変換(成田専用)
	#	elif config_data['sid_morg'] == '90007' and keyData['item_id'] == 'D00501' and sidValue is not None and len(sidValue) > 0:
	#		# daidai出力						# CSV出力
	#		if sidValue == 'M'					: sidValue = '1'		# 基準該当
	#		elif sidValue == 'C12'				: sidValue = '2'		# 予備群該当
	#		else								: sidValue = '3'		# 非該当

		# 保健指導レベルの値を変換
		if keyData['item_id'] in ['D00502'] and sidValue is not None and len(sidValue) > 0:
			# daidai出力						# CSV出力
			if sidValue == '4'					: sidValue = '1'		# 積極的支援
			elif sidValue == '3'				: sidValue = '2'		# 動機づけ支援
			elif sidValue == '1'				: sidValue = '3'		# なし
			elif sidValue == '2'				: sidValue = '3'		# なし
			elif sidValue == '5'				: sidValue = '4'		# 判定不能
			else: # TODO: 一致なしはデータを空にする
				sidValue = None
		# non-HDLコレステロールは20～1000の間
		if keyData['item_id'] in ['B00501']:
			if sidValue is not None and str.isdecimal(sidValue):
				if 20 >= float(sidValue) or float(sidValue) >= 1000:
					log('[value dataSize error] [sid:{}][item_id:{}]'.format(keyData['sid_exam'], keyData['item_id']), LOG_ERR)
			else:
				sidValue = None
		# 血液型ABO変換
		if keyData['item_id'] in ['B01801'] and sidValue is not None and len(sidValue) > 0:
			# daidai出力						# CSV出力
			if sidValue == 'A'					: sidValue = '1'
			elif sidValue == 'B'				: sidValue = '2'
			elif sidValue == 'AB'				: sidValue = '3'
			elif sidValue == 'O'				: sidValue = '4'
		# 血液型Rh変換
		if keyData['item_id'] in ['B01803'] and sidValue is not None and len(sidValue) > 0:
			# daidai出力						# CSV出力
			if sidValue == '+'					: sidValue = '1'
			elif sidValue == '-'				: sidValue = '2'
		# 成田専用
		if config_data['sid_morg'] == '90007':
			# 成田専用　赤血球の単位が違うため、100倍する
			if keyData['item_id'] in ['B02501'] and sidValue is not None:
				sidValue = str(int(float(sidValue) * 100))
			# 成田専用　白血球の単位が違うため、100倍する
			if keyData['item_id'] in ['B02601'] and sidValue is not None:
				sidValue = str(int(float(sidValue) * 1000))
			# 成田専用　肺機能検査(努力肺活量)の単位が違うため、1/1000倍する
			if keyData['item_id'] in ['M01005'] and sidValue is not None:
				sidValue = str(float(sidValue) / 1000)
			# 成田専用　負荷前血糖値
			if keyData['item_id'] in ['B01601'] and sidValue is not None:
				sidValue = str(int(sidValue))
			if keyData['item_id'] in ['M00701'] or keyData['item_id'] in ['M00703'] or keyData['item_id'] in ['M00702'] or keyData['item_id'] in ['M00704']:
				if sidValue is not None and sidValue == '異':
					sidValue = '1'
				else:
					sidValue = '2'

			# 眼底の値を変換する
			elif keyData['item_id'] in ['M00914', 'M00915'] and sidValue is not None:
				try:
					if str.isdecimal(sidValue):
						sidValue = str(int(sidValue) + 1)
				except Exception:
					sidValue = None


		if keyData['item_id'] in ['M00913', 'M00914', 'M00915', 'M00916', 'M00917', 'M00918']:
			sidValue = re.sub(r'[0]+', '', sidValue)


	except Exception as err:
		cmn.traceback_log(err)

	return sidValue


## 特定健診用のフォーマットチェック及び変換
def DataItemVale(result,keyData,conv_data):
	# TODO: 個別処理
	# データ作成後、改めて各項目毎に必要な判定があれば。。。

	# 「xxx-xxxx-UM」から「-UM」を除外するのに使用する
	# 例：心電図の所見有無「SDZ-SHO-UM」⇒「SDZ-SHO」を抽出
	umuString = re.compile(r'有無')

	# 特定コメント（所見）は所見なしと扱う
	shokenNashiMoji = re.compile(r'^(異常(なし|無し|みとめず|認めず|を認めません|は指摘できず)|特記(なし|事項なし|所見なし|すべきことなし)|特になし|所見なし|なし|ない|正常(範囲|範囲内))$')
	# 特定健診所見の有無
	shokenUmuList = ['心電図所見有無', '既往歴有無', '自覚症状有無', '他覚症状有無','ホルター型心電図検査(所見)有無','トレッドミル負荷心機能検査(所見)有無','腹部超音波(所見)有無','胸部エックス線(所見)有無','大腸内視鏡所見有無','腹部CT所見有無','乳房画像診断(マンモグラフィー)(所見)有無','頸動脈超音波所見有無','胸部CT検査(所見)有無','頭部MRI所見有無','上部消化管内視鏡検査（所見）有無']

	try:
		data = {}
		umu_nashi	= '2'		# 特記すべきこと"なし"
		umu_ari		= '1'		# 特記すべきこと"あり"

		if result is not None:
			data.update(result)
		# 成田専用
		if config_data['sid_morg'] == '90007':
			if 'kioudata' in conv_data and '既往歴' in keyData:
				data['既往歴'] = conv_data['kioudata']
			if 'jikakudata' in conv_data:
				data['自覚症状'] = conv_data['jikakudata']
			# 食習慣　値がなければ結果に2を格納
			if '食習慣(朝食抜き)' in keyData and '食習慣(朝食抜き)' not in data:
				data['食習慣(朝食抜き)'] = '2'
			# 保健指導の希望　値がなければ結果に2を格納
			if '保険指導の利用' in keyData and '保険指導の利用' not in data:
				data['保険指導の利用'] = '2'
			# 成田専用　貧血　値があれば１を入れるなければ2を入れる
			if '貧血の有無' in keyData:
				if '貧血の有無' in data and data['貧血の有無'] == '4':
					data['貧血の有無'] = '1'
				else:
					data['貧血の有無'] = '2'
			# 就寝前　食事　値が無ければ2を入れる
			if '食べ方(就寝前)' in keyData and '食べ方(就寝前)' not in data:
				data['食べ方(就寝前)'] = '2'
			# 既往歴(脳血管)　値が無ければ2を入れる
			if 'noudata' in conv_data:
				data['既往歴(脳血管)の有無'] = '1'
			else:
				data['既往歴(脳血管)の有無'] = '2'
			# 既往歴(心血管)　値が無ければ2を入れる
			if 'sindata' in conv_data:
				data['既往歴(心血管)の有無'] = '1'
			else:
				data['既往歴(心血管)の有無'] = '2'
			# 既往歴(腎不全)　値が無ければ2を入れる
			if 'jindata' in conv_data:
				data['既往歴(腎不全・人工透析)の有無'] = '1'
			else:
				data['既往歴(腎不全・人工透析)の有無'] = '2'

		# 服薬1　値がなければ結果に2を格納
		if '服薬１（血圧）の有無' in keyData and '服薬１（血圧）の有無' not in data:
			data['服薬１（血圧）の有無'] = '2'
		# 服薬2　値がなければ結果に2を格納
		if '服薬２（血糖）の有無' in keyData and '服薬２（血糖）の有無' not in data:
			data['服薬２（血糖）の有無'] = '2'
		# 服薬3　値がなければ結果に2を格納
		if '服薬３(脂質)の有無' in keyData and '服薬３(脂質)の有無' not in data:
			data['服薬３(脂質)の有無'] = '2'
		# 喫煙　値がなければ結果に2を格納
		if '喫煙歴の有無' in keyData:
			if '喫煙歴の有無' not in data or data['喫煙歴の有無'] == '3':
				data['喫煙歴の有無'] = '2'
		# 腹囲　値がなければ結果に未実施を格納
		if '腹囲' in keyData and '腹囲' not in data:
				data['腹囲'] = '未実施'

		for keyName in shokenUmuList:
			if keyName in keyData:
				inspKeyName = umuString.sub('', keyName)	# shokenUmuListに登録された名前から「-UM」を除いた名前を抽出
				# 既往歴／自覚症状／他覚症状の文字列チェック
				if keyName in ['既往歴有無', '自覚症状有無', '他覚症状有無'] and inspKeyName in keyData:
					data[keyName] = umu_nashi
					if inspKeyName in data and data[inspKeyName] is not None and len(data[inspKeyName]) > 0:		# 入力データあり
						data[keyName] = umu_ari
						if shokenNashiMoji.search(data[inspKeyName]) is not None:			# 入力データが「異常がない」旨の文字列に一致する
							data[keyName] = umu_nashi
							if keyName == '自覚症状有無' or keyName == '他覚症状有無':		#自覚症状と他覚症状の異常がない場合は文字を削除
								data[inspKeyName] = None
					if data[keyName] == umu_nashi:
						data[inspKeyName] = None
				# 心電図
				elif inspKeyName in data:
					# 医師判定が「異常なし」は所見なしと扱う
					if data[keyName] in ['1','90001']:
						data[keyName] = umu_nashi
					else:
						# 医師判定が「異常なし」"以外"が選択されている場合は、所見有無ありと扱う
						data[keyName] = umu_ari
						# 所見入力なしは「所見有無なし」とする
						if data[inspKeyName] is None or len(data[inspKeyName]) < 1:
							data[keyName] = umu_nashi
						# 所見にデータ入力されている場合は「異常がない」旨の所見文字列が入力されているかチェックを行い該当したら「所見有無なし」とする
						elif data[inspKeyName] is not None and len(data[inspKeyName]) > 0 and shokenNashiMoji.search(data[inspKeyName]) is not None:
							data[keyName] = umu_nashi
					if data[keyName] == umu_nashi:
						data[inspKeyName] = None

				del inspKeyName			# 念のためクリア

		# 採血時間が採血時間が空又は食後10時間以上の場合は空腹時血糖、3時間以上は随時血糖に格納する。3時間未満はNone
		if 'SIKT-TIME' in data and data['SIKT-TIME'] is not None:
			if data['SIKT-TIME'] == '2':
				data['KTZIJKT-SGISN'] = None
			elif data['SIKT-TIME'] == '3':
				data['KTKFJKT-SGKHKDH'] = None
			elif data['SIKT-TIME'] == '4':
				data['KTKFJKT-SGKHKDH'] = None
				data['KTZIJKT-SGISN'] = None

	except Exception as err:
		cmn.traceback_log(err)


	return data

# 言語マスタ取得
def geti18ndictionary(sid_locale):
	try:
		query = 'SELECT * FROM m_i18n_dictionary where sid_morg = 0 and sid_locale = ' + sid_locale + ';'
		rows = cmn.get_sql_query(query)

	except Exception as err:
		log('error', '{}'.format(err))
		raise

	return rows

# 言語コードが含まれているかチェック
def checkComment(target):
	result = False
	checkStr = str(target)

	try:
		pattern = '.*##.+##.*'  # 例. ##D22000##, ##AC10010## など

		repatter = re.compile(pattern)
		if repatter.search(checkStr) is not None:
			result = True

	except Exception as err:
		log('error', '{}'.format(err))
		raise

	return result

# 言語コードを指定言語に変換
def convComment(target):
	result = ""
	conv = ""

	try:
		# 改行で分割
		arr = target.splitlines()

		for i in range(len(arr)):
			conv = arr[i]
			if checkComment(conv):
				conv = arr[i].replace('##', '')
				for k in range(len(langList)):
					if langList[k]['code'] == conv:
						conv = langList[k]['text']
						break
			if result == "":
				result = conv
			else:
				result = result + '　' + conv


	except Exception as err:
		log('error', '{}'.format(err))
		raise

	return result

## 特定健診用のフォーマットチェック及び変換
def getQADataItemVale(result,keyData):
	if result is None: return None
	# まずは結果データを取得。
	# TODO: 個別処理が必要な場合、適宜加工を行うこと
	try:
		sidValue = result['value']
		sidValue = jaconv.z2h(sidValue,digit=True,ascii=True)
		if '::' in sidValue or '：：' in sidValue:

			conv_val = None
			sep_list = sidValue.split('::')
			for k in range(len(sep_list)):
				if conv_val is None or conv_val < sep_list[k]:
					conv_val = sep_list[k]
			sidValue =conv_val

		# 数字チェック　問診は場所によって値がまちまち
		if '92001' == sidValue or '001' == sidValue or 'はい' == sidValue: sidValue = '1'
		elif '92002' == sidValue or '002' == sidValue or 'いいえ' == sidValue: sidValue = '2'
		elif '92003' == sidValue or '003' == sidValue: sidValue = '3'
		elif '92004' == sidValue or '004' == sidValue: sidValue = '4'
		elif '92005' == sidValue or '005' == sidValue: sidValue = '5'
		elif '92006' == sidValue or '006' == sidValue: sidValue = '6'

		# TODO: 定性値(入力)を数値(出力)に変換した後じゃないと、文字列長が不一致になる可能性がある
		# 文字列チェック変換と長さ調整
		if sidValue is not None:
			sidValue = mojiCheckConvAndCut(sidValue, keyData)

	except Exception as err:
		cmn.traceback_log(err)

	return sidValue


## 特定健診用のフォーマットチェック及び変換
def getdataItemconv(result,conv_data):
	if result is None: return None
	# まずは結果データを取得。
	# TODO: 個別処理が必要な場合、適宜加工を行うこと
	try:
		sidValue = result['value']

		# TODO: 定性値(入力)を数値(出力)に変換した後じゃないと、文字列長が不一致になる可能性がある
		# 総合判定取得
		if result['item_id'] == 'TF0101':
			conv_data['総合所見'] = sidValue

		#成田用　各既往歴が分かれているのでまとめる 一つでもあれば値に１を設定
		#既往歴30001512　に選択肢の文言をまとめる。

		if result['item_id'] in noulist:
			if sidValue == '004':
				conv_data['noudata'] = '1'
				if 'kioudata' in conv_data:
					conv_data['kioudata'] = conv_data['kioudata'] + '\n' + result['eName']
				else:
					conv_data['kioudata'] = result['eName']
			else:
				result['value'] = '2'
		elif result['item_id'] in sinlist:
			if sidValue == '004':
				conv_data['sindata'] = '1'
				if 'kioudata' in conv_data:
					conv_data['kioudata'] = conv_data['kioudata'] + '\n' + result['eName']
				else:
					conv_data['kioudata'] = result['eName']
			else:
				result['value'] = '2'
		elif result['item_id'] in jinlist:
			if sidValue == '004':
				conv_data['jindata'] = '1'
				if 'kioudata' in conv_data:
					conv_data['kioudata'] = conv_data['kioudata'] + '\n' + result['eName']
				else:
					conv_data['kioudata'] = result['eName']
			else:
				result['value'] = '2'
		elif '300013' in result['item_id']:
				if 'jikakudata' in conv_data:
					conv_data['jikakudata'] = conv_data['jikakudata'] + '\n' + result['eName']
				else:
					conv_data['jikakudata'] = result['eName']
				"""
				if len(moji) > keyData['dataSize']:
				# 文字列の長さ調整
				if 'f_deleteString_sizeOver' in conf.convert_option and conf.convert_option['f_deleteString_sizeOver'] == '1':
					#（数字のみは除外とする）
					if keyData['attribType'] not in ['9', '9a']:
						moji = moji[:keyData['dataSize']]
"""
		#　ここから所見系
		elif result['item_id'] in tobulist:	#頭部MRI
			conv_data['頭部MRI所見有無'] = '1'
			if '頭部MRI所見' in conv_data:
				conv_data['頭部MRI所見'] = conv_data['頭部MRI所見'] + '\n' + sidValue
			else:
				conv_data['頭部MRI所見'] = result['value']
		elif result['item_id'] in shindenlist:	#心電図
			conv_data['心電図所見有無'] = '1'
			if '心電図所見' in conv_data:
				conv_data['心電図所見'] = conv_data['心電図所見'] + '\n' + sidValue
			else:
				conv_data['心電図所見'] = result['value']
		elif result['item_id'] in holslist:	#ホルター心電図
			conv_data['ホルター型心電図検査(所見)有無'] = '1'
			if 'ホルター型心電図検査(所見)' in conv_data:
				conv_data['ホルター型心電図検査(所見)'] = conv_data['ホルター型心電図検査(所見)'] + '\n' + sidValue
			else:
				conv_data['ホルター型心電図検査(所見)'] = result['value']
		elif result['item_id'] in hukalist:	#負荷心電図
			conv_data['トレッドミル負荷心機能検査(所見)有無'] = '1'
			if 'トレッドミル負荷心機能検査(所見)' in conv_data:
				conv_data['トレッドミル負荷心機能検査(所見)'] = conv_data['トレッドミル負荷心機能検査(所見)'] + '\n' + sidValue
			else:
				conv_data['トレッドミル負荷心機能検査(所見)'] = result['value']
		elif result['item_id'] in hukubulist:	#腹部超音波所見
			conv_data['腹部超音波(所見)有無'] = '1'
			if '腹部超音波(所見)' in conv_data:
				conv_data['腹部超音波(所見)'] = conv_data['腹部超音波(所見)'] + '\n' + sidValue
			else:
				conv_data['腹部超音波(所見)'] = result['value']
		elif result['item_id'] in kyobuxplist:	#胸部Ｘ線所見
			conv_data['胸部エックス線(所見)有無'] = '1'
			if '胸部エックス線(所見)' in conv_data:
				conv_data['胸部エックス線(所見)'] = conv_data['胸部エックス線(所見)'] + '\n' + sidValue
			else:
				conv_data['胸部エックス線(所見)'] = result['value']
		elif result['item_id'] in kyobuctlist:	#胸部CT所見
			conv_data['kyobuctdata_um'] = '1'
			if '胸部CT検査(所見)' in conv_data:
				conv_data['胸部CT検査(所見)'] = conv_data['胸部CT検査(所見)'] + '\n' + sidValue
			else:
				conv_data['胸部CT検査(所見)'] = result['value']
		elif result['item_id'] in daityoulist:	#大腸内視鏡所見
			conv_data['大腸内視鏡所見有無'] = '1'
			if '大腸内視鏡所見' in conv_data:
				conv_data['大腸内視鏡所見'] = conv_data['大腸内視鏡所見'] + '\n' + sidValue
			else:
				conv_data['大腸内視鏡所見'] = result['value']
		elif result['item_id'] in hykubuctlist:	#腹部CT所見
			conv_data['腹部CT所見有無'] = '1'
			if '腹部CT所見' in conv_data:
				conv_data['腹部CT所見'] = conv_data['腹部CT所見'] + '\n' + sidValue
			else:
				conv_data['腹部CT所見'] = result['value']
		elif result['item_id'] in mmglist:	#マンモグラフィー所見
			conv_data['乳房画像診断(マンモグラフィー)(所見)有無'] = '1'
			if '乳房画像診断(マンモグラフィー)(所見)' in conv_data:
				conv_data['乳房画像診断(マンモグラフィー)(所見)'] = conv_data['乳房画像診断(マンモグラフィー)(所見)'] + '\n' + sidValue
			else:
				conv_data['乳房画像診断(マンモグラフィー)(所見)'] = result['value']
		elif result['item_id'] in carotidlist:	#Carotid ultrasonograph所見
			conv_data['頸動脈超音波所見有無'] = '1'
			if '頸動脈超音波所見' in conv_data:
				conv_data['頸動脈超音波所見'] = conv_data['頸動脈超音波所見'] + '\n' + sidValue
			else:
				conv_data['頸動脈超音波所見'] = result['value']
		elif result['item_id'] in stomachlist:	#胃内視鏡
			conv_data['上部消化管内視鏡検査（所見）有無'] = '1'
			if '上部消化管内視鏡検査（所見）' in conv_data:
				conv_data['上部消化管内視鏡検査（所見）'] = conv_data['上部消化管内視鏡検査（所見）'] + '\n' + sidValue
			else:
				conv_data['上部消化管内視鏡検査（所見）'] = result['value']

	except Exception as err:
		cmn.traceback_log(err)

	return conv_data,result

## 特定健診用のフォーマットチェック及び変換
def convdataItemconv(data_row,conv_data):
	if data_row is None: return None
	# まずは結果データを取得。
	# TODO: 個別処理が必要な場合、適宜加工を行うこと
	try:
		for x in conv_data:
			if checkComment(conv_data[x]):
				conv_data[x] = convComment(conv_data[x])
			conv_data[x] = convbreak.sub(r"　", conv_data[x].strip())						# 改行文字は全角スペースに置換
			conv_data[x] = jaconv.h2z(conv_data[x], kana=True, ascii=True, digit=True)	# 半角は全て全角へ変換
			if len(conv_data[x]) > StringChecklist['dataSize']:
			# 文字列の長さ調整
				if StringChecklist['attribType'] not in ['9', '9a']:
					conv_data[x] = conv_data[x][:StringChecklist['dataSize']]


		for k in data_row:
			if checkComment(data_row[k]):
				data_row[k]['value'] = convComment(data_row[k]['value'])
				data_row[k]['value'] = convbreak.sub(r"　", data_row[k]['value'].strip())						# 改行文字は全角スペースに置換
				data_row[k]['value'] = jaconv.h2z(data_row[k]['value'], kana=True, ascii=True, digit=True)	# 半角は全て全角へ変換

			if data_row[k]['item_id'] == '90111' and '頭部MRI所見' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['頭部MRI所見']
			elif data_row[k]['item_id'] == '549' and '心電図所見' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['心電図所見']
			elif data_row[k]['item_id'] == '921' and 'ホルター型心電図検査(所見)' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['ホルター型心電図検査(所見)']
			elif data_row[k]['item_id'] == '1390801' and 'トレッドミル負荷心機能検査(所見)' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['トレッドミル負荷心機能検査(所見)']
			elif data_row[k]['item_id'] == '750' and '腹部超音波(所見)' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['腹部超音波(所見)']
			elif data_row[k]['item_id'] == '557' and '胸部エックス線(所見)' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['胸部エックス線(所見)']
			elif data_row[k]['item_id'] == '941' and '胸部CT検査(所見)' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['胸部CT検査(所見)']
			elif data_row[k]['item_id'] == '664' and '大腸内視鏡所見' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['大腸内視鏡所見']
			elif data_row[k]['item_id'] == '1440101' and '腹部CT所見' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['腹部CT所見']
			elif data_row[k]['item_id'] == '672' and '乳房画像診断(マンモグラフィー)(所見)' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['乳房画像診断(マンモグラフィー)(所見)']
			elif data_row[k]['item_id'] == '90161' and '頸動脈超音波所見' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['頸動脈超音波所見']
			elif data_row[k]['item_id'] == '655' and '上部消化管内視鏡検査（所見）' in conv_data:
				data_row[k]['value'] = data_row[k]['value'] + '　' + conv_data['上部消化管内視鏡検査（所見）']

	except Exception as err:
		cmn.traceback_log(err)

	return data_row

def getaddr(row,zipNum,addrNum):
	try:
		if row[zipNum] is None or row[zipNum] == '' and row[addrNum] is not None and row[addrNum] != '':
			s_addr = row[addrNum]
			# 郵便番号かもしれない個所を狙い撃ちでチェック
			reobj = re.match(r".*[0-9]{3}-[0-9]{4}", zen2han(s_addr[:9]))
			if reobj is not None:
				# 数字かチェックするために、郵便番号に「マイナス」がいたら消す
				if reobj.string[0].strip().replace('-','').isnumeric():
					row[zipNum] = s_addr[0:8]			# 全て数値なら郵便番号っぽい
					row[addrNum] = s_addr[9:]
				else:
					row[zipNum] = s_addr[1:9]			# 郵便マークがいる可能性
					row[addrNum] = s_addr[10:]

	except Exception as err:
		cmn.traceback_log(err)

	return row

# 請求情報作成追加

#kekka1データ作成
def get_price_data1(examineeKekka1Header,csv_row):
	# 成田用に固定値を持たせる
	kekka1_hederitem = examineeKekka1Header		# 定義しておいたヘッダ
	kekka1_data = {k:None for k in kekka1_hederitem.values()}

	#基本的な健診　区分
	key = kekka1_hederitem['mkSec']
	val = '1'
	kekka1_data.update({key:val})
	#詳細な健診　区分
	key = kekka1_hederitem['msSec']
	val = '1'
	kekka1_data.update({key:val})
	#追加健診　区分
	key = kekka1_hederitem['mtSec']
	val = '1'
	kekka1_data.update({key:val})
	#人間ドック健診　区分
	key = kekka1_hederitem['mnSec']
	val = '1'
	kekka1_data.update({key:val})
	#請求区分
	key = kekka1_hederitem['seiSec']
	val = '1'
	kekka1_data.update({key:val})
	#委託料単価区分
	key = kekka1_hederitem['itakuUnitPriceSec']
	val = '1'
	kekka1_data.update({key:val})
	#基本的な健診単価
	key = kekka1_hederitem['kihonUnitPrice']
	val = '0'
	kekka1_data.update({key:val})
	#窓口負担金
	key = kekka1_hederitem['mkMoneyCalc']
	val = '0'
	kekka1_data.update({key:val})
	key = kekka1_hederitem['msMoneyCalc']
	val = '0'
	kekka1_data.update({key:val})
	key = kekka1_hederitem['mtMoneyCalc']
	val = '0'
	kekka1_data.update({key:val})
	#単価(合計）
	key = kekka1_hederitem['UnitPriceCalc']
	val = '0'
	kekka1_data.update({key:val})
	#窓口負担金額（合計）
	key = kekka1_hederitem['mdAllCalc']
	val = '0'
	kekka1_data.update({key:val})
	#他健診負担金額
	key = kekka1_hederitem['taAllCalc']
	val = '0'
	kekka1_data.update({key:val})
	#請求金額
	key = kekka1_hederitem['billingAmount']
	val = '0'
	kekka1_data.update({key:val})
	#受診者ID
	kekka1_data[kekka1_hederitem['id']] = csv_row['健診者ID']

	return kekka1_data

#kekka1データ作成
def get_price_data2(examineeKekka2Header,csv_row):
	# 成田用に固定値を持たせる
	kekka2_hederitem = examineeKekka2Header		# 定義しておいたヘッダ
	kekka2_data = {k:None for k in kekka2_hederitem.values()}
	#受診者ID
	kekka2_data[kekka2_hederitem['id']] = csv_row['健診者ID']
	return kekka2_data

def create_Tokuteikenshin(xml_outsource):
	global config_data
	global csv_file_name
	global langList

	log('!!!! python create_resultCSV 1 !!!!')

	tmp_file = None
	rows = []
	rows2 = []

	csv_header = []
	csv_row = {}
	# ファイル出力対象者を格納するもの
	examineeResultData = []
	csv_data = []
	csv_kessai1_data = []
	csv_kessai2_data = []
	total_cnt = 0						# データ件数のカウント用
	# 特定健診は日本語で出力(固定)
	sid_locale = '140001'

	# 出力ファイル名の部品
	out_file_prefix = config_data['out_file_prefix']
	out_file_suffix = config_data['out_file_suffix']



	log('!!!! python create_resultCSV 2 !!!!')

	try:

		# MySQL
		sql.open()
		sql2.open()
		sql3.open()

		log('!!!! python create_resultCSV 3 !!!!')

		if xml_outsource is not None or xml_outsource == '':
			# CSV形式
			csv_option = cmn.outsource_dict('condition')
		else:
			cmn._exit('xml_error', '[m_outsource] xml get failed')		# m_outsourceのXML取得失敗
		del xml_outsource

		log('!!!! python create_resultCSV 4 !!!!')

		# 言語マスタ取得
		langList = geti18ndictionary(sid_locale)

		# 受診者基本情報取得
		sql_query = 'call p_get_appoint_export2(?,?,?,?,?);'
		param = ('GET', config_data['sid_morg'], config_data['date_start'], config_data['date_end'], None)
		log(' \"{}\", \"{}\"'.format(sql_query, param), LOG_INFO)

		rows = sql.once2noexit(sql_query, param)
		log("rows: {}".format(len(rows)))

		# 受診者抽出条件
		cond_examinee = cmn.search_abst_sort_cond(abst_code['examinee'])			# 健診者

		# 検査項目・判定・所見情報
		sql_query = 'call p_get_appoint_export2(?,?,?,?,?);'
		param = ('GET2', config_data['sid_morg'], config_data['date_start'], config_data['date_end'], None)
		log(' \"{}\", \"{}\"'.format(sql_query, param), LOG_INFO)

		rows2 = sql2.once2noexit(sql_query, param)
		log("rows2: {}".format(len(rows2)))
		log('!!!! python create_resultCSV 5 !!!!')

		# 列設定取得
		# columns = conf.outsource_config['root']['outsource']['columns']['column']
		# log('!!!! python create_resultCSV 5.1 !!!!')
		# log(columns)

		# 列設定取得(m_exportから直接)
		sql_query = 'CALL p_export2(?,?,?);'
		param = ('GET', config_data['sid_morg'], config_data['outsouceSid'])
		log(' \"{}\", \"{}\"'.format(sql_query, param), LOG_INFO)

		columns = sql3.once2noexit(sql_query, param)

		# ヘッダー情報設定
		for col in columns:
			csv_header.append(col['caption'])

		# 0件データチェック
		if rows is None or len(rows) < 1: cmn._exit('info', 'no data')
		# 件数取得
		total_cnt = len(rows)
		log('sql row data count: {}'.format(total_cnt), LOG_INFO)

		# 選択団体番号
		select_no = config_data['abst_condition']['201005']

		#団体番号チェック
		if select_no is None or len(select_no) < 1: cmn._exit('info', 'GroupNo no data')

		log('sql row data count: {}'.format(total_cnt), LOG_INFO)


		log('!!!! python create_resultCSV 5.2 !!!!')

		# csvデータ生成
		for row in rows:
			if (cmn.check_abst_sts(str(int(row['examinee_id'])), cond_examinee) == False):				# 受診者
				log(' *** reject examinee', LOG_DBG)
				continue
			csv_row = {}
			data_row = {}
			TJ_val = None
			conv_data = {}
			#KEKKA1初期化
			examineeKekka1Data = {}
			#KEKKA2初期化
			examineeKekka2Data = {}

			if row['company_id'] == select_no and row['ins_group_id'] != select_no and row['contract_org_id'] != select_no:
				continue
			else:

				for x in range(len(rows2)):
					if row['examinee_id'] == rows2[x]['examinee_id'] and row['dt_appoint'] == rows2[x]['dt_appoint']:
						conv_data,rows2[x] = getdataItemconv(rows2[x],conv_data)
						data_row[x] =  rows2[x]

				data_row = convdataItemconv(data_row,conv_data)

				#住所枠選択
				if row['destination'] is None or row['destination'] == '' or row['destination'] == '0' :
					row['destination'] = '1'
				zipNum = 'zip' + str(row['destination'])
				addrNum = 'address' + str(row['destination'])
				row = getaddr(row,zipNum,addrNum)
				for col in columns:
					val = None
					# 検査項目・判定・所見の場合
					if col['col_name'] == 'DUMMY':
						continue
					elif col['col_name'] == 'value':
						try:
							for row2 in data_row.values():
								if col['sid_exam'] == row2['item_id']:
									if col['item_id'].startswith('Q0'):
										val = getQADataItemVale(row2,col)
									else:
										val = getTKcsvDataItemVale(row2,col)
									#log(val)
									csv_row[col['caption']] = val
								elif col['item_id'] == 'TJ0101' and col['item_id'] == row2['item_id']:
									if '総合所見' in conv_data:
										row2['value'] = row2['value'] + '　' + conv_data['総合所見']
									#総合判定
									TJ_val = getTKcsvDataItemVale(row2,col)

						except Exception as err:
							cmn.traceback_log(err)

					elif col['col_name'] == 'UM':
						csv_row[col['caption']] = None

					# 受診者基本情報
					else:
						try:
							if col['col_name'] == 'visitid':
								val = None
							elif col['col_name'] == 'HOKEN':
								#保険者番号
								val = config_data['abst_condition']['201005']
							elif col['col_name'] == 'Dc_name':
								#医師名
								val = row[col['col_name']]
							else:
								if col['col_name'] == 'zip':
									#郵便番号
									val = row[zipNum]
								elif col['col_name'] == 'adress':
									#住所
									val = row[addrNum]
								else:
									val = row[col['col_name']]
							val = mojiCheckConvAndCut(val, col)
							csv_row[col['caption']] = val
						except Exception as err:
							cmn.traceback_log(err)

				#総合判定、所見はIDないので直接作成
				csv_row['総合判定'] = TJ_val
				csv_row = DataItemVale(csv_row,csv_header,conv_data)
				#CC2Xの並べ替えに対応するため、受診者IDを「受信日+受診者ID」にする。txtには元の受診者IDを表示させるため、変換前にリストを作成
				examineeResultData.append({resultSuccessHeader['apoDay']:csv_row['健診実施年月日'],resultSuccessHeader['id']:csv_row['健診者ID']})
				csv_row['健診者ID'] = csv_row['健診実施年月日'] + csv_row['健診者ID']
				#決済ファイルを作る場合はここでデータを入れる(０円固定値)
				if 'f_kessai' in csv_option and csv_option['f_kessai'] == '1':
					examineeKekka1Data = get_price_data1(examineeKekka1Header,csv_row)
					examineeKekka2Data = get_price_data2(examineeKekka2Header,csv_row)
					#決済情報ファイル1のデータ
					csv_kessai1_data.append(examineeKekka1Data)
					# 決済情報ファイル２のデータ
					csv_kessai2_data.append(examineeKekka2Data)
					#貧血検査に固定値を入れる
					if '貧血の有無' in csv_row:
						csv_row['貧血検査(実施理由)'] = '契約により実施'

				csv_data.append(csv_row)




		log('!!!! python create_resultCSV 6 !!!!')
		log(csv_data)

		csv_config = cmn.get_csv_format(csv_option)
		csv.register_dialect('daidai',\
							 delimiter=csv_config['delimiter'],\
							 doublequote=csv_config['doublequote'],\
							 lineterminator=csv_config['terminated'],\
							 quoting=csv_config['quoting'])

		# tempfile.mkstemp(suffix=None, prefix=None, dir=None, text=False)			# これで作成した一時ファイルは自動で削除されない
		fobj = tempfile.mkstemp(suffix=out_file_suffix, prefix=out_file_prefix, text=False)		# tmpdirはシステムお任せ。ゴミが残ってもOSのポリシーに基づいて削除して貰う
		tmp_file_path = pl.PurePath(fobj[1])
		tmp_file = pl.Path(tmp_file_path)

		log('!!!! python create_resultCSV 7 !!!!')

		# 辞書型のデータを書き込む。ヘッダを参照して該当ヘッダの列に対応するデータを入れてくれるので位置が確定できる
		with open(tmp_file.resolve(), mode='r+', newline='', encoding=csv_config['encoding']) as f:
			# 特定健診の場合、頭に3行必要
			f.write('# {}{}'.format(','.join([str(k) for k in range(1, len(csv_header))]), csv_config['terminated']))
			f.write('#{}'.format(csv_config['terminated']))
			log('!!!! python create_resultCSV 8 !!!!')

			fp = csv.writer(f, dialect='daidai')

			log('!!!! python create_resultCSV 8.1 !!!!')

			# CSVのフォーマットにヘッダ指定
			# TODO: ヘッダに無いデータはエラーにせず無視する(出力しない)(extrasaction='ignore')
			fp = csv.DictWriter(f, dialect='daidai', fieldnames=csv_header, extrasaction='ignore')
			hed0 = fp.fieldnames[0]
			fp.fieldnames[0] = '# ' + fp.fieldnames[0]
			log('!!!! python create_resultCSV 8.2 !!!!')

			# ヘッダの書き込み
			if 'f_csvHeader' in conf.outsource_config['root']['outsource']['condition'] and conf.outsource_config['root']['outsource']['condition']['f_csvHeader'] == '1':
				fp.writeheader()
				fp.fieldnames[0] = hed0

			log('!!!! python create_resultCSV 8.3 !!!!')

			# 明細を書き込み
			for line in csv_data:
				log(line)
				fp.writerow(line)

			log('!!!! python create_resultCSV 8.4 !!!!')

		if 'f_kessai' in csv_option and csv_option['f_kessai'] == '1':
			# 決済1のファイル
			fobj = tempfile.mkstemp(suffix='.tmp', prefix=out_file_prefix+'kessai1_', text=False)
			tmp_file_path = pl.PurePath(fobj[1])
			tmp_kessai1_file = pl.Path(tmp_file_path)
			# 辞書型のデータを書き込む。ヘッダを参照して該当ヘッダの列に対応するデータを入れてくれるので位置が確定できる
			codecs.register_error('hoge', lambda e: ('?', e.end))
			with open(tmp_kessai1_file.resolve(), mode='r+', newline='', encoding=csv_config['encoding'], errors='hoge') as f:
				# 特定健診の場合、頭に3行必要
				fp = csv.DictWriter(f, dialect='daidai', fieldnames=list(examineeKekka1Header.values()), extrasaction='ignore')
				fp.writeheader()
				# IDでソート
				sortData = sorted(csv_kessai1_data, key=lambda x:(x.get(examineeKekka1Header['id']) is not None, x.get(examineeKekka1Header['id'])))
				# ソート済みデータを書き込む
				for line in sortData:
					fp.writerow(line)

			# 決済２のファイル
			fobj = tempfile.mkstemp(suffix='.tmp', prefix=out_file_prefix+'kessai2_', text=False)
			tmp_file_path = pl.PurePath(fobj[1])
			tmp_kessai2_file = pl.Path(tmp_file_path)
			# 辞書型のデータを書き込む。ヘッダを参照して該当ヘッダの列に対応するデータを入れてくれるので位置が確定できる
			codecs.register_error('hoge', lambda e: ('?', e.end))
			with open(tmp_kessai2_file.resolve(), mode='r+', newline='', encoding=csv_config['encoding'], errors='hoge') as f:
				# 特定健診の場合、頭に3行必要
				fp = csv.DictWriter(f, dialect='daidai', fieldnames=list(examineeKekka2Header.values()), extrasaction='ignore')
				fp.writeheader()
				# IDでソート
				sortData = sorted(csv_kessai2_data, key=lambda x:(x.get(examineeKekka2Header['id']) is not None, x.get(examineeKekka2Header['id'])))
				# ソート済みデータを書き込む
				for line in sortData:
					fp.writerow(line)

		# RESULT.txtファイルに正常出力者データを書き込む
		# FIXME: 書き込み処理ここ
		tmp_result_file = None
		if len(examineeResultData) > 0:
			# RESULT.txtに書き込むので、既に存在したらtmpファイルオブジェクトの新規作成は行わない
			fobj = tempfile.mkstemp(suffix='.tmp', prefix=out_file_prefix+'result_', text=False)		# tmpdirはシステムお任せ。ゴミが残ってもOSのポリシーに基づいて削除して貰う
			tmp_file_path = pl.PurePath(fobj[1])
			tmp_result_file = pl.Path(tmp_file_path)
			with open(tmp_result_file.resolve(), mode='a', newline='', encoding=csv_config['encoding'], errors='hoge') as f:
				f.write('・以下の受診者がXML作成の対象になります。\n')
				fp = csv.DictWriter(f, dialect='daidai', fieldnames=list(resultSuccessHeader.values()), extrasaction='ignore')
				fp.writeheader()
				# IDでソート
				sortDataA = sorted(examineeResultData, key=lambda x:(x.get(resultSuccessHeader['id']) is not None, x.get(resultSuccessHeader['id'])))
				# 日付でソート
				sortData = sorted(sortDataA, key=lambda x:(x.get(resultSuccessHeader['apoDay']) is not None, x.get(resultSuccessHeader['apoDay'])))
				for line in sortData:
					fp.writerow(line)
				f.write('\n')


		# ファイル欠落時はzipファイルの作成はしない
		if tmp_file is not None and tmp_result_file is not None and tmp_file.is_file() == True and tmp_result_file.is_file() == True:
			# zipファイル作成
			fobj = tempfile.mkstemp(suffix=out_file_suffix, prefix=out_file_prefix, text=False)		# tmpdirはシステムお任せ。ゴミが残ってもOSのポリシーに基づいて削除して貰う
			tmp_file_path = pl.PurePath(fobj[1])
			tmp_zip_file = pl.Path(tmp_file_path)
			with zipfile.ZipFile(tmp_zip_file.resolve(), 'w', compression=zipfile.ZIP_DEFLATED) as new_zip:
				# 結果ファイル
				new_zip.write(tmp_file, arcname='XML_KEKKA.CSV')
				# RESULTファイル
				new_zip.write(tmp_result_file, arcname='RESULT.txt')
				if 'f_kessai' in csv_option and csv_option['f_kessai'] == '1':
					# 決済１ファイル
					new_zip.write(tmp_kessai1_file, arcname='XML_KESSAI1.CSV')
					# 決済２ファイル
					new_zip.write(tmp_kessai2_file, arcname='XML_KESSAI2.CSV')

			log('Number of data: {0}'.format(total_cnt - 1))
			if total_cnt == 0:				# 絞り込みを行った結果、対象者０なら終わり(カウンタの初期は0)
				cmn.file_del(tmp_zip_file)		# 一時ファイルが存在するなら削除
				cmn._exit('success', 'no data')

			zip_file_name = tmp_zip_file.name

			log('!!!! python create_resultCSV 9 !!!!')
			csv_file_name = tmp_file.name

			# cmn.file_del(tmp_file)			# 一時ファイルが存在するなら削除

			# javascript側でこのキーワードを検索してファイル名を特定する
			msg2js('{0}{1}'.format(config_data['output_search_word'], zip_file_name))

	except Exception as err:
		cmn.file_del(tmp_file)	# こけたときにtmpfileが存在したら削除を試みる
		cmn.traceback_log(err)

	finally:
		# MySqlセッション終了
		sql.close()
		sql2.close()
		sql3.close()

def main():
	xml_outsource = None

	# sm_morgを取得
	row = cmn.get_sm_morg()
	if row is None: cmn._exit('sql_error', '[sm_morg] sid not found')
	if len(row) < 1: cmn._exit('sql_error', '[sm_morg] get failed')
	if len(row) > 1: cmn._exit('sql_error', '[sm_morg] duplicate: {}'.format(len(row)))
	try:
		ret = cmn.getXmlCstmInfo(row[0]['xml_cstminfo'])
		if ret == False: raise ValueError()
	except Exception as err:
		log('xml_cstminfo error:{}'.format(err))
		cmn._exit('xml_error', '[xml_cstminfo] xml convert failed')
	del row

	# 医療機関個別のm_outsourceを取得
	row = cmn.get_m_outsource(sid_section=config_data['sid_section'], sid=config_data['outsouceSid'])
	if row is None:
		# m_outsourceが見つからない
		cmn._exit('sql_error', '[m_outsource] sid_section not found')
	if len(row) != 1:
		# m_outsourceの取得失敗。返却されるのは1個を期待している
		cmn._exit('sql_error', '[m_outsource] get failed: SQL return rows Len:{}'.format(len(row)))
	try:
		xml_outsource = cmn.getXmlOutsource(row[0]['xml_outsource'])
	except Exception as err:
		log('m_outsoucr error:{}'.format(err))
		cmn._exit('xml_error', '[m_outsource] xml convert failed')

	# ベースとなるm_outsourceを特定して取得
	if 'form_code_subType' in conf.outsource_config['root']['outsource']['condition']:
		subFormCode = None
		baseId = None
		if 'subCode' in conf.outsource_config['root']['outsource']['condition']['form_code_subType']:
			subFormCode = conf.outsource_config['root']['outsource']['condition']['form_code_subType']['subCode']
		else:
			subFormCode = conf.outsource_config['root']['outsource']['condition']['form_code_subType']
		if 'base_sid' in conf.outsource_config['root']['outsource']['condition']:
			baseId = conf.outsource_config['root']['outsource']['condition']['base_sid']
		row = cmn.get_m_outsource(sid_section=config_data['sid_section'], sid=baseId, sid_morg='0', subFormCode=subFormCode)
		if row is None:
			# m_outsourceが見つからない
			cmn._exit('sql_error', '[m_outsource base] sid_section not found')
		if len(row) != 1:
			# m_outsourceの取得失敗。返却されるのは1個を期待している
			cmn._exit('sql_error', '[m_outsource base] get failed: SQL return rows Len:{}'.format(len(row)))
		try:
			xml_outsource = cmn.getXmlOutsource(row[0]['xml_outsource'])
		except Exception as err:
			log('m_outsoucr error:{}'.format(err))
			cmn._exit('xml_error', '[m_outsource base] xml convert failed')


	del row
	if xml_outsource is None: cmn._exit('sql_error', '[m_outsource] get failed')		# m_outsourceの取得失敗

	create_Tokuteikenshin(xml_outsource)

if __name__ == '__main__':
	#### デバッグ専用：使うときにコメント解除 ####
	## VSCode ver1.27.1がサポートしているptvsdのバージョンは「4.1.1」
	#import ptvsd
	#log('!!!! enable ptvsd !!!!')
	#ptvsd.enable_attach(address=('0.0.0.0', 3000), redirect_output=True)
	#ptvsd.wait_for_attach()
	#### ここまでデバッグ専用：未使用時はコメントアウト ####


	# 引数の解析
	config_data = cmn.args2config(sys.argv)

	if len(config_data) > 0:
		start = time.time()
		main()
		elapsed_time = time.time() - start
		log('elapsed_time: {:.3f} sec'.format(elapsed_time))	# 実行時間表示
		cmn._exit('success')		# 終わり


	else:
		cmn._exit('error')		# エラー

	cmn._exit('exit')				# 終わり
