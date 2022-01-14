#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# 取り込みファイルの解析用
from collections import defaultdict
from datetime import datetime

# myapp
from .mod import my_file as myFile
from . import plgCommon as plgCmn

modeAppoint = 1
modeExam = 2


# ビンメック用JSONデータ内の重複チェック
def duplicateCheckJson90006(sidMorg, inData, mapDataAll):
	data = []
	tmp = defaultdict(list)

	try:
		if mapDataAll['optionMap']['f_force_visitId'] == 1:
			keyId = mapDataAll['appointMap']['visitId']
		else:
			keyId = mapDataAll['examineeMap']['examinee/id']
	except:
		raise

	try:
		for key in inData:
			tmp[key[keyId]].append(key)
	except:
		raise

	updItemName = mapDataAll['dataNameMap']['updateTime']
	appointDay = mapDataAll['appointMap']['appointDay']
	courseId = mapDataAll['appointMap']['courseId']

	if tmp is not None:
		try:
			for val in tmp.values():
				valSort = sorted(val, key=lambda x: x[mapDataAll['appointMap']['apoAction']], reverse=True)

				if len(valSort) > 1:
					# 日時情報をもっているものを抽出
					tmp2 = [k for k in valSort if updItemName in k and k[updItemName] is not None]
					# 日時情報なしを抽出
					tmp3 = [k for k in valSort if updItemName in k and k[updItemName] is None]

					# 日付ソート
					if len(tmp2) > 1:
						tmp2Sort = sorted(tmp2, key=lambda x: plgCmn.text2datetime(x[updItemName]), reverse=True)
						# kokokara FIXME: ロジックが考えつかないへたくそ
						# jsonデータで、新規->キャンセルと並んでいるものを受け取るたびに延々とキャンセル->新規登録が行われるのを抑止したい
						# 予約日／コースIDが重複するデータは除外したい
						tmpExtraction = []
						tmp4 = []
						for tmpCheck in tmp2Sort:
							if len(tmpExtraction) > 0:
								# 含まれているものが存在するのか？
								for tkey in tmpExtraction:
									# 予約日またはコースIDが一致しないものを格納
									if tmpCheck[appointDay] not in tkey.values() or tmpCheck[courseId] not in tkey.values():
										tmp4.append(tmpCheck)

							else:
								tmpExtraction.append(tmpCheck)

						if len(tmp4) > 0:
							tmpExtraction.extend(tmp4)
						# kokomade

						tmpExtractionSort = sorted(tmpExtraction, key=lambda x: plgCmn.text2datetime(x[updItemName]))
						data.extend(tmpExtractionSort)
					else:
						data.extend(tmp2)

					# 日時情報なしは全て処理対象とする（新規登録扱い）
					if len(tmp3) > 0:
						data.extend(tmp3)
				else:
					data.extend(valSort)
		except:
			raise

		if len(data) < 1:
			return None

	return data


# 90006(ビンメック)用
def analysis90006Json(sidMorg, fp, mapDataAll):
	ret = {
		'data': None,
		'mode': None,
	}
	data = []

	try:
		jsonData = myFile.jsonRead(fp)
	except Exception as err:
		raise

	try:
		# 受診者データ
		if 'PatientList' in jsonData and jsonData['PatientList'] is not None and 'Patient' in jsonData['PatientList'] and jsonData['PatientList']['Patient'] is not None:
			data = [{k: v for k,v in item.items()} for item in jsonData['PatientList']['Patient']]
			ret['mode'] = modeExam

		# コース情報
		elif 'PackageList' in jsonData and jsonData['PackageList'] is not None and 'Package' in jsonData['PackageList'] and jsonData['PackageList']['Package'] is not None:
			ret['mode'] = modeAppoint
			pkgItemList = duplicateCheckJson90006(sidMorg, jsonData['PackageList']['Package'], mapDataAll)
			for pkgItem in pkgItemList:
				# オーダー以外
				tmp1 = {k: v for k,v in pkgItem.items() if k != 'OrderList'}
				# オーダー情報
				tmp2 = defaultdict(set)
				if 'OrderList' in pkgItem and pkgItem['OrderList'] is not None and len(pkgItem['OrderList']) > 0:
					orderList = pkgItem['OrderList']
					if 'Order' in orderList and len(orderList['Order']) > 0:
						orderItemList = orderList['Order']
						for orderItem in orderItemList:
							# ビンメックはこのitemが存在するだけで、実施扱い
							if 'OrderId' in orderItem:
								tmp2[orderItem['OrderId']] = '1'

				data.append({**tmp1, **tmp2})
				del tmp1, tmp2

	except Exception as err:
		raise

	if data is not None and len(data) > 0:
		ret['data'] = data

	return ret


# 医療機関別
def analysisProc(sidMorg, fp, fileSuffix, mapDataAll):
	ret = None
	try:
		if fileSuffix.upper() == '.JSON':
			ret = analysis90006Json(sidMorg, fp, mapDataAll)
	except Exception as err:
		raise

	return ret
