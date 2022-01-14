/**
 * ルーター応答コンテンツ定義
 *   ※ Bit.setRoutes() 呼び出しを使用する。
 *       引数のオブジェクトに応答用HTTPメソッド名で関数を定義することで自動ルーティングされる。
 *       未定義のHTTPメソッドに自動対応する場合は 'DEFAULT' で関数定義する。
 *
 *   予約・受付取込用のファイルを取込するpythonスクリプトを実行する
 *
 */

var os = require('os');
var path = require('path');
var fs = require('fs');

/* エラー番号用メモ書き
 * javascript側のエラー表示は4桁にする
 * Python側のエラー表示は、3桁以下にする
 *
*/


// ログ表示用のタイトル
var title = '[appoint input]';
var log_title = '';
var ret_err_msg = 'Failed to load Import file';

// pythonの定義
// var SCRIPT_PATH = 'childImportAppoint.py';
var SCRIPT_PATH = 'ImportForAll.py';

Bit.setRoutes({
	POST: function(req, res, next){ // for uploadfile
		// p: {req, res, next, config, ret: { files: [] }, file, f, raw, rowIndex }
		var sid_morg;
		var file = req.files.files;
		var resultMsg = ''; // 実行結果メッセージ

		try {
			sid_morg = req.user.sid_morg.toString();
			var m_user = req.user.sid.toString();

			log_title = title + '[' + sid_morg + ':' + m_user + ']';
			var pyLog = {};

		} catch(err) {	// パラメータ取得に失敗
			Bit.log(log_title + ' exception:' + err.code + ', ' + err.message);
			res.Response.setup(Bit.errorCreator(err.code, ret_err_msg));
		}

		try {
			var bin = '', cmd = '', args = [], argv = {}, b64enc = null;

			// pythonへの引数は全て文字列で渡す
			argv = {
				'out_file_prefix'		: 'DD_form_' + sid_morg + '_',
				'out_file_suffix'		: '.tmp',
				's_print'				: '',
				'abst_condition'		: {},
				'sort_condition'		: {},
				'host'					: Bit.config.db.mysql.DBHOST,
				'port'					: 3306,
				'dbName'				: Bit.config.db.mysql.DATABASE,
				'user'					: Bit.config.db.mysql.DBUSER,
				'pass'					: Bit.config.db.mysql.DBPASSWD,
				'sid_morg'				: sid_morg,
				'timeout'				: 120,
				'file_path'				: file.path
			};

			var script_name = SCRIPT_PATH;
			bin = path.join(__dirname, '/', script_name);
			if (os.platform() == 'linux') {
				cmd = 'python3'		// linux
			} else {
				cmd = 'python'		// windows
			}

			b64enc = new Buffer.from(JSON.stringify(argv)).toString('base64');

			args.push('-J ' + b64enc);		// -b は python側でチェックするためのオプション

			var start_log = log_title + ' Start:' + script_name;
			Bit.log(start_log);

			var spawn = require("child_process").spawn;
			// 起動
			var py = spawn(cmd, [bin, args]);
			pyLog[py.pid] = {'log_title': log_title};			// TODO: びみょ。タイミング次第で書き換えられるため、出力されるログタイトルを過信してはいけない。

			py.stdin.on('data',function(chunk){
				Bit.log(pyLog[py.pid]['log_title'] + ' stdin: ' + chunk.toString('UTF-8').replace(/[\r\n]/g,''));
			});

			py.stdout.setEncoding('utf8');
			py.stdout.on('data',function(chunk){	// 標準出力は、pythonとjsでやり取りするものだけを流し込む
				resultMsg += chunk.toString('UTF-8').trim() + '\n';
			});

			py.stderr.setEncoding('utf8');
			py.stderr.on('data',function(chunk){	// pythonからのデバッグログはここに出力する。js同士でforkならmessageが使えた。
				Bit.log(log_title + chunk.toString('UTF-8').trim());
			});

			py.on('close', function(code) {
				Bit.log(pyLog[py.pid]['log_title'] + ' close: ' + code);
				if (code == 0) {
					res.Response.setup({ process: 'imput appoint file complete', message: resultMsg});
				} else if (code != 0) {
					res.Response.setup(Bit.errorCreator(code, 'warning'));
				} else if (code >= 100) {
					res.Response.setup(Bit.errorCreator(code, ret_err_msg));
				}
			});

			py.on('exit', function(code) {
				Bit.log(pyLog[py.pid]['log_title'] + ' exit: ' + code);
			});

			py.on('error', function(err) {
				Bit.log(pyLog[py.pid]['log_title'] + ' error: ' + err);
			});

		} catch (err) {
			Bit.log(log_title + ' exception:' + err.code + ', ' + err.message);
			res.Response.setup(Bit.errorCreator(err.code, ret_err_msg));
		}

	}
}, arguments);

