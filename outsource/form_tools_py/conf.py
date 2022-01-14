#!/usr/bin/python3

# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4


# jsから引数で貰うようにする
config_data = {}
# example_config_data = {
#'http_port': 'xxxx',
#'mysql':'mysql://user:passs@ip:port/DBname',
#'sid_section':'132005',
#'sid_morg':'20023',
#'status':'3',
#'date_start':'2010-01-01',
#'date_end':'2018-12-31',
#'form_name':'健康診断受診者一覧表'
#}

# XMLなm_outsourceを丸ごと
outsource_config = {}
# 医療機関情報（sm_morgのxml_cstminfo）
xml_cstminfo = {}

# 言語対応関係
i18n_list = []
i18n_item = {}
i18n_locale = {}
# ロケール
# TODO: SELECT * FROM dd_data_in.m_i18n_locale;を参考
lo_locale = {
	'ja-JP'		: 1,	# 日本
	'en-US'		: 2,	# 米国
	'vi-VN'		: 3,	# ベトナム
	'mi-MM'		: 4,	# ミャンマー(my-MMではないので注意)
	}

# グローバルで参照したいよね
m_section = {}
m_qualitative = {}
m_opinion_rankset = {}
m_criterion = {}
# 変換オプション
convert_option = {}

## 項目の標準／オプションの状態を格納する
# 値の意味
# 1：標準、未実施
# 2：オプション、未実施
# 3：標準、実施
# 4：オプション、実施
inspStdOptData = {}

# outsource（XML）内でレイアウトファイル名をtag（要素）を作る場合、数字始まりがダメなので先頭に文字を入れる
# それをここで決め打ちする
# (例)f200316　の頭の文字
form_num_prefix = 'f'

# 終了コード
ret_code = {
	# js側ではエラー扱いにしない
	'success': 0,
	'info': 0,
	'exit': 1,
	'warning': 2,
	# xml error
	'xml_error': 100,
	'sql_error': 101,
	# system error
	'error': 253,
	'signal': 254,
	'die': 255
}

# ログレベル
LOG_NOTICE = 0
LOG_INFO = 1
LOG_WARN = 11
LOG_ERR = 21
LOG_DBG = 254
LOG_ALL = 255
LOG_DEF = LOG_ERR	# デフォルトはエラー

# m_sectionのsidをDBから引っ張ってきて名前一致させるのは微妙なので、固定で持たせる
abst_code = {
	#'date'				: '201001',		# 受診日
	'org_agreement'		: '201002',		# 契約団体
	'course'			: '201003',		# 受診コース
	'org_affiliation'	: '201005',		# 所属団体
	'examinee'			: '201007',		# 健診者
	'status'			: '201011',		# 受付ステータス
}

sort_code = {
	'date'				: '202001',		# 受診日
	'course'			: '202002',		# 受診コース
	'org_agreement'		: '202004',		# 契約団体
	'org_affiliation'	: '202005',		# 所属団体
	'number'			: '202006',		# 受診番号
	'examinee'			: '202009',		# 健診者
}

form_code = {
	'inspection'			: '200301',		# 連名表(検査結果リスト)
	'kyoukaikenpo'			: '200302',		# 協会けんぽ（生活習慣／事業者健診）
	'tokuteikenshin'		: '200303',		# 特定健診
	'reservation'			: '200311',		# 受診者リスト
	'escort_sheet'			: '200312',		# 受診項目
	'interview'				: '200313',		# 問診項目
	'price'					: '200314',		# 料金リスト
	'invoice'				: '200315',		# 請求書
	'Receipt'				: '200316',		# 領収書
	'interview_gynecology'	: '200317',		# 問診項目(婦人科)		# TODO：暫定対応。マクロ側で切り替え対応出来たら不要になる
	'simple_report'			: '200318',		# 簡易報告書
	'statistics_individual'	: '200319',		# (統計情報)会計情報：個人
	'statistics_daily'		: '200320',		# (統計情報)会計情報：日別
	'statistics_optionList'	: '200321',		# (統計情報)検査項目（オプション）情報：日別
	'interview_2nd'			: '200322',		# 問診(2回目)

	'denri_kojin'			: '200341', 	# 電離放射線(個人票)
	'tokkabutu_kojin'		: '200342', 	# 特定化学物質(個人票)
	'yuuki_kojin'			: '200343', 	# 有機溶剤等(個人票)

	'denri_toukei'			: '200351', 	# 電離放射線(統計)
	'tokkabutu_toukei'		: '200352', 	# 特定化学物質(統計)
	'yuuki_toukei'			: '200353', 	# 有機溶剤等(統計)
}

## CSV出力機能内部での識別用
form_code_subType = {
	'20030201'				: None,			# （協会けんぽ）生活習慣予防
	'20030202'				: None,			# （協会けんぽ）事業者健診
	'20030203'				: None,			# 　特定健診
	'20030204'				: None,			# 　(協会けんぽ)資格者一括リスト
	'20030205'				: None,			# 　特定健診全項目
}

# 受診者情報
examInfo = {
	'sid'				: None,
	'sid_examinee'		: None,
	'id'				: None,
	'appoint_day'		: None,
	'appo_sts'			: None,
	'course_sid'		: None,
	'courseName'		: None,
	'sid_cntracot'		: None,
	'age'				: None,
	'sex'				: None,
	'locale'			: None,
}

