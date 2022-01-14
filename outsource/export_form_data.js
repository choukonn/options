/**
 * ルーター応答コンテンツ定義
 *   ※ Bit.setRoutes() 呼び出しを使用する。
 *       引数のオブジェクトに応答用HTTPメソッド名で関数を定義することで自動ルーティングされる。
 *       未定義のHTTPメソッドに自動対応する場合は 'DEFAULT' で関数定義する。
 *
 *   Excel帳票用のCSVを出力するpythonスクリプトを実行する
 *
 */

var os = require('os');
var path = require('path')
var fs = require('fs');
var csv = require('csv');


/* エラー番号用メモ書き
 * javascript側のエラー表示は4桁にする
 * Python側のエラー表示は、3桁以下にする
 *
*/

/* 使用しない
var useDebuger = function() {
	var keyword = '.+debug.+';
	var argv = JSON.stringify(process.execArgv);
	var dbg_flag = argv.search(keyword) !== -1 ? true : false;

	return dbg_flag
};
*/


// ログ表示用のタイトル
var title = '[CSV output]';
var log_title = '';
var ret_err_msg = 'Failed to create CSV file';


Bit.setRoutes({
	GET: function(req, res, next) {

	try {
		var p = req.Request.params() || {};
		var abst_conditions = p.xml_syntax.abst_conditions ? p.xml_syntax.abst_conditions.abst_condition : [];
		var sort_conditions = p.xml_syntax.sort_conditions ? p.xml_syntax.sort_conditions.sort_condition : [];
		var s_print = p.xml_syntax.s_print.toString();
		var sid_morg = req.user.sid_morg.toString();
		var m_user = req.user.sid.toString();
		var form_name = p.name;
		var sid_section = '132005';		// 固定
		var abst_from, abst_to;
		//var charCode = p.charcode == 'Shift_JIS' ? 'Shift_JIS' : 'UTF-8';
		var charCode = 'UTF-8';		// 旧字体がSJISでは出力できないので、一律UTF8で出力を行う
		var locale = p.locale ? p.locale : 'en-US';			// ロケール。デフォは英語

		var ret = { status: null, data: [] , config: {'sid_morg':sid_morg, 's_print':s_print, 'form_name':form_name, 'sid_section':sid_section }, xls: [] };

		log_title = title + '[' + sid_morg + ':' + m_user + ':' + form_name + ']';
		var pyLog = {};

	} catch(err) {	// パラメータ取得に失敗
		Bit.log(log_title + ' exception:' + err.code + ', ' + err.message);
		res.Response.setup(Bit.errorCreator(err.code, ret_err_msg));
	}

	try {
		var sql_url = 'mysql://' + Bit.config.db.mysql.DBUSER + ':' + Bit.config.db.mysql.DBPASSWD + '@' + Bit.config.db.mysql.DBHOST + '/' + Bit.config.db.mysql.DATABASE;
		var file_path = null, bin = '', cmd = '', args = [], argv = {}, b64enc = null;
		var search_word = 'kenshin_DD_csv_file:';	// pythonの標準出力から検索するためのキーワード
		//var debug_flag = useDebuger() ? '1' : '0';

		// 抽出条件
		var abst_condition = {};
		var cnt = 0;
		for (cnt=0;cnt<abst_conditions.length;cnt++){
			var a_c = abst_conditions[cnt].s_condition;
			if (a_c == 201001) { abst_from = abst_conditions[cnt].from.replace(/-/g,'/'); abst_to = abst_conditions[cnt].to.replace(/-/g,'/'); }	// 日付は抽出条件から取得
			var val = abst_conditions[cnt].value;
			abst_condition[a_c] = val;
		}

		if (!abst_condition['201011']) { abst_condition['201011'] = '0,1,2,3' }		// 受付ステータス未指定時はALL扱い
		if (!abst_from || !abst_to) { res.Response.setup(Bit.errorCreator(1001, 'Failed to get date, Reload the browser')); return }	// 日付がないときはエラー

		// ソート条件
		var sort_condition = {};
		for (cnt=0;cnt<sort_conditions.length;cnt++){
			var s_cond = {};
			var s_c = sort_conditions[cnt].s_condition;
			s_cond['key'] = sort_conditions[cnt].key;
			s_cond['direction'] = sort_conditions[cnt].direction;
			s_cond['priority'] = sort_conditions[cnt].priority;
			sort_condition[s_c] = s_cond;
		}

		//console.log('abst:' + JSON.stringify(abst_condition));
		//console.log('sort:' + JSON.stringify(sort_condition));

		// pythonへの引数は全て文字列で渡す
		argv = {
			//'http_port': Bit.config.listen.port,
			'out_file_prefix'		: 'DD_form_' + sid_morg + '_' + s_print + '_',		// 出力ファイル名の部品
			'out_file_suffix'		: '.tmp',			// 出力ファイル名の部品
			'translation_lang'		: locale,			// ろけーる(デフォルト英語)
			'mysql'					: sql_url,
			'sid_section'			: sid_section,		// 固定:132005
			's_print'				: s_print,			// m_syntax(xml_syntax)で指定されている帳票の種類
			'sid_morg'				: sid_morg,
			'date_start'			: abst_from,
			'date_end'				: abst_to,
			'form_name'				: form_name,		// CSVファイル内に出力される帳票名
			'output_search_word'	: search_word,		// keyword:csvファイル名　という形でマッチするかのチェックに使う
			'sort_condition'		: sort_condition,
			'abst_condition'		: abst_condition,
			'm_user'				: m_user
			//,'py_debug'				: debug_flag		// デバッグ用
		};

		var regexp = new RegExp(search_word + argv['out_file_prefix'] + '.+' + argv['out_file_suffix']);

		//var script_name = 'test.py';
		var script_name = 'export_form_data.py';
		bin = path.join(__dirname, '/', script_name);
		if (os.platform() == 'linux') {
			cmd = 'python3'		// linux
		} else {
			cmd = 'python'		// windows
		}

		b64enc = new Buffer(JSON.stringify(argv)).toString('base64');
		//console.log(b64enc);

		args.push('-J ' + b64enc);		// -b は python側でチェックするためのオプション

		var start_log = log_title + ' Start:' + script_name
		/*if (debug_flag == '1'){
			start_log += ' : ' + argv
		}*/
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
			//var tmp_word = chunk.toString('UTF-8').replace(/[\r\n]/g,'').match(search_word);
			var tmp_word = chunk.toString('UTF-8').replace(/[\r\n]/g,'').match(regexp);		// 出力されたファイル名を抽出
			if (tmp_word != null) {
				var tmp_keyword = tmp_word.input.toString();
				if (tmp_keyword != null) {
					var keyword = tmp_keyword.replace(search_word,'');	// 「key:CSVファイル名」形式なので、key部を削除してファイル名と思わしき個所を残す
					if (keyword != null){
						file_path = path.join(os.tmpdir(), keyword)		// systemのTMPフォルダを使用。ゴミ掃除はOSのポリシーに従う
						fs.statSync(file_path);	// 存在チェック
					}
				}
			}
			Bit.log(pyLog[py.pid]['log_title'] + ' msg: ' + chunk.toString('UTF-8').trim()/*.replace(/[\r\n]/g,'')*/);
		});

		py.stderr.setEncoding('utf8');
		py.stderr.on('data',function(chunk){	// pythonからのデバッグログはここに出力する。js同士でforkならmessageが使えた。
			Bit.log(pyLog[py.pid]['log_title'] + chunk.toString('UTF-8').trim()/*.replace(/[\r\n]/g,'')*/);
		});

		py.on('close', function(code) {
			Bit.log(pyLog[py.pid]['log_title'] + ' close: ' + code);
			// 仮
			if (code == 0 && file_path != null) {		// ファイル名の取得に成功している
				Bit.log(pyLog[py.pid]['log_title'] + ' start reading file.');
				var readline = require('readline'),
					instream = fs.createReadStream(file_path),
					outstream = new (require('stream'))(),
					rl = readline.createInterface(instream, outstream);		// ファイル読み込みするために、ストリームを作成

				rl.on('line', function (line) {
					// Excelで読み込むことを前提に、\r\n（0x0d0a）固定で出力を行う
					var br = '\r\n';
					//if(p.charcode != 'UTF-8'){ line = jconv.convert(line, 'UTF-8', p.charcode); }	// 最終的にフレームワーク側で変換しているため、ここでは何もしない
					ret.data.push(line + br);
				});

				rl.on('close', function () {
					Bit.log(pyLog[py.pid]['log_title'] + ' done reading file.');
					fs.unlink(file_path);	// ここでファイルを削除
					//for (var i=0;i<=ret.data.length;i++){ console.log(ret.data[i]); };	// debug
					csv.stringify(ret.data, function(err, output) {
						//if(p.charcode != 'UTF-8'){ output = jconv.encode(output, p.charcode); }	// 理由は上記と同じ
						res.Response.setup({ process: 'output csv file complete', file: output, charcode: charCode });
					});
				});

			} else if (code == 0 && file_path == null) {
				// 出力対象無し
				//Bit.log(pyLog[py.pid]['log_title'] + ' done');
				res.Response.setup(Bit.errorCreator(code, 'Data not found, Change the extraction condition'));
			} else if (code != 0) {
				res.Response.setup(Bit.errorCreator(code, 'warning'));
			} else if (code >= 100) {
				res.Response.setup(Bit.errorCreator(code, ret_err_msg));
			}
		});

		py.on('exit', function(code) {
			Bit.log(pyLog[py.pid]['log_title'] + ' exit: ' + code);
			//res.end();
		});

		py.on('error', function(err) {
			Bit.log(pyLog[py.pid]['log_title'] + ' error: ' + err);
			//res.end();
		});

	} catch (err) {
		Bit.log(log_title + ' exception:' + err.code + ', ' + err.message);
		res.Response.setup(Bit.errorCreator(err.code, ret_err_msg));
		//res.end();
	}

	}
}, arguments);


