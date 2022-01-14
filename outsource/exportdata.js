
var async = require('async');
var jconv = require('jconv');
var csv = require('csv');
var encoding = require('encoding-japanese');
var to_json = Bit.nw.xmljson.to_json;
var to_xml= Bit.nw.xmljson.to_xml;
var examineeProc = require('./_examinee.js');
var apointProc = require('./_appoint.js');

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
//	var sid_morg = req.user.sid_morg;
//	var sid = req.user.sid;
	var p = req.Request.params() || {};
	// 機能ライセンス認証
	var license = p.license;
	if(!Bit.nw.util.License.prototype.isLicensed(req, res, next, license)){ return; } // エラーレスポンス済み
	
	p.mode = (p.mode || Bit.nw.code.OUT_SOURCE.EXPORT.MODE.INIT)-0;
	switch(p.mode){
	case Bit.nw.code.OUT_SOURCE.EXPORT.MODE.PROC: // データ処理モード
		proc(req, res, next);
		break;
	default: // UI取得モード
		DATA = {
			Bit: Bit,
			license: license,
			name: Bit.nw.util.License.prototype.name(license),
			title: Bit.nw.util.License.prototype.title(license)
		};
		res.Response.setup(
			DATA,
			'options/outsource/export'
		);
	}
}

}, arguments);

var proc = function(req, res, next){
	var user = req.user;
	var p = req.Request.params()||{};
	var sid_morg = user.sid_morg;
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
			switch(outConfig.outsource.condition.format){
			case 'CSV':
				break;
			case 'TEXT':
				return res.Response.setup(Bit.errorCreator(113, Biti18n('D01554', req.user.locale) + '[_fm_]'));
				break;
			case 'FIXED':
				return res.Response.setup(Bit.errorCreator(114, Biti18n('D01554', req.user.locale) + '[_fm_]'));
				break;
			default:
					return res.Response.setup(Bit.errorCreator(114, Biti18n('D01554', req.user.locale) + '[_fm_]'));
			}
			Bit.defer(function(){
				exportFiles(req, res, next, outConfig);
			});
		},
		exception: function(err){
			res.Response.setup(Bit.errorCreator(112, Biti18n('D01260', req.user.locale) + '[_'+ license +'_]'));
		}
	});
};

var exportFiles = function(req, res, next, xml_outsource){
	var prm = req.Request.params()||{};
	var condition = xml_outsource.outsource.condition;
	if(prm.encode){ condition.encoding = prm.encode; }
	if(!condition.start_rowno){ condition.start_rowno = 1; }
	var ret = { files: [], config: xml_outsource };
	
	processSet.p = { req: req, res: res, next: next, config: xml_outsource, ret: ret };
	Bit.util.Async.waterfall(processSet.procs, function(err){
		if(err){
			res.Response.setup({ process: Biti18n('D01276', req.user.locale), files: ret.files, config: ret.config, err: err});
			return;
		}
		res.Response.setup({ process: Biti18n('D01778', req.user.locale), files: ret.files, config: ret.config });
	});

};

var transformData = function(p, callback){
	var me = this;
	var req = p.req, res = p.res, config = p.config, ret = p.ret, files = ret.files, plugin = p.plugin;
	var condition = config.outsource.condition;
	Bit.util.Async.each(files, function(file, nextfile){
		p.serialize = new Bit.nw.serialize.Serialize({
			config: {
				condition: config.outsource.condition,
				columns: config.outsource.columns.column
			}
		});
		try{
			var mr = p.serialize.serialize(file.data, config.outsource.columns.column); // エラー時はthrow
			var r = Bit.clone(mr[Bit.nw.serialize.plugin.MExaminee.prototype.DB]);
			file.data =plugin.transformData(r);
			nextfile(null, file);
		}catch(err__){
			file.err = err__;
			Bit.log(err__);
			nextfile(null, file);
		}
	}, function(err){
		callback(err, p);
	});
};

var writeFile = function(p, callback){
	var me = this;
	var req = p.req, res = p.res, config = p.config, ret = p.ret, files = ret.files, plugin = p.plugin;
	var condition = config.outsource.condition;
	Bit.util.Async.each(files, function(file, nextfile){
		switch(condition.format){
		case 'CSV':
			var opts = { eof: true };
			if(condition.terminated == 'CRLF'){
				opts.rowDelimiter = 'windows';
			}else if(condition.terminated == 'CR'){
				opts.rowDelimiter = 'mac';
			}else if(condition.terminated == 'LF'){
				opts.rowDelimiter = 'unix';
			}
			if(condition.enclosed == 'DOUBLE_QUOTE'){
				opts.quote = '"';
				opts.quoted = true;
				opts.quotedEmpty = true;
			}else if(condition.enclosed == 'SINGLE_QUOTE'){
				opts.quote = "'";
				opts.quoted = true;
				opts.quotedEmpty = true;
			}
			csv.stringify([ file.data ],
				opts,
//				{ quote: "'", eof: true, quoted: true, quotedEmpty: true },
			function(err, src){
//				Bit.log(src);
				var det = encoding.detect(src);
//				if(det != 'ASCII'){ // 出力では必要なし
//					if((condition.encoding == 'UTF8' && det != 'UTF8') || (condition.encoding == 'Shift_JIS' && det != 'SJIS')){
//						file.encoding = me.encText(det);
//						req.Request.log('ファイルの文字コードが定義されているものと一致しません。name: '+ file.name +' encoding: '+ condition.encoding +' detect: '+ det);
//					}
//				}
				if(condition.encoding == 'Shift_JIS'){ src = jconv.encode(src, 'Shift_JIS'); }
				if(condition.encoding == 'UTF-8'){ src = jconv.encode(src, 'UTF8'); }
				
				var name = file.name || Now().format('yyyymmddhhnnss') +'.txt';
				Bit.log('name: '+ name +' code page: '+ condition.encoding +' detect: '+ det);
				
				var filename = me.conf('root') +'/'+ req.user.sid_morg +'/'+ condition.sid_external +'/'+ me.OUTPUT +'/'+ name;
				fs.writeFile(filename, src/*, { mode: 0o666 }*/, function(err_){
					Bit.log('output: '+ filename);
					if(err_){ Bit.log(err_); }
					nextfile(null, file);
				});
			});
			break;
		case 'XML':
			var src = file.data;
//		Bit.log(src);
			var det = encoding.detect(src);
//		if(det != 'ASCII'){ // 出力では必要なし
//			if((condition.encoding == 'UTF8' && det != 'UTF8') || (condition.encoding == 'Shift_JIS' && det != 'SJIS')){
//				file.encoding = me.encText(det);
//				req.Request.log('ファイルの文字コードが定義されているものと一致しません。name: '+ file.name +' encoding: '+ condition.encoding +' detect: '+ det);
//			}
//		}
			if(condition.encoding == 'Shift_JIS'){ src = jconv.encode(src, 'Shift_JIS'); }
			if(condition.encoding == 'UTF-8'){ src = jconv.encode(src, 'UTF8'); }
			
			var name = file.name || Now().format('yyyymmddhhnnss') +'.txt';
			Bit.log('name: '+ name +' code page: '+ condition.encoding +' detect: '+ det);
			
			var filename = me.conf('root') +'/'+ req.user.sid_morg +'/'+ condition.sid_external +'/'+ me.OUTPUT +'/'+ name;
			fs.writeFile(filename, src/*, { mode: 0o666 }*/, function(err_){
				Bit.log('output: '+ filename);
				if(err_){ Bit.log(err_); }
				nextfile(null, file);
			});
			break;
		default:
			file.err = Bit.errorCreator(210, Biti18n('D01554', req.user.locale) + '[.'+ condition.format +']');
			nextfile(null, file);
		}
	}, function(err){
		callback(err, p);
	});
};

var processSet = {
	p: {},
	procs: [
		function(next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var sid_morg = user.sid_morg;
			Bit.nw.Data.Store.onComplete = function(err){
				if(err){ Bit.log(err); }
				next(err);
			};
			Bit.nw.Data.Store.exec(sid_morg);
		},
		function(next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var eorg = Bit.nw.Data.Store.mEorg;
			eorg.data = { user: user };
			eorg.getData(function(store, data){
				next(null, data.rows);
			}, function(store, code, message){
				next(null, []);
			});
		},
		function(eorgs, next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			console.log('eorgs.length: '+ eorgs.length);
			Bit.util.Async.each(eorgs, function(eorg, next_){
				var st = Bit.nw.Data.Store.mEorgEg;
				st.data = { user: user, data: { sid_eorg: eorg.sid } };
				st.getData(function(store, data){
					next_();
				}, function(store, code, message){
					next_();
				});
			}, function(err){
				next(err, eorgs);
			});
		},
		function(eorgs, next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			Bit.util.Async.each(eorgs, function(eorg, next_){
				var st = Bit.nw.Data.Store.mEorgEi;
				st.data = { user: user, data: { sid_eorg: eorg.sid } };
				st.getData(function(store, data){
					next_();
				}, function(store, code, message){
					next_();
				});
			}, function(err){
				next(err, eorgs);
			});
		},
		function(eorgs, next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var st = Bit.nw.Data.Store.mEorgEie;
			st.data = { user: user };
			st.getData(function(store, data){
				next();
			}, function(store, code, message){
				next();
			});
		},
		function(next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var sid_morg = user.sid_morg;
			var prm = req.Request.params() || {};
			var ext = prm.extraction;
			ext.from = '2016-07-04';
			ext.to = '2016-07-04';
			var today = Now().format('yyyy-mm-dd');
			
			var storeEResults = new Bit.nw.cmp.store.EResults();
			storeEResults.data = { user: { sid_morg: sid_morg, sid: user.sid } };
			storeEResults.getData(function(store, data){
				p.eresults = data.list;
				next();
			}, function(store, code, message){
				next(new Error(message));
			}, ext.from || today, ext.to || today);
		},
		function(next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var condition = config.outsource.condition;
			var eresults = p.eresults;
			Bit.log('ExportData: '+ eresults.length);
			var ress = [];
			Bit.nw.Data.Store.mMe.data = { user: user };
			var storeEResult = new Bit.nw.cmp.store.EResult();
			Bit.util.Async.each(eresults, function(eresult, next_){
				var sid_appoint = eresult.appoint.sid;
				storeEResult.data = { user: user };
				storeEResult.getData(function(store, data){
					eresult.res = data;
					
					var res = eresult.res;
					Bit.nw.Data.Store.mMe.setupGetListeners(function(mdl){
						ress.push({ eresult: res, memdl: mdl });
						next_();
					}, function(code, message){
						next_(new Error(message));
					});
					var mdl = Bit.nw.Data.Store.mMe.getModel(res.sid_me+'');
					if(mdl){
						ress.push({ eresult: res, memdl: mdl });
						next_();
					}
				}, function(store, code, message){
					next_(new Error(message));
				}, sid_appoint);
			}, function(err){
				next(err, ress);
			});
		},
		function(eresults, next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var condition = config.outsource.condition;
			var rmap = new Bit.nw.cmp.EcourseXmlMap({});
			for(var i=0,li=eresults.length,re;i<li;++i){
				re = eresults[i];
				rmap.clear();
				// , sid_contract: re.appoint.appoint_me[0].sid_contract }); //2016-07-06 add jj 契約情報を追加
				rmap.setup(re.eresult.xml_me, { Store: Bit.nw.Data.Store, Model: re.memdl, CriterionKit: { value: memdl.raw('sid_criterion') } }); //2016-09-30 CriterionKit追加
				
				
				
				
				p.ret.files.push(rmap.buildXml(true, true));
			}
			next();
		}
	]
};

var getExec = function(sid_section){
	switch(sid_section){
	case Bit.nw.code.SEC_LIC_APP_OUT_EXAMINEE: return examineeProc.execOut;
	case Bit.nw.code.SEC_LIC_APP_OUT_APPOINT: return appointProc.execOut;
	case Bit.nw.code.SEC_LIC_APP_OUT_ORG:
	case Bit.nw.code.SEC_LIC_APP_OUT_CONTRACT:
	case Bit.nw.code.SEC_LIC_APP_OUT_RESULT:
	default: return function(){};
	}
};
