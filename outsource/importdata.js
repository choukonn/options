/**
 * ルーター応答コンテンツ定義
 *   ※ Bit.setRoutes() 呼び出しを使用する。
 *       引数のオブジェクトに応答用HTTPメソッド名で関数を定義することで自動ルーティングされる。
 *       未定義のHTTPメソッドに自動対応する場合は 'DEFAULT' で関数定義する。
 */

/**
 * 検査結果インポート : 検査結果を取り込む（クライアント処理版）
 * ※ アップロードされたデータをクライアントに戻し、クライアントにてデータを生成する（簡易処理版）
 */
var fs = require('fs');
var async = require('async');
var jconv = require('jconv');
var csv = require('csv');
var encoding = require('encoding-japanese');
var to_json = Bit.nw.xmljson.to_json;
var to_xml= Bit.nw.xmljson.to_xml;
var examineeProc = require('./_examinee.js');
var apointProc = require('./_appoint.js');
var apointCheckinProc = require('./importAppoint.js');
var yplus = require('./importYplus.js');

var encText = function(detect){
	if(detect == 'UTF32'){ return 'UTF-32';}
	if(detect == 'UTF16'){ return 'UTF-16';}
	if(detect == 'UTF16BE'){ return 'UTF-16BE';}
	if(detect == 'UTF16LE'){ return 'UTF-16LE';}
	if(detect == 'BINARY'){ return detect;}
	if(detect == 'ASCII'){ return detect;}
	if(detect == 'JIS'){ return 'ISO-2022-JP';}
	if(detect == 'UTF8'){ return 'UTF-8';}
	if(detect == 'EUCJP'){ return 'EUC-JP';}
	if(detect == 'SJIS'){ return 'Shift_JIS';}
	if(detect == 'UNICODE'){ return detect;}
};

Bit.setRoutes({
	GET: function(req, res, next){
		//ログインユーザーのsid取得
//		var sid_morg = req.user.sid_morg;
//		var sid = req.user.sid;
		var p = req.Request.params() || {};
		// 機能ライセンス認証
		var license = p.license;
		if(!Bit.nw.util.License.prototype.isLicensed(req, res, next, license)){ return; } // エラーレスポンス済み

		DATA = {
			Bit: Bit,
			license: license,
			name: Bit.nw.util.License.prototype.name(license),
			title: Bit.nw.util.License.prototype.title(license)
		};
		res.Response.setup(
			DATA,
			'options/outsource/import'
		);

//		res.Response.setup({
//			"process": "結果送信成功",
//			"list": list,
//		});
//		var er = new Error();
//		er.message = "mysql error";
//		res.Response.setup(er);

	},
	POST: function(req, res, next){ // for uploadfile
//		var target_path = './public/uploads/outsource' + req.files.upfile.name; /* アップロードする場所 */
//    var tmp_path = req.files.upfile.path; /* 一時ファイルの場所 */
//
//    /* サーバに送る際にファイル名がバイトコードになるのでリネーム処理が必要 */
//    fs.rename(tmp_path, target_path, function(err) {
//        if (err){
//   throw err;
//  }

//		var esql = new _es(req,res);
		//esql.init();//esql class init

		var p = req.Request.params()||{};
		// 機能ライセンス認証
		var license = p.license;
		if(!Bit.nw.util.License.prototype.isLicensed(req, res, next, license)){ return; } // エラーレスポンス済み

		var sid_morg = req.user.sid_morg;
		var sid = p.sid;
		var outConfig = null;

		var store = new Bit.store.Mysql();
		store.query({
			sql: 'select xml_outsource from m_outsource where sid_morg=? and sid=?;',
			params: [sid_morg, sid],
			success: function(err, rows, fields) {
				//SQLベタガキ用
	//				var recs = rows, flds = fields;
				//ストアドプロシージャ用
				var recs = rows[0]/*, flds = rows[1]*/;
				if(recs){
					var xml_outsource = recs.xml_outsource;
					if(xml_outsource){
						to_json(xml_outsource, function (error, xml_json){
							outConfig = Bit.nw.xmljson.normalizeJson(Bit.nw.xmljson.config.m_outsource.xml_outsource.json, xml_json);
						});
					}
				}
				if(!outConfig){
					res.Response.setup(Bit.errorCreator(110, Biti18n('D01258', req.user.locale) + '[_'+ license +'_]'));
					return;
				}
				if(!outConfig.outsource.columns || !outConfig.outsource.columns.column){
					res.Response.setup(Bit.errorCreator(111, Biti18n('D01259', req.user.locale) + '[_'+ license +'_]'));
					return;
				}
				Bit.defer(function(){
					importFiles(req, res, next, outConfig);
				});
			},
			exception: function(err){
				res.Response.setup(Bit.errorCreator(112, Biti18n('D01260', req.user.locale) + '[_'+ license +'_]'));
			}
		});

	}
}, arguments);


var importFiles = function(req, res, next, xml_outsource){
	var prm = req.Request.params()||{};
	var condition = xml_outsource.outsource.condition;
	if(prm.encode){ condition.encoding = prm.encode; }
	if(!condition.start_rowno){ condition.start_rowno = 1; }
	var files = prm.files || [];
	files = Bit.isArray(files) ? files : [files];
	var ret = { files: [], config: xml_outsource };
	var p = { req: req, res: res, next: next, config: xml_outsource, ret: ret };

	async.mapSeries(files, function(file, cb){
		p.file = file;
		procFile(p, function(err, result){
			if(err){
				cb(err);
				return;
			}
			cb(null, Biti18n('D01774', req.user.locale));
		});
	}, function complete(err, results){
		if(err){
			res.Response.setup({ process: Biti18n('D01276', req.user.locale), files: ret.files, config: ret.config, err: err});
			return;
		}
		res.Response.setup({ process: Biti18n('D01774', req.user.locale), files: ret.files, config: ret.config });
	});
};

var readFile = function(p, next){
	// read file
	var req = p.req, config = p.config, ret = p.ret, file = p.file;
	var prm = req.Request.params()||{};
	var force = prm.force;
	var condition = config.outsource.condition;
	ret.files.push({ name: file.name });
	var f = null;
	fs.readFile(file.path, function(err, raw){
		for(var i=0,li=ret.files.length,rf;i<li;++i){
			rf = ret.files[i];
			if(rf.name == file.name){ f = rf; break; }
		}
		p.f = f;
		try{
			if(err){
				req.Request.log(err);
				f.err = Bit.errorCreator(102, Biti18n('D01957', req.user.locale) + '[_rf_]');
				next(null, p);
				return;
			}

	//		fs.unlink(file.path, function(err_){
	//			if(err_){
	//				req.Request.log('unlink file ERR: '+ err_);
	//			}else{
	//				Bit.log('unlink file: '+ file.path);
	//			}
	//		});
			var det = encoding.detect(raw);
			if(det != 'ASCII'){
				if((condition.encoding == 'UTF8' && det != 'UTF8') || (condition.encoding == 'Shift_JIS' && det != 'SJIS')){
					f.encoding = encText(det);
					if(!force){
						req.Request.log('ファイルの文字コードが一致しません。name: '+ f.name +' encoding: '+ condition.encoding +' detect: '+ det);
						f.err = Bit.errorCreator(103, Biti18n('D01957', req.user.locale) + '[_en_]');
						next(null, p);
						return;
					}
				}
			}
			var d = raw;
			if(condition.encoding == 'Shift_JIS'){ d = jconv.decode(jconv.convert(raw, 'Shift_JIS', 'UTF8'), 'UTF8'); }
			if(condition.encoding == 'UTF8'){ d = jconv.decode(raw, 'UTF8'); }

//					Bit.log('name: '+ f.name +' code page: '+ condition.encoding +' detect: '+ det +' data: '+ d);
			Bit.log('name: '+ f.name +' code page: '+ condition.encoding +' detect: '+ det);
			p.raw = d;
			next(null, p);
		}catch(_e1_){
			req.Request.log(_e1_);
			f.err = Bit.errorCreator(101, Biti18n('D01957', req.user.locale) + '[_e1_]');
			next(null, p);
		}
	});
};
var parseData = function(p, next){
	// parse Data
	var req = p.req, config = p.config, file = p.file, d = p.raw, f = p.f;
	if(f.err){ next(null, p); return; }
	var condition = config.outsource.condition;
	var term = (condition.terminated == 'CR' ? '\r' : (condition.terminated == 'LF' ? '\n' : '\r\n'));
	var rows = d.split(term);
	if(rows[rows.length-1].length === 0){
		rows.pop(); // 最終空行排除
	}
	if(rows.length < condition.start_rowno){
		req.Request.log('ERROR import CSV: データ行数が足りません。rows: '+ rows.length +' start_rowno: '+ condition.start_rowno);
		f.err = Bit.errorCreator(202, Biti18n('D00540', req.user.locale) + '[' + Biti18n('D06493', req.user.locale, condition.start_rowno) + ']');
		next(null, p);
		return;
	}
	for(var i=1;i<condition.start_rowno;++i){
		rows.shift();
	}
	d = rows.join(term);

	switch(condition.format){
	case 'CSV':
		csv.parse(d, {/*comment: '#'*//*, relax: true*/ }, function(err_p, data){
			try{
				if(err_p){
					req.Request.log(err_p);
					f.err = Bit.errorCreator(201, Biti18n('D00540', req.user.locale) + '[_ps_]');
					next(null, p);
					return;
				}
				console.log('parseData');
				console.log(data);

				f.rows = data;
				req.Request.log('File uploaded from: '+ file.name +' to: ' + file.path + ' - ' + file.size + ' bytes ['+ f.rows.length +' rows]');
				next(null, p);
			}catch(_e2_){
				req.Request.log(_e2_);
				f.err = Bit.errorCreator(203, Biti18n('D00540', req.user.locale) + '[_e2_]');
				next(null, p);
				return;
			}
		});
		break;
	case 'JSON':
		req.Request.log('File uploaded from: '+ file.name +' to: ' + file.path + ' - ' + file.size + ' bytes ');
		next(null, p);
		break;
	case 'TEXT':
		f.err = Bit.errorCreator(210, Biti18n('D01554', req.user.locale) + '[_fm_]');
		next(f.err, p);
		break;
	case 'FIXED':
		f.err = Bit.errorCreator(210, Biti18n('D01554', req.user.locale) + '[_fm_]');
		next(f.err, p);
		break;
	}
};
var updateDB = function(p, next){
	var req = p.req, res = p.res, config = p.config, f = p.f;
	if(f.err){ next(null, p); return; }
	var condition = config.outsource.condition;
	p.serialize = new Bit.nw.serialize.Serialize();
	// var mr = null, exec;
	f.map = [];
	f.result = []; // 結果バッファ（行単位）
	p.rowIndex = -1;
	console.log('updateDB condition.sid_section');
	console.log(condition.sid_section);
	p.exec = getExec(condition.sid_section);
	p.nextProc = function(p_, next_, err_){
		var error = err_;
		if(p_.rowIndex > -1){ // 行処理後の対処
			f.result.push(error ? error : 0); // 0: 正常終了
			error = null;
		}
		++p_.rowIndex;
		if(p_.rowIndex == f.rows.length){ // 最終行後の対処
			next(null, p_);
			return;
		}
		/* serializeが1.5.0からコケるようになっているので一旦コメントアウト
		try{
			mr = p_.serialize.serialize(f.rows[p_.rowIndex], config.outsource.columns.column); // エラー時はthrow
		}catch(err__){
			error = err__;
			Bit.log(error);
			mr = { err: error };
		}
		f.map.push(mr);
		*/
		f.map.push(f.rows[p_.rowIndex]);

		if(error){ // マップエラー時は個別処理パス
			Bit.defer(function(){ p_.nextProc(p_, next_, error); });
		}else{
			try{
				p_.exec(p_, next_);
			}catch(err__2){
				error = Bit.errorCreator(3005, Biti18n('D06588', req.user.locale) + '[_ex_]');
				Bit.log(error);
				Bit.defer(function(){ p_.nextProc(p_, next_, error); });
			}
		}
	};
	p.nextProc(p, next); // 行処理開始
};
var procFile = async.compose(updateDB, parseData, readFile);

var getExec = function(sid_section){
	switch(sid_section){
	case Bit.nw.code.SEC_LIC_APP_IN_EXAMINEE: return examineeProc.execIn;
	case Bit.nw.code.SEC_LIC_APP_IN_APPOINT: return appoint.execIn;
	case Bit.nw.code.SEC_LIC_APP_IN_APPOINT_CHECKIN: return apointCheckinProc.execIn;
	case Bit.nw.code.SEC_LIC_APP_IN_QUESTIONAIR: return apointCheckinProc.execIn;
	case Bit.nw.code.SEC_LIC_APP_MLG_YPLUS: return yplus.execIn;
	case Bit.nw.code.SEC_LIC_APP_IN_ORG:
	case Bit.nw.code.SEC_LIC_APP_IN_CONTRACT:
	case Bit.nw.code.SEC_LIC_APP_IN_RESULT:
	default: return function(){};
	}
};
//var map = function(req, res, next, config, row){
//	var ret = {};
//	var cols = config.import.columns.column;
//	if(row.length < cols.length){ throw Bit.errorCreator(310, '列データが不足しています。'); }
//	for(var i=0,li=cols.length,col,mapping;i<li;++i){
//		col = cols[i];
//		try{
//			mapping = mappingProc(col.key);
//			ret[col.key] = mapping(col, row[i]);
//		}catch(err_){
//			Bit.log(err_);
//			throw Bit.errorCreator(311, '変換ができません。['+ col.key +' : '+ row[i] +']');
//		}
//	}
//	return ret;
//};
