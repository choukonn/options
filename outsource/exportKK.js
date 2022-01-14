/**
 * 協会けんぽCSV出力
 */
var async = require('async');
var jconv = require('jconv');
var csv = require('csv');
var encoding = require('encoding-japanese');
var to_json = Bit.nw.xmljson.to_json;
var to_xml= Bit.nw.xmljson.to_xml;
var _es = require('narwhal/core');
var esql = new _es();
var sv = require('narwhal/core/validation/validation.js');

var checkMemory = function(){
	var mem = process.memoryUsage();
	var rss = Math.ceil(mem.rss / 1024 / 1024);
	var used = Math.ceil(mem.heapUsed / 1024 / 1024);
	var total = Math.ceil(mem.heapTotal / 1024 / 1024);
	Bit.log('proc mem: アプリ: '+ rss +'MB, V8Heap: '+ used +'MB/'+ total +'MB');
};
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

var record_template_header = [ // 5カラム
	'','','','',''
];
var record_template_detail = [ // 366カラム
	'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
	,'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
	,'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
	,'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
	,'','','','','',''
];
var makeRecordFrame = function(isHeader){
	return { data: isHeader ? [ /* 5カラム */'','','','',''] : [ /* 366カラム */
		'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
		,'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
		,'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
		,'','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
		,'','','','','',''
	], conf: { index: 0 } };
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
		Bit.log('協会けんぽCSV出力処理開始。。。');
		//if(global.gc) { global.gc(); }
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
			'options/outsource/export_kk'
		);
	}
}

}, arguments);

var proc = function(req, res, next){
	checkMemory();
	res._startTime = Now().getTime();
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
				res.Response.setup(Bit.errorCreator(110, 'インポート定義ファイルが見つかりません。[_'+ license +'_]'));
				return;
			}
//			if(!outConfig.outsource.columns || !outConfig.outsource.columns.column){
//				res.Response.setup(Bit.errorCreator(111, 'インポート定義ファイルにカラム情報が見つかりません。[_'+ license +'_]'));
//				return;
//			}
//			switch(outConfig.outsource.condition.format){
//			case 'CSV':
//				break;
//			case 'TEXT':
//				return res.Response.setup(Bit.errorCreator(113, 'サポートされていない形式です。[_fm_]'));
//				break;
//			case 'FIXED':
//				return res.Response.setup(Bit.errorCreator(114, 'サポートされていない形式です。[_fm_]'));
//				break;
//			default:
//					return res.Response.setup(Bit.errorCreator(114, 'サポートされていない形式です。[_fm_]'));
//			}
			Bit.defer(function(){
				exportFiles(req, res, next, outConfig);
			});
		},
		exception: function(err){
			res.Response.setup(Bit.errorCreator(112, 'インポート定義ファイル取得中にエラー発生。[_'+ license +'_]'));
		}
	});
};

var exportFiles = function(req, res, next, xml_outsource){
	var prm = req.Request.params()||{};
	var condition = xml_outsource.outsource.condition;
	if(prm.encode){ condition.encoding = prm.encode; }
	if(!condition.start_rowno){ condition.start_rowno = 1; }
	var ret = { CSV: null, file: {}, data: [], config: xml_outsource };
	
	processSet.p = { req: req, res: res, next: next, config: xml_outsource, ret: ret };
	Bit.util.Async.waterfall(processSet.procs, function(err){
		Bit.log('proc time: '+ Math.ceil((Now().getTime() - res._startTime) / 1000) +' sec.');
		checkMemory();
		processSet.store.destroy(); //keepAliveON()
		if(err){
			Bitl.log(err);
			res.Response.setup({ process: 'エラーが発生しました。', file: ret.CSV, config: ret.config, err: err});
			return;
		}
		res.Response.setup({ process: 'データの出力を完了しました。', file: ret.CSV, config: ret.config });
		Bit.log('協会けんぽCSV出力処理完了');
	});

};

var setupCSVData2Rec = function(rec, src, caption){
	caption = caption || '----';
	var c = rec.conf;
	var s = c.index || 0;
	for(var i=0,li=src.length,d=rec.data;i<li;++i){
		d[s++] = src[i];
	}
	//Bit.log('setupCSVData2Rec: '+ caption +' size: '+ src.length +' index: '+ c.index +' > '+ s);
	c.index = s;
};
var makeKKHeader = function(p, data){
//	var reqP = p.req.Request.params();
//	var h = p.config.outsource.condition.header;
//	var dtinv = ''; //(reqP.dt_invoice || '').replaceAll('-', '').replaceAll('/', ''); //!CAUTION 請求年月は未設定で。
//	setupCSVData2Rec(data.record, [h.morg_code, h.morg_name, dtinv, ' ', '']); //TODO 画面で請求年月を入力させる。
	setupCSVData2Rec(data.record, ['', '', '', ' ', '']); // ヘッダはなにもなしでよいかも。。。
};
var chkCourseExamType = function(p, map){//TODO 性別、年齢等での判断も組み込むか？予約画面任せか？
/*
一般健診：問診、身長:178、体重:180、標準体重:182（肥満度？:70308）、腹囲:190、視力:220、聴力:193(192)、胸部聴診・腹部触診（診察所見:171.172）空腹時血糖:463（食後血糖：13507）、HbＡ1c:466、尿糖:503、尿酸:512、血圧:266、
							尿一般・腎機能（尿蛋白:469、尿潜血:472、血清クレアチニン:509）、便潜血:595、直腸:659、血液一般（ヘマトクリット値:358、血色素測定:355、赤血球数:352、白血球数:376）、
							肝機能（GOT:405、GPT:408、γ‐GTP:411、ALP:414）
							12誘導心電図:548(920)、胸部X線:556、胃部X線:579、胃内視鏡:654、眼底:232(23902, 23903, 23904, 23905, 23906)
	※ 腹部超音波:588 が仕様上は一般健診に入ってるけど、単独追加が可能ってこと？（処理からは除外しとく）
子宮頸がん検診（単独受診）：問診、子宮細胞診
※以下、一般健診に追加して受診する健診（セット受診のみで単独受診はできません）
付加健診：尿沈渣:481、血液像:379、血小板:373、肝機能（総蛋白:392、アルブミン:395、総ビリルビン:426、LDH:23）、膵機能（アミラーゼ:445）、眼底:232(23902, 23903, 23904, 23905, 23906)、肺機能:565、腹部超音波:588
乳がん検診：問診、乳房視触診:607、乳房X線:670
子宮頸がん検診：問診、子宮細胞診:604
肝炎ウイルス検査：HCV抗体:439、HBs抗原:429
※眼底の扱いが微妙

健診区分：'1':一般健診、'2':一般健診及び付加健診、'3':20・30歳代の子宮頸がん検診
検査区分：'1':一次検査、'2':単独検査
判定方法

１．付加健診（健診区分：2 検査区分：1）：付加健診の検査項目を一つでも受診しているかどうか。
２．子宮頸がん検診（単独）（健診区分：3 検査区分：1）：子宮頸がん検診（単独受診）である。（一般健診、付加健診、乳がん検診、肝炎検査を一つも受診していない）
３．一般健診（健診区分：1 検査区分：1）：ここまで来たら一般健診とする。
４．単独検査（健診区分：1 検査区分：2）：未使用でいい？
*/
	var ret = [1, 1];
	var i_sids = [178, 180, 182/*（肥満度？:70308）*/, 190, 220, 193/*(192)*/, 171, 463, 466, 503, 512, 266, 469, 472, 509, 595, 659, 358, 355, 352, 376, 405, 408, 411, 414, 548/*(920)*/, 556, 579, 654, 232/*(23902, 23903, 23904, 23905, 23906)*/]; // 一般健診
	var h_sids = [481, 373, 379, 392, 395, 426, 445, 423/*, 232, 23902, 23903, 23904, 23905, 23906*/, 565, 588]; // 付加健診
	var e_sids = [607, 670, 439, 429]; // 子宮頸がん検診（単独受診）判定用乳がん検診、肝炎検査
	var con = false;
	for(var i=0,li=h_sids.length,s;i<li;++i){
		s = h_sids[i];
		if(map.isConsultationConsultEitem(s)){
			con = true;
			break;
		}
	}
	if(con){ // 付加健診検査を受診している。
		ret = [2, 1]; // 付加健診
	}else{
		con = false;
		var ei_sids = i_sids.concat(e_sids);
		for(var i=0,li=ei_sids.length,s;i<li;++i){
			s = ei_sids[i];
			if(map.isConsultationConsultEitem(s)){
				con = true;
				break;
			}
		}
		if(map.isConsultationConsultEitem(604) && !con){ // 子宮頸がん検診を受診しているが、一般健診、付加健診、乳がん検診、肝炎検査を一つも受診していない。
			return [3, 1]; // 子宮頸がん検診（単独受診）
		}
	}
	return ret;
};
var exam_types = [];
var makeKKDetail = function(p, data, ap, org, map){
	var h = p.config.outsource.condition.header;
	var exam = ap.xml_examinee.examinee;
	var birth = new Date(exam.birthday);
	exam_types = chkCourseExamType(p, map);
//	Bit.log('process Examinee: '+ exam.name);
	setupCSVData2Rec(data.record, [h.morg_code, exam_types[0], exam_types[1], exam['name-kana'].hira2Kana(), birth.indexOfJPYear(), birth.format('ee'), birth.format('mm'), birth.format('dd'), exam.sex, ' ', org.n_org.substr(2, 2), Bit.zeroPad(org.xinorg.s_examinee, 8), Bit.zeroPad(org.xinorg.n_examinee, 7), '00', ' ']);
	setupCSVData2Rec(data.record, [ ap.dt_appoint.indexOfJPYear(), ap.dt_appoint.format('ee'), ap.dt_appoint.format('mm'), ap.dt_appoint.format('dd') ]);
};
var getAprvCourse = function(data, map){
	var aprv = data.aprv;
	return { rank: aprv.rank.Total, finding: aprv.finding.Total };
};
var getAprvGroup = function(data, map, gid, outkey){
	var aprv = data.aprv;
	outkey = outkey || 1;
	return { rank: aprv.rank['G'+ gid +'O'+ outkey],
		finding: aprv.rank['G'+ gid]
	};
};
var makeKKExam = function(p, data, ap, org, map){
	var aprvI;
	var aprvG = [getAprvGroup(data, map, 171, 1), getAprvGroup(data, map, 171, 2)]; // 自動判定結果：グループ：診察
	setupCSVData2Rec(data.record, [aprvG[0].rank, ' '], '診察等ー診察等指導区分（１）、（２）'); // 171.1, 171.2
	setupCSVData2Rec(data.record, makeExamKK(map, 178, 179, 'n', { int_: 3, dec: 1 }), '身長');
	setupCSVData2Rec(data.record, makeExamKK(map, 180, 181, 'n', { int_: 3, dec: 1 }), '体重');
	setupCSVData2Rec(data.record, makeExamKK(map, 182, 183, 'n', { int_: 3, dec: 1 }), '標準体重'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 187, 188, 'n', { int_: 3, dec: 1 }), 'BMI'); // 
//	setupCSVData2Rec(data.record, [0, ' ', 0, ' ', 0, ' ']); // 胸囲 //仕様書では胸囲だけど。。。
	setupCSVData2Rec(data.record, makeExamKK(map, 190, 191, 'n', { int_: 3, dec: 1 }), '腹囲実測'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '腹囲自己測定'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '腹囲自己申告'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '内臓脂肪⾯積'); // 
	// 
	setupCSVData2Rec(data.record, makeExamKK(map, 2004, 5, 'f', { only_value: true, fn: function(v){
		return v ? 2 : 1;
	} }), '既往歴 特記有無');
	setupCSVData2Rec(data.record, makeExamKK(map, 2004, 5, '', { only_value: true, length: 20, format: 'multibyte', iids: [2004, 2101], eids: [5, 210101, 210102, 210103, 210104, 210105, 210106, 210107, 210108, 210109, 210110] }), '既往歴'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2025, 726, 'f', { only_value: true, fn: function(v){
		return v ? 2 : 1;
	} }), '自覚症状 特記有無');
	setupCSVData2Rec(data.record, makeExamKK(map, 2025, 726, '', { only_value: true, length: 20, format: 'multibyte', eids: [726, 202502, 202503, 202504, 202505, 202506] }), '自覚症状'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 698, 695, 'f', { only_value: true, fn: function(v){
		return v ? 2 : 1;
	} }), '他覚症状 特記有無');
	setupCSVData2Rec(data.record, makeExamKK(map, 698, 695, '', { only_value: true, length: 20, format: 'multibyte', eids: [695, 696, 697] }), '他覚症状'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 171, 172, '', { only_value: true, length: 8, format: 'multibyte' }), '胸部・腹部所⾒'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 220, 221, 'n', { int_: 2, dec: 2 }), '視力裸眼：右'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 220, 223, 'n', { int_: 2, dec: 2 }), '視力矯正：右'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 220, 222, 'n', { int_: 2, dec: 2 }), '視力裸眼：左'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 220, 224, 'n', { int_: 2, dec: 2 }), '視力矯正：左'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 193, 194, 'f', { only_value: true, iids: [192, 193], eids: [198, 194], fn: function(v){
		if(!v){ return ' '; }
		var eiCriMap = map.eitemAttrCriterionMap(193);
		var cond = eiCriMap.opinionCondition({ eCourseMap: map }), r = 0;
		if(cond){
			var egCriMap = map.eitemParentModelKit(193);
			r = cond.checkHiLo({ eCourseMap: map, egroupSid: egCriMap.exam.raw('sid'), eitemSid: 193, elementSid: 194, $E: 194 });
		}else{
			var rescon = xmlmap.elementResultMap(194);
			if(rescon){
				var result = rescon.result();
				if(result){
					r = result.checkHiLo();
				}
			}
		}
		return Bit.isObject(r) ? ' ' : ((r===0 || r==-1) ? 1 : 2);
	} }), '聴力：右1000'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 193, 196, 'f', { only_value: true, iids: [192, 193], eids: [198, 196], fn: function(v){
		if(!v){ return ' '; }
		var eiCriMap = map.eitemAttrCriterionMap(193);
		var cond = eiCriMap.opinionCondition({ eCourseMap: map }), r = 0;
		if(cond){
			var egCriMap = map.eitemParentModelKit(193);
			r = cond.checkHiLo({ eCourseMap: map, egroupSid: egCriMap.exam.raw('sid'), eitemSid: 193, elementSid: 196, $E: 196 });
		}else{
			var rescon = xmlmap.elementResultMap(196);
			if(rescon){
				var result = rescon.result();
				if(result){
					r = result.checkHiLo();
				}
			}
		}
		return Bit.isObject(r) ? ' ' : ((r===0 || r==-1) ? 1 : 2);
	} }), '聴力：右4000'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 193, 195, 'f', { only_value: true, iids: [192, 193], eids: [199, 195], fn: function(v){
		if(!v){ return ' '; }
		var eiCriMap = map.eitemAttrCriterionMap(193);
		var cond = eiCriMap.opinionCondition({ eCourseMap: map }), r = 0;
		if(cond){
			var egCriMap = map.eitemParentModelKit(193);
			r = cond.checkHiLo({ eCourseMap: map, egroupSid: egCriMap.exam.raw('sid'), eitemSid: 193, elementSid: 195, $E: 195 });
		}else{
			var rescon = xmlmap.elementResultMap(195);
			if(rescon){
				var result = rescon.result();
				if(result){
					r = result.checkHiLo();
				}
			}
		}
		return Bit.isObject(r) ? ' ' : ((r===0 || r==-1) ? 1 : 2);
	} }), '聴力：左1000'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 193, 197, 'f', { only_value: true, iids: [192, 193], eids: [199, 197], fn: function(v){
		if(!v){ return ' '; }
		var eiCriMap = map.eitemAttrCriterionMap(193);
		var cond = eiCriMap.opinionCondition({ eCourseMap: map }), r = 0;
		if(cond){
			var egCriMap = map.eitemParentModelKit(193);
			r = cond.checkHiLo({ eCourseMap: map, egroupSid: egCriMap.exam.raw('sid'), eitemSid: 193, elementSid: 197, $E: 197 });
		}else{
			var rescon = xmlmap.elementResultMap(197);
			if(rescon){
				var result = rescon.result();
				if(result){
					r = result.checkHiLo();
				}
			}
		}
		return Bit.isObject(r) ? ' ' : ((r===0 || r==-1) ? 1 : 2);
	} }), '聴力：左4000'); // 
	setupCSVData2Rec(data.record, [' '], '予備２'); // 
	aprvG = getAprvGroup(data, map, 138); // 自動判定結果：グループ：血圧
	setupCSVData2Rec(data.record, [aprvG.rank], '血圧 指導区分'); // 138 
	setupCSVData2Rec(data.record, makeExamKK(map, 266, 267, 'n', { int_: 3, dec: 1 }), '血圧：収縮期１回目'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 266, 269, 'n', { int_: 3, dec: 1 }), '血圧：収縮期２回目'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血圧：収縮期その他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 266, 268, 'n', { int_: 3, dec: 1 }), '血圧：拡張期１回目'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 266, 270, 'n', { int_: 3, dec: 1 }), '血圧：拡張期２回目'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血圧：拡張期その他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2030, 699, 'c', { only_value: true, map: { '1': 1 /*食後１０時間未満*/, '2': 2 /*食後１０時間以上*/ } }), '血圧：採決時間／食後'); // 
	setupCSVData2Rec(data.record, [' '], '予備３'); // 
	aprvG = getAprvGroup(data, map, 131); // 自動判定結果：グループ：脂質
	setupCSVData2Rec(data.record, [aprvG.rank], '脂質 指導区分'); // 131
	setupCSVData2Rec(data.record, makeExamKK(map, 451, 452, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '総コレステロール'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 460, 461, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '中性脂肪可視'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '中性脂肪紫外'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '中性脂肪その他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 454, 455, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), 'HDLコレステロール可視'); // 
	setupCSVData2Rec(data.record, [' ', ' '], 'HDLコレステロール紫外'); // 
	setupCSVData2Rec(data.record, [' ', ' '], 'HDLコレステロールその他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 457, 458, 'n', { int_: 6, dec: 2 }), 'LDLコレステロール可視'); // 
	setupCSVData2Rec(data.record, [' ', ' '], 'LDLコレステロール紫外'); // 
	setupCSVData2Rec(data.record, [' ', ' '], 'LDLコレステロールその他'); // 
	setupCSVData2Rec(data.record, [' '], '予備４'); // 
	aprvG = getAprvGroup(data, map, 132); // 自動判定結果：グループ：肝機能
	setupCSVData2Rec(data.record, [aprvG.rank], '肝機能 指導区分'); // 132
	setupCSVData2Rec(data.record, makeExamKK(map, 405, 406, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '肝機能：GOT紫外'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '肝機能：GOTその他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 408, 409, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '肝機能：GPT紫外'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '肝機能：GPTその他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 411, 412, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '肝機能：γ-GT可視'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '肝機能：γ-GTその他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 414, 415, 'n', { int_: 3, dec: 1 }), '肝機能：ALP U'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '肝機能：ALP KAU'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 392, 393, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0], types: [2, 1] } }), '肝機能：総蛋白'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 395, 396, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0], types: [2, 1] } }), '肝機能：アルブミン'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 426, 427, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0], types: [2, 1] } }), '肝機能：総ビリルビン'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 423, 424, 'n', { int_: 6, dec: 2 }), '肝機能：LDH IU'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '肝機能：LDH WRU'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 445, 446, 'n', { int_: 6, dec: 2 }), '肝機能：アミラーゼ IU'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '肝機能：アミラーゼ SOU'); // 
	setupCSVData2Rec(data.record, [' '], '予備５'); // 
	aprvG = getAprvGroup(data, map, 135); // 自動判定結果：グループ：血糖
	setupCSVData2Rec(data.record, [aprvG.rank], '血糖 指導区分'); // 135
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：空腹時 電位差'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：空腹時 可視'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, [{ iid: 463, eid: 464 }, { iid: 463, eid: 1350701 }], null, 'n', { int_: 6, dec: 1, intended: { vals: [1, 0] } }), '血糖：空腹時 紫外'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：空腹時 その他'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：随時 電位差'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：随時 可視'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：随時 紫外'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：随時 その他'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：糖負荷 負荷前 血糖'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：糖負荷 負荷前 尿糖'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：糖負荷 １時間 血糖'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：糖負荷 １時間 尿糖'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：糖負荷 ２時間 血糖'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：糖負荷 ２時間 尿糖'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 466, 1057, 'n', { int_: 6, dec: 2 }), '血糖：HbA1c（NGSP）ラテックス'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：HbA1c（NGSP）HPLC'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：HbA1c（NGSP）酵素法'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：HbA1c（NGSP）その他'); // 
	setupCSVData2Rec(data.record, [' ', ' '], '血糖：尿糖 機械'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 503, 504, 'q', { intended: { vals: [1, 0] } }), '血糖：尿糖 目視'); // 
	setupCSVData2Rec(data.record, [' '], '予備６'); // 
	aprvG = getAprvGroup(data, map, 514); // 自動判定結果：グループ：尿酸
	setupCSVData2Rec(data.record, [aprvG.rank], '尿酸 指導区分'); // 514
	setupCSVData2Rec(data.record, makeExamKK(map, 512, 513, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '尿酸：尿酸'); // 
	setupCSVData2Rec(data.record, [' '], '予備７'); // 
	aprvG = getAprvGroup(data, map, 133); // 自動判定結果：グループ：尿腎機能
	setupCSVData2Rec(data.record, [aprvG.rank], '尿腎機能 指導区分'); // 133
	setupCSVData2Rec(data.record, [' ', ' '], '尿腎機能：尿蛋白 機械'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 469, 470, 'q', { intended: { vals: [1, 0] } }), '尿腎機能：尿蛋白 目視'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 472, 473, 'q', { intended: { vals: [1, 0] } }), '尿腎機能：尿潜血'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 481, 482, 'f', { only_value: true, length: 8, format: 'singlebyte', fn: function(v){
		return (v || '').toSingleByte().hira2Kana().kanaW2H().replaceAll(/毎/g, 'ﾏｲ').replaceAll(/全/g, 'ｾﾞﾝ').replaceAll(/数/g, 'ｽｳ').replaceAll(/多数/g, 'ﾀｽｳ').replaceAll(/未満/g, 'ﾐﾏﾝ');
	} }), '尿腎機能：尿沈渣 赤血球'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 481, 483, 'f', { only_value: true, length: 8, format: 'singlebyte', fn: function(v){
		return (v || '').toSingleByte().hira2Kana().kanaW2H().replaceAll(/毎/g, 'ﾏｲ').replaceAll(/全/g, 'ｾﾞﾝ').replaceAll(/数/g, 'ｽｳ').replaceAll(/多数/g, 'ﾀｽｳ').replaceAll(/未満/g, 'ﾐﾏﾝ');
	} }), '尿腎機能：尿沈渣 白血球'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 481, 484, 'f', { only_value: true, length: 8, format: 'singlebyte', fn: function(v){
		return (v || '').toSingleByte().hira2Kana().kanaW2H().replaceAll(/毎/g, 'ﾏｲ').replaceAll(/全/g, 'ｾﾞﾝ').replaceAll(/数/g, 'ｽｳ').replaceAll(/多数/g, 'ﾀｽｳ').replaceAll(/未満/g, 'ﾐﾏﾝ');
	} }), '尿腎機能：尿沈渣 上皮細胞'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 481, 485, 'f', { only_value: true, length: 8, format: 'singlebyte', fn: function(v){
		return (v || '').toSingleByte().hira2Kana().kanaW2H().replaceAll(/毎/g, 'ﾏｲ').replaceAll(/全/g, 'ｾﾞﾝ').replaceAll(/多数/g, 'ﾀｽｳ').replaceAll(/数/g, 'ｽｳ').replaceAll(/未満/g, 'ﾐﾏﾝ');
	} }), '尿腎機能：尿沈渣 円柱'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 481, 486, 'f', { only_value: true, length: 8, format: 'singlebyte', eids: [486, 487], fn: function(v){
		return (v || '').toSingleByte().hira2Kana().kanaW2H().replaceAll(/毎/g, 'ﾏｲ').replaceAll(/全/g, 'ｾﾞﾝ').replaceAll(/多数/g, 'ﾀｽｳ').replaceAll(/数/g, 'ｽｳ').replaceAll(/未満/g, 'ﾐﾏﾝ');
	} }), '尿腎機能：尿沈渣 その他'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 509, 510, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '尿腎機能：クレアチニン'); // 
	setupCSVData2Rec(data.record, [' '], '予備８'); // 
	aprvG = getAprvGroup(data, map, 136); // 自動判定結果：グループ：血液一般 !CAUTION 貧血と合算
	setupCSVData2Rec(data.record, [aprvG.rank], '血液一般 指導区分'); // 136
	setupCSVData2Rec(data.record, makeExamKK(map, 358, 359, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '血液一般：ヘマトクリット'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 355, 356, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '血液一般：ヘモグロビン'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 352, 353, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '血液一般：赤血球数'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 376, 377, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0] } }), '血液一般：白血球数'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 373, 374, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0], types: [2, 1] } }), '血液一般：血小板数'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 380, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Baso'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 381, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Eosino'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 383, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Stab'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 384, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Seg'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 382, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Neutro'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 385, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Lympho'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 386, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Mono'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 379, 749, 'n', { int_: 6, dec: 2 }), '血液一般：血液像 Other'); // 
	setupCSVData2Rec(data.record, [' '], '血液一般：実施理由'); // 
	setupCSVData2Rec(data.record, [' '], '予備９'); // 
	aprvG = getAprvGroup(data, map, 139); // 自動判定結果：グループ：心電図
	setupCSVData2Rec(data.record, [aprvG.rank], '心電図 指導区分'); // 139
	setupCSVData2Rec(data.record, makeExamKK(map, 548, 549, '', { length: 14, format: 'multibyte' }), '心電図：所見'); // 
	setupCSVData2Rec(data.record, [' '], '心電図：実施理由'); // 
	setupCSVData2Rec(data.record, [' '], '予備１０－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１０－２'); // 
	aprvG = getAprvGroup(data, map, 239); // 自動判定結果：グループ：眼底
	setupCSVData2Rec(data.record, [aprvG.rank], '眼底 指導区分'); // 239
	setupCSVData2Rec(data.record, makeExamKK(map, 232, 233, 'c', { iids: [232, 23902], eids: [233, 2390201, 2390202] }), '眼底：K.W.'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 232, 241, 'c', { iids: [232, 23903], eids: [241, 2390301, 2390302] }), '眼底：ScheieH'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 232, 244, 'c', { iids: [232, 23904], eids: [244, 2390401, 2390402] }), '眼底：ScheieS'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 232, 255, 'c', { iids: [232, 23905], eids: [255, 2390501, 2390502] }), '眼底：SCOTT'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 232, 263, '', { only_value: true, length: 20, format: 'multibyte', iids: [232, 23906], eids: [263, 2390601, 2390602] }), '眼底：所見'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 232, 2390701, '', { only_value: true, length: 20, format: 'multibyte' }), '眼底：実施理由'); // 
	setupCSVData2Rec(data.record, [' '], '予備１１'); // 
	aprvG = getAprvGroup(data, map, 578); // 自動判定結果：グループ：肺機能
	setupCSVData2Rec(data.record, [aprvG.rank], '肺機能 指導区分'); // 578
	setupCSVData2Rec(data.record, makeExamKK(map, 565, 566, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0], types: [2, 1] } }), '肺機能：肺活量'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 565, 570, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0], types: [2, 1] } }), '肺機能：１秒量'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 565, 571, 'n', { int_: 6, dec: 2, intended: { vals: [1, 0], types: [2, 1] } }), '肺機能：１秒率'); // 
	setupCSVData2Rec(data.record, [' '], '予備１２'); // 
	aprvG = getAprvGroup(data, map, 141); // 自動判定結果：グループ：胸部X線
	setupCSVData2Rec(data.record, [aprvG.rank], '胸部X線 指導区分'); // 141
	setupCSVData2Rec(data.record, makeExamKK(map, 556, 562, 'c', { only_value: true, map: { '1': 1 /*直接*/, '2': 2 /*間接*/, '3': 1 /*デジタル*/ } }), '胸部X線 撮影区分'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 556, 557, '', { only_value: true, length: 18, format: 'multibyte' }), '胸部X線 所見'); // 
	setupCSVData2Rec(data.record, [' '], '予備１３－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１３－２－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１３－２－２'); // 
//	aprvG = [getAprvGroup(data, map, 753, 1), getAprvGroup(data, map, 753, 2)]; // 自動判定結果：グループ：胃部X線
//	setupCSVData2Rec(data.record, [aprvG[0].rank], '胃部X線 指導区分'); // 753.1
	aprvI = map.groupRankName(map.eitemResultOpinion(579, '1').code()) || '';
	setupCSVData2Rec(data.record, [aprvI], '胃部X線 指導区分'); // 579
	setupCSVData2Rec(data.record, makeExamKK(map, 579, 585, 'c', { only_value: true, map: { '1': 1 /*直接*/, '2': 2 /*間接*/, '3': 1 /*デジタル*/ } }), '胃部X線 撮影区分'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 579, 580, '', { only_value: true, length: 18, format: 'multibyte' }), '胃部X線 所見'); // 
//setupCSVData2Rec(data.record, [aprvG[1].rank], '胃部内視鏡 指導区分'); // 753.2
	aprvI = map.groupRankName(map.eitemResultOpinion(654, '2').code()) || '';
	setupCSVData2Rec(data.record, [aprvI], '胃部内視鏡 指導区分'); // 654
	setupCSVData2Rec(data.record, makeExamKK(map, 654, 655, '', { only_value: true, length: 8, format: 'multibyte' }), '胃部内視鏡 所見'); // 
	setupCSVData2Rec(data.record, [' '], '予備１４－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１４－２－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１４－２－２'); // 
	aprvG = getAprvGroup(data, map, 144); // 自動判定結果：グループ：腹部超音波
	setupCSVData2Rec(data.record, [aprvG.rank], '腹部超音波 指導区分'); // 144
	setupCSVData2Rec(data.record, makeExamKK(map, 588, 750, '', { only_value: true, length: 18, format: 'multibyte' }), '腹部超音波：所見'); // 
	setupCSVData2Rec(data.record, [' '], '予備１５－１'); // 
	aprvG = [getAprvGroup(data, map, 598, 1), getAprvGroup(data, map, 598, 2)]; // 自動判定結果：グループ：便潜血
	setupCSVData2Rec(data.record, [aprvG[0].rank], '便潜血 指導区分'); // 598.1
	setupCSVData2Rec(data.record, makeExamKK(map, 595, 596, 'q', null), '便潜血 １回目 '); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 595, 597, 'q', null), '便潜血 ２回目'); // 
//setupCSVData2Rec(data.record, [aprvG[1].rank], '直腸診 指導区分'); // 598.2
	aprvG = getAprvGroup(data, map, 662, 1); // 自動判定結果：グループ：便潜血
	setupCSVData2Rec(data.record, [aprvG.rank], '直腸診 指導区分'); // 662
	setupCSVData2Rec(data.record, makeExamKK(map, 659, 660, '', { only_value: true, length: 8, format: 'multibyte' }), '直腸診 所見'); // 
	setupCSVData2Rec(data.record, [' '], '予備１６－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１６－２'); // 
	aprvG = getAprvGroup(data, map, 709); // 自動判定結果：グループ：乳房
	setupCSVData2Rec(data.record, [aprvG.rank], '乳房 指導区分'); // 709
	setupCSVData2Rec(data.record, makeExamKK(map, 607, 608, '', { only_value: true, length: 14, format: 'multibyte' }), '乳房視触診 所見'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 670, 671, '', { length: 14, format: 'multibyte' }), '乳房マンモグラフィー 所見'); // 
	setupCSVData2Rec(data.record, [' '], '予備１７－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１７－２'); // 
	aprvG = getAprvGroup(data, map, 708); // 自動判定結果：グループ：子宮
	setupCSVData2Rec(data.record, [aprvG.rank], '子宮 指導区分'); // 708
	// 
	setupCSVData2Rec(data.record, [(function(){
		var v;
		if(map.eitemResultConsult(604)){ // 受診対象
			v = map.elementResultValue4Input(605);
			if(Bit.invalidStr(v)){
				v = map.elementResultValue4Input(1164);
			}
			if(v){ // 結果あり
				var opi = map.eitemResultOpinion(604, '1'); // iid: 604
				var cd = opi ? opi.code() : Bit.nw.code.SEC_RNK_IG;
				switch(cd){
				case Bit.nw.code.SEC_RNK_IG:
				case Bit.nw.code.SEC_RNK_NG:
					v = '?'; // 設定不能にしとく
					break;
				case Bit.nw.code.SEC_RNK_A:
					v = 1;
					break;
				default: v = 2; //!CAUTION A判定以外は ２：要精検に。。。
				}
			}else{ // 結果なし
				v = ' ';
			}
		}else{ // 未受診
			v = ' ';
		}
		return v;
	})()], '子宮細胞診（スメア）');
	setupCSVData2Rec(data.record, [' '], '予備１８－１'); // 
	setupCSVData2Rec(data.record, [' '], '予備１８－２'); // 
//	aprvG = [getAprvGroup(data, map, 707, 1), getAprvGroup(data, map, 707, 2)]; // 自動判定結果：グループ：肝炎
//	setupCSVData2Rec(data.record, [aprvG[0].rank], '肝炎 HBs抗原 指導区分'); // 707.1
	aprvI = map.groupRankName(map.eitemResultOpinion(429, '1').code()) || '';
	setupCSVData2Rec(data.record, [aprvI], '肝炎 HBs抗原 指導区分'); // 429
	// 
	setupCSVData2Rec(data.record, makeExamKK(map, 429, 431, 'q', {}), '肝炎 HBs抗原（定性）');
//		setupCSVData2Rec(data.record, makeExamKK(map, 429, 432, 'n', { int_: 8, dec: 2 }), '肝炎 HBs抗原（定量）'); // 
//	setupCSVData2Rec(data.record, [aprvG[1].rank], '肝炎 HCV指導区分'); // 707.2
	// HCVとHCV核酸増幅で重い方を算出する。
	var hcvcd = map.criterionmap.ranksetMap('GROUP').maxRank([map.eitemResultOpinion(429, '1').code(), map.eitemResultOpinion(439, '1').code()]);
	aprvI = map.groupRankName(hcvcd) || ' ';
//	Bit.log('EXPORTKK：肝炎 HCV指導区分：code: '+ hcvcd +', name: '+ aprvI +' ---------------------------------------------------------------------------');
	setupCSVData2Rec(data.record, [aprvI], '肝炎 HCV指導区分'); // 439
	// 
	setupCSVData2Rec(data.record, makeExamKK(map, 439, 440, 'f', { only_value: true, fn: function(v){
		if(!v){ return ' '; }
		if(map.eitemResultConsult(442)){ // 核酸増幅を受診していれば３
			return 3;
		}
		var opi = map.eitemResultOpinion(439, '1');
		return (opi && opi.code() == Bit.nw.code.SEC_RNK_A) ? 1 : 2; //!CAUTION A判定以外は ２に。。。
	} }), '肝炎 HCV抗体');
	//
	setupCSVData2Rec(data.record, makeExamKK(map, 442, 443, 'f', { only_value: true, fn: function(v){
		if(!v){ return ' '; }
		opi = map.eitemResultOpinion(442, '1');
		return (opi && opi.code() == Bit.nw.code.SEC_RNK_A) ? 1 : 2; //!CAUTION A判定以外は ２に。。。
	} }), '肝炎 HCV核酸増幅');
	setupCSVData2Rec(data.record, [' '], '予備１９'); // 
	var aprvC = getAprvCourse(data, map); // 自動判定結果：総合
	var aprvCs;
//	switch(aprvC.rank-0){ // excel ver.1.01 で仕様通り動くかも。。。
//	case 1: aprvCs = [aprvC.rank, ' ', ' ', ' ', ' ', ' ']; //
//		break;
//	case 2: aprvCs = [' ', aprvC.rank, ' ', ' ', ' ', ' ']; //
//		break;
//	case 3: aprvCs = [' ', ' ', aprvC.rank, ' ', ' ', ' ']; //
//		break;
//	case 4: aprvCs = [' ', ' ', ' ', aprvC.rank, ' ', ' ']; //
//		break;
//	case 5: aprvCs = [' ', ' ', ' ', ' ', aprvC.rank, ' ']; //
//		break;
//	case 6: aprvCs = [' ', ' ', ' ', ' ', ' ', aprvC.rank]; //
//		break;
//	default:  aprvCs = [' ', ' ', ' ', ' ', ' ', ' ']; //
//	}
	switch(aprvC.rank-0){ // excel ver.1.00 だと仕様通りに動かないため、ここは暫定で
	case 1: aprvCs = [aprvC.rank, '', '', '', '', '']; //
		break;
	case 2: aprvCs = ['', aprvC.rank, '', '', '', '']; //
		break;
	case 3: aprvCs = ['', '', aprvC.rank, '', '', '']; //
		break;
	case 4: aprvCs = ['', '', '', aprvC.rank, '', '']; //
		break;
	case 5: aprvCs = ['', '', '', '', aprvC.rank, '']; //
		break;
	case 6: aprvCs = ['', '', '', '', '', aprvC.rank]; //
		break;
	default:  aprvCs = ['', '', '', '', '', '']; //
	}
	setupCSVData2Rec(data.record, aprvCs, '総合所見指導区分（１）～（６）');
	setupCSVData2Rec(data.record, [' '], '予備２０'); // 
	var goAll = map.egroupResultOpinionsAll();
	gfinding = '';
	if(goAll.length){
		for(var i=0,li=goAll.length,g;i<li;++i){
			g = goAll[i];
			gfinding += g.title +'：'+ g.findings.join('');
		}
	}
	setupCSVData2Rec(data.record, [
		(exam_types[0] == 3 && exam_types[1] == 1) ? ' ' : gfinding.toMultiByte().substr(0, 192) || ' ' // 子宮頸がん検診（単独）の場合は設定対象外（' '）に
	], '注意事項'); // 判定所見一覧を結合
	setupCSVData2Rec(data.record, [' '], '判定区分'); // 
	if(exam_types[0] == 3 && exam_types[1] == 1){ // 子宮頸がん検診（単独）の場合は設定対象外（' '）に
		//!CAUTION Excel ver.1.00 は「' '（設定対象外）」にするとエラー出るので、空文字にしとく。（ver.1.01で改修されている可能性あり）
		setupCSVData2Rec(data.record, [''], '医師の判断 メタボ'); // 
	}else{
		setupCSVData2Rec(data.record, makeExamKK(map, 2047, 620, 'f', { only_value: true, fn: function(v){
			switch(v-0){
			case 1: return 3; // 非該当
			case 2: return 2; // 予備群該当
			case 3: return 1; // 基準該当
			case 4: return 4; // 判定不能
			default: return 4; // 判定不能
			}
		} }), '医師の判断 メタボ'); // 
	}

//	setupCSVData2Rec(data.record, [' '], '医師の判断 メタボ保険指導'); // メタボ保険指導はスペースでよいようで。。。
	setupCSVData2Rec(data.record, makeExamKK(map, 2048, 48, 'f', { only_value: true, fn: function(v){
//		if(exam_types[0] == 3 && exam_types[1] == 1){ // 子宮頸がん検診（単独）の場合は設定対象外（' '）に
//			return ''; //!CAUTION Excel ver.1.00 は「' '（設定対象外）」にするとエラー出るので、空文字にしとく。（ver.1.01で改修されている可能性あり）
//		}
		switch(v-0){
		case 1:
		case 2: return 3; // なし
		case 3: return 2; // 動機づけ支援
		case 4: return 1; // 積極的支援
		case 5: return 4; // 判定不能
		default: return ' '; // 設定対象外 //!CAUTION 仕様上は ' '：設定対象外だが、v100では受け付けないため、4：判定不能とする。
		}
	} }), '医師の判断 メタボ保険指導'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2049, 1067, 'f', { only_value: true, length: 20, format: 'multibyte', fn: function(v){
		var corseopi = map.ecourseResultOpinion();
		var rdata = map.totalRankData(corseopi.code());
		var rank = map.totalRankName(corseopi.code()) || '';
		var finding = rdata.finding() || '';
		if(rank || finding){
			return rank +'　'+ finding;
		}
		return '特になし';
	}}), '医師の判断 注意事項/医師の判断'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2056, 1074, 'f', { only_value: true, length: 20, format: 'multibyte', fn: function(v){
		v = v || '';
		if(!v){
			var doctorId = map.ecourseResultOpinion().sid_doctor();
			var user = doctorId ? Bit.nw.Data.Store.mUser.getModel({sid: doctorId}) : null;
			if(user){
				v = user.get('name');
			}
		}
		v = v || ' ';//'----';
		return v;
	} }), '医師の判断 健康診断を実施した医師の氏名'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2006, 23, 'f', { only_value: true, fn: function(v){
		return v == 92001 ? 1 : 2 /* 未設定の場合も '2' */;
	} }), '質問票 服薬１ 血圧'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2006, 200602, '', { only_value: true, length: 20, format: 'multibyte' }), '質問票 服薬１ 薬剤'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2006, 200603, '', { only_value: true, length: 20, format: 'multibyte' }), '質問票 服薬１ 服薬理由'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2007, 24, 'f', { only_value: true, fn: function(v){
		return v == 92001 ? 1 : 2 /* 未設定の場合も '2' */;
	} }), '質問票 服薬２ 血糖'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2007, 200702, '', { only_value: true, length: 20, format: 'multibyte' }), '質問票 服薬２ 薬剤'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2007, 200703, '', { only_value: true, length: 20, format: 'multibyte' }), '質問票 服薬２ 服薬理由'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2008, 25, 'f', { only_value: true, fn: function(v){
		return v == 92001 ? 1 : 2 /* 未設定の場合も '2' */;
	} }), '質問票 服薬３ 脂質'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2008, 200802, '', { only_value: true, length: 20, format: 'multibyte' }), '質問票 服薬３ 薬剤'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2008, 200803, '', { only_value: true, length: 20, format: 'multibyte' }), '質問票 服薬３ 服薬理由'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2001, 2, 'b', { only_value: true }), '質問票 既往歴 脳血管'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2002, 3, 'b', { only_value: true }), '質問票 既往歴 心血管'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2003, 4, 'b', { only_value: true }), '質問票 既往歴 腎不全・人工透析'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2005, 22, 'b', { only_value: true }), '質問票 貧血'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2009, 30, 'f', { only_value: true, fn: function(v){
		return v == 92001 ? 1 : 2 /* 未設定の場合も '2' */;
	} }), '質問票 喫煙歴'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2013, 712, 'b', { only_value: true }), '質問票 ２０歳からの体重変化'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2014, 713, 'b', { only_value: true }), '質問票 ３０分以上の運動習慣'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2015, 714, 'b', { only_value: true }), '質問票 歩行または身体活動'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2016, 715, 'b', { only_value: true }), '質問票 歩行速度'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2017, 716, 'b', { only_value: true }), '質問票 １年間の体重変化'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2018, 717, 'c', { only_value: true, map: { '1': 1/*速い*/, '2': 2/*ふつう*/, '3': 3/*遅い*/, 'NaN': ' ' } }), '質問票 食べ方 早食い等'); //  
	setupCSVData2Rec(data.record, makeExamKK(map, 2019, 718, 'b', { only_value: true }), '質問票 食べ方 就寝前'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2020, 719, 'b', { only_value: true }), '質問票 食べ方 夜食/間食'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2021, 720, 'b', { only_value: true }), '質問票 食習慣'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2010, 40, 'c', { only_value: true, map: { '1': 1/*毎日*/, '2': 2/*時々*/, '3': 3/*ほとんど飲まない*/, 'NaN': ' ' } }), '質問票 飲酒'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2011, 41, 'c', { only_value: true, map: { '1': 1/*１合未満*/, '2': 2/*１～２合未満*/, '3': 3/*２～３未満*/, '4': 4/*３合以上*/, 'NaN': ' ' } }), '質問票 飲酒量'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2022, 723, 'b', { only_value: true }), '質問票 睡眠'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2023, 724, 'c', { only_value: true, map: { '1': 1/*意思なし*/, '2': 2/*意志あり（６か月以内）*/, '3': 3/*近いうち*/, '4': 4/*６か月未満*/, '5': 5/*６か月以上*/, 'NaN': ' ' } }), '質問票 生活習慣の改善'); // 
	setupCSVData2Rec(data.record, makeExamKK(map, 2024, 725, 'b', { only_value: true }), '質問票 保健指導の希望'); // 
	setupCSVData2Rec(data.record, [' '], '予備２１'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 階層化区分'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 特保面談 実施種別'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 特保面談 実施年月日（元号）'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 特保面談 実施年月日（年）'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 特保面談 実施年月日（月）'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 特保面談 実施年月日（日）'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 オプトアウト 区分'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 オプトアウト 日付（元号）'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 オプトアウト 日付（年）'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 オプトアウト 日付（月）'); // 
	setupCSVData2Rec(data.record, [' '], '伝達事項 オプトアウト 日付（日）'); // 
	setupCSVData2Rec(data.record, ['0'], '取下区分'); // 
	setupCSVData2Rec(data.record, [''], '請求額 税込額 一般'); // 
	setupCSVData2Rec(data.record, [''], '請求額 税込額 付加'); // 
	setupCSVData2Rec(data.record, [''], '請求額 税込額 子宮'); // 
	setupCSVData2Rec(data.record, [''], '請求額 税込額 肝炎'); // 
	setupCSVData2Rec(data.record, [''], '請求額 税込額 眼底'); // 
	setupCSVData2Rec(data.record, [''], '請求額 税込額 合計'); // 
	setupCSVData2Rec(data.record, [''], '請求額 未実施 一般'); // 
	setupCSVData2Rec(data.record, [''], '請求額 未実施 付加'); // 
	setupCSVData2Rec(data.record, [''], '請求額 未実施 合計'); // 
	setupCSVData2Rec(data.record, [''], '請求額 自己負担 一般'); // 
	setupCSVData2Rec(data.record, [''], '請求額 自己負担 付加'); // 
	setupCSVData2Rec(data.record, [''], '請求額 自己負担 子宮'); // 
	setupCSVData2Rec(data.record, [''], '請求額 自己負担 肝炎'); // 
	setupCSVData2Rec(data.record, [''], '請求額 自己負担 眼底'); // 
	setupCSVData2Rec(data.record, [''], '請求額 自己負担 合計'); // 
	setupCSVData2Rec(data.record, [''], '請求額 請求額 一般'); // 
	setupCSVData2Rec(data.record, [''], '請求額 請求額 付加'); // 
	setupCSVData2Rec(data.record, [''], '請求額 請求額 子宮'); // 
	setupCSVData2Rec(data.record, [''], '請求額 請求額 肝炎'); // 
	setupCSVData2Rec(data.record, [''], '請求額 請求額 眼底'); // 
	setupCSVData2Rec(data.record, [''], '請求額 請求額 合計'); // 
	setupCSVData2Rec(data.record, [''], '請求額 消費税 一般'); // 
	setupCSVData2Rec(data.record, [''], '請求額 消費税 付加'); // 
	setupCSVData2Rec(data.record, [''], '請求額 消費税 子宮'); // 
	setupCSVData2Rec(data.record, [''], '請求額 消費税 肝炎'); // 
	setupCSVData2Rec(data.record, [''], '請求額 消費税 眼底'); 
	setupCSVData2Rec(data.record, [''], '請求額 消費税 合計'); 
	return ret;
};
var formedKK = function(val/*{ value, form }*/, int_, dec){ // { 'L': '未満', 'E': '以下', 'U': '以上', 'O': '超', 'B': '結果なし' }
	return val.value.round(dec).formatDigit(int_, dec);
};
var picExam = function(map, exams){
	if(!exams){ return { iid: 0, eid: 0 }; }
	if(!Bit.isArray(exams)){ return exams; }
	for(var i=0,li=exams.length,e;i<li;++i){
		e = exams[i];
		if(map.eitemKitAttr(e.iid) && map.elementKitAttr(e.eid)){
			return e;
		}
	}
	return exams[0];
};
var makeExamKK = function(map, iid, eid, type, conf){
	conf = conf || {};
	var v, rc = ' ', rv = '', br = null;
	if(exam_types[0] == 3 && exam_types[1] == 1){ // 子宮頸がん検診（単独）の場合は設定対象外（' '）に
		rv = ' ';
	}else{
		if(Bit.isArray(iid) || Bit.isObject(iid)){ // 数値ではなくてセットアップ情報（{ iid: xxx, eid: xxx }）なら、展開する。ただし、配列の場合は有効なものを取得する。（先頭一致）
			var e = picExam(map, iid);
			iid = e.iid;
			eid = e.eid;
		}
		if(!map.eitemKitAttr(iid) || !map.elementKitAttr(eid)){
//			Bit.log('makeExamKK: No entry!: iid: '+ iid +' eid: '+ eid);
			rc = ' ';
			rv = ' ';
			if(type == 'f'){ // 外部処理の場合は「値なし」で呼び出す。
				br = conf.fn(null, iid, eid);
			}
			if(br){
				if(Bit.isArray(br)){
					rc = br[0];
					rv = br[1];
				}else{
					rv = br;
				}
			}
		}else{
//		Bit.log('makeExamKK: iid: '+ iid +' eid: '+ eid);
			var intended = [1, ' ']/* 受診対象外の場合は「' '：設定対象外」*/, inte = conf.intended;
			if(inte){ // 個別指定がある場合
				if(inte.types){ // コースの限定がある場合
					if(inte.types[0] == exam_types[0] && inte.types[1] == exam_types[1]){
						intended = inte.vals; // コースに一致した場合にのみ適用
					}
				}else{
					intended = inte.vals; // 無条件で適用
				}
			}
			rc = map.eitemResultConsult(iid) ? intended[0] : intended[1];
			if(rc == 1){
				v = map.elementResultValue4Input(eid);
				if(type == 'n'){ // 数値型
					if(Bit.invalid(v.value)){ // 受診対象だが、値がない場合はどうする？：現況「'0'：未実施」とする。
						rc = '0';
						rv = ' ';
					}else{
						if(isNaN(v.value-0)){
		//					Bit.log('  n: '+ v.value);
							rc = '?';
							rv = ' ';
						}else{
							v.value -= 0;
							var vb = v.value.round(conf.dec).formatDigit(conf.int_, conf.dec);
							if(iid == 429 && eid == 432){
								rv = '2'+ Bit.zeroPad(vb, 8);
							}else{
								rv = vb;
							}
						}
					}
				}else if(type == 'q' || type == 'c'){ // 定性型、文字型
					if(Bit.invalid(v.value)){ // 受診対象だが、値がない場合はどうする？：現況「'0'：未実施」とする。
						rc = '0';
						rv = ' ';
					}else{
						var c;
						if(conf.map){ // map が定義されている場合は値変換で完了する。
							c = conf.map[(v.value-0)+''];
							if(Bit.valid(c)){
								rv = c;
							}else{
								rc = '?';
								rv = ' ';
							}
						}else{
							if(type=='c'){
								v.value = map.elementResultText(eid);
							}
							c = convertQuelitativeClassKK(iid, eid, v.value, map);
							if(c){ // コンバート対象の場合（値が適正でない場合には半角スペースが返る）
								if(c == ' '){
									rc = '?';
									rv = ' ';
								}else{
									if(iid == 429 && eid == 431){
										rv = '10000'+ c +'.00';
									}else{
										rv = '00000'+ c +'00';
									}
								}
							}else{
								rv = map.elementResultText(eid) || '';
							}
						}
					}
				}else if(type == 'b'){ // 論理型
					if(Bit.invalid(v.value)){ // 受診対象だが、値がない場合はどうする？：現況「'0'：未実施」とする。
						rc = '0';
						rv = ' ';
					}else{
						rv = (v.value == 92001 ? 1 : 2);
					}
				}else if(type == 'f'){ // カスタム処理
					br = conf.fn(v.value, iid, eid);
					if(br){
						if(Bit.isArray(br)){
							rc = br[0];
							rv = br[1];
						}else{
							rv = br;
						}
					}
				}else{ // 文字列
					rv = v.value || '';
				}
			}else{
				rv = '';
				if(type == 'f'){ // 外部処理の場合は「値なし」で呼び出す。
					br = conf.fn(null, iid, eid);
				}
				if(br){
					if(Bit.isArray(br)){
						rc = br[0];
						rv = br[1];
					}else{
						rv = br;
					}
				}
			}
		}
		if(Bit.valid(rv) && conf.length){
			rv = (rv+'').substr(0, conf.length);
//			Bit.log('makeExamKK: conf.length: '+ conf.length +' '+ rv);
		}
		if(Bit.valid(rv) && conf.format){
			if(conf.format == 'singlebyte'){
				rv = (rv+'').toSingleByte().hira2Kana().kanaW2H();
			}else if(conf.format == 'multibyte'){
				rv = (rv+'').toMultiByte().kanaH2W();
			}
		}
	}
	if(conf.only_intended){
		return [rc];
	}else if(conf.only_value){
		return [rv];
	}
	if(rc === 0 || rc == '?'){ rv = ' '; }
	return [rc, rv];
};
var convertQuelitativeClassKK = function(iid, eid, value, map){
/*
尿糖：機械読み取り、目視法：1：－、2：±、3：＋、4：＋＋、5：＋＋＋以上
眼底：キースワグナー分類：1：０、2：Ⅰ、3：Ⅱa、4：Ⅱb、5：Ⅲ、6：Ⅳ
眼底：シェイエ分類（H）、シェイエ分類（S）：1：０、2：１、3：２、4：３、5：４
眼底：SCOTT 分類：1：Ⅰ(a)、2：Ⅰ(b)、3：Ⅱ、4：Ⅲ(a)、5：Ⅲ(b)、6：Ⅳ、7：Ⅴ(a)、8：Ⅴ(b)、9：Ⅵ
尿蛋白：機械読み取り、目視法：1：－、2：±、3：＋、4：＋＋、5：＋＋＋
尿潜血：1：－、2：＋－、3：＋、4：2＋、5：3＋、6：4＋
免疫便潜血反応（1日、2日）：1：－、3：＋
HBｓ抗原：1：－、2：＋－、3：＋
*/
/*
91001：－、91002：＋－、91003：＋、91004：２＋、91005：３＋、91006：４＋、91007：５＋、91008：６＋、91020：２－、91021：３－、91022：４－、91023：５－、91024：６－
*/
/* 92001：はい、92002：いいえ */
/*
93001：脳卒中、93002：心臓病、93003：慢性腎不全、93004：貧血、93005：痔、93006：高血圧、93007：高脂血症、93008：肝臓病、93009：腎臓病、93010：糖尿病、93011：痛風、
93012：心臓疾患、93013：呼吸器疾患、93014：上部消化器疾患、93015：前立腺疾患、93016：子宮疾患、93017：聴力障害、93018：視力障害
*/
	var iids = [503, 232, 23902, 23903, 23904, 23905, 469, 472, 595, 429];
	var eids = [504, 233, 2390201, 2390202, 241, 244, 2390301, 2390302, 2390401, 2390402, 255, 2390501, 2390502, 470, 473, 596, 597, 431];
	if(iids.indexOf(iid) == -1 || eids.indexOf(eid) == -1){ return; }
	var v, idx;
	switch(iid){
	case 503: // 尿糖：eid：504
		if(eid == 504){
			v = value - 91000;
			if(1 <= v && v <= 5){ return v; }
			else if(5 < v){ return 5; } // 4+以上は5
		}
		break;
	case 232: // 眼底：eid：KW：233：Scheie H：241、Scheie S：244、SCOTT：255
	case 23902: // 眼底KW：eid：右：2390201、左：2390202
	case 23903: // 眼底Scheie H：eid：右：2390301、左：2390302
	case 23904: // 眼底Scheie S：eid：右：2390401、左：2390402
	case 23905: // 眼底SCOTT：eid：右：2390501、左：2390502
		if(eid == 233 || eid == 2390201 || eid == 2390202){ // KW
			idx = ['0', 'Ⅰ', 'Ⅱa', 'Ⅱb', 'Ⅲ', 'Ⅳ'].indexOf(value.toSingleByte());
			if(0 <= idx && idx <= 5){ return idx+1; }
		}
		if(eid == 241 || eid == 244 || eid == 2390301 || eid == 2390302 || eid == 2390401 || eid == 2390402){ // Scheie H, S
			v = value.toSingleByte();
			if(0 <= v && v <= 4){ return (v-0)+1; }
		}
		if(eid == 255 || eid == 2390501 || eid == 2390502){ // SCOTT
			idx = ['Ⅰ(a)', 'Ⅰ(b)', 'Ⅱ', 'Ⅲ(a)', 'Ⅲ(b)', 'Ⅳ', 'Ⅴ(a)', 'Ⅴ(b)', 'Ⅵ'].indexOf(value.toSingleByte());
			if(0 <= idx && idx <= 8){ return idx+1; }
		}
		break;
	case 469: // 尿蛋白：eid：470
		if(eid == 470){
			v = value - 91000;
			if(1 <= v && v <= 5){ return v; }
//			else if(v < 5){ return 5; } // 4+以上は5
		}
		break;
	case 472: // 尿潜血：eid：473
		if(eid == 473){
			v = value - 91000;
			if(1 <= v && v <= 6){ return v; }
//			else if(v < 6){ return 6; } // 5+以上は6
		}
		break;
	case 595: // 便潜血検査：eid：１回目：596、２回目：597
		if(eid == 596 || eid == 597){
			v = value - 91000;
			if(v == 1 || v == 3){ return v; }
//			return 3; // その他は3
		}
		break;
	case 429: // HBs抗原：eid：定性：431、定量：432
		if(eid == 431){
			v = value - 91000;
			if(1 <= v && v <= 3){ return v; }
//			return 3; // その他は3
		}
		break;
	}
	return ' ';
};
// 協会けんぽ出力用データ変換（CSV元データ配列生成）
var convertKKHeader = function(p, data){
	var req = p.req, config = p.config;
	data = data || {};
	data.record = makeRecordFrame(true);
	makeKKHeader(p, data);
//	Bit.log('convertKKHeader: data size: '+ data.record.data.length);
	return data.record.data;
};
var convertKK = function(p, data){
	var req = p.req, config = p.config;
	data.record = makeRecordFrame();
	var ap = data.arc.appoint;
	var org = data.org;
	var map = data.csmap;
	makeKKDetail(p, data, ap, org, map);
	makeKKExam(p, data, ap, org, map);
//	Bit.log('convertKK: data size: '+ data.record.data.length);
	return data.record.data;
};
// 協会けんぽ用CSV生成
var makeCSV = function(p, data, callback){
	var me = this;
	var req = p.req, res = p.res, config = p.config, ret = p.ret;
	var condition = config.outsource.condition;
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
	csv.stringify(data, opts/*{ quote: "'", eof: true, quoted: true, quotedEmpty: true }*/,
	function(err, src){
		if(err){
			callback(err);
			return;
		}
//				Bit.log(src);
		if(condition.encoding == 'Shift_JIS'){ src = jconv.encode(src, 'Shift_JIS'); }
		ret.CSV = src;
		callback(err);
	});
};
// 協会けんぽ出力用データ変換処理呼び出し
var makeCSVData = function(p, callback){
	var dts = p.ret.data;
	if(dts.length === 0){
		Bit.log('makeCSVData: 処理対象データがありません。');
		callback();
		return;
	}
	var csvs = [];
	csvs.push(convertKKHeader(p)); // ヘッダ行はCSVで１件
	for(var i=0,li=dts.length,d;i<li;++i){
		d = dts[i];
//		Bit.log('process sid_appoint: '+ d.arc.appoint.sid);
		csvs.push(convertKK(p, d));
	}
	Bit.log('procdata count: '+ dts.length);
	makeCSV(p, csvs, callback);
};

// 協会けんぽ出力用はSIDを直接管理しとく
// SELECT sid_me FROM m_me_criterion where sid_morg=20006 and sid_criterion = 810; //協会けんぽ出力用を持っているコース
// call p_get_criterions(20006, 810); //協会けんぽ出力用で使用するm_criterionの全エントリ
var processSet = {
	p: {},
	store: new Bit.store.Mysql(),
	procs: [
		function(next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			Bit.nw.Data.Store.onComplete = function(err){
				if(err){
					Bit.log(err);
					next(err);
					return;
				}
				var sids = Bit.nw.Data.Store.mEorg.sids(true);
				Bit.util.Async.waterfall([
					function(_next){
							Bit.nw.Data.Store.loadMEorgEg(req.user.sid_morg, sids, function(){
								_next();
							});
					},
					function(_next){
						Bit.nw.Data.Store.loadMEorgEi(req.user.sid_morg, sids, function(){
							_next();
						});
					},
					function(_next){
						Bit.nw.Data.Store.loadMEorgEie(req.user.sid_morg, sids, function(){
							_next();
						});
					}
					],
				function(_err){
					next(_err);
				});
			};
			Bit.nw.Data.Store.exec(user.sid_morg, ['mEie', 'mEi', 'mEg', 'mEp', 'mOrg', 'mCriterion', 'mMeCriterion', 'mMeAttribute', 'tContract', 'tContractMeAttribute', 'mOpinionRankSet', 'mQualitative', 'mEorg', 'mUser']);
		},
//		function(next){
//			var p = processSet.p;
//			var req = p.req, res = p.res, config = p.config;
//			var user = req.user;
//			var sql = 'call p_get_criterions(?, ?);';
//			var prm = [user.sid_morg, config.outsource.sid_criterion];
//			esql.log(sql,prm);
////			processSet.store.keepAliveON(); // store.destroy()必須
//			var store = processSet.store;
//			store.query({
//				sql: sql,
//				params: prm,
//				success: function(err, rows, fields, time) {
//					Bit.log('time: '+ time +'ms');
//		//			var recs = rows, flds = fields; //SQLベタガキ用
//					var recs = rows[0], flds = rows[1]; //ストアドプロシージャ用
//					if(!esql.echeck(rows,sql,prm)){
//						var er = esql.create(esql);
//						next(er);
//					}else{
//						if(recs.length){
//							next(null, recs);
//						}else{ // コースなし
//							next(new Error('データなし'));
//						}
//					}
//				},
//				exception: function(err, rows){ // DBエラー
//					next(err);
//				}
//			});
//		},
//		function(recs, next){
//			Bit.log('record count: '+ recs.length);
//			var _time = Now();
//			var norm = Bit.nw.xmljson.config.m_criterion.xml_criterion;
//			var conv = null;
//			for(var i=0,li=recs.length,r;i<li;++i){
//				r = recs[i];
//				switch(r.s_exam){
//				case 1001: conv = norm.course; break;
//				case 1003: conv = norm.group; break;
//				case 1004: conv = norm.eitem; break;
//				case 1005: conv = norm.element; break;
//				}
//				to_json(r.xml_criterion, function(error, xml_json){
//					r.xml_criterion = Bit.nw.xmljson.normalizeJson(conv.json, xml_json);
//					if(!r.xml_criterion){ return; }
//					var b = r.xml_criterion.criterion;
//					if(b.structures && b.structures.structure && b.structures.structure.length){
//						var struc = b.structures.structure[0];
//						if(struc.epacks && struc.epacks.epack && struc.epacks.epack.length == 1){ if(!struc.epacks.epack[0].sid){ struc.epacks.epack.length = 0; } }
//						if(struc.egroups && struc.egroups.egroup && struc.egroups.egroup.length == 1){ if(!struc.egroups.egroup[0].sid){ struc.egroups.egroup.length = 0; } }
//						if(struc.eitems && struc.eitems.eitem && struc.eitems.eitem.length == 1){ if(!struc.eitems.eitem[0].sid){ struc.eitems.eitem.length = 0; } }
//						if(struc.elements && struc.elements.element && struc.elements.element.length == 1){ if(!struc.elements.element[0].sid){ struc.elements.element.length = 0; } }
//					}
//				});
//			}
//			Bit.nw.Data.Store.mCriterion.stock.setAll(recs);
//			Bit.nw.Data.Store.mCriterion.dataCache = recs;
//
//			Bit.log('time: '+ (Now().getTime() - _time.getTime()) +'ms');
//			next();
//		},
		function(next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var sql = 'SELECT sid_me FROM m_me_criterion where sid_morg=? and sid_criterion = ?;';
			var prm = [user.sid_morg, config.outsource.sid_criterion];
			esql.log(sql,prm);
			var store = processSet.store;
			store.query({
				sql: sql,
				params: prm,
				success: function(err, rows, fields) {
					//SQLベタガキ用
					var recs = rows, flds = fields;
					//ストアドプロシージャ用
//					var recs = rows[0], flds = rows[1];
					if(!esql.echeck(rows,sql,prm)){
						var er = esql.create(esql);
						next(er);
					}else{
						p.mes = [];
						for(var i=0,li=recs.length;i<li;++i){
							p.mes.push(recs[i].sid_me);
						}
						next();
					}
				},
				exception: function(err, rows){
					next(err);
				}
			});
		},
		function(next){
			var p = processSet.p;
			var req = p.req, res = p.res, config = p.config;
			var user = req.user;
			var prm = req.Request.params() || {};
			var ext = prm.extraction;
//			ext.from = '2016-08-10';
//			ext.to = '2016-08-14';
			var today = Now().format('yyyy-mm-dd');
			Bit.log('process dates: '+ ext.from +' - '+ ext.to);
			var storeEResults = new Bit.nw.cmp.store.EResults();
			storeEResults.data = { user: { sid_morg: user.sid_morg, sid: user.sid } };
			storeEResults.setStatus(3);
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
			var mes = p.mes;
			Bit.log('EResults count: '+ eresults.length);
			var ress = [];
			Bit.nw.Data.Store.mMe.data = { user: user };
			var storeEResult = new Bit.nw.cmp.store.EResult();
			Bit.util.Async.each(eresults, function(eresult, next_){
				var sid_appoint = eresult.appoint.sid;
				storeEResult.data = { user: user };
				storeEResult.getData(function(store, data){
					eresult.res = data;
					
					var res = eresult.res;
					if(mes.indexOf(res.sid_me) == -1){ // m_me_criterion にエントリがあるものだけ処理対象
						next_();
						return;
					}
					Bit.nw.Data.Store.mMe.setupGetListeners(function(mdl){
						ress.push({ eresult: res, memdl: mdl, appoint: eresult.appoint });
						next_();
					}, function(code, message){
						next_(new Error(message));
					});
					var mdl = Bit.nw.Data.Store.mMe.getModel(res.sid_me+'');
					if(mdl){
						ress.push({ eresult: res, memdl: mdl, appoint: eresult.appoint });
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
			for(var i=0,li=eresults.length,re,ap,k;i<li;++i){
				re = eresults[i];
				ap = re.appoint;
				k = null;
				if(ap.xml_xorg && ap.xml_xorg.orgs && ap.xml_xorg.orgs.org && ap.xml_xorg.orgs.org.length){
					k = Bit.find(ap.xml_xorg.orgs.org, function(v){
						return (v.s_org == 11 && v.n_org.substr(0, 2) == '01');  // 協会けんぽ
					});
				}
				if(!k){ continue; }
				
				var rmap = new Bit.nw.cmp.EcourseXmlMap({});
//				rmap.clear();
				// , sid_contract: re.appoint.appoint_me[0].sid_contract }); //2016-07-06 add jj 契約情報を追加
				rmap.setup(re.eresult.xml_me, { Store: Bit.nw.Data.Store, Model: re.memdl, CriterionKit: { value: config.outsource.sid_criterion } });
				
				var output = rmap.autoAprvProcess(ap.xml_examinee);
//				Bit.log('自動判定：'+ ap.dt_appoint.format('yyyy/mm/dd hh:nn') +' '+ ap.xml_examinee.examinee.name +' '+ re.memdl.get('name'));
//				Bit.log(JSON.stringify(output));
				
				p.ret.data.push({ arc: re, org: k, csmap: rmap, aprv: output });
				Bit.log('target sid_appoint: '+ re.appoint.sid);
			}
			makeCSVData(p, next);
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
