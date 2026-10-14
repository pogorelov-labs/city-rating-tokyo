// ============================================================
//  ファイル名：search.js
// ============================================================

$(function(){
	Exports.Modules.Gallery.init();

	//検索ボタン押下
	$('#searchBtn').click(function(){
		// 検索入力がなければ検索しない
		if( $('select[name=cb-area] option:selected').val() == 'select' &&
			$('input[name=freeword]').val() == '' &&
			$('input[name=location]').val() == '') {
			return false;
		}

		//現在地からの検索の場合、ロケーション情報を取得
		var location_flag = $('input[name=location]').val();
		if (location_flag == 'on') {
			var ret = getPosition(function(status){
				if (status === true) {
					search_api();
				}
				else {
					alert($('.noresultGps').text());
					$('.noresultGps').fadeIn();
				}
			});
		}
		else {
			search_api();
		}

		return false;
	});

	//現在地からの検索ボタン押下
	$('#searchBtnLocation').click(function(){
		$('input[name=location]').val('on');
		return false;
	});
	//エリアから検索,やり直しボタン押下
	$('#searchBtnArea, .btn__reset--text').click(function(){
		$('input[name=location], input[name=lat], input[name=lng]').val('');
		return false;
	});
});

/*
* 検索プログラムへフォームデータを送信する
*/
function search_api() {

	var fdata = $("#searchform").serialize(); //フォームデータ
	var query_string = randam_string();

	$.ajax({
		type: 'POST',
		async: true,
		url: '../search.php?'+query_string,
		dataType: 'json',
		data: fdata,
	})
	.done(function(rdata_all, textStatus, jqXHR){
		try {
			var slang = $("#searchform > input[name='search-lang']").val();
			var rdata = rdata_all.rdata;
			var status = rdata_all.status;
			//画像情報の情報表示
			for (var i=0; i < rdata.length; i++) {

				//医療機関
				var sName = String(rdata[i].medical_institution);
				//住所
				var sAddress;
				if ('jpn' === slang) {
					sAddress = '〒' + String(rdata[i].postal_code) + ' ' + String(rdata[i].street_address);
				} else if ('eng' === slang) {
					sAddress = String(rdata[i].street_address) + ', ' + String(rdata[i].postal_code);
				} else if ('kor' === slang) {
					sAddress = '우편번호 ' + String(rdata[i].postal_code) + ' ' + String(rdata[i].street_address);
				} else if ('chc' === slang) {
					sAddress = '郵編 ' + String(rdata[i].postal_code) + ' ' + String(rdata[i].street_address);
				} else if ('chs' === slang) {
					sAddress = '邮编 ' + String(rdata[i].postal_code) + ' ' + String(rdata[i].street_address);
				}
				//電話番号
				var sTel = rdata[i].phone_number;
				//診療時間
				var sOpen = String(rdata[i].reception_time).replace(/★/g, '<br>');
				//WEBサイト
				var sWeb = [];
				var vWeb = {
					'jpn': ['日本語', '英語', ],
					'eng': ['Japanese', 'English', ],
					'kor': ['일본어', '영어', ],
					'chc': ['日文', '英語', ],
					'chs': ['日文', '英语', ],
				}
				var webanchor = function(v) {
					return v.replace(/(http:\/\/[\x21-\x7e]+|https:\/\/[\x21-\x7e]+)/gi, '<a href="$1" target="_blank">$1</a>');
				};
				if (rdata[i].w01) sWeb.push(webanchor(rdata[i].w01)+' ('+vWeb[slang][0]+')');
				if (rdata[i].w02) sWeb.push(webanchor(rdata[i].w02)+' ('+vWeb[slang][1]+')');
				if (rdata[i].w03) sWeb.push(webanchor(rdata[i].w03).replace(/★/g, '<br>'));
				//対応診療科と対応外国語
				var sLanguage = [];
				var sLanguageOther = '';
				if (rdata[i].d01) sLanguage.push(rdata[i].d01);
				if (rdata[i].d02) sLanguage.push(rdata[i].d02);
				if (rdata[i].d03) sLanguage.push(rdata[i].d03);
				if (rdata[i].d04) sLanguage.push(rdata[i].d04);
				if (rdata[i].d05) sLanguage.push(rdata[i].d05);
				if (rdata[i].d06) sLanguage.push(rdata[i].d06);
				if (rdata[i].d07) sLanguage.push(rdata[i].d07);
				if (rdata[i].d08) sLanguage.push(rdata[i].d08);
				if (rdata[i].d09) sLanguage.push(rdata[i].d09);
				if (rdata[i].d10) sLanguage.push(rdata[i].d10);
				if (rdata[i].d11) sLanguage.push(rdata[i].d11);
				if (rdata[i].d12) sLanguage.push(rdata[i].d12);
				if (rdata[i].d13) sLanguage.push(rdata[i].d13);
				if (rdata[i].d14) sLanguage.push(rdata[i].d14);
				if (rdata[i].d15) sLanguage.push(rdata[i].d15);
				if (rdata[i].d16) sLanguageOther = '<br>' + rdata[i].d16.replace(/★/g, '<br>');
				//利用可能なクレジット
				var sCredit = [];
				var sCreditOther = '';
				var vCredit = {
					'jpn': ['VISA', 'MASTER', 'AMEX', 'Diners Club', 'JCB', '中国銀聯', 'その他'],
					'eng': ['VISA', 'MASTER', 'AMEX', 'Diners Club', 'JCB', '中国銀聯', 'Others'],
					'kor': ['VISA', 'MASTER', 'AMEX', 'Diners Club', 'JCB', '은련카드', '기타'],
					'chc': ['VISA', 'MASTER', 'AMEX', 'Diners Club', 'JCB', '銀聯卡', '其他'],
					'chs': ['VISA', 'MASTER', 'AMEX', 'Diners Club', 'JCB', '银联卡', '其他'],
				}
				if (rdata[i].v01) sCredit.push(vCredit[slang][0]);
				if (rdata[i].v02) sCredit.push(vCredit[slang][1]);
				if (rdata[i].v03) sCredit.push(vCredit[slang][2]);
				if (rdata[i].v04) sCredit.push(vCredit[slang][3]);
				if (rdata[i].v05) sCredit.push(vCredit[slang][4]);
				if (rdata[i].v06) sCredit.push(vCredit[slang][5]);
				if (rdata[i].v07) sCredit.push(vCredit[slang][6]);
				if (rdata[i].v08) sCreditOther = '<br>' + rdata[i].v08.replace(/★/g, '<br>');
				//備考
				var sRemarks = String(rdata[i].remarks).replace(/★/g, '<br>');
				//JMIP対応
				var fJMIP = rdata[i].jmip !== '' ? 'visible' : 'hidden';
				//拠点的対応
				var fCategory = (rdata[i].base_hospital1 !== '' || rdata[i].base_hospital2 !== '') ? 'visible' : 'hidden';
				//緯度
				var sLat = parseFloat(rdata[i].latitude);
				//経度
				var sLng = parseFloat(rdata[i].longitude);

				//病院までの距離
				var sDistance = parseFloat(rdata[i].distance);
				var fDistance = ' style="display:none;"';
				if (!isNaN(sDistance)) {
					sDistance = sDistance.toFixed(1);
					if (slang === 'jpn') {
						sDistance = '（現在地から約' + sDistance + 'km）';
					} else if (slang === 'eng') {
						sDistance = '(About ' + sDistance + ' km from your current location)';
					} else if (slang === 'kor') {
						sDistance = '(현 지점에서 약 ' + sDistance + 'km)';
					} else if (slang === 'chc') {
						sDistance = '（距離目前地點約' + sDistance + 'km）';
					} else if (slang === 'chs') {
						sDistance = '（距离目前地点约' + sDistance + 'km）';
					}

					fDistance = '';
				}
				else {
					sDistance = '';
				}

				//map文字
				var sMap = 'Map';
				if (slang === 'jpn') {
					sMap = '地図';
				} else if (slang === 'kor') {
					sMap = '지도';
				} else if (slang === 'chc') {
					sMap = '地圖';
				} else if (slang === 'chs') {
					sMap = '地图';
				}

				$('#searchAreaFreeWord').append(
					'<div class="element"><section>' + 
					'<div class="naviSection__icn--category ' + fCategory + '">' + titles(slang, 7) + '</div>' + 
					'<div class="naviSection__icn--jmip ' + fJMIP + '">JMIP</div>' + 
					'<div class="naviSection__txt--location" ' + fDistance + '>' + sDistance + '</div>' + 
					'<h1>' + sName + '</h1>' + 
					'<div class="detail"><table><tbody>' + 
					'<tr><th>' + titles(slang, 1) + '</th><td class="btn__map">' + sAddress + 
					'<p class="btn__normal btn__normal--type04 pd8 fs1">' + 
					'<a href="https://www.google.co.jp/maps/place/' + sLat + '+' + sLng + '/@' + sLat + '+' + sLng + ',16z?hl=ja" target="_blank">' + sMap + '</a></p></td></tr>' + 
					'<tr><th>' + titles(slang, 2) + '</th><td>' + sTel + '</td></tr>' + 
					'<tr><th>' + titles(slang, 3) + '</th><td>' + sOpen + '</td></tr>' + 
					'<tr><th>' + titles(slang, 4) + '</th><td>' + sWeb.join('<br>') + '</td></tr>' + 
					'<tr><th>' + titles(slang, 5) + '</th><td>' + sLanguage.join('<br>') + sLanguageOther + '</td></tr>' + 
					'<tr><th>' + titles(slang, 6) + '</th><td>' + sCredit.join(',') + sCreditOther + '</td></tr>' + 
					'</tbody></table></div><div class="map__wrap">&nbsp;</div></section></div>');
			}
			// search result is none(by area search)
			if (status == 'all') {
				$('.noresult').fadeIn();
			}
			// search result is none(by freeword search)
			else if(rdata.length == 0) {
				$('.noresultFreeWord').fadeIn();
			}
			// loading off & scroll
			$("html,body").delay(500).animate({scrollTop:$('.naviSection02').offset().top}, 700, 'swing', function(){
				$('#searchBtn').removeClass('btn__normal--loading');
			});
		} catch (e) {
			_system_error(e);
		}
	})
	.fail(function(jqXHR, textStatus, errorThrown){
		_system_error(errorThrown);
	});

}

function randam_string(length) {
	if(typeof length === 'undefined') length = 8;

	var character = 'abcdefghijklmnopqrstuvwxyz0123456789';
	var result = "";
	for(var i = 0; i < length; i++) {
		result += character[Math.floor(Math.random() * character.length)];
	}
	return result;
}

function titles(slang, num) {
	if(typeof slang === 'undefined') slang = 'jpn';
	if(typeof num === 'undefined') num = 1;

	var array1 = ['住所', '電話番号', '受付時間', 'ウェブサイト', '診療科および言語', '利用可能なクレジットカード', '拠点的な医療機関'];
	var array2 = ['Address', 'Tel', 'Hours of Reception', 'Web site', 'Medical departments & Languages', 'Available credit card', 'Base medical institution'];
	var array3 = ['주소', '전화번호', '접수 시간', '웹사이트', '진료과 및 언어', '이용 가능한 신용카드', '거점적인 의료기관'];
	var array4 = ['地址', '電話號碼', '受理時間', '網站', '科室及語言', '可使用的信用卡', '據點醫療機構'];
	var array5 = ['地址', '电话号码', '受理时间', '网站', '科室及语言', '可使用的信用卡', '据点医疗机构'];
	if (slang == 'jpn') return array1[num - 1];
	if (slang == 'eng') return array2[num - 1];
	if (slang == 'kor') return array3[num - 1];
	if (slang == 'chc') return array4[num - 1];
	if (slang == 'chs') return array5[num - 1];
}

var getPosition = function(callback){
	if (navigator.geolocation) {
		// 現在の位置情報取得を実施
		navigator.geolocation.getCurrentPosition(
		// 位置情報取得成功時
		function (position) {
			$('input[name=lat]').val(position.coords.latitude);
			$('input[name=lng]').val(position.coords.longitude);
			callback(true);
		},
		// 位置情報取得失敗時
		function (error) {
			switch(error.code) {
			case 1:
			case 2:
			case 3:
				break;
			}
			callback(false);
		});
	} else {
		callback(false);
	}
}

function _system_error(e) {
	//$('.noresult').fadeIn();
	console.log(e);
}
