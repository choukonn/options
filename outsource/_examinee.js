/**
 * 外部受診者データインポート
 */
var to_json = Bit.nw.xmljson.to_json;
var to_xml= Bit.nw.xmljson.to_xml;
var _es = require('../../../node_modules/narwhal/core');

module.exports = {
	execIn: function(p, next){
		// p: {req, res, next, config, ret: { files: [] }, file, f, raw, rowIndex }
		var req = p.req, res = p.res, config = p.config, f = p.f;
		var r = f.map[p.rowIndex];
		var record = Bit.clone(r);
		var json_link = {};
		var esql = new _es(req,res);
		var texamid = null;
		//var record = Bit.clone(r[Bit.nw.serialize.plugin.MExaminee.prototype.DB]);

		// m_examinee 用レコード生成
		Bit.applyIf(record, {
			sid_morg: req.user.sid_morg,
			sid_upd: req.user.sid,
			dt_upd: Now().format('yyyy-mm-dd hh:nn:ss'),
			s_upd: 1
		});

		json_link = {
						'examinee': {
							'sid': null,
							'id': record[5],
							'name': record[0],
							'name-kana': record[1],
							'birthday': record[3],
							'sex': record[2],
							'bloodtype': null,
							'contact': {
								'zip1': record[6],
								'address1': record[7],
								'zip2': null,
								'address2': record[8],
								'zip3': null,
								'address3': null,
								'send_addr': record[7],
								'tel': record[9],
								'tel2': null,
								'tel3': null,
								'fax': record[10],
								'email': record[11],
							},
							'age-whenapo': null,
							'f_examinee': record[12],
							'multi-attr': null,
							'remarks': null,
							'ccard': {
								'no': null,
								'd_valid': null,
							},
						}
		};

		Bit.log(JSON.stringify(json_link));

		var xml_link = to_xml(json_link);
		// db
		var store1 = new Bit.store.Mysql();
		store1.query({
			sql: 'select sid,xml_examinee from m_examinee where sid_morg=? and id =?',
			params: [req.user.sid_morg,record[5]],

			success: function(err1, rows3, fields3){
				if(rows3.length == 0){
					var mode = 'PUT';
				}
				else{
					var mode = 'POST';
					to_json(rows3[0]['xml_examinee'], function (error, xml_json){
						xml_link = Bit.nw.xmljson.normalizeJson(Bit.nw.xmljson.config.xml_examinee.json, xml_json);
					});
					xml_link['examinee']['sid'] = rows3[0]['sid'];
					xml_link['examinee']['id'] = record[5];
					xml_link['examinee']['name'] = record[0];
					xml_link['examinee']['name-kana'] = record[1];
					xml_link['examinee']['birthday'] = record[3];
					xml_link['examinee']['sex'] = record[2];
					xml_link['examinee']['contact']['zip1'] = record[6];
					xml_link['examinee']['contact']['address1'] = record[7];
					xml_link['examinee']['contact']['address2'] = record[8];
					xml_link['examinee']['contact']['send_addr'] = record[7];
					xml_link['examinee']['contact']['tel'] = record[9];
					xml_link['examinee']['contact']['fax'] = record[10];
					xml_link['examinee']['contact']['email'] = record[11];
					xml_link['examinee']['f_examinee'] = record[12];

					xml_link = to_xml(xml_link);

					record.s_upd = '2';
					var texamid = rows3[0]['sid'];

				}
				var sql = 'CALL p_examinee(?,?,?,?,?,?,null);';
				var prm = [mode, req.user.sid_morg, record.sid_upd, texamid, record.s_upd,xml_link];
				esql.log(sql,prm);
				var store2 = new Bit.store.Mysql();
				store2.query({
					sql: sql,
					params: prm,
					success: function(err2, rows2, fields2){
						//								var recs = rows, flds = fields;
						if(err2){
							Bit.log(err2);
						}
						//ストアドプロシージャ用
						Bit.defer(function(){ p.nextProc(p, next, err2); });
					},
					exception: function(err2){
						Bit.log(err2);
						Bit.defer(function(){ p.nextProc(p, next, err2); });
					}
				});
			},
			exception: function(err2){
				Bit.log(err2);
				Bit.defer(function(){ p.nextProc(p, next, err2); });
			}
		});
	},
	execOut: function(p, next){
		// p: {req, res, next, config, ret: { files: [] }, file, f, raw, rowIndex }
		var req = p.req, res = p.res, config = p.config, f = p.f;
		var r = f.map[p.rowIndex];
		var record = Bit.clone(r[Bit.nw.serialize.plugin.MExaminee.prototype.DB]);
	}
};

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
