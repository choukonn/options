/**
 * Y+予約CSVデータインポート
 */
var _es = require('../../../node_modules/narwhal/core');
var to_json = Bit.nw.xmljson.to_json;
var to_xml= Bit.nw.xmljson.to_xml;

module.exports = {
	execIn: function(p, next){
		// p: {req, res, next, config, ret: { files: [] }, file, f, raw, rowIndex }
		var req = p.req, res = p.res, config = p.config, f = p.f;
		var sid_morg = req.user.sid_morg;
		var sid_upd	= req.user.sid;
		var esql = new _es(req,res);
		// -- CSVレイアウト
		// 0 予約番号,1 お名前（漢字）,2 お名前（かな）, 3 性別, 4 生年月日, 5 メールアドレス, 6 郵便番号, 7 都道府県,
		// 8 市区町村名, 9 番地以降, 10 建物名, 11 ご連絡先, 12 その他ご連絡先, 13 健診コース, 14 保険証番号, 15 保険証記号,
		// 16 所属, 17 その他申し送り事項, 18 企業名, 19 第一希望, 20 第二希望, 21 第三希望, 22 受診者ID, 23 受診日
		var row = f.map[p.rowIndex];
		var r = {};
		var json_link = {};
		var json_app = {};
		var json_inteview = {};
		Bit.log(row);

		// 項目セット
		r.sid_morg = sid_morg; 		// 医療機関SID
		r.sid_upd = sid_upd;   		// 更新者SID
		r.vc_appoint_no = row[0]; 	// 予約番号
		r.name = row[1];          	// お名前(漢字)
		r.kana = row[2];		  	// お名前(かな)
		r.sex = row[3];			  	// 性別
		r.birthday = row[4];	  	// 生年月日
		r.mail = row[5];          	// メールアドレス
		r.zip = row[6];			  	// 郵便番号
		r.adr1 = row[7];          	// 都道府県
		r.adr2 = row[8];		  	// 市区町村名
		r.adr3 = row[9];		  	// 番地以降
		r.adr4 = row[10];		  	// 建物名
		r.contact_tel = row[11]; 	// ご連絡先
		r.contact2_tel = row[12];	// その他ご連絡先
		r.course = row[13];			// 健診コース
		r.n_examinee = row[14];		// 保険証番号
		r.s_examinee = row[15];		// 保険証記号
		r.belongs = row[16];		// 所属
		r.send_off = row[17];		// その他申送り事項
		r.company = row[18];		// 企業名
		r.dt_first_date = row[19];	// 第一希望
		r.dt_second_date = row[20];	// 第二希望
		r.dt_third_date = row[21];  // 第三希望
		r.examinee_id = row[22];	// 受診者ID
		r.dt_appoint = row[23];		// 受診日

		json_link = {xml:{
						'vc_appoint_no': {caption: '予約番号', value:r.vc_appoint_no},
						'name-kana': {caption: 'お名前(かな)', value:r.kana},
						'name': {caption: 'お名前(漢字)', value:r.name},
						'sex': {caption: '性別', value:r.sex},
						'birthday': {caption: '生年月日', value:r.birthday},
						'email': {caption: 'メールアドレス', value:r.mail},
						'contact-address-zip': {caption: '郵便番号', value:r.zip},
						'contact-address-adr1': {caption: '都道府県', value:r.adr1},
						'contact-address-adr2': {caption: '市区町村名', value:r.adr2},
						'contact-address-adr3': {caption: '番地以降', value:r.adr3},
						'contact-address-adr4': {caption: '建物名', value:r.adr4},
						'contact-tel': {caption: 'ご連絡先', value:r.contact_tel},
						'contact2-tel': {caption: 'その他ご連絡先', value:r.contact2_tel},
						'course': {caption: '健診コース', value:r.course},
						'no': {caption: '保険証番号', value:r.n_examinee},
						'symbol': {caption: '保険証記号', value:r.s_examinee},
						'belongs': {caption: '所属', value:r.belongs},
						'send_off': {caption: 'その他申送り事項', value:r.send_off},
						'first_date': {caption: '第一希望', value:r.dt_first_date},
						'second_date': {caption: '第二希望', value:r.dt_second_date},
						'third_date': {caption: '第三希望', value:r.dt_third_date}
						  }};

		Bit.log(JSON.stringify(json_link));

		var xml_link = to_xml(json_link).replace('<root>', '').replace('</root>', ''); // root タグがはいるので除去
		xml_link = '<?xml version="1.0" encoding="utf-8"?>\r\n' + xml_link;

		r.xml_linkage_appoint_info = xml_link;
		r.xml_appoint_info = null;
		r.xml_interview_info = null;
		r.xml_stress_info = null;
		r.remarks = null;

		var sql = 'call p_mlg_post_appoint_infos(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);';
		var prm = [r.sid_morg, r.sid_upd, r.vc_appoint_no, r.dt_appoint, r.dt_first_date, r.dt_second_date, r.dt_third_date,
					r.examinee_id, r.name, r.kana, r.mail, r.xml_linkage_appoint_info, r.xml_appoint_info,
					r.xml_interview_info, r.xml_stress_info, r.remarks ];

		esql.log(sql,prm);

		var store = new Bit.store.Mysql();
		store.query({
			sql: sql,
			params: prm,
			success: function(err_, rows, fields) {
				if(err_){
					Bit.log(err_);
				}
				//ストアドプロシージャ用
				Bit.defer(function(){ p.nextProc(p, next, err_); });
			},
			exception: function(err_){
				Bit.log(err_);
				Bit.defer(function(){ p.nextProc(p, next, err_); });
			}
		});
	}
};

