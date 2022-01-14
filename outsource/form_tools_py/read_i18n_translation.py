#!/usr/bin/python3

# -*- coding: utf-8 -*-
# 文字コードはUTF-8で
# vim: ts=4 sts=4 sw=4

import os
import sys
import pathlib as pl
#import json
#import unicodedata
import re

import form_tools_py.conf as conf
import form_tools_py.common as cmn

# 多言語翻訳のファイルを読み込んで、辞書を作成して返却する
# 呼び元はDxxxxというkeyを辞書から引っ張り、対応するvalを返すようにすればいいはず。

# 以下ディレクトリ内のjsファイルを読み込む
# 読み込み対象のjsファイルに妙なコメントの付け方をされると困るので、jsファイルの編集を行う際は気を付けて貰う
# node_modules\narwhal\i18n\src\xxx.js
# ja-JP.js
# un-US.js
# vi-VN.js
# mi-MM.js


# PATHの組み立てに使う
script_file = pl.Path(__file__).resolve()
script_dir = script_file.parents[0]

################################################################################
#msg2js = cmn.Log().msg2js
log = cmn.Log().log
dbg_log = cmn.Log().dbg_log
sql = cmn.Sql()
zen2han = cmn.Zenkaku2Hankaku().zen2han

################################################################################

def read_file(file_name):

	# PATHの作成
	# (例) Narwhal\node_modules\narwhal\i18n\src\en-US.js
	file_path = script_dir.joinpath(pl.PurePath('..', '..', '..', '..', 'node_modules', 'narwhal', 'i18n' , 'src', file_name))

	i18n_dict = {}

	# 存在チェック
	p = pl.Path(file_path)
	if p.exists() and p.is_file:
		pass
	else:
		cmn._exit('error', 'i18n file not found: {0}'.format(file_name))

	# 読み込んだファイルから抽出するための条件
	#pattern1 = r".D99999"				# debug
	#pattern1 = r".D02326"				# debug
	pattern1 = r".[A-Z]{1,2}[0-9]{5,10}"	# Dxxxxが含まれる行の検索で使用
	pattern2 = r"(//.*$|/\*.+\*/)"			# コメント行の削除に使用。なお範囲コメントの扱いが難しいので、使われていると予想外な削除が行われる可能性大
	pattern3 = r",$"						# 末尾のカンマの削除に使用
	pattern4 = r"(\\n|\\)"					# [\n]とか特定記号をエスケープするための[\]を削除。CSV内に改行は含めない
	pattern_last = r"(^'|'$)"				# 文字列をくくっているシングルクォートの削除に使用。先頭と末尾を指定しているので、分解した最後に実施する
	abst1 = re.compile(pattern1)
	abst2 = re.compile(pattern2)
	abst3 = re.compile(pattern3)
	abst4 = re.compile(pattern4)
	abst_last = re.compile(pattern_last)

	with p.open(mode='r', encoding='UTF-8') as f:
		tmp_list1 = []
		tmp_list2 = []
		for l in f.readlines():
			reobj = abst1.match(l.strip())			# 抽出対象の行なのかチェック
			if reobj:								# 一致したら不要なものを削除していく
				key = ''
				val = ''
				text = reobj.string
				text = abst2.sub('', text.strip())	# パターンnの条件で削除、以下同文
				text = abst3.sub('', text.strip())
				text = abst4.sub('', text.strip())

				text = abst_last.sub('', text.strip())

				# 分割後に文字列をくくっている前後のシングルクォートを落とす
				text = text.split(':')
				key = zen2han(abst_last.sub('', text[0].strip()))	# TODO: 念のため、全角->半角変換も通す。対応できない文字が入っていたら元を直せ
				val = zen2han(abst_last.sub('', text[1].strip()))	#       日本語以外の場合どうなる！？

				# Dxxxxxをkey、翻訳された文をvalueとして対応するlistを作成し、最後に辞書にする
				tmp_list1.append(key.strip())
				tmp_list2.append(val.strip())

				del key, val, text

		# 辞書に変換
		#i18n_dict = {p.stem: dict(zip(tmp_list1, tmp_list2))}
		i18n_dict = dict(zip(tmp_list1, tmp_list2))

		# タプルに変換
		i18n_tuple = tuple(i18n_dict.items())

	return i18n_tuple

#@cmn.measure	# デバッグ専用
def getDBlist(user=False, exam=False):
	# 翻訳オプションが無いとか無効の場合は終わり
	if 'f_translation' in conf.convert_option and conf.convert_option['f_translation'] != '1':
		if conf.convert_option['f_translation'] == '0':
			return
		if 'translation_lang' not in conf.config_data:
			return

	defLocale = 'en-US'		# デフォルト言語
	userLocale = conf.config_data['translation_lang'] if conf.config_data['translation_lang'] is not None else ''		# ログインユーザ
	examLocale = conf.examInfo['locale'] if conf.examInfo['locale'] is not None else ''									# 受診者

	localeList = [defLocale,]
	if user: localeList.append(userLocale)
	if exam: localeList.append(examLocale)
	localeList = list(set(localeList))			# 重複排除

	# CALL p_i18ndictionary('GET',20051,'ja-JP');
	query = 'CALL p_i18ndictionary("GET",?,?);'

	# 言語マスタを取得
	for getLocale in localeList:
		if getLocale is None: continue
		# 未取得の時だけ
		if getLocale not in conf.i18n_locale or len(conf.i18n_locale[getLocale]) < 1:
			param = (conf.config_data['sid_morg'], getLocale)
			rows = cmn.get_sql_query(query, param)
			if rows is None: continue
			conf.i18n_locale[getLocale] = tuple({k['code']:k['text'] for k in rows}.items())

	conf.i18n_list = conf.i18n_locale[defLocale]

	return

if __name__ == '__main__':
	pass

	# 未使用。関数を直接呼ぶ
	#if len(sys.argv) <= 1:
	#	log('argv error: {0}'.format(__file__))
	#	cmn._exit('error')

	#### debug ####
	#trance_dict = read_i18n('en-US.js')
	#log(trance_dict)
