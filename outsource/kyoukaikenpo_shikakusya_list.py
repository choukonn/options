#!/usr/bin/python3

# -*- coding: utf-8 -*-
# 文字コードはUTF-8で
# ネストが深いので４タブね。
# vim: ts=4 sts=4 sw=4

# 協会けんぽの受診者データ取り込み用のCSVを作成する

import sys
import tempfile
import xml.etree.ElementTree as ET
import csv
import datetime
import pathlib as pl
import codecs

# https://github.com/ikegami-yukino/jaconv/blob/master/README_JP.rst
import jaconv

import form_tools_py.conf as conf
import form_tools_py.common as cmn

msg2js = cmn.Log().msg2js
log = cmn.Log().log
sql = cmn.Sql()

abst_code = conf.abst_code

def outputcsv(config):

    sid_morg = config['sid_morg']

    org_sid = None

    sid_examinee = None

    if abst_code['org_affiliation'] in config['abst_condition']:

        if config['abst_condition'][abst_code['org_affiliation']] != '0':
            org_sid = config['abst_condition'][abst_code['org_affiliation']]
            if org_sid is not None and type(org_sid) is str and len(org_sid) < 1:
                org_sid = None


    if abst_code['examinee'] in config['abst_condition']:

        if len(config['abst_condition'][abst_code['examinee']]) > 0 and config['abst_condition'][abst_code['examinee']] != '0':
            # data = '0' 長さ１の”0”という文字列
            # data = ''　長さ0の空っぽの文字列
            sid_examinee = config['abst_condition'][abst_code['examinee']]


    dtfrom = config['date_start']
    dtto = config['date_end']

    ippan_split = conf.outsource_config['root']['outsource']['sid_me']['ippan'].split(',')
    fuka_split = conf.outsource_config['root']['outsource']['sid_me']['fuka'].split(',')
    tandoku_split = conf.outsource_config['root']['outsource']['sid_me']['tandoku'].split(',')

    # kenshin_course = ippan_split + fuka_split + tandoku_split

    sid_me = ','.join(ippan_split + fuka_split + tandoku_split)
    # sid_me = None


    # call p_kyoukaikenpo_shikaku_list(20020, null, NULL, NULL, NULL);
    query = "call p_kyoukaikenpo_shikaku_list(?, ?, ?, ?, ?, ?);"
    param = (sid_morg, org_sid, dtfrom, dtto, sid_me, sid_examinee)
    log('SQL: query: {}, param: {}'.format(query, param))
    # 'SQL: query: call p_kyoukaikenpo_shikaku_list(?, ?, ?, ?, ?, ?);, param: (20020, None, "2020/03/01", "2020/03/31", null, null)
    rows = sql.once(query, param)

    if rows is None:
        log('Data does not exist')
        return

    # 件数をログに表示
    log('findrow: {}'.format(len(rows)))

    # リスト
    shikakusya_list = []

	# 出力ファイル名の部品
    out_file_prefix = config['out_file_prefix']
    out_file_suffix = config['out_file_suffix']

    csv_header = ('hokensya_num', 'symbol', 'number', 'hihuyousya_num', 'dob', 'apo_date', 'kenshinkubun')
    csv_option = cmn.outsource_dict('condition')
    csv_config = cmn.get_csv_format(csv_option)
    csv.register_dialect('daidai', delimiter=csv_config['delimiter'], doublequote=csv_config['doublequote'], lineterminator=csv_config['terminated'], quoting=csv_config['quoting'])




    # コースが分かれている場合のみ健診区分が特定可能

    for row in rows: # SQLで取得したデータの解析を行い出力用データの作成
        kenshinkubun = '1'      # 初期値を1に設定

        if str(row['sid_me']) in ippan_split:
            kenshinkubun = '1'

        elif str(row['sid_me']) in fuka_split:
            kenshinkubun = '2'

        elif str(row['sid_me']) in tandoku_split:
            kenshinkubun = '3'


        temp = {
                'hokensya_num': row['hokensya_num'],
                'symbol': row['symbol'],
                'number': row['number'],
                'hihuyousya_num': row['hihuyousya_num'],
                'dob': row['dob'],
                'apo_date': row['apo_date'],
                'kenshinkubun': kenshinkubun
                }


        shikakusya_list.append(temp)


    fobj = tempfile.mkstemp(suffix=out_file_suffix, prefix=out_file_prefix, text=False)		# tmpdirはシステムお任せ。ゴミが残ってもOSのポリシーに基づいて削除して貰う
    tmp_file_path = pl.PurePath(fobj[1])
    tmp_file = pl.Path(tmp_file_path)

    try:
        # 辞書型のデータを書き込む。ヘッダを参照して該当ヘッダの列に対応するデータを入れてくれるので位置が確定できる
        # 文字化けは？にしてみるテスト
        codecs.register_error('hoge', lambda e: ('?', e.end))
        with open(tmp_file.resolve(), mode='r+', newline='', encoding = csv_config['encoding'], errors='hoge') as f:

            # CSVのフォーマットにヘッダ指定
            # TODO: ヘッダに無いデータはエラーにせず無視する(出力しない)(extrasaction='ignore')
            fp = csv.DictWriter(f, dialect='daidai', fieldnames=csv_header, extrasaction='ignore')

            # ソート済みデータを書き込む
            for line in shikakusya_list:
                try:
                    fp.writerow(line)
                except Exception as err:
                    log('write error : {}'.format(err))

            csv_file_name = tmp_file.name

        # javascript側でこのキーワードを検索してファイル名を特定する
        msg2js('{0}{1}'.format(config['output_search_word'], csv_file_name))


    except Exception as err:
        cmn.file_del(tmp_file)	# こけたときにtmpfileが存在したら削除を試みる
        cmn.traceback_log(err)


    return
