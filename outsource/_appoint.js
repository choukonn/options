/**
 * 外部受診結果データインポート
 */
var to_json = Bit.nw.xmljson.to_json;
var to_xml= Bit.nw.xmljson.to_xml;

module.exports = {
	execIn: function(p, next){
		// p: {req, res, next, config, ret: { files: [] }, file, f, raw, rowIndex }
		var req = p.req, res = p.res, config = p.config, f = p.f;
		var r = f.map[p.rowIndex];
		
		var recApp = Bit.clone(r[Bit.nw.serialize.plugin.TAppoint.prototype.DB]);
		var recExaminee = Bit.clone(r[Bit.nw.serialize.plugin.MExaminee.prototype.DB]);
		
		getStoreExaminee(p, recExaminee, function(err, record){ // id, name, addr, birthday 等から受診者を特定する。
			if(err){
				//m.examinee.xml_examinee.examinee.id
				insertExaminee(p, recExaminee, function(err2, record2){
					if(err2){
						p.nextProc(p, next, err);
						return;
					}
					postAppoint(p, record2.sid, recApp);
				});
			}
			postAppoint(p, record.sid, recApp, function(err3, record3){
				p.nextProc(p, next, err3);
			});
		});
	},
	execOut: function(p, next){
		// p: {req, res, next, config, ret: { files: [] }, file, f, raw, rowIndex }
		var req = p.req, res = p.res, config = p.config, f = p.f;
		var r = f.map[p.rowIndex];
	}
};

function getStoreExaminee(p, record, callback){
	var req = p.req, res = p.res, config = p.config, f = p.f;
	var sql = '', params = [];
	var id = record.xml_examinee.examinee.id;
	if(id){
		sql = 'select sid from m_examinee where ExtractValue(xml_examinee, "/root/examinee/id")=?';
		params = [id];
	}else{
		var name = record.xml_examinee.examinee.name;
		var birthday = record.xml_examinee.examinee.birthday;
		var sex = record.xml_examinee.examinee.sex;
		if(name && birthday && Bit.valid(sex)){
			sql = 'select sid from m_examinee where ExtractValue(xml_examinee, "/root/examinee/name")=? and ExtractValue(xml_examinee, "/root/examinee/birthday")=? and ExtractValue(xml_examinee, "/root/examinee/sex")=?';
			params = [name, (new Date(birthday)).format('yyyy/mm/dd'), sex];
		}
	}
	var store = new Bit.store.Mysql();
	store.query({
		sql: sql,
		params: params,
		success: function(err, row, fields){
			
		},
		exception: function(err){
			Bit.log(err);
			Bit.defer(function(){ callback(err_, record); });
		}
	});
}
function postAppoint(req, res, exsid, record, callback){
	var req = p.req, res = p.res, config = p.config, f = p.f;
	Bit.apply(record, {
		sid_examinee: exsid
	});
	var rec = Bit.clone(record);
	delete rec.xmlExaminee;
	delete rec.xmlXorg;
	delete rec.xmlCcard;
	Bit.apply(rec, {
		xml_examinee: record.xmlExaminee
//		, xml_xorg: record.xmlXorg, xml_ccard: record.xmlCcard
	});
	Bit.defer(function(){ callback(err, record); });
}
function insertExaminee(p, record, callback){
	var req = p.req, res = p.res, config = p.config, f = p.f;
	// m_examinee 用レコード生成
	Bit.applyIf(record, {
		sid_morg: req.user.sid_morg,
		sid_upd: req.user.sid,
		dt_upd: Now().format('yyyy-mm-dd hh:nn:ss'),
		s_upd: 1
	});
	// db
	var store3 = new Bit.store.Mysql();
	store3.query({
		sql: 'select sid_anum from auto_num where sid_morg=? and table_nm="m_examinee"',
		params: [req.user.sid_morg],
		success: function(err3, rows3, fields3){
			var num = rows3[0].sid_anum+1;
			
			var store2 = new Bit.store.Mysql();
			store2.query({
				sql: 'update auto_num set sid_anum = ? where sid_morg = ? and table_nm = "m_examinee"',
				params: [num, req.user.sid_morg],
				success: function(err2, rows2, fields2){
					record.xml_examinee.examinee.sid = num;
					var json = Bit.nw.xmljson.normalizeXml(Bit.nw.xmljson.config.xml_examinee.xml, record.xml_examinee);
					record.xml = to_xml(json);
					var sql = 'INSERT INTO m_examinee(sid_morg,sid_upd,dt_upd,s_upd,sid,xml_examinee,my_number)VALUES(?,?,?,?,?,?,null);';
					Bit.log(sql);
					
					var store = new Bit.store.Mysql();
					store.query({
						sql: sql,
						params: [record.sid_morg, record.sid_upd, record.dt_upd, record.s_upd, num, record.xml],
						success: function(err_, rows, fields) {
							//SQLベタガキ用
//							var recs = rows, flds = fields;
							if(err_){
								Bit.log(err_);
							}
							
							//TODO 団体への登録
							
							//ストアドプロシージャ用
							Bit.defer(function(){ callback(err_, record); });
						},
						exception: function(err_){
								Bit.log(err_);
								Bit.defer(function(){ callback(err_, record); });
						}
					});
				}
			});
		}
	});
}

//var makeMedExam = function(r){
//	var path = 'm.examinee.ccard.s_medexam.name.', no = 1, p = path + no, ret = [], d;
//	while(Bit.valid(r[p])){
//		var o = {};
//		o.name = r[p];
//		o.charge = {
//			examinee: {},
//			insurer: {}
//		};
//		d = r['m.examinee.ccard.s_medexam.charge.examinee.rate.'+ no];
//		if(Bit.valid(d)){
//			o.charge.examinee.rate = d;
//		}
//		d = r['m.examinee.ccard.s_medexam.charge.examinee.value.'+ no];
//		if(Bit.valid(d)){
//			o.charge.examinee.value = d;
//		}
//		d = r['m.examinee.ccard.s_medexam.charge.insurer.value-uplimit.'+ no];
//		if(Bit.valid(d)){
//			o.charge.insurer['value-uplimit'] = d;
//		}
//		ret.push(o);
//		p = path +(++no);
//	}
//	return ret;
//};
//module.exports = Bit.createClass(undefined, undefined,	{
//	init: function(config){
//		this.init.apply(this, arguments);
//	},
//	exec: function(req, res, next, config, ret){
//	}
//});
