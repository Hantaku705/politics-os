'use strict';
// Public, dated examples only. Null means not established, never a score of zero.
const SOURCES = {
  debate: { title: '2022年3月10日 質疑掲載（塩川鉄也氏の公式サイト）', url: 'https://www.shiokawa-tetsuya.jp/wp/?p=8455' },
  inoue: { title: '2024年12月18日 参議院政治改革特別委員会（国会会議録）', url: 'https://kokkai.ndl.go.jp/simple/detail?minId=121614575X00220241218' },
  bill: { title: '第216回国会 参法第2号 審議経過（衆議院）', url: 'https://www.shugiin.go.jp/Internet/itdb_gian.nsf/html/gian/keika/1DDD84E.htm' },
  profile: { title: '金子恭之氏 議員プロフィール（衆議院）', url: 'https://www.shugiin.go.jp/Internet/itdb_giinprof.nsf/html/profile/123.html' },
  law: { title: '政党助成法（e-Gov法令検索）', url: 'https://laws.e-gov.go.jp/law/406AC0000000005' },
  votes: { title: '本会議投票結果（参議院）', url: 'https://www.sangiin.go.jp/japanese/touhyoulist/touhyoulist.html' }
};
const PEOPLE = [
  { id:'kaneko', name:'金子 恭之', party:'自由民主党', role:'当時の総務大臣として答弁', date:'2022-03-10', region:'熊本県', regionNote:'地域分類：確認時の衆議院プロフィールは熊本県第4区。記録当時の役職と区別しています。', stance:'制度の意義を肯定', stanceKey:'maintain', transparency:'現行制度で対応と答弁', transparencyDetail:'監査の十分性を問う質疑で、現行制度で対応しているとの立場を説明。個別の監査強化法案への反対票を意味しません。', action:'国会で答弁', outcome:null, outcomeLabel:'この記録では確認できず', stage:1, summary:'政党の活動経費を社会全体で負担する制度として、その意義を説明。', reason:'政党本位の政治と、民主主義を社会全体で支える仕組みとして説明しています。', sources:['debate'], vote:'この質疑は採決ではありません。', result:'この答弁だけから、制度改正や社会への効果は確認できません。', timeline:[['2022.03.10','制度の意義と監査の現状について、国会で答弁。']] },
  { id:'shiokawa', name:'塩川 鉄也', party:'日本共産党', role:'衆議院で質問', date:'2022-03-10', region:null, regionNote:'この試作では地域別の所属情報を未収録。県別集計には含めません。', stance:'制度の廃止を主張', stanceKey:'abolish', transparency:'監査の十分性を追及', transparencyDetail:'使途等報告書の監査や政治資金監査の範囲を問い、支出の妥当性を検証できるかを追及。質問した事実と、制度改正の成立は別に扱います。', action:'国会で質問', outcome:null, outcomeLabel:'この記録では確認できず', stage:1, summary:'監査の対象と権限の限界を問い、政党助成制度の廃止を主張。', reason:'監査の範囲では適正な支出の説明が十分にならないとして、制度の問題を指摘しています。', sources:['debate'], vote:'この質疑は採決ではありません。', result:'この質問だけから、監査制度が改正されたとは判断できません。', timeline:[['2022.03.10','監査の対象・権限について質問。制度廃止を主張。']] },
  { id:'inoue', name:'井上 哲士', party:'日本共産党', role:'参議院で廃止法案を発議', date:'2024-12-18', region:null, regionNote:'この試作では地域別の所属情報を未収録。県別集計には含めません。', stance:'制度の廃止を提案', stanceKey:'abolish', transparency:'この記録では未評価', transparencyDetail:'今回収録した記録は制度廃止法案に関するものです。透明化の各論に対する立場は、別の法案・発言を確認してから追加します。', action:'廃止法案を発議', outcome:false, outcomeLabel:'対象法案は審査未了', stage:2, summary:'政党助成法の廃止法案を発議し、国会で趣旨を説明。対象法案は審査未了。', reason:'政党助成制度を廃止する法案の発議者として、趣旨を説明しています。', sources:['inoue','bill'], vote:'対象の廃止法案は審査未了。「他の議員が反対票を投じて否決」とは分類しません。', result:'第216回国会・参法第2号は審査未了。法案の成立という成果には到達していません。社会への影響や他の活動の成果は未測定です。', timeline:[['2024.11.28','第216回国会に政党助成法の廃止法案を提出。'],['2024.12.18','発議者として委員会で法案の趣旨を説明。'],['第216回国会 終了時','審査未了。対象法案は成立に至らず。']] }
];
const PREFECTURES = '北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split(' ');
const state = { view:'people', search:'', stance:'all', sort:'name', region:'東京都', party:'all' };
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const source = key => `<a class="source-link" href="${SOURCES[key].url}" target="_blank" rel="noopener noreferrer">${SOURCES[key].title} ↗</a>`;
const tag = (text, cls='gray') => `<span class="tag ${cls}">${esc(text)}</span>`;
const stanceClass = p => p.stanceKey === 'maintain' ? 'dark' : 'purple';

function card(p){return `<article class="person-card"><div class="person-top"><span class="monogram" aria-hidden="true">${p.name.slice(0,1)}</span><div><h3>${p.name}</h3><p>${p.party} · ${p.date.replaceAll('-','.')}</p></div></div><div class="record-row"><span>制度への立場</span>${tag(p.stance,stanceClass(p))}</div><div class="record-row"><span>透明化・監査</span><span>${p.transparency}</span></div><div class="record-row"><span>確認した行動</span><strong>${p.action}</strong></div><div class="record-row"><span>制度の変化</span>${tag(p.outcomeLabel,p.outcome===false?'amber':'gray')}</div><p>${p.summary}</p><button data-person="${p.id}" aria-label="${p.name}の記録を開く">根拠と経過を見る <span>↗</span></button></article>`;}

function renderIssues(){
  $('#view').innerHTML = `<div class="issue-layout"><article class="feature-card"><div class="card-kicker"><span>01 — 政治のお金</span>${tag('事例収録中','dark')}</div><h3>政党交付金</h3><p class="description">税金で、政党の活動を支える仕組み。<br>制度を続けるか。そして、使い道をどう確かめるか。</p><div class="axes"><div class="axis"><span>AXIS 01</span><strong>制度への立場</strong><p>維持・廃止・変更への主張と行動</p></div><div class="axis"><span>AXIS 02</span><strong>お金の透明性</strong><p>公開・監査への発言と行動</p></div></div><div class="card-footer"><span>3人の記録 · 2022 / 2024年</span><button class="card-button" data-action="issue">論点と記録を開く ↗</button></div></article><div class="side-stack"><article class="mini-card"><span class="eyebrow">COMING INTO FOCUS</span><h3>調査研究広報滞在費</h3><p>議員1人に月100万円。2025年8月分から使途報告・残額返還が義務に（初回公開は2026年11月30日まで）。</p><button data-action="money">公費の内訳と見方を見る ↗</button></article><article class="mini-card"><span class="eyebrow">COMING INTO FOCUS</span><h3>立法事務費・交通費</h3><p>立法事務費は月65万円を会派に交付（使途の公開義務なし）。JRパス・航空券は議員別の利用額が分からない。</p><button data-action="money">公費の内訳と見方を見る ↗</button></article></div></div><p class="notice">制度への賛否と、不正の有無は別です。このサイトでは、発言・採決・制度の結果をそれぞれの根拠に結び付けます。</p><h3 class="subheading">政党交付金に、どう向き合った？</h3><div class="person-list">${PEOPLE.map(card).join('')}</div>`;
}
// ---- Real roster: all current Diet members (data/members.json) ----
const DB = { members: [], meta: null, ready: false, error: null };
const R = { search:'', houses:new Set(), kaiha:new Set(), election:new Set(), sort:'kana', shown:30, pref:null, block:null, rk:{unit:'person',metric:'action',order:'desc',houses:new Set(['衆議院','参議院']),kaiha:new Set(),side:new Set(['与党','野党','不明']),band:new Set(),longGov:false,shown:100} };
const HOUSES = ['衆議院','参議院'];
const ELECTIONS = ['小選挙区','選挙区','比例'];
const num = v => v==null ? null : Number(v);
const fmtCount = m => m.activityStatus==='homonym' ? '要確認（同姓同名）' : m.speeches==null ? '未取得' : `${m.speeches}件`;
const kaihaKey = m => `${m.house}|${m.kaiha}`;
function median(a){if(!a.length)return null;const s=[...a].sort((x,y)=>x-y),h=s.length>>1;return s.length%2?s[h]:Math.round((s[h-1]+s[h])/2);}
function kokkaiUrl(m){const p=DB.meta?.activityPeriod||{};return `https://kokkai.ndl.go.jp/api/speech?${new URLSearchParams({speaker:m.speakerQuery,from:p.from||'',until:p.until||'',maximumRecords:'100'})}`;}
function seat(m){return m.electionType==='比例'?m.block:`${m.district}${m.house==='衆議院'?'区':''}（${m.electionType}）`;}
// seat with the election type explained (tap the dotted word)
function seatHtml(m){const t=esc(seat(m));if(t.includes('小選挙区'))return t.replace('小選挙区',term('小選挙区'));if(t.includes('比例'))return t.replace('比例',term('比例代表','比例'));return t;}
function periodLabel(){const p=DB.meta?.activityPeriod;return p?`${p.from.replaceAll('-','.')}〜${p.until.replaceAll('-','.')}`:'';}

async function loadData(){
  try{
    const [m,meta,map,pl]=await Promise.all([fetch('data/members.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}),fetch('data/meta.json').then(r=>r.json()),fetch('data/japan-map.json').then(r=>r.ok?r.json():null).catch(()=>null),fetch('data/pledges.json').then(r=>r.ok?r.json():null).catch(()=>null)]);
    DB.members=m;DB.meta=meta;DB.map=map;DB.pledges=pl;computeScores(m);DB.ready=true;renderStats();
    R.houses=new Set(HOUSES);R.kaiha=new Set(m.map(kaihaKey));R.election=new Set(ELECTIONS);R.rk.kaiha=new Set(m.map(kaihaKey));R.rk.band=new Set(m.map(bandKey));
  }catch(e){DB.error=String(e);}
  if(['people','parties','regions','rankings','government','money','rules'].includes(state.view))setView(state.view,false);
}
function renderStats(){const el=$('#stats');if(!el)return;const ms=DB.members,pp=ms.filter(m=>m.pp&&m.pp.n!=null),n=pp.reduce((a,m)=>a+m.pp.n,0),sh=ms.filter(m=>m.house==='衆議院').length;
  const v=[[`${ms.length}<small>人</small>`,`衆議院 ${sh}・参議院 ${ms.length-sh}`],[`${pp.length}<small>人</small>`,`点数が出る人 ${ms.filter(m=>specVal(m)!=null).length}人`],[`${n.toLocaleString()}<small>こ</small>`,'本人の選挙公報から'],[esc(periodLabel()),`データ入手日 ${esc(DB.meta.fetchedAt||'')}`]];
  el.querySelectorAll('dd').forEach((d,i)=>{d.innerHTML=`${v[i][0]}<span>${v[i][1]}</span>`;});}
function waitView(){if(DB.error){$('#view').innerHTML=`<div class="empty"><strong>名簿データを読み込めませんでした</strong><p>時間をおいて再読み込みしてください。（${esc(DB.error)}）</p></div>`;return true;}if(!DB.ready){$('#view').innerHTML=`<div class="empty"><strong>名簿を読み込み中…</strong></div>`;return true;}return false;}


// ---- Per-axis scores (0-100). score = share of members with a strictly smaller value. No total score. ----
const BLOCK_PREFS={'北海道':['北海道'],'東北':['青森県','岩手県','宮城県','秋田県','山形県','福島県'],'北関東':['茨城県','栃木県','群馬県','埼玉県'],'南関東':['千葉県','神奈川県','山梨県'],'東京':['東京都'],'北陸信越':['新潟県','富山県','石川県','福井県','長野県'],'東海':['岐阜県','静岡県','愛知県','三重県'],'近畿':['滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県'],'中国':['鳥取県','島根県','岡山県','広島県','山口県'],'四国':['徳島県','香川県','愛媛県','高知県'],'九州':['福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県']};
function rankPrefs(m){if(m.house==='衆議院'&&m.electionType==='比例'){const k=Object.keys(BLOCK_PREFS).find(b=>(m.block||'').includes(b));return k?BLOCK_PREFS[k]:[];}return m.electionType==='比例'?[]:(m.prefectures||[]);}
const speechVal=m=>m.activityStatus==='homonym'||m.speeches==null?null:m.speeches;
function scorer(vals){const s=vals.filter(v=>v!=null).sort((a,b)=>a-b),n=s.length;return v=>{if(v==null)return null;let lo=0,hi=n;while(lo<hi){const mid=(lo+hi)>>1;if(s[mid]<v)lo=mid+1;else hi=mid;}return n>1?Math.round(lo/(n-1)*100):0;};}
const meetVal=m=>m.activityStatus==='homonym'||!m.sp?null:m.sp.meet;
const restVal=m=>m.activityStatus==='homonym'||!m.sp?null:m.sp.rest;
const leadVal=m=>m.bills?m.bills.lead:null;
const passVal=m=>m.bills?m.bills.passed:null;
function rankInfo(ms,get){const v=ms.map(get).filter(x=>x!=null),cnt=new Map();for(const x of v)cnt.set(x,(cnt.get(x)||0)+1);const max=v.length?Math.max(...v):0;return m=>{const x=get(m);return x==null?null:{rank:1+v.filter(y=>y>x).length,tie:cnt.get(x),n:v.length,max};};}
const qVal=m=>m.q==null?null:m.q;
const specVal=m=>m.pp&&m.pp.spec!=null?m.pp.spec:null;  // 公約の具体性 0-100 (pipeline/build_records.py)
const bandKey=m=>m.band||'参議院（当選回数の帯なし）';
const longGov=m=>(m.govMonths||0)>=6;
const presidingOnly=m=>!!(m.sp&&m.sp.presiding>0&&m.sp.meet===0);
// reason a member is left out of peer comparison and the default ranking (null = compared normally)
const outOfCmp=m=>longGov(m)?'政府側の在任が長い':presidingOnly(m)?'議長・副議長としての発言のみ':null;
const peerKey=m=>m.side==='不明'?null:`${m.house}｜${m.side}${m.band?`｜${m.band}`:''}`;
function dataLine(){const r=DB.meta?.records||{};return `データ入手日 ${esc(DB.meta?.fetchedAt||'')}／発言 ${esc(periodLabel())}／法律案 第${esc(r.billSessions?.[0]||'')}〜${esc(r.billSessions?.[1]||'')}回／質問主意書 第${esc((r.questionSessions||[])[0]||'')}〜${esc((r.questionSessions||[]).slice(-1)[0]||'')}回`;}
function computeScores(ms){
  const sc=scorer(ms.map(meetVal));
  for(const m of ms)m.score={action:sc(meetVal(m)),spec:specVal(m)};
  const RI={action:rankInfo(ms,m=>m.score.action),spec:rankInfo(ms,specVal),meet:rankInfo(ms,meetVal),rest:rankInfo(ms,restVal),lead:rankInfo(ms,leadVal),passed:rankInfo(ms,passVal)};
  RI.q=rankInfo(ms,qVal);
  for(const m of ms){m.rk={};for(const k in RI)m.rk[k]=RI[k](m);const a=m.rk.action;Object.assign(m.score,{actionRank:a?.rank,actionTie:a?.tie,actionN:a?.n});const s2=m.rk.spec;Object.assign(m.score,{specRank:s2?.rank,specTie:s2?.tie,specN:s2?.n});}
  // peer groups (same house x ruling/opposition x term band), excluding long-serving government members
  const groups=new Map();for(const m of ms){const k=peerKey(m);if(!k||outOfCmp(m))continue;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(m);}
  for(const [k,g] of groups){const PI={action:rankInfo(g,x=>x.score.action),spec:rankInfo(g,specVal),meet:rankInfo(g,meetVal),rest:rankInfo(g,restVal),lead:rankInfo(g,leadVal),passed:rankInfo(g,passVal),q:rankInfo(g,qVal)};
    const med={spec:median(g.map(specVal).filter(v=>v!=null)),meet:median(g.map(meetVal).filter(v=>v!=null)),rest:median(g.map(restVal).filter(v=>v!=null)),lead:median(g.map(leadVal).filter(v=>v!=null)),passed:median(g.map(passVal).filter(v=>v!=null)),q:median(g.map(qVal).filter(v=>v!=null))};
    for(const m of g){m.peer={key:k,n:g.length,med,rk:{}};for(const x in PI)m.peer.rk[x]=PI[x](m);}}
}
const rankText=(rank,n,tie,zero)=>zero?`${n}人中 ${tie}人が0（順位なし）`:`${n}人中${rank}位${tie>1?`（同率${tie}人）`:''}`;
function scoreBar(score,rank,n,na,tie){
  if(score==null)return `<div class="axis-score"><div class="bar na" role="img" aria-label="未評価"></div><small>未評価・${esc(na)}</small></div>`;
  return `<div class="axis-score"><div class="bar" role="img" aria-label="${score}点（100点中）"><i style="width:${Math.max(score,1)}%"></i></div><small><b>${score}点</b> · ${rankText(rank,n,tie,score===0)}</small></div>`;
}
const SCORE_NA={pledge:'公約は件数のみ（実現の判定前）',transp:'透明性の判定基準が未確定'};
function actionNa(m){return m.activityStatus==='homonym'?'同姓同名で発言を確定できない':'発言の記録が未取得';}
function countBar(val,info,unit,na){
  if(val==null||!info)return `<div class="axis-score"><div class="bar na" role="img" aria-label="未評価"></div><small>未評価・${esc(na)}</small></div>`;
  const w=info.max?Math.round(val/info.max*100):0;
  return `<div class="axis-score"><div class="bar count" role="img" aria-label="${val}${unit}（最多${info.max}${unit}）"><i style="width:${val?Math.max(w,2):0}%"></i></div><small><b>${val}${unit}</b> · ${rankText(info.rank,info.n,info.tie,val===0)} · 最多 ${info.max}${unit}</small></div>`;
}
const partialTerm=m=>m.house==='衆議院'&&/^1(?!\d)/.test(String(m.terms||''));
function activityNote(m){
  if(m.activityStatus==='homonym')return '';
  const sp=m.sp||{},ls=m.lastSpeech;
  const notes=[];
  if(sp.presiding&&!sp.meet)notes.push(`この期間の発言は議長・副議長として議事を進めた ${sp.presiding}回のみです。議長・副議長は慣例で質問しないため、努力の点数と順位の比較から外しています。`);
  if(sp.chair&&!sp.meet&&!sp.presiding)notes.push(`この期間の発言は、委員長などとして議事を進めた会議（${sp.chair}回）のみです。議事の進行は点数に含めていません。`);
  if(m.gov&&!sp.gov&&!m.gov.former)notes.push(`首相官邸の名簿では現在「${esc(m.gov.posts[0])}」です。この期間の会議録に政府側としての答弁はまだありません（就任直後などのため）。`);
  if(sp.gov&&!sp.meet)notes.push(`この期間の発言は政府側（大臣など）としての ${sp.gov}回のみです。努力の点数は政府側の発言を除いて数えています。`);
  if(!m.speeches)notes.push(ls?`この期間の会議録に発言はありません。会議録で確認できた直近の発言（集計終了日以前）：${esc(ls.date)} ${esc(ls.house)} ${esc(ls.meeting)}${ls.position?`（${esc(ls.position)}）`:''}。`:'この期間の会議録に発言はありません（集計終了日以前の会議録にも確認できず）。');
  if(partialTerm(m))notes.push('衆議院議員としての在職は2026年2月の総選挙からで、集計期間の一部です。');
  return notes.length?`<p class="member-note">${notes.join('<br>')}</p>`:'';
}
// 3 measures: ① 公約の具体性 (0-100) ② 進捗率 (preparing) ③ 努力 (0-100). Never summed.
const SPEC_CK=[['t','何を'],['a','どうする'],['dl','いつまでに'],['ms','どこまで']];
function specNaText(m){const x=m.pp;if(!x)return 'まだ調べられていません';if(x.n==null){const w=x.why||'';return /比例/.test(w)?'比例代表で当選。本人の選挙公報がありません':/公開が終了/.test(w)?'選挙公報の公開が終わっています':/取得できず/.test(w)?'選挙公報を取得できませんでした':'選挙公報から読み取れませんでした';}if(x.n<3)return `公約が${x.n}こで、3こ未満のため点数なし`;return 'まだ判定していません';}
const PROGRESS_NA='約束が国会でどこまで進んだかを、いま調べています';
function scorePanel(m){const sc=m.score||{};return `<div class="score-panel"><div class="score-panel-head"><span class="eyebrow">3つの物差し（足し合わせません）</span><button type="button" class="score-how" data-action="score-method">点数の決め方</button></div>
  <div class="score-line"><span>① 公約の具体性</span>${scoreBar(sc.spec,sc.specRank,sc.specN,specNaText(m),sc.specTie)}</div>
  <div class="score-line"><span>② 進捗率</span>${scoreBar(null,0,0,'準備中。'+PROGRESS_NA)}</div>
  <div class="score-line"><span>③ 努力</span>${scoreBar(sc.action,sc.actionRank,sc.actionN,actionNa(m),sc.actionTie)}</div>
  <div class="score-line ref"><span>参考：法律になった数</span>${countBar(passVal(m),m.rk?.passed,'件','法案の記録が未取得')}</div></div>`;}
function openScoreMethod(){if(!DB.meta)return;const r=DB.meta.records||{};openDialog(`<h2 class="dialog-title" id="dialog-title">点数の決め方</h2><p class="dialog-sub">3つの物差しで見ます。3つは足し合わせず、合計点は出しません。</p>
<section class="dialog-section"><h3>① 公約の具体性（0〜100点）</h3><ul>
<li>何を見るか：あとで確かめられる約束をしているか</li>
<li>元データ：本人の${term('選挙公報')}に書かれた「これからやる」約束</li>
<li>公約1こごとに4つチェックします（1つ1点、4点満点）
<ul><li>何を：対象がはっきりしている</li><li>どうする：やることが書いてある</li><li>いつまでに：期限がある</li><li>どこまで：数値や達成の条件がある</li></ul></li>
<li>点数 ＝ 全公約の平均点 ÷ 4 × 100</li>
<li>公約が3こ未満の人は、点数を出さずに数だけ表示します</li>
<li>${term('比例代表')}だけで当選した人は、本人の公報がないため「対象外」です</li></ul>
<details class="more"><summary>くわしく（AIの判定について）</summary><ul><li>公報の画像から公約の文をAIが抜き出し、4つのチェックもAIが文の文字だけで判定しました。推測では補っていません。</li><li>無作為に選んだ50件を人が確かめたところ、47件（94%）で判定が一致しました。食い違った3件は、AIが「どうする」を厳しめに判定したものです（例：「憲法改正の早期発議」）。</li><li>「推進」「充実」「強化」「取り組む」だけの文は「どうする」に入れません。</li><li>公約の数が多いだけでは点は上がりません。政策の良し悪しは見ていません。</li></ul></details></section>
<section class="dialog-section"><h3>② 進捗率（%）</h3><ul>
<li>何を見るか：約束したことが、どこまで進んだか</li>
<li>公約1こごとに、どこまで進んだかを4段階で判定します
<ul><li>0 言った：公約がある</li><li>1 動いた：関係する質問・法案提出・修正案がある</li><li>2 通った：関係する法案が${term('成立')}した</li><li>3 効いた：施行されて、数字で変化が確認できた</li></ul></li>
<li>出す数字は2つです
<ul><li>アクション率 ＝ 段階1以上の数 ÷ 公約の数</li><li>実現率 ＝ 段階2以上の数 ÷ 公約の数</li></ul></li>
<li>必ず数と率を並べて表示します（例：12こ中3こ 25%）</li>
<li>公約が5こ未満の人は、順位に入れません</li>
<li>公約と逆の投票をした場合は「逆行」として別に数えます</li>
<li>${term('与党')}か${term('野党')}かを横に表示します（野党は法案が通りにくいため）</li>
<li><b>いまの状況：準備中です。</b>公約と国会での動きを結びつける作業をしています。</li></ul></section>
<section class="dialog-section"><h3>③ 努力（0〜100点）</h3><ul>
<li>何を見るか：国会でどれだけ動いているか</li>
<li>元データ：${esc(periodLabel())}に発言した会議の回数
<ul><li>同じ日に同じ会議で何回発言しても、1回と数えます</li><li>大臣としての答弁と、議長・委員長として会議を進めた発言は除きます</li></ul></li>
<li>点数 ＝ 現職のうち、自分より回数が少ない人の割合 × 100（いちばん多い人が100点、0回の人は0点）</li>
<li>次の3つは点数に入れず、数で横に表示します。<ul><li>${term('質問主意書')}（文書で内閣に質問した数）</li><li>筆頭で出した${term('法案')}の数</li><li>共同で出した法案の数</li></ul></li>
<li>測っているのは量だけで、中身の良さは見ていません</li></ul>
<details class="more"><summary>くわしく（数え方の細かいルール）</summary><ul><li>会議録の肩書が大臣・副大臣・政務官・長官など（政府側）と議長・副議長の発言は除きます。政府側の発言回数は別に表示します。</li><li>委員長などとして議事を進めた会議も除きます（その会議の最初の発言者を議事を進めた人と判定。会議録本文で抜き取り25件すべて確認）。進めた会議の回数は別に表示します。</li><li>法案の提出者としての答弁は、会議録に肩書が付かないため区別できず、含まれています。</li><li>同姓同名で発言を確定できない議員（2人）は、0点ではなく「未評価」です。そのため努力の母数は709人です。</li><li>集計期間の外の活動（例：期間より前の総理・大臣としての答弁）は含みません。発言0回の議員には、会議録で確認できた直近の発言を表示します。</li><li>2026年2月の総選挙で初当選した衆議院議員は、在職が集計期間の一部です。</li></ul></details></section>
<section class="dialog-section"><h3>参考：法律になった数（点数に入れません）</h3><p>提出に加わった法律案のうち、成立した数です。成立した議員は少ないため、点数にせず数と順位で示します。</p><details class="more"><summary>くわしく</summary><ul><li>第${esc(r.billSessions?.[0]||'')}〜${esc(r.billSessions?.[1]||'')}回国会。1つの法律案は1件です。</li><li>委員会が出した法案（提出者が「○○委員長」）は委員長個人の法律案に数えず、「委員長として提出」と分けて表示します。</li><li>決議・規則・規程は法律案に数えません。内閣が出した法律案も議員の数に入れません。</li><li>参議院は、公開資料に筆頭発議者しか載っていないため、共同発議者として加わった法律案を数えられません（筆頭のみ）。</li></ul></details></section>
<section class="dialog-section"><h3>同じ立場どうしの比較</h3><details class="more"><summary>くわしく</summary><ul><li>「同じ立場」＝同じ院・与党か野党か・当選回数の帯（衆議院：1回／2〜3回／4〜6回／7回以上。参議院は名簿に当選回数がないため帯なし）。</li><li>与党は会派単位で判定します（${esc((DB.meta.records?.coalition?.ruling||[]).map(k=>k.replace('|',' ')).join('・'))}。${esc(DB.meta.records?.coalition?.asOf||'')}に公式発表で確認）。どの会派にも属さない議員は「不明」で、立場別の比較から外します。</li><li>政府側としての発言がある月が12か月中6か月以上の議員は、政府側の在任が長いとみなして、立場別の比較とランキングの初期表示から外します。</li><li>議長・副議長としての発言だけの議員も、同じく比較と初期表示から外します。</li></ul></details></section>
<section class="dialog-section"><h3>読むときの注意</h3><ul><li>3つの物差しは足し合わせず、合計点は出しません。</li><li>確かめられない人は、0点ではなく「未評価」と表示します。</li><li>お金の報告（${term('透明性')}）は、報告書の数が説明の良し悪しを表さないため、点数にしていません。</li></ul></section>`);}

// ---- Rankings ----
const RK_METRICS={
  action:{label:'③ 努力の点数（発言のあった会議の回数）',unit:'点',get:m=>m.score.action,agg:'mean'},
  spec:{label:'① 公約の具体性の点数（4つのチェック）',unit:'点',get:m=>m.score.spec,agg:'mean'},
  meet:{label:'発言のあった会議の回数',unit:'回',get:meetVal,agg:'median'},
  rest:{label:'発言回数（政府側・議長・委員長としての発言を除く）',unit:'回',get:restVal,agg:'median'},
  lead:{label:'筆頭で出した法律案',unit:'件',get:leadVal,agg:'mean'},
  passed:{label:'参考：提出に加わった法律案の成立',unit:'件',get:passVal,agg:'mean'},
  q:{label:'質問主意書の件数',unit:'件',get:qVal,agg:'mean'},
};
const RK_UNITS={person:'人物',party:'政党（会派）',pref:'県'};
function aggValue(ms,metric){const v=ms.map(RK_METRICS[metric].get).filter(x=>x!=null);if(!v.length)return null;if(RK_METRICS[metric].agg==='median')return median(v);return Math.round(v.reduce((a,b)=>a+b,0)/v.length*10)/10;}
function rankRows(rows,order){const ok=rows.filter(r=>r.v!=null),na=rows.filter(r=>r.v==null);ok.sort((a,b)=>order==='asc'?a.v-b.v:b.v-a.v);for(const r of ok)r.rank=1+ok.filter(x=>order==='asc'?x.v<r.v:x.v>r.v).length;return {ok,na};}
function rkGroups(){
  const u=R.rk.unit,met=R.rk.metric;
  if(u==='person')return DB.members.filter(m=>R.rk.houses.has(m.house)&&R.rk.kaiha.has(kaihaKey(m))&&R.rk.side.has(m.side)&&R.rk.band.has(bandKey(m))&&(R.rk.longGov||!outOfCmp(m))).map(m=>({key:m.id,name:m.name,sub:`${m.house} · ${m.kaihaName} · ${m.side}${m.band?` · ${m.band}`:''}`,n:1,v:RK_METRICS[met].get(m),m}));
  if(u==='party'){const g=new Map();for(const m of DB.members){const k=kaihaKey(m);if(!g.has(k))g.set(k,[]);g.get(k).push(m);}return [...g.entries()].map(([k,ms])=>({key:k,name:ms[0].kaihaName,sub:ms[0].house,n:ms.length,v:aggValue(ms,met),small:ms.length<5}));}
  return PREFECTURES.map(p=>{const ms=DB.members.filter(m=>rankPrefs(m).includes(p));const top=ms.filter(m=>RK_METRICS[met].get(m)!=null&&RK_METRICS[met].get(m)>0).sort((a,b)=>RK_METRICS[met].get(b)-RK_METRICS[met].get(a)).slice(0,3);return {key:p,name:p,sub:`衆${ms.filter(m=>m.house==='衆議院').length}・参${ms.filter(m=>m.house==='参議院').length}（うち衆院比例${ms.filter(m=>m.electionType==='比例').length}）`,n:ms.length,v:aggValue(ms,met),top};});
}
function fmtV(v,met){return v==null?'—':`${v}${RK_METRICS[met].unit}`;}
function renderRankings(){
  if(waitView())return;
  if(!RK_METRICS[R.rk.metric])R.rk.metric='action';
  if(R.rk._band){R.rk.band=new Set(R.rk._band);delete R.rk._band;}
  const u=R.rk.unit;
  $('#view').innerHTML=`<h3 class="view-heading">ランキング：人物・政党（会派）・県</h3>
  <p class="notice">記録で並べています。政策の良し悪しの評価ではありません。3つの物差しは足し合わせません。<button type="button" class="score-how" data-action="score-method">点数の決め方</button></p><details class="more"><summary>くわしく</summary><p class="muted-line">努力は記録の量の並びで、仕事の質の評価ではありません。公約の具体性は、選挙公報の本人の欄に公約が3こ以上ある議員だけが対象です。進捗率は準備中です。赤札（公金の抜け穴に賛成した記録）のランキングは、対象にする法案のリストを公開してから追加します。</p></details>
  ${sideQuick()}
  <div class="rk-units" role="group" aria-label="ランキングの単位">${Object.entries(RK_UNITS).map(([k,l])=>`<button type="button" data-rk-unit="${k}" aria-pressed="${k===u}" class="${k===u?'selected':''}">${l}</button>`).join('')}</div>
  <div class="controls"><select id="rk-metric" aria-label="指標">${Object.entries(RK_METRICS).map(([k,x])=>`<option value="${k}">${x.label}</option>`).join('')}</select>
  <select id="rk-order" aria-label="並び順"><option value="desc">多い順（高い順）</option><option value="asc">少ない順（低い順）</option></select>
  ${u==='person'?multiSelect('ms-rk-house','院',HOUSES.map(h=>({value:h,label:h})),R.rk.houses)+multiSelect('ms-rk-kaiha','会派',kaihaOptions(),R.rk.kaiha)+multiSelect('ms-rk-side','与野党',['与党','野党','不明'].map(x=>({value:x,label:x})),R.rk.side)+multiSelect('ms-rk-band','当選回数',['当選1回','当選2〜3回','当選4〜6回','当選7回以上','参議院（当選回数の帯なし）'].map(x=>({value:x,label:x})),R.rk.band)+`<label class="rk-check"><input type="checkbox" id="rk-longgov" ${R.rk.longGov?'checked':''}> 政府側の在任が長い議員と議長・副議長（${DB.members.filter(outOfCmp).length}人）も含める</label>`:''}</div>
  <p class="rk-dataline">${dataLine()}</p>
  <div id="rk-table" aria-live="polite"></div>
  ${u==='person'?`<p class="muted-line rk-note">役職のタグは、会議録で確認できた直近の政府側の肩書です（集計期間内）。政府側（大臣・副大臣・政務官など）としての発言がある月が12か月中6か月以上の議員は「政府側の在任が長い」として、初期状態では順位から外しています（在任期間そのものは会議録から取れないため、発言がある月で判定）。議長・副議長としての発言だけの議員も、慣例で質問しない立場のため同じく外しています。与党＝${esc((DB.meta.records?.coalition?.ruling||[]).map(k=>k.replace('|',' ')).join('・'))}（${esc(DB.meta.records?.coalition?.asOf||'')}確認、<a href="${esc(DB.meta.records?.coalition?.sources?.[0]?.url||'#')}" target="_blank" rel="noopener noreferrer">出典</a>）。</p>`:''}
  <div class="group-note">${u==='person'?(R.rk.metric==='spec'?'公約の具体性＝公約1こごとの4つのチェックの平均÷4×100。公約が3こ以上ある議員だけです。':'努力の点数は「現職のうち、この議員より値が小さい人の割合」×100。')+'<button type="button" class="score-how" data-action="score-method">点数の決め方</button>':u==='party'?'会派は国会内の単位で、院ごとに分けています。点数・法案は所属議員の平均、発言件数は中央値。所属5人未満の会派は値がぶれやすいため順位を付けず、参考として下に表示します。':'県の議員団＝その県の小選挙区・選挙区の議員＋衆議院比例ブロックの議員（ブロックを構成するすべての県に含めます）。参議院の全国比例は全国1区のため県には含めません。点数・法案は平均、発言件数は中央値。県の経済状況や県民の評価とは関係ありません。<a class="source-link" href="https://laws.e-gov.go.jp/law/325AC1000000100" target="_blank" rel="noopener noreferrer">比例ブロックの区域：公職選挙法 別表第二（e-Gov） ↗</a>'}</div>`;
  $('#rk-metric').value=R.rk.metric;$('#rk-order').value=R.rk.order;
  $('#rk-metric').addEventListener('change',e=>{R.rk.metric=e.target.value;R.rk.shown=100;renderRankings();});
  $('#rk-order').addEventListener('change',e=>{R.rk.order=e.target.value;R.rk.shown=100;renderRankingTable();});
  $('#rk-longgov')?.addEventListener('change',e=>{R.rk.longGov=e.target.checked;R.rk.shown=100;renderRankingTable();});
  renderRankingTable();
}
function renderRankingTable(){
  const box=$('#rk-table');if(!box)return;syncRankUrl();
  const met=R.rk.metric,u=R.rk.unit,rows=rkGroups();
  const ranked=rows.filter(r=>!r.small),small=rows.filter(r=>r.small);
  const {ok,na}=rankRows(ranked,R.rk.order);
  const max=Math.max(1,...ok.map(r=>r.v));
  const tie=new Map();for(const r of ok)tie.set(r.v,(tie.get(r.v)||0)+1);
  const isScore=RK_METRICS[met].unit==='点';
  const shown=u==='person'?ok.slice(0,R.rk.shown):ok;
  const btn=r=>u==='person'?`<button type="button" data-member="${esc(r.key)}">詳細 ↗</button>`:u==='party'?`<button type="button" data-kaiha="${esc(r.key)}">議員 ↗</button>`:`<button type="button" data-rank-pref="${esc(r.key)}">議員団 ↗</button>`;
  const row=r=>`<li class="rk-row${u==='person'?' rk-click':''}"${u==='person'?` data-open-member="${esc(r.key)}" role="button" tabindex="0" aria-label="${esc(r.name)}の点数の内訳と実績を開く"`:''}><span class="rk-rank">${r.rank==null||r.v===0?'—':r.rank}<small>${r.rank==null||r.v===0?'':'位'}</small>${r.rank!=null&&r.v===0?`<em>0が${tie.get(r.v)}人</em>`:r.rank!=null&&tie.get(r.v)>1?`<em>同率${tie.get(r.v)}</em>`:''}</span><span class="rk-name">${u==='person'?avatar(r.m):''}<span><b>${esc(r.name)}${u==='person'?roleTag(r.m):''}</b><small>${esc(r.sub)}${u==='person'?'':` · ${r.n}人`}</small>${u==='person'&&r.m.mainMeeting?`<small class="rk-main">主な会議：${esc(r.m.mainMeeting.name)}</small>`:''}${r.top?`<span class="rk-top3">${r.top.length?`県の上位：${r.top.map((m,i)=>`<span class="rk-click" data-open-member="${esc(m.id)}" role="button" tabindex="0">${i+1}.${esc(m.name)}<i>${esc(fmtV(RK_METRICS[met].get(m),met))}</i></span>`).join('')}`:'県の上位：該当なし（全員0）'}</span>`:''}</span></span><span class="rk-val"><b>${esc(fmtV(r.v,met))}</b><span class="bar"><i style="width:${r.v==null?0:Math.max(1,Math.round((isScore?r.v:r.v/max*100)))}%"></i></span></span><span class="rk-act">${btn(r)}</span></li>`;
  box.innerHTML=`<div class="result-head"><span>${esc(RK_UNITS[u])}・${esc(RK_METRICS[met].label)}・${R.rk.order==='asc'?'少ない順':'多い順'}：順位あり ${ok.length}${u==='person'?'人':'件'}</span><span>${u==='person'?'同じ値は同じ順位':'1人あたり（平均・中央値）'}</span></div>
  ${ok.length?`<ol class="rk-list">${shown.map(row).join('')}</ol>`:'<div class="empty"><strong>表示できる項目がありません</strong><p>院の絞り込みを変更してください。</p></div>'}
  ${u==='person'&&ok.length>shown.length?`<button type="button" class="card-button rk-more" data-action="rk-more">さらに100人を表示（${shown.length}/${ok.length}）</button>`:''}
  ${small.length?`<h4 class="mini-h">参考（所属5人未満・順位なし）</h4><ol class="rk-list">${small.map(r=>row({...r,rank:null})).join('')}</ol>`:''}
  ${na.length?`<h4 class="mini-h">順位外：値を確定できない ${na.length}${u==='person'?'人':'件'}</h4><p class="muted-line">${na.slice(0,40).map(r=>esc(r.name)).join('、')}${na.length>40?' ほか':''}。${met==='spec'?'比例代表だけで当選して本人の選挙公報がない・公報が読めない・公約が3こ未満などのため。0点とは扱いません。':'同姓同名で発言件数を確定できない・記録が未取得などのため。0件とは扱いません。'}</p>`:''}`;
}
const rerender=()=>{if(state.view==='rankings')renderRankingTable();else renderResults();};

function monthChart(title,months,vals,unit){
  const max=Math.max(1,...vals),w=100/months.length;
  const bars=vals.map((v,i)=>{const h=Math.round(v/max*100);return `<g><rect x="${(i*w+w*0.15).toFixed(2)}%" y="${100-h}%" width="${(w*0.7).toFixed(2)}%" height="${h}%" class="mc-bar"><title>${esc(months[i])}：${v}${unit}</title></rect></g>`;}).join('');
  return `<figure class="month-chart"><figcaption>${esc(title)}<small>最多 ${max}${unit}／月</small></figcaption><svg viewBox="0 0 100 40" preserveAspectRatio="none" role="img" aria-label="${esc(title)}：${months.map((mo,i)=>`${mo} ${vals[i]}${unit}`).join('、')}"><svg x="0" y="0" width="100%" height="100%">${bars}</svg></svg><div class="mc-labels">${months.map(mo=>`<span>${+mo.slice(5)}月</span>`).join('')}</div></figure>`;
}
function exchangeBlock(m,ex){
  if(!ex||(!ex.asked&&!ex.answered))return '<p class="muted-line">この期間に、質問と答弁の組み合わせとして確認できたやり取りはありません。</p>';
  const plist=ps=>`<ul class="rec-list">${ps.map(([n,l,c])=>{const t=DB.members.find(x=>x.name===n||x.speakerQuery===n);return `<li><span>${t?`<span class="rk-click link-like" data-open-member="${esc(t.id)}" role="button" tabindex="0">${esc(n)}</span>`:esc(n)}　<small style="display:inline">${esc(l)}</small></span><small>${c}往復</small></li>`;}).join('')}</ul>`;
  const recent=rs=>`<ul class="rec-list">${rs.map(([d,h,mt,pairs,ps,url])=>`<li><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(d)}　${esc(h)} ${esc(mt)}　${pairs}往復 ↗</a><small>${ps.map(([n,l,c])=>`${esc(n)}（${esc(l)}）${c}`).join('・')}</small></li>`).join('')}</ul>`;
  let html='';
  if(ex.asked)html+=`<h4 class="mini-h">この議員の発言に答えた相手（${ex.asked.meetings}会議・${ex.asked.pairs}往復）</h4>${plist(ex.asked.partners)}<details class="rec-group"><summary>最近の会議（最大10件）</summary>${recent(ex.asked.recent)}</details>`;
  if(ex.answered)html+=`<h4 class="mini-h">この議員が政府側として答えた相手（${ex.answered.meetings}会議・${ex.answered.pairs}往復）</h4>${plist(ex.answered.partners)}<details class="rec-group"><summary>最近の会議（最大10件）</summary>${recent(ex.answered.recent)}</details>`;
  return html+'<p class="muted-line">会議録の発言の順番から機械的に判定しています。議員の発言の直後に話した人（その会議の議長・委員長を除く）を「答えた相手」、政府側の発言の直前に話した人を「質問した相手」としています。質問者どうしの続けての発言なども1往復に数えられる場合があります。肩書はその発言の会議録の肩書です。</p>';
}

// ---- ranking state in the URL (shareable) ----
function rankQuery(){const k=R.rk,q=new URLSearchParams({u:k.unit,m:k.metric,o:k.order});
  const allSide=['与党','野党','不明'].every(x=>k.side.has(x));if(!allSide)q.set('side',[...k.side].join(','));
  if(k.houses.size<2)q.set('house',[...k.houses].join(','));
  if(DB.ready){const bands=new Set(DB.members.map(bandKey));if([...bands].some(b=>!k.band.has(b)))q.set('band',[...k.band].join(','));}
  if(k.longGov)q.set('gov','1');return '?'+q.toString();}
function readRankState(){const h=location.hash.slice(1);if(!h.startsWith('rankings?'))return;const q=new URLSearchParams(h.split('?')[1]);
  if(q.get('u')&&RK_UNITS[q.get('u')])R.rk.unit=q.get('u');if(q.get('m'))R.rk.metric=q.get('m');if(['asc','desc'].includes(q.get('o')))R.rk.order=q.get('o');
  if(q.get('side'))R.rk.side=new Set(q.get('side').split(','));if(q.get('house'))R.rk.houses=new Set(q.get('house').split(','));
  if(q.get('band'))R.rk._band=q.get('band').split(',');R.rk.longGov=q.get('gov')==='1';}
function syncRankUrl(){if(state.view==='rankings')history.replaceState(null,'','#rankings'+rankQuery());}
function copyRankLink(btn){const url=location.origin+location.pathname+'#rankings'+rankQuery();
  const done=()=>{btn.textContent='リンクをコピーしました';setTimeout(()=>{btn.textContent='この条件のリンクをコピー';},2500);};
  if(navigator.clipboard?.writeText)navigator.clipboard.writeText(url).then(done,()=>{prompt('このリンクをコピーしてください',url);});else{prompt('このリンクをコピーしてください',url);}}
function sideQuick(){const s=R.rk.side;const cur=s.has('与党')&&s.has('野党')?'all':s.has('与党')&&!s.has('野党')?'ruling':!s.has('与党')&&s.has('野党')?'opp':'custom';
  return `<div class="rk-units rk-side" role="group" aria-label="与党・野党">${[['all','全員'],['ruling','与党'],['opp','野党']].map(([k,l])=>`<button type="button" data-rk-side="${k}" aria-pressed="${cur===k}" class="${cur===k?'selected':''}">${l}</button>`).join('')}<button type="button" class="score-how rk-copy" data-action="rk-copy">この条件のリンクをコピー</button></div>`;}

// ---- government tab (official roster x minutes) ----
const G={sort:'roster'};
function renderGovernment(){
  if(waitView())return;
  const cab=DB.meta.records?.cabinet;if(!cab){$('#view').innerHTML='<div class="empty"><strong>政府側の名簿を読み込めませんでした</strong></div>';return;}
  const byId=new Map(DB.members.map(m=>[m.id,m]));
  const groups=['閣僚','副大臣','大臣政務官','総理補佐官'];
  const rows=cab.people.filter(p=>!p.former);
  const sorted=g=>{const r=rows.filter(p=>p.group===g);if(G.sort==='answers')r.sort((a,b)=>((byId.get(b.memberId)?.gov?.answers)??-1)-((byId.get(a.memberId)?.gov?.answers)??-1));return r;};
  const cell=p=>{const m=byId.get(p.memberId);const g=m?.gov;
    return `<li class="gov-row">
      <span class="gov-post">${esc(p.posts[0])}${p.posts.length>1?`<small>${esc(p.posts.slice(1).join('・'))}</small>`:''}</span>
      <span class="gov-name">${m?`<span class="rk-click link-like" data-open-member="${esc(m.id)}" role="button" tabindex="0">${avatar(m)}<b>${esc(m.name)}</b></span><small>${esc(m.house)} · ${esc(m.kaihaName)}</small>`:`<b>${esc(p.display)}</b><small>国会議員ではないため会議録の集計の対象外</small>`}</span>
      <span class="gov-num">${m?`<b>${g?.answers??0}回</b><small>政府側の答弁（${g?.months??0}か月）</small>`:'—'}</span>
      <span class="gov-q">${m&&g?.questioners?.length?`<small>質問が多かった議員</small>${g.questioners.map(([n,c])=>{const t=DB.members.find(x=>x.name===n||x.speakerQuery===n);return t?`<span class="rk-click link-like" data-open-member="${esc(t.id)}" role="button" tabindex="0">${esc(n)}</span> ${c}往復`:`${esc(n)} ${c}往復`;}).join('・')}`:m?'<small>この期間の答弁の記録なし</small>':''}</span>
    </li>`;};
  const former=cab.people.filter(p=>p.former);
  $('#view').innerHTML=`<h3 class="view-heading">政府側：大臣・副大臣・政務官と答弁の記録</h3>
  <p class="notice">首相官邸の名簿（${esc(cab.asOf?.['閣僚']||'')}、<a href="${esc(cab.source)}" target="_blank" rel="noopener noreferrer">出典</a>）に載っている人ごとに、会議録の政府側の肩書での答弁回数と、質問が多かった議員を並べます。評価や順位ではありません。答弁の回数は${esc(periodLabel())}の合計で、今の役職に就く前の政府側の答弁も含みます（会議録の肩書で判定）。</p>
  <p class="rk-dataline">${dataLine()}</p>
  <div class="controls"><select id="gov-sort" aria-label="並び順"><option value="roster">名簿の順</option><option value="answers">答弁が多い順</option></select></div>
  ${groups.map(g=>{const r=sorted(g);return r.length?`<h4 class="mini-h gov-h">${esc(g)}（${r.length}人）</h4><ul class="gov-list">${r.map(cell).join('')}</ul>`:'';}).join('')}
  ${former.length?`<p class="muted-line rk-note">名簿上の前任：${former.map(p=>`${esc(p.posts[0])} ${esc(p.display)}（${esc(p.former)}）`).join('、')}</p>`:''}`;
  $('#gov-sort').value=G.sort;$('#gov-sort').addEventListener('change',e=>{G.sort=e.target.value;renderGovernment();});
}

// ---- per-session chart (no ranking) ----
function sessionChart(m,sp){
  const ses=DB.meta.records?.sessions||{};const keys=Object.keys(ses).sort();if(!keys.length||!sp?.bySession)return '';
  const meet=keys.map(k=>(sp.bySession[k]||[0,0])[0]),gov=keys.map(k=>(sp.bySession[k]||[0,0])[1]);
  const bars=(vals,unit)=>{const max=Math.max(1,...vals);return `<div class="ses-bars">${keys.map((k,i)=>`<div class="ses-col"><span class="ses-val">${vals[i]}${unit}</span><span class="ses-bar"><i style="height:${Math.round(vals[i]/max*100)}%"></i></span><span class="ses-lab">第${k}回<small>${esc(ses[k].from.slice(5).replace('-','/'))}〜${esc(ses[k].until.slice(5).replace('-','/'))}・${ses[k].days}日</small></span></div>`).join('')}</div>`;};
  return `<h4 class="mini-h">国会の会期ごとの推移</h4><figure class="month-chart"><figcaption>発言のあった会議の回数（政府側・議長・委員長を除く）<small>順位は付けません</small></figcaption>${bars(meet,'回')}</figure>${gov.some(v=>v)?`<figure class="month-chart"><figcaption>政府側（大臣など）としての発言回数</figcaption>${bars(gov,'回')}</figure>`:''}<p class="muted-line">会期ごとに日数が大きく違い、閉会中は会議が少なくなります。2026年2月の総選挙をはさむため、会期どうしの単純な比較には向きません。日付は集計期間（${esc(periodLabel())}）内で会議録が公開されている範囲です。</p>`;
}

// ---- X reactions (reference only; never part of a score) ----
let XR=null;
function getXR(){if(!XR)XR=fetch('data/x_reactions.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}).catch(e=>{XR=null;throw e;});return XR;}
const XR_LABEL={positive:'ポジティブ',neutral:'ニュートラル',negative:'ネガティブ'};
function xrLine(m){const x=m.xr;if(!x)return '';if(!x.reviewed)return `<p class="xr-line"><span>Xでの反応（参考）</span>この期間に、Grokの検索で確認できた投稿はありませんでした<small>${esc(x.from)}〜${esc(x.until)}・点数には入れていません</small></p>`;return `<p class="xr-line"><span>Xでの反応（参考）</span>ポジティブ ${x.positive}件・ニュートラル ${x.neutral}件・ネガティブ ${x.negative}件<small>Grokの検索で確認できた${x.reviewed}件のみ・${esc(x.from)}〜${esc(x.until)}・点数には入れていません</small></p>`;}
function xrSection(m,x){
  if(!x)return `<p class="muted-line">この議員は、まだ調べていません。いまは一部の議員だけを調べています。</p>`;
  if(!x.reviewed)return `<p>${esc(x.from)}〜${esc(x.until)}に、Xでこの議員についての投稿は見つかりませんでした。</p><p class="muted-line">AI（Grok）で1回だけ検索した結果です。話題になっていないとは限りません。</p>`;
  const total=x.counts.positive+x.counts.neutral+x.counts.negative||1;
  const bar=`<div class="xr-bar" role="img" aria-label="ポジティブ${x.counts.positive}件、ニュートラル${x.counts.neutral}件、ネガティブ${x.counts.negative}件">${['positive','neutral','negative'].map(k=>x.counts[k]?`<i class="xr-${k}" style="width:${x.counts[k]/total*100}%"></i>`:'').join('')}</div>`;
  const block=k=>{const ts=x.themes[k]||[];return `<div class="xr-block xr-b-${k}"><h4 class="mini-h">${XR_LABEL[k]}　${x.counts[k]}件</h4>${ts.length?`<ul class="rec-list">${ts.map(t=>`<li><span>${esc(t.theme)}<small style="display:inline">　${t.count}件</small></span>${t.links.length?`<small>実際の投稿：${t.links.map((u,i)=>`<a href="${esc(u)}" target="_blank" rel="noopener noreferrer nofollow">投稿${i+1} ↗</a>`).join('　')}</small>`:'<small>投稿へのリンクなし（検索結果で確認できたものだけを載せています）</small>'}</li>`).join('')}</ul>`:'<p class="muted-line">確認できた投稿はありません。</p>'}</div>`;};
  return `<p>${esc(x.from)}〜${esc(x.until)}に、Grok（xAI）の X 検索で確認できた <b>${x.reviewed}件</b>の投稿のうち、話題に分類できた ${x.counts.positive+x.counts.neutral+x.counts.negative}件の内訳です。</p>${bar}
  ${['positive','neutral','negative'].map(block).join('')}
  ${x.topics?.length?`<h4 class="mini-h">期間中の主な話題</h4><ul>${x.topics.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>`:''}
  <div class="group-note xr-note"><b>読むときの注意：</b>検索で目立った投稿だけを見た結果で、世論や評判の全体ではありません。件数が少ないため割合は出していません。支持者・政党関係・中継告知のアカウントの投稿が多くなりがちです。本人の投稿・ボット・同じ文面の繰り返しは除いています。投稿の本文は転載せず、X 上の元の投稿へのリンクだけを載せています（侮辱的な表現は話題として要約）。点数・ランキングには入れていません。${x.caveats?.length?`<br>この議員について分析時に挙がった注意：${x.caveats.map(esc).join('／')}`:''}<br>分類：${esc(x.model)}・取得 ${esc(x.fetchedAt.slice(0,10))}</div>`;
}

// ---- personal pledges from election bulletins (公約の具体性 = 4 checks; no judgement of policy merit) ----
let PP=null;
function getPP(){if(!PP)PP=fetch('data/pledges_personal.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}).catch(e=>{PP=null;throw e;});return PP;}
function ppLine(m){const x=m.pp;if(!x)return `<strong>個人の公約 未収録<small>${esc(pledgeSummary(m))}</small></strong>`;
  if(x.n==null)return `<strong>個人の公約 なし<small>${esc(x.why)}<br>${esc(pledgeSummary(m))}</small></strong>`;
  return `<strong>選挙公報の公約 ${x.n}件<small>具体的 ${x.v}件・期限や数値あり ${x.d}件${x.a?`・ほかに実績の記述 ${x.a}件`:''}（${esc(x.el)}の本人の欄）</small></strong>`;}
const PP_CRIT={1:'政治資金：公開',2:'政治資金：領収書',3:'政治資金：監査',4:'政治資金：罰則・返還'};
function ppSection(m,d){
  if(!d)return `<p>${m.pp?.n==null?esc(specNaText(m))+'。':'本人の約束は、まだ調べられていません。'}</p>`;
  const has=x=>SPEC_CK.filter(([k])=>x[k]).map(([,l])=>l);
  const DOT={t:'何',a:'動',dl:'期',ms:'数'};
  const dots=x=>'t' in x?`<span class="pp-dots" role="img" aria-label="書いてあること：${has(x).join('・')||'なし'}">${SPEC_CK.map(([k,l])=>`<i class="${x[k]?'on':''}" title="${l}">${DOT[k]}</i>`).join('')}</span>`:'';
  const li=x=>`<li><q>${esc(x.q)}</q><p class="pp-meta">${dots(x)}${x.area?`<span class="pp-area">${esc(x.area)}</span>`:''}${x.c?`<span class="pp-area">${esc(PP_CRIT[x.c])}</span>`:''}</p></li>`;
  const pl=d.items.filter(x=>x.k!=='実績'),ac=d.items.filter(x=>x.k==='実績');
  return `<p class="pp-howto"><span class="pp-dots legend"><i class="on">何</i><i class="on">動</i><i class="on">期</i><i class="on">数</i></span>何を・どう動く・期限・数字。色が多いほど、確かめやすい約束です。</p>
  ${pl.length?`<ol class="pp-items">${pl.map(li).join('')}</ol>`:'<p>これからやる約束は、書いてありませんでした（実績の記述だけです）。</p>'}
  ${ac.length?`<details class="more"><summary>実績として書いたこと（${ac.length}件）</summary><ol class="pp-items">${ac.map(li).join('')}</ol><p class="muted-line">本人の主張です。このサイトでは事実を確かめていません。</p></details>`:''}
  <details class="more"><summary>読むときの注意（AIで読み取っています）</summary><ul>
   <li>公報の画像から、AI（${esc(d.model)}）が文を抜き出しました。</li>
   <li>11人・128件を人が確かめたところ、125件が原文どおりでした。</li>
   <li>4つのチェックもAIの判定です。50件中47件が人の判定と同じでした。</li>
   <li>「約束」と「実績」の分け方には、迷う例があります。</li>
   <li>引用するときは、出典のPDFで確かめてください。</li></ul>
   <p class="muted-line">公報での名前：${esc(d.name||'')}${d.party?`（${esc(d.party)}）`:''}。<a href="${esc(d.url)}${d.page?`#page=${d.page}`:''}" target="_blank" rel="noopener noreferrer">${esc(d.pref)}選挙管理委員会の選挙公報 PDF${d.page?`（${d.page}ページ）`:''} ↗</a></p></details>`;
}
// ---- 議席の勢力図 (seat map). Built from the roster only. Same neutral tones for every party; only the majority line is red ----
const SEATS={'衆議院':465,'参議院':248};
const SIDE_ORDER={'与党':0,'不明':1,'野党':2};
const SIDE_TONES={'与党':['#2b3340','#4a5466'],'不明':['#c9ced6','#dde1e7'],'野党':['#8a919e','#aab1bc']};
function seatMap(){
  return `<h3 class="view-heading">いまの議席：どちらが過半数？</h3><p class="notice">法案は、多くの場合「出席した議員の${term('過半数','半分より多く')}」の賛成で決まります。${term('与党')}が過半数の議席を持つと、与党だけで法案を通せます。</p>
  <div class="seat-maps">${HOUSES.map(h=>{
    const ms=DB.members.filter(m=>m.house===h),total=SEATS[h],need=Math.floor(total/2)+1,vac=total-ms.length;
    const g=new Map();for(const m of ms){const k=kaihaKey(m);if(!g.has(k))g.set(k,{name:m.kaihaName,side:m.side||'不明',n:0});g.get(k).n++;}
    const rows=[...g.values()].sort((a,b)=>SIDE_ORDER[a.side]-SIDE_ORDER[b.side]||b.n-a.n);
    const cnt=s=>ms.filter(m=>(m.side||'不明')===s).length,ruling=cnt('与党');
    const tone={};const seen={'与党':0,'不明':0,'野党':0};for(const r of rows){tone[r.name]=SIDE_TONES[r.side][seen[r.side]++%2];}
    const pct=n=>(n/total*100).toFixed(2);
    return `<article class="seat-card"><div class="seat-head"><h4>${term(h)}</h4><span>${total}議席・過半数は${need}議席</span></div>
    <div class="seat-bar" role="img" aria-label="${esc(h)}：与党${ruling}、野党${cnt('野党')}、どちらでもない${cnt('不明')}、欠員${vac}。過半数は${need}">${rows.map(r=>`<i style="width:${pct(r.n)}%;background:${tone[r.name]}" title="${esc(r.name)} ${r.n}人"></i>`).join('')}${vac?`<i class="seat-vacant" style="width:${pct(vac)}%" title="欠員 ${vac}"></i>`:''}<b class="seat-line" style="left:${pct(need)}%"></b></div>
    <p class="seat-sum"><span class="seat-chip" style="background:${SIDE_TONES['与党'][0]}"></span>与党 <b>${ruling}</b>　<span class="seat-chip" style="background:${SIDE_TONES['野党'][0]}"></span>野党 <b>${cnt('野党')}</b>　<span class="seat-chip" style="background:${SIDE_TONES['不明'][0]}"></span>どの会派にも入っていない <b>${cnt('不明')}</b>${vac?`　欠員 <b>${vac}</b>`:''}<br><span class="seat-verdict">${ruling>=need?`与党だけで過半数です（あと${ruling-need+1}議席減ると過半数を下回ります）。`:`与党だけでは過半数に${need-ruling}議席たりません。法案を通すには、ほかの会派の賛成が必要です。`}</span></p>
    <ol class="seat-legend">${rows.map(r=>`<li><i style="background:${tone[r.name]}"></i><span>${esc(r.name)}</span><small>${r.side==='不明'?'どちらでもない':r.side}</small><b>${r.n}</b></li>`).join('')}</ol></article>`;}).join('')}</div>
  <details class="more"><summary>くわしく（数え方と出典）</summary><ul><li>人数は衆参の公式名簿の会派ごとの人数です（${esc(DB.meta.rosterAsOf?.['衆議院']||'')}、${esc(DB.meta.rosterAsOf?.['参議院']||'')}）。</li><li>与党・野党は会派ごとに決めています（${esc((DB.meta.records?.coalition?.ruling||[]).map(k=>k.replace('|',' ')).join('・'))}が与党。${esc(DB.meta.records?.coalition?.asOf||'')}に公式発表で確認）。${(DB.meta.records?.coalition?.sources||[]).map(s=>`<a class="inline-link" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a>`).join(' ')}</li><li>どの会派にも入っていない議員は、与党・野党のどちらにも数えません。実際の採決では、法案ごとに賛否が分かれることがあります。</li><li>色は与党・野党などの区別だけで、政党ごとの色は使いません。</li></ul></details>`;
}

// ---- 政党のお金 (party HQ income & spending, 総務省「収支報告書の要旨」). Numbers pass the report's own sums ----
const PF={data:null,loading:false,error:null,year:null};
const PF_IN=[['subsidy','政党交付金（税金）','#c8102e'],['fees','党費','#2b3340'],['donations','寄附','#5b6270'],['business','新聞・本などの事業','#8a919e'],['transfers','支部などから','#b9c0ca'],['loans','借入金','#d9a441'],['otherRest','その他','#dde1e7']];
function pfLoad(){if(PF.data||PF.loading)return;PF.loading=true;fetch('data/party_finance.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}).then(d=>{PF.data=d;PF.year=d.years[0].year;}).catch(e=>{PF.error=String(e);}).finally(()=>{PF.loading=false;if(state.view==='parties')renderParties();});}
const oku=y=>y>=1e8?`${(y/1e8).toFixed(1)}億円`:`${Math.round(y/1e4).toLocaleString()}万円`;
function pfParts(p){return {...p,otherRest:Math.max(0,(p.other||0)-(p.subsidy||0))};}
function partyMoney(){
  const head=`<h3 class="view-heading" id="party-money" style="margin-top:44px">政党のお金：どこから入って、何に使った？</h3><p class="notice">政党の本部が国に出した${term('収支報告書','お金の報告書')}の数字です。赤い部分は${term('政党交付金')}で、わたしたちの税金です。</p>`;
  if(PF.error)return head+`<div class="empty"><strong>政党のお金のデータを読み込めませんでした</strong><p>${esc(PF.error)}</p></div>`;
  if(!PF.data){pfLoad();return head+'<div class="empty"><strong>読み込み中…</strong></div>';}
  const Y=PF.data.years.find(y=>y.year===PF.year)||PF.data.years[0];
  const ps=Y.parties.map(pfParts).sort((a,b)=>b.income-a.income),max=Math.max(...ps.map(p=>p.income));
  const failed=PF.data.failed.filter(f=>`${f.year}分`===Y.label);
  return head+`<div class="pf-years" role="group" aria-label="年をえらぶ">${PF.data.years.map(y=>`<button type="button" data-pf-year="${y.year}" ${y.year===Y.year?'aria-pressed="true"':'aria-pressed="false"'}>${esc(y.label)}</button>`).join('')}</div>
  <ol class="money-legend pf-legend">${PF_IN.map(([k,l,c])=>`<li><i style="background:${c}"></i><span>${l}</span></li>`).join('')}</ol>
  <div class="pf-list">${ps.map(p=>`<article class="pf-row"><div class="pf-name"><b>${esc(p.name)}</b><small>収入 ${oku(p.income)}・支出 ${oku(p.spend)}</small></div>
   <div class="pf-bar" style="width:${(p.income/max*100).toFixed(1)}%" role="img" aria-label="${esc(p.name)}の収入 ${oku(p.income)}。${PF_IN.filter(([k])=>p[k]).map(([k,l])=>`${l} ${oku(p[k])}`).join('、')}">${PF_IN.map(([k,l,c])=>p[k]?`<i style="width:${(p[k]/p.income*100).toFixed(2)}%;background:${c}" title="${l} ${oku(p[k])}"></i>`:'').join('')}</div>
   <p class="pf-note">税金（政党交付金）<b>${p.subsidy?`${oku(p.subsidy)}（収入の${Math.round(p.subsidy/p.income*100)}%）`:'受け取っていません'}</b>${p.business/p.income>=.3?`　事業の収入 <b>${oku(p.business)}</b>（党の新聞など）`:''}</p></article>`).join('')}</div>
  <details class="more"><summary>くわしく（数字の出どころ・確かめ方）</summary><ul>
   <li>出典：<a class="inline-link" href="${esc(Y.source.url)}" target="_blank" rel="noopener noreferrer">${esc(Y.source.title)} ↗</a>（${esc(Y.published)} 公表）。<a class="inline-link" href="${esc(Y.source.pdf)}" target="_blank" rel="noopener noreferrer">PDF ↗</a></li>
   <li>対象は${esc(PF.data.scope)}党の全体のお金は、政党の支部などの分を足すともっと大きくなります。</li>
   <li>「収入」は、その年に入ったお金です（前の年からの繰り越しは入れません）。「政党交付金」は報告書では「その他の収入」の中に入っているため、ここでは別に取り出しています。</li>
   <li>数字は報告書の文字をそのまま読み取り、報告書の中の合計と全部合うことを確かめました：${PF.data.checks.map(esc).join('／')}。さらに、総務省の「収支報告の概要」の数字（千円単位）とも全部一致しました。</li>
   ${failed.length?`<li>次の政党は、報告書の欄の数字が合計と合わないため、表示していません：${failed.map(f=>esc(f.name)).join('、')}。</li>`:''}
   <li>寄附した人の名前は、このサイトでは扱いません。お金の多い少ないで政党を評価したり、点数にしたりはしません。</li></ul></details>`;
}

// ---- ルールと計算 (rules tab): what we measure, how, what we exclude, data & changes. Same rules for every party ----
const CHANGELOG=[
  ['2026-11-04','政党タブに「いまの議席」と「政党のお金（本部の収支 令和4〜6年分）」を追加。「ルールと計算」タブ、AI・研究向けのデータ説明を追加。'],
  ['2026-11-04','点数を「3つの物差し」（①公約の具体性・②進捗率・③努力）に変更。合計点は出しません。'],
  ['2026-11-04','本人の選挙公報から公約を読み取り、議員ごとに表示（抜き取り検算 11人・128件中125件一致）。'],
  ['2026-11-02','努力の数え方を修正：委員長などとして会議を進めた回を除外。大臣としての答弁・議長の発言も除外。'],
  ['2026-11-02','法案の数え方を修正：会期をまたいで同じ法案を何度も数えていたため、1つの法案は1件に（951件→422件。成立68件は変わらず）。'],
  ['2026-11-02','公開（URLを知る人だけ）。'],
];
const DATASETS=[
  ['members.json','国会議員711人の名簿と、議員ごとの件数（発言・法案・公約・お金の報告）','衆議院・参議院の公式名簿、国会会議録検索システム、衆参の議案情報'],
  ['meta.json','入手日・集計期間・出典・与党の判定・公費の目安','各データの出典ページ'],
  ['records.json','議員ごとの法案・参議院の投票・政治団体（議員の詳細を開いたときに読む）','衆参の議案情報、参議院の投票結果、総務省の政治団体名簿'],
  ['speeches.json','議員ごとの国会での発言の記録（日付・会議・リンク。本文は入れていません）','国会会議録検索システム'],
  ['pledges_personal.json','本人の選挙公報から抜き出した公約と、4つのチェック','各都道府県の選挙管理委員会が公開した選挙公報'],
  ['pledges.json','各党の公約のうち、政治資金・透明性の項目','各党の公式の選挙公約'],
  ['party_finance.json','政党本部の収入と支出の内訳（令和4〜6年分）','総務省「政治資金収支報告書の要旨」（官報）'],
];
function renderRules(){
  if(waitView())return;
  const M=DB.meta,c=M.records?.coalition;
  $('#view').innerHTML=`<h3 class="view-heading">ルールと計算：このサイトは、どう決めている？</h3>
  <p class="notice">どの政党にも、同じルールを使います。そのルールを、ここに全部のせます。おかしいと思ったら、ここを見れば理由が分かるようにしています。</p>
  <div class="rule-grid">
   <article class="rule-card"><span class="eyebrow">01</span><h4>同じ物差し</h4><p>政党や人によって、数え方を変えません。与党と野党で条件がちがうところ（法案の通りやすさなど）は、数字の横に書きます。</p></article>
   <article class="rule-card"><span class="eyebrow">02</span><h4>0と「分からない」を分ける</h4><p>確かめられないことは「0」とせず、「未評価」「まだ調べていません」と書きます。</p></article>
   <article class="rule-card"><span class="eyebrow">03</span><h4>足し合わせない</h4><p>3つの物差しは合計しません。お金の多い少ないも、点数に入れません。</p></article>
   <article class="rule-card"><span class="eyebrow">04</span><h4>出どころを必ずつける</h4><p>数字には、国や議会などの公式の記録へのリンクをつけます。</p></article>
  </div>
  <h3 class="subheading">点数の計算</h3>
  <p class="notice" style="padding-top:0">①公約の具体性・②進捗率・③努力の計算方法は、ここで全部見られます。 <button type="button" class="text-button" data-action="score-method">点数の決め方を開く ↗</button></p>
  <h3 class="subheading">比べるときに外している人</h3>
  <ul class="rule-list"><li>大臣など（${term('政府側')}）として答える月が、1年のうち6か月以上の人。質問する立場ではないためです。</li><li>${term('議長')}・副議長として会議を進める発言だけの人。</li><li>同じ名前の人がいて、発言を区別できない人（2人）。0点ではなく「未評価」にします。</li></ul>
  <p class="muted-line">外した人も、「含める」を選べばランキングで見られます。</p>
  <h3 class="subheading">${term('赤札')}のルール（まだだれにも付けていません）</h3>
  <p class="notice" style="padding-top:0">お金の使い道を見えにくくする法案（${term('抜け穴')}）に賛成した記録に付けます。抜け穴かどうかは、次の4つで決めます。</p>
  <ol class="rule-list"><li>お金の使い道の公開を、減らす・遅らせる</li><li>領収書を出さなくていい範囲を、広げる</li><li>${term('監査','チェック（監査）')}を、弱める・対象から外す</li><li>罰や返金のルールを、なくす・軽くする</li></ol>
  <details class="more"><summary>いま付けていない理由</summary><ul><li>いま集めている期間（第211〜222回国会）には、この4つに当たって成立した法案が見つかっていません。</li><li>参議院の押しボタン式の投票しか、議員ひとりずつの賛否が公式の記録に残りません。衆議院や起立での採決は、個人の賛否が分かりません。</li><li>対象にする法案のリストを先に公開してから、付け始めます。休んだ人や記録がない人を「賛成」とは数えません。</li></ul></details>
  <h3 class="subheading">使っているデータ（AI・研究にも使えます）</h3>
  <p class="notice" style="padding-top:0">このサイトの数字は、下のファイルにまとまっています。だれでも読めます。AIに読ませるときは、<a class="inline-link" href="llms.txt" target="_blank" rel="noopener">llms.txt</a> と <a class="inline-link" href="catalog.json" target="_blank" rel="noopener">catalog.json</a>（項目の説明つき）を渡してください。</p>
  <div class="table-wrap"><table><thead><tr><th>ファイル</th><th>中身</th><th>もとの記録</th></tr></thead><tbody>${DATASETS.map(([f,d,s])=>`<tr><td><a class="inline-link" href="data/${f}" target="_blank" rel="noopener">${f}</a></td><td>${esc(d)}</td><td>${esc(s)}</td></tr>`).join('')}</tbody></table></div>
  <details class="more"><summary>くわしく（使うときの条件）</summary><ul><li>出どころ（POLITICS OS と、もとの公式の記録）を書けば、自由に使えます（${'CC BY 4.0'}）。</li><li>議員の写真は Wikimedia Commons のもので、写真ごとに別の条件があります。議員の詳細に書いた条件にしたがってください。</li><li>データの入手日：${esc(M.fetchedAt||'')}。名簿は${esc(M.rosterAsOf?.['衆議院']||'')}・${esc(M.rosterAsOf?.['参議院']||'')}。与党の判定は${esc(c?.asOf||'')}時点。自動では更新していません。</li><li>AIが読み取った部分（選挙公報の公約）は、その旨と検算の結果を書いています。</li></ul></details>
  <h3 class="subheading">変更の記録</h3>
  <p class="notice" style="padding-top:0">数え方を変えたり、まちがいを直したりしたら、ここに残します。</p>
  <ol class="changelog">${CHANGELOG.map(([d,t])=>`<li><time>${d}</time><span>${esc(t)}</span></li>`).join('')}</ol>`;
}

// ---- 公費 (public money per seat). Averages from the 衆議院 budget; never anyone's income, never part of a score ----
const man=y=>`${Math.round(y/1e4).toLocaleString()}万円`;
const MONEY_COL={secretary:'#2f4a3a',salary:'#7a5a2e',stay:'#b8892a',legislative:'#8a8f5a',travel:'#c9b98a'};
function moneyBar(c){return `<div class="money-bar" role="img" aria-label="${c.items.map(i=>`${i.label} ${man(i.perSeatYen)}`).join('、')}">${c.items.map(i=>`<i style="width:${i.share}%;background:${MONEY_COL[i.key]||'#999'}" title="${esc(i.label)} ${i.share}%"></i>`).join('')}</div>`;}
function renderMoney(){
  if(waitView())return;
  const c=DB.meta.records?.publicCost;if(!c){$('#view').innerHTML='<div class="empty"><strong>公費のデータを読み込めませんでした</strong></div>';return;}
  const yes=t=>t==='○'?'<b class="money-ok">○ 公開</b>':esc(t);
  $('#view').innerHTML=`<h3 class="view-heading">公費：国会議員1議席に、年間いくら使われている？</h3>
  <p class="notice">${esc(c.house)}の${esc(c.fiscalYear)}予算（案）のうち、議員に直接かかわる主な5項目を、${c.seats}議席で割った平均です。<b>議員本人の年収ではありません。</b>実際の支出は議員ごとに違い、議員会館・宿舎などの費用は含みません。</p>
  <div class="money-hero"><span class="eyebrow">${esc(c.house)}議員1議席あたり・年間の主な公費（予算の平均）</span><strong>約${man(c.perSeatYen)}</strong>${moneyBar(c)}
   <ol class="money-legend">${c.items.map(i=>`<li><i style="background:${MONEY_COL[i.key]}"></i><span>${esc(i.label)}</span><b>${man(i.perSeatYen)}</b><small>${i.share}%</small></li>`).join('')}</ol>
   <p class="muted-line">金額・割合は四捨五入。計算：各項目の予算額 ÷ ${c.seats}議席。出典：<a class="inline-link" href="${esc(c.source.url)}" target="_blank" rel="noopener noreferrer">${esc(c.source.title)} ↗</a></p></div>
  <h3 class="subheading">5つの費用：何のため？ 金額の根拠は？ 使い道は確かめられる？</h3>
  <div class="money-cards">${c.items.map((i,k)=>`<article class="money-card" style="border-top-color:${MONEY_COL[i.key]}"><span class="eyebrow">0${k+1}</span><h4>${esc(i.label)}</h4><p class="money-amt">年 約${man(i.perSeatYen)}<small>（予算 ${i.budgetMillion.toLocaleString()}百万円 ÷ ${c.seats}）</small></p>
    ${i.parts?`<p class="muted-line">内訳：${i.parts.map(x=>`${esc(x.label)} 約${man(x.perSeatYen)}`).join('・')}</p>`:''}
    <dl><dt>何のため？</dt><dd>${esc(i.purpose)}</dd><dt>金額の決まり方</dt><dd>${esc(i.basis)}</dd><dt>妥当か考える点</dt><dd>${esc(i.check)}</dd><dt>使い道は確かめられる？</dt><dd>${esc(i.useOpen)}</dd></dl>
    ${i.law?`<a class="source-link" href="${esc(i.law.url)}" target="_blank" rel="noopener noreferrer">${esc(i.law.title)}（e-Gov法令検索） ↗</a>`:''}</article>`).join('')}</div>
  <h3 class="subheading">見えること・まだ見えないこと</h3>
  <div class="table-wrap"><table class="money-table"><thead><tr><th>公費</th><th>金額は分かる？</th><th>実際の使い道は分かる？</th><th>成果は分かる？</th></tr></thead><tbody>${c.items.map(i=>`<tr><td>${esc(i.label)}</td><td>${yes(i.amountOpen)}</td><td>${esc(i.useOpen)}</td><td>${esc(i.outcome)}</td></tr>`).join('')}</tbody></table></div>
  <div class="group-note"><b>このサイトの考え方：</b>予算が必要な理由と、その予算が成果に結びついているかは別の問題です。「成果がまだ分からない」と「成果がゼロ」は分けて扱います。公費の額で議員を点数化したり、「発言1回あたり○円」のような割り算はしません。<br>問いは「この公費を使って、その議員は具体的に何をして、何を実現したか」。各議員の「行動」「結果」の記録と並べて、判断は読む人に委ねます。</div>
  <h3 class="subheading">このほかにかかる費用（上の合計に含まない）</h3>
  <ul class="money-excluded">${c.excluded.map(x=>`<li>${esc(x.label)}${x.budgetMillion?`：${x.budgetMillion.toLocaleString()}百万円（衆議院全体）`:''}${x.note?`：${esc(x.note)}`:''}</li>`).join('')}</ul>
  <h3 class="subheading">参議院について</h3><p class="notice" style="padding-top:0">${esc(c.sangiin.note)} 出典：<a class="inline-link" href="${esc(c.sangiin.source.url)}" target="_blank" rel="noopener noreferrer">${esc(c.sangiin.source.title)} ↗</a></p>
  <h3 class="subheading">調査研究広報滞在費の使い道の公開</h3><p class="notice" style="padding-top:0">状態：<b>${esc(c.stayReport.status)}</b>。${esc(c.stayReport.note)}</p>
  <p class="muted-line">確認日 ${esc(c.asOf)}。${(c.otherSources||[]).map(s=>`<a class="inline-link" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a>`).join('　')}</p>`;
}
function moneyShort(m){const c=DB.meta.records?.publicCost,t=m.transp||{};
  const tax=c?(m.house==='衆議院'?`<p>この議席にかかる税金は、年 <b>約${man(c.perSeatYen)}</b>（${term('衆議院')}の予算を議席の数で割った平均。この人が使った額ではありません）。</p>`:`<p>${term('歳費','給料')}・活動費・秘書など、税金の使い方の決まりは${term('衆議院')}と同じです。</p>`):'';
  const rep=t.listed?`<p>お金の報告をする団体（${term('関係政治団体')}）が <b>${t.orgs}団体</b>。${term('収支報告書','お金の報告書')}は <b>${t.reports||0}件</b>にリンクしています。</p>`:`<p>お金の報告をする団体は、国の名簿にのっていません（未確認）。</p>`;
  return tax+rep;}
function moneyMember(m){const c=DB.meta.records?.publicCost;if(!c)return '';
  const items=c.items.map(i=>`<li><span>${esc(i.label)}</span><b>${m.house==='衆議院'?`約${man(i.perSeatYen)}`:'同じ制度'}</b></li>`).join('');
  return `<h4 class="mini-h">この議席にかかる主な公費（制度・予算の平均）</h4>${m.house==='衆議院'?`<p class="muted-line">衆議院の${esc(c.fiscalYear)}予算（案）を${c.seats}議席で割った平均：<b>年 約${man(c.perSeatYen)}</b>。この議員が実際に使った額ではありません。</p>`:`<p class="muted-line">${esc(c.sangiin.note)}</p>`}<ul class="money-mini">${items}</ul>
  <p class="muted-line">調査研究広報滞在費の使途報告：<b>${esc(c.stayReport.status)}</b>（初回の公開期限 ${esc(c.stayReport.firstDeadline)}）。公開されたら、この議員の報告へのリンクを載せます。 <button type="button" class="text-button" data-action="money">公費の内訳と見方 ↗</button></p>`;}

// ---- plain words: glossary of political terms (tap a dotted word to see what it means) ----
const TERMS={
  'GDP':'国内総生産。1年間に国の中で新しく生み出された、もうけや豊かさの合計です。',
  '赤札':'このサイトの印。お金の使い道をかくせる法案（抜け穴）に、賛成した記録1回につき1枚つけます。まだだれにも付けていません。',
  '透明性':'お金の使い方や、決めた理由を、外の人が確かめられるように説明しているかどうかです。',
  '名誉毀損':'人の評判を、事実でないことや根拠のない決めつけで下げることです。法律で罰せられることがあります。',
  '国会議員':'国のルール（法律）を決める人。選挙で選ばれます。',
  '衆議院':'国会にある2つの議会の1つ。465人。任期は4年で、途中で解散することもあります。',
  '参議院':'国会のもう1つの議会。248人。任期は6年で、3年ごとに半分を選びます。',
  '会派':'国会の中で一緒に動く議員のグループ。ふつうは政党ごとに作ります。',
  '与党':'内閣（政府）をつくっている側の政党。',
  '野党':'内閣に入っていない側の政党。政府の仕事をチェックします。',
  '法案':'法律の案。国会で賛成が多いと、法律になります。',
  '成立':'法案が国会で認められて、法律になること。',
  '採決':'賛成か反対かを決める投票。',
  '本会議':'議員全員が集まって、最後に決める会議。',
  '委員会':'テーマごとに少ない人数で法案を話し合う会議。',
  '小選挙区':'1つの地区から1人だけを選ぶ選挙。',
  '比例代表':'政党の名前に投票して、票の割合で議席を分ける選挙。',
  '選挙公報':'選挙の前に配られる、候補者の約束がのった紙。',
  '公約':'選挙のときに「これをやります」と約束したこと。',
  '質問主意書':'議員が文書で政府に質問するしくみ。政府も文書で答えます。',
  '答弁':'国会での質問に、大臣などが答えること。',
  '歳費':'国会議員の給料。月129万4千円です。',
  '公設秘書':'税金で雇われる、議員のスタッフ。1人の議員に3人までです。',
  '立法事務費':'法律づくりの調査に使うお金。議員ではなく、会派に渡されます。',
  '旧文通費':'議員の活動費。月100万円。いまは「調査研究広報滞在費」という名前です。',
  '政党交付金':'税金から政党に配られるお金。',
  '収支報告書':'政治団体が、お金の出入りを国などに報告する書類。',
  '関係政治団体':'議員と関係があると届け出された、政治のお金を集める団体。',
  '抜け穴':'お金の使い道を見えにくくするルールのこと。',
  '監査':'お金の使い方を、ほかの人がチェックすること。',
  '政府側':'大臣・副大臣など、政府として答える立場。',
  '議長':'国会の会議を進める、いちばん上の役。',
  '委員長':'委員会の会議を進める役。',
  '国会会議録':'国会で話されたことを、すべて文字にした公式の記録。',
  '過半数':'半分より多いこと。衆議院は465議席なので233議席、参議院は248議席なので125議席です。',
};
function term(w,label){const k=TERMS[w]?w:null;return k?`<button type="button" class="term" data-term="${esc(k)}">${esc(label||w)}</button>`:esc(label||w);}
function renderWords(){const el=$('#words-list');if(!el)return;el.innerHTML=Object.entries(TERMS).map(([k,v])=>`<div><dt id="word-${esc(k)}">${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('');}
let TIP=null;
function closeTip(){if(TIP){TIP.remove();TIP=null;document.querySelectorAll('.term[aria-expanded=true]').forEach(b=>b.setAttribute('aria-expanded','false'));}}
function openTip(btn){
  closeTip();const k=btn.dataset.term;if(!TERMS[k])return;
  TIP=document.createElement('div');TIP.className='term-tip';TIP.id='term-tip';TIP.setAttribute('role','tooltip');
  TIP.innerHTML=`<b>${esc(k)}</b>${esc(TERMS[k])}`;
  (btn.closest('dialog')||document.body).appendChild(TIP);
  btn.setAttribute('aria-expanded','true');btn.setAttribute('aria-describedby','term-tip');
  const r=btn.getBoundingClientRect(),W=document.documentElement.clientWidth,w=Math.min(300,W-24);
  TIP.style.width=w+'px';
  const left=Math.max(12,Math.min(r.left+r.width/2-w/2,W-w-12));
  TIP.style.left=left+'px';TIP.style.top=(r.bottom+8)+'px';
  if(r.bottom+8+TIP.offsetHeight>innerHeight-8)TIP.style.top=Math.max(8,r.top-8-TIP.offsetHeight)+'px';
}
document.addEventListener('click',e=>{const b=e.target.closest('.term');if(b){e.preventDefault();e.stopPropagation();if(TIP&&b.getAttribute('aria-expanded')==='true')closeTip();else openTip(b);return;}if(TIP&&!e.target.closest('.term-tip'))closeTip();},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&TIP){closeTip();}});
document.addEventListener('scroll',closeTip,true);

// ---- number tiles: the 4 things to see at a glance ----
function ppShort(m){const w=m.pp?.why||'';if(/比例/.test(w))return `${term('比例代表')}で当選。本人の${term('選挙公報')}がありません`;if(/公開が終了/.test(w))return `${term('選挙公報')}の公開が終わっています`;if(/取得できず/.test(w))return `${term('選挙公報')}を取得できませんでした`;return `${term('選挙公報')}から読み取れませんでした`;}
function cardNote(m){
  if(m.activityStatus==='homonym')return '';
  const sp=m.sp||{},n=[];
  if(sp.presiding&&!sp.meet)n.push(`${term('議長')}・副議長は、慣例で国会で質問しません（会議を進めた ${sp.presiding}回は数えていません）。`);
  else if(sp.chair)n.push(`${term('委員長')}などとして会議を進めた ${sp.chair}回は、数えていません。`);
  if(m.gov&&!sp.gov&&!m.gov.former)n.push(`首相官邸の名簿では、いまは「${esc(m.gov.posts[0])}」です（大臣などとしての${term('答弁')}は、まだ記録にありません）。`);
  else if(sp.gov&&!sp.meet)n.push(`大臣などとしての${term('答弁')}（${sp.gov}回）は数えていません。`);
  if(partialTerm(m))n.push('2026年2月の選挙で初めて当選しました。');
  return n.length?`<p class="card-note">${n.join('<br>')}</p>`:'';
}
function tiles(m,noRef){
  const sp=m.sp||{},b=m.bills,t=m.transp,x=m.pp,sc=m.score||{};
  const ax=(cls,no,label,val,unit,sub,bar)=>`<div class="axis-tile${cls?' '+cls:''}"><span class="ax-label"><i>${no}</i>${label}</span><b class="ax-num">${val}<small>${unit}</small></b><span class="ax-bar${bar==null?' na':''}">${bar==null?'':`<i style="width:${Math.max(bar,1)}%"></i>`}</span><span class="ax-sub">${sub}</span></div>`;
  const spec=sc.spec!=null?ax('','①','公約の具体性',sc.spec,'点',`${sc.specN}人中${sc.specRank}位・公約${x.n}こ`,sc.spec):ax('na','①','公約の具体性','—','',x&&x.n!=null&&x.n<3?`公約が${x.n}こ（3こ未満は点数なし）`:x&&x.n==null?ppShort(m):'まだ調べられていません',null);
  const prog=ax('na','②','進捗率','準備中','',PROGRESS_NA,null);
  const eff=m.activityStatus==='homonym'?ax('na','③','努力','—','','同じ名前の議員がいて数えられません',null):sc.action==null?ax('na','③','努力','—','','まだ調べられていません',null):ax('','③','努力',sc.action,'点',sc.action===0?'この1年、国会で話した記録がありません':`話した会議 ${sp.meet}回・${sc.actionN}人中${sc.actionRank}位`,sc.action);
  const ref=`<ul class="ref-strip" aria-label="参考の記録（点数に入れません）"><li><span>法律になった数</span><b>${b?b.passed+'本':'—'}</b></li><li><span>文書での質問（${term('質問主意書')}）</span><b>${m.q??0}回</b></li><li><span>お金の報告をする団体</span><b>${t&&t.listed?t.orgs+'団体':'—'}</b></li></ul>`;
  return `<div class="axis-tiles">${spec}${prog}${eff}</div>${noRef?'':ref}`;
}

let SPEECHES=null;
function getSpeeches(){if(!SPEECHES)SPEECHES=fetch('data/speeches.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}).catch(e=>{SPEECHES=null;throw e;});return SPEECHES;}
function scoreDetail(m){
  const sc=m.score||{},same=DB.members.filter(x=>kaihaKey(x)===kaihaKey(m)),b=m.bills||{},sp=m.sp||{};
  const medOf=(arr,f)=>median(arr.map(f).filter(v=>v!=null));
  const meanOf=(arr,f)=>{const v=arr.map(f).filter(x=>x!=null);return v.length?Math.round(v.reduce((a,c)=>a+c,0)/v.length*100)/100:null;};
  const rk=(i,v)=>i?rankText(i.rank,i.n,i.tie,v===0):'—';
  const pr=m.peer;
  const src=(href,t='元の記録')=>href?`<a class="src-link" href="${esc(href)}" ${href.startsWith('#')?'':'target="_blank" rel="noopener noreferrer"'}>${t} ↗</a>`:'';
  const peerCell=(k,val)=>outOfCmp(m)?`${outOfCmp(m)}のため比較外`:!pr?'与野党が不明のため比較外':`${rk(pr.rk[k],val)}<small>中央値 ${pr.med[k]??'—'}</small>`;
  const row=(label,val,unit,score,info,cmp,k,href)=>`<tr><th scope="row">${label}${src(href)}</th><td><b>${val==null?'—':val+unit}</b></td><td>${score==null?'—':`${score}点`}</td><td>${rk(info,val)}</td><td>${k?peerCell(k,val):'—'}</td><td>${cmp}</td></tr>`;
  const kk=kokkaiUrl(m);
  const homo=m.activityStatus==='homonym';
  return `${tiles(m,true)}<p class="rank-hint">順位は、数字が小さいほど上です。</p>
  <details class="more"><summary>点数と順位のくわしい内訳</summary>${activityNote(m)}<p class="card-dataline">${dataLine()}</p>${scorePanel(m)}
  <section class="dialog-section"><h3>点数の内訳</h3>
  <div class="table-wrap score-table"><table><thead><tr><th>もとの数字</th><th>この議員</th><th>点数</th><th>全議員での順位</th><th>同じ立場での順位${pr?`<small>${esc(pr.key)}・${pr.n}人</small>`:''}</th><th>比べる目安</th></tr></thead><tbody>
  ${(()=>{const x=m.pp,ck=x&&x.ck,avg=ck&&x.n?Math.round((ck.t+ck.a+ck.dl+ck.ms)/x.n*10)/10:null;return row('公約の4つのチェックの平均（具体性の点数のもと）',avg,'点',sc.spec,m.rk?.spec,`全議員の中央値 ${medOf(DB.members,specVal)??'—'}点（具体性）`,'spec','#pp-section');})()}
  ${row('発言のあった会議の回数（努力の点数のもと）',homo?null:sp.meet,'回',sc.action,m.rk?.meet,`全議員の中央値 ${medOf(DB.members,meetVal)}回 ／ 同じ会派の中央値 ${medOf(same,meetVal)}回`,'meet',homo?null:kk)}
  ${row('発言回数（政府側・議長・委員長を除く）',homo?null:sp.rest,'回',null,m.rk?.rest,`全議員の中央値 ${medOf(DB.members,restVal)}回 ／ 同じ会派の中央値 ${medOf(same,restVal)}回`,'rest',homo?null:kk)}
  ${row('政府側（大臣など）としての発言',homo?null:sp.gov,'回',null,null,'点数には入れません',null,homo?null:kk)}
  ${row('委員長などとして議事を進めた会議',homo?null:(sp.chair??0),'回',null,null,sp.chairMain?`主に${esc(sp.chairMain.name)}。点数には入れません`:'点数には入れません',null,homo?null:kk)}
  ${row('筆頭で出した法律案',b.lead,'件',null,m.rk?.lead,`全議員の平均 ${meanOf(DB.members,leadVal)}件 ／ 同じ会派の平均 ${meanOf(same,leadVal)}件`,'lead','#bills-detail')}
  ${row('参考：提出に加わった法律案の成立',b.passed,'件',null,m.rk?.passed,`成立が1件以上ある議員は全体で ${DB.members.filter(x=>(x.bills?.passed||0)>0).length}人`,'passed','#bills-detail')}
  ${row('質問主意書（文書での質問）',m.q??0,'件',null,m.rk?.q,`提出が1件以上ある議員は全体で ${DB.members.filter(x=>(x.q||0)>0).length}人`,'q','#questions-detail')}
  ${row('超党派の法律案（衆法・提出会派2つ以上）',b.cross,'件',null,null,b.cross==null?'参議院は提出会派を取得できないため未収録':'筆頭・共同として加わった件数',null,'#bills-detail')}
  </tbody></table></div>
  <ul class="calc-lines">
   <li><b>① 公約の具体性 ${sc.spec==null?'未評価':sc.spec+'点'}</b> ＝ 公約1こごとの4つのチェック（何を・どうする・いつまでに・どこまで）の平均 ÷ 4 × 100${m.pp?.ck?`。何を ${m.pp.ck.t}こ・どうする ${m.pp.ck.a}こ・いつまでに ${m.pp.ck.dl}こ・どこまで ${m.pp.ck.ms}こ（公約${m.pp.n}こ中）`:''}${sc.spec==null?`。${esc(specNaText(m))}`:''}</li>
   <li><b>② 進捗率 準備中</b> ＝ 公約と国会での動き（質問・法案・成立）を結びつけてから計算します</li>
   <li><b>③ 努力 ${sc.action==null?'未評価':sc.action+'点'}</b> ＝ 発言のあった会議の回数の点数（現職のうち、回数がこの議員より少ない人の割合×100）${sc.action==null?'。同姓同名で発言を確定できないため未評価':''}</li>
   <li><b>参考：法律になった数 ${b.passed??'—'}件</b> ＝ 提出に加わった法律案（筆頭 ${b.lead??'—'}件・共同 ${m.house==='参議院'?'未公開':(b.co??0)+'件'}）のうち成立した件数（筆頭で成立 ${b.leadPassed??0}件・共同で成立 ${m.house==='参議院'?'—':(b.coPassed??0)+'件'}）</li>
   ${b.chair||b.other?`<li>点数・件数に入れていないもの：${b.chair?`委員長として提出した委員会の法案 ${b.chair}件`:''}${b.chair&&b.other?'、':''}${b.other?`決議・規則など ${b.other}件`:''}</li>`:''}
  </ul></section></details>`;
}
function speechSection(m,sp){
  const link=m.activityStatus==='homonym'?'':`<a class="source-link" href="${esc(kokkaiUrl(m))}" target="_blank" rel="noopener noreferrer">国会の記録（会議録）で確かめる ↗</a>`;
  if(m.activityStatus==='homonym')return '';
  if(!sp)return `<p class="muted-line">発言の記録は、まだ取り込んでいません。</p>${link}`;
  if(!sp.n)return `<p class="muted-line">${esc(periodLabel())}の会議録に、発言はありません。</p>${link}`;
  const pct=x=>Math.round(x/sp.n*100);
  const item=([d,h,mt,pos,sn,url],snip)=>`<li><a href="${esc(url)}" target="_blank" rel="noopener noreferrer"><time>${esc(d)}</time><span>${esc(h)} ${esc(mt)}${pos?`（${esc(pos)}）`:''}</span></a>${snip?`<small>${esc(sn)}…</small>`:''}</li>`;
  const charts=sp.months?`${monthChart('発言のあった会議の回数（政府側・議長・委員長を除く）',sp.months,sp.monthlyMeet,'回')}${sp.monthlyGov.some(v=>v)?monthChart('政府側（大臣など）としての発言回数',sp.months,sp.monthlyGov,'回'):''}`:'';
  return `<h4 class="mini-h">最近、話した会議</h4><ul class="recent-list">${sp.recent.filter((r,i,a)=>a.findIndex(q=>q[0]===r[0]&&q[1]===r[1]&&q[2]===r[2])===i).slice(0,3).map(r=>item(r,false)).join('')}</ul>
  <details class="more"><summary>話した記録のくわしい内訳</summary>
  ${m.mainMeeting?`<p>いちばん多く話した会議は、<b>${esc(m.mainMeeting.name)}</b>です（${m.mainMeeting.count}回）。</p>`:''}
  <h4 class="mini-h">月ごとの推移</h4>${charts}${sessionChart(m,sp)}
  <h4 class="mini-h">質問と答弁のやり取り</h4>${exchangeBlock(m,sp.ex)}
  <h4 class="mini-h">どの立場で話したか</h4><ul class="role-list">${sp.roles.map(([k,v])=>`<li><span>${esc(k)}</span><span class="bar"><i style="width:${Math.max(1,pct(v))}%"></i></span><b>${v}件</b></li>`).join('')}</ul>
  <p class="muted-line">会議録の肩書（大臣・議長など）で分けています。法案を出した人としての答弁は、肩書が付かないため「それ以外」に入ります。</p>
  <h4 class="mini-h">話すことが多い会議</h4><ul class="rec-list">${sp.meetings.map(([k,v])=>`<li><span>${esc(k)}</span><small>${v}件</small></li>`).join('')}</ul>
  <h4 class="mini-h">最近の発言と、話し始めのことば（最大10件）</h4><ul class="recent-list">${sp.recent.map(r=>item(r,true)).join('')}</ul></details>${link}`;
}
let RECORDS=null;
function getRecords(){if(!RECORDS)RECORDS=fetch('data/records.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}).catch(e=>{RECORDS=null;throw e;});return RECORDS;}
const avatar=(m,big)=>m.photo?`<img class="avatar${big?' big':''}" src="photos/${esc(m.id)}.${esc(m.photo)}" alt="${esc(m.name)}の写真" loading="lazy" decoding="async" width="${big?96:48}" height="${big?96:48}">`:`<span class="monogram${big?' big':''}" aria-hidden="true">${esc(m.name.slice(0,1))}</span>`;
const CRIT={'1':'公開','2':'領収書・明細','3':'監査','4':'罰則・返還','制度':'制度'};
const KUBUN={'１':'政党支部等','２':'資金管理団体等','３':'政策研究団体'};
const kubunLabel=k=>String(k).split('・').map(x=>x.replace(/^[１２３]/,d=>KUBUN[d]).replace('（構）','（構成員）').replace('（主）','（主宰）')).join('・');
const STATUS_CLS={'成立':'dark','可決':'dark','否決':'amber','一院で可決':'purple','未成立':'gray'};
function partyPledges(m){return DB.pledges?DB.pledges.parties.filter(p=>(m.parties||[]).includes(p.party)):[];}
function pledgeSummary(m){const pp=partyPledges(m).filter(p=>p.status==='ok');if(!pp.length)return '所属政党の公約：該当なし（院内会派・無所属など）';const n=pp.reduce((a,p)=>a+p.pledges.length,0),v=pp.reduce((a,p)=>a+p.pledges.filter(x=>x.verifiable).length,0);return `所属政党の公約（政治資金・透明性）${n}件・うち具体的 ${v}件`;}
const roleTag=m=>m.role?`<span class="role-tag" title="会議録で確認できた直近の政府側の肩書（${esc(m.role.date)}）">${esc(m.role.label)}</span>`:'';
const ownBills=m=>m.bills?m.bills.lead+m.bills.co:0;
function billLine(m){if(!m.bills)return '';const b=m.bills;const extra=`${b.chair?`・委員長として提出 ${b.chair}件`:''}${b.other?`・決議など ${b.other}件`:''}`;return m.house==='参議院'?`筆頭の法律案 ${b.lead}件（共同発議は未収録）${extra}`:`筆頭の法律案 ${b.lead}件・共同 ${b.co}件・賛成者 ${b.sup}件${extra}`;}
function resultLine(m){if(!m.bills)return '<em class="na">未収録</em>';const b=m.bills,rng=DB.meta?.records?`第${DB.meta.records.billSessions[0]}〜${DB.meta.records.billSessions[1]}回国会`:'';return `<strong>提出に加わった法律案の成立 ${b.passed}件<small>筆頭 ${b.leadPassed??0}件・共同 ${m.house==='参議院'?'—（未公開）':(b.coPassed??0)+'件'}・${rng}</small></strong>`;}
function transpLine(m){const t=m.transp;if(!t)return '<em class="na">未収録</em>';if(!t.listed&&!t.reports)return '<em class="na">総務省名簿に掲載なし（未確認）</em>';return `<strong>${t.listed?`関係政治団体 ${t.orgs}団体`:'関係政治団体：名簿に掲載なし'}<small>収支報告書（令和6年分・総務大臣届出分）${t.reports||0}件にリンク</small></strong>`;}
function actionLine(m){
  if(m.activityStatus==='homonym')return `<strong>要確認（同姓同名）<small>${esc(billLine(m))}</small></strong>`;
  const sp=m.sp||{};
  return `<strong>発言のあった会議 ${sp.meet??'—'}回<small>発言 ${sp.rest??'—'}回（政府側・議長・委員長としての発言を除く）・${esc(periodLabel())}</small>${sp.chair?`<small>委員長などとして議事を進めた会議 ${sp.chair}回${sp.chairMain?`（${esc(sp.chairMain.name)}${sp.chair>sp.chairMain.count?'など':''}）`:''}・点数に含めない</small>`:''}${sp.gov?`<small>政府側（大臣など）としての発言 ${sp.gov}回</small>`:''}<small>${esc(billLine(m))}</small>${m.mainMeeting?`<small>主な会議：${esc(m.mainMeeting.name)}（${m.mainMeeting.count}回）</small>`:''}<small>質問主意書 ${m.q??0}件${m.bills?.cross!=null?`・超党派の法律案 ${m.bills.cross}件`:''}</small>${m.votes?`<small>参院本会議の投票 ${m.votes.n}回（反対 ${m.votes.no}・投票なし ${m.votes.none}）</small>`:''}</strong>`;
}
function memberCard(m){
    const sc=m.score||{};
    return `<article class="person-card member-card"><div class="person-top rk-click" data-open-member="${esc(m.id)}" role="button" tabindex="0" aria-label="${esc(m.name)}のくわしい記録を開く">${avatar(m)}<div><h3>${esc(m.name)}${roleTag(m)}</h3><p>${esc(m.kana)}${m.legalName?` · 本名 ${esc(m.legalName)}`:''}</p></div></div>
  <p class="card-sub">${term(m.house)}・${seatHtml(m)}</p>
  <p class="card-sub">${term('会派','国会のグループ')}：${esc(m.kaihaName)}　${m.house==='衆議院'?`当選 ${esc(m.terms)}回`:`任期は${esc(m.termEnd||'—')}まで`}</p>
  ${tiles(m)}
  ${cardNote(m)}
  ${xrLine(m)}
  <p class="card-dataline">${m.side==='与党'||m.side==='野党'?term(m.side):esc(m.side)}${m.band?`・${esc(m.band)}`:''}${outOfCmp(m)?`・${outOfCmp(m)}（順位は参考）`:''}　<button type="button" class="score-how" data-action="score-method">点数の決め方</button></p>
  <div class="member-links"><a href="${m.profileUrl}" target="_blank" rel="noopener noreferrer">公式プロフィール ↗</a>${m.activityStatus==='homonym'?'':`<a href="${esc(kokkaiUrl(m))}" target="_blank" rel="noopener noreferrer">${term('国会会議録','国会の記録')}を見る ↗</a>`}</div>
  <button data-member="${esc(m.id)}" aria-label="${esc(m.name)}のくわしい記録と出典を開く">くわしく見る（内訳・出典） <span>↗</span></button>
  ${m.caseId?`<button data-person="${m.caseId}" aria-label="${esc(m.name)}の事例記録を開く">政党交付金の事例記録を見る <span>↗</span></button>`:''}</article>`;
}

function multiSelect(id,label,options,selected){
  const all=options.every(o=>selected.has(o.value));
  const summary=all?'すべて':selected.size===0?'なし':`${selected.size}件選択`;
  return `<details class="multi" id="${id}"><summary>${label}：${summary}</summary><div class="multi-panel"><div class="multi-actions"><button type="button" data-ms="${id}" data-ms-all="1">すべて選択</button><button type="button" data-ms="${id}" data-ms-all="0">すべて解除</button></div>${options.map(o=>`<label><input type="checkbox" data-ms-item="${id}" value="${esc(o.value)}" ${selected.has(o.value)?'checked':''}> ${esc(o.label)}</label>`).join('')}</div></details>`;
}
const MS = { 'ms-house':()=>R.houses, 'ms-kaiha':()=>R.kaiha, 'ms-election':()=>R.election, 'ms-rk-house':()=>R.rk.houses, 'ms-rk-kaiha':()=>R.rk.kaiha, 'ms-rk-side':()=>R.rk.side, 'ms-rk-band':()=>R.rk.band };
function kaihaOptions(){const seen=new Map();for(const m of DB.members){const k=kaihaKey(m);if(!seen.has(k))seen.set(k,{value:k,label:`${m.house==='衆議院'?'衆':'参'}｜${m.kaihaName}`,n:0});seen.get(k).n++;}return [...seen.values()].sort((a,b)=>a.value.localeCompare(b.value,'ja')||b.n-a.n).map(o=>({...o,label:`${o.label}（${o.n}）`}));}

function filteredMembers(){
  const q=R.search.replace(/\s/g,'');
  const rows=DB.members.filter(m=>R.houses.has(m.house)&&R.kaiha.has(kaihaKey(m))&&R.election.has(m.electionType)&&(!q||`${m.name}${m.legalName||''}${m.kana}${m.kaihaName}${m.district}`.includes(q)));
  const v=x=>x==null?-1:x;
  if(R.sort==='speech-desc')rows.sort((a,b)=>v(b.speeches)-v(a.speeches));
  else if(R.sort==='speech-asc')rows.sort((a,b)=>(a.speeches==null?1e9:a.speeches)-(b.speeches==null?1e9:b.speeches));
  else if(R.sort==='money-desc')rows.sort((a,b)=>v(b.moneySpeeches)-v(a.moneySpeeches));
  else if(R.sort==='bills-desc')rows.sort((a,b)=>ownBills(b)-ownBills(a)||a.kana.localeCompare(b.kana,'ja'));
  else rows.sort((a,b)=>a.kana.localeCompare(b.kana,'ja'));
  return rows;
}
function renderPeople(){
  if(waitView())return;
  $('#view').innerHTML=`<h3 class="view-heading">いまの国会議員 ${DB.members.length}人</h3><p class="notice">${term('衆議院')} ${DB.meta.counts['衆議院']}人・${term('参議院')} ${DB.meta.counts['参議院']}人。名前・ふりがな・県でさがせます。<br>「話した回数」は国会で話した量です。よい・わるいの評価ではありません。</p>
  <details class="more"><summary>この一覧のくわしい説明</summary><p class="notice">欠員は衆参で1人ずつ。名簿は${esc(DB.meta.rosterAsOf['衆議院'])}・${esc(DB.meta.rosterAsOf['参議院'])}。発言件数は${periodLabel()}の${term('国会会議録')}から数えた活動の量で、成果や質ではありません。<br>${dataLine()}</p></details>
  <div class="controls"><label class="search-wrap"><span aria-hidden="true">⌕</span><input id="search" aria-label="名前・ふりがな・県・政党で検索" placeholder="名前・ふりがな・県・政党で検索" value="${esc(R.search)}"></label>
  ${multiSelect('ms-house','衆議院・参議院',HOUSES.map(h=>({value:h,label:h})),R.houses)}
  ${multiSelect('ms-kaiha','国会のグループ（会派）',kaihaOptions(),R.kaiha)}
  ${multiSelect('ms-election','選ばれ方',ELECTIONS.map(e=>({value:e,label:e})),R.election)}
  <select id="sort" aria-label="並び順"><option value="kana">五十音順</option><option value="speech-desc">国会で話した回数が多い順</option><option value="speech-asc">国会で話した回数が少ない順</option><option value="money-desc">「政治資金」について話した回数が多い順</option><option value="bills-desc">出した法案が多い順</option></select></div>
  <div class="result-head"><span id="result-count" role="status" aria-live="polite"></span><span>出典：衆議院・参議院ホームページ、国会会議録検索システム</span></div><div class="person-list" id="people-results"></div><div id="more-sentinel" aria-hidden="true"></div>`;
  $('#sort').value=R.sort;
  $('#search').addEventListener('input',e=>{R.search=e.target.value;R.shown=30;renderResults();});
  $('#sort').addEventListener('change',e=>{R.sort=e.target.value;R.shown=30;renderResults();});
  renderResults();
  const io=new IntersectionObserver(es=>{if(es.some(x=>x.isIntersecting)&&$('#people-results')&&R.shown<filteredMembers().length){R.shown+=30;renderResults(true);}},{rootMargin:'600px'});
  io.observe($('#more-sentinel'));
}
function renderResults(append){
  const rows=filteredMembers(),list=$('#people-results');if(!list)return;
  $('#result-count').textContent=`${rows.length}人を表示中（${Math.min(R.shown,rows.length)}人まで表示） / 全${DB.members.length}人`;
  if(!rows.length){list.innerHTML=`<div class="empty" style="grid-column:1/-1"><strong>一致する議員がいません</strong><p>検索語や絞り込みを変更してください。</p><button class="card-button" style="margin-top:15px" data-action="reset">絞り込みを解除</button></div>`;return;}
  const start=append?list.children.length:0,end=Math.min(R.shown,rows.length);
  const html=rows.slice(start,end).map(memberCard).join('');
  if(append)list.insertAdjacentHTML('beforeend',html);else list.innerHTML=html;
}


function pledgeSection(){
  if(!DB.pledges)return '<p class="notice">党の公約データを読み込めませんでした。</p>';
  const P=DB.pledges;
  return `<h3 class="view-heading" id="pledges" style="margin-top:44px">各党の公約：政治資金・透明性の項目</h3><p class="notice">各党が直近に戦った国政選挙の公式公約から、政治資金・透明性に関する項目だけを抜き出しています（確認日 ${esc(P.asOf)}）。党の約束であり、所属議員個人の約束ではありません。「具体的」は対象と内容が書かれているもの、「期限あり」は期日・条件があるものです。実現したかどうか（結果率）は、対象法案リストの確定後に判定します。</p>
  <div class="pledge-grid">${P.parties.map(p=>`<article class="pledge-card"><h4>${esc(p.party)}</h4><p class="pledge-meta">${esc(p.election||'')}</p>${p.status==='ok'?`<ol class="pledge-list">${p.pledges.map(x=>`<li><div class="pledge-tags">${tag(CRIT[x.criterion]||x.criterion,'dark')}${x.verifiable?tag('具体的','purple'):tag('具体性なし','gray')}${x.hasDeadline?tag('期限あり','amber'):''}</div><b>${esc(x.topic)}</b><q>${esc(x.text)}</q><small>${esc(x.note||'')}${x.quoteCheck?`　照合：${esc(x.quoteCheck)}`:''}</small><a class="source-link" href="${esc(x.sourceUrl)}" target="_blank" rel="noopener noreferrer">出典 ↗</a></li>`).join('')}</ol>`:`<p class="pledge-none">${esc(p.note||'党の公約なし')}</p>`}</article>`).join('')}</div>`;
}

function renderParties(){
  if(waitView())return;
  const groups=new Map();for(const m of DB.members){const k=kaihaKey(m);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(m);}
  const rows=[...groups.entries()].sort((a,b)=>a[0].split('|')[0].localeCompare(b[0].split('|')[0],'ja')||b[1].length-a[1].length);
  $('#view').innerHTML=`${seatMap()}<h3 class="view-heading" style="margin-top:44px">会派ごとの、所属議員と活動量</h3><p class="notice">国会内の「会派」単位です。政党と会派は一致しない場合があります。発言件数は${periodLabel()}の会議録から数えた量で、成果や質ではありません。</p><div class="wide-notice">順位・赤札率は、判定基準と対象法案リストの公開後に表示します。この表は並び替えのための事実の一覧です。</div>
  <div class="table-wrap"><table><thead><tr><th>院</th><th>会派</th><th>人数</th><th>小選挙区・選挙区</th><th>比例</th><th>発言件数（中央値）</th><th>「政治資金」発言がある議員</th><th>議員</th></tr></thead><tbody>${rows.map(([k,ms])=>{const valid=ms.filter(m=>m.speeches!=null);const money=ms.filter(m=>(m.moneySpeeches||0)>0).length;return `<tr><td>${esc(ms[0].house)}</td><td>${esc(ms[0].kaihaName)}</td><td>${ms.length}人</td><td>${ms.filter(m=>m.electionType!=='比例').length}人</td><td>${ms.filter(m=>m.electionType==='比例').length}人</td><td>${median(valid.map(m=>m.speeches))??'—'}件</td><td>${money}人</td><td><button data-kaiha="${esc(k)}">一覧へ ↗</button></td></tr>`;}).join('')}</tbody></table></div>
  <div class="group-note"><strong>中央値を使う理由：</strong>委員長や大臣など役職によって発言が極端に多い人がいるため、平均より実態に近い値を示します。同姓同名で件数を確定できない議員は計算から除いています。</div>${partyMoney()}${pledgeSection()}`;
}

function renderRegions(){
  if(waitView())return;
  if(!R.pref&&!R.block)R.pref=state.region||'東京都';
  const byPref=p=>DB.members.filter(m=>m.prefectures.includes(p));
  const blocks=[...new Set(DB.members.filter(m=>m.block).map(m=>m.block))];
  const mapSvg=DB.map?`<figure class="jp-map"><svg viewBox="${DB.map.viewBox}" role="group" aria-label="日本地図。都道府県を選ぶと、その県から選ばれた国会議員を表示します"><rect class="inset" data-map-pref="沖縄県" x="${DB.map.inset.x}" y="${DB.map.inset.y}" width="${DB.map.inset.w}" height="${DB.map.inset.h}" aria-hidden="true"/>${DB.map.prefs.map(p=>`<path class="pref" data-map-pref="${p.name}" d="${p.d}" tabindex="0" role="button" aria-label="${p.name}（${byPref(p.name).length}人）"><title>${p.name}　${byPref(p.name).length}人</title></path>`).join('')}<g class="map-labels" aria-hidden="true">${DB.map.prefs.map(p=>`<text data-map-label="${p.name}" x="${p.cx}" y="${p.cy}">${p.name.replace(/[都府県]$/,'')}</text>`).join('')}</g><g id="map-pin" class="map-pin" aria-hidden="true" style="display:none"><circle r="7"/><rect class="pin-bg" rx="3"/><text class="pin-text"></text></g></svg><figcaption>地図をタップして、あなたの県を選ぶ<small>地図：地球地図日本（国土地理院）をもとに作成</small></figcaption></figure>`:'';
  $('#view').innerHTML=`<h3 class="view-heading">あなたの県が送り出した、国会議員団</h3><p class="notice">小選挙区（衆議院）と選挙区（参議院）で選ばれた議員を、その都道府県の議員団として表示します。比例代表は都道府県に割り当てず、下のブロック別に分けています。県の経済状況や県民の評価とは関係ありません。</p>
  <div class="map-layout">${mapSvg}<div class="map-side"><label for="region-select" class="eyebrow">都道府県を選ぶ</label><select id="region-select" style="margin-top:10px">${PREFECTURES.map(p=>`<option>${p}</option>`).join('')}</select><div id="region-summary" aria-live="polite"></div></div></div>
  <details class="grid-toggle"><summary>47都道府県の一覧から選ぶ</summary><div class="region-grid">${PREFECTURES.map(p=>`<button data-region="${p}" class="has-record">${p}<small>${byPref(p).length}人</small></button>`).join('')}</div></details>
  <div class="block-row"><span class="eyebrow">比例代表（別枠）</span>${blocks.map(b=>`<button data-block="${esc(b)}">${esc(b)}</button>`).join('')}</div>
  <div id="region-detail" aria-live="polite"></div>`;
  $('#region-select').addEventListener('change',e=>{R.pref=e.target.value;R.block=null;state.region=R.pref;renderRegionDetail();});
  renderRegionDetail();
}
function renderRegionDetail(){
  if(!DB.ready)return;
  const sel=$('#region-select');if(R.pref&&sel)sel.value=R.pref;
  document.querySelectorAll('[data-region]').forEach(b=>{const on=!R.block&&b.dataset.region===R.pref;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});
  document.querySelectorAll('[data-block]').forEach(b=>{const on=b.dataset.block===R.block;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});
  document.querySelectorAll('path[data-map-pref]').forEach(el=>{const on=!R.block&&el.dataset.mapPref===R.pref;el.classList.toggle('selected',on);el.setAttribute('aria-pressed',String(on));});
  document.querySelectorAll('[data-map-label]').forEach(el=>el.classList.toggle('selected',!R.block&&el.dataset.mapLabel===R.pref));
  const pin=$('#map-pin'),pd=DB.map&&!R.block?DB.map.prefs.find(x=>x.name===R.pref):null;
  if(pin){if(pd){pin.style.display='';pin.setAttribute('transform',`translate(${pd.cx},${pd.cy})`);const t=pin.querySelector('text');t.textContent=pd.name;t.setAttribute('x',0);t.setAttribute('y',-16);const w=pd.name.length*15+14;const r=pin.querySelector('rect');r.setAttribute('x',-w/2);r.setAttribute('y',-31);r.setAttribute('width',w);r.setAttribute('height',24);const sel=document.querySelector(`path[data-map-pref="${pd.name}"]`);if(sel)sel.parentNode.insertBefore(sel,document.querySelector('.map-labels'));}else pin.style.display='none';}
  const title=R.block||R.pref;
  const rows=(R.block?DB.members.filter(m=>m.block===R.block):DB.members.filter(m=>m.prefectures.includes(R.pref))).sort((a,b)=>a.house.localeCompare(b.house,'ja')||a.district.localeCompare(b.district,'ja',{numeric:true}));
  const valid=rows.filter(m=>m.speeches!=null);
  const kaiha=Object.entries(rows.reduce((o,m)=>(o[m.kaihaName]=(o[m.kaihaName]||0)+1,o),{})).sort((a,b)=>b[1]-a[1]);
  const sum=$('#region-summary');if(sum)sum.innerHTML=`<div class="summary-card"><span class="eyebrow">${R.block?'比例代表（別枠）':'選んだ都道府県'}</span><strong>${esc(title)}</strong><p><b>${rows.length}</b>人の議員団</p><p>衆議院 ${rows.filter(m=>m.house==='衆議院').length}人 · 参議院 ${rows.filter(m=>m.house==='参議院').length}人</p><a class="card-button" href="#region-detail">議員を見る ↓</a></div>`;
  $('#region-detail').innerHTML=`<div class="region-panel"><div><span class="eyebrow">${R.block?'PROPORTIONAL BLOCK':'LOCAL DELEGATION'}</span><h3>${esc(title)}</h3><p>${R.block?'この比例ブロック・全国比例で選ばれた議員':'この都道府県から選ばれた議員'}：${rows.length}人<br>衆議院 ${rows.filter(m=>m.house==='衆議院').length}人 · 参議院 ${rows.filter(m=>m.house==='参議院').length}人<br>発言件数（中央値・直近1年）：${median(valid.map(m=>m.speeches))??'—'}件<br><button type="button" class="score-how" data-view="rankings">県のランキングを見る ↗</button></p><ul class="kaiha-list">${kaiha.map(([k,n])=>`<li><span>${esc(k)}</span><b>${n}人</b></li>`).join('')}</ul>${!R.block&&R.pref.match(/鳥取|島根|徳島|高知/)?'<p class="member-note">参議院は合区（鳥取・島根、徳島・高知）のため、両県に同じ議員を表示しています。</p>':''}</div><div><div class="person-list">${rows.map(memberCard).join('')}</div></div></div>`;
}

function billItems(rec,idx){return [...idx].sort((x,y)=>(+rec.bills[y].session-+rec.bills[x].session)||(+rec.bills[y].number-+rec.bills[x].number)).map(i=>{const b=rec.bills[i];return `<li><a href="${esc(b.url)}" target="_blank" rel="noopener noreferrer">第${esc(b.session)}回 ${esc(b.kind)}第${esc(b.number)}号　${esc(b.title)} ↗</a><span class="bill-state">${tag(b.status,STATUS_CLS[b.status]||'gray')}${b.status==='未成立'?`<small>公式ページ上の最後の状態：${esc(b.last)}</small>`:''}</span></li>`;}).join('');}
function billGroup(rec,title,idx,open){if(!idx||!idx.length)return `<p class="muted-line">${esc(title)}：記録なし（収録範囲内）</p>`;const passed=idx.filter(i=>rec.bills[i].status==='成立').length;return `<details class="rec-group"${open?' open':''}><summary>${esc(title)} <b>${idx.length}件</b>（うち成立 ${passed}件）</summary><ul class="rec-list">${billItems(rec,idx)}</ul></details>`;}
function voteGroup(rec,s,ch,title,open){const idx=[...s].map((c,i)=>c===ch?i:-1).filter(i=>i>=0).reverse();if(!idx.length)return `<p class="muted-line">${esc(title)}：0回</p>`;return `<details class="rec-group"${open?' open':''}><summary>${esc(title)} <b>${idx.length}回</b></summary><ul class="rec-list">${idx.map(i=>{const v=rec.votes[i];return `<li><a href="${esc(v.url)}" target="_blank" rel="noopener noreferrer">${esc(v.date)}　${esc(v.title)} ↗</a><small>全体：賛成 ${v.yes}・反対 ${v.no}</small></li>`;}).join('')}</ul></details>`;}
// ---- number cards for the member dialog: big number first, a few words under it ----
const stat=(label,val,unit,sub)=>`<div class="stat"><span class="stat-label">${label}</span><b class="stat-num">${val}${unit?`<small>${unit}</small>`:''}</b>${sub?`<span class="stat-sub">${sub}</span>`:''}</div>`;
async function openMember(id){
  const m=DB.members.find(x=>x.id===id);if(!m)return;
  openDialog(`<h2 class="dialog-title" id="dialog-title">${esc(m.name)}</h2><p class="dialog-sub">記録を読み込み中…</p>`);
  let rec;try{rec=await getRecords();}catch(e){$('#dialog-body').innerHTML=`<h2 class="dialog-title" id="dialog-title">${esc(m.name)}</h2><div class="empty"><strong>記録を読み込めませんでした</strong><p>時間をおいて再度開いてください。（${esc(e)}）</p></div>`;return;}
  if(!$('#detail').open)return;
  const r=rec.members[id]||{},b=r.b||{},meta=DB.meta.records||{},t=r.t||{},mb=m.bills;
  const k=t.kankeiDantai,rep=t.shushiR6,sp=m.sp||{},homo=m.activityStatus==='homonym';
  const photo=r.p?`<li>写真：<a href="${esc(r.p.filePage)}" target="_blank" rel="noopener noreferrer">Wikimedia Commons ↗</a>（${esc(r.p.artist)}・${esc(r.p.license)}）</li>`:'';
  const qi=r.q||[],qs=meta.questionSessions||[];
  const ownN=mb?mb.lead+(mb.co||0):null;
  const facts=`<div class="stat-grid">${[
    stat('質問・発言した会議',homo?'—':(sp.meet??0),homo?'':'回',homo?'同名の議員がいて数えられません':''),
    stat(`出した${term('法案')}`,ownN??'—',ownN==null?'':'本',''),
    stat('法律になった法案',mb?mb.passed:'—',mb?'本':'',''),
    stat(`文書での質問`,qi.length,'回',term('質問主意書')),
    ...(m.house==='参議院'&&r.v?[stat(`${term('本会議')}で反対`,m.votes.no,'回',`賛成${m.votes.yes}・投票なし${m.votes.none}`)]:[]),
  ].join('')}</div>${m.house==='衆議院'?`<p class="sec-note">${term('衆議院')}の本会議は、だれが賛成したかが残りません。</p>`:''}`;
  const dietNotes=homo?'':`<ul class="rec-list"><li>発言の回数は、全部で${m.speeches??0}回です（同じ会議で何回話しても、会議の数は1回）。</li>${sp.chair?`<li>${term('委員長')}として会議を進めた${sp.chair}回は、数えていません。</li>`:''}${sp.gov?`<li>大臣など（${term('政府側')}）としての答弁${sp.gov}回は、数えていません。</li>`:''}${mb&&m.house==='衆議院'?`<li>出した法案の内訳：中心になって${mb.lead}本・いっしょに${mb.co}本。賛成者として名前をのせた法案が${mb.sup}本あります。</li>`:mb?'<li>参議院は、いっしょに出した人の記録が公開されていません。</li>':''}</ul>`;
  const voteList=m.house==='参議院'&&r.v?`<h4 class="mini-h">参議院の本会議での投票</h4>${voteGroup(rec,r.v,'0','反対した採決',true)}${voteGroup(rec,r.v,'-','投票なし（欠席・棄権など。反対ではありません）',false)}${voteGroup(rec,r.v,'1','賛成した採決',false)}<p class="muted-line">押しボタン式の投票${meta.individualVotes}回のうち、在職中の${m.votes.n}回です。起立での採決（${meta.standingVotes}回）は、個人の賛否が残りません。</p>`:'';
  const billList=`<h4 class="mini-h">出した法案と、法律になったか</h4>${m.house==='参議院'?`${billGroup(rec,'中心になって出した法案',b.lead,true)}`:`${billGroup(rec,'中心になって出した法案',b.lead,true)}${billGroup(rec,'いっしょに出した法案',b.co,false)}${billGroup(rec,'賛成者として名前をのせた法案',b.sup,false)}`}<p class="muted-line">第${esc((meta.billSessions||[])[0])}〜${esc((meta.billSessions||[])[1])}回国会の、議員が出した法案です。「未成立」は、否決されたという意味ではありません。</p>`;
  const qList=qi.length?`<h4 class="mini-h">文書での質問（新しい順・最大20件）</h4><ul class="rec-list">${qi.map(i=>rec.questions[i]).sort((a,b)=>(+b.session-+a.session)||(b.number-a.number)).slice(0,20).map(q=>`<li><a href="${esc(q.url)}" target="_blank" rel="noopener noreferrer">第${esc(q.session)}回 ${esc(q.house)} 第${q.number}号　${esc(q.title)} ↗</a></li>`).join('')}</ul><p class="muted-line">第${esc(qs[0]||'')}〜${esc(qs.slice(-1)[0]||'')}回国会。いっしょに出した場合は、最初の提出者だけに数えています。</p>`:'';
  const orgs=k&&k.listed?`<p>総務省の名簿（${esc(k.asOf)}）に <b>${k.total}団体</b>がのっています。</p><ul class="rec-list">${k.orgs.map(o=>`<li><span>${esc(o.name)}</span><small>${esc(kubunLabel(o.kubun))} ／ 届出先：${esc(o.filedWith)}</small></li>`).join('')}</ul><a class="source-link" href="${esc(k.url)}" target="_blank" rel="noopener noreferrer">関係政治団体一覧（総務省・PDF） ↗</a>`:'<p>総務省の関係政治団体の名簿（令和8年3月31日時点）に、のっていません。その後に当選した場合や、届出がない場合があります。</p>';
  const reports=rep&&rep.reportCount?`<ul class="rec-list">${rep.reports.map(x=>`<li><a href="${esc(x.pdf)}" target="_blank" rel="noopener noreferrer">${esc(x.org)}（${esc(rep.year)}・${esc(x.publishedOn)}公表） ↗</a>${x.scannedImage?'<small>画像のPDFです。金額は、このサイトでは読み取っていません</small>':''}</li>`).join('')}</ul>`:'<p class="muted-line">総務大臣に出した令和6年分の報告書は、ありません（都道府県に出した分は対象外）。</p>';
  const notOnline=(meta.transparencyNotOnline||[]).map(x=>`<li>${esc(x.title)}：${esc(x.status)}</li>`).join('');
  const pp=partyPledges(m);
  const pledges=pp.length?pp.map(p=>`<div class="pledge-mini"><b>${esc(p.party)}</b>${p.status==='ok'?`<span>${esc(p.election)}・${p.pledges.length}件（うち具体的 ${p.pledges.filter(x=>x.verifiable).length}件）</span>`:`<span>${esc(p.note||'党の公約なし')}</span>`}</div>`).join('')+`<button class="card-button" data-action="pledges">政党の約束の原文を見る ↗</button>`:'<p>所属する政党の約束は、のっていません（無所属など）。</p>';
  const partyName=(m.parties&&m.parties[0])||m.kaihaName;
  const govBadge=(m.gov&&!m.gov.former?`<span class="mh-badge">いまは${esc(m.gov.posts[0])}</span>`:m.role?`<span class="mh-badge">${esc(m.role.label)}</span>`:'')+(partialTerm(m)?'<span class="mh-badge plain">2026年2月に初当選</span>':'');
  $('#dialog-body').innerHTML=`<div class="member-head">${avatar(m,true)}<div><h2 class="dialog-title" id="dialog-title">${esc(m.name)}</h2><p class="mh-kana">${esc(m.kana)}</p><p class="mh-line">${esc(partyName)}</p><p class="mh-line">${seatHtml(m)}・${term(m.house)}</p>${govBadge?`<p class="mh-badges">${govBadge}</p>`:''}</div></div>
  ${scoreDetail(m)}
  <section class="dialog-section" id="pp-section"><h3>選挙で、何を約束した？</h3><div id="pp-detail"><p class="muted-line">読み込み中…</p></div></section>
  <section class="dialog-section" id="diet-section"><h3>国会で、何をした？</h3><p class="sec-note">${esc(periodLabel())}の記録です。</p>${facts}
   <div id="speech-detail"><p class="muted-line">読み込み中…</p></div>
   <details class="more" id="bills-detail"><summary>数え方と、法案・投票・質問の一覧</summary>${dietNotes}${billList}${voteList}<div id="questions-detail">${qList}</div></details></section>
  <section class="dialog-section"><h3>お金は？</h3><div class="stat-grid">${(()=>{const c=DB.meta.records?.publicCost,tr=m.transp||{};return (c&&m.house==='衆議院'?stat('この議席にかかる税金（年）',`約${Math.round(c.perSeatYen/1e4).toLocaleString()}`,'万円','予算を議席の数で割った平均'):stat('この議席にかかる税金','衆議院と同じ制度','',''))+stat(`お金の報告をする団体`,tr.listed?tr.orgs:'—',tr.listed?'団体':'',term('関係政治団体'));})()}</div><details class="more"><summary>お金の報告と、議員にかかる税金のくわしい内訳</summary>${moneyMember(m)}<h4 class="mini-h">お金の報告をする団体（${term('関係政治団体')}）</h4>${orgs}<h4 class="mini-h">${term('収支報告書','お金の報告書')}（${rep?esc(rep.year):'令和6年分'}）</h4>${reports}${notOnline?`<h4 class="mini-h">まだ確かめられない資料</h4><ul>${notOnline}</ul>`:''}</details></section>
  <details class="more more-end"><summary>もっと見る（Xでの反応・政党の約束・出典）</summary>
   <section class="dialog-section" id="xr-section"><h3>Xでの反応（参考）</h3><div id="xr-detail"><p class="muted-line">読み込み中…</p></div></section>
   <section class="dialog-section"><h3>所属する政党の約束</h3><p>政党としての約束です。この人個人の約束ではありません。</p>${pledges}</section>
   <section class="dialog-section"><h3>出典と注意</h3><ul class="src-list"><li><a href="${m.profileUrl}" target="_blank" rel="noopener noreferrer">公式プロフィール ↗</a></li>${homo?'':`<li><a href="${esc(kokkaiUrl(m))}" target="_blank" rel="noopener noreferrer">国会の記録（会議録） ↗</a></li>`}${photo}</ul>
   ${m.gov?`<p class="muted-line">首相官邸の名簿：${esc(m.gov.posts.join('・'))}（${esc(m.gov.group)}）</p>`:''}
   <h4 class="mini-h">データの集め方と注意</h4><ul>${(meta.notes||[]).map(n=>`<li>${esc(n)}</li>`).join('')}</ul><p class="muted-line">確認日：${esc(DB.meta.fetchedAt)}。赤札・白紙は、対象の法案を決めて公開してから付けます。</p></section></details>`;
  getPP().then(all=>{const el=$('#pp-detail');if(el&&$('#detail').open)el.innerHTML=ppSection(m,all[m.id]);}).catch(()=>{const el=$('#pp-detail');if(el)el.innerHTML='<p class="muted-line">選挙の約束を読み込めませんでした。</p>';});
  getXR().then(all=>{const el=$('#xr-detail');if(el&&$('#detail').open)el.innerHTML=xrSection(m,all[m.id]);}).catch(()=>{const el=$('#xr-detail');if(el)el.innerHTML='<p class="muted-line">Xでの反応を読み込めませんでした。</p>';});
  getSpeeches().then(all=>{const el=$('#speech-detail');if(el&&$('#detail').open)el.innerHTML=speechSection(m,all[m.id]);}).catch(()=>{const el=$('#speech-detail');if(el)el.innerHTML=speechSection(m,null);});
}
function openDialog(html){$('#dialog-body').innerHTML=html;if(!$('#detail').open)$('#detail').showModal();$('#detail').scrollTop=0;}
function openPerson(id){const p=PEOPLE.find(p=>p.id===id);if(!p)return;openDialog(`<h2 class="dialog-title" id="dialog-title">${p.name}</h2><p class="dialog-sub">${p.party} / ${p.role}<br>記録日 ${p.date} · 対象制度：政党交付金</p><div class="dialog-grid"><div><span class="eyebrow">制度への立場</span><h3 style="margin-top:10px">${p.stance}</h3><p>${p.reason}</p></div><div><span class="eyebrow">透明化・監査への立場</span><h3 style="margin-top:10px">${p.transparency}</h3><p>${p.transparencyDetail}</p></div></div><section class="dialog-section"><h3>確認できた経過</h3><ol class="timeline">${p.timeline.map(([d,t])=>`<li><small>${d}</small>${t}</li>`).join('')}</ol></section><section class="dialog-section"><h3>採決での賛否</h3><p>${p.vote}</p></section><section class="dialog-section"><h3>実際の結果</h3><p>${p.result}</p><p style="margin-top:8px">経済効果・GDPへの寄与・費用対効果：未測定。数値は付けていません。</p></section><section class="dialog-section"><h3>出典を確認する</h3>${p.sources.map(source).join('')}<p style="margin-top:12px;color:var(--muted)">確認日：2026.11.02。2022年の質疑は議員本人の掲載資料を参照しています。現在の立場やすべての活動を網羅するものではありません。</p></section><section class="dialog-section"><h3>地域の扱い</h3><p>${p.regionNote}</p>${p.region?source('profile'):''}</section>`);}
function openIssue(){openDialog(`<h2 class="dialog-title" id="dialog-title">政党交付金</h2><p class="dialog-sub">制度を続けるか。使い道をどう確かめるか。</p><div class="dialog-grid"><div><span class="eyebrow">制度を支える考え方</span><h3 style="margin-top:8px">政治活動を社会全体で支える</h3><p>政党が活動するための経費を公的に支えるという考え方。金子氏の答弁では、民主主義における制度の意義が説明されています。</p></div><div><span class="eyebrow">制度に対する問題提起</span><h3 style="margin-top:8px">税金の使途を十分に検証できるか</h3><p>塩川氏の質疑では監査の範囲や権限が問われました。井上氏は制度を廃止する法案を発議しています。</p></div></div><section class="dialog-section"><h3>混同しない、2つの軸</h3><p>制度を支持していても、公開・監査の強化を支持する場合があります。制度の存廃と、透明化に関する個別提案への賛否を分けて確認します。</p></section><section class="dialog-section"><h3>対象の廃止法案はどうなった？</h3><p>第216回国会・参法第2号は審査未了。成立には至っていません。「誰かが反対票を投じて否決した」とは異なります。</p>${source('bill')}</section><section class="dialog-section"><h3>資料</h3>${source('law')}${source('debate')}${source('inoue')}</section><section class="dialog-section"><button class="card-button" data-action="issue-people">3人の記録を比較する ↗</button></section>`);}
function openMethod(){openDialog(`<h2 class="dialog-title" id="dialog-title">記録の読み方</h2><p class="dialog-sub">結論を先に決めず、判断の材料を確かめるために。</p><section class="dialog-section"><h3>この試作に含まれるもの</h3><p>①現職の国会議員全員（衆議院464人・参議院247人）の名簿。衆参両院の公式ページから取得し、会派・選挙区・当選回数（衆）・任期満了（参）を収録。②各議員の直近1年の国会での発言件数と、そのうち「政治資金」を含む発言件数（国会会議録検索システム）。③議員提出法案（第211〜222回国会。衆法は提出者・賛成者の全員、参法は筆頭発議者のみ）と成立の記録。④参議院本会議の押しボタン式投票の議員別の賛否。⑤総務省の関係政治団体一覧と、令和6年分収支報告書（総務大臣届出分）へのリンク。⑥各党公約のうち政治資金・透明性の項目と、各議員がいまの議席を得た選挙の選挙公報に載せた本人の公約（原文の抜き出し）。⑦政党交付金に関する事例記録（2022年の質疑、第216回国会の廃止法案）。最新の政策一覧や、賛否の判定ではありません。</p></section><section class="dialog-section"><h3>賛否の根拠を区別</h3><ul><li>発言：制度への考え方を述べた記録。</li><li>提出：法案や修正案を提出した記録。</li><li>採決：対象法案について実際に投票した記録。</li><li>未確認：資料を収録していない状態。賛成・反対へ振り分けません。</li></ul></section><section class="dialog-section"><h3>活動と成果は別</h3><p>質問・答弁・提案の事実は「活動」、成立・施行は「制度の変化」として扱います。経済効果はさらに別の検証が必要です。未測定をゼロとせず、意図や不正の有無を推測しません。</p></section><section class="dialog-section"><h3>比較・集計の範囲</h3><p>会派の表は、公式名簿の会派ごとの人数と、発言件数の中央値です。県別は小選挙区・選挙区で選ばれた議員のみで、比例代表はブロック別の別枠です。発言件数は発言者名の完全一致で数え、同姓同名の議員は件数を出しません。役職名（大臣・委員長など）で記録された発言は含まれない場合があります。赤札・達成率・総合順位は、判定基準と対象法案リストの公開後に算出します。</p></section><section class="dialog-section"><h3>更新とプライバシー</h3><p>資料確認日：2026年11月2日。自動更新はありません。ログイン・分析タグ・政治的関心の保存はありません。検索条件はページを閉じると消えます。外部出典は別タブで開きます。</p>${source('votes')}</section>`);}
function setView(view, updateHash=true){if(!['issues','people','parties','regions','rankings','government','money','rules'].includes(view))view='people';state.view=view;document.querySelectorAll('[data-view]').forEach(b=>{if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});({issues:renderIssues,people:renderPeople,parties:renderParties,regions:renderRegions,rankings:renderRankings,government:renderGovernment,money:renderMoney,rules:renderRules}[view])();if(updateHash)history.replaceState(null,'','#'+view+(view==='rankings'?rankQuery():''));}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.view)setView(b.dataset.view);
 if(b.dataset.pfYear){PF.year=Number(b.dataset.pfYear);renderParties();setTimeout(()=>$('#party-money')?.scrollIntoView(),0);return;}
 if(b.dataset.person)openPerson(b.dataset.person);
 if(b.dataset.member)openMember(b.dataset.member);
 if(b.dataset.action==='score-method')openScoreMethod();
 if(b.dataset.rkSide){R.rk.side=new Set(b.dataset.rkSide==='ruling'?['与党']:b.dataset.rkSide==='opp'?['野党']:['与党','野党','不明']);R.rk.shown=100;renderRankings();}
 if(b.dataset.action==='rk-copy')copyRankLink(b);
 if(b.dataset.rkUnit){R.rk.unit=b.dataset.rkUnit;R.rk.shown=100;renderRankings();}
 if(b.dataset.action==='rk-more'){R.rk.shown+=100;renderRankingTable();}
 if(b.dataset.rankPref){state.region=b.dataset.rankPref;R.pref=b.dataset.rankPref;R.block=null;setView('regions');$('#explore').scrollIntoView();}
 if(b.dataset.action==='money'){if($('#detail').open)$('#detail').close();setView('money');setTimeout(()=>$('#explore')?.scrollIntoView(),0);return;}
 if(b.dataset.action==='pledges'){$('#detail').close();setView('parties');setTimeout(()=>$('#pledges')?.scrollIntoView(),0);}
 if(b.dataset.kaiha){R.kaiha=new Set([b.dataset.kaiha]);R.houses=new Set(HOUSES);R.election=new Set(ELECTIONS);R.search='';R.shown=30;setView('people');$('#explore').scrollIntoView();}
 if(b.dataset.ms){const set=MS[b.dataset.ms]();const det=b.closest('details');det.querySelectorAll('[data-ms-item]').forEach(c=>{c.checked=b.dataset.msAll==='1';if(c.checked)set.add(c.value);else set.delete(c.value);});R.shown=30;R.rk.shown=100;rerender();det.querySelector('summary').textContent=det.querySelector('summary').textContent.split('：')[0]+'：'+(b.dataset.msAll==='1'?'すべて':'なし');}
 if(b.dataset.block){R.block=b.dataset.block;R.pref=null;renderRegionDetail();}
 if(b.dataset.region){state.region=b.dataset.region;R.pref=b.dataset.region;R.block=null;renderRegionDetail();}
 if(b.dataset.pending)openDialog(`<h2 class="dialog-title" id="dialog-title">${esc(b.dataset.pending)}</h2><p class="dialog-sub">記録はまだ収録していません。</p><section class="dialog-section"><h3>今後確認する項目</h3><ul><li>制度の支給先・対象・使途・金額</li><li>公開・監査・返還のルールと改正履歴</li><li>議員ごとの主張・提案・採決</li><li>成立・施行と、その後の変化</li></ul><p>制度の問題点や個人の立場を、確認前に断定しません。</p></section>`);
 if(b.dataset.action==='issue')openIssue();
 if(b.dataset.action==='issue-people'){$('#detail').close();setView('issues');$('.subheading')?.scrollIntoView();}
 if(b.dataset.action==='reset'){R.search='';R.houses=new Set(HOUSES);R.kaiha=new Set(DB.members.map(kaihaKey));R.election=new Set(ELECTIONS);R.shown=30;renderPeople();}
});
$('#method').addEventListener('click',openMethod);$('#coverage').addEventListener('click',openMethod);$('#close').addEventListener('click',()=>$('#detail').close());
$('#detail').addEventListener('click',e=>{if(e.target===$('#detail')){const r=$('#detail').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('#detail').close();}});
window.addEventListener('hashchange',()=>{const name=location.hash.slice(1).split('?')[0];readRankState();if(['issues','people','parties','regions','rankings','government','money','rules'].includes(name))setView(name,false);});
readRankState();renderWords();setView(location.hash.slice(1).split('?')[0],false);
document.querySelectorAll('[data-goto]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();setView(a.dataset.goto);document.getElementById('explore').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}));
document.addEventListener('change',e=>{const c=e.target;if(!c.dataset||!c.dataset.msItem)return;const set=MS[c.dataset.msItem]();if(c.checked)set.add(c.value);else set.delete(c.value);R.shown=30;R.rk.shown=100;rerender();const det=c.closest('details'),boxes=[...det.querySelectorAll('[data-ms-item]')],n=boxes.filter(x=>x.checked).length;det.querySelector('summary').textContent=det.querySelector('summary').textContent.split('：')[0]+'：'+(n===boxes.length?'すべて':n===0?'なし':n+'件選択');});
loadData();
document.addEventListener('click',e=>{const o=e.target.closest('[data-open-member]');if(o&&!e.target.closest('button,a'))openMember(o.dataset.openMember);});
document.addEventListener('keydown',e=>{const o=e.target.closest&&e.target.closest('[data-open-member]');if(o&&e.target===o&&(e.key==='Enter'||e.key===' ')){e.preventDefault();openMember(o.dataset.openMember);}});
function pickMapPref(el){state.region=el.dataset.mapPref;R.pref=el.dataset.mapPref;R.block=null;renderRegionDetail();}
document.addEventListener('click',e=>{const el=e.target.closest('[data-map-pref]');if(el)pickMapPref(el);});
document.addEventListener('keydown',e=>{const el=e.target.closest&&e.target.closest('[data-map-pref]');if(el&&(e.key==='Enter'||e.key===' ')){e.preventDefault();pickMapPref(el);}});
