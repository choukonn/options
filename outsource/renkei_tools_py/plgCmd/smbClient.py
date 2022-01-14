#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sts=4 sw=4

# sambaアクセスするためのやつ

from logging import getLogger
logger = getLogger('days_renkei').getChild(__name__)

import platform
import pathlib
import re
from smb.SMBConnection import SMBConnection


# myapp



# こういう感じで渡すと、解析した結果を返却する
# 必要なオプションのみ指定し、初期値でいい場合はオプション自体をつけないこと
# 'smb://hcs-was:445/daidai/90006/11/out&is_direct_tcp=True&domain=WORKGROUP&pattern=*.job'


def analysisPath(smbPath):
	parse1 = re.compile(r'&.*$')
	import urllib.parse
	config = {}
	# 無理やりパース
	url = urllib.parse.quote(smbPath, safe=':@/')
	# 分解
	url = urllib.parse.urlparse(url, scheme='smb', allow_fragments=False)
	qs = urllib.parse.parse_qs(smbPath)
	spPath = url.path.split('/')
	config['host'] = url.hostname
	config['port'] = url.port
	config['service_name'] = spPath[1]
	# オプション部分を除外するためにエスケープしていた文字列を戻す
	unquoteUrl = urllib.parse.unquote('/'.join(spPath[2:]))
	config['path'] = parse1.sub('', unquoteUrl)
	# エスケープしていた文字を戻す
	config['user'] = urllib.parse.unquote(url.username) if url.username is not None else ''
	config['pass'] = urllib.parse.unquote(url.password) if url.password is not None else ''

	try:
		# パラメータ
		config['timeout'] = 10
		if 'timeout' in qs and len(qs['timeout']) == 1:
			config['timeout'] = int(qs['timeout'][0])

		config['domain'] = 'WORKGROUP'
		if 'domain' in qs and len(qs['domain']) == 1:
			config['domain'] = qs['domain'][0]

		config['pattern'] = None
		if 'pattern' in qs and len(qs['pattern']) == 1:
			config['pattern'] = qs['pattern'][0]

		config['my_name'] = platform.uname().node
		if 'my_name' in qs and len(qs['my_name']) == 1:
			config['my_name'] = qs['my_name'][0]

		config['remote_name'] = 'remote_name'
		if 'remote_name' in qs and len(qs['remote_name']) == 1:
			config['remote_name'] = qs['remote_name'][0]

		config['use_ntlm_v2'] = False
		if 'use_ntlm_v2' in qs and len(qs['use_ntlm_v2']) == 1:
			config['use_ntlm_v2'] = bool(qs['use_ntlm_v2'][0])

		config['sign_options'] = False
		if 'sign_options' in qs and len(qs['sign_options']) == 1:
			config['sign_options'] = int(qs['sign_options'][0])

		config['is_direct_tcp'] = False
		if 'is_direct_tcp' in qs and len(qs['is_direct_tcp']) == 1:
			config['is_direct_tcp'] = bool(qs['is_direct_tcp'][0])

	except Exception as err:
		logger.debug(err)
		raise

	return config


# samba（リモート）から取得
def getSmbR2L(sidMorg, *, smbPath, saveDir, fileDelFlag=True):
	smbConf = analysisPath(smbPath)
	if smbConf is None or len(smbConf) < 1:
		return

	# connection open
	conn = SMBConnection(
		# user
		username=smbConf['user'],
		# pass
		password=smbConf['pass'],
		my_name=smbConf['my_name'],
		remote_name=smbConf['remote_name'],
		domain=smbConf['domain'],
		use_ntlm_v2=smbConf['use_ntlm_v2'],
		sign_options=smbConf['sign_options'],
		is_direct_tcp=smbConf['is_direct_tcp']
	)

	conn.connect(smbConf['host'], smbConf['port'], timeout=smbConf['timeout'])

	items = conn.listPath(service_name=smbConf['service_name'], path=smbConf['path'], pattern=smbConf['pattern'], timeout=smbConf['timeout'])
	#logger.debug([item.filename for item in items if item.isDirectory == False])

	for item in items:
		if item.isDirectory == True:
			continue
		if item.file_size < 1:
			continue
		saveItem = pathlib.Path(saveDir).joinpath(item.filename)
		remoteFile = smbConf['path'] + '/' + item.filename
		try:
			# ローカルに同一名ファイルが存在する、かつ、リモートの更新時間がローカルより古い場合、リモートファイルの削除を試みる
			if saveItem.is_file() == True and item.last_write_time > saveItem.stat().st_mtime:
				# リモートファイルの削除
				if fileDelFlag == True and item.isReadOnly == False:
					conn.deleteFiles(service_name=smbConf['service_name'], path_file_pattern=remoteFile, timeout=smbConf['timeout'])
		except Exception as err:
			logger.error(err)
			raise

		try:
			with open(saveItem, mode='w+b', newline=None) as fp:
				conn.retrieveFile(service_name=smbConf['service_name'], path=remoteFile, file_obj=fp, timeout=smbConf['timeout'])

			# リモートファイルの削除
			if fileDelFlag == True and item.isReadOnly == False:
				conn.deleteFiles(service_name=smbConf['service_name'], path_file_pattern=remoteFile, timeout=smbConf['timeout'])

		except Exception as err:
			logger.error(err)
			raise


	conn.close()

	return
