/**
 * ルーター応答コンテンツ定義
 *   ※ Bit.setRoutes() 呼び出しを使用する。
 *       引数のオブジェクトに応答用HTTPメソッド名で関数を定義することで自動ルーティングされる。
 *       未定義のHTTPメソッドに自動対応する場合は 'DEFAULT' で関数定義する。
 *
 *   オプションファイルダウンロード
 *
 */

//var os = require('os');
var path = require('path')
var fs = require('fs');
var to_json = Bit.nw.xmljson.to_json;


// ログ表示用のタイトル
var title = '[file download]';
var log_title = '';
//var ret_err_msg = 'Failed to create CSV file';


Bit.setRoutes({
	GET: function(req, res, next) {

		var p = req.Request.params() || {};
		var sid_morg = req.user.sid_morg.toString();
		var sid_section = '132008';		// 固定

		var sql_str = '', store = null, items = [];

		log_title = title + '[' + sid_morg + ']';

		// 機能ライセンス認証
		var license = p.license;		// 予約エクスポートのライセンスID
		if(!Bit.nw.util.License.prototype.isLicensed(req, res, next, license)){ return; } // エラーレスポンス済み
		p.mode = (p.mode || Bit.nw.code.OUT_SOURCE.EXPORT.MODE.INIT)-0;
		switch(p.mode){
		case Bit.nw.code.OUT_SOURCE.EXPORT.MODE.PROC: // データ処理モード
			//if (p.dl_item.length < 1) { res.Response.setup(Bit.errorCreator(100, '受付ステータスが選択されていません。')); return; }
			//if(global.gc) { global.gc(); }

			var bin = null;

			var rdata = [], fname = null, msg = '';

			//console.log("p.fileInfo.length:" + p.fileInfo.length);
			bin = path.join(__dirname, '../../../', p.fileInfo.path);
			fname = p.fileInfo.save_name;
			Bit.log(log_title + ' ' + fname + ':' + bin);

			//console.log('binary path: ' + bin);
			if (bin) {
				var raw = fs.createReadStream(bin);
				raw.on('data', function(chunk){
					//console.log('chunk: ' + chunk.length);
					rdata.push(chunk);
				});
				raw.on('close', function(){
					raw.destroy();
					/*for (var i=0; i<rdata.length;i++) {
						console.log('data length: ' + rdata[i].length);
					}*/
					res.Response.setup({ process: 'file download', file: Buffer.concat(rdata), type: 'application/octet-stream', name: fname, encoding:'UTF-8', isBinary: true, isOpen: false, isReturnURL: false });
				});
				raw.on('error', function(err){
					raw.destroy();
					msg = 'file get faild';
					Bit.log(log_title + ' error: ' + err.message);
					res.Response.setup(Bit.errorCreator(1011, msg)); return;
				});
			} else {
				msg = 'file path not found';
				Bit.log(log_title + ' error: ' + msg);
				res.Response.setup(Bit.errorCreator(1011, msg)); return;
			}

			break;

		default: // UI取得モード
			var DATA = {
				Bit: Bit,
				license: license,
				name: Bit.nw.util.License.prototype.name(license),
				title: Bit.nw.util.License.prototype.title(license),
				itemList: items
			};

			// m_outsourceのxmlが欲しい
			sql_str = 'SELECT xml_outsource FROM m_outsource WHERE sid_morg=' + sid_morg + ' AND sid_section = ' + sid_section + ';';
			store = new Bit.store.Mysql();
			store.query({
				sql: sql_str,
				success: function(err, rows, fields) {
					//console.log("rows.length: " + rows.length);
					// m_outsourceが取れなかった
					if (rows.length <= 0){
						Bit.log(log_title + ' m_outsource get faild');
						res.Response.setup(DATA,'options/outsource/download_option_file');
					} else {
						to_json(rows[0].xml_outsource, function (err, xml_json){
							var conf = Bit.nw.xmljson.normalizeJson(Bit.nw.xmljson.config.m_outsource.xml_outsource.json, xml_json);
							if (conf == null) { msg = 'error: m_outsource get failed'; return; }
							var dl = conf.outsource.downloads.download;
							if (dl.length != null) {	// 複数
								for(var i=0; i<dl.length; i++) {
									items.push({'num':i, 'title':dl[i].title, 'id':dl[i].id});
								}
							} else {	// 1個
								items.push({'num':i, 'title':dl.title, 'id':dl.id});
							}
							//console.log("items: " + items);
							res.Response.setup(DATA,'options/outsource/download_option_file');
							if (err) { msg = 'exception: ' + err.code + ', ' + err.message; return; }
						});
					}
				},
				exception: function(err){ res.Response.setup(DATA,'options/outsource/download_option_file'); }
			});
		}	// end switch-case

	}
}, arguments);


