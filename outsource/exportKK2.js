/**
 * 協会けんぽCSV出力（生活習慣病予防健診健診結果データ作成ツール用）
 */
var child_process = require("child_process");
var path = require('path')
var os = require('os');
var csv = require('csv');

Bit.setRoutes({
GET: function(req, res, next){
	Bit.log('協会けんぽCSV出力処理 GET start');
	var p = req.Request.params() || {};
	// ユーザー情報を追加
	p.user = req.user;
	// 機能ライセンス認証
	var license = p.license;
	if(!Bit.nw.util.License.prototype.isLicensed(req, res, next, license)){ return; } // エラーレスポンス済み
	var logCode = {};

	p.mode = (p.mode || Bit.nw.code.OUT_SOURCE.EXPORT.MODE.INIT)-0;
	switch(p.mode){
	case Bit.nw.code.OUT_SOURCE.EXPORT.MODE.PROC: // データ処理モード
		Bit.log('協会けんぽCSV出力処理開始。。。');
		// pythonを使用するのかチェック
		var outsource = p.extraction.outsource;
		var progType = outsource.f_programType;

		if ( progType == null || progType == '0') {
		var child_js, zipData, csvData, err, ext;
		ext = p.extraction;

		// 年度によって呼び出し先を切り替え
		if(ext.from >= '2018-04-01'){
			child_js = "childKK2-2018.js"
		}else{
			child_js = "childKK2.js"
		}

		// PATH結合
		child_js = path.join(__dirname, '/', child_js);

		// argsはJSON形式で渡す
		// optionsには標準出力、エラーを有効にするためのsilentオプションを設定
		var child = child_process.fork(child_js, [JSON.stringify(p)], { silent: true });
		//var child = child_process.fork(child_js, [JSON.stringify(p)], { silent: true, execArgv: ["--nolazy", "--debug-brk=5859"] });		// デバッグ（attach）専用
		logCode[child.pid] = '協会けんぽ [' + p.user.sid_morg + ':' + p.user.sid.toString() + '] ';
		child.stdout.on('data', function(data) {
			Bit.log('stdout: ' + logCode[child.pid] + data.toString('UTF-8').trim());
		});
		child.stderr.on('data', function(data) {
			Bit.log('stderr: ' + logCode[child.pid] + data.toString('UTF-8').trim());
		});
		child.on("message", function (msg) {
			if(msg.zip) {
				// zipファイルのバイトデータの配列をコピー
				zipData = msg.zip.slice();
			} else if(msg.csv) {
				// csvファイルのバイトデータの配列をコピー
				csvData = msg.csv.slice();
			} else if(msg.err) {
				err = msg.err;
			} else {
				Bit.log(msg);
			}
		});
		child.on('close', function(code) {
			Bit.log('closing code: ' + code);
		});
		child.on('exit', function(code) {
			Bit.log('exit code: ' + code);
			if(zipData) {
				res.send({file: zipData, 'content-type': 'application/zip'});
			} else if(csvData) {
				res.send({file: csvData, 'content-type': 'text/csv', err: err});
			} else if(err) {
				res.Response.setup(Bit.errorCreator(err.code, err.message));
			} else {
				// それ以外の場合もエラー
				res.Response.setup(Bit.errorCreator(999, 'CSVの出力に失敗しました。'));
			}
		});
		}
		// python start
		else if (progType == '3') {
			var fs = require('fs');

			var title = '[CSV]';
			var log_title = '';
			var ret_err_msg = 'Failed to create CSV file';

			try {
				// ログ表示用のタイトル

				var abst_conditions = {'from': p.extraction.from, 'to': p.extraction.to, 'sid_criterion': outsource.sid_criterion.toString()};
				//var sort_conditions = null;
				var s_print = '200302' //p.xml_syntax.s_print.toString();	// TODO: 固定（仮）
				var sid_morg = req.user.sid_morg.toString();
				var m_user = req.user.sid.toString();
				var form_name = outsource.name.toString();
				var sid_section = outsource.sid_section.toString();		// 固定(134001)
				var abst_from = abst_conditions['from'];
				var abst_to = abst_conditions['to'];
				//var charCode = p.charcode == 'Shift_JIS' ? 'Shift_JIS' : 'UTF-8';
				var charCode = 'shift_jis';		// 協会けんぽツールのCSV取り込みは、Shift_JIS専用
				//var locale = p.locale ? p.locale : 'en-US';			// ロケール。デフォは英語

				var ret = { status: null, data: [] , config: {'sid_morg':sid_morg, 's_print':'', 'form_name':form_name, 'sid_section':sid_section }, xls: [] };

				log_title = title + '[' + sid_morg + ':' + m_user + ':' + form_name + ']';

			} catch(err) {	// パラメータ取得に失敗
				Bit.log(log_title + ' exception:' + err.code + ', ' + err.message);
				res.Response.setup(Bit.errorCreator(err.code, ret_err_msg));
			}

			try {
				var sql_url = 'mysql://' + Bit.config.db.mysql.DBUSER + ':' + Bit.config.db.mysql.DBPASSWD + '@' + Bit.config.db.mysql.DBHOST + '/' + Bit.config.db.mysql.DATABASE;
				var file_path = null, bin = '', cmd = '', args = [], argv = {}, b64enc = null;
				var search_word = 'kenshin_KK_csv_file:';	// pythonの標準出力から検索するためのキーワード
				//var debug_flag = useDebuger() ? '1' : '0';


				// 抽出条件
				var abst_condition = {};
				//var cnt = 0;
				/*for (cnt=0;cnt<Object.keys(abst_conditions).length;cnt++){
					var a_c = abst_conditions[cnt].s_condition;
					if (a_c == 201001) { abst_from = abst_conditions[cnt].from.replace(/-/g,'/'); abst_to = abst_conditions[cnt].to.replace(/-/g,'/'); }	// 日付は抽出条件から取得
					var val = abst_conditions[cnt].value;
					abst_condition[a_c] = val;
				}*/

				if (!abst_condition['201011']) { abst_condition['201011'] = '3' }		// ステータスは３固定（確定済み）
				if (!abst_condition['201007']) { abst_condition['201007'] = p.extraction.examlist ? p.extraction.examlist.join() : ''}		// 出力対象者の指定
				if (!abst_condition['201003']) { abst_condition['201003'] = outsource.sid_me.toString() }		// 入力(協会けんぽ)コース
				if (!abst_condition['201005']) {
					if (p.extraction.orgsid != null){
						abst_condition['201005'] = p.extraction.orgsid.toString();
					}
				}		// 所属団体
				if (!abst_from || !abst_to) { res.Response.setup(Bit.errorCreator(1001, 'Failed to get date, Reload the browser')); return }	// 日付がないときはエラー
				if (abst_condition['201003'].length < 1) {
					// ファイル出力対象を絞り込むために、m_outsourceに協会けんぽコースのt_appoint_meで表示されるsid_meを登録する必要がある
					// 例：保険団体に協会けんぽが紐づけされているが、人間ドックコースを受診している場合は除外等
					// チェック自体はpython側で行うため、jsはsid_meを渡すだけ
					var errMsg = 'Failed to get course info, Set sid_me to m_outsource';
					//Bit.log(errMsg);
					res.Response.setup(Bit.errorCreator(1001, errMsg));
					return;
				}

				// ソート条件
				var sort_condition = {};
				/*for (cnt=0;cnt<Object.keys(sort_conditions).length;cnt++){
					var s_cond = {};
					var s_c = sort_conditions[cnt].s_condition;
					s_cond['key'] = sort_conditions[cnt].key;
					s_cond['direction'] = sort_conditions[cnt].direction;
					s_cond['priority'] = sort_conditions[cnt].priority;
					sort_condition[s_c] = s_cond;
				}*/

				//console.log('abst:' + JSON.stringify(abst_condition));
				//console.log('sort:' + JSON.stringify(sort_condition));

				// pythonへの引数は全て文字列で渡す
				argv = {
					'out_file_prefix'		: 'DD_form_' + sid_morg + '_' + s_print + '_',		// 出力ファイル名の部品
					'out_file_suffix'		: '.tmp',			// 出力ファイル名の部品
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
					'm_user'				: m_user,
					'outsouceSid'			: outsource.sid.toString()
				};

				var regexp = new RegExp(search_word + argv['out_file_prefix'] + '.+' + argv['out_file_suffix']);

				var script_name = 'childKyoukaiKenpo.py';
				//Bit.log('dir-path: ' + __dirname);
				bin = path.join(__dirname, '/', script_name);
				//Bit.log('script-path: ' + bin);
				if (os.platform() == 'linux') {
					cmd = 'python3'		// linux
				} else {
					cmd = 'python'		// windows
				}

				b64enc = Buffer.from(JSON.stringify(argv)).toString('base64');
				//console.log(b64enc);

				args.push('-J ' + b64enc);		// -b は python側でチェックするためのオプション

				var start_log = log_title + ' Start:' + script_name
				Bit.log(start_log);

				var spawn = require("child_process").spawn;
				// 起動
				var py = spawn(cmd, [bin, args]);

				py.stdin.on('data',function(chunk){
					Bit.log(log_title + ' stdin: ' + chunk.toString('UTF-8').replace(/[\r\n]/g,''));
				});

				py.stdout.setEncoding('utf8');
				py.stdout.on('data',function(chunk){	// 標準出力は、pythonとjsでやり取りするものだけを流し込む
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
					Bit.log(log_title + ' msg: ' + chunk.toString('UTF-8').trim()/*.replace(/[\r\n]/g,'')*/);
				});

				py.stderr.setEncoding('utf8');
				py.stderr.on('data',function(chunk){	// pythonからのデバッグログはここに出力する。js同士でforkならmessageが使えた。
					Bit.log(log_title + chunk.toString('UTF-8').trim()/*.replace(/[\r\n]/g,'')*/);
				});

				py.on('close', function(code) {
					Bit.log(log_title + ' close: ' + code);
					// 仮
					if (code == 0 && file_path != null) {		// ファイル名の取得に成功している
						Bit.log(log_title + ' start reading file.');
						var readline = require('readline'),
							instream = fs.createReadStream(file_path),
							outstream = new (require('stream'))(),
							rl = readline.createInterface(instream, outstream);		// ファイル読み込みするために、ストリームを作成

						rl.on('line', function (line) {
							// Excelで読み込むことを前提に、\r\n（0x0d0a）固定で出力を行う
							var br = '\r\n';
							ret.data.push(line + br);
						});

						rl.on('close', function () {
							Bit.log(log_title + ' done reading file.');
							//fs.unlink(file_path);	// ここでファイルを削除
							csv.stringify(ret.data, function(err, output) {
								var filename = '協会けんぽ用CSV_'+ (Now().format('yyyymm')) +'_'+ Now().format('yyyymmddhhnnss');
								if (outsource.subCode == '20030204' ){
									filename = 'SIKAKU_' + outsource.morg_code
								}
								res.Response.setup({ process: 'output csv file complete', file: output, filename:filename, charcode: charCode });
							});
						});

					} else if (code == 0 && file_path == null) {
						// 出力対象無し
						//Bit.log(log_title + ' done');
						res.Response.setup(Bit.errorCreator(code, 'Data not found, Change the extraction condition'));
					} else if (code != 0) {
						res.Response.setup(Bit.errorCreator(code, 'warning'));
					} else if (code >= 100) {
						res.Response.setup(Bit.errorCreator(code, ret_err_msg));
					}
				});

				py.on('exit', function(code) {
					Bit.log(log_title + ' exit: ' + code);
					//res.end();
				});

				py.on('error', function(err) {
					Bit.log(log_title + ' error: ' + err);
					//res.end();
				});

			} catch (err) {
				Bit.log(log_title + ' exception:' + err.code + ', ' + err.message);
				res.Response.setup(Bit.errorCreator(err.code, ret_err_msg));
				//res.end();
			}
		} // python end
		break;

	default: // UI取得モード
		req.Request.log("UI取得モード");
		var DATA = {
			Bit: Bit,
			license: license,
			name: Bit.nw.util.License.prototype.name(license),
			title: Bit.nw.util.License.prototype.title(license)
		};
		res.Response.setup(
			DATA,
			'options/outsource/export_kk2'
		);
	}
}

}, arguments);
