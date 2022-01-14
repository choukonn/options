#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

from collections import defaultdict

# myapp
from .plgCmd import m_me

# 更新者
sidUpd = 0

# オプション
optionData = {
	'default'		: {
		'sid_upd': sidUpd,
		# t_appoint登録時にステータスを強制で受付にする
		'f_fourceCheckInOn': 0,
		# visitIDの強制必須フラグ(0=OFF, 1=ON)
		'f_force_visitId': 1,
		# K+予約連携機能ON/OFF
		'f_kp_appoint_link': 0,
		# コース情報の更新時刻のチェックを行う
		'f_courseUpdateTimeCheck': 0,
		# データ内に存在しないオプション項目は全て未実施扱い
		'f_inspOptNotExistForceDisable': 0,
		# コースIDとvisitIdが登録済みのt_appointと不一致の場合、強制キャンセルを行う
		'f_unmatchIdAppointForceCancel': 0,
		# 国コードと言語コードをべた書き内容で強制する
		'f_CountryCode2langCode': 0,
		# 新規受信データのvid／予約日／コースIDが一致するコース情報の最終更新ステータスがキャンセルの場合、強制スキップを行う
		'f_force_courseUpdLastStsCancelSkip': 1,
		# 団体向けコースを団体なしで登録可にする
		'f_force_not_org_regist': 0,
	},
	'4'				: {
		'f_force_visitId': 0,
		'f_kp_appoint_link': 1,
	},
	'20073' : {
		'f_force_visitId': 0,
		# vidがないので使えない
		'f_force_courseUpdLastStsCancelSkip': 0,
		# 予約専用取り込み（検査項目操作なし）
		'f_appoint_only': 1,
	},
	'90006'			: {
		'f_fourceCheckInOn': 1,
		'f_force_visitId': 1,
		'f_kp_appoint_link': 1,
		'f_courseUpdateTimeCheck': 1,
		'f_inspOptNotExistForceDisable': 1,
		'f_unmatchIdAppointForceCancel': 0,
		'f_CountryCode2langCode': 1,
	},
	'90007'			: {
		'f_fourceCheckInOn': 0,
		'f_force_visitId': 1,
		'f_kp_appoint_link': 1,
		'f_courseUpdateTimeCheck': 0,
		'f_inspOptNotExistForceDisable': 1,
		'f_unmatchIdAppointForceCancel': 0,
		'f_CountryCode2langCode': 0,
		'f_force_not_org_regist': 1,
		# 'f_allDataNullisAppointCancel': 1,		# 強制'予約/受付' => 'キャンセル'
	},
}

# 受診者情報
examineeMappingData = {
	'default': {
		'examinee/id': 'Id',
		'examinee/name': 'Name',
		'examinee/name-kana': 'Kana',
		'examinee/birthday': 'Dob',
		'examinee/sex': 'Sex',
		'examinee/contact/send_zip': 'Zip',
		'examinee/contact/send_addr': 'Address',
		'examinee/contact/tel': 'Tel',
		'examinee/contact/fax': 'Fax',
		'examinee/contact/email': 'Email',
	},
	'4': {
		'examinee/id': '健診者ＩＤ',
		'examinee/name': '氏名漢字',
		'examinee/name-kana': '氏名カナ',
		'examinee/birthday': '生年月日',
		'examinee/sex': '性別',
		#'examinee/bloodtype': '血液型',
		'examinee/contact/send_zip': '郵便番号',
		'examinee/contact/send_addr': '住所1',
		'examinee/contact/send_addr_sub': '住所2',
		'examinee/contact/tel': '電話番号',
		'examinee/contact/fax': 'FAX番号',
		'examinee/contact/email': 'Ｅメール',
		'examinee/f_examinee': '保険家族区分',
		'examinee/hk_no': '保健番号',
	},
	'90006': {
		'examinee/id': 'Id',
		'examinee/my_number': 'IdNumber',
		'examinee/name': 'Name',
		'examinee/name-kana': 'Alphabet',
		'examinee/birthday': 'Dob',
		'examinee/sex': 'Sex',
		'examinee/locale': 'Language',
		'examinee/remarks': 'Remarks',
		'examinee/nationality': 'Nationality',
		'examinee/contact/zip1': 'Zip1',
		'examinee/contact/address1': 'Address1',
		'examinee/contact/zip2': 'Zip2',
		'examinee/contact/address2': 'Address2',
		'examinee/contact/zip3': 'Zip3',
		'examinee/contact/address3': 'Address3',
		'examinee/contact/tel': 'Tel1',
		'examinee/contact/tel2': 'Tel2',
		'examinee/contact/tel3': 'Tel3',
		'examinee/contact/destination': 'DestAddrNum',
		'examinee/contact/fax': 'Fax',
		'examinee/contact/email': 'Email',
		'examinee/status/emphasis_information/f_allergy': 'emphasisInfoAllergy',
		'examinee/status/emphasis_information/f_hbv': 'emphasisInfoHbv',
		'examinee/status/emphasis_information/f_hcv': 'emphasisInfoHcv',
		'examinee/status/emphasis_information/f_hiv': 'emphasisInfoHiv',
		'examinee/status/emphasis_information/f_syphilitis': 'emphasisInfoSyphilitis',
		'examinee/status/emphasis_information/remarks': 'emphasisInfoRemarks',
		'examinee/status/medical_information/f_pacemaker': 'medicalInfoPacemaker',
		'examinee/status/medical_information/f_internal_metal': 'medicalInfoInternalMetal',
		'examinee/status/medical_information/f_care': 'medicalInfoCare',
		'examinee/status/medical_information/f_blood_difficult': 'medicalInfoBloodDifficult',
		'examinee/status/medical_information/remarks': 'medicalInfoRemarks',
		'examinee/status/personal_information/f_vip': 'personalInfoVip',
		'examinee/status/personal_information/f_claim': 'personalInfoClaim',
		'examinee/status/personal_information/f_prolix': 'personalInfoProlix',
		'examinee/status/personal_information/remarks': 'personalInfoRemarks',
	},
	'90007': {
		'examinee/id': 'Id',
		'examinee/name': 'Name',
		'examinee/name-kana': 'Kana',
		'examinee/birthday': 'Dob',
		'examinee/sex': 'Sex',
		'examinee/contact/send_addr': 'Address',
		'examinee/contact/zip1': 'Zip',
		'examinee/contact/email': 'Email',
		'examinee/remarks': 'Remarks',
		'examinee/status/personal_information/remarks': 'Memo',
		'examinee/status/emphasis_information/remarks': 'remarks',
	}
}

# 団体情報
orgMappingData = {
	'default': {
		'org/n_org': 'CompanyId',
		'org/name': 'Company',
		'org/name-kana': 'CompanyAlphabet',
		'org/address2': 'CompanyAddress',
		'org/tel': 'CompanyTell',
		'org/fax': 'CompanyFax',
	},
	'4': {
		'org/n_org': '団体番号',
		'org/name': '団体名',
		'org/name-kana': '団体名（ふりがな）',
	},
	'90005': {
		'org/n_org': 'CompanyId',
		'org/name': 'Company',
		'org/name-kana': 'CompanyAlphabet',
	},
	'90006': {
		'org/n_org': 'CompanyId',
		'org/name': 'Company',
		'org/name-kana': 'CompanyAlphabet',
	},
}

# 予約情報
appointMappingData = {
	'default': {
		'appointDay'		: 'AppointDate',
		'appointTime'		: 'AppointTime',
		'courseName'		: 'CourseName',
		'courseId'			: 'CourseId',
	},
	'20073': {
		'karuteId'			: 'Id',
		'appointDay'		: 'AppointDate',
		'appointTime'		: 'AppointTime',
		'courseName'		: 'CourseName',
		'courseId'			: 'CourseId',
		'apoStatus'			: 'ApoStatus',
		'apoAction'			: 'ApoAction',
		'remarks'			: 'remarks',
	},
	'90005': {	# 四川
		'appointDay'		: 'AppointDate',
		'appointTime'		: 'AppointTime',
		'courseName'		: 'CourseName',
		'courseId'			: 'CourseId',
		'visitId'			: 'VisitId',
		'apoStatus'			: 'ApoStatus',
		'apoAction'			: 'ApoAction',
	},
	'90006': {	# ビンメック
		'appointDay'		: 'AppointDate',
		'appointTime'		: 'AppointTime',
		'courseName'		: 'CourseName',
		'courseId'			: 'CourseId',
		'visitId'			: 'VisitId',
		'apoStatus'			: 'ApoStatus',
		'apoAction'			: 'ApoAction',
	},
	'90007': {	# こうのす
		'appointDay'		: 'AppointDate',
		'visitId'			: 'AppointNumber',
		'apoAction'			: 'AppointStatus',
		'courseName'		: 'CourseName',
		'courseId'			: 'CourseId',
		'karuteId'			: 'Id',
		'name'				: 'Name',
		'kana'				: 'Kana',
		'sex'				: 'Sex',
		'birthday'			: 'Dob',
		'age'				: 'Age',
		'zip'				: 'Zip',
		'address'			: 'Address',
		'company'			: 'Company',
		'companyId'			: 'CompanyId',
		'remarks'			: 'Remarks',
	}
}
"""
'90007': {	# 成田病院
		'appointDay'		: 'AppointDate',
		'appointTime'		: 'Time',
		'karuteId'			: 'Id',
		'name'				: 'Name',
		'birthday'			: 'Birthday',
		'sex'				: 'Sex',
		'orgNo'				: 'OrgNo',
		'orgName'			: 'OrgName',
		'insOrgNo'			: 'InsOrgNo',
		'insOrgName'		: 'InsOrgName',
		'areaOrgNo'			: 'AreaOrgNo',
		'areaOrgName'		: 'AreaOrgName',
		'otherOrgNo'		: 'OtherOrgNo',
		'otherOrgName'		: 'OtherOrgName',
		'employeeNo'		: 'EmployeeNo',
		'insSymbol'			: 'InsSymbol',
		'insNo'				: 'InsNo',
		'sOrgName'			: 'SOrgName',
		'sOrg'				: 'SOrg',
		'courseId'			: 'CourseId',
		'courseName'		: 'CourseName',
		'apoStatus'			: 'ApoStatus',
		'visitId'			: 'VisitId',
		'apoAction'			: 'ApoAction',
		'option1'			: 'Option1',
		'option2'			: 'Option2',
		'option3'			: 'Option3',
		'option4'			: 'Option4',
		'option5'			: 'Option5',
		'option6'			: 'Option6',
		'option7'			: 'Option7',
		'option8'			: 'Option8',
		'option9'			: 'Option9',
		'option10'			: 'Option10',
		'option11'			: 'Option11',
		'option12'			: 'Option12',
		'option13'			: 'Option13',
		'option14'			: 'Option14',
		'option15'			: 'Option15',
		'option16'			: 'Option16',
		'option17'			: 'Option17',
		'option18'			: 'Option18',
		'option19'			: 'Option19',
		'option20'			: 'Option20',
		'yobi1'				: 'Yobi1',
		'yobi2'				: 'Yobi2',
		'yobi3'				: 'Yobi3',
		'yobi4'				: 'Yobi4',
		'yobi5'				: 'Yobi5',
	}
"""
# '90007': {
# 	'examinee': ['examinee/id','examinee/name'],
# 	'appoint': ['appointDay', 'appointTime', 'karuteId', 'sOrgName', 'sOrg', 'courseId', 'apoStatus', 'visitId', 'apoAction'],
# }

# 必須項目（ベース）
requiredBaseData = {
	'default': {
		'examinee': ['examinee/id','examinee/name', 'examinee/birthday', 'examinee/sex'],
		'appoint': ['appointDay', 'courseId', 'apoStatus', 'apoAction'],
	},
	'20073': {
		'examinee': [],
		'appoint': ['karuteId', 'appointDay', 'courseId', 'apoStatus', 'apoAction'],
	},
	'90005': {
		'examinee': ['examinee/id','examinee/name', 'examinee/birthday', 'examinee/sex'],
		'appoint': ['appointDay', 'courseId'],
	},
	'90007': {
		'examinee': ['examinee/id','examinee/name'],
		'appoint': ['visitId', 'appointDay', 'apoAction', 'courseName', 'courseId', 'karuteId', 'name', 'sex', 'birthday'],
	}

}
# 必須項目（オプション）
requiredOptData = {
	'default': {
		'appoint': ['visitId'],
	},
	'20073': {
		'appoint': [],
	},
	'90005': {
		'appoint': ['visitId'],
	},
}

# データ内の定義情報用
dataItemMapping = {
	'default': {
		'updateTime' : 'UpdateTime',
		'statusFlag' : 'stsFlag',
	}
}

# 団体なしでも登録するコース系統(宿泊コースの2～3日目など)
force_not_org_regist = {'90007':['80019']}


# 差分取り込み
# 2次元配列はめんどくさいので、渡すオブジェクトは1次元のみで。
def mergeData(src, dst):
	valListFlag = False
	try:
		d = defaultdict(set)
		if type(src) == list:
			for k,v in src:
				if k in dst.keys():
					d[k].update(dst[k])
				else:
					d[k].update(v)
		elif type(src) == dict and type(dst) == dict:
			for key in src:
				d1 = []
				if type(src[key]) != list:
					break
				valListFlag = True
				d1 = list(set(src[key]) & set(dst[key]))
				noDuplicateKey = set(src[key]) ^ set(dst[key])
				if len(noDuplicateKey) > 0:
					for key2 in noDuplicateKey:
						if key2 in src[key]:
							d1.append(key2)
				d[key].update(d1)
			if not valListFlag:
				for key, val in src.items():
					# dstに含まれる場合はvalを比較
					if key in dst:
						# 不一致の場合、srcの値を採用
						if dst[key] != val:
							d[key] = val
						else:
							d[key] = val
					else:
						d[key] = val

	except:
		raise

	ret = {k : v for k,v in d.items()}
	return ret


# 受診者情報取得
def examineeMapGet(sidMorg):
	try:
		d = examineeMappingData['default']
		if sidMorg in examineeMappingData.keys():
			d = mergeData(dst=examineeMappingData['default'], src=examineeMappingData[sidMorg])
	except:
		raise
	return d

# 団体情報取得
def orgMapGet(sidMorg):
	try:
		d = orgMappingData['default']
		if sidMorg in orgMappingData.keys():
			d = mergeData(dst=orgMappingData['default'], src=orgMappingData[sidMorg])
	except:
		raise
	return d

# 予約情報取得
def appointMapGet(sidMorg):
	try:
		d = appointMappingData['default']
		if sidMorg in appointMappingData.keys():
			d = mergeData(dst=appointMappingData['default'], src=appointMappingData[sidMorg])
	except:
		raise
	return d

# オプション情報取得
def optionMapGet(sidMorg):
	try:
		d = optionData['default']
		if sidMorg in optionData.keys():
			d = {**optionData['default'], **optionData[sidMorg]}
	except:
		raise
	return d

# 必須情報取得
def requiredMapGet(sidMorg):
	try:
		# 必須
		d1 = requiredBaseData['default']
		if sidMorg in requiredBaseData.keys():
			d1 = mergeData(dst=requiredBaseData['default'], src=requiredBaseData[sidMorg])
		# オプション
		d2 = requiredOptData['default']
		if sidMorg in requiredOptData.keys():
			d2 = mergeData(dst=requiredOptData['default'], src=requiredOptData[sidMorg])
		# 結合
		d = {}
		for key, val in d1.items():
			d[key] = []
			if key in d2:
				d[key] = list(set(d2[key]) | set(val))
			else:
				d[key] = val
	except:
		raise
	return d

# コース情報取得
def courseMapGet(sidMorg):
	try:
		d = None
		# m_meの取得
		# {'courseId': 'C10001', 'courseName': '人間ドック', 'sidMe':'5', 'sid':'388'},
		rows = m_me.getMe(sidMorg)
		if rows is not None:
			d = [{'courseId': row['inCourseID'], 'courseName': row['name'], 'sidMe': str(row['sid']), 'sid': str(row['sid_criterion']), 'psid': str(row['psid'])} for row in rows]
		return d
	except:
		raise


# データ定義情報
def dataItemMapGet(sidMorg):
	try:
		d = dataItemMapping['default']
		if sidMorg in dataItemMapping.keys():
			d = mergeData(dst=dataItemMapping['default'], src=dataItemMapping[sidMorg])
	except:
		raise
	return d
